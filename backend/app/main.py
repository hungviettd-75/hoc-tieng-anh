from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.v1.api import api_router
from app.core.config import settings
from app.db.base_class import Base
from app.db.session import engine
from app.models import models # Đảm bảo models được nạp để Base nhận diện
import os


# Tạo bảng database nếu chưa có
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI English Coach API",
    description="Modern AI-powered English Learning Platform API",
    version="1.0.0",
)



# Middleware để log request
@app.middleware("http")
async def log_requests(request, call_next):
    print(f"DEBUG: Receiving request {request.method} {request.url.path}")
    response = await call_next(request)
    print(f"DEBUG: Finished request {request.method} {request.url.path} with status {response.status_code}")
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to AI English Coach API", "status": "online"}

app.include_router(api_router, prefix=settings.API_V1_STR)

# Mount admin dashboard static files
admin_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "admin_dashboard")
if os.path.exists(admin_dir):
    app.mount("/admin", StaticFiles(directory=admin_dir, html=True), name="admin")

# Trigger reload (Force reload at 2026-05-16 15:05)
