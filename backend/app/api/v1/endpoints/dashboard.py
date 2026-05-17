from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import schemas, models
from app.api import deps
import random

router = APIRouter()

@router.get("/stats", response_model=schemas.dashboard.DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(deps.get_db),
    current_user: models.models.User = Depends(deps.get_current_user)
) -> Any:
    user = current_user
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Mock dynamic greeting & motivation
    greetings = ["Chào buổi tối", "Chào mừng trở lại", "Xin chào", "Cố lên nào"]
    motivations = [
        "Khả năng lưu loát của bạn đang tiến bộ mỗi ngày!",
        "Sự kiên trì là chìa khóa để làm chủ tiếng Anh.",
        "Hôm nay là một ngày tuyệt vời để học thêm 10 từ mới!"
    ]
    
    # Ensure relationships exist (mock if needed for demo)
    if not user.xp:
        user.xp = models.models.UserXP(user_id=user.id, total_xp=450, level=14)
        db.add(user.xp)
    
    if not user.streak:
        user.streak = models.models.Streak(user_id=user.id, current_streak=12, longest_streak=20)
        db.add(user.streak)
        
    if not user.daily_goals:
        user.daily_goals = [
            models.models.DailyGoal(user_id=user.id, goal_type="speaking", target_value=15, current_value=12),
            models.models.DailyGoal(user_id=user.id, goal_type="vocabulary", target_value=20, current_value=8)
        ]
        for goal in user.daily_goals:
            db.add(goal)
    
    db.commit()

    return {
        "full_name": user.full_name or "Alex",
        "greeting": random.choice(greetings),
        "motivation": random.choice(motivations),
        "xp": {
            "total_xp": user.xp.total_xp,
            "level": user.xp.level,
            "next_level_xp": 600
        },
        "streak": {
            "current_streak": user.streak.current_streak,
            "longest_streak": user.streak.longest_streak
        },
        "daily_goals": [
            {
                "goal_type": g.goal_type,
                "target_value": g.target_value,
                "current_value": g.current_value
            } for g in user.daily_goals
        ],
        "recent_activity": ["Luyện nói nâng cao", "Từ vựng trung cấp"]
    }
