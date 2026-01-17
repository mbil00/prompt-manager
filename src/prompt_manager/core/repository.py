"""Data access layer for prompt storage."""

from datetime import UTC, datetime
from typing import Literal

from slugify import slugify
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from prompt_manager.core.models import Prompt, PromptVersion
from prompt_manager.core.schemas import PromptCreate, PromptUpdate


class PromptRepository:
    """Repository for prompt CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: PromptCreate) -> Prompt:
        """Create a new prompt."""
        slug = data.slug or slugify(data.title)

        # Ensure unique slug
        existing = await self.get_by_slug(slug)
        if existing:
            base_slug = slug
            counter = 1
            while existing:
                slug = f"{base_slug}-{counter}"
                existing = await self.get_by_slug(slug)
                counter += 1

        prompt = Prompt(
            slug=slug,
            title=data.title,
            content=data.content,
            description=data.description,
            category=data.category,
            tags=data.tags,
            source_url=data.source_url,
            is_template=data.is_template,
            template_vars=data.template_vars,
            success_notes=data.success_notes,
            failure_notes=data.failure_notes,
            related_slugs=data.related_slugs,
        )

        self.session.add(prompt)
        await self.session.flush()

        # Create initial version
        version = PromptVersion(
            prompt_id=prompt.id,
            version=1,
            content=data.content,
            change_note="Initial version",
        )
        self.session.add(version)
        await self.session.commit()
        await self.session.refresh(prompt)

        return prompt

    async def get_by_slug(self, slug: str) -> Prompt | None:
        """Get a prompt by its slug."""
        result = await self.session.execute(select(Prompt).where(Prompt.slug == slug))
        return result.scalar_one_or_none()

    async def get_by_id(self, prompt_id: str) -> Prompt | None:
        """Get a prompt by its ID."""
        result = await self.session.execute(select(Prompt).where(Prompt.id == prompt_id))
        return result.scalar_one_or_none()

    async def update(self, slug: str, data: PromptUpdate) -> Prompt | None:
        """Update an existing prompt."""
        prompt = await self.get_by_slug(slug)
        if not prompt:
            return None

        update_data = data.model_dump(exclude_unset=True, exclude={"change_note"})
        content_changed = "content" in update_data and update_data["content"] != prompt.content

        for field, value in update_data.items():
            setattr(prompt, field, value)

        # Create version if content changed
        if content_changed:
            prompt.version += 1
            version = PromptVersion(
                prompt_id=prompt.id,
                version=prompt.version,
                content=update_data["content"],
                change_note=data.change_note,
            )
            self.session.add(version)

        await self.session.commit()
        await self.session.refresh(prompt)
        return prompt

    async def delete(self, slug: str) -> bool:
        """Delete a prompt by slug."""
        prompt = await self.get_by_slug(slug)
        if not prompt:
            return False

        await self.session.delete(prompt)
        await self.session.commit()
        return True

    async def list_prompts(
        self,
        page: int = 1,
        page_size: int = 20,
        category: str | None = None,
        tags: list[str] | None = None,
        search: str | None = None,
        sort: Literal["recent", "popular", "updated", "created"] = "created",
    ) -> tuple[list[Prompt], int]:
        """List prompts with filtering and pagination."""
        query = select(Prompt)

        # Apply filters
        if category:
            query = query.where(Prompt.category == category)

        if tags:
            # Filter prompts that have all specified tags
            for tag in tags:
                query = query.where(Prompt.tags.contains([tag]))

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                (Prompt.title.ilike(search_pattern))
                | (Prompt.content.ilike(search_pattern))
                | (Prompt.description.ilike(search_pattern))
            )

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply sorting
        if sort == "recent":
            query = query.order_by(Prompt.last_used_at.desc().nullslast())
        elif sort == "popular":
            query = query.order_by(Prompt.usage_count.desc())
        elif sort == "updated":
            query = query.order_by(Prompt.updated_at.desc())
        else:  # created
            query = query.order_by(Prompt.created_at.desc())

        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(query)
        prompts = list(result.scalars().all())

        return prompts, total

    async def increment_usage(self, slug: str) -> Prompt | None:
        """Increment usage count and update last_used_at."""
        prompt = await self.get_by_slug(slug)
        if not prompt:
            return None

        prompt.usage_count += 1
        prompt.last_used_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(prompt)
        return prompt

    async def get_versions(self, slug: str) -> list[PromptVersion]:
        """Get all versions of a prompt."""
        prompt = await self.get_by_slug(slug)
        if not prompt:
            return []

        result = await self.session.execute(
            select(PromptVersion)
            .where(PromptVersion.prompt_id == prompt.id)
            .order_by(PromptVersion.version.desc())
        )
        return list(result.scalars().all())

    async def get_version(self, slug: str, version: int) -> PromptVersion | None:
        """Get a specific version of a prompt."""
        prompt = await self.get_by_slug(slug)
        if not prompt:
            return None

        result = await self.session.execute(
            select(PromptVersion).where(
                PromptVersion.prompt_id == prompt.id, PromptVersion.version == version
            )
        )
        return result.scalar_one_or_none()

    async def get_categories(self) -> list[tuple[str, int]]:
        """Get all categories with their prompt counts."""
        result = await self.session.execute(
            select(Prompt.category, func.count(Prompt.id))
            .where(Prompt.category.isnot(None))
            .group_by(Prompt.category)
            .order_by(func.count(Prompt.id).desc())
        )
        return list(result.all())

    async def get_tags(self) -> dict[str, int]:
        """Get all tags with their counts."""
        result = await self.session.execute(select(Prompt.tags))
        tag_counts: dict[str, int] = {}
        for (tags,) in result.all():
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        return tag_counts

    async def get_stats(self) -> dict:
        """Get usage statistics."""
        # Total prompts
        total_result = await self.session.execute(select(func.count(Prompt.id)))
        total_prompts = total_result.scalar() or 0

        # Total usage
        usage_result = await self.session.execute(select(func.sum(Prompt.usage_count)))
        total_usage = usage_result.scalar() or 0

        # Categories
        categories = await self.get_categories()
        total_categories = len(categories)

        # Tags
        tags = await self.get_tags()
        total_tags = len(tags)

        # Most used
        most_used_result = await self.session.execute(
            select(Prompt).order_by(Prompt.usage_count.desc()).limit(5)
        )
        most_used = list(most_used_result.scalars().all())

        # Recently used
        recently_used_result = await self.session.execute(
            select(Prompt)
            .where(Prompt.last_used_at.isnot(None))
            .order_by(Prompt.last_used_at.desc())
            .limit(5)
        )
        recently_used = list(recently_used_result.scalars().all())

        # Recently added
        recently_added_result = await self.session.execute(
            select(Prompt).order_by(Prompt.created_at.desc()).limit(5)
        )
        recently_added = list(recently_added_result.scalars().all())

        return {
            "total_prompts": total_prompts,
            "total_categories": total_categories,
            "total_tags": total_tags,
            "total_usage": total_usage,
            "most_used": most_used,
            "recently_used": recently_used,
            "recently_added": recently_added,
        }

    async def get_random(self, category: str | None = None) -> Prompt | None:
        """Get a random prompt, optionally filtered by category."""
        query = select(Prompt)
        if category:
            query = query.where(Prompt.category == category)
        query = query.order_by(func.random()).limit(1)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
