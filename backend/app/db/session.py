from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Lấy URL kết nối từ cấu hình (Render cấp PostgreSQL, máy local cấp SQLite hoặc PostgreSQL tuỳ biến)
engine_url = settings.SQLALCHEMY_DATABASE_URI

# Nếu là SQLite, cần check_same_thread=False
connect_args = {"check_same_thread": False} if engine_url.startswith("sqlite") else {}

engine = create_engine(engine_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
