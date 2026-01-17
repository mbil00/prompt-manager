"""CRUD endpoints for prompts."""

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from prompt_manager.api.deps import AuthDep, ServiceDep
from prompt_manager.core.schemas import (
    PromptCreate,
    PromptRead,
    PromptUpdate,
    PromptVersionRead,
    RenderResponse,
)

router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.post("", response_model=PromptRead, status_code=status.HTTP_201_CREATED)
async def create_prompt(
    data: PromptCreate,
    service: ServiceDep,
    _auth: AuthDep,
) -> PromptRead:
    """Create a new prompt."""
    prompt = await service.create_prompt(data)
    return PromptRead.model_validate(prompt)


@router.get("/{slug}", response_model=PromptRead)
async def get_prompt(
    slug: str,
    service: ServiceDep,
    _auth: AuthDep,
    increment_usage: bool = Query(True, description="Whether to increment usage count"),
) -> PromptRead:
    """Get a prompt by slug."""
    prompt = await service.get_prompt(slug, increment_usage=increment_usage)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt '{slug}' not found",
        )
    return PromptRead.model_validate(prompt)


@router.put("/{slug}", response_model=PromptRead)
async def update_prompt(
    slug: str,
    data: PromptUpdate,
    service: ServiceDep,
    _auth: AuthDep,
) -> PromptRead:
    """Update a prompt."""
    prompt = await service.update_prompt(slug, data)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt '{slug}' not found",
        )
    return PromptRead.model_validate(prompt)


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt(
    slug: str,
    service: ServiceDep,
    _auth: AuthDep,
) -> None:
    """Delete a prompt."""
    deleted = await service.delete_prompt(slug)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt '{slug}' not found",
        )


@router.get("/{slug}/render", response_model=RenderResponse)
async def render_prompt(
    slug: str,
    service: ServiceDep,
    _auth: AuthDep,
    variables: dict[str, Any] | None = None,
) -> RenderResponse:
    """Render a prompt template with variables.

    Variables can be passed as query parameters: ?var1=value1&var2=value2
    """
    # Get variables from query string if not provided in body
    if variables is None:
        variables = {}

    prompt = await service.get_prompt(slug, increment_usage=False)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt '{slug}' not found",
        )

    result = await service.render_prompt(slug, variables)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt '{slug}' not found",
        )

    rendered, used_vars = result
    return RenderResponse(
        content=rendered,
        slug=slug,
        is_template=prompt.is_template,
        variables_used=used_vars,
    )


@router.get("/{slug}/versions", response_model=list[PromptVersionRead])
async def list_versions(
    slug: str,
    service: ServiceDep,
    _auth: AuthDep,
) -> list[PromptVersionRead]:
    """Get version history for a prompt."""
    versions = await service.get_versions(slug)
    return [PromptVersionRead.model_validate(v) for v in versions]


@router.get("/{slug}/versions/{version}", response_model=PromptVersionRead)
async def get_version(
    slug: str,
    version: int,
    service: ServiceDep,
    _auth: AuthDep,
) -> PromptVersionRead:
    """Get a specific version of a prompt."""
    version_record = await service.get_version(slug, version)
    if not version_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version} of prompt '{slug}' not found",
        )
    return PromptVersionRead.model_validate(version_record)


@router.post("/{slug}/versions/{version}/restore", response_model=PromptRead)
async def restore_version(
    slug: str,
    version: int,
    service: ServiceDep,
    _auth: AuthDep,
) -> PromptRead:
    """Restore a prompt to a previous version."""
    prompt = await service.restore_version(slug, version)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version} of prompt '{slug}' not found",
        )
    return PromptRead.model_validate(prompt)
