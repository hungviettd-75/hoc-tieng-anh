from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# --- Achievements ---
class AchievementBase(BaseModel):
    name: str
    description: Optional[str] = None
    icon_url: Optional[str] = None
    required_xp: int = 0
    condition_type: Optional[str] = None
    condition_value: Optional[int] = None

class AchievementCreate(AchievementBase):
    pass

class Achievement(AchievementBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class UserAchievementBase(BaseModel):
    user_id: int
    achievement_id: int

class UserAchievement(UserAchievementBase):
    id: int
    unlocked_at: datetime
    achievement: Achievement

    class Config:
        from_attributes = True

# --- Missions ---
class MissionBase(BaseModel):
    title: str
    description: Optional[str] = None
    reward_xp: int = 10
    mission_type: Optional[str] = None
    target_action: Optional[str] = None
    target_value: Optional[int] = None

class MissionCreate(MissionBase):
    pass

class Mission(MissionBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class UserMissionBase(BaseModel):
    user_id: int
    mission_id: int
    progress: int = 0
    is_completed: bool = False

class UserMission(UserMissionBase):
    id: int
    created_at: datetime
    mission: Mission

    class Config:
        from_attributes = True

# --- Rewards ---
class RewardBase(BaseModel):
    reward_type: Optional[str] = None
    amount: Optional[int] = None

class Reward(RewardBase):
    id: int
    user_id: int
    claimed_at: datetime

    class Config:
        from_attributes = True

# --- Leaderboard ---
class LeaderboardEntry(BaseModel):
    user_id: int
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    total_xp: int
    level: int

# --- Status ---
class GamificationStatus(BaseModel):
    total_xp: int
    level: int
    current_streak: int
    longest_streak: int
    achievements_count: int
    completed_missions_today: int
