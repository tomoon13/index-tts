"""
Auth Schemas
============

Pydantic schemas for authentication.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


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
    display_name: Optional[str] = Field(
        None,
        max_length=100,
        description="Display name",
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    """Request model for user login"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class TokenResponse(BaseModel):
    """Response model for successful authentication"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class UserInfo(BaseModel):
    """User information response"""
    id: int = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    username: Optional[str] = Field(None, description="Username")
    display_name: Optional[str] = Field(None, description="Display name")
    is_active: bool = Field(default=True, description="Account active status")
    is_verified: bool = Field(default=False, description="Email verified status")
    is_admin: bool = Field(default=False, description="Admin status")
    total_generations: int = Field(default=0, description="Total TTS generations")
    created_at: datetime
    last_login_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    """Response model for successful authentication with user info"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserInfo


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str


class ChangePasswordRequest(BaseModel):
    """Request model for password change"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="New password (min 8 characters)",
    )
