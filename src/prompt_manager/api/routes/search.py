"""Search and filter endpoints."""

from typing import Literal

from fastapi import APIRouter, Query

from prompt_manager.api.deps import AuthDep, ServiceDep
from prompt_manager.core.schemas import PromptList, PromptRead

router = APIRouter(tags=["search"])


@router.get("/prompts", response_model=PromptList)
async def list_prompts(
    service: ServiceDep,
    _auth: AuthDep,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    category: str | None = Query(None, description="Filter by category"),
    tags: str | None = Query(None, description="Filter by tags (comma-separated)"),
    q: str | None = Query(None, description="Full-text search query"),
    sort: Literal["recent", "popular", "updated", "created"] = Query(
        "created", description="Sort order"
    ),
) -> PromptList:
    """List prompts with filtering and pagination."""
    tag_list = tags.split(",") if tags else None

    return await service.list_prompts(
        page=page,
        page_size=page_size,
        category=category,
        tags=tag_list,
        search=q,
        sort=sort,
    )


@router.get("/random", response_model=PromptRead)
async def get_random_prompt(
    service: ServiceDep,
    _auth: AuthDep,
    category: str | None = Query(None, description="Filter by category"),
) -> PromptRead:
    """Get a random prompt, optionally filtered by category."""
    from fastapi import HTTPException, status

    prompt = await service.get_random(category)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No prompts found",
        )
    return PromptRead.model_validate(prompt)
