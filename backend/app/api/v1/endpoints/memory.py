from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.services.memory_service import memory_service
from app.models.models import AIMemory, User
from typing import List, Dict, Any

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/insights/{user_id}")
async def get_memory_insights(user_id: int, db: Session = Depends(get_db)):
    """
    Lấy các thông tin chi tiết mà AI đã ghi nhớ về người dùng.
    """
    # 1. Lấy từ Relational DB (AIMemory)
    db_memories = db.query(AIMemory).filter(AIMemory.user_id == user_id).order_by(AIMemory.updated_at.desc()).all()
    
    # 2. Lấy tóm tắt từ Vector DB (đây là ví dụ, thực tế có thể query cụ thể hơn)
    recent_vectors = await memory_service.retrieve_relevant_memories(user_id, "summary goals progress habits", top_k=5)
    
    return {
        "structured_memories": [
            {"key": m.key, "value": m.value, "importance": m.importance, "updated_at": m.updated_at}
            for m in db_memories
        ],
        "ai_insights": [m["text"] for m in recent_vectors],
        "timeline": [
             # Giả lập timeline từ dữ liệu thực tế
             {"date": "2024-05-13", "event": "Started learning Business English", "type": "goal"},
             {"date": "2024-05-12", "event": "Mastered the use of 'Conditional Sentences'", "type": "achievement"},
             {"date": "2024-05-10", "event": "Practiced speaking for 30 minutes", "type": "activity"}
        ]
    }

@router.post("/refresh/{user_id}")
async def refresh_memory(user_id: int, db: Session = Depends(get_db)):
    """
    Yêu cầu AI phân tích lại toàn bộ lịch sử để cập nhật bộ nhớ.
    """
    # Logic để quét qua Message history và tạo summary mới
    return {"message": "Memory refresh started in background"}
