"""
Routes Package
"""

from api.routes.health import router as health_router
from api.routes.jobs import router as jobs_router
from api.routes.auth import router as auth_router
from api.routes.users import router as users_router

__all__ = [
    "health_router",
    "jobs_router",
    "auth_router",
    "users_router",
]
