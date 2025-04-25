from .auth import router as auth_router
from .superadmin import router as superadmin_router
from .admin import router as admin_router

__all__ = ["auth_router", "superadmin_router", "admin_router"]