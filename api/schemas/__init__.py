"""
Pydantic Schemas Package
"""

from api.schemas.task import (
    TaskInfo,
    TaskCreate,
    TaskStatusEnum,
    GenerateResponse,
    TaskListResponse,
)
from api.schemas.job import (
    JobStatusEnum,
    JobLinks,
    JobCreateResponse,
    JobInfo,
    JobListItem,
    JobListResponse,
)
from api.schemas.tts import TTSGenerateRequest
from api.schemas.health import HealthResponse
from api.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserInfo,
    AuthResponse,
    MessageResponse,
    ChangePasswordRequest,
)
from api.schemas.user import (
    UserCreate,
    UserUpdate,
    UserSetPassword,
    UserListItem,
    UserDetail,
    UserListResponse,
)

__all__ = [
    # Task (legacy, kept for compatibility)
    "TaskInfo",
    "TaskCreate",
    "TaskStatusEnum",
    "GenerateResponse",
    "TaskListResponse",
    # Job (new)
    "JobStatusEnum",
    "JobLinks",
    "JobCreateResponse",
    "JobInfo",
    "JobListItem",
    "JobListResponse",
    # TTS
    "TTSGenerateRequest",
    # Health
    "HealthResponse",
    # Auth
    "RegisterRequest",
    "LoginRequest",
    "TokenResponse",
    "UserInfo",
    "AuthResponse",
    "MessageResponse",
    "ChangePasswordRequest",
    # User
    "UserCreate",
    "UserUpdate",
    "UserSetPassword",
    "UserListItem",
    "UserDetail",
    "UserListResponse",
]
