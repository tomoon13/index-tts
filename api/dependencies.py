"""
Dependencies
============

FastAPI dependency injection providers.
"""

import asyncio
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_session
from api.models.user import User
from api.services.auth_service import AuthService, UserService


# ============================================================================
# Global State
# ============================================================================

_tts_model = None
_task_semaphore: Optional[asyncio.Semaphore] = None


def set_tts_model(model):
    """Set the TTS model instance"""
    global _tts_model
    _tts_model = model


def set_task_semaphore(semaphore: asyncio.Semaphore):
    """Set the task semaphore"""
    global _task_semaphore
    _task_semaphore = semaphore


def get_tts_model():
    """Get the TTS model instance"""
    return _tts_model


def get_task_semaphore() -> asyncio.Semaphore:
    """Get the task semaphore for concurrency control"""
    return _task_semaphore


# ============================================================================
# Authentication Dependencies
# ============================================================================

# HTTP Bearer token scheme
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    """
    Dependency to get the current authenticated user.

    Validates JWT token from Authorization header and returns the user.

    Usage:
        @router.get("/protected")
        async def protected_route(user: User = Depends(get_current_user)):
            return {"user_id": user.id}
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # Decode and validate token
    user_id = AuthService.get_user_id_from_token(token)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    user_service = UserService(session)
    user = await user_service.get_user_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> Optional[User]:
    """
    Dependency to optionally get the current user.

    Returns None if no authentication provided (for public endpoints).
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials, session)
    except HTTPException:
        return None


async def get_current_admin_user(
    user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to get the current user and verify admin status.

    Raises 403 Forbidden if user is not an admin.

    Usage:
        @router.get("/admin-only")
        async def admin_route(user: User = Depends(get_current_admin_user)):
            return {"admin_id": user.id}
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return user
