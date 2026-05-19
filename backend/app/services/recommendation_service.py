import json
import uuid
from typing import List, Dict, Any
import google.generativeai as genai
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.models import User, UserSkillLevel, WeakPoint, LearningPreference, RecommendationHistory
from app.schemas.learn import RecommendationItem

class RecommendationService:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        # Using gemini-2.5-flash for stable quota and high performance
        self.model = genai.GenerativeModel('gemini-2.5-flash')

    async def generate_daily_recommendations(self, db: Session, user_id: int) -> List[RecommendationItem]:
        # Caching layer to make tab loading instant (~1ms) and keep daily recommendations stable
        import datetime as dt
        today_str = dt.date.today().isoformat()
        
        if not hasattr(self, "_cache"):
            self._cache = {}
            
        if user_id in self._cache:
            cached_date, cached_list = self._cache[user_id]
            if cached_date == today_str:
                # Query completed recommendation IDs from database
                completed_ids = {
                    r.recommended_content_id 
                    for r in db.query(RecommendationHistory)
                    .filter(
                        RecommendationHistory.user_id == user_id,
                        RecommendationHistory.status == "completed"
                    ).all()
                }
                # Filter out already completed items
                remaining = [item for item in cached_list if item.id not in completed_ids]
                return remaining

        # Fetch user profile data
        skill_level = db.query(UserSkillLevel).filter(UserSkillLevel.user_id == user_id).first()
        weak_points = db.query(WeakPoint).filter(WeakPoint.user_id == user_id, WeakPoint.is_resolved == False).all()
        preferences = db.query(LearningPreference).filter(LearningPreference.user_id == user_id).first()

        # Build prompt context
        context = f"User English Level: {skill_level.vocabulary if skill_level else 'A2'}\n"
        if weak_points:
            weak_points_str = ", ".join([wp.description for wp in weak_points])
            context += f"Weaknesses: {weak_points_str}\n"
        if preferences:
            context += f"Target Level: {preferences.target_level}\n"
            context += f"Daily Goal (minutes): {preferences.daily_time_goal_minutes}\n"

        prompt = (
            "You are an AI English Coach. Based on the user's profile below, recommend exactly 3 personalized learning activities for today.\n"
            f"{context}\n\n"
            "Return the response ONLY as a JSON array of objects. Each object must have the following keys:\n"
            "- 'topic': str (MUST be in Vietnamese, e.g., 'Làm chủ Thì Hiện tại Hoàn thành' or 'Từ vựng chủ đề Du lịch')\n"
            "- 'content_type': str (must be exactly 'grammar', 'vocabulary', 'roleplay', 'speaking', or 'listening')\n"
            "- 'difficulty_level': str (e.g., 'Beginner', 'Intermediate', 'Advanced')\n"
            "- 'estimated_minutes': int (e.g., 5)\n"
            "- 'description': str (MUST be a brief description in Vietnamese of what the user will do)\n"
            "- 'reason': str (MUST be a brief explanation in Vietnamese of why you recommend this based on their weaknesses or goals)\n"
            "\nCRITICAL REQUIREMENT: The fields 'topic', 'description', and 'reason' MUST be written entirely in Vietnamese. Do not include Markdown formatting like ```json or any other text outside the JSON array."
        )

        try:
            response = await self.model.generate_content_async(prompt)
            raw_text = response.text.strip()
            # Clean up markdown formatting if Gemini still includes it
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            
            data = json.loads(raw_text.strip())
            
            recommendations = []
            for item in data:
                # Store in DB
                rec_id = str(uuid.uuid4())
                db_rec = RecommendationHistory(
                    user_id=user_id,
                    recommended_content_id=rec_id,
                    topic=item.get("topic", "General English"),
                    content_type=item.get("content_type", "grammar"),
                    difficulty_level=item.get("difficulty_level", "Intermediate")
                )
                db.add(db_rec)
                
                recommendations.append(RecommendationItem(
                    id=rec_id,
                    topic=item.get("topic", "General English"),
                    content_type=item.get("content_type", "grammar"),
                    difficulty_level=item.get("difficulty_level", "Intermediate"),
                    estimated_minutes=item.get("estimated_minutes", 5),
                    description=item.get("description", ""),
                    reason=item.get("reason", "")
                ))
            db.commit()
            
            # Save to daily memory cache
            self._cache[user_id] = (today_str, recommendations)
            
            return recommendations
        except Exception as e:
            print(f"Error generating recommendations: {e}")
            # Fallback
            return [
                RecommendationItem(
                    id=str(uuid.uuid4()),
                    topic="Luyện Từ Vựng Mỗi Ngày",
                    content_type="vocabulary",
                    difficulty_level="Intermediate",
                    estimated_minutes=5,
                    description="Ôn tập 10 từ vựng tiếng Anh giao tiếp phổ biến hàng ngày.",
                    reason="Duy trì thói quen học tập đều đặn mỗi ngày."
                )
            ]

recommendation_service = RecommendationService()
