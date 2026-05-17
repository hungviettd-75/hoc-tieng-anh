from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class SkillLevelBase(BaseModel):
    vocabulary: float = 0.0
    grammar: float = 0.0
    pronunciation: float = 0.0
    listening: float = 0.0
    fluency: float = 0.0

class SkillLevel(SkillLevelBase):
    last_evaluated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class WeakPointBase(BaseModel):
    category: str
    description: str
    frequency: int = 1

class WeakPoint(WeakPointBase):
    id: int
    is_resolved: bool
    
    class Config:
        from_attributes = True

class RecommendationItem(BaseModel):
    id: str
    topic: str
    content_type: str
    difficulty_level: str
    estimated_minutes: int
    description: str
    reason: str # Why AI recommends this

class LearningDashboardResponse(BaseModel):
    skill_level: SkillLevel
    weak_points: List[WeakPoint]
    daily_recommendations: List[RecommendationItem]

class LearningPreferenceUpdate(BaseModel):
    daily_time_goal_minutes: Optional[int] = None
    target_level: Optional[str] = None
    focus_areas: Optional[List[str]] = None

class LessonCompleteRequest(BaseModel):
    recommendation_id: str
    topic: str
    content_type: str
    minutes_spent: int
