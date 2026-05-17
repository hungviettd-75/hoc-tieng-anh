from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.api import deps
from app.schemas import gamification as schemas
from app.services.gamification_service import gamification_service
from app.models.models import User

router = APIRouter()

@router.get("/status", response_model=schemas.GamificationStatus)
def get_gamification_status(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Get the current user's XP, level, and streak status."""
    return gamification_service.get_user_status(db, current_user.id)

@router.get("/leaderboard", response_model=List[schemas.LeaderboardEntry])
def get_leaderboard(
    limit: int = 10,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Get top users globally."""
    return gamification_service.get_leaderboard(db, limit=limit)

@router.get("/missions", response_model=List[schemas.UserMission])
def get_missions(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Get daily missions for the user."""
    return gamification_service.get_user_missions(db, current_user.id)

@router.post("/add_xp")
def add_xp(
    amount: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Add XP to a user (usually called internally, but exposed for demo)."""
    user_xp, leveled_up = gamification_service.add_xp(db, current_user.id, amount)
    return {"message": f"Added {amount} XP", "total_xp": user_xp.total_xp, "level": user_xp.level, "leveled_up": leveled_up}
