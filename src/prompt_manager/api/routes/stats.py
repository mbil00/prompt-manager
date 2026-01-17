"""Statistics and metadata endpoints."""

from fastapi import APIRouter

from prompt_manager.api.deps import AuthDep, ServiceDep
from prompt_manager.core.schemas import CategoryCount, Stats, TagCount

router = APIRouter(tags=["stats"])


@router.get("/stats", response_model=Stats)
async def get_stats(
    service: ServiceDep,
    _auth: AuthDep,
) -> Stats:
    """Get usage statistics."""
    return await service.get_stats()


@router.get("/categories", response_model=list[CategoryCount])
async def list_categories(
    service: ServiceDep,
    _auth: AuthDep,
) -> list[CategoryCount]:
    """List all categories with prompt counts."""
    categories = await service.get_categories()
    return [CategoryCount(category=cat, count=count) for cat, count in categories]


@router.get("/tags", response_model=list[TagCount])
async def list_tags(
    service: ServiceDep,
    _auth: AuthDep,
) -> list[TagCount]:
    """List all tags with counts."""
    tags = await service.get_tags()
    return sorted(
        [TagCount(tag=tag, count=count) for tag, count in tags.items()],
        key=lambda x: x.count,
        reverse=True,
    )
