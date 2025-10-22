from .auth import router as auth_router
from .superadmin import router as superadmin_router
from .admin import router as admin_router
from .ml import router as ml_router

__all__ = [
    "auth_router",
    "superadmin_router",
    "admin_router",
    "ml_router",
]

# This file makes the routes directory a Python package