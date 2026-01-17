"""API key authentication."""

from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

from prompt_manager.core.config import settings

api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


def is_localhost(request: Request) -> bool:
    """Check if request is from localhost."""
    client_host = request.client.host if request.client else None
    return client_host in ("127.0.0.1", "localhost", "::1")


async def verify_api_key(
    request: Request,
    api_key: str | None = Security(api_key_header),
) -> str | None:
    """Verify API key from Authorization header.

    Allows localhost bypass if configured.
    Returns the validated API key or None for localhost bypass.
    """
    # Allow localhost bypass if configured
    if settings.allow_localhost_bypass and is_localhost(request):
        return None

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide 'Authorization: Bearer <key>' header.",
        )

    # Handle "Bearer <key>" format
    if api_key.startswith("Bearer "):
        api_key = api_key[7:]

    if api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )

    return api_key
