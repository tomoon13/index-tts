"""
User Management Schemas
=======================

Pydantic schemas for user management operations.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator


class UserCreate(BaseModel):
    """Schema for creating a new user (admin only)"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Password (min 8 characters)",
    )
    username: Optional[str] = Field(
        None,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Optional username",
    )
    displayName: Optional[str] = Field(
        None,
        max_length=100,
        description="Display name",
        alias="displayName",
    )
    isAdmin: bool = Field(
        default=False,
        description="Admin status",
        alias="isAdmin",
    )
    isVerified: bool = Field(
        default=False,
        description="Email verified status",
        alias="isVerified",
    )

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserUpdate(BaseModel):
    """Schema for updating user (admin only)"""
    email: Optional[EmailStr] = Field(None, description="User email address")
    username: Optional[str] = Field(
        None,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Username",
    )
    displayName: Optional[str] = Field(
        None,
        max_length=100,
        description="Display name",
        alias="displayName",
    )
    isActive: Optional[bool] = Field(None, description="Active status", alias="isActive")
    isVerified: Optional[bool] = Field(None, description="Verified status", alias="isVerified")
    isAdmin: Optional[bool] = Field(None, description="Admin status", alias="isAdmin")

    model_config = ConfigDict(populate_by_name=True)


class UserSetPassword(BaseModel):
    """Schema for setting user password (admin only)"""
    newPassword: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="New password",
        alias="newPassword",
    )

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("newPassword")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserListItem(BaseModel):
    """User item in list response"""
    id: int
    email: str
    username: Optional[str] = None
    displayName: Optional[str] = Field(None, serialization_alias="displayName")
    isActive: bool = Field(..., serialization_alias="isActive")
    isVerified: bool = Field(..., serialization_alias="isVerified")
    isAdmin: bool = Field(..., serialization_alias="isAdmin")
    totalGenerations: int = Field(..., serialization_alias="totalGenerations")
    createdAt: datetime = Field(..., serialization_alias="createdAt")
    lastLoginAt: Optional[datetime] = Field(None, serialization_alias="lastLoginAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class UserDetail(BaseModel):
    """Detailed user information (admin only)"""
    id: int
    email: str
    username: Optional[str] = None
    displayName: Optional[str] = Field(None, serialization_alias="displayName")
    isActive: bool = Field(..., serialization_alias="isActive")
    isVerified: bool = Field(..., serialization_alias="isVerified")
    isAdmin: bool = Field(..., serialization_alias="isAdmin")
    totalGenerations: int = Field(..., serialization_alias="totalGenerations")
    createdAt: datetime = Field(..., serialization_alias="createdAt")
    lastLoginAt: Optional[datetime] = Field(None, serialization_alias="lastLoginAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class UserListResponse(BaseModel):
    """Response for user list endpoint"""
    users: list[UserListItem]
    total: int
    page: int
    pageSize: int = Field(..., serialization_alias="pageSize")

    model_config = ConfigDict(populate_by_name=True)
