from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models.models import User, UserSkillLevel, WeakPoint, LearningPreference
from app.schemas.learn import (
    LearningDashboardResponse, 
    LearningPreferenceUpdate, 
    SkillLevel, 
    WeakPoint as WeakPointSchema,
    LessonCompleteRequest
)
from app.services.recommendation_service import recommendation_service
from datetime import datetime

router = APIRouter()

@router.get("/dashboard", response_model=LearningDashboardResponse)
async def get_learning_dashboard(
    db: Session = Depends(get_db),
    user_id: int = 1 # Temporary hardcoded ID
):
    current_user = db.query(User).filter(User.id == user_id).first()
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")
    # Ensure user has SkillLevel and Preference initialized
    skill_level = db.query(UserSkillLevel).filter(UserSkillLevel.user_id == current_user.id).first()
    if not skill_level:
        skill_level = UserSkillLevel(user_id=current_user.id, vocabulary=20, grammar=20, pronunciation=20, listening=20, fluency=20)
        db.add(skill_level)
        db.commit()
        db.refresh(skill_level)
        
    preferences = db.query(LearningPreference).filter(LearningPreference.user_id == current_user.id).first()
    if not preferences:
        preferences = LearningPreference(user_id=current_user.id)
        db.add(preferences)
        db.commit()

    weak_points = db.query(WeakPoint).filter(WeakPoint.user_id == current_user.id, WeakPoint.is_resolved == False).all()

    # Generate daily recommendations
    recommendations = await recommendation_service.generate_daily_recommendations(db, current_user.id)

    return LearningDashboardResponse(
        skill_level=skill_level,
        weak_points=weak_points,
        daily_recommendations=recommendations
    )

@router.put("/preferences")
def update_learning_preferences(
    preferences_in: LearningPreferenceUpdate,
    db: Session = Depends(get_db),
    user_id: int = 1
):
    current_user = db.query(User).filter(User.id == user_id).first()
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")
    preferences = db.query(LearningPreference).filter(LearningPreference.user_id == current_user.id).first()
    if not preferences:
        preferences = LearningPreference(user_id=current_user.id)
        db.add(preferences)
        
    if preferences_in.daily_time_goal_minutes is not None:
        preferences.daily_time_goal_minutes = preferences_in.daily_time_goal_minutes
    if preferences_in.target_level is not None:
        preferences.target_level = preferences_in.target_level
    if preferences_in.focus_areas is not None:
        preferences.focus_areas = preferences_in.focus_areas

    db.commit()
    return {"status": "success", "message": "Preferences updated"}

@router.post("/complete-lesson")
def complete_lesson(
    request: LessonCompleteRequest,
    db: Session = Depends(get_db),
    user_id: int = 1
):
    # Record completion in history
    from app.models.models import RecommendationHistory
    rec = db.query(RecommendationHistory).filter(RecommendationHistory.recommended_content_id == request.recommendation_id).first()
    if rec:
        rec.is_completed = True
        rec.completed_at = datetime.now()
    
    # Reward user skill points
    skill_level = db.query(UserSkillLevel).filter(UserSkillLevel.user_id == user_id).first()
    if skill_level:
        reward = 1.5 # Basic reward per lesson
        if request.content_type == 'vocabulary':
            skill_level.vocabulary = min(100.0, skill_level.vocabulary + reward)
        elif request.content_type == 'grammar':
            skill_level.grammar = min(100.0, skill_level.grammar + reward)
        elif request.content_type == 'listening':
            skill_level.listening = min(100.0, skill_level.listening + reward)
        
        # Also increase fluency slightly for any lesson
        skill_level.fluency = min(100.0, skill_level.fluency + 0.2)
    
    db.commit()
    return {"status": "success", "xp_gained": 50, "skill_boosted": request.content_type}
