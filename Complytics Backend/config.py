from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os
from typing import Optional
from pathlib import Path

# Load environment variables first
# Try to find .env file in the backend directory (for local development)
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # In Docker, env_file directive handles this, but try to load anyway
    load_dotenv()

class Settings(BaseSettings):
    MONGODB_URL: str
    MONGODB_NAME: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    GOOGLE_API_KEY: Optional[str] = None
    
    # SMTP settings
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    SMTP_FROM_EMAIL: str
    
    class Config:
        # In Docker, env_file from docker-compose sets env vars directly
        # This is just a fallback for local development
        env_file = ".env"
        # Read from environment variables (which docker-compose sets)
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"

# Create settings instance
settings = Settings()