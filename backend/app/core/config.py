from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AI English Coach"
    
    # AI SERVICE
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    
    # PINECONE
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX_NAME: str = "ai-english-coach"

    # DATABASE
    POSTGRES_SERVER: str = "db"
    POSTGRES_USER: str = "admin"
    POSTGRES_PASSWORD: str = "password123"
    POSTGRES_DB: str = "ai_coach"
    SQLALCHEMY_DATABASE_URI: str = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}/{POSTGRES_DB}"

    # REDIS
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    # JWT
    SECRET_KEY: str = "YOUR_SUPER_SECRET_KEY_CHANGE_ME_IN_PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days

    class Config:
        case_sensitive = True
        env_file = [".env", "../.env"]
        env_file_encoding = 'utf-8'

settings = Settings()
