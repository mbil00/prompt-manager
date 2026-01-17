"""HTTP client for API communication."""

from typing import Any

import httpx

from prompt_manager.core.config import settings


class APIClient:
    """HTTP client for communicating with the Prompt Manager API."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        self.base_url = (base_url or settings.api_url).rstrip("/")
        self.api_key = api_key or settings.api_key
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._client = httpx.Client(
                base_url=self.base_url,
                headers=headers,
                timeout=30.0,
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self) -> "APIClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle API response and raise errors if needed."""
        if response.status_code == 404:
            raise NotFoundError(response.json().get("detail", "Not found"))
        if response.status_code == 401:
            raise AuthError(response.json().get("detail", "Unauthorized"))
        if response.status_code == 422:
            raise ValidationError(response.json().get("detail", "Validation error"))
        response.raise_for_status()
        if response.status_code == 204:
            return {}
        return response.json()

    # Prompt CRUD
    def create_prompt(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new prompt."""
        response = self.client.post("/api/v1/prompts", json=data)
        return self._handle_response(response)

    def get_prompt(
        self, slug: str, increment_usage: bool = True
    ) -> dict[str, Any]:
        """Get a prompt by slug."""
        params = {"increment_usage": str(increment_usage).lower()}
        response = self.client.get(f"/api/v1/prompts/{slug}", params=params)
        return self._handle_response(response)

    def update_prompt(self, slug: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update a prompt."""
        response = self.client.put(f"/api/v1/prompts/{slug}", json=data)
        return self._handle_response(response)

    def delete_prompt(self, slug: str) -> None:
        """Delete a prompt."""
        response = self.client.delete(f"/api/v1/prompts/{slug}")
        self._handle_response(response)

    # Render
    def render_prompt(
        self, slug: str, variables: dict[str, Any]
    ) -> dict[str, Any]:
        """Render a prompt template with variables."""
        response = self.client.get(
            f"/api/v1/prompts/{slug}/render",
            params={"variables": variables},
        )
        return self._handle_response(response)

    # Search
    def list_prompts(
        self,
        page: int = 1,
        page_size: int = 20,
        category: str | None = None,
        tags: list[str] | None = None,
        search: str | None = None,
        sort: str = "created",
    ) -> dict[str, Any]:
        """List prompts with filtering."""
        params: dict[str, Any] = {
            "page": page,
            "page_size": page_size,
            "sort": sort,
        }
        if category:
            params["category"] = category
        if tags:
            params["tags"] = ",".join(tags)
        if search:
            params["q"] = search

        response = self.client.get("/api/v1/prompts", params=params)
        return self._handle_response(response)

    def get_random(self, category: str | None = None) -> dict[str, Any]:
        """Get a random prompt."""
        params = {}
        if category:
            params["category"] = category
        response = self.client.get("/api/v1/random", params=params)
        return self._handle_response(response)

    # Versions
    def list_versions(self, slug: str) -> list[dict[str, Any]]:
        """Get version history for a prompt."""
        response = self.client.get(f"/api/v1/prompts/{slug}/versions")
        return self._handle_response(response)

    def get_version(self, slug: str, version: int) -> dict[str, Any]:
        """Get a specific version."""
        response = self.client.get(f"/api/v1/prompts/{slug}/versions/{version}")
        return self._handle_response(response)

    def restore_version(self, slug: str, version: int) -> dict[str, Any]:
        """Restore a prompt to a previous version."""
        response = self.client.post(
            f"/api/v1/prompts/{slug}/versions/{version}/restore"
        )
        return self._handle_response(response)

    # Stats
    def get_stats(self) -> dict[str, Any]:
        """Get usage statistics."""
        response = self.client.get("/api/v1/stats")
        return self._handle_response(response)

    def get_categories(self) -> list[dict[str, Any]]:
        """Get all categories."""
        response = self.client.get("/api/v1/categories")
        return self._handle_response(response)

    def get_tags(self) -> list[dict[str, Any]]:
        """Get all tags."""
        response = self.client.get("/api/v1/tags")
        return self._handle_response(response)


class APIError(Exception):
    """Base API error."""

    pass


class NotFoundError(APIError):
    """Resource not found."""

    pass


class AuthError(APIError):
    """Authentication error."""

    pass


class ValidationError(APIError):
    """Validation error."""

    pass
