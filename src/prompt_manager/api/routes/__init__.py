"""API route modules."""

from prompt_manager.api.routes.prompts import router as prompts_router
from prompt_manager.api.routes.search import router as search_router
from prompt_manager.api.routes.stats import router as stats_router

__all__ = ["prompts_router", "search_router", "stats_router"]
