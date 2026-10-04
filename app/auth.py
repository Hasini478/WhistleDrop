"""Authentication dependencies for WhistleDrop moderator endpoints.

Implements HTTP Basic authentication validated against environment credentials
using constant-time comparison to prevent timing attacks.
"""

from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from app.config import Settings, get_settings
from app.security import safe_compare

security_scheme = HTTPBasic(
    realm="WhistleDrop Moderator Area",
    auto_error=False,
)


def get_current_moderator(
    credentials: Annotated[HTTPBasicCredentials | None, Depends(security_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> str:
    """Validate moderator HTTP Basic credentials.

    Raises:
        HTTPException(401): If credentials are missing or invalid.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Moderator authentication required.",
            headers={"WWW-Authenticate": 'Basic realm="WhistleDrop Moderator Area"'},
        )

    is_username_valid = safe_compare(credentials.username, settings.MODERATOR_USERNAME)
    is_password_valid = safe_compare(credentials.password, settings.MODERATOR_PASSWORD)

    if not (is_username_valid and is_password_valid):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid moderator credentials.",
            headers={"WWW-Authenticate": 'Basic realm="WhistleDrop Moderator Area"'},
        )

    return credentials.username
