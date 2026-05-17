from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

class DailyGoalSchema(BaseModel):
    goal_type: str
    target_value: int
    current_value: int

class StreakSchema(BaseModel):
    current_streak: int
    longest_streak: int

class XPStats(BaseModel):
    total_xp: int
    level: int
    next_level_xp: int

class DashboardStats(BaseModel):
    full_name: str
    greeting: str
    motivation: str
    xp: XPStats
    streak: StreakSchema
    daily_goals: List[DailyGoalSchema]
    recent_activity: List[str]
