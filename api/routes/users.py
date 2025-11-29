"""
User Management Routes
======================

Admin-only endpoints for managing users (CRUD operations).
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_session
from api.dependencies import get_current_admin_user
from api.models.user import User
from api.schemas import (
    UserCreate,
    UserUpdate,
    UserSetPassword,
    UserListItem,
    UserDetail,
    UserListResponse,
    MessageResponse,
)
from api.services import AuthService, UserService

router = APIRouter(prefix="/v1/users", tags=["User Management"])


@router.get("", response_model=UserListResponse)
async def list_users(
    admin: User = Depends(get_current_admin_user),
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    pageSize: int = Query(20, ge=1, le=100, description="Items per page", alias="pageSize"),
    session: AsyncSession = Depends(get_session),
):
    """
    List all users (admin only).

    Returns paginated list of all users in the system.
    """
    user_service = UserService(session)

    skip = (page - 1) * pageSize
    users, total = await user_service.get_all_users(skip=skip, limit=pageSize)

    return UserListResponse(
        users=[UserListItem.model_validate(user) for user in users],
        total=total,
        page=page,
        pageSize=pageSize,
    )


@router.post("", response_model=UserDetail, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: UserCreate,
    admin: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Create a new user (admin only).

    Allows admin to create users with specified roles and permissions.
    """
    user_service = UserService(session)

    # Check if email already exists
    existing_user = await user_service.get_user_by_email(request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Check if username already exists
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

    # Set admin/verified flags if specified
    if request.isAdmin or request.isVerified:
        user.is_admin = request.isAdmin
        user.is_verified = request.isVerified
        await session.flush()

    await session.commit()

    print(f"✓ Admin {admin.id} created user: {user.id} ({user.email})")

    return UserDetail.model_validate(user)


@router.get("/{user_id}", response_model=UserDetail)
async def get_user(
    user_id: int,
    admin: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get user details (admin only).

    Returns detailed information about a specific user.
    """
    user_service = UserService(session)
    user = await user_service.get_user_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserDetail.model_validate(user)


@router.patch("/{user_id}", response_model=UserDetail)
async def update_user(
    user_id: int,
    request: UserUpdate,
    admin: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Update user (admin only).

    Allows updating user profile and permissions.
    """
    user_service = UserService(session)

    # Check if email is being changed and if it's already taken
    if request.email:
        existing_email = await user_service.get_user_by_email(request.email)
        if existing_email and existing_email.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use",
            )

    # Check if username is being changed and if it's already taken
    if request.username:
        existing_username = await user_service.get_user_by_username(request.username)
        if existing_username and existing_username.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )

    user = await user_service.update_user(
        user_id=user_id,
        email=request.email,
        username=request.username,
        display_name=request.displayName,
        is_active=request.isActive,
        is_verified=request.isVerified,
        is_admin=request.isAdmin,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    await session.commit()

    print(f"✓ Admin {admin.id} updated user: {user.id} ({user.email})")

    return UserDetail.model_validate(user)


@router.post("/{user_id}/password", response_model=MessageResponse)
async def set_user_password(
    user_id: int,
    request: UserSetPassword,
    admin: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Set user password (admin only).

    Allows admin to reset user passwords.
    """
    user_service = UserService(session)

    success = await user_service.update_password(user_id, request.newPassword)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    await session.commit()

    print(f"✓ Admin {admin.id} reset password for user: {user_id}")

    return MessageResponse(message="Password updated successfully")


@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: int,
    admin: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Delete user (admin only).

    Permanently deletes a user and all their tasks (CASCADE).

    Warning: This action cannot be undone!
    """
    # Prevent admin from deleting themselves
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    user_service = UserService(session)

    # Get user info before deletion
    user = await user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user_email = user.email

    success = await user_service.delete_user(user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    await session.commit()

    print(f"✓ Admin {admin.id} deleted user: {user_id} ({user_email})")

    return MessageResponse(message=f"User {user_email} deleted successfully")
