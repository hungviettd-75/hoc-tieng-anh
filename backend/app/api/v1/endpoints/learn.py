from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
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
    current_user: User = Depends(get_current_user)
):
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
    current_user: User = Depends(get_current_user)
):
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
    current_user: User = Depends(get_current_user)
):
    # Record completion in history
    from app.models.models import RecommendationHistory
    rec = db.query(RecommendationHistory).filter(RecommendationHistory.recommended_content_id == request.recommendation_id).first()
    if rec:
        rec.status = "completed"
    
    # Reward user skill points
    skill_level = db.query(UserSkillLevel).filter(UserSkillLevel.user_id == current_user.id).first()
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
    current_user: User = Depends(get_current_user)
):
    """
    API Kho từ vựng thông minh: Trả về danh sách từ vựng theo trình độ,
    kết hợp cá nhân hóa bằng các từ phát âm sai thực tế của người dùng từ PronunciationMistakeLog.
    """
    # 1. Định nghĩa kho từ vựng chuẩn (Base Vocabulary) cực kỳ phong phú theo cấp độ CEFR (15 từ mỗi cấp)
    base_vocab = {
        "A1": [
            {"word": "Beginner", "ipa": "/bɪˈɡɪnə(r)/", "meaning": "Người mới bắt đầu", "level": "A1", "status": "Mastered", "example": "This class is for total beginners."},
            {"word": "Practice", "ipa": "/ˈpræktɪs/", "meaning": "Luyện tập", "level": "A1", "status": "Learning", "example": "You need more speaking practice."},
            {"word": "Vocabulary", "ipa": "/vəˈkæbjuləri/", "meaning": "Từ vựng", "level": "A1", "status": "New", "example": "Reading helps build your vocabulary."},
            {"word": "Improve", "ipa": "/ɪmˈpruːv/", "meaning": "Cải thiện, nâng cao", "level": "A1", "status": "New", "example": "I want to improve my English speaking skills."},
            {"word": "Welcome", "ipa": "/ˈwelkəm/", "meaning": "Chào mừng", "level": "A1", "status": "New", "example": "Welcome to our English class!"},
            {"word": "Language", "ipa": "/ˈlæŋɡwɪdʒ/", "meaning": "Ngôn ngữ", "level": "A1", "status": "Learning", "example": "English is a global language."},
            {"word": "Simple", "ipa": "/ˈsɪmpl/", "meaning": "Đơn giản", "level": "A1", "status": "Mastered", "example": "Let's start with a simple sentence."},
            {"word": "Friend", "ipa": "/frend/", "meaning": "Người bạn", "level": "A1", "status": "Mastered", "example": "She is my best friend at school."},
            {"word": "Happy", "ipa": "/ˈhæpi/", "meaning": "Vui vẻ, hạnh phúc", "level": "A1", "status": "New", "example": "I am so happy to see you here today."},
            {"word": "Learn", "ipa": "/lɜːn/", "meaning": "Học hỏi", "level": "A1", "status": "Learning", "example": "We learn something new every single day."},
            {"word": "Family", "ipa": "/ˈfæməli/", "meaning": "Gia đình", "level": "A1", "status": "Mastered", "example": "I love spending time with my family."},
            {"word": "Morning", "ipa": "/ˈmɔːnɪŋ/", "meaning": "Buổi sáng", "level": "A1", "status": "New", "example": "He goes for a run every morning."},
            {"word": "School", "ipa": "/skuːl/", "meaning": "Trường học", "level": "A1", "status": "Learning", "example": "We walk to school together."},
            {"word": "Summer", "ipa": "/ˈsʌmə(r)/", "meaning": "Mùa hè", "level": "A1", "status": "New", "example": "Summer is my favorite season of the year."},
            {"word": "Active", "ipa": "/ˈæktɪv/", "meaning": "Năng động", "level": "A1", "status": "Learning", "example": "You should play an active role in class."}
        ],
        "A2": [
            {"word": "Journey", "ipa": "/ˈdʒɜːni/", "meaning": "Hành trình, chuyến đi", "level": "A2", "status": "Mastered", "example": "Learning English is a beautiful journey."},
            {"word": "Confident", "ipa": "/ˈkɒnfɪdənt/", "meaning": "Tự tin", "level": "A2", "status": "Learning", "example": "Be confident when speaking English!"},
            {"word": "Habit", "ipa": "/ˈhæbɪt/", "meaning": "Thói quen", "level": "A2", "status": "New", "example": "Make learning English a daily habit."},
            {"word": "Encourage", "ipa": "/ɪnˈkʌrɪdʒ/", "meaning": "Khuyến khích, động viên", "level": "A2", "status": "New", "example": "My tutor encouraged me to speak more."},
            {"word": "Positive", "ipa": "/ˈpɒzətɪv/", "meaning": "Tích cực", "level": "A2", "status": "Learning", "example": "Keep a positive attitude while learning."},
            {"word": "Healthy", "ipa": "/ˈhelθi/", "meaning": "Khỏe mạnh, lành mạnh", "level": "A2", "status": "Mastered", "example": "Eating fruits is a healthy choice."},
            {"word": "Creative", "ipa": "/kriˈeɪtɪv/", "meaning": "Sáng tạo", "level": "A2", "status": "New", "example": "She came up with a creative speaking topic."},
            {"word": "Success", "ipa": "/səkˈses/", "meaning": "Sự thành công", "level": "A2", "status": "New", "example": "Hard work is the key to success."},
            {"word": "Goal", "ipa": "/ɡəʊl/", "meaning": "Mục tiêu", "level": "A2", "status": "Learning", "example": "My main goal is to speak English fluently."},
            {"word": "Experience", "ipa": "/ɪkˈspɪəriəns/", "meaning": "Kinh nghiệm, trải nghiệm", "level": "A2", "status": "New", "example": "Travel gives you great life experience."},
            {"word": "Patient", "ipa": "/ˈpeɪʃnt/", "meaning": "Kiên nhẫn", "level": "A2", "status": "Mastered", "example": "Be patient with yourself when practicing."},
            {"word": "Support", "ipa": "/səˈpɔːt/", "meaning": "Hỗ trợ", "level": "A2", "status": "Learning", "example": "My teacher supports me a lot."},
            {"word": "Believe", "ipa": "/bɪˈliːv/", "meaning": "Tin tưởng", "level": "A2", "status": "Mastered", "example": "I believe you can master this level."},
            {"word": "Method", "ipa": "/ˈmeθəd/", "meaning": "Phương pháp", "level": "A2", "status": "New", "example": "What is your favorite study method?"},
            {"word": "Imagine", "ipa": "/ɪˈmædʒɪn/", "meaning": "Tưởng tượng", "level": "A2", "status": "Learning", "example": "Imagine speaking English without hesitation!"}
        ],
        "B1": [
            {"word": "Persistent", "ipa": "/pəˈsɪstənt/", "meaning": "Kiên trì, bền bỉ", "level": "B1", "status": "Learning", "example": "She is persistent in her efforts to learn English."},
            {"word": "Collaborate", "ipa": "/kəˈlæbəreɪt/", "meaning": "Cộng tác, hợp tác", "level": "B1", "status": "New", "example": "We can collaborate on this speaking task."},
            {"word": "Effective", "ipa": "/ɪˈfektɪv/", "meaning": "Hiệu quả", "level": "B1", "status": "Mastered", "example": "Shadowing is an effective method for fluency."},
            {"word": "Challenge", "ipa": "/ˈtʃælɪndʒ/", "meaning": "Thử thách", "level": "B1", "status": "New", "example": "Speaking with natives is a good challenge."},
            {"word": "Achieve", "ipa": "/əˈtʃiːv/", "meaning": "Đạt được", "level": "B1", "status": "Learning", "example": "You can achieve your dream score soon."},
            {"word": "Determine", "ipa": "/dɪˈtɜːmɪn/", "meaning": "Quyết định, xác định", "level": "B1", "status": "New", "example": "We need to determine the cause of the issue."},
            {"word": "Essential", "ipa": "/ɪˈsenʃl/", "meaning": "Thiết yếu, cần thiết", "level": "B1", "status": "Mastered", "example": "Practice is essential for language growth."},
            {"word": "Progress", "ipa": "/ˈprəʊɡres/", "meaning": "Sự tiến bộ", "level": "B1", "status": "Learning", "example": "You have made excellent progress today."},
            {"word": "Valuable", "ipa": "/ˈvæljuəbl/", "meaning": "Có giá trị, quý giá", "level": "B1", "status": "New", "example": "Feedback is very valuable for learners."},
            {"word": "Optimize", "ipa": "/ˈɒptɪmaɪz/", "meaning": "Tối ưu hóa", "level": "B1", "status": "New", "example": "Let's optimize our study schedule."},
            {"word": "Dynamic", "ipa": "/daɪˈnæmɪk/", "meaning": "Năng động, sôi nổi", "level": "B1", "status": "Learning", "example": "We had a dynamic discussion about culture."},
            {"word": "Strategy", "ipa": "/ˈstrætədʒ/", "meaning": "Chiến lược", "level": "B1", "status": "Mastered", "example": "I need a clear strategy to improve my score."},
            {"word": "Productive", "ipa": "/prəˈdʌktɪv/", "meaning": "Hiệu suất, năng suất", "level": "B1", "status": "New", "example": "I had a very productive study session."},
            {"word": "Opportunity", "ipa": "/ˌɒpəˈtjuːnəti/", "meaning": "Cơ hội", "level": "B1", "status": "Learning", "example": "Don't miss the opportunity to speak English."},
            {"word": "Flexibly", "ipa": "/ˈfleksebli/", "meaning": "Linh hoạt", "level": "B1", "status": "New", "example": "You should use vocab flexibly in contexts."}
        ],
        "B2": [
            {"word": "Substantial", "ipa": "/səbˈstænʃl/", "meaning": "Đáng kể, quan trọng", "level": "B2", "status": "New", "example": "You have made substantial progress in speaking."},
            {"word": "Fluency", "ipa": "/ˈfluːənsi/", "meaning": "Sự trôi chảy, lưu loát", "level": "B2", "status": "Learning", "example": "He speaks English with great fluency."},
            {"word": "Analyze", "ipa": "/ˈænəlaɪz/", "meaning": "Phân tích", "level": "B2", "status": "New", "example": "We need to analyze your pronunciation errors."},
            {"word": "Evaluate", "ipa": "/ɪˈvæljueɪt/", "meaning": "Đánh giá", "level": "B2", "status": "Mastered", "example": "The AI will evaluate your speech instantly."},
            {"word": "Alternative", "ipa": "/ɔːlˈtɜːnətɪv/", "meaning": "Giải pháp thay thế", "level": "B2", "status": "Learning", "example": "We should look for alternative solutions."},
            {"word": "Consequence", "ipa": "/ˈkɒnsɪkwəns/", "meaning": "Hậu quả, hệ quả", "level": "B2", "status": "New", "example": "Consider the consequences before acting."},
            {"word": "Significant", "ipa": "/sɪɡˈnɪfɪkənt/", "meaning": "Đáng kể, có ý nghĩa", "level": "B2", "status": "Mastered", "example": "There is a significant difference in accents."},
            {"word": "Distinguish", "ipa": "/dɪˈstɪŋɡwɪʃ/", "meaning": "Phân biệt", "level": "B2", "status": "New", "example": "It is hard to distinguish the twins."},
            {"word": "Innovative", "ipa": "/ˈɪnəveɪtɪv/", "meaning": "Mang tính đổi mới, đột phá", "level": "B2", "status": "Learning", "example": "She designed an innovative learning app."},
            {"word": "Perspective", "ipa": "/pəˈspektɪv/", "meaning": "Góc nhìn, quan điểm", "level": "B2", "status": "New", "example": "Try to see it from my perspective."},
            {"word": "Professional", "ipa": "/prəˈfeʃənl/", "meaning": "Chuyên nghiệp", "level": "B2", "status": "Mastered", "example": "He gave a professional speech in English."},
            {"word": "Sustainable", "ipa": "/səˈsteɪnəbl/", "meaning": "Bền vững", "level": "B2", "status": "New", "example": "We need a sustainable learning habit."},
            {"word": "Coherent", "ipa": "/kəʊˈhɪərənt/", "meaning": "Mạch lạc, chặt chẽ", "level": "B2", "status": "Learning", "example": "His essay was very coherent and clear."},
            {"word": "Efficient", "ipa": "/ɪˈfɪʃnt/", "meaning": "Hiệu quả, năng suất cao", "level": "B2", "status": "Mastered", "example": "This is an efficient tool to practice grammar."},
            {"word": "Implement", "ipa": "/ˈɪmplɪment/", "meaning": "Thi hành, thực thi", "level": "B2", "status": "New", "example": "Let's implement the new teaching method."}
        ],
        "C1": [
            {"word": "Pragmatic", "ipa": "/præɡˈmætɪk/", "meaning": "Thực tế, thực dụng", "level": "C1", "status": "New", "example": "We need a pragmatic approach to language learning."},
            {"word": "Eloquent", "ipa": "/ˈeləkwənt/", "meaning": "Hùng biện, thuyết phục", "level": "C1", "status": "Learning", "example": "She made an eloquent speech at the seminar."},
            {"word": "Cognitive", "ipa": "/kɒɡnətɪv/", "meaning": "Thuộc về nhận thức", "level": "C1", "status": "New", "example": "Bilingualism has great cognitive benefits."},
            {"word": "Sophisticated", "ipa": "/səˈfɪstɪkeɪtɪd/", "meaning": "Tinh tế, phức tạp, sành điệu", "level": "C1", "status": "Mastered", "example": "She uses sophisticated vocabulary when writing."},
            {"word": "Ambiguous", "ipa": "/æmˈbɪɡjuəs/", "meaning": "Mơ hồ, lưỡng nghĩa", "level": "C1", "status": "New", "example": "The instructions were a bit ambiguous."},
            {"word": "Comprehensive", "ipa": "/ˌkɒmprɪˈhensɪv/", "meaning": "Toàn diện, bao quát", "level": "C1", "status": "Learning", "example": "We need a comprehensive learning plan."},
            {"word": "Ephemeral", "ipa": "/ɪˈfemərəl/", "meaning": "Phù du, chóng tàn", "level": "C1", "status": "New", "example": "Fame is often ephemeral and temporary."},
            {"word": "Inevitable", "ipa": "/ɪnˈevɪtəbl/", "meaning": "Không thể tránh khỏi", "level": "C1", "status": "Mastered", "example": "Change is an inevitable part of life."},
            {"word": "Paradigm", "ipa": "/ˈpærədaɪm/", "meaning": "Hình mẫu, hệ hình", "level": "C1", "status": "New", "example": "This represents a paradigm shift in education."},
            {"word": "Resilient", "ipa": "/rɪˈzɪliənt/", "meaning": "Kiên cường, kiên định", "level": "C1", "status": "Learning", "example": "She is resilient in facing learning difficulties."},
            {"word": "Ubiquitous", "ipa": "/juːˈbɪkwɪtəs/", "meaning": "Phổ biến, ở khắp mọi nơi", "level": "C1", "status": "New", "example": "Smartphones are now ubiquitous in society."},
            {"word": "Volatile", "ipa": "/ˈvɒlətaɪl/", "meaning": "Biến động, dễ bay hơi", "level": "C1", "status": "Mastered", "example": "The job market is highly volatile today."},
            {"word": "Aesthetic", "ipa": "/iːsˈθetɪk/", "meaning": "Thuộc mỹ học, thẩm mỹ", "level": "C1", "status": "New", "example": "The application has a beautiful aesthetic design."},
            {"word": "Paradox", "ipa": "/ˈpærədɒks/", "meaning": "Nghịch lý", "level": "C1", "status": "Learning", "example": "It is a paradox that less is sometimes more."},
            {"word": "Synthesis", "ipa": "/ˈsɪnθəsɪs/", "meaning": "Sự tổng hợp", "level": "C1", "status": "Mastered", "example": "His theory is a synthesis of previous ideas."}
        ]
    }

    # Lấy danh sách từ nền cho level hiện tại (mặc định B1 nếu không thấy)
    base_pool = base_vocab.get(level, base_vocab["B1"])
    
    # Thực hiện xáo trộn ngẫu nhiên từ vựng để tạo tính tươi mới và thông minh
    import random
    shuffled_pool = list(base_pool)
    random.shuffle(shuffled_pool)
    vocab_list = shuffled_pool  # Lấy toàn bộ từ nền để hiển thị đầy đủ kho từ vựng

    # 2. Truy xuất các từ phát âm sai thực tế của User từ database để tích hợp vào "Kho từ vựng thông minh"
    from app.models.models import PronunciationMistakeLog
    mistakes = db.query(PronunciationMistakeLog).filter(
        PronunciationMistakeLog.user_id == current_user.id,
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
