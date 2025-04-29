from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db import database
from routes import auth_router, superadmin_router, admin_router
from routes.team import router as team_router
from config import settings
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.security import HTTPBearer
from routes.registration import router as registration_router


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
    
# CORS setup
origins = [
    "http://localhost:5173",  # React development server
    "http://localhost:3000",  # Alternative React port
    "http://127.0.0.1:5173",  # Alternative localhost format
    "http://127.0.0.1:3000",  # Alternative localhost format
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(superadmin_router, prefix="/superadmin", tags=["Superadmin"])
app.include_router(admin_router, prefix="/admin", tags=["Admin"])
app.include_router(registration_router, prefix="/registration", tags=["Registration"])
app.include_router(team_router, prefix="/team", tags=["Team"])


@app.on_event("startup")
async def startup_db():
    await database.connect()

@app.on_event("shutdown")
async def shutdown_db():
    await database.disconnect()