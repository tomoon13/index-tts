"""
Auth Routes
===========

Authentication endpoints for email/password login.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.database import get_session
from api.dependencies import get_current_user
from api.models.user import User
from api.schemas import (
    RegisterRequest,
    LoginRequest,
    AuthResponse,
    UserInfo,
    MessageResponse,
    ChangePasswordRequest,
)
from api.services import AuthService, UserService

router = APIRouter(prefix="/v1/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    request: RegisterRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Register a new user account.

    Returns an access token upon successful registration.
    """
    user_service = UserService(session)

    # Check if email already exists
    existing_user = await user_service.get_user_by_email(request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Check if username already exists (if provided)
    if request.username:
        existing_username = await user_service.get_user_by_username(request.username)
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )

    # Create user
    user = await user_service.create_user(
        email=request.email,
        password=request.password,
        username=request.username,
        display_name=request.displayName,
    )

    # Generate token
    access_token = AuthService.create_access_token(user.id)
    expires_in = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60

    print(f"[OK] New user registered: {user.id} ({user.email})")

    return AuthResponse(
        accessToken=access_token,
        tokenType="bearer",
        expiresIn=expires_in,
        user=UserInfo.model_validate(user),
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Login with username/email and password.

    Returns an access token upon successful authentication.
    """
    user_service = UserService(session)

    # Authenticate user (accepts both email and username)
    user = await user_service.authenticate(request.identifier, request.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate token
    access_token = AuthService.create_access_token(user.id)
    expires_in = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60

    print(f"[OK] User logged in: {user.id} ({user.email})")

    return AuthResponse(
        accessToken=access_token,
        tokenType="bearer",
        expiresIn=expires_in,
        user=UserInfo.model_validate(user),
    )


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    user: User = Depends(get_current_user),
):
    """
    Get current user information.

    Requires `Authorization: Bearer <token>` header.
    """
    return UserInfo.model_validate(user)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    request: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Change current user's password.

    Requires `Authorization: Bearer <token>` header.
    """
    # Verify current password
    if not AuthService.verify_password(request.currentPassword, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Update password
    user_service = UserService(session)
    await user_service.update_password(user.id, request.newPassword)

    return MessageResponse(message="Password changed successfully")


@router.get("/verify")
async def verify_auth(
    user: User = Depends(get_current_user),
):
    """
    Verify authentication status.

    Quick endpoint to check if the token is valid.
    Requires `Authorization: Bearer <token>` header.
    """
    return {
        "authenticated": True,
        "user_id": user.id,
        "email": user.email,
    }
