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
    
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        import os
        database_url = os.environ.get("DATABASE_URL")
        if database_url:
            # SQLAlchemy 2.0 requires postgresql:// instead of postgres://
            if database_url.startswith("postgres://"):
                database_url = database_url.replace("postgres://", "postgresql://", 1)
            return database_url
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"

    # REDIS
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    
    @property
    def REDIS_URL_CONFIG(self) -> str:
        import os
        redis_url = os.environ.get("REDIS_URL")
        if redis_url:
            return redis_url
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}"

    # JWT
    SECRET_KEY: str = "YOUR_SUPER_SECRET_KEY_CHANGE_ME_IN_PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days

    class Config:
        case_sensitive = True
        env_file = [".env", "../.env"]
        env_file_encoding = 'utf-8'

settings = Settings()

# Đảm bảo ưu tiên đọc trực tiếp từ biến môi trường hệ thống (đề phòng file .env đè giá trị rỗng trên Render)
import os
system_gemini_key = os.environ.get("GEMINI_API_KEY")
if system_gemini_key and system_gemini_key.strip():
    settings.GEMINI_API_KEY = system_gemini_key.strip()

system_openai_key = os.environ.get("OPENAI_API_KEY")
if system_openai_key and system_openai_key.strip():
    settings.OPENAI_API_KEY = system_openai_key.strip()

