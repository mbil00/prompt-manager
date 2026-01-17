"""Tests for prompt API endpoints."""

from typing import Any

import pytest
from httpx import AsyncClient


class TestPromptEndpoints:
    """Tests for /api/v1/prompts endpoints."""

    @pytest.mark.asyncio
    async def test_create_prompt(
        self, client: AsyncClient, sample_prompt_data: dict[str, Any]
    ) -> None:
        """Test creating a prompt via API."""
        response = await client.post("/api/v1/prompts", json=sample_prompt_data)
        assert response.status_code == 201

        data = response.json()
        assert data["slug"] == sample_prompt_data["slug"]
        assert data["title"] == sample_prompt_data["title"]
        assert data["content"] == sample_prompt_data["content"]
        assert data["version"] == 1

    @pytest.mark.asyncio
    async def test_create_prompt_auto_detect_template(
        self, client: AsyncClient, sample_template_data: dict[str, Any]
    ) -> None:
        """Test that templates are auto-detected."""
        response = await client.post("/api/v1/prompts", json=sample_template_data)
        assert response.status_code == 201

        data = response.json()
        assert data["is_template"] is True
        assert "name" in data["template_vars"]
        assert "place" in data["template_vars"]

    @pytest.mark.asyncio
    async def test_get_prompt(
        self, client: AsyncClient, sample_prompt_data: dict[str, Any]
    ) -> None:
        """Test getting a prompt by slug."""
        # Create first
        await client.post("/api/v1/prompts", json=sample_prompt_data)

        # Get
        response = await client.get(f"/api/v1/prompts/{sample_prompt_data['slug']}")
        assert response.status_code == 200

        data = response.json()
        assert data["slug"] == sample_prompt_data["slug"]
        assert data["usage_count"] == 1  # Should be incremented

    @pytest.mark.asyncio
    async def test_get_prompt_no_usage_increment(
        self, client: AsyncClient, sample_prompt_data: dict[str, Any]
    ) -> None:
        """Test getting a prompt without incrementing usage."""
        await client.post("/api/v1/prompts", json=sample_prompt_data)

        response = await client.get(
            f"/api/v1/prompts/{sample_prompt_data['slug']}",
            params={"increment_usage": "false"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["usage_count"] == 0

    @pytest.mark.asyncio
    async def test_get_prompt_not_found(self, client: AsyncClient) -> None:
        """Test getting a non-existent prompt."""
        response = await client.get("/api/v1/prompts/non-existent")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_prompt(
        self, client: AsyncClient, sample_prompt_data: dict[str, Any]
    ) -> None:
        """Test updating a prompt."""
        await client.post("/api/v1/prompts", json=sample_prompt_data)

        update_data = {"title": "Updated Title"}
        response = await client.put(
            f"/api/v1/prompts/{sample_prompt_data['slug']}",
            json=update_data,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["version"] == 1  # No version bump for non-content change

    @pytest.mark.asyncio
    async def test_update_prompt_content_creates_version(
        self, client: AsyncClient, sample_prompt_data: dict[str, Any]
    ) -> None:
        """Test that updating content creates a new version."""
        await client.post("/api/v1/prompts", json=sample_prompt_data)

        update_data = {"content": "New content"}
        response = await client.put(
            f"/api/v1/prompts/{sample_prompt_data['slug']}",
            json=update_data,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["content"] == "New content"
        assert data["version"] == 2

    @pytest.mark.asyncio
    async def test_delete_prompt(
        self, client: AsyncClient, sample_prompt_data: dict[str, Any]
    ) -> None:
        """Test deleting a prompt."""
        await client.post("/api/v1/prompts", json=sample_prompt_data)

        response = await client.delete(f"/api/v1/prompts/{sample_prompt_data['slug']}")
        assert response.status_code == 204

        # Verify deleted
        response = await client.get(f"/api/v1/prompts/{sample_prompt_data['slug']}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_prompts(
        self, client: AsyncClient, sample_prompt_data: dict[str, Any]
    ) -> None:
        """Test listing prompts."""
        # Create multiple prompts
        for i in range(3):
            data = {**sample_prompt_data, "slug": f"prompt-{i}"}
            await client.post("/api/v1/prompts", json=data)

        response = await client.get("/api/v1/prompts")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    @pytest.mark.asyncio
    async def test_list_prompts_filter_by_category(
        self, client: AsyncClient
    ) -> None:
        """Test filtering prompts by category."""
        await client.post(
            "/api/v1/prompts",
            json={"title": "Code 1", "content": "c1", "category": "code"},
        )
        await client.post(
            "/api/v1/prompts",
            json={"title": "Code 2", "content": "c2", "category": "code"},
        )
        await client.post(
            "/api/v1/prompts",
            json={"title": "Writing 1", "content": "w1", "category": "writing"},
        )

        response = await client.get("/api/v1/prompts", params={"category": "code"})
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 2
        assert all(item["category"] == "code" for item in data["items"])

    @pytest.mark.asyncio
    async def test_list_prompts_search(self, client: AsyncClient) -> None:
        """Test searching prompts."""
        await client.post(
            "/api/v1/prompts",
            json={"title": "Hello World", "content": "greeting"},
        )
        await client.post(
            "/api/v1/prompts",
            json={"title": "Goodbye", "content": "farewell"},
        )

        response = await client.get("/api/v1/prompts", params={"q": "hello"})
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Hello World"

    @pytest.mark.asyncio
    async def test_list_versions(
        self, client: AsyncClient, sample_prompt_data: dict[str, Any]
    ) -> None:
        """Test listing prompt versions."""
        await client.post("/api/v1/prompts", json=sample_prompt_data)

        # Create a new version
        await client.put(
            f"/api/v1/prompts/{sample_prompt_data['slug']}",
            json={"content": "Version 2"},
        )

        response = await client.get(
            f"/api/v1/prompts/{sample_prompt_data['slug']}/versions"
        )
        assert response.status_code == 200

        versions = response.json()
        assert len(versions) == 2
        assert versions[0]["version"] == 2
        assert versions[1]["version"] == 1

    @pytest.mark.asyncio
    async def test_get_version(
        self, client: AsyncClient, sample_prompt_data: dict[str, Any]
    ) -> None:
        """Test getting a specific version."""
        await client.post("/api/v1/prompts", json=sample_prompt_data)
        await client.put(
            f"/api/v1/prompts/{sample_prompt_data['slug']}",
            json={"content": "Version 2"},
        )

        response = await client.get(
            f"/api/v1/prompts/{sample_prompt_data['slug']}/versions/1"
        )
        assert response.status_code == 200

        data = response.json()
        assert data["version"] == 1
        assert data["content"] == sample_prompt_data["content"]


class TestStatsEndpoints:
    """Tests for stats endpoints."""

    @pytest.mark.asyncio
    async def test_get_stats(self, client: AsyncClient) -> None:
        """Test getting statistics."""
        # Create some prompts
        await client.post(
            "/api/v1/prompts",
            json={
                "title": "Test 1",
                "content": "Content 1",
                "category": "code",
                "tags": ["python"],
            },
        )
        await client.post(
            "/api/v1/prompts",
            json={
                "title": "Test 2",
                "content": "Content 2",
                "category": "writing",
                "tags": ["english"],
            },
        )

        response = await client.get("/api/v1/stats")
        assert response.status_code == 200

        data = response.json()
        assert data["total_prompts"] == 2
        assert data["total_categories"] == 2
        assert data["total_tags"] == 2

    @pytest.mark.asyncio
    async def test_get_categories(self, client: AsyncClient) -> None:
        """Test getting categories."""
        await client.post(
            "/api/v1/prompts",
            json={"title": "Test 1", "content": "c1", "category": "code"},
        )
        await client.post(
            "/api/v1/prompts",
            json={"title": "Test 2", "content": "c2", "category": "code"},
        )
        await client.post(
            "/api/v1/prompts",
            json={"title": "Test 3", "content": "c3", "category": "writing"},
        )

        response = await client.get("/api/v1/categories")
        assert response.status_code == 200

        categories = response.json()
        assert len(categories) == 2
        code_cat = next((c for c in categories if c["category"] == "code"), None)
        assert code_cat is not None
        assert code_cat["count"] == 2

    @pytest.mark.asyncio
    async def test_get_tags(self, client: AsyncClient) -> None:
        """Test getting tags."""
        await client.post(
            "/api/v1/prompts",
            json={"title": "Test 1", "content": "c1", "tags": ["python", "api"]},
        )
        await client.post(
            "/api/v1/prompts",
            json={"title": "Test 2", "content": "c2", "tags": ["python", "web"]},
        )

        response = await client.get("/api/v1/tags")
        assert response.status_code == 200

        tags = response.json()
        python_tag = next((t for t in tags if t["tag"] == "python"), None)
        assert python_tag is not None
        assert python_tag["count"] == 2
