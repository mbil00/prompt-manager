"""Tests for repository layer."""

from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from prompt_manager.core.repository import PromptRepository
from prompt_manager.core.schemas import PromptCreate, PromptUpdate


class TestPromptRepository:
    """Tests for PromptRepository."""

    @pytest_asyncio.fixture
    async def repo(self, test_session: AsyncSession) -> PromptRepository:
        return PromptRepository(test_session)

    @pytest.mark.asyncio
    async def test_create_prompt(
        self, repo: PromptRepository, sample_prompt_data: dict[str, Any]
    ) -> None:
        """Test creating a prompt."""
        data = PromptCreate(**sample_prompt_data)
        prompt = await repo.create(data)

        assert prompt.slug == sample_prompt_data["slug"]
        assert prompt.title == sample_prompt_data["title"]
        assert prompt.content == sample_prompt_data["content"]
        assert prompt.category == sample_prompt_data["category"]
        assert prompt.tags == sample_prompt_data["tags"]
        assert prompt.version == 1
        assert prompt.usage_count == 0

    @pytest.mark.asyncio
    async def test_create_prompt_auto_slug(self, repo: PromptRepository) -> None:
        """Test that slug is auto-generated from title."""
        data = PromptCreate(
            title="My Test Prompt",
            content="Test content",
        )
        prompt = await repo.create(data)
        assert prompt.slug == "my-test-prompt"

    @pytest.mark.asyncio
    async def test_create_prompt_unique_slug(
        self, repo: PromptRepository, sample_prompt_data: dict[str, Any]
    ) -> None:
        """Test that duplicate slugs are made unique."""
        data = PromptCreate(**sample_prompt_data)
        prompt1 = await repo.create(data)
        prompt2 = await repo.create(data)

        assert prompt1.slug == "test-prompt"
        assert prompt2.slug == "test-prompt-1"

    @pytest.mark.asyncio
    async def test_get_by_slug(
        self, repo: PromptRepository, sample_prompt_data: dict[str, Any]
    ) -> None:
        """Test getting a prompt by slug."""
        data = PromptCreate(**sample_prompt_data)
        created = await repo.create(data)

        prompt = await repo.get_by_slug(created.slug)
        assert prompt is not None
        assert prompt.id == created.id

    @pytest.mark.asyncio
    async def test_get_by_slug_not_found(self, repo: PromptRepository) -> None:
        """Test getting a non-existent prompt."""
        prompt = await repo.get_by_slug("non-existent")
        assert prompt is None

    @pytest.mark.asyncio
    async def test_update_prompt(
        self, repo: PromptRepository, sample_prompt_data: dict[str, Any]
    ) -> None:
        """Test updating a prompt."""
        data = PromptCreate(**sample_prompt_data)
        created = await repo.create(data)

        update = PromptUpdate(title="Updated Title")
        updated = await repo.update(created.slug, update)

        assert updated is not None
        assert updated.title == "Updated Title"
        assert updated.content == sample_prompt_data["content"]

    @pytest.mark.asyncio
    async def test_update_content_creates_version(
        self, repo: PromptRepository, sample_prompt_data: dict[str, Any]
    ) -> None:
        """Test that updating content creates a new version."""
        data = PromptCreate(**sample_prompt_data)
        created = await repo.create(data)
        assert created.version == 1

        update = PromptUpdate(content="New content", change_note="Updated content")
        updated = await repo.update(created.slug, update)

        assert updated is not None
        assert updated.version == 2
        assert updated.content == "New content"

    @pytest.mark.asyncio
    async def test_delete_prompt(
        self, repo: PromptRepository, sample_prompt_data: dict[str, Any]
    ) -> None:
        """Test deleting a prompt."""
        data = PromptCreate(**sample_prompt_data)
        created = await repo.create(data)

        deleted = await repo.delete(created.slug)
        assert deleted is True

        prompt = await repo.get_by_slug(created.slug)
        assert prompt is None

    @pytest.mark.asyncio
    async def test_delete_not_found(self, repo: PromptRepository) -> None:
        """Test deleting a non-existent prompt."""
        deleted = await repo.delete("non-existent")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_list_prompts(
        self, repo: PromptRepository, sample_prompt_data: dict[str, Any]
    ) -> None:
        """Test listing prompts."""
        # Create multiple prompts
        for i in range(5):
            data = PromptCreate(
                slug=f"prompt-{i}",
                title=f"Prompt {i}",
                content=f"Content {i}",
                category="testing",
            )
            await repo.create(data)

        prompts, total = await repo.list_prompts(page=1, page_size=10)
        assert total == 5
        assert len(prompts) == 5

    @pytest.mark.asyncio
    async def test_list_prompts_filter_by_category(
        self, repo: PromptRepository
    ) -> None:
        """Test filtering prompts by category."""
        # Create prompts in different categories
        for i, cat in enumerate(["code", "code", "writing"]):
            data = PromptCreate(
                slug=f"prompt-{i}",
                title=f"Prompt {i}",
                content=f"Content {i}",
                category=cat,
            )
            await repo.create(data)

        prompts, total = await repo.list_prompts(category="code")
        assert total == 2
        assert all(p.category == "code" for p in prompts)

    @pytest.mark.asyncio
    async def test_list_prompts_search(self, repo: PromptRepository) -> None:
        """Test searching prompts."""
        await repo.create(
            PromptCreate(
                slug="hello-world",
                title="Hello World",
                content="A greeting prompt",
            )
        )
        await repo.create(
            PromptCreate(
                slug="goodbye",
                title="Goodbye",
                content="A farewell prompt",
            )
        )

        prompts, total = await repo.list_prompts(search="hello")
        assert total == 1
        assert prompts[0].slug == "hello-world"

    @pytest.mark.asyncio
    async def test_increment_usage(
        self, repo: PromptRepository, sample_prompt_data: dict[str, Any]
    ) -> None:
        """Test incrementing usage count."""
        data = PromptCreate(**sample_prompt_data)
        created = await repo.create(data)
        assert created.usage_count == 0
        assert created.last_used_at is None

        updated = await repo.increment_usage(created.slug)
        assert updated is not None
        assert updated.usage_count == 1
        assert updated.last_used_at is not None

    @pytest.mark.asyncio
    async def test_get_versions(
        self, repo: PromptRepository, sample_prompt_data: dict[str, Any]
    ) -> None:
        """Test getting version history."""
        data = PromptCreate(**sample_prompt_data)
        created = await repo.create(data)

        # Create a new version
        await repo.update(created.slug, PromptUpdate(content="Version 2"))
        await repo.update(created.slug, PromptUpdate(content="Version 3"))

        versions = await repo.get_versions(created.slug)
        assert len(versions) == 3
        assert versions[0].version == 3
        assert versions[1].version == 2
        assert versions[2].version == 1

    @pytest.mark.asyncio
    async def test_get_categories(self, repo: PromptRepository) -> None:
        """Test getting category list."""
        for cat in ["code", "code", "writing", "general"]:
            await repo.create(
                PromptCreate(
                    title=f"Prompt in {cat}",
                    content="Content",
                    category=cat,
                )
            )

        categories = await repo.get_categories()
        assert len(categories) == 3
        assert any(cat == "code" and count == 2 for cat, count in categories)

    @pytest.mark.asyncio
    async def test_get_tags(self, repo: PromptRepository) -> None:
        """Test getting tag counts."""
        await repo.create(
            PromptCreate(
                title="Prompt 1",
                content="Content",
                tags=["python", "api"],
            )
        )
        await repo.create(
            PromptCreate(
                title="Prompt 2",
                content="Content",
                tags=["python", "web"],
            )
        )

        tags = await repo.get_tags()
        assert tags["python"] == 2
        assert tags["api"] == 1
        assert tags["web"] == 1
