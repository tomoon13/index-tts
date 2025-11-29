"""
Auth Schemas
============

Pydantic schemas for authentication.
"""

from datetime import datetime
from typing import Optional

from pydantic import EmailStr, Field, field_validator, ConfigDict

from api.schemas.base import BaseModel


class RegisterRequest(BaseModel):
    """Request model for user registration"""
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
        description="Optional username (alphanumeric, underscore, hyphen)",
    )
    displayName: Optional[str] = Field(
        None,
        max_length=100,
        description="Display name",
        alias="displayName",
    )

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    """Request model for user login"""
    identifier: str = Field(..., description="Username or email address", serialization_alias="identifier")
    password: str = Field(..., description="User password")

    model_config = ConfigDict(populate_by_name=True)


class TokenResponse(BaseModel):
    """Response model for successful authentication"""
    accessToken: str = Field(..., description="JWT access token", serialization_alias="accessToken")
    tokenType: str = Field(default="bearer", description="Token type", serialization_alias="tokenType")
    expiresIn: int = Field(..., description="Token expiration time in seconds", serialization_alias="expiresIn")

    model_config = ConfigDict(populate_by_name=True)


class UserInfo(BaseModel):
    """User information response - automatically converts snake_case to camelCase"""
    id: int = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    username: Optional[str] = Field(None, description="Username")
    display_name: Optional[str] = Field(None, description="Display name")
    is_active: bool = Field(default=True, description="Account active status")
    is_verified: bool = Field(default=False, description="Email verified status")
    is_admin: bool = Field(default=False, description="Admin status")
    total_generations: int = Field(default=0, description="Total TTS generations")
    created_at: datetime = Field(..., description="Created timestamp")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")


class AuthResponse(BaseModel):
    """Response model for successful authentication with user info"""
    accessToken: str = Field(..., serialization_alias="accessToken")
    tokenType: str = Field(default="bearer", serialization_alias="tokenType")
    expiresIn: int = Field(..., serialization_alias="expiresIn")
    user: UserInfo

    model_config = ConfigDict(populate_by_name=True)


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str


class ChangePasswordRequest(BaseModel):
    """Request model for password change"""
    currentPassword: str = Field(..., description="Current password", alias="currentPassword")
    newPassword: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="New password (min 8 characters)",
        alias="newPassword",
    )

    model_config = ConfigDict(populate_by_name=True)
