"""FastAPI dependency injection."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from prompt_manager.api.auth import verify_api_key
from prompt_manager.core.database import get_session
from prompt_manager.core.service import PromptService


async def get_prompt_service(
    session: AsyncSession = Depends(get_session),
) -> AsyncGenerator[PromptService, None]:
    """Get prompt service instance."""
    yield PromptService(session)


# Type aliases for cleaner route signatures
SessionDep = Annotated[AsyncSession, Depends(get_session)]
ServiceDep = Annotated[PromptService, Depends(get_prompt_service)]
AuthDep = Annotated[str | None, Depends(verify_api_key)]
