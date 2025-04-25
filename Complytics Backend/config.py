from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

# Load environment variables first
load_dotenv()

class Settings(BaseSettings):
    MONGODB_URL: str
    MONGODB_NAME: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    
    # SMTP settings
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    SMTP_FROM_EMAIL: str
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()