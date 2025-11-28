"""
Routes Package
"""

from api.routes.health import router as health_router
from api.routes.tts import router as tts_router
from api.routes.tasks import router as tasks_router
from api.routes.auth import router as auth_router

__all__ = [
    "health_router",
    "tts_router",
    "tasks_router",
    "auth_router",
]
