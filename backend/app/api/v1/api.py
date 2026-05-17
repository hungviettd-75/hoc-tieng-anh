from fastapi import APIRouter
from app.api.v1.endpoints import chat, auth, dashboard, speaking, learn, gamification, memory, admin

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(speaking.router, prefix="/speaking", tags=["speaking"])
api_router.include_router(learn.router, prefix="/learn", tags=["learn"])
api_router.include_router(gamification.router, prefix="/gamification", tags=["gamification"])
api_router.include_router(memory.router, prefix="/memory", tags=["memory"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])

# Placeholder for future route implementations
# api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
# api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
# api_router.include_router(users.router, prefix="/users", tags=["users"])

@api_router.get("/health")
def health_check():
    return {"status": "healthy"}
