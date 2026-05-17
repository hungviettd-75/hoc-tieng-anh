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

@router.get("/vocabulary")
def get_vocabulary_list(
    level: str = "B1",
    db: Session = Depends(get_db),
    user_id: int = 1
):
    """
    API Kho từ vựng thông minh: Trả về danh sách từ vựng theo trình độ,
    kết hợp cá nhân hóa bằng các từ phát âm sai thực tế của người dùng từ PronunciationMistakeLog.
    """
    # 1. Định nghĩa kho từ vựng chuẩn (Base Vocabulary) theo cấp độ CEFR
    base_vocab = {
        "A1": [
            {"word": "Beginner", "ipa": "/bɪˈɡɪnə(r)/", "meaning": "Người bắt đầu", "level": "A1", "status": "Mastered", "example": "This class is for total beginners."},
            {"word": "Practice", "ipa": "/ˈpræktɪs/", "meaning": "Luyện tập", "level": "A1", "status": "Learning", "example": "You need more speaking practice."},
            {"word": "Vocabulary", "ipa": "/vəˈkæbjuləri/", "meaning": "Từ vựng", "level": "A1", "status": "New", "example": "Reading helps build your vocabulary."},
            {"word": "Improve", "ipa": "/ɪmˈpruːv/", "meaning": "Cải thiện, nâng cao", "level": "A1", "status": "New", "example": "I want to improve my English speaking skills."}
        ],
        "A2": [
            {"word": "Journey", "ipa": "/ˈdʒɜːni/", "meaning": "Hành trình, chuyến đi", "level": "A2", "status": "Mastered", "example": "Learning English is a beautiful journey."},
            {"word": "Confident", "ipa": "/ˈkɒnfɪdənt/", "meaning": "Tự tin", "level": "A2", "status": "Learning", "example": "Be confident when speaking English!"},
            {"word": "Habit", "ipa": "/ˈhæbɪt/", "meaning": "Thói quen", "level": "A2", "status": "New", "example": "Make learning English a daily habit."},
            {"word": "Encourage", "ipa": "/ɪnˈkʌrɪdʒ/", "meaning": "Khuyến khích, động viên", "level": "A2", "status": "New", "example": "My tutor encouraged me to speak more."}
        ],
        "B1": [
            {"word": "Persistent", "ipa": "/pəˈsɪstənt/", "meaning": "Kiên trì, bền bỉ", "level": "B1", "status": "Learning", "example": "She is persistent in her efforts to learn English."},
            {"word": "Collaborate", "ipa": "/kəˈlæbəreɪt/", "meaning": "Cộng tác, hợp tác", "level": "B1", "status": "New", "example": "We can collaborate on this speaking task."},
            {"word": "Effective", "ipa": "/ɪˈfektɪv/", "meaning": "Hiệu quả", "level": "B1", "status": "Mastered", "example": "Shadowing is an effective method for fluency."},
            {"word": "Challenge", "ipa": "/ˈtʃælɪndʒ/", "meaning": "Thử thách", "level": "B1", "status": "New", "example": "Speaking with natives is a good challenge."}
        ],
        "B2": [
            {"word": "Substantial", "ipa": "/səbˈstænʃl/", "meaning": "Đáng kể, quan trọng", "level": "B2", "status": "New", "example": "You have made substantial progress in speaking."},
            {"word": "Fluency", "ipa": "/ˈfluːənsi/", "meaning": "Sự trôi chảy, lưu loát", "level": "B2", "status": "Learning", "example": "He speaks English with great fluency."},
            {"word": "Analyze", "ipa": "/ˈænəlaɪz/", "meaning": "Phân tích", "level": "B2", "status": "New", "example": "We need to analyze your pronunciation errors."},
            {"word": "Evaluate", "ipa": "/ɪˈvæljueɪt/", "meaning": "Đánh giá", "level": "B2", "status": "Mastered", "example": "The AI will evaluate your speech instantly."}
        ],
        "C1": [
            {"word": "Pragmatic", "ipa": "/præɡˈmætɪk/", "meaning": "Thực tế, thực dụng", "level": "C1", "status": "New", "example": "We need a pragmatic approach to language learning."},
            {"word": "Eloquent", "ipa": "/ˈeləkwənt/", "meaning": "Hùng biện, lưu loát thuyết phục", "level": "C1", "status": "Learning", "example": "She made an eloquent speech at the seminar."},
            {"word": "Cognitive", "ipa": "/ˈhɒɡnətɪv/", "meaning": "Liên quan đến nhận thức", "level": "C1", "status": "New", "example": "Bilingualism has great cognitive benefits."},
            {"word": "Sophisticated", "ipa": "/səˈfɪstɪkeɪtɪd/", "meaning": "Tinh tế, phức tạp, sành điệu", "level": "C1", "status": "Mastered", "example": "She uses sophisticated vocabulary when writing."}
        ]
    }

    # Lấy danh sách từ nền cho level hiện tại (mặc định B1 nếu không thấy)
    vocab_list = list(base_vocab.get(level, base_vocab["B1"]))

    # 2. Truy xuất các từ phát âm sai thực tế của User từ database để tích hợp vào "Kho từ vựng thông minh"
    from app.models.models import PronunciationMistakeLog
    mistakes = db.query(PronunciationMistakeLog).filter(
        PronunciationMistakeLog.user_id == user_id,
        PronunciationMistakeLog.is_mastered == False
    ).order_by(PronunciationMistakeLog.frequency.desc()).all()

    # Thêm các từ phát âm sai vào danh sách ôn tập (Personalized Spaced Repetition)
    for m in mistakes:
        # Kiểm tra tránh trùng lặp từ nền
        exists = any(v["word"].lower() == m.correct_word.lower() for v in vocab_list)
        if not exists:
            vocab_list.insert(0, {
                "word": m.correct_word,
                "ipa": m.ipa_target or "/.../",
                "meaning": f"Từ bạn cần ôn tập (Lỗi phát âm: '{m.original_word}')",
                "level": level,
                "status": "Learning",
                "example": f"Bạn đã nói từ này sai {m.frequency} lần. Hãy luyện lại ngay!"
            })

    return vocab_list
