"""
Auth Service
============

Handles user authentication with email/password and JWT tokens.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.models.user import User


class AuthService:
    """Service for authentication operations"""

    # JWT settings
    ALGORITHM = "HS256"

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode(), salt).decode()

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return bcrypt.checkpw(
            plain_password.encode(),
            hashed_password.encode()
        )

    @staticmethod
    def create_access_token(
        user_id: int,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Create a JWT access token"""
        if expires_delta is None:
            expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

        expire = datetime.now(timezone.utc) + expires_delta

        payload = {
            "sub": str(user_id),
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "access",
        }

        return jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=AuthService.ALGORITHM,
        )

    @staticmethod
    def decode_token(token: str) -> Optional[dict]:
        """Decode and validate a JWT token"""
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[AuthService.ALGORITHM],
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    @staticmethod
    def get_user_id_from_token(token: str) -> Optional[int]:
        """Extract user ID from a valid token"""
        payload = AuthService.decode_token(token)
        if payload and "sub" in payload:
            try:
                return int(payload["sub"])
            except ValueError:
                return None
        return None


class UserService:
    """Service for user management"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        result = await self.session.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def create_user(
        self,
        email: str,
        password: str,
        username: Optional[str] = None,
        display_name: Optional[str] = None,
    ) -> User:
        """Create a new user"""
        user = User(
            email=email.lower(),
            hashed_password=AuthService.hash_password(password),
            username=username,
            display_name=display_name or email.split("@")[0],
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def authenticate(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        user = await self.get_user_by_email(email)

        if not user:
            return None

        if not AuthService.verify_password(password, user.hashed_password):
            return None

        if not user.is_active:
            return None

        # Update last login
        user.last_login_at = datetime.now(timezone.utc)
        await self.session.flush()

        return user

    async def increment_generation_count(self, user_id: int) -> None:
        """Increment user's generation count"""
        user = await self.get_user_by_id(user_id)
        if user:
            user.total_generations += 1
            await self.session.flush()

    async def update_password(self, user_id: int, new_password: str) -> bool:
        """Update user's password"""
        user = await self.get_user_by_id(user_id)
        if user:
            user.hashed_password = AuthService.hash_password(new_password)
            await self.session.flush()
            return True
        return False

    async def deactivate_user(self, user_id: int) -> bool:
        """Deactivate a user"""
        user = await self.get_user_by_id(user_id)
        if user:
            user.is_active = False
            await self.session.flush()
            return True
        return False
