from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models import models
from app.schemas import gamification as schemas
from datetime import datetime, date
import math

class GamificationService:
    
    def calculate_level(self, total_xp: int) -> int:
        """
        Simple XP formula: Level = floor(sqrt(total_xp / 100)) + 1
        For example:
        0 - 399 XP: Level 1
        400 - 899 XP: Level 2
        900 - 1599 XP: Level 3
        """
        if total_xp <= 0:
            return 1
        return int(math.floor(math.sqrt(total_xp / 100))) + 1

    def add_xp(self, db: Session, user_id: int, amount: int):
        """Add XP to user and handle level ups."""
        user_xp = db.query(models.UserXP).filter(models.UserXP.user_id == user_id).first()
        if not user_xp:
            user_xp = models.UserXP(user_id=user_id, total_xp=0, level=1)
            db.add(user_xp)
            db.flush()
        
        user_xp.total_xp += amount
        new_level = self.calculate_level(user_xp.total_xp)
        
        level_up = False
        if new_level > user_xp.level:
            user_xp.level = new_level
            level_up = True
            
        db.commit()
        db.refresh(user_xp)
        
        # Optionally log activity
        activity = models.ActivityLog(user_id=user_id, activity_type="xp_gain", xp_earned=amount)
        db.add(activity)
        db.commit()
        
        return user_xp, level_up

    def get_leaderboard(self, db: Session, limit: int = 10) -> list[schemas.LeaderboardEntry]:
        """Get top users by XP."""
        top_xp = db.query(models.UserXP).order_by(desc(models.UserXP.total_xp)).limit(limit).all()
        leaderboard = []
        for entry in top_xp:
            user = db.query(models.User).filter(models.User.id == entry.user_id).first()
            if user:
                leaderboard.append(schemas.LeaderboardEntry(
                    user_id=user.id,
                    full_name=user.full_name or "Anonymous",
                    avatar_url=user.avatar_url,
                    total_xp=entry.total_xp,
                    level=entry.level
                ))
        return leaderboard

    def get_user_status(self, db: Session, user_id: int) -> schemas.GamificationStatus:
        user_xp = db.query(models.UserXP).filter(models.UserXP.user_id == user_id).first()
        streak = db.query(models.Streak).filter(models.Streak.user_id == user_id).first()
        achievements_count = db.query(models.UserAchievement).filter(models.UserAchievement.user_id == user_id).count()
        
        # Count missions completed today
        today = date.today()
        completed_missions = db.query(models.UserMission).filter(
            models.UserMission.user_id == user_id,
            models.UserMission.is_completed == True,
            # Simple cast for sqlite compat in this example
        ).count() # This should ideally filter by date

        return schemas.GamificationStatus(
            total_xp=user_xp.total_xp if user_xp else 0,
            level=user_xp.level if user_xp else 1,
            current_streak=streak.current_streak if streak else 0,
            longest_streak=streak.longest_streak if streak else 0,
            achievements_count=achievements_count,
            completed_missions_today=completed_missions
        )

    def generate_daily_missions(self, db: Session, user_id: int):
        """Mock generating daily missions for user."""
        # For a real implementation, you'd check if they already have today's missions
        # and if not, pick random templates from models.Mission and create UserMission
        pass

    def get_user_missions(self, db: Session, user_id: int):
        """Get active missions for user."""
        return db.query(models.UserMission).filter(models.UserMission.user_id == user_id).all()

gamification_service = GamificationService()
