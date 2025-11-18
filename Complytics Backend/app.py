from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db import database
from routes import auth_router, superadmin_router, admin_router, ml_router
from routes.team import router as team_router
from config import settings
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.security import HTTPBearer
from routes.registration import router as registration_router
from routes.compliance import router as compliance_router
from routes.azure import router as azure_router
from routes.ui_testing import router as ui_testing_router
from routes.azure_checker import router as azure_checker_router


app = FastAPI(docs_url=None, redoc_url=None)
security = HTTPBearer()

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="API Docs",
        swagger_ui_parameters={
            "defaultModelsExpandDepth": -1,
            "persistAuthorization": True,
            "displayRequestDuration": True,
            "docExpansion": "none",
            "tryItOutEnabled": True,
        },
        oauth2_redirect_url=None
    )
    
# CORS setup - Allow all origins for flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r".*",  # Allow all origins via regex (works with credentials)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(superadmin_router, prefix="/superadmin", tags=["superadmin"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])
app.include_router(registration_router, prefix="/registration", tags=["registration"])
app.include_router(team_router, prefix="/team", tags=["team"])
app.include_router(compliance_router, prefix="/api/compliance", tags=["compliance"])
app.include_router(azure_router, prefix="/api/azure", tags=["azure"])
app.include_router(ui_testing_router, prefix="/api", tags=["ui-testing"])
app.include_router(ml_router, prefix="/api/ml", tags=["ml"])
app.include_router(azure_checker_router, tags=["azure-checker"])


@app.on_event("startup")
async def startup_db():
    await database.connect()

@app.on_event("shutdown")
async def shutdown_db():
    await database.disconnect()