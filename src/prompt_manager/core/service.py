"""Business logic layer for prompt management."""

from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from prompt_manager.core.models import Prompt, PromptVersion
from prompt_manager.core.repository import PromptRepository
from prompt_manager.core.schemas import PromptCreate, PromptList, PromptRead, PromptUpdate, Stats
from prompt_manager.core.templates import TemplateEngine


class PromptService:
    """Service layer for prompt operations."""

    def __init__(self, session: AsyncSession):
        self.repo = PromptRepository(session)
        self.template_engine = TemplateEngine()

    async def create_prompt(self, data: PromptCreate) -> Prompt:
        """Create a new prompt, detecting if it's a template."""
        # Auto-detect template
        if not data.is_template:
            data.is_template = self.template_engine.is_template(data.content)

        # Extract template variables if it's a template
        if data.is_template and not data.template_vars:
            variables = self.template_engine.extract_variables(data.content)
            data.template_vars = {var: {"type": "string", "required": True} for var in variables}

        return await self.repo.create(data)

    async def get_prompt(self, slug: str, increment_usage: bool = True) -> Prompt | None:
        """Get a prompt by slug, optionally incrementing usage."""
        if increment_usage:
            return await self.repo.increment_usage(slug)
        return await self.repo.get_by_slug(slug)

    async def update_prompt(self, slug: str, data: PromptUpdate) -> Prompt | None:
        """Update a prompt."""
        # Auto-detect template if content is being updated
        if data.content is not None:
            if data.is_template is None:
                data.is_template = self.template_engine.is_template(data.content)

            if data.is_template and data.template_vars is None:
                variables = self.template_engine.extract_variables(data.content)
                data.template_vars = {var: {"type": "string", "required": True} for var in variables}

        return await self.repo.update(slug, data)

    async def delete_prompt(self, slug: str) -> bool:
        """Delete a prompt."""
        return await self.repo.delete(slug)

    async def list_prompts(
        self,
        page: int = 1,
        page_size: int = 20,
        category: str | None = None,
        tags: list[str] | None = None,
        search: str | None = None,
        sort: Literal["recent", "popular", "updated", "created"] = "created",
    ) -> PromptList:
        """List prompts with filtering and pagination."""
        prompts, total = await self.repo.list_prompts(
            page=page,
            page_size=page_size,
            category=category,
            tags=tags,
            search=search,
            sort=sort,
        )

        pages = (total + page_size - 1) // page_size if total > 0 else 1

        return PromptList(
            items=[PromptRead.model_validate(p) for p in prompts],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def render_prompt(
        self, slug: str, variables: dict[str, Any]
    ) -> tuple[str, dict[str, Any]] | None:
        """Render a prompt template with variables."""
        prompt = await self.get_prompt(slug, increment_usage=True)
        if not prompt:
            return None

        rendered = self.template_engine.render(prompt.content, variables)
        return rendered, variables

    async def get_versions(self, slug: str) -> list[PromptVersion]:
        """Get version history for a prompt."""
        return await self.repo.get_versions(slug)

    async def get_version(self, slug: str, version: int) -> PromptVersion | None:
        """Get a specific version of a prompt."""
        return await self.repo.get_version(slug, version)

    async def restore_version(self, slug: str, version: int) -> Prompt | None:
        """Restore a prompt to a previous version."""
        version_record = await self.repo.get_version(slug, version)
        if not version_record:
            return None

        return await self.repo.update(
            slug,
            PromptUpdate(
                content=version_record.content,
                change_note=f"Restored from version {version}",
            ),
        )

    async def add_note(
        self, slug: str, success_note: str | None = None, failure_note: str | None = None
    ) -> Prompt | None:
        """Add success or failure notes to a prompt."""
        prompt = await self.repo.get_by_slug(slug)
        if not prompt:
            return None

        update_data: dict[str, Any] = {}

        if success_note:
            existing = prompt.success_notes or ""
            update_data["success_notes"] = (
                f"{existing}\n\n---\n\n{success_note}" if existing else success_note
            )

        if failure_note:
            existing = prompt.failure_notes or ""
            update_data["failure_notes"] = (
                f"{existing}\n\n---\n\n{failure_note}" if existing else failure_note
            )

        if update_data:
            return await self.repo.update(slug, PromptUpdate(**update_data))

        return prompt

    async def get_categories(self) -> list[tuple[str, int]]:
        """Get all categories with counts."""
        return await self.repo.get_categories()

    async def get_tags(self) -> dict[str, int]:
        """Get all tags with counts."""
        return await self.repo.get_tags()

    async def get_stats(self) -> Stats:
        """Get usage statistics."""
        stats_data = await self.repo.get_stats()
        return Stats(
            total_prompts=stats_data["total_prompts"],
            total_categories=stats_data["total_categories"],
            total_tags=stats_data["total_tags"],
            total_usage=stats_data["total_usage"],
            most_used=[PromptRead.model_validate(p) for p in stats_data["most_used"]],
            recently_used=[PromptRead.model_validate(p) for p in stats_data["recently_used"]],
            recently_added=[PromptRead.model_validate(p) for p in stats_data["recently_added"]],
        )

    async def get_random(self, category: str | None = None) -> Prompt | None:
        """Get a random prompt."""
        return await self.repo.get_random(category)
