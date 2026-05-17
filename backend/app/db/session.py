from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Sử dụng SQLite để chạy trực tiếp trên máy (không cần Docker/PostgreSQL)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQLITE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'ai_coach.db')}"

engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
