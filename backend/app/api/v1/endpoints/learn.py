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
        {"word": "Journey", "ipa": "/ˈʤərni/", "meaning": "Hành trình, chuyến đi", "level": "A2", "status": "Mastered", "example": "Learning English is a beautiful journey."},
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
        {"word": "Challenge", "ipa": "/ˈʧælənʤ/", "meaning": "Thử thách", "level": "B1", "status": "New", "example": "Speaking with natives is a good challenge."},
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

@router.get("/vocabulary")
def get_vocabulary_list(
    level: str = "B1",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    API Kho từ vựng thông minh tích hợp AI Personalization:
    Ưu tiên đẩy các từ cần ôn tập (Spaced Repetition) và các từ hay sai (Weak Words) lên hàng đầu.
    """
    from app.models.models import Vocabulary, VocabularyMemory, VocabularyWrongAnswer
    from datetime import datetime
    
    # 1. Lấy danh sách từ vựng nền từ db hoặc fallback
    db_vocab = db.query(Vocabulary).filter(Vocabulary.level == level, Vocabulary.is_active == True).all()
    if db_vocab:
        base_pool = [
            {
                "word": v.word,
                "ipa": v.ipa,
                "meaning": v.meaning,
                "level": v.level,
                "status": "New",
                "example": v.example
            }
            for v in db_vocab
        ]
    else:
        # Dùng fallback base_vocab được khai báo phía trên
        base_pool = list(base_vocab.get(level, base_vocab["B1"]))

    # 2. Xáo trộn ngẫu nhiên từ vựng nền
    import random
    vocab_list = list(base_pool)
    random.shuffle(vocab_list)

    # 3. Lấy danh sách từ đến hạn ôn tập (Spaced Repetition)
    now = datetime.utcnow()
    scheduled_memories = db.query(VocabularyMemory).filter(
        VocabularyMemory.user_id == current_user.id,
        VocabularyMemory.next_review_at <= now
    ).all()
    scheduled_words = {m.word.lower(): m for m in scheduled_memories}

    # 4. Lấy danh sách từ hay trả lời sai
    wrong_records = db.query(VocabularyWrongAnswer).filter(
        VocabularyWrongAnswer.user_id == current_user.id
    ).order_by(VocabularyWrongAnswer.error_count.desc()).all()
    wrong_words = {w.word.lower(): w for w in wrong_records}

    # 5. Cập nhật status của các từ trong danh sách và ưu tiên sắp xếp
    priority_list = []
    normal_list = []

    for item in vocab_list:
        word_lower = item["word"].lower()
        if word_lower in scheduled_words:
            item["status"] = "Learning"
            item["meaning"] = f"{item['meaning']} 🔄 (Đến hạn ôn tập)"
            priority_list.append(item)
        elif word_lower in wrong_words:
            item["status"] = "Learning"
            item["meaning"] = f"{item['meaning']} ⚠️ (Từ hay sai, lỗi: {wrong_words[word_lower].error_count} lần)"
            priority_list.append(item)
        else:
            normal_list.append(item)

    # Kết hợp: Ưu tiên trước, từ bình thường sau
    return priority_list + normal_list

# --- Vocabulary Game API ---
from pydantic import BaseModel
from typing import List
import random

class AnswerSubmit(BaseModel):
    word: str
    user_answer: str

class AttemptIn(BaseModel):
    word: str
    user_answer: str
    is_correct: bool

class GameResultIn(BaseModel):
    level: str
    score: int
    xp_earned: int
    duration_seconds: int
    attempts: List[AttemptIn]

@router.get("/vocabulary-game/questions")
def get_game_questions(
    level: str = "B1",
    topic: str | None = None,
    words: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lấy danh sách câu hỏi game trắc nghiệm từ vựng theo chủ đề (topic) hoặc danh sách từ chỉ định (words),
    ưu tiên từ cần ôn tập (Spaced Repetition) và từ hay sai (Weak Words).
    """
    from app.models.models import Vocabulary, VocabularyMemory, VocabularyWrongAnswer
    from datetime import datetime
    
    # 1. Xác định pool từ vựng cơ sở dựa trên topic/words hoặc level
    vocab_pool_dict = {}
    
    if words:
        # Lọc theo danh sách từ cụ thể được truyền từ frontend
        word_list = [w.strip().lower() for w in words.split(",") if w.strip()]
        db_vocab = db.query(Vocabulary).filter(
            Vocabulary.word.in_(word_list),
            Vocabulary.is_active == True
        ).all()
        for v in db_vocab:
            vocab_pool_dict[v.word.lower()] = {
                "word": v.word,
                "ipa": v.ipa,
                "meaning": v.meaning,
                "example": v.example,
                "level": v.level
            }
            
        # Tìm thêm từ fallback từ base_vocab
        for lvl_name, lvl_words in base_vocab.items():
            for w in lvl_words:
                w_low = w["word"].lower()
                if w_low in word_list and w_low not in vocab_pool_dict:
                    vocab_pool_dict[w_low] = {
                        "word": w["word"],
                        "ipa": w["ipa"],
                        "meaning": w["meaning"],
                        "example": w["example"],
                        "level": w["level"]
                    }
                    
        # Bổ sung quét fallback từ toàn bộ topic_vocab_db (15 chủ đề) nếu DB hoặc base_vocab vẫn trống/thiếu từ
        for t_code, t_levels in topic_vocab_db.items():
            for lvl_name, lvl_words in t_levels.items():
                for item in lvl_words:
                    w_low = item["word"].lower()
                    if w_low in word_list and w_low not in vocab_pool_dict:
                        vocab_pool_dict[w_low] = {
                            "word": item["word"],
                            "ipa": item["ipa"],
                            "meaning": item["meaning"],
                            "example": item["example"],
                            "level": lvl_name
                        }
    elif topic:
        # Lọc theo chủ đề cụ thể
        db_vocab = db.query(Vocabulary).filter(
            Vocabulary.topic == topic,
            Vocabulary.level == level,
            Vocabulary.is_active == True
        ).all()
        for v in db_vocab:
            vocab_pool_dict[v.word.lower()] = {
                "word": v.word,
                "ipa": v.ipa,
                "meaning": v.meaning,
                "example": v.example,
                "level": v.level
            }
            
        # Fallback từ topic_vocab_db nếu DB trống hoặc thiếu
        fallback_topic = topic_vocab_db.get(topic, topic_vocab_db.get("travel", {}))
        fallback_list = fallback_topic.get(level, fallback_topic.get("B1", []))
        for item in fallback_list:
            w_low = item["word"].lower()
            if w_low not in vocab_pool_dict:
                vocab_pool_dict[w_low] = {
                    "word": item["word"],
                    "ipa": item["ipa"],
                    "meaning": item["meaning"],
                    "example": item["example"],
                    "level": level
                }
    else:
        # Mặc định lọc theo level
        db_vocab = db.query(Vocabulary).filter(
            Vocabulary.level == level, 
            Vocabulary.is_active == True
        ).all()
        for v in db_vocab:
            vocab_pool_dict[v.word.lower()] = {
                "word": v.word,
                "ipa": v.ipa,
                "meaning": v.meaning,
                "example": v.example,
                "level": v.level
            }
            
        fallback_list = base_vocab.get(level, base_vocab["B1"])
        for item in fallback_list:
            w_low = item["word"].lower()
            if w_low not in vocab_pool_dict:
                vocab_pool_dict[w_low] = {
                    "word": item["word"],
                    "ipa": item["ipa"],
                    "meaning": item["meaning"],
                    "example": item["example"],
                    "level": item["level"]
                }

    vocab_pool = list(vocab_pool_dict.values())
    if not vocab_pool:
        # Nếu hoàn toàn trống, trả về list rỗng
        return []

    # 2. Phân loại độ ưu tiên dựa trên AI Personalization
    now = datetime.utcnow()
    spaced_words = [
        m.word.lower() for m in db.query(VocabularyMemory).filter(
            VocabularyMemory.user_id == current_user.id,
            VocabularyMemory.next_review_at <= now
        ).all()
    ]
    wrong_words = [
        w.word.lower() for w in db.query(VocabularyWrongAnswer).filter(
            VocabularyWrongAnswer.user_id == current_user.id
        ).all()
    ]

    priority_items = []
    normal_items = []

    for item in vocab_pool:
        w_low = item["word"].lower()
        if w_low in spaced_words or w_low in wrong_words:
            priority_items.append(item)
        else:
            normal_items.append(item)

    random.shuffle(priority_items)
    random.shuffle(normal_items)

    # Chọn tối đa 10 từ (hoặc ít hơn nếu tổng số từ của topic nhỏ hơn 10)
    total_to_take = min(10, len(vocab_pool))
    selected_items = (priority_items + normal_items)[:total_to_take]

    # Để các đáp án sai phong phú, ta lấy pool làm các distractor.
    # Nếu pool quá bé, ta lấy thêm từ base_vocab của level làm distractor.
    distractor_pool = list(vocab_pool)
    if len(distractor_pool) < 5:
        level_fallback = selected_items[0]["level"] if selected_items else level
        for item in base_vocab.get(level_fallback, base_vocab["B1"]):
            distractor_pool.append(item)

    questions = []
    for item in selected_items:
        correct_meaning = item["meaning"]
        
        other_meanings_set = set(v["meaning"] for v in vocab_pool if v["meaning"] != correct_meaning)
        if len(other_meanings_set) < 3:
            for d in distractor_pool:
                if d["meaning"] != correct_meaning:
                    other_meanings_set.add(d["meaning"])
                    
        other_meanings = list(other_meanings_set)
        distractors = random.sample(other_meanings, min(3, len(other_meanings)))
        
        while len(distractors) < 3:
            distractors.append("Nghĩa khác ngẫu nhiên")
            
        options = [correct_meaning] + distractors
        random.shuffle(options)
        
        questions.append({
            "word": item["word"],
            "ipa": item["ipa"],
            "correct_answer": correct_meaning,
            "options": options,
            "example": item["example"],
            "explanation": f"Từ '{item['word']}' có nghĩa là '{correct_meaning}'."
        })
        
    return questions

@router.post("/vocabulary-game/submit-answer")
def submit_answer(
    data: AnswerSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Kiểm tra câu trả lời real-time.
    """
    from app.models.models import Vocabulary
    vocab_item = db.query(Vocabulary).filter(Vocabulary.word.ilike(data.word)).first()
    
    correct_meaning = None
    example = ""
    if vocab_item:
        correct_meaning = vocab_item.meaning
        example = vocab_item.example
    else:
        for lvl, words in base_vocab.items():
            for w in words:
                if w["word"].lower() == data.word.lower():
                    correct_meaning = w["meaning"]
                    example = w["example"]
                    break
            if correct_meaning:
                break
                
    if not correct_meaning:
        raise HTTPException(status_code=404, detail="Không tìm thấy từ vựng.")
        
    is_correct = data.user_answer.strip().lower() == correct_meaning.strip().lower()
    explanation = f"Từ '{data.word}' có nghĩa là '{correct_meaning}'."
    
    return {
        "is_correct": is_correct,
        "correct_answer": correct_meaning,
        "example": example,
        "explanation": explanation
    }

@router.post("/vocabulary-game/save-result")
def save_game_result(
    result: GameResultIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lưu kết quả game, cộng XP, cập nhật level, streak và chạy Spaced Repetition (SuperMemo SM-2)
    cho từng từ vựng trong lượt chơi của user.
    """
    from app.models.models import (
        VocabularyGame, VocabularyAttempt, UserXP, UserSkillLevel, 
        ActivityLog, Streak, VocabularyMemory, VocabularyWrongAnswer, 
        VocabularyMasteredWord, VocabularyAchievement, VocabularyXP,
        VocabularyReport, DailyVocabularyProgress, VocabularyLearningStatistics
    )
    from datetime import datetime, timedelta
    
    # 1. Tạo game record
    game = VocabularyGame(
        user_id=current_user.id,
        level=result.level,
        score=result.score,
        xp_earned=result.xp_earned,
        duration_seconds=result.duration_seconds
    )
    db.add(game)
    db.commit()
    db.refresh(game)
    
    now = datetime.utcnow()
    correct_count = 0
    max_combo = 0
    current_combo = 0
    
    # 2. Xử lý từng attempt & cập nhật Spaced Repetition
    for att in result.attempts:
        if att.is_correct:
            correct_count += 1
            current_combo += 1
            if current_combo > max_combo:
                max_combo = current_combo
        else:
            current_combo = 0

        attempt = VocabularyAttempt(
            game_id=game.id,
            word=att.word,
            user_answer=att.user_answer,
            is_correct=att.is_correct
        )
        db.add(attempt)

        mem = db.query(VocabularyMemory).filter(
            VocabularyMemory.user_id == current_user.id,
            VocabularyMemory.word.ilike(att.word)
        ).first()

        if not mem:
            mem = VocabularyMemory(
                user_id=current_user.id,
                word=att.word,
                ease_factor=2.5,
                interval_days=0,
                repetitions=0
            )
            db.add(mem)

        if att.is_correct:
            mem.repetitions += 1
            if mem.repetitions == 1:
                mem.interval_days = 1
            elif mem.repetitions == 2:
                mem.interval_days = 6
            else:
                mem.interval_days = round(mem.interval_days * mem.ease_factor)

            mem.ease_factor = min(3.0, max(1.3, mem.ease_factor + 0.1))
            
            wrong = db.query(VocabularyWrongAnswer).filter(
                VocabularyWrongAnswer.user_id == current_user.id,
                VocabularyWrongAnswer.word.ilike(att.word)
            ).first()
            if wrong:
                if wrong.error_count > 1:
                    wrong.error_count -= 1
                else:
                    db.delete(wrong)

            mastered = db.query(VocabularyMasteredWord).filter(
                VocabularyMasteredWord.user_id == current_user.id,
                VocabularyMasteredWord.word.ilike(att.word)
            ).first()
            if not mastered:
                mastered = VocabularyMasteredWord(
                    user_id=current_user.id,
                    word=att.word,
                    correct_streak=1
                )
                db.add(mastered)
            else:
                mastered.correct_streak += 1
        else:
            mem.repetitions = 0
            mem.interval_days = 1
            mem.ease_factor = max(1.3, mem.ease_factor - 0.2)

            wrong = db.query(VocabularyWrongAnswer).filter(
                VocabularyWrongAnswer.user_id == current_user.id,
                VocabularyWrongAnswer.word.ilike(att.word)
            ).first()
            if not wrong:
                wrong = VocabularyWrongAnswer(
                    user_id=current_user.id,
                    word=att.word,
                    error_count=1
                )
                db.add(wrong)
            else:
                wrong.error_count += 1

            mastered = db.query(VocabularyMasteredWord).filter(
                VocabularyMasteredWord.user_id == current_user.id,
                VocabularyMasteredWord.word.ilike(att.word)
            ).first()
            if mastered:
                db.delete(mastered)

        mem.last_reviewed_at = now
        mem.next_review_at = now + timedelta(days=mem.interval_days)

    # 3. GAMIFICATION ENGINE (XP & Combo)
    base_xp = result.xp_earned
    bonus_xp = 0
    unlocked_achievements = []

    # Perfect Game Bonus
    is_perfect = len(result.attempts) > 0 and correct_count == len(result.attempts)
    if is_perfect:
        bonus_xp += 50  # Perfect Game bonus +50 XP
        # Kiểm tra mở khóa thành tựu Perfect
        perf_ach = db.query(VocabularyAchievement).filter(
            VocabularyAchievement.user_id == current_user.id,
            VocabularyAchievement.achievement_code == "first_perfect"
        ).first()
        if not perf_ach:
            db_ach = VocabularyAchievement(
                user_id=current_user.id,
                achievement_code="first_perfect",
                title="Chiến thắng tuyệt đối 🏆",
                description="Đạt tỉ lệ chính xác 100% trong một bài luyện từ vựng."
            )
            db.add(db_ach)
            unlocked_achievements.append("Chiến thắng tuyệt đối 🏆")

    # Combo Bonus
    if max_combo >= 5:
        bonus_xp += 20
        if max_combo >= 10:
            bonus_xp += 30
            combo_ach = db.query(VocabularyAchievement).filter(
                VocabularyAchievement.user_id == current_user.id,
                VocabularyAchievement.achievement_code == "streak_10"
            ).first()
            if not combo_ach:
                db_ach = VocabularyAchievement(
                    user_id=current_user.id,
                    achievement_code="streak_10",
                    title="Chuỗi lửa đỏ 🔥",
                    description="Đạt combo 10 câu đúng liên tiếp trong một trò chơi từ vựng."
                )
                db.add(db_ach)
                unlocked_achievements.append("Chuỗi lửa đỏ 🔥")

    total_xp_gained = base_xp + bonus_xp

    # Cập nhật Vocabulary XP chuyên biệt
    v_xp = db.query(VocabularyXP).filter(VocabularyXP.user_id == current_user.id).first()
    if not v_xp:
        v_xp = VocabularyXP(user_id=current_user.id, xp=0, level=1, weekly_xp=0)
        db.add(v_xp)
    v_xp.xp += total_xp_gained
    v_xp.weekly_xp += total_xp_gained
    v_xp.level = (v_xp.xp // 150) + 1  # 150 XP mỗi level từ vựng

    # Thành tựu Bậc thầy từ vựng
    if v_xp.xp >= 500:
        master_ach = db.query(VocabularyAchievement).filter(
            VocabularyAchievement.user_id == current_user.id,
            VocabularyAchievement.achievement_code == "vocab_master"
        ).first()
        if not master_ach:
            db_ach = VocabularyAchievement(
                user_id=current_user.id,
                achievement_code="vocab_master",
                title="Bậc thầy từ vựng 🧠",
                description="Tích lũy đạt mốc 500 XP từ vựng chuyên sâu."
            )
            db.add(db_ach)
            unlocked_achievements.append("Bậc thầy từ vựng 🧠")
        
    # Cập nhật XP chung của User
    user_xp = db.query(UserXP).filter(UserXP.user_id == current_user.id).first()
    if not user_xp:
        user_xp = UserXP(user_id=current_user.id, total_xp=0, level=1)
        db.add(user_xp)
    user_xp.total_xp += total_xp_gained
    user_xp.level = (user_xp.total_xp // 100) + 1
    
    # 4. Tăng skill level vocabulary
    skill = db.query(UserSkillLevel).filter(UserSkillLevel.user_id == current_user.id).first()
    if skill:
        skill.vocabulary = min(100.0, skill.vocabulary + (result.score / 100.0) * 2.0)
        
    # 5. Lưu nhật ký hoạt động (ActivityLog)
    activity = ActivityLog(
        user_id=current_user.id,
        activity_type="vocabulary_game",
        xp_earned=total_xp_gained,
        duration_minutes=max(1, result.duration_seconds // 60)
    )
    db.add(activity)
    
    # 6. Cập nhật Streak
    streak = db.query(Streak).filter(Streak.user_id == current_user.id).first()
    if streak:
        today = datetime.utcnow().date()
        if streak.last_activity_date:
            last_date = streak.last_activity_date.date()
            delta = (today - last_date).days
            if delta == 1:
                streak.current_streak += 1
            elif delta > 1:
                streak.current_streak = 1
        else:
            streak.current_streak = 1
            
        if streak.current_streak > streak.longest_streak:
            streak.longest_streak = streak.current_streak
        streak.last_activity_date = datetime.utcnow()

    # 7. AI INSIGHTS & LEARNING REPORT SYSTEM
    # Gợi ý từ cần ôn tập (words user trả lời sai)
    wrong_attempts = [a.word for a in result.attempts if not a.is_correct]
    correct_attempts = [a.word for a in result.attempts if a.is_correct]

    # Đề xuất chủ đề tiếp theo thông minh
    suggested_topics = ["Du lịch", "AI", "Công nghệ"]
    for t in default_topics:
        if t["code"] != result.level:
            suggested_topics = [t["name"], "Công nghệ", "Công việc"]
            break

    # Phát hiện điểm yếu
    weak_points = []
    if wrong_attempts:
        weak_points.append(f"Chưa làm chủ tốt {len(wrong_attempts)} từ vựng của trình độ {result.level}.")
        weak_points.append("Gặp khó khăn trong việc nhận diện nghĩa từ ở tốc độ phản xạ nhanh.")
    else:
        weak_points.append("Không có điểm yếu nổi bật! Bạn đang học tập cực kỳ xuất sắc.")

    ai_insights = {
        "words_to_review": wrong_attempts,
        "words_mastered": correct_attempts,
        "weak_points": weak_points,
        "suggested_topics": suggested_topics
    }

    # Tạo VocabularyReport
    accuracy_rate = (correct_count / len(result.attempts) * 100.0) if len(result.attempts) > 0 else 100.0
    report = VocabularyReport(
        user_id=current_user.id,
        game_id=game.id,
        words_learned_count=len(result.attempts),
        correct_answers_count=correct_count,
        accuracy=accuracy_rate,
        max_combo=max_combo,
        xp_earned=total_xp_gained,
        ai_insights_json=ai_insights
    )
    db.add(report)

    # Cập nhật DailyVocabularyProgress
    daily_prog = db.query(DailyVocabularyProgress).filter(
        DailyVocabularyProgress.user_id == current_user.id,
        DailyVocabularyProgress.date >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    ).first()

    if not daily_prog:
        daily_prog = DailyVocabularyProgress(
            user_id=current_user.id,
            words_studied=len(result.attempts),
            minutes_spent=max(1, result.duration_seconds // 60),
            xp_earned=total_xp_gained
        )
        db.add(daily_prog)
    else:
        daily_prog.words_studied += len(result.attempts)
        daily_prog.minutes_spent += max(1, result.duration_seconds // 60)
        daily_prog.xp_earned += total_xp_gained

    # Cập nhật VocabularyLearningStatistics
    stats = db.query(VocabularyLearningStatistics).filter(VocabularyLearningStatistics.user_id == current_user.id).first()
    if not stats:
        stats = VocabularyLearningStatistics(
            user_id=current_user.id,
            total_words_studied=len(result.attempts),
            total_games_played=1,
            overall_accuracy=accuracy_rate
        )
        db.add(stats)
    else:
        stats.total_words_studied += len(result.attempts)
        stats.total_games_played += 1
        stats.overall_accuracy = (stats.overall_accuracy * (stats.total_games_played - 1) + accuracy_rate) / stats.total_games_played

    db.commit()
    
    return {
        "status": "success",
        "game_id": game.id,
        "xp_earned": result.xp_earned,
        "new_total_xp": user_xp.total_xp,
        "new_level": user_xp.level
    }

@router.get("/vocabulary/analytics")
def get_vocabulary_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    API Analytics: Trả về các chỉ số phân tích học từ vựng (độ chính xác, từ yếu, từ đã thuộc, tần suất ôn tập).
    """
    from app.models.models import VocabularyAttempt, VocabularyWrongAnswer, VocabularyMasteredWord, VocabularyMemory
    
    total_attempts = db.query(VocabularyAttempt).join(
        VocabularyAttempt.game
    ).filter(VocabularyAttempt.game.has(user_id=current_user.id)).count()
    
    correct_attempts = db.query(VocabularyAttempt).join(
        VocabularyAttempt.game
    ).filter(VocabularyAttempt.game.has(user_id=current_user.id), VocabularyAttempt.is_correct == True).count()
    
    accuracy = (correct_attempts / total_attempts * 100.0) if total_attempts > 0 else 100.0
    
    weak_records = db.query(VocabularyWrongAnswer).filter(
        VocabularyWrongAnswer.user_id == current_user.id
    ).order_by(VocabularyWrongAnswer.error_count.desc()).limit(10).all()
    
    weak_vocab = [
        {"word": w.word, "error_count": w.error_count, "last_attempt_at": w.last_attempt_at}
        for w in weak_records
    ]
    
    mastered_records = db.query(VocabularyMasteredWord).filter(
        VocabularyMasteredWord.user_id == current_user.id,
        VocabularyMasteredWord.correct_streak >= 5
    ).limit(10).all()
    
    mastered_vocab = [
        {"word": m.word, "correct_streak": m.correct_streak, "mastered_at": m.mastered_at}
        for m in mastered_records
    ]
    
    from datetime import datetime
    now = datetime.utcnow()
    
    overdue_count = db.query(VocabularyMemory).filter(
        VocabularyMemory.user_id == current_user.id,
        VocabularyMemory.next_review_at <= now
    ).count()
    
    upcoming_count = db.query(VocabularyMemory).filter(
        VocabularyMemory.user_id == current_user.id,
        VocabularyMemory.next_review_at > now
    ).count()
    
    return {
        "accuracy": round(accuracy, 1),
        "total_attempts": total_attempts,
        "correct_attempts": correct_attempts,
        "weak_vocabulary": weak_vocab,
        "mastered_vocabulary": mastered_vocab,
        "spaced_repetition": {
            "overdue_count": overdue_count,
            "upcoming_count": upcoming_count
        }
    }

# --- Vocabulary Sets & Topics API ---

# 15 chủ đề mặc định
default_topics = [
    {"name": "Du lịch", "code": "travel", "icon": "flight_takeoff_rounded", "description": "Giao tiếp sân bay, khách sạn, hỏi đường và trải nghiệm văn hóa."},
    {"name": "Công nghệ", "code": "tech", "icon": "devices_other_rounded", "description": "Thiết bị số, xu hướng công nghệ và cuộc sống hiện đại."},
    {"name": "Trí tuệ nhân tạo (AI)", "code": "ai", "icon": "psychology_rounded", "description": "Học máy, mạng nơ-ron, mô hình ngôn ngữ và ứng dụng AI."},
    {"name": "Marketing", "code": "marketing", "icon": "campaign_rounded", "description": "Quảng cáo, tiếp thị số, thương hiệu và nghiên cứu thị trường."},
    {"name": "Công việc", "code": "job", "icon": "work_outline_rounded", "description": "Môi trường công sở, viết CV và xin việc làm."},
    {"name": "Kinh doanh", "code": "business", "icon": "business_center_rounded", "description": "Đàm phán thương mại, hợp đồng và khởi nghiệp."},
    {"name": "Thể thao", "code": "sports", "icon": "sports_soccer_rounded", "description": "Các môn thể thao, rèn luyện thể chất và thế vận hội."},
    {"name": "Âm nhạc", "code": "music", "icon": "music_note_rounded", "description": "Thể loại nhạc, nhạc cụ và hòa nhạc."},
    {"name": "Sức khỏe", "code": "health", "icon": "medical_services_rounded", "description": "Dinh dưỡng, y tế, chăm sóc sức khỏe và lối sống lành mạnh."},
    {"name": "Nấu ăn", "code": "cooking", "icon": "restaurant_menu_rounded", "description": "Công thức nấu ăn, nguyên liệu và dụng cụ nhà bếp."},
    {"name": "Phần mềm", "code": "software", "icon": "code_rounded", "description": "Lập trình phần mềm, thuật toán và hệ điều hành."},
    {"name": "Phỏng vấn", "code": "interview", "icon": "record_voice_over_rounded", "description": "Kỹ năng trả lời phỏng vấn xin việc và đàm phán lương."},
    {"name": "Tài chính", "code": "finance", "icon": "account_balance_wallet_rounded", "description": "Đầu tư tài chính, ngân hàng và quản lý tài sản cá nhân."},
    {"name": "Thời trang", "code": "fashion", "icon": "checkroom_rounded", "description": "Trang phục, xu hướng thời trang và mua sắm."},
    {"name": "Mạng xã hội", "code": "social_media", "icon": "share_rounded", "description": "Tương tác số, nền tảng mạng xã hội và lan truyền thông tin."}
]

# Dữ liệu từ vựng mẫu cho các chủ đề theo level (A1, A2, B1, B2, C1)
topic_vocab_db = {
    "ai": {
        "A1": [
            {"word": "Robot", "ipa": "/ˈrəʊbɒt/", "meaning": "Người máy", "example": "The factory uses robots to build cars."},
            {"word": "Smart", "ipa": "/smɑːt/", "meaning": "Thông minh", "example": "He has a smart TV in his living room."},
            {"word": "Data", "ipa": "/ˈdeɪtə/", "meaning": "Dữ liệu", "example": "All customer data is encrypted."},
            {"word": "Code", "ipa": "/kəʊd/", "meaning": "Mã lập trình", "example": "I wrote a few lines of code today."},
            {"word": "App", "ipa": "/æp/", "meaning": "Ứng dụng", "example": "You can download the app for free."},
            {"word": "User", "ipa": "/ˈjuːzə(r)/", "meaning": "Người dùng", "example": "The system has active users globally."},
            {"word": "Web", "ipa": "/web/", "meaning": "Trang mạng, mạng lưới", "example": "We search the web for answers."},
            {"word": "Fast", "ipa": "/fɑːst/", "meaning": "Nhanh", "example": "This computer is extremely fast."},
            {"word": "Android", "ipa": "/ˈænˌdrɔɪd/", "meaning": "Người máy", "example": "The factory uses robots to build cars."},
            {"word": "Bright", "ipa": "/braɪt/", "meaning": "Thông minh", "example": "He has a smart TV in his living room."},
            {"word": "Information", "ipa": "/ˌɪnˌfɔrˈmeɪʃən/", "meaning": "Dữ liệu", "example": "All customer data is encrypted."},
            {"word": "Syntax", "ipa": "/ˈsɪnˌtæks/", "meaning": "Mã lập trình", "example": "I wrote a few lines of code today."},
            {"word": "Application", "ipa": "/ˌæpləˈkeɪʃən/", "meaning": "Ứng dụng", "example": "You can download the app for free."},
            {"word": "Operator", "ipa": "/ˈɑpərˌeɪtər/", "meaning": "Người dùng", "example": "The system has active users globally."},
            {"word": "Cyberspace", "ipa": "/ˈsaɪbərˌspeɪs/", "meaning": "Trang mạng, mạng lưới", "example": "We search the web for answers."},
            {"word": "Rapid", "ipa": "/ˈræpɪd/", "meaning": "Nhanh", "example": "This computer is extremely fast."},
        ],
        "A2": [
            {"word": "Computer", "ipa": "/kəmˈpjuːtə(r)/", "meaning": "Máy tính", "example": "I use my computer for coding."},
            {"word": "System", "ipa": "/ˈsɪstəm/", "meaning": "Hệ thống", "example": "The computer system needs an update."},
            {"word": "Network", "ipa": "/ˈnetwɜːk/", "meaning": "Mạng lưới, mạng kết nối", "example": "The social network connects millions of people."},
            {"word": "Program", "ipa": "/ˈprəʊɡræm/", "meaning": "Chương trình máy tính", "example": "This program helps detect grammar errors."},
            {"word": "Digital", "ipa": "/ˈdɪdʒɪtl/", "meaning": "Kỹ thuật số", "example": "We are living in a digital age."},
            {"word": "Device", "ipa": "/dɪˈvaɪs/", "meaning": "Thiết bị điện tử", "example": "Every device in the smart home is connected to the internet."},
            {"word": "Storage", "ipa": "/ˈstɔːrɪdʒ/", "meaning": "Bộ nhớ lưu trữ", "example": "This cloud storage is highly secure."},
            {"word": "Process", "ipa": "/ˈprəʊses/", "meaning": "Xử lý, quy trình", "example": "The CPU processes information quickly."},
            {"word": "Workstation", "ipa": "/ˈwərkˌsteɪʃən/", "meaning": "Máy tính", "example": "I use my computer for coding."},
            {"word": "Mechanism", "ipa": "/ˈmɛkəˌnɪzəm/", "meaning": "Hệ thống", "example": "The computer system needs an update."},
            {"word": "Grid", "ipa": "/ɡrɪd/", "meaning": "Lưới điện, mạng lưới ô vuông", "example": "The power grid supplies electricity to the entire region."},
            {"word": "Utility", "ipa": "/juˈtɪləti/", "meaning": "Chương trình máy tính", "example": "This program helps detect grammar errors."},
            {"word": "Cyber", "ipa": "/ˈsaɪbər/", "meaning": "Kỹ thuật số", "example": "We are living in a digital age."},
            {"word": "Gadget", "ipa": "/ˈgæʤət/", "meaning": "Thiết bị", "example": "Smartphones are essential mobile devices."},
            {"word": "Cache", "ipa": "/kæˈʃeɪ/", "meaning": "Bộ nhớ lưu trữ", "example": "This cloud storage is highly secure."},
            {"word": "Procedure", "ipa": "/prəˈsiʤər/", "meaning": "Xử lý, quy trình", "example": "The CPU processes information quickly."},
        ],
        "B1": [
            {"word": "Automation", "ipa": "/ˌɔːtəˈmeɪʃn/", "meaning": "Tự động hóa", "example": "Automation will change the future of work."},
            {"word": "Database", "ipa": "/ˈdeɪtəbeɪs/", "meaning": "Cơ sở dữ liệu", "example": "The customer records are in the database."},
            {"word": "Software", "ipa": "/ˈsɒftweə(r)/", "meaning": "Phần mềm", "example": "They design software for language learning."},
            {"word": "Interface", "ipa": "/ˈɪntəfeɪs/", "meaning": "Giao diện", "example": "The user interface is very clean."},
            {"word": "Assistant", "ipa": "/əˈsɪstənt/", "meaning": "Trợ lý", "example": "Siri is a virtual assistant on iOS."},
            {"word": "Analyze", "ipa": "/ˈænəlaɪz/", "meaning": "Phân tích", "example": "We use AI to analyze pronunciation."},
            {"word": "Prediction", "ipa": "/prɪˈdɪkʃn/", "meaning": "Sự dự đoán", "example": "AI makes a prediction based on trends."},
            {"word": "Mechanization", "ipa": "/ˌmɛkənəˈzeɪʃən/", "meaning": "Cơ giới hóa sản xuất", "example": "Mechanization replaced many manual labor jobs in factories."},
            {"word": "Repository", "ipa": "/riˈpɑzəˌtɔri/", "meaning": "Cơ sở dữ liệu", "example": "The customer records are in the database."},
            {"word": "Application", "ipa": "/ˌæpləˈkeɪʃən/", "meaning": "Phần mềm", "example": "They design software for language learning."},
            {"word": "Console", "ipa": "/ˈkɒnsoʊl/", "meaning": "Bảng điều khiển; máy chơi game", "example": "The game console was connected to the television."},
            {"word": "Aide", "ipa": "/eɪd/", "meaning": "Trợ lý, người giúp đỡ", "example": "The president's aide arranged the meeting schedule."},
            {"word": "Evaluate", "ipa": "/ɪˈvæljuˌeɪt/", "meaning": "Phân tích", "example": "We use AI to analyze pronunciation."},
            {"word": "Projection", "ipa": "/prɪˈdɪkʃn/", "meaning": "Sự dự đoán", "example": "AI makes a prediction based on trends."},
            {"word": "Formula", "ipa": "/ˈfɔrmjələ/", "meaning": "Thuật toán", "example": "The search engine uses a complex algorithm."},
        ],
        "B2": [
            {"word": "Neural network", "ipa": "/ˈnjʊərəl ˈnetwɜːk/", "meaning": "Mạng nơ-ron", "example": "AI is built on neural networks."},
            {"word": "Machine learning", "ipa": "/məˈʃiːn ˈlɜːnɪŋ/", "meaning": "Học máy", "example": "Machine learning is a subset of AI."},
            {"word": "Dataset", "ipa": "/ˈdeɪtəset/", "meaning": "Tập dữ liệu", "example": "The model was trained on a massive dataset."},
            {"word": "Optimization", "ipa": "/ˌɒptɪmaɪˈzeɪʃn/", "meaning": "Sự tối ưu hóa", "example": "We perform optimization on the search logic."},
            {"word": "Classification", "ipa": "/ˌklæsɪfɪˈkeɪʃn/", "meaning": "Sự phân loại", "example": "The algorithm handles image classification."},
            {"word": "Framework", "ipa": "/ˈfreɪmwɜːk/", "meaning": "Khung làm việc, thư viện mẫu", "example": "TensorFlow is a popular framework for deep learning."},
            {"word": "Generative", "ipa": "/ˈdʒenərətɪv/", "meaning": "Tạo sinh", "example": "ChatGPT is a popular generative AI application."},
            {"word": "Autonomous", "ipa": "/ɔːˈtɒnəməs/", "meaning": "Tự trị, tự lái", "example": "Autonomous vehicles are being tested on public roads."},
            {"word": "Deep network", "ipa": "/diːp ˈnɛtwɜːk/", "meaning": "Mạng nơ-ron sâu nhiều lớp", "example": "A deep network can learn complex patterns from large datasets."},
            {"word": "Pattern recognition", "ipa": "/ˈpætərn ˌrɛkɪgˈnɪʃən/", "meaning": "Học máy", "example": "Machine learning is a subset of AI."},
            {"word": "Corpus", "ipa": "/ˈkɔːpəs/", "meaning": "Kho ngữ liệu văn bản", "example": "Linguists use a corpus to study language patterns."},
            {"word": "Fine-tuning", "ipa": "/faɪn ˈtjuːnɪŋ/", "meaning": "Tinh chỉnh mô hình AI", "example": "Fine-tuning a pre-trained model improves its performance on specific tasks."},
            {"word": "Categorization", "ipa": "/ˌklæsɪfɪˈkeɪʃn/", "meaning": "Sự phân loại", "example": "The algorithm handles image classification."},
            {"word": "Infrastructure", "ipa": "/ˈɪnfrəˌstrʌktʃər/", "meaning": "Cơ sở hạ tầng kỹ thuật", "example": "The company invested in new IT infrastructure to support growth."},
            {"word": "Productive", "ipa": "/ˈdʒenərətɪv/", "meaning": "Tạo sinh", "example": "ChatGPT is a popular generative AI application."},
            {"word": "Independent", "ipa": "/ˌɪndɪˈpɛndənt/", "meaning": "Tự trị, tự lái", "example": "Autonomous vehicles are being tested on public roads."},
        ],
        "C1": [
            {"word": "Cognitive computing", "ipa": "/ˈkɒɡnətɪv kəmˈpjuːtɪŋ/", "meaning": "Điện toán nhận thức", "example": "Cognitive computing mimics human thought."},
            {"word": "Deep learning", "ipa": "/diːp ˈlɜːnɪŋ/", "meaning": "Học sâu", "example": "Deep learning achieves state of the art results."},
            {"word": "Reinforcement", "ipa": "/ˌriːɪnˈfɔːsmənt/", "meaning": "Sự tăng cường", "example": "AlphaGo uses reinforcement learning."},
            {"word": "Transformers", "ipa": "/trænsˈfɔːməs/", "meaning": "Mô hình Transformer", "example": "Modern LLMs are built on the Transformer architecture."},
            {"word": "Supervised", "ipa": "/ˈsuːpəvaɪzd/", "meaning": "Có giám sát", "example": "Supervised learning requires labeled training data."},
            {"word": "Natural Language", "ipa": "/ˈnætʃrəl ˈlæŋɡwɪdʒ/", "meaning": "Ngôn ngữ tự nhiên", "example": "Natural Language Processing makes chatbots smarter."},
            {"word": "Hyperparameters", "ipa": "/ˌhaɪpəpəˈræmɪtəz/", "meaning": "Siêu tham số", "example": "Tuning hyperparameters is essential for model training."},
            {"word": "Backpropagation", "ipa": "/ˌbækprɒpəˈɡeɪʃn/", "meaning": "Lan truyền ngược", "example": "Backpropagation is used to train deep neural networks."},
            {"word": "Artificial brain", "ipa": "/ɑːˈtɪfɪʃəl breɪn/", "meaning": "Não bộ nhân tạo, trí tuệ nhân tạo", "example": "Researchers are developing an artificial brain to simulate human cognition."},
            {"word": "Neural computing", "ipa": "/ˈnjʊərəl kəmˈpjuːtɪŋ/", "meaning": "Điện toán nơ-ron", "example": "Neural computing mimics the way the human brain processes information."},
            {"word": "Feedback loop", "ipa": "/ˈfiːdbæk luːp/", "meaning": "Vòng phản hồi học tăng cường", "example": "A feedback loop helps the AI model improve over time."},
            {"word": "Attention mechanism", "ipa": "/əˈtenʃən ˈmɛkənɪzəm/", "meaning": "Cơ chế chú ý trong AI", "example": "The attention mechanism allows the model to focus on relevant parts of the input."},
            {"word": "Guided learning", "ipa": "/ˈɡaɪdɪd ˈlɜːnɪŋ/", "meaning": "Học có giám sát, học theo hướng dẫn", "example": "Guided learning uses labeled data to train the AI model."},
            {"word": "Speech recognition", "ipa": "/spiːʧ ˌrɛkəɡˈnɪʃən/", "meaning": "Nhận dạng giọng nói", "example": "Speech recognition technology converts spoken words into text."},
            {"word": "Model parameters", "ipa": "/ˈmɒdəl pəˈræmɪtəz/", "meaning": "Tham số mô hình AI", "example": "Tuning model parameters is essential for better accuracy."},
            {"word": "Gradient descent", "ipa": "/ˈɡreɪdiənt dɪˈsɛnt/", "meaning": "Phương pháp hạ gradient (tối ưu hóa)", "example": "Gradient descent is used to minimize the loss function in training."},
        ],
    },
    "business": {
        "A1": [
            {"word": "company", "ipa": "/ˈkʌm.pə.ni/", "meaning": "công ty", "example": "She works for a large company in London."},
            {"word": "trade", "ipa": "/treɪd/", "meaning": "buôn bán, thương mại", "example": "International trade is important for the economy."},
            {"word": "bank", "ipa": "/bæŋk/", "meaning": "ngân hàng", "example": "I go to the bank to deposit my savings."},
            {"word": "plan", "ipa": "/plæn/", "meaning": "kế hoạch", "example": "We need a good plan before starting the project."},
            {"word": "goal", "ipa": "/ɡəʊl/", "meaning": "mục tiêu", "example": "Our goal is to increase sales this year."},
            {"word": "deal", "ipa": "/diːl/", "meaning": "thỏa thuận, giao dịch", "example": "They made a deal to supply goods at a lower price."},
            {"word": "profit", "ipa": "/ˈprɒf.ɪt/", "meaning": "lợi nhuận", "example": "The company made a large profit last year."},
            {"word": "cost", "ipa": "/kɒst/", "meaning": "chi phí", "example": "The cost of materials has increased recently."},
            {"word": "enterprise", "ipa": "/ˈɛntəpraɪz/", "meaning": "Doanh nghiệp lớn", "example": "She founded a successful enterprise in the tech sector."},
            {"word": "commerce", "ipa": "/ˈkɒmɜːs/", "meaning": "Thương mại, hoạt động mua bán", "example": "E-commerce has grown rapidly in recent years."},
            {"word": "depository", "ipa": "/dɪˈpɒzɪtri/", "meaning": "Kho lưu trữ, ngân hàng lưu ký", "example": "The securities depository holds shares on behalf of investors."},
            {"word": "blueprint", "ipa": "/ˈbluːˌprɪnt/", "meaning": "Bản vẽ kỹ thuật; kế hoạch chi tiết", "example": "The architect showed us the blueprint for the new building."},
            {"word": "target", "ipa": "/ˈtɑːɡɪt/", "meaning": "Mục tiêu cần đạt được", "example": "The sales team hit their monthly target."},
            {"word": "transaction", "ipa": "/trænˈzækʃən/", "meaning": "Giao dịch tài chính", "example": "The bank recorded every transaction in its system."},
            {"word": "gain", "ipa": "/geɪn/", "meaning": "lợi nhuận", "example": "The company made a large profit last year."},
            {"word": "expense", "ipa": "/ɪkˈspɛns/", "meaning": "chi phí", "example": "The cost of materials has increased recently."},
        ],
        "A2": [
            {"word": "contract", "ipa": "/ˈkɒn.trækt/", "meaning": "hợp đồng", "example": "Both parties signed the contract yesterday."},
            {"word": "partner", "ipa": "/ˈpɑːt.nər/", "meaning": "đối tác", "example": "We are looking for a reliable business partner."},
            {"word": "invest", "ipa": "/ɪnˈvest/", "meaning": "đầu tư", "example": "She decided to invest her savings in the stock market."},
            {"word": "budget", "ipa": "/ˈbʌdʒ.ɪt/", "meaning": "ngân sách", "example": "We need to stay within the project budget."},
            {"word": "income", "ipa": "/ˈɪn.kʌm/", "meaning": "thu nhập", "example": "His monthly income covers all his living expenses."},
            {"word": "tax", "ipa": "/tæks/", "meaning": "thuế", "example": "Everyone must pay tax on their earnings."},
            {"word": "import", "ipa": "/ˈɪm.pɔːt/", "meaning": "nhập khẩu", "example": "The country imports oil from the Middle East."},
            {"word": "export", "ipa": "/ˈek.spɔːt/", "meaning": "xuất khẩu", "example": "Vietnam exports a lot of rice to other countries."},
            {"word": "agreement", "ipa": "/əˈgrimənt/", "meaning": "hợp đồng", "example": "Both parties signed the contract yesterday."},
            {"word": "associate", "ipa": "/əˈsoʊʃiˌeɪt/", "meaning": "đối tác", "example": "We are looking for a reliable business partner."},
            {"word": "fund", "ipa": "/fənd/", "meaning": "đầu tư", "example": "She decided to invest her savings in the stock market."},
            {"word": "allowance", "ipa": "/əˈlaʊəns/", "meaning": "ngân sách", "example": "We need to stay within the project budget."},
            {"word": "revenue", "ipa": "/ˈrɛvəˌnu/", "meaning": "thu nhập", "example": "His monthly income covers all his living expenses."},
            {"word": "duty", "ipa": "/ˈduti/", "meaning": "thuế", "example": "Everyone must pay tax on their earnings."},
            {"word": "inbound", "ipa": "/ˌɪnˈbaʊnd/", "meaning": "nhập khẩu", "example": "The country imports oil from the Middle East."},
            {"word": "outbound", "ipa": "/ˈaʊtˌbaʊnd/", "meaning": "xuất khẩu", "example": "Vietnam exports a lot of rice to other countries."},
        ],
        "B1": [
            {"word": "entrepreneur", "ipa": "/ˌɒn.trə.prəˈnɜːr/", "meaning": "doanh nhân khởi nghiệp", "example": "She became a successful entrepreneur after launching her first startup."},
            {"word": "startup", "ipa": "/ˈstɑːt.ʌp/", "meaning": "công ty khởi nghiệp", "example": "His startup raised $2 million in seed funding this year."},
            {"word": "strategy", "ipa": "/ˈstræt.ə.dʒi/", "meaning": "chiến lược", "example": "The company needs a clear strategy to enter the Asian market."},
            {"word": "revenue", "ipa": "/ˈrev.ən.juː/", "meaning": "doanh thu", "example": "The company's annual revenue increased by 20% last quarter."},
            {"word": "stakeholder", "ipa": "/ˈsteɪk.həʊl.dər/", "meaning": "bên liên quan", "example": "All stakeholders must approve the new business plan before implementation."},
            {"word": "venture capital", "ipa": "/ˈven.tʃər ˈkæp.ɪ.təl/", "meaning": "vốn đầu tư mạo hiểm", "example": "The startup secured venture capital funding from a Silicon Valley firm."},
            {"word": "merger", "ipa": "/ˈmɜː.dʒər/", "meaning": "sự sáp nhập", "example": "The merger of the two banks created one of the largest financial institutions."},
            {"word": "franchise", "ipa": "/ˈfræn.tʃaɪz/", "meaning": "nhượng quyền thương mại", "example": "He opened a franchise restaurant in the city center."},
            {"word": "negotiation", "ipa": "/nɪˌɡəʊ.ʃiˈeɪ.ʃən/", "meaning": "đàm phán", "example": "The salary negotiation lasted two hours before both sides agreed."},
            {"word": "profit margin", "ipa": "/ˈprɒf.ɪt ˌmɑː.dʒɪn/", "meaning": "biên lợi nhuận", "example": "The company maintains a high profit margin by keeping costs low."},
            {"word": "market share", "ipa": "/ˈmɑː.kɪt ʃeər/", "meaning": "thị phần", "example": "Apple has a large market share in the premium smartphone segment."},
            {"word": "supply chain", "ipa": "/səˈplaɪ tʃeɪn/", "meaning": "chuỗi cung ứng", "example": "The pandemic disrupted global supply chains significantly."},
            {"word": "cash flow", "ipa": "/kæʃ fləʊ/", "meaning": "dòng tiền", "example": "Good cash flow management is essential for any small business."},
            {"word": "business model", "ipa": "/ˈbɪz.nɪs ˌmɒd.əl/", "meaning": "mô hình kinh doanh", "example": "Their subscription-based business model generates predictable monthly revenue."},
            {"word": "partnership", "ipa": "/ˈpɑːt.nər.ʃɪp/", "meaning": "quan hệ đối tác", "example": "The two companies formed a strategic partnership to expand globally."},
            {"word": "trademark", "ipa": "/ˈtreɪd.mɑːk/", "meaning": "nhãn hiệu thương mại", "example": "The company registered its logo as a trademark to prevent copying."},
            {"word": "patent", "ipa": "/ˈpeɪ.tənt/", "meaning": "bằng sáng chế", "example": "The inventor applied for a patent to protect her new technology."},
            {"word": "subsidiary", "ipa": "/səbˈsɪd.i.ər.i/", "meaning": "công ty con", "example": "The firm opened a subsidiary in Germany to expand into Europe."},
            {"word": "shareholder", "ipa": "/ˈʃeər.həʊl.dər/", "meaning": "cổ đông", "example": "Shareholders will vote on the new acquisition at the annual meeting."},
            {"word": "dividend", "ipa": "/ˈdɪv.ɪ.dend/", "meaning": "cổ tức", "example": "The company paid a generous dividend to its shareholders last year."},
            {"word": "audit", "ipa": "/ˈɔː.dɪt/", "meaning": "kiểm toán", "example": "An independent audit confirmed that the company's finances were in order."},
            {"word": "compliance", "ipa": "/kəmˈplaɪ.əns/", "meaning": "sự tuân thủ", "example": "All employees must complete compliance training to meet regulatory requirements."},
            {"word": "outsourcing", "ipa": "/ˈaʊt.sɔː.sɪŋ/", "meaning": "thuê ngoài", "example": "The company reduced costs by outsourcing customer service to a third party."},
            {"word": "overhead", "ipa": "/ˈəʊ.vər.hed/", "meaning": "chi phí cố định", "example": "They reduced overhead costs by moving to a smaller office space."},
            {"word": "scalable", "ipa": "/ˈskeɪ.lə.bəl/", "meaning": "có khả năng mở rộng", "example": "The platform is highly scalable and can handle millions of users."},
            {"word": "competitive advantage", "ipa": "/kəmˌpet.ɪ.tɪv ədˈvɑːn.tɪdʒ/", "meaning": "lợi thế cạnh tranh", "example": "Their proprietary technology gives them a competitive advantage in the market."},
            {"word": "market research", "ipa": "/ˈmɑː.kɪt rɪˈsɜːtʃ/", "meaning": "nghiên cứu thị trường", "example": "The team conducted extensive market research before launching the new product."},
            {"word": "brand awareness", "ipa": "/brænd əˈweər.nəs/", "meaning": "nhận thức thương hiệu", "example": "Social media campaigns can significantly increase brand awareness."},
            {"word": "customer retention", "ipa": "/ˈkʌs.tə.mər rɪˈten.ʃən/", "meaning": "giữ chân khách hàng", "example": "Good customer service is key to improving customer retention rates."},
            {"word": "product launch", "ipa": "/ˈprɒd.ʌkt lɔːntʃ/", "meaning": "ra mắt sản phẩm", "example": "The product launch attracted hundreds of journalists and industry experts."},
            {"word": "value proposition", "ipa": "/ˈvæl.juː ˌprɒp.əˈzɪʃ.ən/", "meaning": "đề xuất giá trị", "example": "A clear value proposition helps customers understand why to choose your product."},
            {"word": "break-even point", "ipa": "/breɪk ˈiː.vən pɔɪnt/", "meaning": "điểm hòa vốn", "example": "The startup expects to reach break-even point within the first two years."},
            {"word": "gross profit", "ipa": "/ɡrəʊs ˈprɒf.ɪt/", "meaning": "lợi nhuận gộp", "example": "The company reported strong gross profit despite rising material costs."},
            {"word": "return on investment", "ipa": "/rɪˈtɜːn ɒn ɪnˈvest.mənt/", "meaning": "tỷ suất hoàn vốn", "example": "The marketing campaign delivered an excellent return on investment."},
            {"word": "business ethics", "ipa": "/ˈbɪz.nɪs ˈeθ.ɪks/", "meaning": "đạo đức kinh doanh", "example": "Business ethics are increasingly important to consumers and investors."},
            {"word": "corporate governance", "ipa": "/ˈkɔː.pər.ɪt ˈɡʌv.ən.əns/", "meaning": "quản trị doanh nghiệp", "example": "Strong corporate governance protects shareholders' interests and ensures transparency."},
            {"word": "risk assessment", "ipa": "/rɪsk əˈses.mənt/", "meaning": "đánh giá rủi ro", "example": "The team completed a thorough risk assessment before entering the new market."},
            {"word": "performance indicator", "ipa": "/pəˈfɔː.məns ˈɪn.dɪ.keɪ.tər/", "meaning": "chỉ số hiệu suất", "example": "Key performance indicators help managers track progress towards business goals."},
            {"word": "annual report", "ipa": "/ˈæn.ju.əl rɪˈpɔːt/", "meaning": "báo cáo thường niên", "example": "The annual report showed significant growth in both revenue and net profit."},
            {"word": "board of directors", "ipa": "/bɔːd əv daɪˈrek.tərz/", "meaning": "hội đồng quản trị", "example": "The board of directors approved the new expansion strategy unanimously."},
            {"word": "joint venture", "ipa": "/dʒɔɪnt ˈven.tʃər/", "meaning": "liên doanh", "example": "The two companies formed a joint venture to develop new technology together."},
            {"word": "business development", "ipa": "/ˈbɪz.nɪs dɪˈvel.əp.mənt/", "meaning": "phát triển kinh doanh", "example": "The business development team identifies new partnership opportunities."},
            {"word": "cost reduction", "ipa": "/kɒst rɪˈdʌk.ʃən/", "meaning": "cắt giảm chi phí", "example": "Cost reduction measures helped the company become profitable."},
            {"word": "distribution channel", "ipa": "/ˌdɪs.trɪˈbjuː.ʃən ˈtʃæn.əl/", "meaning": "kênh phân phối", "example": "They expanded their distribution channel to reach rural markets."},
            {"word": "financial forecast", "ipa": "/faɪˈnæn.ʃəl ˈfɔː.kɑːst/", "meaning": "dự báo tài chính", "example": "The financial forecast predicts 15% revenue growth next year."},
            {"word": "competitive analysis", "ipa": "/kəmˈpet.ɪ.tɪv əˈnæl.ə.sɪs/", "meaning": "phân tích cạnh tranh", "example": "A competitive analysis helps businesses understand their position in the market."},
            {"word": "operational efficiency", "ipa": "/ˌɒp.ər.ˈeɪ.ʃən.əl ɪˈfɪʃ.ən.si/", "meaning": "hiệu quả vận hành", "example": "Automation improved operational efficiency across all departments."},
            {"word": "product development", "ipa": "/ˈprɒd.ʌkt dɪˈvel.əp.mənt/", "meaning": "phát triển sản phẩm", "example": "The product development cycle typically takes 12 to 18 months."},
            {"word": "market penetration", "ipa": "/ˈmɑː.kɪt ˌpen.ɪˈtreɪ.ʃən/", "meaning": "thâm nhập thị trường", "example": "Their aggressive pricing strategy helped achieve rapid market penetration."},
            {"word": "benchmark", "ipa": "/ˈbentʃ.mɑːk/", "meaning": "tiêu chuẩn so sánh", "example": "The sales team set a new benchmark for monthly performance targets."},
        ],
        "B2": [
            {"word": "acquisition", "ipa": "/ˌæk.wɪˈzɪʃ.ən/", "meaning": "thâu tóm, mua lại", "example": "The tech giant completed the acquisition of a smaller competitor last month."},
            {"word": "equity", "ipa": "/ˈek.wɪ.ti/", "meaning": "vốn cổ phần", "example": "Employees received equity in the startup as part of their compensation package."},
            {"word": "liability", "ipa": "/ˌlaɪ.əˈbɪl.ɪ.ti/", "meaning": "khoản nợ, trách nhiệm pháp lý", "example": "The company's total liabilities exceeded its assets, raising solvency concerns."},
            {"word": "diversification", "ipa": "/daɪˌvɜː.sɪ.fɪˈkeɪ.ʃən/", "meaning": "đa dạng hóa", "example": "Portfolio diversification helps reduce financial risk for investors."},
            {"word": "portfolio", "ipa": "/pɔːtˈfəʊ.li.əʊ/", "meaning": "danh mục đầu tư", "example": "The investment portfolio generated above-average returns this fiscal year."},
            {"word": "due diligence", "ipa": "/djuː ˈdɪl.ɪ.dʒəns/", "meaning": "thẩm định", "example": "Thorough due diligence was conducted before finalizing the merger agreement."},
            {"word": "leveraged buyout", "ipa": "/ˈlev.ər.ɪdʒd ˈbaɪ.aʊt/", "meaning": "mua lại bằng vốn vay", "example": "The leveraged buyout was funded primarily through high-yield debt securities."},
            {"word": "market capitalization", "ipa": "/ˈmɑː.kɪt ˌkæp.ɪ.t.əl.aɪˈzeɪ.ʃən/", "meaning": "vốn hóa thị trường", "example": "Apple's market capitalization exceeded two trillion dollars."},
            {"word": "derivatives", "ipa": "/dɪˈrɪv.ə.tɪvz/", "meaning": "chứng khoán phái sinh", "example": "Many banks use derivatives to hedge against interest rate fluctuations."},
            {"word": "hedge fund", "ipa": "/hedʒ fʌnd/", "meaning": "quỹ đầu cơ", "example": "The hedge fund outperformed major market indices last year."},
            {"word": "securitization", "ipa": "/sɪˌkjʊər.ɪ.taɪˈzeɪ.ʃən/", "meaning": "chứng khoán hóa", "example": "Securitization of mortgage loans was a major factor in the 2008 financial crisis."},
            {"word": "collateral", "ipa": "/kəˈlæt.ər.əl/", "meaning": "tài sản thế chấp", "example": "The bank required collateral before approving the large business loan."},
            {"word": "amortization", "ipa": "/əˌmɔː.tɪˈzeɪ.ʃən/", "meaning": "khấu hao dần", "example": "The amortization schedule showed how the loan would be paid off over 10 years."},
            {"word": "working capital", "ipa": "/ˈwɜː.kɪŋ ˈkæp.ɪ.təl/", "meaning": "vốn lưu động", "example": "Sufficient working capital is essential for maintaining daily business operations."},
            {"word": "accounts receivable", "ipa": "/əˈkaʊnts rɪˈsiː.və.bəl/", "meaning": "khoản phải thu", "example": "Reducing accounts receivable collection time improves cash flow significantly."},
            {"word": "accounts payable", "ipa": "/əˈkaʊnts ˈpeɪ.ə.bəl/", "meaning": "khoản phải trả", "example": "The company renegotiated its accounts payable terms to extend payment deadlines."},
            {"word": "net profit margin", "ipa": "/net ˈprɒf.ɪt ˌmɑː.dʒɪn/", "meaning": "biên lợi nhuận ròng", "example": "The firm achieved a net profit margin of 18% in the last fiscal year."},
            {"word": "return on equity", "ipa": "/rɪˈtɜːn ɒn ˈek.wɪ.ti/", "meaning": "tỷ suất sinh lời vốn cổ phần", "example": "A high return on equity indicates the company uses shareholders' money efficiently."},
            {"word": "earnings per share", "ipa": "/ˈɜː.nɪŋz pər ʃeər/", "meaning": "thu nhập trên mỗi cổ phần", "example": "The company's earnings per share grew significantly after the cost-cutting measures."},
            {"word": "price-to-earnings ratio", "ipa": "/praɪs tə ˈɜː.nɪŋz ˈreɪ.ʃi.əʊ/", "meaning": "tỷ số giá/thu nhập", "example": "A high price-to-earnings ratio may indicate that a stock is overvalued."},
            {"word": "goodwill", "ipa": "/ˈɡʊd.wɪl/", "meaning": "lợi thế thương mại", "example": "The company recorded significant goodwill after acquiring its competitor at a premium."},
            {"word": "intellectual property", "ipa": "/ˌɪn.tɪˌlek.tju.əl ˈprɒp.ə.ti/", "meaning": "sở hữu trí tuệ", "example": "Protecting intellectual property is crucial for technology companies."},
            {"word": "non-disclosure agreement", "ipa": "/nɒn dɪsˈkləʊ.ʒər əˈɡriː.mənt/", "meaning": "thỏa thuận bảo mật", "example": "All employees must sign a non-disclosure agreement before starting work."},
            {"word": "private equity", "ipa": "/ˈpraɪ.vɪt ˈek.wɪ.ti/", "meaning": "vốn cổ phần tư nhân", "example": "The private equity firm acquired a controlling stake in the retail chain."},
            {"word": "initial public offering", "ipa": "/ɪˈnɪʃ.əl ˈpʌb.lɪk ˈɒf.ər.ɪŋ/", "meaning": "phát hành cổ phiếu lần đầu", "example": "The company's initial public offering raised over $500 million for expansion."},
            {"word": "capital gains", "ipa": "/ˈkæp.ɪ.təl ɡeɪnz/", "meaning": "lãi vốn", "example": "Investors pay a lower tax rate on long-term capital gains."},
            {"word": "corporate restructuring", "ipa": "/ˈkɔː.pər.ɪt ˌriːˈstrʌk.tʃər.ɪŋ/", "meaning": "tái cơ cấu doanh nghiệp", "example": "Corporate restructuring resulted in significant cost savings but also layoffs."},
            {"word": "market volatility", "ipa": "/ˈmɑː.kɪt ˌvɒl.əˈtɪl.ɪ.ti/", "meaning": "biến động thị trường", "example": "High market volatility makes it difficult for investors to predict returns."},
            {"word": "foreign direct investment", "ipa": "/ˈfɒr.ɪn daɪˈrekt ɪnˈvest.mənt/", "meaning": "đầu tư trực tiếp nước ngoài", "example": "Foreign direct investment has played a key role in Vietnam's economic growth."},
            {"word": "financial leverage", "ipa": "/faɪˈnæn.ʃəl ˈliː.vər.ɪdʒ/", "meaning": "đòn bẩy tài chính", "example": "Using financial leverage can amplify both gains and losses for investors."},
            {"word": "cost of goods sold", "ipa": "/kɒst əv ɡʊdz səʊld/", "meaning": "giá vốn hàng bán", "example": "Reducing the cost of goods sold is key to improving profit margins."},
            {"word": "operating expenses", "ipa": "/ˈɒp.ər.eɪ.tɪŋ ɪkˈspens.ɪz/", "meaning": "chi phí hoạt động", "example": "The company cut operating expenses by reducing office space and staff."},
            {"word": "revenue stream", "ipa": "/ˈrev.ən.juː striːm/", "meaning": "luồng doanh thu", "example": "Diversifying revenue streams protects businesses from market downturns."},
            {"word": "debt-to-equity ratio", "ipa": "/det tə ˈek.wɪ.ti ˈreɪ.ʃi.əʊ/", "meaning": "tỷ số nợ/vốn cổ phần", "example": "A high debt-to-equity ratio indicates the company relies heavily on borrowed money."},
            {"word": "cash burn rate", "ipa": "/kæʃ bɜːn reɪt/", "meaning": "tốc độ đốt tiền mặt", "example": "The startup needed to control its cash burn rate to survive until the next funding round."},
            {"word": "fixed costs", "ipa": "/fɪkst kɒsts/", "meaning": "chi phí cố định", "example": "Fixed costs remain constant regardless of production volume or sales."},
            {"word": "variable costs", "ipa": "/ˈveər.i.ə.bəl kɒsts/", "meaning": "chi phí biến đổi", "example": "Variable costs increase as the company produces more units."},
            {"word": "economies of scale", "ipa": "/ɪˈkɒn.ə.miz əv skeɪl/", "meaning": "lợi thế kinh tế nhờ quy mô", "example": "Large manufacturers benefit from economies of scale that smaller firms cannot achieve."},
            {"word": "disruptive innovation", "ipa": "/dɪsˈrʌp.tɪv ˌɪn.əˈveɪ.ʃən/", "meaning": "đổi mới đột phá", "example": "Electric vehicles represent a disruptive innovation in the automotive industry."},
            {"word": "regulatory compliance", "ipa": "/ˌreɡ.jʊˈleɪ.tər.i kəmˈplaɪ.əns/", "meaning": "tuân thủ quy định", "example": "Companies in the financial sector must maintain strict regulatory compliance."},
            {"word": "supply chain management", "ipa": "/səˈplaɪ tʃeɪn ˈmæn.ɪdʒ.mənt/", "meaning": "quản lý chuỗi cung ứng", "example": "Effective supply chain management reduces costs and improves delivery times."},
            {"word": "business intelligence", "ipa": "/ˈbɪz.nɪs ɪnˈtel.ɪ.dʒəns/", "meaning": "thông tin kinh doanh", "example": "Business intelligence tools help executives make data-driven decisions."},
            {"word": "total cost of ownership", "ipa": "/ˈtəʊ.təl kɒst əv ˈəʊ.nər.ʃɪp/", "meaning": "tổng chi phí sở hữu", "example": "When comparing products, consider the total cost of ownership, not just the purchase price."},
            {"word": "brand licensing", "ipa": "/brænd ˈlaɪ.sən.sɪŋ/", "meaning": "cấp phép thương hiệu", "example": "Brand licensing allows other companies to use your brand in exchange for royalties."},
            {"word": "market disruption", "ipa": "/ˈmɑː.kɪt dɪsˈrʌp.ʃən/", "meaning": "gián đoạn thị trường", "example": "The rise of streaming services caused major market disruption to traditional broadcasting."},
            {"word": "cross-border transaction", "ipa": "/krɒs ˈbɔː.dər trænˈzæk.ʃən/", "meaning": "giao dịch xuyên biên giới", "example": "Cross-border transactions are subject to international tax and regulatory requirements."},
            {"word": "stakeholder management", "ipa": "/ˈsteɪk.həʊl.dər ˈmæn.ɪdʒ.mənt/", "meaning": "quản lý các bên liên quan", "example": "Effective stakeholder management is critical for large infrastructure projects."},
            {"word": "fiscal deficit", "ipa": "/ˈfɪs.kəl ˈdef.ɪ.sɪt/", "meaning": "thâm hụt tài chính", "example": "The country's growing fiscal deficit is a cause for concern among economists."},
            {"word": "financial modeling", "ipa": "/faɪˈnæn.ʃəl ˈmɒd.əl.ɪŋ/", "meaning": "mô hình tài chính", "example": "Financial modeling helps predict future revenue and expense scenarios."},
            {"word": "gross domestic product", "ipa": "/ɡrəʊs dəˈmes.tɪk ˈprɒd.ʌkt/", "meaning": "tổng sản phẩm nội địa", "example": "The country's gross domestic product grew by 6% last year."},
            {"word": "return on assets", "ipa": "/rɪˈtɜːn ɒn ˈæs.ets/", "meaning": "tỷ suất sinh lời trên tổng tài sản", "example": "A high return on assets indicates the company manages its resources efficiently."},
        ],
        "C1": [
            {"word": "conglomerate", "ipa": "/kənˈɡlɒm.ər.ɪt/", "meaning": "tập đoàn đa ngành", "example": "The Korean conglomerate operates in electronics, construction, and financial services."},
            {"word": "fiduciary", "ipa": "/fɪˈdjuː.ʃi.ər.i/", "meaning": "người/trách nhiệm ủy thác", "example": "Directors have a fiduciary duty to act in the best interests of shareholders."},
            {"word": "hostile takeover", "ipa": "/ˈhɒs.taɪl ˈteɪk.əʊ.vər/", "meaning": "thâu tóm thù địch", "example": "The board rejected the hostile takeover bid from the rival corporation."},
            {"word": "vertical integration", "ipa": "/ˈvɜː.tɪ.kəl ˌɪn.tɪˈɡreɪ.ʃən/", "meaning": "tích hợp theo chiều dọc", "example": "Through vertical integration, the company controls every stage of production."},
            {"word": "oligopoly", "ipa": "/ˌɒl.ɪˈɡɒp.ə.li/", "meaning": "thị trường độc quyền nhóm", "example": "The telecommunications industry in many countries is an oligopoly."},
            {"word": "synergy", "ipa": "/ˈsɪn.ə.dʒi/", "meaning": "hiệu ứng cộng lực", "example": "The merger created significant synergy, reducing costs and boosting revenue."},
            {"word": "golden parachute", "ipa": "/ˈɡəʊl.dən ˈpær.ə.ʃuːt/", "meaning": "khoản đền bù hậu hĩnh khi sa thải", "example": "The CEO negotiated a golden parachute worth $20 million upon departure."},
            {"word": "poison pill", "ipa": "/ˈpɔɪ.zən pɪl/", "meaning": "biện pháp phòng thủ chống tiếp quản", "example": "The board adopted a poison pill strategy to deter the hostile acquisition."},
            {"word": "white knight", "ipa": "/waɪt naɪt/", "meaning": "nhà đầu tư trắng (cứu vớt)", "example": "A white knight emerged to offer a more favorable acquisition deal."},
            {"word": "tax inversion", "ipa": "/tæks ɪnˈvɜː.ʃən/", "meaning": "đảo ngược thuế", "example": "The company underwent a tax inversion by reincorporating in a low-tax country."},
            {"word": "shadow banking", "ipa": "/ˈʃæd.əʊ ˈbæŋ.kɪŋ/", "meaning": "ngân hàng bóng tối", "example": "Shadow banking activities are less regulated than traditional banks and pose systemic risks."},
            {"word": "systemic risk", "ipa": "/sɪˈstem.ɪk rɪsk/", "meaning": "rủi ro hệ thống", "example": "The collapse of major banks poses systemic risk to the entire financial system."},
            {"word": "moral hazard", "ipa": "/ˈmɒr.əl ˈhæz.əd/", "meaning": "rủi ro đạo đức", "example": "Government bailouts can create moral hazard by encouraging reckless behavior."},
            {"word": "information asymmetry", "ipa": "/ˌɪn.fəˈmeɪ.ʃən eɪˈsɪm.ɪ.tri/", "meaning": "thông tin bất đối xứng", "example": "Information asymmetry between buyers and sellers can lead to market failures."},
            {"word": "principal-agent problem", "ipa": "/ˈprɪn.sɪ.pəl ˈeɪ.dʒənt ˈprɒb.ləm/", "meaning": "vấn đề người ủy thác-đại lý", "example": "The principal-agent problem arises when managers pursue their own interests rather than shareholders'."},
            {"word": "network effects", "ipa": "/ˈnet.wɜːk ɪˈfekts/", "meaning": "hiệu ứng mạng lưới", "example": "Facebook's dominance is partly due to powerful network effects that attract more users."},
            {"word": "platform economy", "ipa": "/ˈplæt.fɔːm ɪˈkɒn.ə.mi/", "meaning": "kinh tế nền tảng", "example": "The platform economy has disrupted traditional industries by connecting buyers and sellers directly."},
            {"word": "creative destruction", "ipa": "/kriˈeɪ.tɪv dɪˈstrʌk.ʃən/", "meaning": "sự phá hủy sáng tạo", "example": "Schumpeter's concept of creative destruction explains how innovation displaces old industries."},
            {"word": "game theory", "ipa": "/ɡeɪm ˈθɪə.ri/", "meaning": "lý thuyết trò chơi", "example": "Game theory is used to model strategic interactions between competing firms."},
            {"word": "Nash equilibrium", "ipa": "/næʃ ˌiː.kwɪˈlɪb.ri.əm/", "meaning": "cân bằng Nash", "example": "In a Nash equilibrium, no player can benefit by unilaterally changing their strategy."},
            {"word": "Pareto efficiency", "ipa": "/pəˌreɪ.toʊ ɪˈfɪʃ.ən.si/", "meaning": "hiệu quả Pareto", "example": "Pareto efficiency occurs when no one can be made better off without making someone else worse off."},
            {"word": "deadweight loss", "ipa": "/ˈded.weɪt lɒs/", "meaning": "tổn thất vô ích", "example": "Taxes and price controls can create deadweight loss by reducing market efficiency."},
            {"word": "price elasticity", "ipa": "/praɪs ˌɪ.læsˈtɪs.ɪ.ti/", "meaning": "độ co giãn của giá", "example": "The price elasticity of demand for gasoline is relatively low."},
            {"word": "first-mover advantage", "ipa": "/fɜːst ˈmuː.vər ədˈvɑːn.tɪdʒ/", "meaning": "lợi thế người tiên phong", "example": "Amazon capitalized on its first-mover advantage in online retail."},
            {"word": "blue ocean strategy", "ipa": "/bluː ˈəʊ.ʃən ˈstræt.ə.dʒi/", "meaning": "chiến lược đại dương xanh", "example": "The company pursued a blue ocean strategy by creating a market where no competition existed."},
            {"word": "regulatory arbitrage", "ipa": "/ˌreɡ.jʊˈleɪ.tər.i ˈɑː.bɪ.trɑːʒ/", "meaning": "lợi dụng sự chênh lệch quy định", "example": "Companies engage in regulatory arbitrage by operating in jurisdictions with looser regulations."},
            {"word": "transfer pricing", "ipa": "/ˈtræns.fər ˈpraɪ.sɪŋ/", "meaning": "định giá chuyển nhượng nội bộ", "example": "Transfer pricing strategies allow multinationals to shift profits to low-tax regions."},
            {"word": "bounded rationality", "ipa": "/ˈbaʊnd.ɪd ˌræʃ.əˈnæl.ɪ.ti/", "meaning": "tính hợp lý có giới hạn", "example": "Bounded rationality means decision-makers work with limited information and cognitive capacity."},
            {"word": "adverse selection", "ipa": "/ˈæd.vɜːs sɪˈlek.ʃən/", "meaning": "lựa chọn bất lợi", "example": "Adverse selection in health insurance occurs when sicker people are more likely to buy coverage."},
            {"word": "disintermediation", "ipa": "/ˌdɪs.ɪn.tə.miː.diˈeɪ.ʃən/", "meaning": "loại bỏ trung gian", "example": "The internet enabled disintermediation by allowing producers to sell directly to consumers."},
            {"word": "counterparty risk", "ipa": "/ˈkaʊn.tər.pɑː.ti rɪsk/", "meaning": "rủi ro đối tác", "example": "Counterparty risk refers to the possibility that the other party in a transaction may default."},
            {"word": "financial contagion", "ipa": "/faɪˈnæn.ʃəl kənˈteɪ.dʒən/", "meaning": "lan truyền khủng hoảng tài chính", "example": "Financial contagion spread the crisis from the US housing market to global economies."},
            {"word": "carry trade", "ipa": "/ˈkær.i treɪd/", "meaning": "giao dịch chênh lệch lãi suất", "example": "Investors use carry trades to profit from interest rate differentials between countries."},
            {"word": "algorithmic trading", "ipa": "/ˌæl.ɡəˈrɪð.mɪk ˈtreɪ.dɪŋ/", "meaning": "giao dịch thuật toán", "example": "Algorithmic trading now accounts for the majority of stock market transactions."},
            {"word": "quantitative easing", "ipa": "/ˈkwɒn.tɪ.teɪ.tɪv ˈiː.zɪŋ/", "meaning": "nới lỏng định lượng", "example": "Central banks used quantitative easing to stimulate economies during the financial crisis."},
            {"word": "yield curve", "ipa": "/jiːld kɜːv/", "meaning": "đường cong lợi suất", "example": "An inverted yield curve is often seen as a predictor of economic recession."},
            {"word": "credit default swap", "ipa": "/ˈkred.ɪt dɪˈfɔːlt swɒp/", "meaning": "hoán đổi rủi ro tín dụng", "example": "Credit default swaps were widely used to speculate on mortgage defaults."},
            {"word": "stagflation", "ipa": "/stæɡˈfleɪ.ʃən/", "meaning": "lạm phát đình trệ", "example": "The 1970s experienced stagflation, a rare combination of high inflation and economic stagnation."},
            {"word": "deleveraging", "ipa": "/diːˈlev.ər.ɪ.dʒɪŋ/", "meaning": "giảm đòn bẩy", "example": "Deleveraging after excessive borrowing can slow economic growth for years."},
            {"word": "macroprudential", "ipa": "/ˌmæk.rəʊ.pruːˈden.ʃəl/", "meaning": "vĩ mô thận trọng", "example": "Macroprudential policy aims to reduce systemic risk in the financial system."},
            {"word": "Basel accords", "ipa": "/ˈbɑː.zəl əˈkɔːdz/", "meaning": "Hiệp ước Basel", "example": "The Basel accords set international standards for bank capital requirements."},
            {"word": "sovereign wealth fund", "ipa": "/ˈsɒv.rɪn welθ fʌnd/", "meaning": "quỹ tài sản quốc gia", "example": "Norway's sovereign wealth fund is one of the largest in the world."},
            {"word": "regulatory capture", "ipa": "/ˌreɡ.jʊˈleɪ.tər.i ˈkæp.tʃər/", "meaning": "sự thâu tóm cơ quan quản lý", "example": "Regulatory capture occurs when regulators act in favor of the industries they oversee."},
            {"word": "dynamic pricing", "ipa": "/daɪˈnæm.ɪk ˈpraɪ.sɪŋ/", "meaning": "định giá linh hoạt", "example": "Airlines and ride-hailing apps use dynamic pricing to adjust fares based on demand."},
            {"word": "market microstructure", "ipa": "/ˈmɑː.kɪt ˈmaɪ.krəʊˌstrʌk.tʃər/", "meaning": "cấu trúc vi mô thị trường", "example": "Market microstructure examines how trading mechanisms affect price formation."},
            {"word": "reinsurance", "ipa": "/ˌriː.ɪnˈʃʊər.əns/", "meaning": "tái bảo hiểm", "example": "Insurance companies use reinsurance to reduce their exposure to large claims."},
            {"word": "collateralized debt obligation", "ipa": "/kəˌlæt.ər.ə.laɪzd det ˌɒb.lɪˈɡeɪ.ʃən/", "meaning": "nghĩa vụ nợ có tài sản đảm bảo", "example": "Collateralized debt obligations were at the center of the 2008 financial crisis."},
            {"word": "economies of scope", "ipa": "/ɪˈkɒn.ə.miz əv skəʊp/", "meaning": "lợi thế kinh tế theo phạm vi", "example": "The company benefits from economies of scope by sharing resources across its divisions."},
            {"word": "oligarchy", "ipa": "/ˈɒl.ɪ.ɡɑː.ki/", "meaning": "chế độ đầu sỏ", "example": "Critics argue that corporate oligarchy has too much influence over government policy."},
            {"word": "monopsony", "ipa": "/mɒˈnɒp.sə.ni/", "meaning": "thị trường độc quyền mua", "example": "A monopsony exists when there is only one buyer for a product or service."},
            {"word": "externality", "ipa": "/ˌek.stɜːˈnæl.ɪ.ti/", "meaning": "ngoại tác", "example": "Air pollution is a negative externality of industrial production."},
        ],
    },
    "cooking": {
        "A1": [
            {"word": "cook", "ipa": "/kʊk/", "meaning": "nấu ăn; đầu bếp", "example": "She cooks dinner for her family every evening."},
            {"word": "eat", "ipa": "/iːt/", "meaning": "ăn", "example": "We eat breakfast together every morning."},
            {"word": "drink", "ipa": "/drɪŋk/", "meaning": "uống", "example": "Remember to drink enough water every day."},
            {"word": "kitchen", "ipa": "/ˈkɪtʃ.ɪn/", "meaning": "nhà bếp", "example": "She spends a lot of time in the kitchen cooking."},
            {"word": "pot", "ipa": "/pɒt/", "meaning": "nồi", "example": "She boiled water in a large pot."},
            {"word": "pan", "ipa": "/pæn/", "meaning": "chảo", "example": "Fry the eggs in a hot pan with some butter."},
            {"word": "knife", "ipa": "/naɪf/", "meaning": "con dao", "example": "Use a sharp knife to cut the vegetables."},
            {"word": "spoon", "ipa": "/spuːn/", "meaning": "cái muỗng", "example": "Stir the soup with a wooden spoon."},
            {"word": "fork", "ipa": "/fɔːk/", "meaning": "cái nĩa", "example": "Use a fork to eat your pasta."},
            {"word": "plate", "ipa": "/pleɪt/", "meaning": "cái đĩa", "example": "Put the food on a clean plate before serving."},
            {"word": "bowl", "ipa": "/bəʊl/", "meaning": "cái bát/tô", "example": "She served the soup in a large bowl."},
            {"word": "cup", "ipa": "/kʌp/", "meaning": "cái ly/cốc", "example": "She poured tea into her favorite cup."},
            {"word": "hot", "ipa": "/hɒt/", "meaning": "nóng", "example": "Be careful — the soup is very hot."},
            {"word": "cold", "ipa": "/kəʊld/", "meaning": "lạnh", "example": "She keeps her drinks cold in the fridge."},
            {"word": "rice", "ipa": "/raɪs/", "meaning": "gạo/cơm", "example": "He eats rice with every meal."},
            {"word": "bread", "ipa": "/bred/", "meaning": "bánh mì", "example": "She bakes fresh bread every Sunday morning."},
            {"word": "egg", "ipa": "/ɛg/", "meaning": "trứng", "example": "Scrambled eggs are quick and easy to make."},
            {"word": "meat", "ipa": "/miːt/", "meaning": "thịt", "example": "He doesn't eat meat — he is vegetarian."},
            {"word": "fish", "ipa": "/fɪʃ/", "meaning": "cá", "example": "She loves to cook fresh fish with lemon."},
            {"word": "vegetable", "ipa": "/ˈvedʒ.tə.bəl/", "meaning": "rau củ", "example": "Add plenty of vegetables to your meals for good health."},
            {"word": "fruit", "ipa": "/fruːt/", "meaning": "trái cây", "example": "Fresh fruit is a healthy snack for children."},
            {"word": "sugar", "ipa": "/ˈʃʊɡ.ər/", "meaning": "đường", "example": "Add one spoon of sugar to the tea."},
            {"word": "salt", "ipa": "/sɔːlt/", "meaning": "muối", "example": "Don't add too much salt to the food."},
            {"word": "oil", "ipa": "/ɔɪl/", "meaning": "dầu ăn", "example": "Heat some oil in the pan before adding the onions."},
            {"word": "water", "ipa": "/ˈwɔː.tər/", "meaning": "nước", "example": "Boil water before adding the pasta."},
            {"word": "milk", "ipa": "/mɪlk/", "meaning": "sữa", "example": "She adds milk to her coffee every morning."},
            {"word": "butter", "ipa": "/ˈbʌt.ər/", "meaning": "bơ", "example": "Spread butter on the toast while it's still warm."},
            {"word": "cheese", "ipa": "/tʃiːz/", "meaning": "phô mai", "example": "She put cheese on top of the pizza."},
            {"word": "onion", "ipa": "/ˈʌn.jən/", "meaning": "hành tây", "example": "Chop the onion finely before adding it to the sauce."},
            {"word": "garlic", "ipa": "/ˈɡɑː.lɪk/", "meaning": "tỏi", "example": "Add two cloves of garlic to give the dish more flavor."},
            {"word": "boil", "ipa": "/bɔɪl/", "meaning": "đun sôi", "example": "Boil the potatoes for about 20 minutes."},
            {"word": "fry", "ipa": "/fraɪ/", "meaning": "chiên rán", "example": "Fry the chicken until it's golden brown on both sides."},
            {"word": "bake", "ipa": "/beɪk/", "meaning": "nướng (lò)", "example": "She loves to bake cakes on weekends."},
            {"word": "cut", "ipa": "/kʌt/", "meaning": "cắt", "example": "Cut the carrots into small pieces."},
            {"word": "mix", "ipa": "/mɪks/", "meaning": "trộn", "example": "Mix the flour and eggs together in a bowl."},
            {"word": "stir", "ipa": "/stɜːr/", "meaning": "khuấy", "example": "Stir the sauce constantly to prevent it from burning."},
            {"word": "smell", "ipa": "/smel/", "meaning": "mùi hương", "example": "The bread smells wonderful when it comes out of the oven."},
            {"word": "taste", "ipa": "/teɪst/", "meaning": "nếm; hương vị", "example": "Taste the soup and add more salt if needed."},
            {"word": "recipe", "ipa": "/ˈres.ɪ.pi/", "meaning": "công thức nấu ăn", "example": "She found a great recipe for chocolate cake online."},
            {"word": "ingredient", "ipa": "/ɪnˈɡriː.di.ənt/", "meaning": "nguyên liệu", "example": "Make sure you have all the ingredients before you start cooking."},
            {"word": "meal", "ipa": "/miːl/", "meaning": "bữa ăn", "example": "Dinner is my favorite meal of the day."},
            {"word": "oven", "ipa": "/ˈʌv.ən/", "meaning": "lò nướng", "example": "Preheat the oven to 180 degrees before baking."},
            {"word": "fridge", "ipa": "/frɪdʒ/", "meaning": "tủ lạnh", "example": "Keep the vegetables in the fridge to stay fresh."},
            {"word": "spicy", "ipa": "/ˈspaɪ.si/", "meaning": "cay", "example": "This curry is very spicy — be careful!"},
            {"word": "sweet", "ipa": "/swiːt/", "meaning": "ngọt", "example": "She loves sweet desserts like chocolate cake."},
            {"word": "sour", "ipa": "/ˈsaʊ.ər/", "meaning": "chua", "example": "The lemon juice made the sauce taste sour."},
            {"word": "bitter", "ipa": "/ˈbɪt.ər/", "meaning": "đắng", "example": "Dark chocolate can taste bitter if you're not used to it."},
            {"word": "salty", "ipa": "/ˈsɔːl.ti/", "meaning": "mặn", "example": "The chips were too salty for her taste."},
            {"word": "dinner", "ipa": "/ˈdɪn.ər/", "meaning": "bữa tối", "example": "We had a delicious dinner at the new restaurant."},
            {"word": "breakfast", "ipa": "/ˈbrek.fəst/", "meaning": "bữa sáng", "example": "A good breakfast gives you energy for the whole day."},
        ],
        "A2": [
            {"word": "recipe", "ipa": "/ˈres.ɪ.pi/", "meaning": "công thức nấu ăn", "example": "Follow the recipe carefully to get the best results."},
            {"word": "chop", "ipa": "/ʧɑp/", "meaning": "chặt, thái (thực phẩm)", "example": "Chop the onions into small pieces before adding them to the pan."},
            {"word": "roast", "ipa": "/rəʊst/", "meaning": "quay, nướng (thịt)", "example": "She roasted a whole chicken in the oven for Sunday lunch."},
            {"word": "steam", "ipa": "/stiːm/", "meaning": "hấp", "example": "Steam the vegetables to preserve their nutrients."},
            {"word": "grill", "ipa": "/ɡrɪl/", "meaning": "nướng vỉ", "example": "Grill the fish on a high heat for four minutes each side."},
            {"word": "simmer", "ipa": "/ˈsɪm.ər/", "meaning": "đun lửa nhỏ", "example": "Let the soup simmer for 30 minutes to develop the flavors."},
            {"word": "season", "ipa": "/ˈsiː.zən/", "meaning": "nêm gia vị", "example": "Season the chicken with salt, pepper, and herbs."},
            {"word": "marinate", "ipa": "/ˈmær.ɪ.neɪt/", "meaning": "ướp (thực phẩm)", "example": "Marinate the meat overnight for the best flavor."},
            {"word": "peel", "ipa": "/piːl/", "meaning": "gọt vỏ", "example": "Peel the potatoes before boiling them."},
            {"word": "slice", "ipa": "/slaɪs/", "meaning": "cắt lát", "example": "Slice the bread thinly for the sandwiches."},
            {"word": "dice", "ipa": "/daɪs/", "meaning": "cắt hạt lựu", "example": "Dice the tomatoes and add them to the salad."},
            {"word": "mince", "ipa": "/mɪns/", "meaning": "băm nhỏ", "example": "Mince the garlic before adding it to the sauce."},
            {"word": "drain", "ipa": "/dreɪn/", "meaning": "để ráo nước", "example": "Drain the pasta and rinse it with cold water."},
            {"word": "whisk", "ipa": "/wɪsk/", "meaning": "đánh (trứng)", "example": "Whisk the eggs until they are light and fluffy."},
            {"word": "knead", "ipa": "/niːd/", "meaning": "nhào bột", "example": "Knead the dough for ten minutes until it's smooth."},
            {"word": "portion", "ipa": "/ˈpɔː.ʃən/", "meaning": "khẩu phần ăn", "example": "The restaurant serves large portions at a reasonable price."},
            {"word": "serving", "ipa": "/ˈsɜː.vɪŋ/", "meaning": "suất ăn", "example": "This recipe makes four servings."},
            {"word": "flavor", "ipa": "/ˈfleɪ.vər/", "meaning": "hương vị", "example": "The garlic adds a wonderful flavor to the dish."},
            {"word": "texture", "ipa": "/ˈteks.tʃər/", "meaning": "kết cấu (món ăn)", "example": "The sauce has a smooth, creamy texture."},
            {"word": "aroma", "ipa": "/əˈrəʊ.mə/", "meaning": "hương thơm", "example": "The aroma of freshly baked bread filled the kitchen."},
            {"word": "herb", "ipa": "/ərb/", "meaning": "rau thơm/thảo mộc", "example": "Add fresh herbs like basil and thyme to the sauce."},
            {"word": "spice", "ipa": "/spaɪs/", "meaning": "gia vị (cay)", "example": "This dish is packed with exotic spices from Asia."},
            {"word": "sauce", "ipa": "/sɔːs/", "meaning": "sốt", "example": "Pour the tomato sauce over the pasta."},
            {"word": "dough", "ipa": "/dəʊ/", "meaning": "bột nhào", "example": "Roll out the dough to make the pizza base."},
            {"word": "batter", "ipa": "/ˈbæt.ər/", "meaning": "bột chiên pha lỏng", "example": "Dip the fish in batter before frying it."},
            {"word": "broth", "ipa": "/brɒθ/", "meaning": "nước dùng", "example": "She made a rich chicken broth for the soup."},
            {"word": "stock", "ipa": "/stɒk/", "meaning": "nước dùng cô (dùng nấu)", "example": "Use vegetable stock to give the soup more flavor."},
            {"word": "condiment", "ipa": "/ˈkɒn.dɪ.mənt/", "meaning": "gia vị ăn kèm", "example": "Ketchup and mustard are popular condiments for burgers."},
            {"word": "starch", "ipa": "/stɑːtʃ/", "meaning": "tinh bột", "example": "Rice, pasta, and potatoes are all starchy foods."},
            {"word": "leftovers", "ipa": "/ˈleft.əʊ.vərz/", "meaning": "thức ăn thừa", "example": "She put the leftovers in the fridge for tomorrow's lunch."},
            {"word": "portion control", "ipa": "/ˈpɔː.ʃən kənˈtrəʊl/", "meaning": "kiểm soát khẩu phần", "example": "Portion control helps manage calorie intake."},
            {"word": "cookware", "ipa": "/ˈkʊk.weər/", "meaning": "dụng cụ nấu ăn", "example": "Invest in good cookware to make cooking easier."},
            {"word": "cutting board", "ipa": "/ˈkʌt.ɪŋ bɔːd/", "meaning": "thớt", "example": "Use a separate cutting board for meat and vegetables."},
            {"word": "colander", "ipa": "/ˈkɒl.ən.dər/", "meaning": "rổ lọc nước", "example": "Pour the boiled pasta into a colander to drain it."},
            {"word": "grater", "ipa": "/ˈɡreɪ.tər/", "meaning": "dụng cụ bào", "example": "Use a grater to grate the cheese finely."},
            {"word": "spatula", "ipa": "/ˈspætʃ.ʊ.lə/", "meaning": "cái xẻng lật (bếp)", "example": "Use a spatula to flip the pancakes without breaking them."},
            {"word": "ladle", "ipa": "/ˈleɪ.dəl/", "meaning": "cái muôi múc canh", "example": "Use a ladle to serve the soup into bowls."},
            {"word": "tongs", "ipa": "/tɒŋz/", "meaning": "kẹp gắp thức ăn", "example": "Use tongs to turn the steaks on the grill."},
            {"word": "microwave", "ipa": "/ˈmaɪ.krə.weɪv/", "meaning": "lò vi sóng", "example": "Reheat the leftovers in the microwave for two minutes."},
            {"word": "blender", "ipa": "/ˈblen.dər/", "meaning": "máy xay sinh tố", "example": "Blend the fruit and yogurt together in a blender."},
            {"word": "food processor", "ipa": "/fuːd ˈprəʊ.ses.ər/", "meaning": "máy chế biến thực phẩm", "example": "Use the food processor to chop the onions quickly."},
            {"word": "pressure cooker", "ipa": "/ˈpreʃ.ər ˌkʊk.ər/", "meaning": "nồi áp suất", "example": "A pressure cooker reduces cooking time significantly."},
            {"word": "slow cooker", "ipa": "/ˈsləʊ ˌkʊk.ər/", "meaning": "nồi nấu chậm", "example": "She prepares the stew in a slow cooker before going to work."},
            {"word": "wok", "ipa": "/wɒk/", "meaning": "chảo wok", "example": "Stir-fry the vegetables quickly in a hot wok."},
            {"word": "apron", "ipa": "/ˈeɪ.prən/", "meaning": "tạp dề", "example": "Always wear an apron to protect your clothes when cooking."},
            {"word": "raw", "ipa": "/rɑ/", "meaning": "sống, chưa nấu", "example": "Never eat raw chicken as it can cause food poisoning."},
            {"word": "well-done", "ipa": "/ˌwel ˈdʌn/", "meaning": "chín kỹ (thịt)", "example": "He prefers his steak well-done with no pink in the middle."},
            {"word": "medium-rare", "ipa": "/ˌmiː.di.əm ˈreər/", "meaning": "tái vừa (thịt)", "example": "She ordered her steak medium-rare with fries on the side."},
            {"word": "garnish", "ipa": "/ˈɡɑː.nɪʃ/", "meaning": "trang trí món ăn", "example": "Garnish the dish with fresh parsley before serving."},
            {"word": "plating", "ipa": "/ˈpleɪ.tɪŋ/", "meaning": "trình bày món ăn", "example": "Good plating makes the dish look appealing and professional."},
        ],
        "B1": [
            {"word": "sous vide", "ipa": "/suː ˈviːd/", "meaning": "kỹ thuật nấu chân không nhiệt độ thấp", "example": "Sous vide cooking produces perfectly cooked meat by controlling temperature precisely."},
            {"word": "blanch", "ipa": "/blɑːntʃ/", "meaning": "chần nhanh qua nước sôi", "example": "Blanch the spinach for 30 seconds and then transfer to ice water."},
            {"word": "deglaze", "ipa": "/diːˈɡleɪz/", "meaning": "hòa tan cặn nồi bằng chất lỏng", "example": "Deglaze the pan with white wine to release all the caramelized bits."},
            {"word": "render", "ipa": "/ˈren.dər/", "meaning": "rán chảy mỡ", "example": "Render the bacon fat before adding the vegetables to the pan."},
            {"word": "emulsify", "ipa": "/ɪˈmʌl.sɪ.faɪ/", "meaning": "nhũ hóa", "example": "Whisk the oil and vinegar together to emulsify the dressing."},
            {"word": "reduction", "ipa": "/rɪˈdʌk.ʃən/", "meaning": "nước sốt cô đặc", "example": "Make a balsamic reduction to drizzle over the steak."},
            {"word": "caramelize", "ipa": "/ˈkær.ə.mə.laɪz/", "meaning": "làm vàng/caramel", "example": "Caramelize the onions slowly over low heat for extra sweetness."},
            {"word": "sauté", "ipa": "/ˈsɒt.eɪ/", "meaning": "xào nhẹ trong bơ/dầu", "example": "Sauté the mushrooms in butter until they are golden brown."},
            {"word": "braise", "ipa": "/breɪz/", "meaning": "hầm (bít tết...)", "example": "Braise the short ribs in red wine for three hours."},
            {"word": "poach", "ipa": "/pəʊtʃ/", "meaning": "luộc nhẹ trong nước/sữa", "example": "Poach the eggs gently in simmering water."},
            {"word": "cure", "ipa": "/kjʊər/", "meaning": "ướp muối bảo quản", "example": "Salmon is cured with salt and sugar to make gravlax."},
            {"word": "smoke", "ipa": "/sməʊk/", "meaning": "hun khói", "example": "They smoke the ribs over hickory wood for six hours."},
            {"word": "ferment", "ipa": "/fɜːˈment/", "meaning": "lên men", "example": "Kimchi is made by fermenting vegetables with spices."},
            {"word": "pickle", "ipa": "/ˈpɪk.əl/", "meaning": "muối chua", "example": "She pickled cucumbers in a mixture of vinegar and spices."},
            {"word": "infuse", "ipa": "/ɪnˈfjuːz/", "meaning": "hãm/ngâm để lấy hương vị", "example": "Infuse the milk with vanilla beans before making the custard."},
            {"word": "tempering", "ipa": "/ˈtem.pər.ɪŋ/", "meaning": "điều hòa nhiệt độ (chocolate)", "example": "Tempering chocolate gives it a glossy finish and a satisfying snap."},
            {"word": "mise en place", "ipa": "/ˌmiːz ɒn ˈplɑːs/", "meaning": "chuẩn bị nguyên liệu trước khi nấu", "example": "Professional chefs always practice mise en place for efficiency."},
            {"word": "julienne", "ipa": "/ˌdʒuː.liˈen/", "meaning": "thái chỉ mỏng", "example": "Julienne the carrots into thin matchstick-sized strips."},
            {"word": "brunoise", "ipa": "/ˈbruː.nwɑːz/", "meaning": "thái hạt lựu cực nhỏ", "example": "A brunoise cut produces tiny 1-2mm cubes for garnishes."},
            {"word": "chiffonade", "ipa": "/ˌʃɪf.əˈnɑːd/", "meaning": "thái chỉ lá rau thơm", "example": "Roll the basil leaves and cut into a fine chiffonade."},
            {"word": "macerate", "ipa": "/ˈmæs.ə.reɪt/", "meaning": "ngâm mềm (trái cây) trong đường/rượu", "example": "Macerate the strawberries in sugar and balsamic for one hour."},
            {"word": "fold", "ipa": "/fəʊld/", "meaning": "trộn nhẹ nhàng (không phá vỡ bọt khí)", "example": "Carefully fold the egg whites into the batter."},
            {"word": "proof", "ipa": "/pruːf/", "meaning": "ủ bột lên men", "example": "Let the dough proof for one hour before baking."},
            {"word": "score", "ipa": "/skɔːr/", "meaning": "khía rạch (thịt/cá)", "example": "Score the fish skin to prevent it from curling during cooking."},
            {"word": "truss", "ipa": "/trʌs/", "meaning": "buộc (thịt gà) trước khi quay", "example": "Truss the chicken before roasting to ensure even cooking."},
            {"word": "baste", "ipa": "/beɪst/", "meaning": "tưới nước thịt lên khi nướng", "example": "Baste the turkey with its own juices every 30 minutes."},
            {"word": "resting meat", "ipa": "/ˈres.tɪŋ miːt/", "meaning": "để thịt nghỉ sau khi nấu", "example": "Always rest the meat for 10 minutes after cooking for juicier results."},
            {"word": "food safety", "ipa": "/fuːd ˈseɪf.ti/", "meaning": "an toàn thực phẩm", "example": "Food safety guidelines prevent contamination and foodborne illness."},
            {"word": "cross-contamination", "ipa": "/ˈkrɒs kənˌtæm.ɪˈneɪ.ʃən/", "meaning": "nhiễm chéo vi khuẩn", "example": "Use separate boards to avoid cross-contamination between meat and produce."},
            {"word": "food allergy", "ipa": "/fuːd ˈæl.ə.dʒi/", "meaning": "dị ứng thực phẩm", "example": "The chef was careful to avoid nut contamination for guests with a food allergy."},
            {"word": "dietary restriction", "ipa": "/ˈdaɪ.ɪ.tər.i rɪˈstrɪk.ʃən/", "meaning": "hạn chế ăn uống", "example": "Always ask guests about dietary restrictions before planning the menu."},
            {"word": "umami", "ipa": "/uːˈmɑː.mi/", "meaning": "vị umami (vị ngon đặc biệt)", "example": "Parmesan cheese and miso add deep umami flavor to dishes."},
            {"word": "maillard reaction", "ipa": "/maɪˈjɑːr riˈæk.ʃən/", "meaning": "phản ứng Maillard (tạo vỏ vàng)", "example": "The Maillard reaction gives bread and meat their characteristic brown crust."},
            {"word": "pastry", "ipa": "/ˈpeɪ.stri/", "meaning": "bánh ngọt làm từ bột", "example": "She trained as a pastry chef and specializes in French desserts."},
            {"word": "gluten", "ipa": "/ˈɡluː.tən/", "meaning": "gluten (protein trong bột mì)", "example": "Gluten gives bread its chewy, elastic texture."},
            {"word": "yeast", "ipa": "/jiːst/", "meaning": "men nở (làm bánh mì)", "example": "Add active yeast to the warm water to activate it before using."},
            {"word": "baking powder", "ipa": "/ˈbeɪ.kɪŋ ˌpaʊ.dər/", "meaning": "bột nở", "example": "Add baking powder to the batter to make the cake rise."},
            {"word": "gelatin", "ipa": "/ˈdʒel.ə.tɪn/", "meaning": "gelatin", "example": "Dissolve gelatin in warm water before adding it to the mousse."},
            {"word": "vinaigrette", "ipa": "/ˌvɪn.ɪˈɡret/", "meaning": "sốt dấm dầu", "example": "Whisk together oil, vinegar, and mustard to make a simple vinaigrette."},
            {"word": "gastrique", "ipa": "/ɡæˈstriːk/", "meaning": "sốt caramel chua ngọt", "example": "A gastrique is a sweet and sour reduction used to finish savory dishes."},
            {"word": "coulis", "ipa": "/ˈkuː.li/", "meaning": "sốt trái cây xay", "example": "Serve the chocolate cake with a raspberry coulis."},
            {"word": "mousse", "ipa": "/muːs/", "meaning": "kem bọt (bánh mousse)", "example": "She made a light chocolate mousse for the dinner party."},
            {"word": "soufflé", "ipa": "/ˈsuː.fleɪ/", "meaning": "bánh soufflé (phồng)", "example": "A cheese soufflé must be served immediately or it will collapse."},
            {"word": "crème brûlée", "ipa": "/ˌkrem bruːˈleɪ/", "meaning": "bánh kem brûlée", "example": "She torched the sugar on the crème brûlée to create the caramel topping."},
            {"word": "terrine", "ipa": "/təˈriːn/", "meaning": "pâté khuôn terrine", "example": "The chef prepared a country-style terrine with pork and herbs."},
            {"word": "pâté", "ipa": "/ˈpæt.eɪ/", "meaning": "pâté (gan thịt xay nhuyễn)", "example": "The mushroom pâté was served on toasted bread as an appetizer."},
            {"word": "tapenade", "ipa": "/ˈtæp.ɪ.neɪd/", "meaning": "sốt ô-liu đen", "example": "Spread tapenade on the bread as a simple but flavorful appetizer."},
            {"word": "mise en scène (plating)", "ipa": "/ˌmiːz ɒn ˈsen/", "meaning": "nghệ thuật trình bày đĩa", "example": "The chef's artistic plating turned the dish into a visual masterpiece."},
            {"word": "pairing", "ipa": "/ˈpeər.ɪŋ/", "meaning": "ghép đôi (rượu + món ăn)", "example": "A good wine pairing enhances the flavors of the meal."},
            {"word": "tasting menu", "ipa": "/ˈteɪ.stɪŋ ˈmen.juː/", "meaning": "thực đơn thử nhiều món nhỏ", "example": "The restaurant offers an eight-course tasting menu on Friday evenings."},
        ],
        "B2": [
            {"word": "molecular gastronomy", "ipa": "/məˈlek.jʊ.lər ˌɡæs.trɒˈnɒm.i/", "meaning": "ẩm thực phân tử", "example": "Molecular gastronomy uses science to transform textures and presentations."},
            {"word": "spherification", "ipa": "/ˌsfɪər.ɪ.fɪˈkeɪ.ʃən/", "meaning": "kỹ thuật tạo hình cầu (ẩm thực)", "example": "Spherification creates liquid-filled spheres that burst in the mouth."},
            {"word": "hydrocolloid", "ipa": "/ˌhaɪ.drəʊˈkɒl.ɔɪd/", "meaning": "hydrocolloid (chất tạo gel)", "example": "Agar agar is a plant-based hydrocolloid used to set gels."},
            {"word": "transglutaminase", "ipa": "/ˌtræns.ɡluːˈtæm.ɪ.neɪz/", "meaning": "enzyme dán thịt", "example": "Transglutaminase, or meat glue, bonds proteins together."},
            {"word": "sous vide immersion circulator", "ipa": "/suː viːd ɪˈmɜː.ʃən ˈsɜː.kjʊ.leɪ.tər/", "meaning": "máy nấu sous vide tuần hoàn", "example": "An immersion circulator maintains the precise temperature needed for sous vide cooking."},
            {"word": "fermentation science", "ipa": "/ˌfɜː.menˈteɪ.ʃən ˈsaɪəns/", "meaning": "khoa học lên men", "example": "Fermentation science is behind products like kimchi, kefir, and sourdough."},
            {"word": "Maillard reaction optimization", "ipa": "/maɪˈjɑːr riˈæk.ʃən ˌɒp.tɪ.maɪˈzeɪ.ʃən/", "meaning": "tối ưu hóa phản ứng Maillard", "example": "Chefs optimize the Maillard reaction by controlling heat and moisture."},
            {"word": "knife skills", "ipa": "/naɪf skɪlz/", "meaning": "kỹ năng dùng dao", "example": "Good knife skills are the foundation of professional cooking."},
            {"word": "brigade system", "ipa": "/brɪˈɡeɪd ˈsɪs.təm/", "meaning": "hệ thống tổ chức bếp nhà hàng", "example": "Escoffier created the brigade system to organize professional kitchens."},
            {"word": "gastronomy", "ipa": "/ɡæsˈtrɒn.ə.mi/", "meaning": "ẩm thực học", "example": "Gastronomy is the study of food and culture."},
            {"word": "terroir", "ipa": "/tɛˈrwɑːr/", "meaning": "điều kiện địa lý ảnh hưởng đến hương vị", "example": "The terroir of a region affects the flavor of its wine and produce."},
            {"word": "provenance", "ipa": "/ˈprɒv.ɪ.nəns/", "meaning": "xuất xứ nguồn gốc thực phẩm", "example": "Chefs increasingly focus on the provenance of their ingredients."},
            {"word": "farm-to-table", "ipa": "/fɑːm tə ˈteɪ.bəl/", "meaning": "thực phẩm từ trang trại đến bàn ăn", "example": "The farm-to-table movement emphasizes fresh, locally sourced ingredients."},
            {"word": "foraging", "ipa": "/ˈfɒr.ɪ.dʒɪŋ/", "meaning": "tìm kiếm thực phẩm trong tự nhiên", "example": "The chef went foraging for wild mushrooms and herbs in the forest."},
            {"word": "food waste reduction", "ipa": "/fuːd weɪst rɪˈdʌk.ʃən/", "meaning": "giảm thiểu lãng phí thực phẩm", "example": "Many restaurants are implementing food waste reduction strategies."},
            {"word": "nose-to-tail cooking", "ipa": "/nəʊz tə teɪl ˈkʊk.ɪŋ/", "meaning": "nấu sử dụng toàn bộ con vật", "example": "Nose-to-tail cooking uses every part of an animal, reducing waste."},
            {"word": "umami bomb", "ipa": "/uːˈmɑː.mi bɒm/", "meaning": "kết hợp nhiều nguyên liệu giàu umami", "example": "Combining miso, soy sauce, and mushrooms creates an umami bomb."},
            {"word": "flavor profile", "ipa": "/ˈfleɪ.vər ˈprəʊ.faɪl/", "meaning": "hồ sơ hương vị", "example": "Each region's cuisine has a unique flavor profile shaped by local ingredients."},
            {"word": "deconstruction (cuisine)", "ipa": "/ˌdiː.kənˈstrʌk.ʃən/", "meaning": "giải cấu trúc món ăn", "example": "Deconstruction presents traditional dishes in surprising new forms."},
            {"word": "emulsion sauce", "ipa": "/ɪˈmʌl.ʃən sɔːs/", "meaning": "sốt nhũ tương", "example": "Hollandaise and béarnaise are classic emulsion sauces made with egg yolks and butter."},
            {"word": "mother sauce", "ipa": "/ˈmʌð.ər sɔːs/", "meaning": "nước sốt mẹ (5 loại cơ bản của Pháp)", "example": "French cooking is based on five mother sauces from which all others derive."},
            {"word": "velouté", "ipa": "/vəˈluː.teɪ/", "meaning": "sốt velouté (nước dùng sánh)", "example": "Velouté is one of the French mother sauces made from light stock and roux."},
            {"word": "beurre blanc", "ipa": "/ˌbɜː ˈblɒŋ/", "meaning": "sốt bơ trắng kiểu Pháp", "example": "Beurre blanc is a light butter sauce often served with fish."},
            {"word": "roux", "ipa": "/ruː/", "meaning": "hỗn hợp bơ + bột làm đặc sốt", "example": "A dark roux is the foundation of many Cajun and Creole dishes."},
            {"word": "espagnole", "ipa": "/ˌes.pænˈjəʊl/", "meaning": "sốt nâu (espagnole)", "example": "Espagnole is a rich brown sauce that is one of the five French mother sauces."},
            {"word": "hollandaise", "ipa": "/ˌhɒl.ənˈdeɪz/", "meaning": "sốt hollandaise", "example": "Eggs Benedict is traditionally served with hollandaise sauce."},
            {"word": "béchamel", "ipa": "/ˌbeɪ.ʃəˈmel/", "meaning": "sốt béchamel (sốt trắng)", "example": "Béchamel is the creamy white sauce used in lasagna."},
            {"word": "confit", "ipa": "/ˈkɒn.fiː/", "meaning": "kỹ thuật nấu và bảo quản trong mỡ", "example": "Duck confit is cooked and preserved in its own fat."},
            {"word": "en papillote", "ipa": "/ɒn ˌpæp.ɪˈjɒt/", "meaning": "nấu trong túi giấy bạc/giấy nến", "example": "Fish en papillote is steamed inside a parchment paper parcel."},
            {"word": "stir-fry technique", "ipa": "/stɜː fraɪ tekˈniːk/", "meaning": "kỹ thuật xào nhanh", "example": "Good stir-fry technique requires high heat and constant movement."},
            {"word": "culinary arts", "ipa": "/ˈkʌl.ɪ.nər.i ɑːts/", "meaning": "nghệ thuật ẩm thực", "example": "She studied culinary arts at a prestigious institute in Paris."},
            {"word": "Michelin star", "ipa": "/ˌmɪʃ.ɪ.lɪn stɑːr/", "meaning": "sao Michelin (giải thưởng ẩm thực)", "example": "The restaurant earned its first Michelin star after just two years of operation."},
            {"word": "food criticism", "ipa": "/fuːd ˈkrɪt.ɪ.sɪ.zəm/", "meaning": "phê bình ẩm thực", "example": "Food criticism requires both technical knowledge and excellent writing skills."},
            {"word": "menu engineering", "ipa": "/ˈmen.juː ˌen.dʒɪˈnɪər.ɪŋ/", "meaning": "thiết kế thực đơn chiến lược", "example": "Menu engineering uses psychology and profitability to design effective menus."},
            {"word": "food costing", "ipa": "/fuːd ˈkɒs.tɪŋ/", "meaning": "tính giá thành món ăn", "example": "Food costing calculates the exact cost of each dish to ensure profitability."},
            {"word": "food styling", "ipa": "/fuːd ˈstaɪ.lɪŋ/", "meaning": "tạo kiểu thực phẩm cho ảnh chụp", "example": "Food styling makes dishes look their most attractive for photography."},
            {"word": "recipe development", "ipa": "/ˈres.ɪ.pi dɪˈvel.əp.mənt/", "meaning": "phát triển công thức nấu ăn", "example": "Recipe development involves multiple rounds of testing and adjustment."},
            {"word": "culinary tourism", "ipa": "/ˈkʌl.ɪ.nər.i ˈtʊər.ɪ.zəm/", "meaning": "du lịch ẩm thực", "example": "Culinary tourism attracts travelers who want to experience local food culture."},
            {"word": "fermented beverages", "ipa": "/fɜːˈmen.tɪd ˈbev.ər.ɪdʒɪz/", "meaning": "đồ uống lên men", "example": "Kombucha and kefir are popular fermented beverages with health benefits."},
            {"word": "food pairing theory", "ipa": "/fuːd ˈpeər.ɪŋ ˈθɪər.i/", "meaning": "lý thuyết ghép đôi thực phẩm", "example": "Food pairing theory suggests combining ingredients that share flavor compounds."},
            {"word": "sustainable seafood", "ipa": "/səˈsteɪ.nə.bəl ˈsiː.fuːd/", "meaning": "hải sản bền vững", "example": "Sustainable seafood choices help protect ocean ecosystems."},
            {"word": "plant-based diet", "ipa": "/plɑːnt beɪst ˈdaɪ.ɪt/", "meaning": "chế độ ăn thực vật", "example": "A plant-based diet has been linked to reduced risk of heart disease."},
            {"word": "fermentation crock", "ipa": "/ˌfɜː.menˈteɪ.ʃən krɒk/", "meaning": "hũ lên men", "example": "She uses a ceramic fermentation crock to make sauerkraut at home."},
            {"word": "charcuterie", "ipa": "/ˌʃɑː.kʊˈtər.i/", "meaning": "nghề làm thịt nguội xúc xích", "example": "A charcuterie board features an array of cured meats, cheeses, and accompaniments."},
            {"word": "affinage", "ipa": "/ˌæf.ɪˈnɑːʒ/", "meaning": "nghề ủ chín phô mai", "example": "Affinage is the art of maturing and caring for cheese to develop its flavor."},
            {"word": "fromage affiné", "ipa": "/frɒˈmɑːʒ ˌæf.ɪˈneɪ/", "meaning": "phô mai ủ chín", "example": "Fromage affiné develops complex flavors during the aging process."},
            {"word": "mirepoix", "ipa": "/ˌmɪər.ˈpwɑː/", "meaning": "hỗn hợp hành/cà rốt/cần tây", "example": "Sweat a mirepoix of onion, carrot, and celery as the base for the stock."},
            {"word": "bouquet garni", "ipa": "/ˌbuː.keɪ ɡɑːˈniː/", "meaning": "bó rau thơm nấu súp", "example": "Add a bouquet garni of thyme, bay leaf, and parsley to the broth."},
            {"word": "deglazing liquid", "ipa": "/diːˈɡleɪ.zɪŋ ˈlɪk.wɪd/", "meaning": "chất lỏng dùng để hòa tan cặn nồi", "example": "Wine or stock can be used as a deglazing liquid to enhance flavor."},
            {"word": "modern cuisine", "ipa": "/ˈmɑdərn kwɪˈzin/", "meaning": "ẩm thực phân tử", "example": "Molecular gastronomy uses science to transform textures and presentations."},
        ],
        "C1": [
            {"word": "umami glutamate", "ipa": "/uːˈmɑː.mi ˈɡluː.tə.meɪt/", "meaning": "glutamate tạo vị umami", "example": "Glutamate is the amino acid responsible for the umami taste in fermented and aged foods."},
            {"word": "encapsulation (culinary)", "ipa": "/ɪnˌkæp.sjʊˈleɪ.ʃən/", "meaning": "đóng gói hương vị/ẩm thực phân tử", "example": "Encapsulation in molecular gastronomy traps flavors inside edible shells."},
            {"word": "culinary biophysics", "ipa": "/ˈkʌl.ɪ.nər.i ˌbaɪ.əʊˈfɪz.ɪks/", "meaning": "vật lý sinh học ẩm thực", "example": "Culinary biophysics investigates the physical changes that occur during cooking."},
            {"word": "thermal diffusivity", "ipa": "/ˈθɜː.məl dɪˌfjuː.zɪˈvɪt.i/", "meaning": "độ khuếch tán nhiệt", "example": "Thermal diffusivity determines how quickly heat penetrates the center of food."},
            {"word": "water activity", "ipa": "/ˈwɔː.tər ækˈtɪv.ɪ.ti/", "meaning": "hoạt độ nước trong thực phẩm", "example": "Low water activity prevents microbial growth in dried and cured foods."},
            {"word": "Maillard kinetics", "ipa": "/maɪˈjɑːr kɪˈnet.ɪks/", "meaning": "động học phản ứng Maillard", "example": "Understanding Maillard kinetics helps chefs control browning precisely."},
            {"word": "gelatinization", "ipa": "/dʒɪˌlæt.ɪ.naɪˈzeɪ.ʃən/", "meaning": "sự hồ hóa tinh bột", "example": "Gelatinization of starch occurs when it is heated in the presence of water."},
            {"word": "retrogradation", "ipa": "/rɪˌtrɒɡ.rəˈdeɪ.ʃən/", "meaning": "sự thoái hóa tinh bột", "example": "Retrogradation causes cooked starch to recrystallize on cooling."},
            {"word": "protein denaturation", "ipa": "/ˈprəʊ.tiːn ˌdiː.neɪ.tʃəˈreɪ.ʃən/", "meaning": "biến tính protein", "example": "Heat causes protein denaturation, changing the texture of eggs and meat."},
            {"word": "lipid oxidation", "ipa": "/ˈlɪp.ɪd ˌɒk.sɪˈdeɪ.ʃən/", "meaning": "oxy hóa chất béo", "example": "Lipid oxidation causes fats to become rancid over time."},
            {"word": "enzymatic browning", "ipa": "/ˌen.zaɪˈmæt.ɪk ˈbraʊ.nɪŋ/", "meaning": "sự thâm đen do enzyme", "example": "Enzymatic browning turns cut apples brown; lemon juice can prevent this."},
            {"word": "collagen conversion", "ipa": "/ˈkɒl.ə.dʒən kənˈvɜː.ʃən/", "meaning": "chuyển đổi collagen thành gelatin", "example": "Slow cooking converts collagen into gelatin, making tough cuts tender."},
            {"word": "pectin structure", "ipa": "/ˈpek.tɪn ˈstrʌk.tʃər/", "meaning": "cấu trúc pectin (trong trái cây)", "example": "Pectin structure determines how well fruit will set as jam."},
            {"word": "vapor pressure", "ipa": "/ˈveɪ.pər ˌpreʃ.ər/", "meaning": "áp suất hơi nước", "example": "Vapor pressure affects the boiling point of water and cooking at altitude."},
            {"word": "osmosis in cooking", "ipa": "/ɒzˈməʊ.sɪs ɪn ˈkʊk.ɪŋ/", "meaning": "thẩm thấu trong nấu ăn", "example": "Osmosis draws moisture out of vegetables when salt is applied."},
            {"word": "centrifugal clarification", "ipa": "/ˌsen.trɪˈfjuː.ɡəl ˌklær.ɪ.fɪˈkeɪ.ʃən/", "meaning": "làm trong bằng ly tâm", "example": "Centrifugal clarification creates crystal-clear stocks without filtration."},
            {"word": "rotary evaporation", "ipa": "/ˈrəʊ.tər.i ɪˌvæp.əˈreɪ.ʃən/", "meaning": "bay hơi xoay (cô đặc hương thơm)", "example": "Rotary evaporation concentrates delicate flavors without applying heat."},
            {"word": "liquid nitrogen cooking", "ipa": "/ˈlɪk.wɪd ˈnaɪ.trə.dʒən ˈkʊk.ɪŋ/", "meaning": "nấu ăn bằng nitơ lỏng", "example": "Liquid nitrogen cooking flash-freezes food instantly for unique textures."},
            {"word": "anti-griddle", "ipa": "/ˌæn.tiˈɡrɪd.əl/", "meaning": "thiết bị làm lạnh nhanh bề mặt", "example": "An anti-griddle freezes the outside of food while the inside remains warm."},
            {"word": "edible aerosol", "ipa": "/ˈed.ɪ.bəl ˈeər.ə.sɒl/", "meaning": "sương ăn được", "example": "Chefs use edible aerosols to deliver intense flavor in tiny amounts."},
            {"word": "culinary neuroscience", "ipa": "/ˈkʌl.ɪ.nər.i ˌnjʊər.əʊˈsaɪəns/", "meaning": "thần kinh học ẩm thực", "example": "Culinary neuroscience studies how flavor perception works in the brain."},
            {"word": "flavor volatiles", "ipa": "/ˈfleɪ.vər ˈvɒl.ə.taɪlz/", "meaning": "hợp chất hương bay hơi", "example": "Heat releases flavor volatiles that give food its characteristic aroma."},
            {"word": "gas chromatography (food)", "ipa": "/ɡæs ˌkrəʊ.mæˈtɒɡ.rə.fi/", "meaning": "sắc ký khí (phân tích hương vị)", "example": "Gas chromatography identifies the volatile compounds responsible for aroma."},
            {"word": "food rheology", "ipa": "/fuːd riˈɒl.ə.dʒi/", "meaning": "lưu biến học thực phẩm", "example": "Food rheology studies the flow and deformation behavior of food materials."},
            {"word": "sol-gel transition", "ipa": "/sɒl dʒel trænˈzɪʃ.ən/", "meaning": "chuyển đổi dung dịch-gel", "example": "The sol-gel transition occurs when a hot liquid sets into a solid upon cooling."},
            {"word": "freeze-drying", "ipa": "/ˈfriːz ˌdraɪ.ɪŋ/", "meaning": "đông khô thực phẩm", "example": "Freeze-drying preserves food while retaining its nutritional value and flavor."},
            {"word": "high-pressure processing", "ipa": "/haɪ ˈpreʃ.ər ˈprəʊ.ses.ɪŋ/", "meaning": "xử lý áp suất cao", "example": "High-pressure processing extends shelf life without using heat."},
            {"word": "pulsed electric field", "ipa": "/pʌlst ɪˈlek.trɪk fiːld/", "meaning": "điện trường xung (bảo quản thực phẩm)", "example": "Pulsed electric field technology preserves food by disrupting cell membranes."},
            {"word": "biopreservation", "ipa": "/ˌbaɪ.əʊˌprez.əˈveɪ.ʃən/", "meaning": "bảo quản sinh học", "example": "Biopreservation uses beneficial microorganisms to extend the shelf life of food."},
            {"word": "sensory evaluation", "ipa": "/ˈsen.sər.i ɪˌvæl.juˈeɪ.ʃən/", "meaning": "đánh giá cảm quan", "example": "Sensory evaluation panels test food products for taste, texture, and appearance."},
            {"word": "olfactory fatigue", "ipa": "/ɒlˈfæk.tər.i fəˈtiːɡ/", "meaning": "mệt mỏi khứu giác", "example": "Olfactory fatigue reduces a person's ability to detect smells after prolonged exposure."},
            {"word": "supertaster", "ipa": "/ˈsuː.pər.teɪ.stər/", "meaning": "người siêu nhạy vị giác", "example": "A supertaster perceives flavors more intensely due to a higher density of taste buds."},
            {"word": "retronasal olfaction", "ipa": "/ˌret.rəʊˈneɪ.zəl ɒlˈfæk.ʃən/", "meaning": "khứu giác sau mũi (khi ăn)", "example": "Retronasal olfaction is responsible for most of what we perceive as flavor."},
            {"word": "taste receptor", "ipa": "/teɪst rɪˈsep.tər/", "meaning": "thụ thể vị giác", "example": "Different taste receptors respond to sweet, sour, salty, bitter, and umami."},
            {"word": "synesthesia (taste)", "ipa": "/ˌsɪn.ɪsˈθiː.zi.ə/", "meaning": "chứng hỗn giác vị giác", "example": "Some people experience synesthesia, perceiving tastes as colors or sounds."},
            {"word": "food matrix", "ipa": "/fuːd ˈmeɪ.trɪks/", "meaning": "ma trận thực phẩm", "example": "The food matrix influences how nutrients are absorbed and flavors are released."},
            {"word": "culinary epigenetics", "ipa": "/ˈkʌl.ɪ.nər.i ˌep.ɪ.dʒɪˈnet.ɪks/", "meaning": "biểu sinh học dinh dưỡng", "example": "Culinary epigenetics explores how diet affects gene expression and health outcomes."},
            {"word": "nutraceuticals", "ipa": "/ˌnjuː.trəˈsuː.tɪ.kəlz/", "meaning": "thực phẩm chức năng dược phẩm", "example": "Nutraceuticals are food components that provide medical or health benefits."},
            {"word": "biofortification", "ipa": "/ˌbaɪ.əʊˌfɔː.tɪ.fɪˈkeɪ.ʃən/", "meaning": "tăng cường dinh dưỡng sinh học cho cây trồng", "example": "Biofortification increases the nutrient content of crops through breeding."},
            {"word": "food neophobia", "ipa": "/fuːd ˌniː.əˈfəʊ.bi.ə/", "meaning": "sợ thử thức ăn mới", "example": "Food neophobia is common in young children who are reluctant to try new foods."},
            {"word": "cultural food heritage", "ipa": "/ˈkʌl.tʃər.əl fuːd ˈher.ɪ.tɪdʒ/", "meaning": "di sản ẩm thực văn hóa", "example": "UNESCO recognizes cultural food heritage as part of intangible cultural heritage."},
            {"word": "precision fermentation", "ipa": "/prɪˈsɪʒ.ən ˌfɜː.menˈteɪ.ʃən/", "meaning": "lên men chính xác", "example": "Precision fermentation produces dairy proteins without using animals."},
            {"word": "cultivated meat", "ipa": "/ˈkʌl.tɪ.veɪ.tɪd miːt/", "meaning": "thịt nuôi cấy", "example": "Cultivated meat is grown from animal cells in a lab, without slaughter."},
            {"word": "mycoprotein", "ipa": "/ˌmaɪ.kəʊˈprəʊ.tiːn/", "meaning": "protein từ nấm", "example": "Mycoprotein is a high-protein food made from fermented fungi."},
            {"word": "insect protein", "ipa": "/ˈɪn.sekt ˈprəʊ.tiːn/", "meaning": "protein côn trùng", "example": "Insect protein is a sustainable alternative to conventional livestock."},
            {"word": "algae-based food", "ipa": "/ˈæl.dʒiː beɪst fuːd/", "meaning": "thực phẩm từ tảo", "example": "Algae-based food provides protein, omega-3s, and essential nutrients."},
            {"word": "circular food economy", "ipa": "/ˈsɜː.kjʊ.lər fuːd ɪˈkɒn.ə.mi/", "meaning": "kinh tế thực phẩm tuần hoàn", "example": "A circular food economy minimizes waste by reusing and recycling food resources."},
            {"word": "gastrodiplomacy", "ipa": "/ˌɡæs.trəʊ.dɪˈpləʊ.mə.si/", "meaning": "ngoại giao ẩm thực", "example": "Thailand uses gastrodiplomacy to promote its cuisine and culture globally."},
            {"word": "epicureanism", "ipa": "/ˌep.ɪˌkjʊər.iˈeɪ.nɪ.zəm/", "meaning": "chủ nghĩa hưởng thụ ẩm thực", "example": "Epicureanism in food refers to the pursuit of refined culinary pleasure."},
            {"word": "savory essence", "ipa": "/ˈseɪvəri ˈɛsəns/", "meaning": "glutamate tạo vị umami", "example": "Glutamate is the amino acid responsible for the umami taste in fermented and aged foods."},
        ],
    },
    "fashion": {
        "A1": [
            {"word": "clothes", "ipa": "/kləʊðz/", "meaning": "quần áo", "example": "She bought new clothes for the new school year."},
            {"word": "shirt", "ipa": "/ʃɜːt/", "meaning": "áo sơ mi", "example": "He wore a white shirt to the office."},
            {"word": "dress", "ipa": "/dres/", "meaning": "váy liền thân", "example": "She wore a beautiful blue dress to the party."},
            {"word": "jeans", "ipa": "/dʒiːnz/", "meaning": "quần jeans", "example": "He wears jeans almost every day."},
            {"word": "shoes", "ipa": "/ʃuːz/", "meaning": "giày", "example": "She bought a pair of white shoes for summer."},
            {"word": "hat", "ipa": "/hæt/", "meaning": "mũ", "example": "Wear a hat to protect yourself from the sun."},
            {"word": "jacket", "ipa": "/ˈdʒæk.ɪt/", "meaning": "áo khoác", "example": "He put on his jacket before going outside."},
            {"word": "coat", "ipa": "/kəʊt/", "meaning": "áo khoác dài", "example": "She wore a warm coat in the cold weather."},
            {"word": "bag", "ipa": "/bæɡ/", "meaning": "túi xách", "example": "She carries a small bag to work every day."},
            {"word": "socks", "ipa": "/sɒks/", "meaning": "tất/vớ", "example": "He always wears matching socks with his shoes."},
            {"word": "boots", "ipa": "/buːts/", "meaning": "giày bốt", "example": "She loves wearing boots in autumn."},
            {"word": "shorts", "ipa": "/ʃɔːts/", "meaning": "quần short", "example": "He wears shorts when the weather is hot."},
            {"word": "skirt", "ipa": "/skɜːt/", "meaning": "váy", "example": "She wore a long floral skirt to the festival."},
            {"word": "trousers", "ipa": "/ˈtraʊ.zərz/", "meaning": "quần dài", "example": "He wore smart black trousers to the interview."},
            {"word": "t-shirt", "ipa": "/ˈtiː.ʃɜːt/", "meaning": "áo thun", "example": "He put on a plain white t-shirt and jeans."},
            {"word": "sweater", "ipa": "/ˈswet.ər/", "meaning": "áo len", "example": "She wore a cozy sweater on the cold evening."},
            {"word": "scarf", "ipa": "/skɑːf/", "meaning": "khăn quàng cổ", "example": "She wrapped a scarf around her neck to keep warm."},
            {"word": "gloves", "ipa": "/ɡlʌvz/", "meaning": "găng tay", "example": "She put on gloves before going out in the snow."},
            {"word": "belt", "ipa": "/belt/", "meaning": "thắt lưng", "example": "He wore a brown leather belt with his jeans."},
            {"word": "ring", "ipa": "/rɪŋ/", "meaning": "nhẫn", "example": "She wears a gold ring on her right hand."},
            {"word": "necklace", "ipa": "/ˈnek.ləs/", "meaning": "vòng cổ", "example": "She received a beautiful necklace as a birthday gift."},
            {"word": "earrings", "ipa": "/ˈɪər.ɪŋz/", "meaning": "bông tai", "example": "She put on small silver earrings for the dinner."},
            {"word": "watch", "ipa": "/wɔʧ/", "meaning": "đồng hồ đeo tay", "example": "He always wears his grandfather's old watch."},
            {"word": "color", "ipa": "/ˈkʌl.ər/", "meaning": "màu sắc", "example": "She prefers wearing light colors in summer."},
            {"word": "size", "ipa": "/saɪz/", "meaning": "kích cỡ (quần áo)", "example": "What size do you wear? I need a medium."},
            {"word": "wear", "ipa": "/weər/", "meaning": "mặc, đeo", "example": "She likes to wear comfortable clothes at home."},
            {"word": "put on", "ipa": "/pʊt ɒn/", "meaning": "mặc vào, đội vào", "example": "Put on your coat — it's cold outside."},
            {"word": "take off", "ipa": "/teɪk ɒf/", "meaning": "cởi ra", "example": "Please take off your shoes before entering."},
            {"word": "fashion", "ipa": "/ˈfæʃ.ən/", "meaning": "thời trang", "example": "She is very interested in fashion and style."},
            {"word": "style", "ipa": "/staɪl/", "meaning": "phong cách ăn mặc", "example": "He has a very unique style with bold colors and patterns."},
            {"word": "new", "ipa": "/njuː/", "meaning": "mới", "example": "She loves buying new clothes every season."},
            {"word": "old", "ipa": "/əʊld/", "meaning": "cũ", "example": "He donated his old clothes to charity."},
            {"word": "clean", "ipa": "/kliːn/", "meaning": "sạch sẽ", "example": "Always wear clean clothes to work."},
            {"word": "dirty", "ipa": "/ˈdɜː.ti/", "meaning": "bẩn", "example": "She put her dirty clothes in the washing machine."},
            {"word": "tight", "ipa": "/taɪt/", "meaning": "chật, bó sát", "example": "The jeans are a bit too tight — I need a bigger size."},
            {"word": "loose", "ipa": "/luːs/", "meaning": "rộng, thoải mái", "example": "She prefers loose-fitting clothes for working out."},
            {"word": "comfortable", "ipa": "/ˈkʌm.fə.tə.bəl/", "meaning": "thoải mái", "example": "She dresses for comfort rather than style."},
            {"word": "pretty", "ipa": "/ˈprɪt.i/", "meaning": "đẹp, dễ thương", "example": "She wore a pretty pink top to the lunch."},
            {"word": "casual", "ipa": "/ˈkæʒ.u.əl/", "meaning": "thông thường, không trang trọng", "example": "The office has a casual dress code on Fridays."},
            {"word": "formal", "ipa": "/ˈfɔː.məl/", "meaning": "trang trọng", "example": "He wore formal clothes to the business dinner."},
            {"word": "uniform", "ipa": "/ˈjuː.nɪ.fɔːm/", "meaning": "đồng phục", "example": "All students must wear the school uniform."},
            {"word": "swimsuit", "ipa": "/ˈswɪm.suːt/", "meaning": "đồ bơi", "example": "She packed a swimsuit for the beach holiday."},
            {"word": "pajamas", "ipa": "/pəˈdʒɑː.məz/", "meaning": "bộ đồ ngủ", "example": "He changed into pajamas before going to bed."},
            {"word": "underwear", "ipa": "/ˈʌn.də.weər/", "meaning": "đồ lót", "example": "She bought a pack of cotton underwear."},
            {"word": "raincoat", "ipa": "/ˈreɪn.kəʊt/", "meaning": "áo mưa", "example": "Don't forget your raincoat — it's supposed to rain."},
            {"word": "sunglasses", "ipa": "/ˈsʌnˌɡlɑː.sɪz/", "meaning": "kính râm", "example": "She put on sunglasses before going to the beach."},
            {"word": "fabric", "ipa": "/ˈfæb.rɪk/", "meaning": "vải", "example": "The dress is made of a soft cotton fabric."},
            {"word": "pattern", "ipa": "/ˈpæt.ən/", "meaning": "họa tiết", "example": "She chose a floral pattern for the curtains and dress."},
            {"word": "stripe", "ipa": "/straɪp/", "meaning": "sọc", "example": "He wore a blue and white striped shirt."},
            {"word": "pocket", "ipa": "/ˈpɒk.ɪt/", "meaning": "túi (áo quần)", "example": "She put her phone in her coat pocket."},
        ],
        "A2": [
            {"word": "outfit", "ipa": "/ˈaʊt.fɪt/", "meaning": "bộ trang phục", "example": "She put together a great outfit for the party."},
            {"word": "wardrobe", "ipa": "/ˈwɔː.drəʊb/", "meaning": "tủ quần áo; tổng bộ trang phục", "example": "She has a large wardrobe full of colorful clothes."},
            {"word": "accessory", "ipa": "/əkˈses.ər.i/", "meaning": "phụ kiện thời trang", "example": "A simple outfit can be elevated with the right accessories."},
            {"word": "brand", "ipa": "/brænd/", "meaning": "thương hiệu", "example": "She only buys clothes from well-known brands."},
            {"word": "designer", "ipa": "/dɪˈzaɪ.nər/", "meaning": "nhà thiết kế; hàng hiệu", "example": "She dreams of owning designer handbags."},
            {"word": "second-hand", "ipa": "/ˌsek.əndˈhænd/", "meaning": "hàng cũ, đồ secondhand", "example": "She shops at second-hand stores to save money."},
            {"word": "vintage", "ipa": "/ˈvɪn.tɪdʒ/", "meaning": "đồ cổ điển, vintage", "example": "She loves collecting vintage clothing from the 1970s."},
            {"word": "trendy", "ipa": "/ˈtren.di/", "meaning": "hợp mốt, theo xu hướng", "example": "She always wears the most trendy outfits."},
            {"word": "classic", "ipa": "/ˈklæs.ɪk/", "meaning": "cổ điển, không lỗi thời", "example": "A little black dress is a classic wardrobe staple."},
            {"word": "elegant", "ipa": "/ˈel.ɪ.ɡənt/", "meaning": "thanh lịch", "example": "She looked elegant in her silk evening gown."},
            {"word": "stylish", "ipa": "/ˈstaɪ.lɪʃ/", "meaning": "thời thượng, sành điệu", "example": "He is always stylish no matter what he wears."},
            {"word": "fashionable", "ipa": "/ˈfæʃ.ən.ə.bəl/", "meaning": "hợp thời trang", "example": "She always looks fashionable in her choice of clothes."},
            {"word": "trend", "ipa": "/trend/", "meaning": "xu hướng thời trang", "example": "Oversized blazers are a big fashion trend this season."},
            {"word": "season", "ipa": "/ˈsiː.zən/", "meaning": "mùa (thời trang)", "example": "New fashion collections are released every season."},
            {"word": "collection", "ipa": "/kəˈlek.ʃən/", "meaning": "bộ sưu tập thời trang", "example": "The designer unveiled a stunning new collection at Paris Fashion Week."},
            {"word": "model", "ipa": "/ˈmɒd.əl/", "meaning": "người mẫu", "example": "She works as a fashion model in Milan."},
            {"word": "runway", "ipa": "/ˈrʌn.weɪ/", "meaning": "sàn catwalk trình diễn", "example": "The models walked down the runway in stunning outfits."},
            {"word": "fashion show", "ipa": "/ˈfæʃ.ən ʃəʊ/", "meaning": "buổi trình diễn thời trang", "example": "She attended a fashion show during Milan Fashion Week."},
            {"word": "boutique", "ipa": "/buːˈtiːk/", "meaning": "cửa hàng thời trang nhỏ", "example": "She owns a small boutique selling handmade clothes."},
            {"word": "fitting room", "ipa": "/ˈfɪt.ɪŋ ruːm/", "meaning": "phòng thử đồ", "example": "She tried on several dresses in the fitting room."},
            {"word": "tailor", "ipa": "/ˈteɪ.lər/", "meaning": "thợ may", "example": "She took the suit to a tailor to have it altered."},
            {"word": "seamstress", "ipa": "/ˈsiːm.strəs/", "meaning": "thợ may (nữ)", "example": "The seamstress made a custom dress for the wedding."},
            {"word": "sew", "ipa": "/səʊ/", "meaning": "may vá", "example": "She learned to sew her own clothes as a teenager."},
            {"word": "button", "ipa": "/ˈbʌt.ən/", "meaning": "cúc áo", "example": "One of the buttons fell off her coat."},
            {"word": "zipper", "ipa": "/ˈzɪp.ər/", "meaning": "khóa kéo", "example": "The zipper on her jacket is broken."},
            {"word": "hem", "ipa": "/hem/", "meaning": "đường viền vải; gấu áo/váy", "example": "She asked the tailor to shorten the hem of her skirt."},
            {"word": "collar", "ipa": "/ˈkɒl.ər/", "meaning": "cổ áo", "example": "The collar of his shirt was too tight."},
            {"word": "sleeve", "ipa": "/sliːv/", "meaning": "tay áo", "example": "She rolled up her sleeves before washing the dishes."},
            {"word": "lining", "ipa": "/ˈlaɪ.nɪŋ/", "meaning": "lớp lót bên trong", "example": "The jacket has a beautiful silk lining inside."},
            {"word": "cotton", "ipa": "/ˈkɒt.ən/", "meaning": "vải cotton", "example": "She prefers cotton clothes because they are breathable."},
            {"word": "silk", "ipa": "/sɪlk/", "meaning": "lụa", "example": "She wore a beautiful silk blouse to the gala."},
            {"word": "wool", "ipa": "/wʊl/", "meaning": "len", "example": "The sweater is made of soft merino wool."},
            {"word": "leather", "ipa": "/ˈleð.ər/", "meaning": "da (chất liệu)", "example": "She bought a genuine leather handbag on her trip to Italy."},
            {"word": "denim", "ipa": "/ˈden.ɪm/", "meaning": "vải denim (jean)", "example": "Denim jackets never go out of style."},
            {"word": "lace", "ipa": "/leɪs/", "meaning": "ren", "example": "The wedding dress was adorned with delicate lace."},
            {"word": "velvet", "ipa": "/ˈvel.vɪt/", "meaning": "nhung", "example": "She wore a deep red velvet blazer to the event."},
            {"word": "floral", "ipa": "/ˈflɔː.rəl/", "meaning": "hoa văn, có hoa", "example": "She wore a floral summer dress to the picnic."},
            {"word": "plaid", "ipa": "/plæd/", "meaning": "vải ô vuông (caro)", "example": "He wore a plaid flannel shirt on the hiking trip."},
            {"word": "polka dot", "ipa": "/ˈpɒl.kə dɒt/", "meaning": "chấm bi", "example": "She wore a polka dot dress to the retro-themed party."},
            {"word": "solid color", "ipa": "/ˈsɒl.ɪd ˈkʌl.ər/", "meaning": "một màu đồng nhất", "example": "A solid color top is easy to pair with any bottoms."},
            {"word": "monochrome", "ipa": "/ˈmɒn.ə.krəʊm/", "meaning": "đơn sắc", "example": "She loves a monochrome black-and-white look."},
            {"word": "neon", "ipa": "/ˈniː.ɒn/", "meaning": "màu neon sáng", "example": "Neon colors were a huge trend in the 1980s."},
            {"word": "pastel", "ipa": "/ˈpæs.təl/", "meaning": "màu pastel nhạt", "example": "Pastel shades are popular for spring fashion."},
            {"word": "neutral", "ipa": "/ˈnjuː.trəl/", "meaning": "màu trung tính (be, xám, trắng)", "example": "She builds her outfits around neutral colors like beige and white."},
            {"word": "statement piece", "ipa": "/ˈsteɪt.mənt piːs/", "meaning": "món đồ nổi bật trong outfit", "example": "A bold necklace can be the statement piece of a simple outfit."},
            {"word": "layering", "ipa": "/ˈleɪər.ɪŋ/", "meaning": "mặc nhiều lớp", "example": "Layering allows you to adapt your outfit to changing temperatures."},
            {"word": "mix and match", "ipa": "/mɪks ənd mætʃ/", "meaning": "phối đồ linh hoạt", "example": "She loves to mix and match different pieces from her wardrobe."},
            {"word": "dress code", "ipa": "/ˈdres kəʊd/", "meaning": "quy định trang phục", "example": "The restaurant has a smart casual dress code."},
            {"word": "capsule wardrobe", "ipa": "/ˈkæp.sjuːl ˈwɔː.drəʊb/", "meaning": "tủ đồ tối giản", "example": "A capsule wardrobe consists of versatile, timeless pieces."},
            {"word": "high street", "ipa": "/haɪ striːt/", "meaning": "thời trang phổ thông", "example": "She shops at high street brands like Zara and H&M."},
        ],
        "B1": [
            {"word": "haute couture", "ipa": "/ˌəʊt kuːˈtjʊər/", "meaning": "thời trang cao cấp đặt riêng", "example": "Haute couture garments are handmade to the client's exact measurements."},
            {"word": "prêt-à-porter", "ipa": "/ˌpret ɑː pɔːˈteɪ/", "meaning": "thời trang may sẵn cao cấp", "example": "Prêt-à-porter bridges the gap between haute couture and mass market fashion."},
            {"word": "fast fashion", "ipa": "/fɑːst ˈfæʃ.ən/", "meaning": "thời trang nhanh, giá rẻ", "example": "Fast fashion produces cheap, trend-led clothing at high volume."},
            {"word": "slow fashion", "ipa": "/sləʊ ˈfæʃ.ən/", "meaning": "thời trang chậm, bền vững", "example": "Slow fashion advocates for quality, durability, and ethical production."},
            {"word": "sustainable fashion", "ipa": "/səˈsteɪ.nə.bəl ˈfæʃ.ən/", "meaning": "thời trang bền vững", "example": "Sustainable fashion uses eco-friendly materials and ethical labor practices."},
            {"word": "upcycling (fashion)", "ipa": "/ˈʌp.saɪ.klɪŋ/", "meaning": "tái chế sáng tạo quần áo", "example": "She upcycled old jeans into stylish shorts to reduce waste."},
            {"word": "capsule collection", "ipa": "/ˈkæp.sjuːl kəˈlek.ʃən/", "meaning": "bộ sưu tập giới hạn", "example": "The designer launched a capsule collection of ten essential pieces."},
            {"word": "lookbook", "ipa": "/ˈlʊk.bʊk/", "meaning": "sách ảnh trang phục mẫu", "example": "The brand released a stunning lookbook for its spring collection."},
            {"word": "editorial (fashion)", "ipa": "/ˌɛdəˈtɔriəl (ˈfæʃən)/", "meaning": "ảnh thời trang tạp chí", "example": "She was featured in a Vogue fashion editorial."},
            {"word": "silhouette", "ipa": "/ˌsɪl.uˈet/", "meaning": "dáng (thiết kế quần áo)", "example": "The designer favors a slim, tailored silhouette."},
            {"word": "drape", "ipa": "/dreɪp/", "meaning": "cách vải buông, rủ", "example": "The silk dress has a beautiful drape that flatters the figure."},
            {"word": "fit and flare", "ipa": "/fɪt ənd fleər/", "meaning": "dáng ôm trên, xòe dưới", "example": "The fit and flare dress is universally flattering on all body types."},
            {"word": "A-line", "ipa": "/ˈeɪ laɪn/", "meaning": "dáng chữ A", "example": "She chose an A-line skirt for the wedding."},
            {"word": "peplum", "ipa": "/ˈpep.ləm/", "meaning": "kiểu áo xòe ở eo", "example": "A peplum top creates an hourglass silhouette."},
            {"word": "midi", "ipa": "/ˈmɪd.i/", "meaning": "độ dài midi (đến bắp chân)", "example": "Midi skirts are a versatile and elegant choice."},
            {"word": "maxi", "ipa": "/ˈmæk.si/", "meaning": "váy/áo dài đến mắt cá", "example": "She wore a flowing maxi dress to the beach wedding."},
            {"word": "mini", "ipa": "/ˈmɪn.i/", "meaning": "váy/áo ngắn", "example": "Mini skirts were iconic in the 1960s fashion revolution."},
            {"word": "cropped", "ipa": "/krɒpt/", "meaning": "áo ngắn cắt gọn", "example": "She paired a cropped top with high-waisted trousers."},
            {"word": "oversized", "ipa": "/ˌəʊ.vəˈsaɪzd/", "meaning": "quá khổ, rộng thùng thình", "example": "Oversized blazers are a staple of contemporary streetwear."},
            {"word": "tailored", "ipa": "/ˈteɪ.ləd/", "meaning": "may đo vừa vặn, trang nhã", "example": "A tailored suit always looks professional and sharp."},
            {"word": "bespoke", "ipa": "/bɪˈspəʊk/", "meaning": "đặt may riêng theo yêu cầu", "example": "He had a bespoke suit made for his wedding day."},
            {"word": "off-the-rack", "ipa": "/ˌɒf.ðəˈræk/", "meaning": "quần áo may sẵn", "example": "She bought an off-the-rack blazer and had it altered."},
            {"word": "athleisure", "ipa": "/ˈæθ.liːʒ.ər/", "meaning": "phong cách thể thao-thời trang", "example": "Athleisure blends athletic wear with casual everyday fashion."},
            {"word": "streetwear", "ipa": "/ˈstriːt.weər/", "meaning": "thời trang đường phố", "example": "Brands like Supreme and Off-White dominate the streetwear market."},
            {"word": "boho", "ipa": "/ˈbəʊ.həʊ/", "meaning": "phong cách bohemian", "example": "She loves the boho style with flowy fabrics and earthy tones."},
            {"word": "minimalist fashion", "ipa": "/ˈmɪn.ɪ.mə.lɪst ˈfæʃ.ən/", "meaning": "thời trang tối giản", "example": "Her minimalist fashion choices focus on clean lines and neutral colors."},
            {"word": "maximalist fashion", "ipa": "/ˈmæk.sɪ.mə.lɪst ˈfæʃ.ən/", "meaning": "thời trang tối đa (nhiều màu, hoạ tiết)", "example": "Maximalist fashion embraces bold colors, prints, and accessories."},
            {"word": "gender-neutral fashion", "ipa": "/ˈdʒen.dər ˌnjuː.trəl ˈfæʃ.ən/", "meaning": "thời trang phi giới tính", "example": "Gender-neutral fashion challenges traditional clothing norms."},
            {"word": "androgynous style", "ipa": "/ænˈdrɒdʒ.ɪ.nəs staɪl/", "meaning": "phong cách lưỡng tính", "example": "She embraces an androgynous style with sharp suits and bold accessories."},
            {"word": "capsule wardrobe planning", "ipa": "/ˈkæp.sjuːl ˈwɔː.drəʊb ˈplæn.ɪŋ/", "meaning": "lên kế hoạch tủ đồ tối giản", "example": "Capsule wardrobe planning helps you dress better with fewer items."},
            {"word": "color theory (fashion)", "ipa": "/ˈkʌl.ər ˈθɪər.i/", "meaning": "lý thuyết màu sắc ứng dụng thời trang", "example": "Understanding color theory helps you create harmonious outfits."},
            {"word": "complementary colors", "ipa": "/ˌkɒm.plɪˈmen.tər.i ˈkʌl.ərz/", "meaning": "màu bổ trợ (tương phản)", "example": "Blue and orange are complementary colors that create a striking contrast."},
            {"word": "personal shopper", "ipa": "/ˈpɜː.sən.əl ˈʃɒp.ər/", "meaning": "người mua sắm cá nhân", "example": "She hired a personal shopper to help update her wardrobe."},
            {"word": "fashion stylist", "ipa": "/ˈfæʃ.ən ˈstaɪ.lɪst/", "meaning": "chuyên gia phong cách thời trang", "example": "The celebrity's fashion stylist chooses all her red-carpet outfits."},
            {"word": "fashion photographer", "ipa": "/ˈfæʃ.ən fəˈtɒɡ.rə.fər/", "meaning": "nhiếp ảnh gia thời trang", "example": "The fashion photographer worked with Vogue for 20 years."},
            {"word": "fashion week", "ipa": "/ˈfæʃ.ən wiːk/", "meaning": "tuần lễ thời trang", "example": "The four major fashion weeks are held in New York, London, Milan, and Paris."},
            {"word": "catwalk", "ipa": "/ˈkæt.wɔːk/", "meaning": "sàn trình diễn thời trang", "example": "The models walked the catwalk to showcase the new collection."},
            {"word": "sample sale", "ipa": "/ˈsɑːm.pəl seɪl/", "meaning": "bán hàng mẫu giảm giá", "example": "She got a designer dress at a fraction of the price at a sample sale."},
            {"word": "preloved", "ipa": "/ˌpriːˈlʌvd/", "meaning": "đồ đã qua sử dụng (mua lại)", "example": "She buys preloved luxury handbags to save money."},
            {"word": "thrift shop", "ipa": "/θrɪft ʃɒp/", "meaning": "cửa hàng đồ cũ từ thiện", "example": "She found a stunning vintage dress at the thrift shop for $5."},
            {"word": "fashion influencer", "ipa": "/ˈfæʃ.ən ˈɪn.fluː.ən.sər/", "meaning": "người ảnh hưởng về thời trang", "example": "She became a successful fashion influencer through her Instagram posts."},
            {"word": "outfit of the day (OOTD)", "ipa": "/ˈaʊt.fɪt əv ðə deɪ/", "meaning": "trang phục hôm nay", "example": "She posts her OOTD on Instagram every morning."},
            {"word": "fashion blogger", "ipa": "/ˈfæʃ.ən ˈblɒɡ.ər/", "meaning": "blogger thời trang", "example": "She started as a fashion blogger and grew to 1 million followers."},
            {"word": "subscription box (fashion)", "ipa": "/səbˈskrɪp.ʃən bɒks/", "meaning": "hộp quần áo đăng ký", "example": "She receives a monthly subscription box with curated clothing items."},
            {"word": "rental fashion", "ipa": "/ˈren.təl ˈfæʃ.ən/", "meaning": "thuê trang phục", "example": "Rental fashion services let you wear new outfits without buying."},
            {"word": "fashion archive", "ipa": "/ˈfæʃ.ən ˈɑː.kaɪv/", "meaning": "kho lưu trữ thời trang", "example": "Fashion archives preserve iconic looks for future generations."},
            {"word": "heritage brand", "ipa": "/ˈher.ɪ.tɪdʒ brænd/", "meaning": "thương hiệu lâu đời", "example": "Burberry and Chanel are iconic heritage brands."},
            {"word": "logomania", "ipa": "/ˌləʊ.ɡəʊˈmeɪ.ni.ə/", "meaning": "trào lưu khoe logo thương hiệu", "example": "Logomania returned as a major trend with visible brand logos on clothing."},
            {"word": "athleisure trend", "ipa": "/ˈæθ.liːʒ.ər trend/", "meaning": "xu hướng trang phục thể thao-thường nhật", "example": "The athleisure trend grew significantly during the work-from-home era."},
            {"word": "fashion tech", "ipa": "/ˈfæʃ.ən tek/", "meaning": "công nghệ ứng dụng trong thời trang", "example": "Fashion tech includes virtual fitting rooms and AI-powered recommendations."},
        ],
        "B2": [
            {"word": "deconstructivism (fashion)", "ipa": "/ˌdiː.kənˈstrʌk.tɪ.vɪ.zəm/", "meaning": "chủ nghĩa giải cấu trúc trong thời trang", "example": "Maison Margiela is known for its deconstructivism, exposing seams and linings."},
            {"word": "avant-garde fashion", "ipa": "/ˌæv.ɒ̃ˈɡɑːrd ˈfæʃ.ən/", "meaning": "thời trang tiên phong", "example": "Avant-garde fashion challenges conventions with experimental designs."},
            {"word": "fashion semiotics", "ipa": "/ˈfæʃ.ən ˌsem.iˈɒt.ɪks/", "meaning": "ký hiệu học thời trang", "example": "Fashion semiotics studies how clothing communicates social meaning."},
            {"word": "material culture", "ipa": "/məˈtɪər.i.əl ˈkʌl.tʃər/", "meaning": "văn hóa vật chất (thời trang học)", "example": "Fashion is a key component of material culture in every society."},
            {"word": "trickle-down theory (fashion)", "ipa": "/ˈtrɪk.əl daʊn ˈθɪər.i/", "meaning": "lý thuyết nhỏ giọt (xu hướng từ trên xuống)", "example": "The trickle-down theory suggests trends flow from elite fashion to mass market."},
            {"word": "trickle-up effect", "ipa": "/ˈtrɪk.əl ʌp ɪˈfekt/", "meaning": "xu hướng từ dưới lên (subculture)", "example": "The trickle-up effect occurs when street and subculture styles influence high fashion."},
            {"word": "fashion cycle", "ipa": "/ˈfæʃ.ən ˈsaɪ.kəl/", "meaning": "vòng chu kỳ thời trang", "example": "The fashion cycle describes how trends emerge, peak, and decline."},
            {"word": "micro-trend", "ipa": "/ˈmaɪ.krəʊ trend/", "meaning": "xu hướng nhỏ ngắn hạn", "example": "Micro-trends rise and fall quickly, driven by social media."},
            {"word": "macro-trend", "ipa": "/ˈmæk.rəʊ trend/", "meaning": "xu hướng lớn dài hạn", "example": "Sustainability is a macro-trend reshaping the entire fashion industry."},
            {"word": "fashion forecasting", "ipa": "/ˈfæʃ.ən ˈfɔː.kɑːst.ɪŋ/", "meaning": "dự báo xu hướng thời trang", "example": "Fashion forecasting agencies predict colors and styles up to two years ahead."},
            {"word": "WGSN", "ipa": "/ˌdʌb.əl.juː.dʒiːˌes.ˈen/", "meaning": "WGSN (công ty dự báo xu hướng thời trang)", "example": "WGSN is the world's leading fashion trend forecasting company."},
            {"word": "Pantone color of the year", "ipa": "/ˈpæn.tən ˈkʌl.ər əv ðə jɪər/", "meaning": "màu sắc của năm Pantone", "example": "The Pantone color of the year influences fashion, design, and marketing globally."},
            {"word": "textile innovation", "ipa": "/ˈteks.taɪl ˌɪn.əˈveɪ.ʃən/", "meaning": "đổi mới trong vải/chất liệu", "example": "Textile innovation has produced fabrics that regulate body temperature."},
            {"word": "bio-fabrication", "ipa": "/ˌbaɪ.əʊ.fæb.rɪˈkeɪ.ʃən/", "meaning": "chế tạo vải sinh học", "example": "Bio-fabrication grows materials from microorganisms for sustainable fashion."},
            {"word": "synthetic fiber", "ipa": "/ˈsɪn.θet.ɪk ˈfaɪ.bər/", "meaning": "sợi tổng hợp", "example": "Polyester and nylon are the most common synthetic fibers in fashion."},
            {"word": "microplastic pollution", "ipa": "/ˈmaɪ.krəʊˌplæs.tɪk pəˈluː.ʃən/", "meaning": "ô nhiễm vi nhựa (từ vải tổng hợp)", "example": "Washing synthetic fabrics releases microplastics into waterways."},
            {"word": "ethical supply chain", "ipa": "/ˈeθ.ɪ.kəl ˈsʌp.laɪ tʃeɪn/", "meaning": "chuỗi cung ứng đạo đức", "example": "Brands with an ethical supply chain ensure fair wages and safe conditions."},
            {"word": "garment worker rights", "ipa": "/ˈɡɑː.mənt ˈwɜː.kər raɪts/", "meaning": "quyền lợi công nhân may mặc", "example": "The Rana Plaza disaster highlighted garment worker rights globally."},
            {"word": "greenwashing (fashion)", "ipa": "/ˈɡriːn.wɒʃ.ɪŋ/", "meaning": "rửa xanh (giả mạo thân thiện môi trường)", "example": "Some brands are accused of greenwashing with superficial sustainability claims."},
            {"word": "circular fashion economy", "ipa": "/ˈsɜː.kjʊ.lər ˈfæʃ.ən ɪˈkɒn.ə.mi/", "meaning": "kinh tế thời trang tuần hoàn", "example": "A circular fashion economy eliminates waste by designing for recyclability."},
            {"word": "digital fashion", "ipa": "/ˈdɪdʒ.ɪ.təl ˈfæʃ.ən/", "meaning": "thời trang kỹ thuật số", "example": "Digital fashion creates clothing that exists only in virtual environments."},
            {"word": "virtual try-on", "ipa": "/ˈvɜː.tʃu.əl ˈtraɪ.ɒn/", "meaning": "thử đồ ảo", "example": "Virtual try-on technology lets shoppers see how clothes look without wearing them."},
            {"word": "augmented reality (fashion)", "ipa": "/ɔːɡˈmen.tɪd riˈæl.ɪ.ti/", "meaning": "thực tế tăng cường trong thời trang", "example": "Augmented reality allows customers to visualize outfits in real time."},
            {"word": "metaverse fashion", "ipa": "/ˈmet.ə.vɜːs ˈfæʃ.ən/", "meaning": "thời trang trong metaverse", "example": "Metaverse fashion lets avatars wear designer outfits in virtual worlds."},
            {"word": "NFT fashion", "ipa": "/ˌen.ef.ˈtiː ˈfæʃ.ən/", "meaning": "thời trang NFT", "example": "Luxury brands are releasing NFT fashion collections on the blockchain."},
            {"word": "resale market", "ipa": "/ˈriː.seɪl ˈmɑː.kɪt/", "meaning": "thị trường hàng secondhand", "example": "The fashion resale market has grown faster than traditional retail."},
            {"word": "deadstock (fashion)", "ipa": "/ˈded.stɒk/", "meaning": "vải tồn kho chưa dùng", "example": "Some designers use deadstock fabric to reduce waste."},
            {"word": "fashion conglomerate", "ipa": "/ˈfæʃ.ən kənˈɡlɒm.ər.ɪt/", "meaning": "tập đoàn thời trang lớn", "example": "LVMH is the world's largest luxury fashion conglomerate."},
            {"word": "luxury segment", "ipa": "/ˈlʌk.ʃər.i ˈseɡ.mənt/", "meaning": "phân khúc hàng xa xỉ", "example": "The luxury segment grew despite economic slowdowns."},
            {"word": "accessible luxury", "ipa": "/əkˈses.ɪ.bəl ˈlʌk.ʃər.i/", "meaning": "xa xỉ phổ thông", "example": "Brands like Michael Kors offer accessible luxury at mid-range prices."},
            {"word": "masstige", "ipa": "/ˈmæs.tɪdʒ/", "meaning": "prestige cho đại chúng (masstige)", "example": "Masstige brands like Coach combine mass appeal with prestige positioning."},
            {"word": "price anchoring (fashion)", "ipa": "/praɪs ˈæŋ.kər.ɪŋ/", "meaning": "neo giá (tâm lý định giá xa xỉ)", "example": "Luxury brands use price anchoring to signal quality and exclusivity."},
            {"word": "scarcity marketing", "ipa": "/ˈskeər.sɪ.ti ˈmɑː.kɪ.tɪŋ/", "meaning": "marketing khan hiếm", "example": "Scarcity marketing creates urgency and drives demand for limited-edition items."},
            {"word": "drop culture", "ipa": "/drɒp ˈkʌl.tʃər/", "meaning": "văn hóa ra hàng giới hạn", "example": "Supreme popularized drop culture with its weekly limited product releases."},
            {"word": "hype beast culture", "ipa": "/haɪp biːst ˈkʌl.tʃər/", "meaning": "văn hóa săn hàng hiệu hype", "example": "Hype beast culture drives demand for exclusive sneakers and streetwear."},
            {"word": "fashion law", "ipa": "/ˈfæʃ.ən lɔː/", "meaning": "luật bảo vệ quyền sở hữu thời trang", "example": "Fashion law covers intellectual property rights for designs and trademarks."},
            {"word": "design plagiarism", "ipa": "/dɪˈzaɪn ˈpleɪ.dʒər.ɪ.zəm/", "meaning": "đạo nhái thiết kế", "example": "Design plagiarism is a widespread problem in the fast fashion industry."},
            {"word": "trade dress", "ipa": "/treɪd dres/", "meaning": "bảo vệ phong cách thiết kế độc đáo", "example": "Trade dress protection covers a brand's distinctive visual identity."},
            {"word": "fashion collab", "ipa": "/ˈfæʃ.ən ˈkɒl.æb/", "meaning": "hợp tác thời trang", "example": "The H&M and Balmain fashion collab sold out within hours."},
            {"word": "capsule collaboration", "ipa": "/ˈkæp.sjuːl kəˌlæb.əˈreɪ.ʃən/", "meaning": "bộ sưu tập hợp tác giới hạn", "example": "The capsule collaboration between Uniqlo and Jil Sander was critically acclaimed."},
            {"word": "cross-category brand extension", "ipa": "/krɒs ˈkæt.ɪ.ɡər.i brænd ɪkˈsten.ʃən/", "meaning": "mở rộng thương hiệu sang danh mục khác", "example": "Gucci extended into home décor as a cross-category brand extension."},
            {"word": "fashion weeks (BIG 4)", "ipa": "/ˈfæʃ.ən wiːks bɪɡ fɔːr/", "meaning": "4 tuần lễ thời trang lớn", "example": "The Big 4 fashion weeks are held in New York, London, Milan, and Paris each season."},
            {"word": "resort collection", "ipa": "/rɪˈzɔːt kəˈlek.ʃən/", "meaning": "bộ sưu tập nghỉ dưỡng (giữa mùa)", "example": "Resort collections bridge the gap between main runway seasons."},
            {"word": "diffusion line", "ipa": "/dɪˈfjuː.ʒən laɪn/", "meaning": "dòng sản phẩm phổ thông của thương hiệu xa xỉ", "example": "Marc by Marc Jacobs was a diffusion line more affordable than the main collection."},
            {"word": "house codes (luxury)", "ipa": "/haʊs kəʊdz/", "meaning": "mã nhận dạng thương hiệu xa xỉ", "example": "A brand's house codes include recurring motifs, colors, and materials."},
            {"word": "fashion house", "ipa": "/ˈfæʃ.ən haʊs/", "meaning": "nhà mốt", "example": "Chanel is one of the most iconic fashion houses in the world."},
            {"word": "creative director", "ipa": "/kriˈeɪ.tɪv dɪˈrek.tər/", "meaning": "giám đốc sáng tạo", "example": "The new creative director completely transformed the brand's aesthetic."},
            {"word": "heritage craftsmanship", "ipa": "/ˈher.ɪ.tɪdʒ ˈkrɑːfts.mən.ʃɪp/", "meaning": "kỹ thuật thủ công truyền thống", "example": "Heritage craftsmanship is a core value of luxury brands like Hermès."},
            {"word": "exclusivity (fashion)", "ipa": "/ˌek.skluˈsɪv.ɪ.ti/", "meaning": "sự độc quyền, hiếm có", "example": "Exclusivity is a key pillar of the luxury fashion brand strategy."},
            {"word": "avant-garde fashion", "ipa": "/əˈvɑnˈgɑrd ˈfæʃən/", "meaning": "chủ nghĩa giải cấu trúc trong thời trang", "example": "Maison Margiela is known for its deconstructivism, exposing seams and linings."},
        ],
        "C1": [
            {"word": "fashion theory", "ipa": "/ˈfæʃ.ən ˈθɪər.i/", "meaning": "lý thuyết thời trang", "example": "Fashion theory explores the cultural, social, and economic dimensions of clothing."},
            {"word": "vestimentary code", "ipa": "/ˌves.tɪˈmen.tər.i kəʊd/", "meaning": "hệ thống quy tắc ăn mặc văn hóa", "example": "Barthes analyzed fashion through a vestimentary code of signs and meanings."},
            {"word": "Roland Barthes' fashion system", "ipa": "/ˈrəʊ.lænd ˈbɑːts ˈfæʃ.ən ˈsɪs.təm/", "meaning": "hệ thống thời trang của Roland Barthes", "example": "Barthes argued that written fashion creates an idealized, mythologized version of clothing."},
            {"word": "conspicuous consumption", "ipa": "/kənˌspɪk.juəs kənˈsʌmp.ʃən/", "meaning": "tiêu dùng phô trương (Veblen)", "example": "Veblen coined conspicuous consumption to describe luxury spending as status signaling."},
            {"word": "trickle-across theory", "ipa": "/ˈtrɪk.əl əˈkrɒs ˈθɪər.i/", "meaning": "lý thuyết lan ngang (xu hướng song song)", "example": "The trickle-across theory suggests trends spread simultaneously across social groups."},
            {"word": "fashion ecology", "ipa": "/ˈfæʃ.ən ɪˈkɒl.ə.dʒi/", "meaning": "sinh thái học thời trang", "example": "Fashion ecology examines the environmental impact of the fashion system."},
            {"word": "posthuman fashion", "ipa": "/ˌpəʊst.hjuːˈmæn ˈfæʃ.ən/", "meaning": "thời trang hậu nhân loại", "example": "Posthuman fashion explores the intersection of the body, technology, and identity."},
            {"word": "cyborg aesthetics", "ipa": "/ˈsaɪ.bɔːɡ esˈθet.ɪks/", "meaning": "thẩm mỹ cyborg", "example": "Cyborg aesthetics in fashion integrate technology into wearable design."},
            {"word": "fashion anthropology", "ipa": "/ˈfæʃ.ən ˌæn.θrəˈpɒl.ə.dʒi/", "meaning": "nhân học thời trang", "example": "Fashion anthropology studies how dress practices reflect cultural identity."},
            {"word": "embodiment theory (fashion)", "ipa": "/ɪmˈbɒd.i.mənt ˈθɪər.i/", "meaning": "lý thuyết thân thể (thời trang)", "example": "Embodiment theory examines how clothing shapes our experience of the body."},
            {"word": "Gilles Lipovetsky's fashion paradox", "ipa": "/ʒiːl ˌlɪp.əˈvet.skiz ˈfæʃ.ən ˈpær.ə.dɒks/", "meaning": "nghịch lý thời trang của Lipovetsky", "example": "Lipovetsky argues fashion is both a tool of social conformity and individual expression."},
            {"word": "fashion capital", "ipa": "/ˈfæʃ.ən ˈkæp.ɪ.təl/", "meaning": "trung tâm thời trang thế giới", "example": "Paris remains the undisputed global fashion capital."},
            {"word": "fashion geography", "ipa": "/ˈfæʃ.ən dʒiˈɒɡ.rə.fi/", "meaning": "địa lý thời trang", "example": "Fashion geography maps where trends are produced, distributed, and consumed."},
            {"word": "postcolonial fashion", "ipa": "/ˌpəʊst.kəˈləʊ.ni.əl ˈfæʃ.ən/", "meaning": "thời trang hậu thực dân", "example": "Postcolonial fashion reclaims and celebrates non-Western aesthetic traditions."},
            {"word": "cultural appropriation (fashion)", "ipa": "/ˈkʌl.tʃər.əl əˌprəʊ.priˈeɪ.ʃən/", "meaning": "chiếm đoạt văn hóa trong thời trang", "example": "Cultural appropriation in fashion involves borrowing from marginalized cultures without credit."},
            {"word": "decolonizing fashion", "ipa": "/ˌdiːˈkɒl.ə.naɪz.ɪŋ ˈfæʃ.ən/", "meaning": "phi thực dân hóa thời trang", "example": "Decolonizing fashion challenges Eurocentric beauty and design standards."},
            {"word": "fashion ethics", "ipa": "/ˈfæʃ.ən ˈeθ.ɪks/", "meaning": "đạo đức thời trang", "example": "Fashion ethics encompasses labor rights, environmental impact, and cultural respect."},
            {"word": "body positivity movement", "ipa": "/ˈbɒd.i ˌpɒz.ɪˈtɪv.ɪ.ti ˈmuːv.mənt/", "meaning": "phong trào yêu cơ thể", "example": "The body positivity movement pushes fashion to include diverse sizes and shapes."},
            {"word": "size inclusivity", "ipa": "/saɪz ɪnˌkluː.ˈsɪv.ɪ.ti/", "meaning": "bao gồm mọi kích cỡ", "example": "Size inclusivity in fashion ensures clothing is available for all body types."},
            {"word": "disability fashion", "ipa": "/dɪsəˈbɪl.ɪ.ti ˈfæʃ.ən/", "meaning": "thời trang cho người khuyết tật", "example": "Disability fashion designs adaptive clothing for people with physical limitations."},
            {"word": "adaptive clothing", "ipa": "/əˈdæp.tɪv ˈkləʊ.ðɪŋ/", "meaning": "quần áo thích ứng (cho người khuyết tật)", "example": "Adaptive clothing features magnetic fasteners and open-back designs for ease of use."},
            {"word": "fashion psychology", "ipa": "/ˈfæʃ.ən saɪˈkɒl.ə.dʒi/", "meaning": "tâm lý học thời trang", "example": "Fashion psychology studies how clothing affects mood, behavior, and perception."},
            {"word": "enclothed cognition", "ipa": "/ɪnˈkləʊðd kɒɡˈnɪʃ.ən/", "meaning": "nhận thức được định hình bởi trang phục", "example": "Enclothed cognition research shows that wearing a lab coat improves attention."},
            {"word": "symbolic interactionism (fashion)", "ipa": "/ˌsɪm.bɒl.ɪk ˌɪn.tərˈæk.ʃən.ɪ.zəm/", "meaning": "chủ nghĩa tương tác biểu tượng (thời trang)", "example": "Symbolic interactionism explains how clothing creates shared social meanings."},
            {"word": "fashion as resistance", "ipa": "/ˈfæʃ.ən əz rɪˈzɪs.təns/", "meaning": "thời trang như một hình thức kháng cự", "example": "Fashion as resistance is evident in punk, feminism, and LGBTQ+ movements."},
            {"word": "subversive fashion", "ipa": "/səbˈvɜː.sɪv ˈfæʃ.ən/", "meaning": "thời trang đảo lộn, phá vỡ chuẩn mực", "example": "Vivienne Westwood's subversive fashion challenged social norms through provocative designs."},
            {"word": "spectacle (fashion theory)", "ipa": "/ˈspek.tə.kəl/", "meaning": "cảnh tượng (lý thuyết thời trang Debord)", "example": "Debord's concept of the spectacle applies to fashion shows as theatrical performance."},
            {"word": "brand equity (fashion)", "ipa": "/brænd ˈek.wɪ.ti/", "meaning": "giá trị thương hiệu thời trang", "example": "Chanel's brand equity is built on heritage, quality, and consistent aesthetic identity."},
            {"word": "fashion museology", "ipa": "/ˈfæʃ.ən ˌmjuː.ziˈɒl.ə.dʒi/", "meaning": "bảo tàng học thời trang", "example": "Fashion museology explores how exhibitions curate and present historic garments."},
            {"word": "dress history", "ipa": "/dres ˈhɪs.tər.i/", "meaning": "lịch sử trang phục", "example": "Dress history documents how clothing has evolved across cultures and centuries."},
            {"word": "fashion archives preservation", "ipa": "/ˈfæʃ.ən ˈɑː.kaɪvz ˌprez.əˈveɪ.ʃən/", "meaning": "bảo tồn kho lưu trữ thời trang", "example": "Fashion archives preservation ensures iconic garments survive for research and display."},
            {"word": "fashion epistemology", "ipa": "/ˈfæʃ.ən ɪˌpɪs.tɪˈmɒl.ə.dʒi/", "meaning": "nhận thức luận thời trang", "example": "Fashion epistemology questions what constitutes knowledge in the field of dress studies."},
            {"word": "transnational fashion", "ipa": "/ˌtræns.ˈnæʃ.ən.əl ˈfæʃ.ən/", "meaning": "thời trang xuyên quốc gia", "example": "Transnational fashion flows blur the boundaries of national style identities."},
            {"word": "glocalization (fashion)", "ipa": "/ˌɡlɒk.əl.aɪˈzeɪ.ʃən/", "meaning": "địa phương hóa toàn cầu trong thời trang", "example": "Glocalization in fashion adapts global trends to local cultural preferences."},
            {"word": "fashion activism", "ipa": "/ˈfæʃ.ən ˈæk.tɪ.vɪ.zəm/", "meaning": "chủ nghĩa hành động thời trang", "example": "Fashion activism uses clothing to promote political or social messages."},
            {"word": "speculative fashion", "ipa": "/ˈspek.jʊ.lə.tɪv ˈfæʃ.ən/", "meaning": "thời trang đầu cơ/tương lai", "example": "Speculative fashion imagines future dress in response to climate change and technology."},
            {"word": "biomimicry in fashion", "ipa": "/ˌbaɪ.əʊˈmɪm.ɪ.kri ɪn ˈfæʃ.ən/", "meaning": "mô phỏng sinh học trong thời trang", "example": "Biomimicry in fashion draws inspiration from natural structures like shells and wings."},
            {"word": "zero-waste pattern making", "ipa": "/ˈzɪər.əʊ weɪst ˈpæt.ən ˌmeɪ.kɪŋ/", "meaning": "cắt may không lãng phí vải", "example": "Zero-waste pattern making designs garments that use every piece of fabric."},
            {"word": "fashion futures studies", "ipa": "/ˈfæʃ.ən ˈfjuː.tʃərz ˈstʌd.iz/", "meaning": "nghiên cứu tương lai thời trang", "example": "Fashion futures studies projects how the industry will evolve over the next 50 years."},
            {"word": "phenomenology of dress", "ipa": "/fɪˌnɒm.ɪˈnɒl.ə.dʒi əv dres/", "meaning": "hiện tượng học trang phục", "example": "The phenomenology of dress investigates the lived experience of wearing clothes."},
            {"word": "queer fashion theory", "ipa": "/kwɪər ˈfæʃ.ən ˈθɪər.i/", "meaning": "lý thuyết thời trang queer", "example": "Queer fashion theory examines how dress challenges heteronormative gender norms."},
            {"word": "trans* fashion", "ipa": "/træns ˈfæʃ.ən/", "meaning": "thời trang trans", "example": "Trans* fashion designers are creating clothing for gender non-conforming bodies."},
            {"word": "intersectional fashion studies", "ipa": "/ˌɪn.tə.ˈsek.ʃən.əl ˈfæʃ.ən ˈstʌd.iz/", "meaning": "nghiên cứu thời trang liên chiều", "example": "Intersectional fashion studies examines how race, class, and gender shape dress."},
            {"word": "fashion ontology", "ipa": "/ˈfæʃ.ən ɒnˈtɒl.ə.dʒi/", "meaning": "bản thể luận thời trang", "example": "Fashion ontology asks fundamental questions about the nature of clothing as an object."},
            {"word": "temporal aesthetics", "ipa": "/ˈtem.pər.əl esˈθet.ɪks/", "meaning": "thẩm mỹ thời gian (thời trang)", "example": "Temporal aesthetics in fashion explores how clothing encodes time, memory, and nostalgia."},
            {"word": "haptic fashion", "ipa": "/ˈhæp.tɪk ˈfæʃ.ən/", "meaning": "thời trang xúc giác", "example": "Haptic fashion uses texture and tactile sensation as its primary design language."},
            {"word": "olfactory fashion", "ipa": "/ɒlˈfæk.tər.i ˈfæʃ.ən/", "meaning": "thời trang khứu giác (mùi hương trong thiết kế)", "example": "Olfactory fashion incorporates scent into garments for multisensory experience."},
            {"word": "relational dressing", "ipa": "/rɪˈleɪ.ʃən.əl ˈdres.ɪŋ/", "meaning": "ăn mặc dựa trên quan hệ xã hội", "example": "Relational dressing considers how clothing choices affect social interactions."},
            {"word": "fashion manifesto", "ipa": "/ˈfæʃ.ən ˌmæn.ɪˈfes.təʊ/", "meaning": "tuyên ngôn thời trang", "example": "The designer's fashion manifesto called for a radical revaluation of beauty standards."},
            {"word": "style philosophy", "ipa": "/staɪl fəˈlɑsəfi/", "meaning": "lý thuyết thời trang", "example": "Fashion theory explores the cultural, social, and economic dimensions of clothing."},
        ],
    },
    "finance": {
        "A1": [
            {"word": "money", "ipa": "/ˈmʌn.i/", "meaning": "tiền", "example": "She saves money every month for her vacation."},
            {"word": "buy", "ipa": "/baɪ/", "meaning": "mua", "example": "I want to buy a new phone next month."},
            {"word": "sell", "ipa": "/sel/", "meaning": "bán", "example": "He decided to sell his car to pay for his studies."},
            {"word": "pay", "ipa": "/peɪ/", "meaning": "thanh toán, trả tiền", "example": "Can I pay by credit card?"},
            {"word": "cost", "ipa": "/kɒst/", "meaning": "giá cả", "example": "How much does this product cost?"},
            {"word": "price", "ipa": "/praɪs/", "meaning": "giá", "example": "The price of this jacket is too high for me."},
            {"word": "save", "ipa": "/seɪv/", "meaning": "tiết kiệm", "example": "I try to save at least 20% of my income every month."},
            {"word": "bank", "ipa": "/bæŋk/", "meaning": "ngân hàng", "example": "She opened a savings account at the bank."},
            {"word": "cash", "ipa": "/kæʃ/", "meaning": "tiền mặt", "example": "Do you have enough cash to pay for the meal?"},
            {"word": "card", "ipa": "/kɑːd/", "meaning": "thẻ ngân hàng", "example": "She paid for the groceries with her debit card."},
            {"word": "spend", "ipa": "/spend/", "meaning": "chi tiêu", "example": "I try not to spend too much on clothes."},
            {"word": "cheap", "ipa": "/tʃiːp/", "meaning": "rẻ", "example": "This supermarket is cheap compared to others."},
            {"word": "expensive", "ipa": "/ɪkˈspen.sɪv/", "meaning": "đắt tiền", "example": "The restaurant is too expensive for us to eat there every week."},
            {"word": "free", "ipa": "/friː/", "meaning": "miễn phí", "example": "The museum is free to enter on Sundays."},
            {"word": "discount", "ipa": "/ˈdɪs.kaʊnt/", "meaning": "giảm giá", "example": "The store is offering a 20% discount on all shoes."},
            {"word": "sale", "ipa": "/seɪl/", "meaning": "đợt giảm giá", "example": "I bought a coat in the winter sale."},
            {"word": "receipt", "ipa": "/rɪˈsiːt/", "meaning": "hóa đơn", "example": "Keep the receipt in case you want to return the item."},
            {"word": "change", "ipa": "/tʃeɪndʒ/", "meaning": "tiền thối lại", "example": "Here is your change — $5 back from $20."},
            {"word": "wallet", "ipa": "/ˈwɒl.ɪt/", "meaning": "ví tiền", "example": "He lost his wallet with all his cards inside."},
            {"word": "coin", "ipa": "/kɔɪn/", "meaning": "đồng xu", "example": "She found a few coins in her coat pocket."},
            {"word": "bill", "ipa": "/bɪl/", "meaning": "tờ tiền; hóa đơn", "example": "She paid the electricity bill online this month."},
            {"word": "account", "ipa": "/əˈkaʊnt/", "meaning": "tài khoản ngân hàng", "example": "I have a savings account and a checking account."},
            {"word": "loan", "ipa": "/ləʊn/", "meaning": "khoản vay", "example": "He took out a loan to buy his first car."},
            {"word": "borrow", "ipa": "/ˈbɒr.əʊ/", "meaning": "vay mượn", "example": "Can I borrow 50 dollars until next week?"},
            {"word": "rent", "ipa": "/rent/", "meaning": "tiền thuê nhà/xe", "example": "She pays 500 dollars in rent every month."},
            {"word": "income", "ipa": "/ˈɪŋ.kʌm/", "meaning": "thu nhập", "example": "His monthly income is enough to cover all expenses."},
            {"word": "tax", "ipa": "/tæks/", "meaning": "thuế", "example": "Everyone must pay income tax every year."},
            {"word": "salary", "ipa": "/ˈsæl.ər.i/", "meaning": "lương tháng", "example": "Her salary increased after her promotion."},
            {"word": "wage", "ipa": "/weɪdʒ/", "meaning": "tiền công (theo giờ/ngày)", "example": "He earns minimum wage at his part-time job."},
            {"word": "invest", "ipa": "/ɪnˈvest/", "meaning": "đầu tư", "example": "She decided to invest in stocks for the long term."},
            {"word": "profit", "ipa": "/ˈprɒf.ɪt/", "meaning": "lợi nhuận", "example": "The shop made a good profit last year."},
            {"word": "loss", "ipa": "/lɒs/", "meaning": "lỗ, thua lỗ", "example": "The business suffered a loss during the pandemic."},
            {"word": "debt", "ipa": "/det/", "meaning": "nợ", "example": "It took him five years to pay off his debt."},
            {"word": "transfer", "ipa": "/ˈtræns.fɜːr/", "meaning": "chuyển khoản", "example": "I will transfer the money to your account tonight."},
            {"word": "withdraw", "ipa": "/wɪðˈdrɔː/", "meaning": "rút tiền", "example": "She withdrew $200 from the ATM."},
            {"word": "deposit", "ipa": "/dɪˈpɒz.ɪt/", "meaning": "gửi tiền vào tài khoản", "example": "He deposited his salary into his savings account."},
            {"word": "ATM", "ipa": "/ˌeɪ.tiːˈem/", "meaning": "máy rút tiền tự động", "example": "She used the ATM to get some cash."},
            {"word": "interest", "ipa": "/ˈɪn.trəst/", "meaning": "lãi suất; tiền lãi", "example": "The bank pays 3% interest on savings accounts."},
            {"word": "budget", "ipa": "/ˈbʌdʒ.ɪt/", "meaning": "ngân sách", "example": "We need to stay within our monthly budget."},
            {"word": "exchange rate", "ipa": "/ɪksˈtʃeɪndʒ reɪt/", "meaning": "tỷ giá hối đoái", "example": "Check the exchange rate before converting your money."},
            {"word": "currency", "ipa": "/ˈkʌr.ən.si/", "meaning": "tiền tệ", "example": "The US dollar is the world's most traded currency."},
            {"word": "checkout", "ipa": "/ˈtʃek.aʊt/", "meaning": "thanh toán (tại quầy)", "example": "Please go to the checkout to pay for your items."},
            {"word": "transaction", "ipa": "/trænˈzækʃən/", "meaning": "Giao dịch tài chính", "example": "The bank recorded every transaction in its system."},
            {"word": "fee", "ipa": "/fiː/", "meaning": "phí dịch vụ", "example": "There is a small fee for using the ATM abroad."},
            {"word": "credit", "ipa": "/ˈkred.ɪt/", "meaning": "tín dụng", "example": "She has a good credit score, so she got a loan easily."},
            {"word": "debit", "ipa": "/ˈdeb.ɪt/", "meaning": "ghi nợ (trừ tiền từ tài khoản)", "example": "The payment was debited directly from her bank account."},
            {"word": "financial", "ipa": "/faɪˈnæn.ʃəl/", "meaning": "tài chính (tính từ)", "example": "She is worried about her financial situation."},
            {"word": "rich", "ipa": "/rɪtʃ/", "meaning": "giàu có", "example": "He became rich after starting a successful business."},
            {"word": "poor", "ipa": "/pɔːr/", "meaning": "nghèo", "example": "Growing up poor motivated him to work hard and succeed."},
            {"word": "afford", "ipa": "/əˈfɔːd/", "meaning": "đủ khả năng mua", "example": "I cannot afford to buy a new car right now."},
        ],
        "A2": [
            {"word": "budget", "ipa": "/ˈbʌdʒ.ɪt/", "meaning": "lập ngân sách", "example": "She creates a monthly budget to track her spending."},
            {"word": "mortgage", "ipa": "/ˈmɔː.ɡɪdʒ/", "meaning": "vay thế chấp mua nhà", "example": "They took out a 30-year mortgage to buy their home."},
            {"word": "insurance", "ipa": "/ɪnˈʃʊər.əns/", "meaning": "bảo hiểm", "example": "Car insurance is required by law in most countries."},
            {"word": "premium", "ipa": "/ˈpriː.mi.əm/", "meaning": "phí bảo hiểm", "example": "She pays a monthly premium for her health insurance."},
            {"word": "claim", "ipa": "/kleɪm/", "meaning": "yêu cầu bồi thường bảo hiểm", "example": "She filed an insurance claim after the accident."},
            {"word": "pension", "ipa": "/ˈpen.ʃən/", "meaning": "lương hưu", "example": "He has been contributing to his pension fund for 20 years."},
            {"word": "retirement", "ipa": "/rɪˈtaɪər.mənt/", "meaning": "về hưu", "example": "She plans to retire at 60 with a comfortable savings."},
            {"word": "stock", "ipa": "/stɒk/", "meaning": "cổ phiếu", "example": "She invested in tech stocks and made a good return."},
            {"word": "share", "ipa": "/ʃeər/", "meaning": "cổ phần", "example": "He bought 100 shares of the company at $10 each."},
            {"word": "bond", "ipa": "/bɒnd/", "meaning": "trái phiếu", "example": "Government bonds are considered a safe investment."},
            {"word": "fund", "ipa": "/fʌnd/", "meaning": "quỹ đầu tư", "example": "She invested in a mutual fund diversified across sectors."},
            {"word": "portfolio", "ipa": "/pɔːtˈfəʊ.li.əʊ/", "meaning": "danh mục đầu tư", "example": "A diversified portfolio helps manage investment risk."},
            {"word": "return", "ipa": "/rɪˈtɜːn/", "meaning": "lợi nhuận đầu tư", "example": "The investment generated a 10% annual return."},
            {"word": "risk", "ipa": "/rɪsk/", "meaning": "rủi ro tài chính", "example": "Higher returns usually come with higher financial risk."},
            {"word": "asset", "ipa": "/ˈæs.et/", "meaning": "tài sản", "example": "Her house and car are her main assets."},
            {"word": "liability", "ipa": "/ˌlaɪ.əˈbɪl.ɪ.ti/", "meaning": "khoản nợ phải trả", "example": "Student loans are a significant financial liability."},
            {"word": "net worth", "ipa": "/net wɜːθ/", "meaning": "tài sản ròng", "example": "Her net worth increased significantly after selling the property."},
            {"word": "inflation", "ipa": "/ɪnˈfleɪ.ʃən/", "meaning": "lạm phát", "example": "Inflation erodes the purchasing power of money over time."},
            {"word": "deflation", "ipa": "/dɪˈfleɪ.ʃən/", "meaning": "giảm phát", "example": "Deflation can reduce consumer spending and slow growth."},
            {"word": "GDP", "ipa": "/ˌdʒiː.diːˈpiː/", "meaning": "tổng sản phẩm nội địa", "example": "GDP measures the total value of goods produced in a country."},
            {"word": "recession", "ipa": "/rɪˈseʃ.ən/", "meaning": "suy thoái kinh tế", "example": "The country entered a recession after two quarters of negative growth."},
            {"word": "credit card", "ipa": "/ˈkred.ɪt kɑːd/", "meaning": "thẻ tín dụng", "example": "She uses her credit card for online shopping."},
            {"word": "interest rate", "ipa": "/ˈɪn.trəst reɪt/", "meaning": "lãi suất", "example": "Low interest rates encourage borrowing and investment."},
            {"word": "minimum payment", "ipa": "/ˈmɪn.ɪ.məm ˈpeɪ.mənt/", "meaning": "thanh toán tối thiểu", "example": "Always pay more than the minimum payment on your credit card."},
            {"word": "overdraft", "ipa": "/ˈəʊ.vər.drɑːft/", "meaning": "thấu chi tài khoản", "example": "She accidentally went into overdraft and had to pay a fee."},
            {"word": "balance", "ipa": "/ˈbæl.əns/", "meaning": "số dư tài khoản", "example": "Check your account balance before making a large purchase."},
            {"word": "statement", "ipa": "/ˈsteɪt.mənt/", "meaning": "sao kê tài khoản", "example": "She reviews her bank statement every month."},
            {"word": "financial goal", "ipa": "/faɪˈnæn.ʃəl ɡəʊl/", "meaning": "mục tiêu tài chính", "example": "Her financial goal is to save for a house deposit."},
            {"word": "emergency fund", "ipa": "/ɪˈmɜː.dʒən.si fʌnd/", "meaning": "quỹ khẩn cấp", "example": "Keep an emergency fund of three to six months' expenses."},
            {"word": "compound interest", "ipa": "/ˈkɒm.paʊnd ˈɪn.trəst/", "meaning": "lãi kép", "example": "Compound interest makes your savings grow faster over time."},
            {"word": "financial literacy", "ipa": "/faɪˈnæn.ʃəl ˈlɪt.ər.ə.si/", "meaning": "hiểu biết tài chính", "example": "Financial literacy helps people make better money decisions."},
            {"word": "credit score", "ipa": "/ˈkred.ɪt skɔːr/", "meaning": "điểm tín dụng", "example": "A high credit score helps you get lower interest rates."},
            {"word": "investment", "ipa": "/ɪnˈvest.mənt/", "meaning": "đầu tư", "example": "Real estate is a popular long-term investment."},
            {"word": "dividend", "ipa": "/ˈdɪv.ɪ.dend/", "meaning": "cổ tức", "example": "She received a quarterly dividend from her stock holdings."},
            {"word": "capital", "ipa": "/ˈkæp.ɪ.təl/", "meaning": "vốn", "example": "The startup needs more capital to expand."},
            {"word": "savings account", "ipa": "/ˈseɪ.vɪŋz əˌkaʊnt/", "meaning": "tài khoản tiết kiệm", "example": "A savings account earns interest on your deposited money."},
            {"word": "checking account", "ipa": "/ˈtʃek.ɪŋ əˌkaʊnt/", "meaning": "tài khoản thanh toán", "example": "She uses her checking account for daily expenses."},
            {"word": "wire transfer", "ipa": "/waɪər ˈtræns.fɜːr/", "meaning": "chuyển khoản điện tử", "example": "She sent money overseas via wire transfer."},
            {"word": "financial advisor", "ipa": "/faɪˈnæn.ʃəl ədˈvaɪ.zər/", "meaning": "cố vấn tài chính", "example": "A financial advisor helped her plan for retirement."},
            {"word": "tax return", "ipa": "/tæks rɪˈtɜːn/", "meaning": "khai thuế thu nhập", "example": "She filed her tax return before the April deadline."},
            {"word": "tax deduction", "ipa": "/tæks dɪˈdʌk.ʃən/", "meaning": "khấu trừ thuế", "example": "Charitable donations qualify as a tax deduction."},
            {"word": "VAT", "ipa": "/væt/", "meaning": "thuế giá trị gia tăng", "example": "The price includes 10% VAT."},
            {"word": "net income", "ipa": "/net ˈɪŋ.kʌm/", "meaning": "thu nhập ròng (sau thuế)", "example": "His net income after tax is $3,000 per month."},
            {"word": "gross income", "ipa": "/ɡrəʊs ˈɪŋ.kʌm/", "meaning": "tổng thu nhập (trước thuế)", "example": "Her gross income is $50,000 per year."},
            {"word": "payslip", "ipa": "/ˈpeɪ.slɪp/", "meaning": "phiếu lương", "example": "The payslip shows all deductions from the monthly salary."},
            {"word": "expenditure", "ipa": "/ɪkˈspen.dɪ.tʃər/", "meaning": "chi tiêu", "example": "Total government expenditure increased by 5% this year."},
            {"word": "fixed expense", "ipa": "/fɪkst ɪkˈspens/", "meaning": "chi phí cố định", "example": "Rent is a fixed expense that stays the same each month."},
            {"word": "variable expense", "ipa": "/ˈveər.i.ə.bəl ɪkˈspens/", "meaning": "chi phí biến đổi", "example": "Food and entertainment are variable expenses."},
            {"word": "financial freedom", "ipa": "/faɪˈnæn.ʃəl ˈfriː.dəm/", "meaning": "tự do tài chính", "example": "She is working towards financial freedom by investing regularly."},
            {"word": "passive income", "ipa": "/ˈpæs.ɪv ˈɪŋ.kʌm/", "meaning": "thu nhập thụ động", "example": "Rental properties provide passive income with minimal effort."},
        ],
        "B1": [
            {"word": "asset allocation", "ipa": "/ˈæs.et ˌæl.əˈkeɪ.ʃən/", "meaning": "phân bổ tài sản đầu tư", "example": "Smart asset allocation balances risk across stocks, bonds, and real estate."},
            {"word": "diversification", "ipa": "/daɪˌvɜː.sɪ.fɪˈkeɪ.ʃən/", "meaning": "đa dạng hóa danh mục đầu tư", "example": "Diversification reduces risk by spreading investments across different sectors."},
            {"word": "liquidity", "ipa": "/lɪˈkwɪd.ɪ.ti/", "meaning": "tính thanh khoản", "example": "Cash is the most liquid asset you can hold."},
            {"word": "mutual fund", "ipa": "/ˈmjuː.tʃu.əl fʌnd/", "meaning": "quỹ tương hỗ", "example": "A mutual fund pools money from many investors to buy a diversified portfolio."},
            {"word": "index fund", "ipa": "/ˈɪn.deks fʌnd/", "meaning": "quỹ chỉ số", "example": "An index fund tracks a market index like the S&P 500."},
            {"word": "ETF (Exchange-Traded Fund)", "ipa": "/ˌiː.tiːˈef/", "meaning": "quỹ giao dịch trên sàn", "example": "ETFs combine the benefits of mutual funds and individual stocks."},
            {"word": "bull market", "ipa": "/bʊl ˈmɑː.kɪt/", "meaning": "thị trường tăng giá", "example": "Stock prices rose sharply during the bull market."},
            {"word": "bear market", "ipa": "/beər ˈmɑː.kɪt/", "meaning": "thị trường giảm giá", "example": "Many investors sold their stocks during the bear market."},
            {"word": "market correction", "ipa": "/ˈmɑː.kɪt kəˈrek.ʃən/", "meaning": "điều chỉnh thị trường", "example": "A 10% drop in stock prices is considered a market correction."},
            {"word": "dollar-cost averaging", "ipa": "/ˈdɒl.ər kɒst ˈæv.ər.ɪ.dʒɪŋ/", "meaning": "mua định kỳ trung bình giá", "example": "Dollar-cost averaging reduces the impact of market volatility on investments."},
            {"word": "rebalancing", "ipa": "/ˌriːˈbæl.əns.ɪŋ/", "meaning": "tái cân bằng danh mục", "example": "Annual rebalancing keeps your portfolio aligned with your target allocation."},
            {"word": "capital gains tax", "ipa": "/ˈkæp.ɪ.təl ɡeɪnz tæks/", "meaning": "thuế lãi vốn", "example": "Capital gains tax applies when you sell an asset for more than you paid."},
            {"word": "tax-advantaged account", "ipa": "/tæks ədˈvɑːn.tɪdʒd əˈkaʊnt/", "meaning": "tài khoản ưu đãi thuế", "example": "A 401(k) is a tax-advantaged account for retirement savings."},
            {"word": "net asset value", "ipa": "/net ˈæs.et ˈvæl.juː/", "meaning": "giá trị tài sản ròng", "example": "The net asset value of the fund increased by 12% this year."},
            {"word": "expense ratio", "ipa": "/ɪkˈspens ˈreɪ.ʃi.əʊ/", "meaning": "tỷ lệ chi phí quản lý quỹ", "example": "Choose funds with a low expense ratio to maximize returns."},
            {"word": "brokerage account", "ipa": "/ˈbrəʊ.kər.ɪdʒ əˈkaʊnt/", "meaning": "tài khoản môi giới chứng khoán", "example": "You need a brokerage account to buy and sell stocks."},
            {"word": "stock exchange", "ipa": "/stɒk ɪksˈtʃeɪndʒ/", "meaning": "sàn giao dịch chứng khoán", "example": "She bought shares listed on the New York Stock Exchange."},
            {"word": "market capitalization", "ipa": "/ˈmɑː.kɪt ˌkæp.ɪ.t.əl.aɪˈzeɪ.ʃən/", "meaning": "vốn hóa thị trường", "example": "Large-cap companies have a market capitalization over $10 billion."},
            {"word": "P/E ratio", "ipa": "/piː tuː ˈɜː.nɪŋz ˈreɪ.ʃi.əʊ/", "meaning": "tỷ lệ giá/lợi nhuận", "example": "A low P/E ratio may indicate an undervalued stock."},
            {"word": "earnings per share", "ipa": "/ˈɜː.nɪŋz pər ʃeər/", "meaning": "lợi nhuận trên mỗi cổ phần", "example": "Rising earnings per share signal a healthy and growing company."},
            {"word": "fundamental analysis", "ipa": "/ˌfʌn.dəˈmen.təl əˈnæl.ɪ.sɪs/", "meaning": "phân tích cơ bản", "example": "Fundamental analysis evaluates a company's financials to determine its intrinsic value."},
            {"word": "technical analysis", "ipa": "/ˈtek.nɪ.kəl əˈnæl.ɪ.sɪs/", "meaning": "phân tích kỹ thuật", "example": "Technical analysis uses price charts and patterns to predict future movements."},
            {"word": "short selling", "ipa": "/ʃɔːt ˈsel.ɪŋ/", "meaning": "bán khống", "example": "Short selling profits when a stock's price falls."},
            {"word": "margin trading", "ipa": "/ˈmɑː.dʒɪn ˈtreɪ.dɪŋ/", "meaning": "giao dịch ký quỹ", "example": "Margin trading amplifies returns but also increases risk of loss."},
            {"word": "options trading", "ipa": "/ˈɒp.ʃənz ˈtreɪ.dɪŋ/", "meaning": "giao dịch quyền chọn", "example": "Options trading allows investors to hedge against market movements."},
            {"word": "futures contract", "ipa": "/ˈfjuː.tʃərz ˈkɒn.trækt/", "meaning": "hợp đồng tương lai", "example": "Farmers use futures contracts to lock in crop prices in advance."},
            {"word": "commodity", "ipa": "/kəˈmɒd.ɪ.ti/", "meaning": "hàng hóa (đầu tư)", "example": "Gold and oil are popular commodity investments."},
            {"word": "real estate investment", "ipa": "/rɪəl ɪˈsteɪt ɪnˈvest.mənt/", "meaning": "đầu tư bất động sản", "example": "Real estate investment provides both income and capital appreciation."},
            {"word": "cryptocurrency", "ipa": "/ˈkrɪp.təʊˌkʌr.ən.si/", "meaning": "tiền điện tử", "example": "Bitcoin is the world's most well-known cryptocurrency."},
            {"word": "blockchain", "ipa": "/ˈblɒk.tʃeɪn/", "meaning": "chuỗi khối (công nghệ)", "example": "Blockchain technology underpins most cryptocurrencies."},
            {"word": "fintech", "ipa": "/ˈfɪn.tek/", "meaning": "công nghệ tài chính", "example": "Fintech companies are disrupting traditional banking with innovative solutions."},
            {"word": "robo-advisor", "ipa": "/ˌrəʊ.bəʊ ədˈvaɪ.zər/", "meaning": "cố vấn đầu tư tự động", "example": "A robo-advisor automatically manages your investments based on your goals."},
            {"word": "financial planning", "ipa": "/faɪˈnæn.ʃəl ˈplæn.ɪŋ/", "meaning": "lập kế hoạch tài chính", "example": "Financial planning helps you achieve your short and long-term money goals."},
            {"word": "estate planning", "ipa": "/ɪˈsteɪt ˈplæn.ɪŋ/", "meaning": "lập kế hoạch di sản", "example": "Estate planning involves creating a will and designating beneficiaries."},
            {"word": "will (legal)", "ipa": "/wɪl (ˈligəl)/", "meaning": "di chúc", "example": "She updated her will to include her new grandchildren."},
            {"word": "trust fund", "ipa": "/trʌst fʌnd/", "meaning": "quỹ tín thác", "example": "The parents set up a trust fund for their children's education."},
            {"word": "bankruptcy", "ipa": "/ˈbæŋk.rʌp.si/", "meaning": "phá sản", "example": "The company filed for bankruptcy after years of losses."},
            {"word": "insolvency", "ipa": "/ɪnˈsɒl.vən.si/", "meaning": "mất khả năng thanh toán", "example": "Insolvency means a company cannot meet its financial obligations."},
            {"word": "cash reserve", "ipa": "/kæʃ rɪˈzɜːv/", "meaning": "dự trữ tiền mặt", "example": "A healthy cash reserve protects businesses during economic downturns."},
            {"word": "working capital management", "ipa": "/ˈwɜː.kɪŋ ˈkæp.ɪ.təl ˈmæn.ɪdʒ.mənt/", "meaning": "quản lý vốn lưu động", "example": "Efficient working capital management ensures smooth daily operations."},
            {"word": "accounts receivable", "ipa": "/əˈkaʊnts rɪˈsiː.və.bəl/", "meaning": "khoản phải thu", "example": "Accelerating accounts receivable collection improves cash flow."},
            {"word": "accounts payable", "ipa": "/əˈkaʊnts ˈpeɪ.ə.bəl/", "meaning": "khoản phải trả", "example": "Managing accounts payable efficiently maintains supplier relationships."},
            {"word": "payroll", "ipa": "/ˈpeɪ.rəʊl/", "meaning": "bảng lương nhân viên", "example": "The finance team processes payroll at the end of each month."},
            {"word": "fiscal year", "ipa": "/ˈfɪs.kəl jɪər/", "meaning": "năm tài chính", "example": "The company's fiscal year runs from April to March."},
            {"word": "quarterly earnings", "ipa": "/ˈkwɔː.tər.li ˈɜː.nɪŋz/", "meaning": "lợi nhuận hàng quý", "example": "Investors pay close attention to quarterly earnings reports."},
            {"word": "revenue recognition", "ipa": "/ˈrev.ən.juː ˌrek.əɡˈnɪʃ.ən/", "meaning": "ghi nhận doanh thu", "example": "Revenue recognition rules determine when income is officially recorded."},
            {"word": "cash flow statement", "ipa": "/kæʃ fləʊ ˈsteɪt.mənt/", "meaning": "báo cáo lưu chuyển tiền tệ", "example": "The cash flow statement shows how money moves in and out of the business."},
            {"word": "balance sheet", "ipa": "/ˈbæl.əns ʃiːt/", "meaning": "bảng cân đối kế toán", "example": "A balance sheet shows a company's assets, liabilities, and equity."},
            {"word": "income statement", "ipa": "/ˈɪŋ.kʌm ˈsteɪt.mənt/", "meaning": "báo cáo kết quả kinh doanh", "example": "The income statement shows revenues and expenses over a period."},
            {"word": "accrual accounting", "ipa": "/əˈkruː.əl əˈkaʊn.tɪŋ/", "meaning": "kế toán dồn tích", "example": "Accrual accounting records income when earned, not when cash is received."},
            {"word": "depreciation", "ipa": "/dɪˌpriː.ʃiˈeɪ.ʃən/", "meaning": "khấu hao tài sản", "example": "Depreciation allocates the cost of assets over their useful life."},
        ],
        "B2": [
            {"word": "quantitative easing", "ipa": "/ˈkwɒn.tɪ.teɪ.tɪv ˈiː.zɪŋ/", "meaning": "nới lỏng định lượng (chính sách tiền tệ)", "example": "Central banks used quantitative easing to stimulate the economy after 2008."},
            {"word": "monetary policy", "ipa": "/ˈmʌn.ɪ.tər.i ˈpɒl.ɪ.si/", "meaning": "chính sách tiền tệ", "example": "Monetary policy controls the money supply and interest rates."},
            {"word": "fiscal policy", "ipa": "/ˈfɪs.kəl ˈpɒl.ɪ.si/", "meaning": "chính sách tài khóa", "example": "Fiscal policy uses government spending and taxes to influence the economy."},
            {"word": "central bank", "ipa": "/ˈsen.trəl bæŋk/", "meaning": "ngân hàng trung ương", "example": "The central bank raised interest rates to control inflation."},
            {"word": "federal reserve", "ipa": "/ˈfed.ər.əl rɪˈzɜːv/", "meaning": "Cục Dự trữ Liên bang Mỹ", "example": "The Federal Reserve's decision influenced global financial markets."},
            {"word": "bond yield", "ipa": "/bɒnd jiːld/", "meaning": "lợi suất trái phiếu", "example": "Rising bond yields often signal expectations of higher inflation."},
            {"word": "yield curve", "ipa": "/jiːld kɜːv/", "meaning": "đường cong lợi suất", "example": "An inverted yield curve has historically predicted recessions."},
            {"word": "liquidity crisis", "ipa": "/lɪˈkwɪd.ɪ.ti ˈkraɪ.sɪs/", "meaning": "khủng hoảng thanh khoản", "example": "The bank collapsed after a severe liquidity crisis."},
            {"word": "systemic risk", "ipa": "/sɪˈstem.ɪk rɪsk/", "meaning": "rủi ro hệ thống", "example": "The failure of major banks creates systemic risk for the entire economy."},
            {"word": "moral hazard", "ipa": "/ˈmɒr.əl ˈhæz.əd/", "meaning": "rủi ro đạo đức", "example": "Bank bailouts can create moral hazard by encouraging excessive risk-taking."},
            {"word": "sovereign debt", "ipa": "/ˈsɒv.rɪn det/", "meaning": "nợ công quốc gia", "example": "Greece's sovereign debt crisis affected all of Europe."},
            {"word": "credit rating", "ipa": "/ˈkred.ɪt ˈreɪ.tɪŋ/", "meaning": "xếp hạng tín dụng quốc gia/công ty", "example": "A downgrade in credit rating increases borrowing costs."},
            {"word": "credit default swap", "ipa": "/ˈkred.ɪt dɪˈfɔːlt swɒp/", "meaning": "hoán đổi rủi ro vỡ nợ", "example": "Credit default swaps allow investors to hedge against bond defaults."},
            {"word": "collateralized loan obligation", "ipa": "/kəˌlæt.ər.ə.laɪzd ləʊn ˌɒb.lɪˈɡeɪ.ʃən/", "meaning": "nghĩa vụ cho vay có tài sản đảm bảo", "example": "CLOs bundle corporate loans into structured securities for investors."},
            {"word": "securitization", "ipa": "/sɪˌkjʊər.ɪ.taɪˈzeɪ.ʃən/", "meaning": "chứng khoán hóa", "example": "Securitization converts illiquid assets into tradeable securities."},
            {"word": "derivatives market", "ipa": "/dɪˈrɪv.ə.tɪvz ˈmɑː.kɪt/", "meaning": "thị trường phái sinh", "example": "The derivatives market is much larger than the underlying asset market."},
            {"word": "hedging strategy", "ipa": "/ˈhedʒ.ɪŋ ˈstræt.ɪ.dʒi/", "meaning": "chiến lược phòng hộ rủi ro", "example": "A hedging strategy uses derivatives to offset potential losses."},
            {"word": "carry trade", "ipa": "/ˈkær.i treɪd/", "meaning": "giao dịch chênh lệch lãi suất", "example": "Carry trades borrow in low-interest currencies to invest in high-yielding ones."},
            {"word": "currency risk", "ipa": "/ˈkʌr.ən.si rɪsk/", "meaning": "rủi ro tỷ giá hối đoái", "example": "International investors face currency risk when investing abroad."},
            {"word": "purchasing power parity", "ipa": "/ˈpɜː.tʃɪ.sɪŋ ˈpaʊər ˈpær.ɪ.ti/", "meaning": "ngang giá sức mua", "example": "Purchasing power parity compares the relative value of currencies."},
            {"word": "current account deficit", "ipa": "/ˈkʌr.ənt əˈkaʊnt ˈdef.ɪ.sɪt/", "meaning": "thâm hụt tài khoản vãng lai", "example": "A large current account deficit can weaken a country's currency."},
            {"word": "balance of payments", "ipa": "/ˈbæl.əns əv ˈpeɪ.mənts/", "meaning": "cán cân thanh toán", "example": "The balance of payments records all transactions between a country and the world."},
            {"word": "foreign exchange reserves", "ipa": "/ˈfɒr.ɪn ɪksˈtʃeɪndʒ rɪˈzɜːvz/", "meaning": "dự trữ ngoại hối", "example": "China holds the world's largest foreign exchange reserves."},
            {"word": "capital flight", "ipa": "/ˈkæp.ɪ.təl flaɪt/", "meaning": "tháo chạy vốn", "example": "Political instability caused massive capital flight from the country."},
            {"word": "austerity measures", "ipa": "/ɒˈster.ɪ.ti ˈmeʒ.ərz/", "meaning": "biện pháp thắt lưng buộc bụng", "example": "Austerity measures reduced public spending but also slowed growth."},
            {"word": "economic stimulus", "ipa": "/ˌiː.kəˈnɒm.ɪk ˈstɪm.jʊ.ləs/", "meaning": "gói kích thích kinh tế", "example": "The government announced an economic stimulus package to boost growth."},
            {"word": "helicopter money", "ipa": "/ˈhel.ɪ.kɒp.tər ˈmʌn.i/", "meaning": "phát tiền trực tiếp cho dân", "example": "Helicopter money refers to direct cash payments to boost consumer spending."},
            {"word": "negative interest rate", "ipa": "/ˈneɡ.ə.tɪv ˈɪn.trəst reɪt/", "meaning": "lãi suất âm", "example": "Some central banks have introduced negative interest rates to stimulate lending."},
            {"word": "LIBOR", "ipa": "/ˈlaɪ.bɔːr/", "meaning": "lãi suất liên ngân hàng London", "example": "LIBOR was the benchmark interest rate for global lending until its replacement."},
            {"word": "SOFR", "ipa": "/ˈsɒ.fər/", "meaning": "lãi suất tài trợ qua đêm bảo đảm", "example": "SOFR has replaced LIBOR as the preferred benchmark rate."},
            {"word": "green finance", "ipa": "/ɡriːn ˈfaɪ.næns/", "meaning": "tài chính xanh", "example": "Green finance channels investment into environmentally sustainable projects."},
            {"word": "ESG investing", "ipa": "/ˌiː.es.ˈdʒiː ɪnˈves.tɪŋ/", "meaning": "đầu tư ESG (môi trường, xã hội, quản trị)", "example": "ESG investing considers environmental, social, and governance factors alongside returns."},
            {"word": "impact investing", "ipa": "/ˈɪm.pækt ɪnˈves.tɪŋ/", "meaning": "đầu tư tác động xã hội", "example": "Impact investing seeks both financial returns and positive social outcomes."},
            {"word": "microfinance", "ipa": "/ˈmaɪ.krəʊˌfaɪ.næns/", "meaning": "tài chính vi mô", "example": "Microfinance provides small loans to entrepreneurs in developing countries."},
            {"word": "financial inclusion", "ipa": "/faɪˈnæn.ʃəl ɪnˈkluː.ʒən/", "meaning": "hòa nhập tài chính", "example": "Financial inclusion ensures all people have access to basic banking services."},
            {"word": "decentralized finance (DeFi)", "ipa": "/diːˈsen.trəl.aɪzd ˈfaɪ.næns/", "meaning": "tài chính phi tập trung", "example": "DeFi uses blockchain to offer financial services without intermediaries."},
            {"word": "stablecoin", "ipa": "/ˈsteɪ.bəl.kɔɪn/", "meaning": "tiền điện tử ổn định giá", "example": "A stablecoin pegs its value to a stable asset like the US dollar."},
            {"word": "NFT (Non-Fungible Token)", "ipa": "/ˌen.ef.ˈtiː/", "meaning": "token không thể thay thế", "example": "NFTs represent unique digital assets on the blockchain."},
            {"word": "tokenization (finance)", "ipa": "/ˌtəʊ.kən.aɪˈzeɪ.ʃən/", "meaning": "mã hóa tài sản thành token", "example": "Tokenization enables fractional ownership of real-world assets."},
            {"word": "algorithmic trading", "ipa": "/ˌæl.ɡəˈrɪð.mɪk ˈtreɪ.dɪŋ/", "meaning": "giao dịch thuật toán", "example": "Algorithmic trading executes orders at speeds impossible for human traders."},
            {"word": "high-frequency trading", "ipa": "/haɪ ˈfriː.kwən.si ˈtreɪ.dɪŋ/", "meaning": "giao dịch tần suất cao", "example": "High-frequency trading firms profit from tiny price discrepancies."},
            {"word": "dark pool", "ipa": "/dɑːk puːl/", "meaning": "hồ giao dịch ẩn", "example": "Institutional investors use dark pools to trade large blocks without affecting prices."},
            {"word": "market maker", "ipa": "/ˈmɑː.kɪt ˌmeɪ.kər/", "meaning": "nhà tạo lập thị trường", "example": "A market maker provides liquidity by always being willing to buy and sell securities."},
            {"word": "bid-ask spread", "ipa": "/bɪd æsk spred/", "meaning": "chênh lệch giá mua-bán", "example": "A narrow bid-ask spread indicates a liquid market."},
            {"word": "order book", "ipa": "/ˈɔː.dər bʊk/", "meaning": "sổ lệnh (chứng khoán)", "example": "The order book displays all pending buy and sell orders for a security."},
            {"word": "arbitrage", "ipa": "/ˈɑː.bɪ.trɑːʒ/", "meaning": "kinh doanh chênh lệch giá", "example": "Arbitrage exploits price differences for the same asset in different markets."},
            {"word": "price discovery", "ipa": "/praɪs dɪˈskʌv.ər.i/", "meaning": "khám phá giá thị trường", "example": "Financial markets facilitate price discovery through supply and demand."},
            {"word": "information efficiency", "ipa": "/ˌɪn.fəˈmeɪ.ʃən ɪˈfɪʃ.ən.si/", "meaning": "hiệu quả thông tin thị trường", "example": "An informationally efficient market reflects all available information in prices."},
            {"word": "behavioral finance", "ipa": "/bɪˈheɪ.vjər.əl ˈfaɪ.næns/", "meaning": "tài chính hành vi", "example": "Behavioral finance studies how psychology affects financial decisions."},
            {"word": "monetary expansion", "ipa": "/ˈmɑnəˌtɛri ɪkˈspænʧən/", "meaning": "nới lỏng định lượng (chính sách tiền tệ)", "example": "Central banks used quantitative easing to stimulate the economy after 2008."},
        ],
        "C1": [
            {"word": "efficient market hypothesis", "ipa": "/ɪˈfɪʃ.ənt ˈmɑː.kɪt haɪˈpɒθ.ɪ.sɪs/", "meaning": "giả thuyết thị trường hiệu quả", "example": "The efficient market hypothesis suggests prices reflect all available information."},
            {"word": "stochastic calculus", "ipa": "/stəˈkæs.tɪk ˈkæl.kjʊ.ləs/", "meaning": "phép tính ngẫu nhiên", "example": "Stochastic calculus underpins option pricing models like Black-Scholes."},
            {"word": "Black-Scholes model", "ipa": "/blæk ʃəʊlz ˈmɒd.əl/", "meaning": "mô hình Black-Scholes (định giá quyền chọn)", "example": "The Black-Scholes model revolutionized options pricing in financial markets."},
            {"word": "Monte Carlo simulation", "ipa": "/ˌmɒn.tɪ ˈkɑː.ləʊ ˌsɪm.jʊˈleɪ.ʃən/", "meaning": "mô phỏng Monte Carlo", "example": "Monte Carlo simulation models the probability distribution of financial outcomes."},
            {"word": "value at risk (VaR)", "ipa": "/ˈvæl.juː ət rɪsk/", "meaning": "giá trị chịu rủi ro", "example": "VaR quantifies the maximum expected loss over a given time period at a confidence level."},
            {"word": "conditional value at risk (CVaR)", "ipa": "/kənˈdɪʃ.ən.əl ˈvæl.juː ət rɪsk/", "meaning": "giá trị chịu rủi ro có điều kiện", "example": "CVaR, or expected shortfall, measures the average loss beyond the VaR threshold."},
            {"word": "Sharpe ratio", "ipa": "/ʃɑːp ˈreɪ.ʃi.əʊ/", "meaning": "chỉ số Sharpe (hiệu suất điều chỉnh rủi ro)", "example": "A higher Sharpe ratio indicates better risk-adjusted performance."},
            {"word": "alpha (finance)", "ipa": "/ˈælfə (ˈfaɪˌnæns)/", "meaning": "alpha (lợi nhuận vượt trội)", "example": "Generating positive alpha means outperforming the benchmark after adjusting for risk."},
            {"word": "beta (finance)", "ipa": "/ˈbeɪtə (ˈfaɪˌnæns)/", "meaning": "beta (độ nhạy với thị trường)", "example": "A beta of 1.5 means the stock is 50% more volatile than the market."},
            {"word": "Markowitz portfolio theory", "ipa": "/ˌmɑː.kəˈwɪts pɔːtˈfəʊ.li.əʊ ˈθɪər.i/", "meaning": "lý thuyết danh mục Markowitz", "example": "Markowitz portfolio theory formalizes the trade-off between risk and return."},
            {"word": "capital asset pricing model", "ipa": "/ˈkæp.ɪ.təl ˈæs.et ˈpraɪ.sɪŋ ˈmɒd.əl/", "meaning": "mô hình định giá tài sản vốn (CAPM)", "example": "CAPM calculates the expected return of an asset based on its systematic risk."},
            {"word": "arbitrage pricing theory", "ipa": "/ˈɑː.bɪ.trɑːʒ ˈpraɪ.sɪŋ ˈθɪər.i/", "meaning": "lý thuyết định giá arbitrage", "example": "Arbitrage pricing theory uses multiple factors to explain asset returns."},
            {"word": "Fama-French three-factor model", "ipa": "/ˈfɑː.mə frentʃ θriː ˈfæk.tər ˈmɒd.əl/", "meaning": "mô hình ba nhân tố Fama-French", "example": "The Fama-French model adds size and value factors to the CAPM."},
            {"word": "risk-neutral measure", "ipa": "/rɪsk ˈnjuː.trəl ˈmeʒ.ər/", "meaning": "độ đo trung tính rủi ro", "example": "Risk-neutral measure is used in derivative pricing to simplify calculations."},
            {"word": "Girsanov's theorem", "ipa": "/ˈɡɪər.sɑː.nɒvz ˈθɪər.əm/", "meaning": "định lý Girsanov", "example": "Girsanov's theorem allows changing probability measures in stochastic models."},
            {"word": "Ito's lemma", "ipa": "/ˈiː.toʊz ˈlem.ə/", "meaning": "bổ đề Ito (tính toán ngẫu nhiên)", "example": "Ito's lemma is fundamental to deriving the Black-Scholes equation."},
            {"word": "volatility smile", "ipa": "/ˌvɒl.əˈtɪl.ɪ.ti smaɪl/", "meaning": "nụ cười biến động (quyền chọn)", "example": "The volatility smile shows implied volatility varies with option strike price."},
            {"word": "implied volatility", "ipa": "/ɪmˈplaɪd ˌvɒl.əˈtɪl.ɪ.ti/", "meaning": "biến động ngụ ý", "example": "Implied volatility is derived from option prices and reflects market expectations."},
            {"word": "term structure of interest rates", "ipa": "/tɜːm ˈstrʌk.tʃər əv ˈɪn.trəst reɪts/", "meaning": "cấu trúc kỳ hạn lãi suất", "example": "The term structure of interest rates describes how yields vary by maturity."},
            {"word": "duration (bonds)", "ipa": "/djʊˈreɪ.ʃən/", "meaning": "thời gian đáo hạn điều chỉnh (trái phiếu)", "example": "Duration measures a bond's sensitivity to interest rate changes."},
            {"word": "convexity (bonds)", "ipa": "/kənˈvek.sɪ.ti/", "meaning": "độ lồi trái phiếu", "example": "Convexity measures the curvature in the bond price-yield relationship."},
            {"word": "credit spread", "ipa": "/ˈkred.ɪt spred/", "meaning": "chênh lệch tín dụng", "example": "Widening credit spreads signal increased perceived risk of default."},
            {"word": "basis risk", "ipa": "/ˈbeɪ.sɪs rɪsk/", "meaning": "rủi ro cơ sở (phòng hộ không hoàn hảo)", "example": "Basis risk arises when a hedge does not perfectly offset the underlying exposure."},
            {"word": "delta hedging", "ipa": "/ˈdel.tə ˈhedʒ.ɪŋ/", "meaning": "phòng hộ delta (quyền chọn)", "example": "Delta hedging maintains a neutral position by continuously adjusting holdings."},
            {"word": "gamma (options)", "ipa": "/ˈgæmə (ˈɔpʃənz)/", "meaning": "gamma (tốc độ thay đổi delta)", "example": "Gamma measures how fast delta changes as the underlying price moves."},
            {"word": "vega (options)", "ipa": "/ˈveɪgə (ˈɔpʃənz)/", "meaning": "vega (độ nhạy với biến động)", "example": "Vega measures an option's sensitivity to changes in implied volatility."},
            {"word": "theta (options)", "ipa": "/ˈθeɪtə (ˈɔpʃənz)/", "meaning": "theta (hao mòn thời gian quyền chọn)", "example": "Theta represents the daily time decay of an option's value."},
            {"word": "rho (options)", "ipa": "/roʊ (ˈɔpʃənz)/", "meaning": "rho (độ nhạy lãi suất của quyền chọn)", "example": "Rho measures an option's sensitivity to changes in the risk-free interest rate."},
            {"word": "GARCH model", "ipa": "/ɡɑːtʃ ˈmɒd.əl/", "meaning": "mô hình GARCH (biến động tự hồi quy)", "example": "The GARCH model captures time-varying volatility in financial time series."},
            {"word": "cointegration", "ipa": "/ˌkəʊ.ɪn.tɪˈɡreɪ.ʃən/", "meaning": "đồng tích hợp", "example": "Cointegration identifies long-run equilibrium relationships between financial series."},
            {"word": "factor model", "ipa": "/ˈfæk.tər ˈmɒd.əl/", "meaning": "mô hình nhân tố", "example": "Factor models decompose asset returns into systematic and idiosyncratic components."},
            {"word": "smart beta", "ipa": "/smɑːt ˈbiː.tə/", "meaning": "beta thông minh (chiến lược đầu tư nhân tố)", "example": "Smart beta strategies exploit systematic factors like value and momentum."},
            {"word": "risk parity", "ipa": "/rɪsk ˈpær.ɪ.ti/", "meaning": "cân bằng rủi ro", "example": "Risk parity allocates capital so each asset contributes equally to portfolio risk."},
            {"word": "mean reversion", "ipa": "/miːn rɪˈvɜː.ʃən/", "meaning": "hồi quy về trung bình", "example": "Mean reversion strategies bet that prices will return to their historical averages."},
            {"word": "momentum strategy", "ipa": "/məˈmen.təm ˈstræt.ɪ.dʒi/", "meaning": "chiến lược động lực", "example": "A momentum strategy buys assets that have recently outperformed."},
            {"word": "pairs trading", "ipa": "/peərz ˈtreɪ.dɪŋ/", "meaning": "giao dịch cặp", "example": "Pairs trading exploits the relative mispricing between two correlated assets."},
            {"word": "statistical arbitrage", "ipa": "/stəˈtɪs.tɪ.kəl ˈɑː.bɪ.trɑːʒ/", "meaning": "arbitrage thống kê", "example": "Statistical arbitrage uses quantitative models to identify mispriced securities."},
            {"word": "machine learning in finance", "ipa": "/məˈʃiːn ˈlɜː.nɪŋ ɪn ˈfaɪ.næns/", "meaning": "học máy trong tài chính", "example": "Machine learning in finance enables more accurate credit scoring and fraud detection."},
            {"word": "natural language processing (finance)", "ipa": "/ˈnætʃ.rəl ˈlæŋ.ɡwɪdʒ ˈprəʊ.ses.ɪŋ/", "meaning": "xử lý ngôn ngữ tự nhiên (tài chính)", "example": "NLP analyzes news and earnings calls to generate trading signals."},
            {"word": "sentiment analysis (finance)", "ipa": "/ˈsen.tɪ.mənt əˈnæl.ɪ.sɪs/", "meaning": "phân tích tâm lý thị trường", "example": "Sentiment analysis of social media can predict short-term stock movements."},
            {"word": "alternative data", "ipa": "/ɔːlˈtɜː.nə.tɪv ˈdeɪ.tə/", "meaning": "dữ liệu thay thế (đầu tư)", "example": "Alternative data such as satellite imagery and web traffic is used by hedge funds."},
            {"word": "regulatory technology (RegTech)", "ipa": "/ˌreɡ.jʊˈleɪ.tər.i tekˈnɒl.ə.dʒi/", "meaning": "công nghệ quản lý tuân thủ", "example": "RegTech automates compliance monitoring to reduce regulatory risk."},
            {"word": "systemic importance", "ipa": "/sɪˈstem.ɪk ɪmˈpɔː.təns/", "meaning": "tầm quan trọng hệ thống", "example": "Systemically important financial institutions receive special regulatory oversight."},
            {"word": "prudential regulation", "ipa": "/pruːˈden.ʃəl ˌreɡ.jʊˈleɪ.ʃən/", "meaning": "giám sát thận trọng", "example": "Prudential regulation ensures financial institutions maintain adequate capital buffers."},
            {"word": "Solvency II", "ipa": "/ˈsɒl.vən.si tuː/", "meaning": "Solvency II (quy định bảo hiểm EU)", "example": "Solvency II sets risk-based capital requirements for European insurers."},
            {"word": "Dodd-Frank Act", "ipa": "/ˌdɒd fræŋk ækt/", "meaning": "Đạo luật Dodd-Frank", "example": "The Dodd-Frank Act introduced sweeping financial reforms after the 2008 crisis."},
            {"word": "MiFID II", "ipa": "/ˈmɪf.ɪd tuː/", "meaning": "MiFID II (quy định tài chính EU)", "example": "MiFID II requires greater transparency in European financial markets."},
            {"word": "Basel III", "ipa": "/ˈbɑː.zəl θriː/", "meaning": "Basel III (tiêu chuẩn vốn ngân hàng)", "example": "Basel III strengthens bank capital requirements to prevent future crises."},
            {"word": "anti-money laundering (AML)", "ipa": "/ˌæn.ti ˈmʌn.i ˈlɔːn.dər.ɪŋ/", "meaning": "chống rửa tiền", "example": "AML regulations require banks to monitor and report suspicious transactions."},
            {"word": "know your customer (KYC)", "ipa": "/nəʊ jɔːr ˈkʌs.tə.mər/", "meaning": "xác minh danh tính khách hàng", "example": "KYC procedures verify customer identity to prevent financial crime."},
            {"word": "FATF recommendations", "ipa": "/fætf ˌrek.əmenˈdeɪ.ʃənz/", "meaning": "khuyến nghị của FATF (chống rửa tiền)", "example": "Countries implement FATF recommendations to combat money laundering and terrorism financing."},
        ],
    },
    "health": {
        "A1": [
            {"word": "doctor", "ipa": "/ˈdɒk.tər/", "meaning": "bác sĩ", "example": "I need to see a doctor because I have a fever."},
            {"word": "sick", "ipa": "/sɪk/", "meaning": "ốm, bệnh", "example": "She stayed home from school because she was sick."},
            {"word": "pain", "ipa": "/peɪn/", "meaning": "đau đớn", "example": "He felt pain in his stomach after eating."},
            {"word": "pill", "ipa": "/pɪl/", "meaning": "viên thuốc", "example": "Take one pill three times a day after meals."},
            {"word": "body", "ipa": "/ˈbɒd.i/", "meaning": "cơ thể", "example": "Exercise is good for your body and your mind."},
            {"word": "sleep", "ipa": "/sliːp/", "meaning": "ngủ", "example": "Children need at least 9 hours of sleep every night."},
            {"word": "water", "ipa": "/ˈwɔː.tər/", "meaning": "nước uống", "example": "Drink plenty of water to stay healthy and hydrated."},
            {"word": "food", "ipa": "/fuːd/", "meaning": "thức ăn", "example": "Eating healthy food keeps your body strong and energetic."},
            {"word": "hospital", "ipa": "/ˈhɒs.pɪ.təl/", "meaning": "bệnh viện", "example": "She was taken to the hospital after the accident."},
            {"word": "healthy", "ipa": "/ˈhel.θi/", "meaning": "khỏe mạnh", "example": "Eating vegetables helps you stay healthy."},
            {"word": "headache", "ipa": "/ˈhed.eɪk/", "meaning": "đau đầu", "example": "I have a bad headache and need to rest."},
            {"word": "fever", "ipa": "/ˈfiː.vər/", "meaning": "sốt", "example": "He had a high fever for three days."},
            {"word": "cough", "ipa": "/kɒf/", "meaning": "ho", "example": "She has a bad cough and a sore throat."},
            {"word": "cold", "ipa": "/kəʊld/", "meaning": "cảm lạnh", "example": "I caught a cold and had to stay home."},
            {"word": "rest", "ipa": "/rest/", "meaning": "nghỉ ngơi", "example": "The doctor told me to rest for a few days."},
            {"word": "exercise", "ipa": "/ˈek.sə.saɪz/", "meaning": "tập thể dục", "example": "She exercises every morning to stay fit."},
            {"word": "medicine", "ipa": "/ˈmed.ɪ.sɪn/", "meaning": "thuốc; y học", "example": "The doctor prescribed some medicine for my sore throat."},
            {"word": "nurse", "ipa": "/nɜːs/", "meaning": "y tá", "example": "The nurse checked my blood pressure every hour."},
            {"word": "heart", "ipa": "/hɑːt/", "meaning": "tim", "example": "Exercise keeps your heart strong and healthy."},
            {"word": "eye", "ipa": "/aɪ/", "meaning": "mắt", "example": "She has beautiful blue eyes."},
            {"word": "tooth", "ipa": "/tuːθ/", "meaning": "răng", "example": "Brush your teeth twice a day to prevent cavities."},
            {"word": "hand", "ipa": "/hænd/", "meaning": "tay", "example": "Wash your hands regularly to prevent illness."},
            {"word": "stomach", "ipa": "/ˈstʌm.ək/", "meaning": "dạ dày; bụng", "example": "I have a stomach ache after eating too much."},
            {"word": "ear", "ipa": "/ɪər/", "meaning": "tai", "example": "She had an ear infection and needed antibiotics."},
            {"word": "arm", "ipa": "/ɑːm/", "meaning": "cánh tay", "example": "He broke his arm playing football."},
            {"word": "leg", "ipa": "/lɛg/", "meaning": "chân", "example": "She hurt her leg during the running race."},
            {"word": "back", "ipa": "/bæk/", "meaning": "lưng", "example": "He has back pain from sitting too long."},
            {"word": "skin", "ipa": "/skɪn/", "meaning": "da", "example": "Use sunscreen to protect your skin in hot weather."},
            {"word": "lungs", "ipa": "/lʌŋz/", "meaning": "phổi", "example": "Smoking damages your lungs and causes cancer."},
            {"word": "blood", "ipa": "/blʌd/", "meaning": "máu", "example": "The test showed that his blood pressure was too high."},
            {"word": "knee", "ipa": "/niː/", "meaning": "đầu gối", "example": "He injured his knee while playing basketball."},
            {"word": "broken bone", "ipa": "/ˈbrəʊ.kən bəʊn/", "meaning": "xương gãy", "example": "He went to hospital with a broken bone in his foot."},
            {"word": "bandage", "ipa": "/ˈbæn.dɪdʒ/", "meaning": "băng bó vết thương", "example": "The nurse put a bandage on her cut finger."},
            {"word": "injection", "ipa": "/ɪnˈdʒek.ʃən/", "meaning": "mũi tiêm", "example": "He was afraid of getting an injection at the doctor's."},
            {"word": "appointment", "ipa": "/əˈpɔɪnt.mənt/", "meaning": "cuộc hẹn khám bệnh", "example": "I have a doctor's appointment at 10 o'clock tomorrow."},
            {"word": "ambulance", "ipa": "/ˈæm.bjʊ.ləns/", "meaning": "xe cứu thương", "example": "They called an ambulance after the car accident."},
            {"word": "thermometer", "ipa": "/θəˈmɒm.ɪ.tər/", "meaning": "nhiệt kế", "example": "The nurse used a thermometer to check the child's temperature."},
            {"word": "temperature", "ipa": "/ˈtem.prɪ.tʃər/", "meaning": "nhiệt độ cơ thể", "example": "His temperature was 39 degrees, so he had a fever."},
            {"word": "allergy", "ipa": "/ˈæl.ə.dʒi/", "meaning": "dị ứng", "example": "She has an allergy to peanuts."},
            {"word": "vitamin", "ipa": "/ˈvɪt.ə.mɪn/", "meaning": "vitamin", "example": "Fruits are a good source of vitamins."},
            {"word": "diet", "ipa": "/ˈdaɪ.ɪt/", "meaning": "chế độ ăn kiêng", "example": "A healthy diet includes lots of vegetables and fruits."},
            {"word": "checkup", "ipa": "/ˈʧɛˌkəp/", "meaning": "khám sức khỏe định kỳ", "example": "She goes for a health checkup every year."},
            {"word": "sneeze", "ipa": "/sniːz/", "meaning": "hắt hơi", "example": "Cover your mouth when you sneeze to stop spreading germs."},
            {"word": "wash", "ipa": "/wɒʃ/", "meaning": "rửa", "example": "Wash your hands before eating to stay healthy."},
            {"word": "sore throat", "ipa": "/sɔː θrəʊt/", "meaning": "đau họng", "example": "I have a sore throat and it hurts to swallow."},
            {"word": "fresh air", "ipa": "/freʃ eər/", "meaning": "không khí trong lành", "example": "Going for a walk gives you fresh air and exercise."},
            {"word": "hygiene", "ipa": "/ˈhaɪ.dʒiːn/", "meaning": "vệ sinh sạch sẽ", "example": "Good personal hygiene helps prevent the spread of disease."},
            {"word": "overweight", "ipa": "/ˌəʊ.vəˈweɪt/", "meaning": "thừa cân", "example": "Being overweight increases the risk of many health problems."},
            {"word": "fit", "ipa": "/fɪt/", "meaning": "khỏe mạnh, cường tráng", "example": "She runs regularly to keep fit."},
            {"word": "well-being", "ipa": "/ˌwel.ˈbiː.ɪŋ/", "meaning": "sức khỏe và hạnh phúc", "example": "Regular exercise improves your overall well-being."},
        ],
        "A2": [
            {"word": "symptom", "ipa": "/ˈsɪmp.təm/", "meaning": "triệu chứng bệnh", "example": "Coughing and fever are common symptoms of the flu."},
            {"word": "prescription", "ipa": "/prɪˈskrɪp.ʃən/", "meaning": "đơn thuốc", "example": "The doctor gave her a prescription for antibiotics."},
            {"word": "pharmacy", "ipa": "/ˈfɑː.mə.si/", "meaning": "nhà thuốc", "example": "You can get this medicine from any pharmacy without a prescription."},
            {"word": "nutrition", "ipa": "/njuːˈtrɪʃ.ən/", "meaning": "dinh dưỡng", "example": "Good nutrition is important for children's growth and development."},
            {"word": "immune system", "ipa": "/ɪˈmjuːn ˈsɪs.təm/", "meaning": "hệ miễn dịch", "example": "Eating well helps strengthen your immune system."},
            {"word": "antibiotic", "ipa": "/ˌæn.ti.baɪˈɒt.ɪk/", "meaning": "kháng sinh", "example": "The doctor prescribed antibiotics to fight the bacterial infection."},
            {"word": "blood pressure", "ipa": "/blʌd ˈpreʃ.ər/", "meaning": "huyết áp", "example": "High blood pressure can lead to heart disease if untreated."},
            {"word": "diabetes", "ipa": "/ˌdaɪ.əˈbiː.tiːz/", "meaning": "bệnh tiểu đường", "example": "She was diagnosed with diabetes and had to change her diet."},
            {"word": "obesity", "ipa": "/əʊˈbiː.sɪ.ti/", "meaning": "béo phì", "example": "Obesity increases the risk of heart disease and diabetes."},
            {"word": "asthma", "ipa": "/ˈæz.mə/", "meaning": "hen suyễn", "example": "He uses an inhaler to manage his asthma."},
            {"word": "infection", "ipa": "/ɪnˈfek.ʃən/", "meaning": "nhiễm trùng", "example": "The wound became infected and needed antibiotics."},
            {"word": "inflammation", "ipa": "/ˌɪn.fləˈmeɪ.ʃən/", "meaning": "viêm", "example": "Ice helps reduce inflammation and swelling after an injury."},
            {"word": "recovery", "ipa": "/rɪˈkʌv.ər.i/", "meaning": "sự hồi phục", "example": "Full recovery from the surgery took about three months."},
            {"word": "surgeon", "ipa": "/ˈsərʤɪn/", "meaning": "bác sĩ phẫu thuật", "example": "The surgeon performed a six-hour operation on the patient."},
            {"word": "operation", "ipa": "/ˌɒp.ərˈeɪ.ʃən/", "meaning": "ca phẫu thuật", "example": "He had an operation to remove his appendix."},
            {"word": "X-ray", "ipa": "/ˈeks.reɪ/", "meaning": "chụp X-quang", "example": "The doctor took an X-ray to check if the bone was broken."},
            {"word": "scan", "ipa": "/skæn/", "meaning": "chụp hình nội soi", "example": "She had an MRI scan to check for any brain abnormalities."},
            {"word": "dentist", "ipa": "/ˈden.tɪst/", "meaning": "nha sĩ", "example": "You should visit the dentist at least twice a year."},
            {"word": "vaccine", "ipa": "/ˈvæk.siːn/", "meaning": "vắc-xin", "example": "Getting the flu vaccine reduces your risk of getting sick."},
            {"word": "clinic", "ipa": "/ˈklɪn.ɪk/", "meaning": "phòng khám", "example": "The local clinic provides free health check-ups."},
            {"word": "emergency", "ipa": "/ɪˈmɜː.dʒən.si/", "meaning": "cấp cứu; tình huống khẩn cấp", "example": "Call 911 in case of a medical emergency."},
            {"word": "mental health", "ipa": "/ˈmen.təl helθ/", "meaning": "sức khỏe tâm thần", "example": "Taking care of your mental health is just as important as physical health."},
            {"word": "stress", "ipa": "/stres/", "meaning": "căng thẳng", "example": "Too much stress can lead to serious health problems."},
            {"word": "anxiety", "ipa": "/æŋˈzaɪ.ɪ.ti/", "meaning": "lo lắng, lo âu", "example": "She experienced anxiety before important exams."},
            {"word": "depression", "ipa": "/dɪˈpreʃ.ən/", "meaning": "trầm cảm", "example": "Depression is a serious condition that requires professional treatment."},
            {"word": "therapy", "ipa": "/ˈθer.ə.pi/", "meaning": "liệu pháp điều trị", "example": "She attends weekly therapy sessions to help with her anxiety."},
            {"word": "physical therapy", "ipa": "/ˈfɪz.ɪ.kəl ˈθer.ə.pi/", "meaning": "vật lý trị liệu", "example": "Physical therapy helped her recover faster from the knee injury."},
            {"word": "calorie", "ipa": "/ˈkæl.ər.i/", "meaning": "calo (đơn vị năng lượng)", "example": "You need to burn more calories than you consume to lose weight."},
            {"word": "protein", "ipa": "/ˈprəʊ.tiːn/", "meaning": "chất đạm", "example": "Meat, fish, and beans are good sources of protein."},
            {"word": "carbohydrate", "ipa": "/ˌkɑː.bəʊˈhaɪ.dreɪt/", "meaning": "carbohydrat (chất bột)", "example": "Bread, rice, and pasta are high in carbohydrates."},
            {"word": "fat", "ipa": "/fæt/", "meaning": "chất béo", "example": "Olive oil contains healthy fats that are good for the heart."},
            {"word": "fiber", "ipa": "/ˈfaɪ.bər/", "meaning": "chất xơ", "example": "A diet high in fiber helps prevent constipation."},
            {"word": "mineral", "ipa": "/ˈmɪn.ər.əl/", "meaning": "khoáng chất", "example": "Calcium is a mineral essential for strong bones."},
            {"word": "obesity", "ipa": "/əʊˈbiː.sɪ.ti/", "meaning": "béo phì", "example": "Childhood obesity is a growing problem in many countries."},
            {"word": "hydration", "ipa": "/haɪˈdreɪ.ʃən/", "meaning": "giữ đủ nước trong cơ thể", "example": "Proper hydration is essential for athletic performance."},
            {"word": "dehydration", "ipa": "/ˌdiː.haɪˈdreɪ.ʃən/", "meaning": "mất nước", "example": "Dehydration can cause headaches and fatigue."},
            {"word": "supplement", "ipa": "/ˈsʌp.lɪ.mənt/", "meaning": "thực phẩm bổ sung", "example": "Many athletes take protein supplements to build muscle."},
            {"word": "organic food", "ipa": "/ɔːˈɡæn.ɪk fuːd/", "meaning": "thực phẩm hữu cơ", "example": "Organic food is grown without the use of pesticides."},
            {"word": "balanced diet", "ipa": "/ˈbæl.ənst ˈdaɪ.ɪt/", "meaning": "chế độ ăn cân bằng", "example": "A balanced diet includes all food groups in the right proportions."},
            {"word": "junk food", "ipa": "/dʒʌŋk fuːd/", "meaning": "thức ăn không lành mạnh", "example": "Eating too much junk food leads to weight gain and poor health."},
            {"word": "obesity clinic", "ipa": "/əʊˈbiː.sɪ.ti ˈklɪn.ɪk/", "meaning": "phòng khám béo phì", "example": "The obesity clinic offers personalized weight loss programs."},
            {"word": "smoking", "ipa": "/ˈsməʊ.kɪŋ/", "meaning": "hút thuốc lá", "example": "Smoking causes lung cancer and many other serious diseases."},
            {"word": "alcohol", "ipa": "/ˈæl.kə.hɒl/", "meaning": "rượu bia", "example": "Excessive alcohol consumption damages the liver."},
            {"word": "sedentary lifestyle", "ipa": "/ˈsed.ən.tər.i ˈlaɪf.staɪl/", "meaning": "lối sống ít vận động", "example": "A sedentary lifestyle increases the risk of heart disease."},
            {"word": "weight loss", "ipa": "/weɪt lɒs/", "meaning": "giảm cân", "example": "Regular exercise combined with a healthy diet supports weight loss."},
            {"word": "fitness", "ipa": "/ˈfɪt.nəs/", "meaning": "thể lực; sức khỏe thể chất", "example": "She improved her fitness by joining a gym."},
            {"word": "first aid", "ipa": "/fɜːst eɪd/", "meaning": "sơ cứu", "example": "Knowing first aid can save someone's life in an emergency."},
            {"word": "CPR", "ipa": "/ˌsiː.piːˈɑːr/", "meaning": "hô hấp nhân tạo", "example": "He was trained to perform CPR in case of cardiac arrest."},
            {"word": "self-care", "ipa": "/ˈself.keər/", "meaning": "chăm sóc bản thân", "example": "Self-care includes getting enough sleep, eating well, and managing stress."},
            {"word": "sign", "ipa": "/saɪn/", "meaning": "triệu chứng bệnh", "example": "Coughing and fever are common symptoms of the flu."},
        ],
        "B1": [
            {"word": "cardiovascular", "ipa": "/ˌkɑː.di.əʊˈvæs.kjʊ.lər/", "meaning": "tim mạch", "example": "Cardiovascular exercise strengthens the heart and improves circulation."},
            {"word": "metabolism", "ipa": "/məˈtæb.ə.lɪ.zəm/", "meaning": "trao đổi chất", "example": "Regular exercise boosts your metabolism and helps burn more calories."},
            {"word": "chronic disease", "ipa": "/ˈkrɒn.ɪk dɪˈziːz/", "meaning": "bệnh mãn tính", "example": "Diabetes and hypertension are common chronic diseases."},
            {"word": "diagnosis", "ipa": "/ˌdaɪ.əɡˈnəʊ.sɪs/", "meaning": "chẩn đoán", "example": "An early diagnosis increases the chances of successful treatment."},
            {"word": "preventive care", "ipa": "/prɪˈven.tɪv keər/", "meaning": "chăm sóc phòng ngừa", "example": "Preventive care like regular checkups helps catch diseases early."},
            {"word": "prognosis", "ipa": "/prɒɡˈnəʊ.sɪs/", "meaning": "tiên lượng bệnh", "example": "The doctor gave a positive prognosis for the patient's recovery."},
            {"word": "rehabilitation", "ipa": "/ˌriː.ə.bɪl.ɪˈteɪ.ʃən/", "meaning": "phục hồi chức năng", "example": "He underwent six months of rehabilitation after the stroke."},
            {"word": "chronic pain", "ipa": "/ˈkrɒn.ɪk peɪn/", "meaning": "đau mãn tính", "example": "Chronic pain can significantly impact a person's quality of life."},
            {"word": "inflammatory response", "ipa": "/ɪnˈflæm.ə.tɔːr.i rɪˈspɒns/", "meaning": "phản ứng viêm", "example": "The body's inflammatory response helps fight infection."},
            {"word": "autoimmune disease", "ipa": "/ˌɔː.tə.ɪˈmjuːn dɪˈziːz/", "meaning": "bệnh tự miễn", "example": "Rheumatoid arthritis is an autoimmune disease that affects the joints."},
            {"word": "hormone", "ipa": "/ˈhɔː.məʊn/", "meaning": "hooc-môn", "example": "Hormones control many functions in the body, including growth and mood."},
            {"word": "cholesterol", "ipa": "/kəˈles.tər.ɒl/", "meaning": "cholesterol", "example": "High cholesterol increases the risk of heart disease."},
            {"word": "obesity management", "ipa": "/əʊˈbiː.sɪ.ti ˈmæn.ɪdʒ.mənt/", "meaning": "quản lý béo phì", "example": "Obesity management involves diet, exercise, and behavioral changes."},
            {"word": "mental wellness", "ipa": "/ˈmen.təl ˈwel.nəs/", "meaning": "sức khỏe tinh thần tổng thể", "example": "Mental wellness includes emotional, psychological, and social well-being."},
            {"word": "mindfulness", "ipa": "/ˈmaɪnd.fəl.nəs/", "meaning": "chánh niệm", "example": "Practicing mindfulness meditation reduces stress and anxiety."},
            {"word": "insomnia", "ipa": "/ɪnˈsɒm.ni.ə/", "meaning": "chứng mất ngủ", "example": "She suffered from insomnia and was unable to sleep for more than 4 hours."},
            {"word": "clinical trial", "ipa": "/ˈklɪn.ɪ.kəl ˈtraɪ.əl/", "meaning": "thử nghiệm lâm sàng", "example": "The new drug is currently undergoing clinical trials."},
            {"word": "placebo", "ipa": "/pləˈsiː.bəʊ/", "meaning": "thuốc giả (đối chứng)", "example": "In the clinical trial, one group received the drug and the other received a placebo."},
            {"word": "blood test", "ipa": "/blʌd test/", "meaning": "xét nghiệm máu", "example": "The doctor ordered a blood test to check for diabetes."},
            {"word": "biopsy", "ipa": "/ˈbaɪ.ɒp.si/", "meaning": "sinh thiết", "example": "A biopsy was taken to check if the tumor was malignant."},
            {"word": "oncology", "ipa": "/ɒŋˈkɒl.ə.dʒi/", "meaning": "ung thư học", "example": "She is seeing an oncologist for her breast cancer treatment."},
            {"word": "chemotherapy", "ipa": "/ˌkiː.məʊˈθer.ə.pi/", "meaning": "hóa trị", "example": "She underwent several rounds of chemotherapy to fight the cancer."},
            {"word": "radiation therapy", "ipa": "/ˌreɪ.diˈeɪ.ʃən ˈθer.ə.pi/", "meaning": "xạ trị", "example": "Radiation therapy targets cancer cells to destroy them."},
            {"word": "immunotherapy", "ipa": "/ˌɪm.jʊ.nəʊˈθer.ə.pi/", "meaning": "liệu pháp miễn dịch", "example": "Immunotherapy uses the body's immune system to fight cancer."},
            {"word": "epidemiology", "ipa": "/ˌep.ɪ.diː.miˈɒl.ə.dʒi/", "meaning": "dịch tễ học", "example": "Epidemiology studies the patterns and causes of disease in populations."},
            {"word": "pandemic", "ipa": "/pænˈdem.ɪk/", "meaning": "đại dịch", "example": "The COVID-19 pandemic affected every country in the world."},
            {"word": "endemic", "ipa": "/enˈdem.ɪk/", "meaning": "bệnh đặc hữu (địa phương)", "example": "Malaria is endemic in many tropical regions."},
            {"word": "herd immunity", "ipa": "/hɜːd ɪˈmjuː.nɪ.ti/", "meaning": "miễn dịch cộng đồng", "example": "Herd immunity protects vulnerable people who cannot be vaccinated."},
            {"word": "public health", "ipa": "/ˈpʌb.lɪk helθ/", "meaning": "y tế công cộng", "example": "Public health campaigns educate communities about disease prevention."},
            {"word": "healthcare system", "ipa": "/ˈhelθ.keər ˈsɪs.təm/", "meaning": "hệ thống y tế", "example": "A strong healthcare system is essential for national development."},
            {"word": "primary care", "ipa": "/ˈpraɪ.mər.i keər/", "meaning": "chăm sóc y tế ban đầu", "example": "Primary care doctors are the first point of contact for health concerns."},
            {"word": "specialist", "ipa": "/ˈspeʃ.ə.lɪst/", "meaning": "bác sĩ chuyên khoa", "example": "He was referred to a cardiologist, a specialist in heart conditions."},
            {"word": "outpatient", "ipa": "/ˈaʊt.peɪ.ʃənt/", "meaning": "bệnh nhân ngoại trú", "example": "She had the procedure done as an outpatient and went home the same day."},
            {"word": "inpatient", "ipa": "/ˈɪn.peɪ.ʃənt/", "meaning": "bệnh nhân nội trú", "example": "He was admitted as an inpatient for observation after the accident."},
            {"word": "telemedicine", "ipa": "/ˈtel.ɪˌmed.ɪ.sɪn/", "meaning": "y tế từ xa", "example": "Telemedicine allows patients to consult doctors via video call."},
            {"word": "health insurance", "ipa": "/helθ ɪnˈʃʊər.əns/", "meaning": "bảo hiểm y tế", "example": "Health insurance covers the cost of most medical treatments."},
            {"word": "palliative care", "ipa": "/ˈpæl.i.ə.tɪv keər/", "meaning": "chăm sóc giảm nhẹ", "example": "Palliative care focuses on relieving pain and improving quality of life."},
            {"word": "organ donation", "ipa": "/ˈɔː.ɡən dəʊˈneɪ.ʃən/", "meaning": "hiến tạng", "example": "Organ donation can save the lives of many people on transplant waiting lists."},
            {"word": "transplant", "ipa": "/ˈtræns.plɑːnt/", "meaning": "cấy ghép nội tạng", "example": "She received a kidney transplant after years of dialysis."},
            {"word": "dialysis", "ipa": "/daɪˈæl.ɪ.sɪs/", "meaning": "lọc máu nhân tạo", "example": "Dialysis cleans the blood of patients with kidney failure."},
            {"word": "hospice", "ipa": "/ˈhɒs.pɪs/", "meaning": "cơ sở chăm sóc người hấp hối", "example": "She spent her final weeks in a hospice surrounded by family."},
            {"word": "genetic testing", "ipa": "/dʒɪˈnet.ɪk ˈtes.tɪŋ/", "meaning": "xét nghiệm di truyền", "example": "Genetic testing can reveal predispositions to certain diseases."},
            {"word": "biomarker", "ipa": "/ˈbaɪ.əʊˌmɑː.kər/", "meaning": "dấu ấn sinh học", "example": "Elevated biomarkers in the blood can indicate heart damage."},
            {"word": "vaccination program", "ipa": "/ˌvæk.sɪˈneɪ.ʃən ˈprəʊ.ɡræm/", "meaning": "chương trình tiêm chủng", "example": "The national vaccination program aims to eliminate measles."},
            {"word": "screening program", "ipa": "/ˈskriː.nɪŋ ˈprəʊ.ɡræm/", "meaning": "chương trình sàng lọc bệnh", "example": "Cancer screening programs detect disease in its early stages."},
            {"word": "risk factor", "ipa": "/rɪsk ˈfæk.tər/", "meaning": "yếu tố nguy cơ", "example": "Smoking is a major risk factor for lung cancer."},
            {"word": "complication", "ipa": "/ˌkɒm.plɪˈkeɪ.ʃən/", "meaning": "biến chứng", "example": "Uncontrolled diabetes can lead to serious complications."},
            {"word": "remission", "ipa": "/rɪˈmɪʃ.ən/", "meaning": "giai đoạn lui bệnh", "example": "After treatment, the cancer went into full remission."},
            {"word": "relapse", "ipa": "/rɪˈlæps/", "meaning": "tái phát bệnh", "example": "She suffered a relapse of depression after stopping medication."},
            {"word": "side effect", "ipa": "/saɪd ɪˈfekt/", "meaning": "tác dụng phụ", "example": "Nausea is a common side effect of this medication."},
        ],
        "B2": [
            {"word": "pathogen", "ipa": "/ˈpæθ.ə.dʒən/", "meaning": "mầm bệnh (vi sinh vật)", "example": "A pathogen is any microorganism that can cause disease in humans."},
            {"word": "virulence", "ipa": "/ˈvɪr.jʊ.ləns/", "meaning": "độc lực của mầm bệnh", "example": "The virulence of the virus determined how severe the outbreak became."},
            {"word": "antimicrobial resistance", "ipa": "/ˌæn.ti.maɪˈkrəʊ.bi.əl rɪˈzɪs.təns/", "meaning": "kháng kháng sinh/kháng vi sinh vật", "example": "Antimicrobial resistance is a growing global health threat."},
            {"word": "cytokine storm", "ipa": "/ˈsaɪ.tə.kaɪn stɔːm/", "meaning": "bão cytokine", "example": "A cytokine storm is an overreaction of the immune system that can be fatal."},
            {"word": "morbidity", "ipa": "/mɔːˈbɪd.ɪ.ti/", "meaning": "tỷ lệ bệnh tật", "example": "The morbidity rate from cardiovascular disease remains very high."},
            {"word": "mortality rate", "ipa": "/mɔːˈtæl.ɪ.ti reɪt/", "meaning": "tỷ lệ tử vong", "example": "The mortality rate from the disease dropped significantly after the vaccine rollout."},
            {"word": "genomic medicine", "ipa": "/dʒɪˈnəʊ.mɪk ˈmed.ɪ.sɪn/", "meaning": "y học bộ gen", "example": "Genomic medicine uses an individual's genetic information to guide treatment."},
            {"word": "precision medicine", "ipa": "/prɪˈsɪʒ.ən ˈmed.ɪ.sɪn/", "meaning": "y học chính xác", "example": "Precision medicine tailors treatment to the unique genetics of each patient."},
            {"word": "gene therapy", "ipa": "/dʒiːn ˈθer.ə.pi/", "meaning": "liệu pháp gen", "example": "Gene therapy corrects genetic defects by introducing healthy DNA into cells."},
            {"word": "CRISPR", "ipa": "/ˈkrɪs.pər/", "meaning": "công nghệ chỉnh sửa gen", "example": "CRISPR technology allows scientists to edit genes with unprecedented precision."},
            {"word": "stem cell therapy", "ipa": "/stem sel ˈθer.ə.pi/", "meaning": "liệu pháp tế bào gốc", "example": "Stem cell therapy shows promise for treating Parkinson's disease."},
            {"word": "neuropathology", "ipa": "/ˌnjʊər.əʊ.pəˈθɒl.ə.dʒi/", "meaning": "bệnh học thần kinh", "example": "Neuropathology studies diseases of the nervous system."},
            {"word": "neuroplasticity", "ipa": "/ˌnjʊər.əʊ.plæsˈtɪs.ɪ.ti/", "meaning": "tính mềm dẻo thần kinh", "example": "Neuroplasticity allows the brain to reorganize itself after injury."},
            {"word": "placebo effect", "ipa": "/pləˈsiː.bəʊ ɪˈfekt/", "meaning": "hiệu ứng giả dược", "example": "The placebo effect can cause real physiological changes in some patients."},
            {"word": "double-blind trial", "ipa": "/ˌdʌb.əl blaɪnd ˈtraɪ.əl/", "meaning": "thử nghiệm mù đôi", "example": "A double-blind trial ensures neither participants nor researchers know who receives the drug."},
            {"word": "cohort study", "ipa": "/ˈkəʊ.hɔːt ˈstʌd.i/", "meaning": "nghiên cứu đoàn hệ", "example": "The cohort study followed 10,000 people over 20 years."},
            {"word": "meta-analysis", "ipa": "/ˌmet.ə.əˈnæl.ɪ.sɪs/", "meaning": "phân tích tổng hợp", "example": "A meta-analysis combines data from multiple studies to reach stronger conclusions."},
            {"word": "systematic review", "ipa": "/ˌsɪs.tɪˈmæt.ɪk rɪˈvjuː/", "meaning": "tổng quan hệ thống", "example": "A systematic review of the evidence showed the treatment was effective."},
            {"word": "randomized controlled trial", "ipa": "/ˈræn.dəm.aɪzd kənˈtrəʊld ˈtraɪ.əl/", "meaning": "thử nghiệm ngẫu nhiên có đối chứng", "example": "A randomized controlled trial is the gold standard in clinical research."},
            {"word": "pharmacokinetics", "ipa": "/ˌfɑː.mə.kəʊ.kɪˈnet.ɪks/", "meaning": "dược động học", "example": "Pharmacokinetics studies how drugs are absorbed and eliminated by the body."},
            {"word": "pharmacodynamics", "ipa": "/ˌfɑː.mə.kəʊˌdaɪˈnæm.ɪks/", "meaning": "dược lực học", "example": "Pharmacodynamics examines the effects of drugs on the body."},
            {"word": "adverse drug reaction", "ipa": "/ˈæd.vɜːs drʌɡ riˈæk.ʃən/", "meaning": "phản ứng bất lợi của thuốc", "example": "An adverse drug reaction can range from mild discomfort to life-threatening anaphylaxis."},
            {"word": "contraindication", "ipa": "/ˌkɒn.trəˌɪn.dɪˈkeɪ.ʃən/", "meaning": "chống chỉ định", "example": "Pregnancy is a contraindication for this particular medication."},
            {"word": "drug interaction", "ipa": "/drʌɡ ˌɪn.tərˈæk.ʃən/", "meaning": "tương tác thuốc", "example": "Drug interactions can alter the effectiveness or safety of medications."},
            {"word": "bioavailability", "ipa": "/ˌbaɪ.əʊ.əˌveɪ.ləˈbɪl.ɪ.ti/", "meaning": "độ khả dụng sinh học", "example": "Oral drugs have lower bioavailability than intravenous ones."},
            {"word": "blood-brain barrier", "ipa": "/blʌd breɪn ˈbær.i.ər/", "meaning": "hàng rào máu não", "example": "The blood-brain barrier protects the brain from harmful substances in the bloodstream."},
            {"word": "microbiome", "ipa": "/ˈmaɪ.krəʊ.baɪ.əʊm/", "meaning": "hệ vi sinh vật đường ruột", "example": "A healthy microbiome is essential for digestion and immune function."},
            {"word": "gut health", "ipa": "/ɡʌt helθ/", "meaning": "sức khỏe đường ruột", "example": "Good gut health supports immunity, mood, and overall well-being."},
            {"word": "epigenetics", "ipa": "/ˌep.ɪ.dʒɪˈnet.ɪks/", "meaning": "biểu sinh học", "example": "Epigenetics studies how lifestyle factors affect gene expression."},
            {"word": "telomere", "ipa": "/ˈtel.ə.mɪər/", "meaning": "telomere (đầu mút nhiễm sắc thể)", "example": "Shorter telomeres are associated with aging and increased disease risk."},
            {"word": "oxidative stress", "ipa": "/ˈɒk.sɪ.deɪ.tɪv stres/", "meaning": "stress oxy hóa", "example": "Oxidative stress occurs when there is an imbalance between free radicals and antioxidants."},
            {"word": "antioxidant", "ipa": "/ˌæn.tiˈɒk.sɪ.dənt/", "meaning": "chất chống oxy hóa", "example": "Berries are rich in antioxidants that protect cells from damage."},
            {"word": "inflammation cascade", "ipa": "/ˌɪn.fləˈmeɪ.ʃən kæˈskeɪd/", "meaning": "chuỗi phản ứng viêm", "example": "The inflammation cascade triggers a series of immune responses."},
            {"word": "proteomics", "ipa": "/ˌprəʊ.tiˈɒm.ɪks/", "meaning": "protein học", "example": "Proteomics studies all the proteins in a cell or tissue."},
            {"word": "metabolomics", "ipa": "/ˌmet.ə.bəˈlɒm.ɪks/", "meaning": "chuyển hóa học", "example": "Metabolomics profiles metabolic compounds to understand disease states."},
            {"word": "neuroendocrinology", "ipa": "/ˌnjʊər.əʊˌen.dəʊ.krɪˈnɒl.ə.dʒi/", "meaning": "thần kinh nội tiết học", "example": "Neuroendocrinology studies the interaction between the nervous system and hormones."},
            {"word": "immunogenicity", "ipa": "/ˌɪm.jʊ.nəʊ.dʒɪˈnɪs.ɪ.ti/", "meaning": "tính sinh miễn dịch", "example": "The immunogenicity of the vaccine was tested in clinical trials."},
            {"word": "seroprevalence", "ipa": "/ˌsɪər.əʊˈprev.ə.ləns/", "meaning": "tỷ lệ lưu hành huyết thanh học", "example": "Seroprevalence studies measure the proportion of a population with antibodies."},
            {"word": "zoonotic disease", "ipa": "/ˌzuː.əˈnɒt.ɪk dɪˈziːz/", "meaning": "bệnh lây truyền từ động vật", "example": "COVID-19 is believed to be a zoonotic disease that crossed from animals to humans."},
            {"word": "vector-borne disease", "ipa": "/ˈvek.tər bɔːn dɪˈziːz/", "meaning": "bệnh lây qua vật trung gian (muỗi...)", "example": "Malaria is a vector-borne disease transmitted by the Anopheles mosquito."},
            {"word": "epidemiological surveillance", "ipa": "/ˌep.ɪˌdiː.mi.əˈlɒdʒ.ɪ.kəl səˈveɪ.ləns/", "meaning": "giám sát dịch tễ học", "example": "Epidemiological surveillance tracks disease trends across populations."},
            {"word": "contact tracing", "ipa": "/ˈkɒn.tækt ˈtreɪ.sɪŋ/", "meaning": "truy vết tiếp xúc", "example": "Contact tracing helps identify and isolate people exposed to an infectious disease."},
            {"word": "quarantine", "ipa": "/ˈkwɒr.ən.tiːn/", "meaning": "cách ly", "example": "People who may have been exposed to the virus were placed in quarantine."},
            {"word": "social determinants of health", "ipa": "/ˈsəʊ.ʃəl dɪˈtɜː.mɪ.nənts əv helθ/", "meaning": "yếu tố xã hội quyết định sức khỏe", "example": "Social determinants of health include education, income, and housing conditions."},
            {"word": "health equity", "ipa": "/helθ ˈek.wɪ.ti/", "meaning": "công bằng y tế", "example": "Health equity means ensuring everyone has access to the care they need."},
            {"word": "non-communicable disease", "ipa": "/nɒn kəˈmjuː.nɪ.kə.bəl dɪˈziːz/", "meaning": "bệnh không lây nhiễm", "example": "Heart disease, cancer, and diabetes are leading non-communicable diseases."},
            {"word": "comorbidity", "ipa": "/ˌkəʊ.mɔːˈbɪd.ɪ.ti/", "meaning": "bệnh đồng mắc", "example": "Patients with diabetes often have comorbidities such as hypertension."},
            {"word": "functional medicine", "ipa": "/ˈfʌŋk.ʃən.əl ˈmed.ɪ.sɪn/", "meaning": "y học chức năng", "example": "Functional medicine addresses the root causes of disease rather than symptoms."},
            {"word": "integrative medicine", "ipa": "/ˈɪn.tɪ.ɡreɪ.tɪv ˈmed.ɪ.sɪn/", "meaning": "y học tích hợp", "example": "Integrative medicine combines conventional and complementary approaches."},
            {"word": "evidence-based medicine", "ipa": "/ˈev.ɪ.dəns beɪst ˈmed.ɪ.sɪn/", "meaning": "y học dựa trên bằng chứng", "example": "Evidence-based medicine uses the best available research to guide treatment decisions."},
        ],
        "C1": [
            {"word": "immunodeficiency", "ipa": "/ˌɪm.jʊ.nəʊ.dɪˈfɪʃ.ən.si/", "meaning": "suy giảm miễn dịch", "example": "HIV causes immunodeficiency by destroying the body's CD4 T cells."},
            {"word": "pathogenesis", "ipa": "/ˌpæθ.əˈdʒen.ɪ.sɪs/", "meaning": "cơ chế sinh bệnh", "example": "Understanding the pathogenesis of a disease is crucial for developing effective treatments."},
            {"word": "neurodegenerative disease", "ipa": "/ˌnjʊər.əʊ.dɪˈdʒen.ər.ə.tɪv dɪˈziːz/", "meaning": "bệnh thoái hóa thần kinh", "example": "Alzheimer's is the most common neurodegenerative disease, affecting millions globally."},
            {"word": "psychosomatic", "ipa": "/ˌsaɪ.kəʊ.səˈmæt.ɪk/", "meaning": "tâm thể (bệnh do yếu tố tâm lý)", "example": "Psychosomatic illnesses have a physical component triggered by psychological factors."},
            {"word": "pharmacogenomics", "ipa": "/ˌfɑː.mə.kəʊ.dʒɪˈnəʊ.mɪks/", "meaning": "dược di truyền học", "example": "Pharmacogenomics studies how genes affect a person's response to drugs."},
            {"word": "immunomodulation", "ipa": "/ˌɪm.jʊ.nəʊ.ˌmɒd.jʊˈleɪ.ʃən/", "meaning": "điều biến miễn dịch", "example": "Immunomodulation aims to either stimulate or suppress the immune response."},
            {"word": "proteostasis", "ipa": "/ˌprəʊ.ti.əˈsteɪ.sɪs/", "meaning": "cân bằng nội môi protein", "example": "Proteostasis ensures that proteins are properly folded and functional."},
            {"word": "autophagy", "ipa": "/ɔːˈtɒf.ə.dʒi/", "meaning": "tự thực bào", "example": "Autophagy is the process by which cells degrade and recycle their own components."},
            {"word": "apoptosis", "ipa": "/ˌæp.əpˈtəʊ.sɪs/", "meaning": "chết tế bào theo chương trình", "example": "Apoptosis is programmed cell death that eliminates damaged or unwanted cells."},
            {"word": "senescence", "ipa": "/sɪˈnes.əns/", "meaning": "sự lão hóa tế bào", "example": "Cellular senescence contributes to aging and age-related diseases."},
            {"word": "angiogenesis", "ipa": "/ˌæn.dʒi.əʊˈdʒen.ɪ.sɪs/", "meaning": "sinh mạch máu mới", "example": "Tumors stimulate angiogenesis to obtain the nutrients needed for growth."},
            {"word": "oncogenesis", "ipa": "/ˌɒŋ.kəʊˈdʒen.ɪ.sɪs/", "meaning": "cơ chế sinh ung thư", "example": "Oncogenesis involves the transformation of normal cells into cancer cells."},
            {"word": "bioinformatics", "ipa": "/ˌbaɪ.əʊ.ɪn.fəˈmæt.ɪks/", "meaning": "tin sinh học", "example": "Bioinformatics uses computational tools to analyze biological data."},
            {"word": "systems biology", "ipa": "/ˈsɪs.təmz baɪˈɒl.ə.dʒi/", "meaning": "sinh học hệ thống", "example": "Systems biology studies the complex interactions within biological systems."},
            {"word": "synthetic biology", "ipa": "/sɪnˈθet.ɪk baɪˈɒl.ə.dʒi/", "meaning": "sinh học tổng hợp", "example": "Synthetic biology engineers biological systems for medical and industrial applications."},
            {"word": "liquid biopsy", "ipa": "/ˈlɪk.wɪd ˈbaɪ.ɒp.si/", "meaning": "sinh thiết lỏng", "example": "Liquid biopsy detects cancer DNA in a blood sample without invasive procedures."},
            {"word": "proteolysis", "ipa": "/ˌprəʊ.tiˈɒl.ɪ.sɪs/", "meaning": "phân giải protein", "example": "Proteolysis breaks down proteins into their constituent amino acids."},
            {"word": "translational research", "ipa": "/trænsˈleɪ.ʃən.əl rɪˈsɜːtʃ/", "meaning": "nghiên cứu chuyển dịch", "example": "Translational research converts laboratory findings into clinical treatments."},
            {"word": "regenerative medicine", "ipa": "/rɪˌdʒen.ər.ə.tɪv ˈmed.ɪ.sɪn/", "meaning": "y học tái tạo", "example": "Regenerative medicine aims to repair or replace damaged tissues and organs."},
            {"word": "exosome therapy", "ipa": "/ˈek.sə.səʊm ˈθer.ə.pi/", "meaning": "liệu pháp exosome", "example": "Exosome therapy uses cell-derived vesicles to deliver therapeutic molecules."},
            {"word": "nanotechnology in medicine", "ipa": "/ˌnæn.əʊ.tekˈnɒl.ə.dʒi ɪn ˈmed.ɪ.sɪn/", "meaning": "công nghệ nano trong y học", "example": "Nanotechnology in medicine enables targeted drug delivery to tumor cells."},
            {"word": "artificial intelligence in diagnostics", "ipa": "/ˌɑː.tɪˈfɪʃ.əl ɪnˈtel.ɪ.dʒəns ɪn ˌdaɪ.əɡˈnɒs.tɪks/", "meaning": "AI trong chẩn đoán y tế", "example": "Artificial intelligence in diagnostics can detect cancer from medical images with high accuracy."},
            {"word": "digital health", "ipa": "/ˈdɪdʒ.ɪ.təl helθ/", "meaning": "sức khỏe kỹ thuật số", "example": "Digital health technologies include wearables, apps, and telehealth platforms."},
            {"word": "neuroinflammation", "ipa": "/ˌnjʊər.əʊˌɪn.fləˈmeɪ.ʃən/", "meaning": "viêm thần kinh", "example": "Neuroinflammation is implicated in conditions such as Alzheimer's and multiple sclerosis."},
            {"word": "metabolic syndrome", "ipa": "/ˌmet.əˈbɒl.ɪk ˈsɪn.drəʊm/", "meaning": "hội chứng chuyển hóa", "example": "Metabolic syndrome is a cluster of conditions that increase the risk of heart disease."},
            {"word": "longitudinal study", "ipa": "/ˌlɒŋ.dʒɪˈtjuː.dɪ.nəl ˈstʌd.i/", "meaning": "nghiên cứu dọc theo thời gian", "example": "A longitudinal study tracked the health of participants for 30 years."},
            {"word": "health technology assessment", "ipa": "/helθ tekˈnɒl.ə.dʒi əˈses.mənt/", "meaning": "đánh giá công nghệ y tế", "example": "Health technology assessment evaluates the clinical and economic value of new treatments."},
            {"word": "pharmacovigilance", "ipa": "/ˌfɑː.mə.kəʊˈvɪdʒ.ɪ.ləns/", "meaning": "cảnh giác dược", "example": "Pharmacovigilance monitors the safety of drugs after they are approved."},
            {"word": "bioethics", "ipa": "/ˌbaɪ.əʊˈeθ.ɪks/", "meaning": "đạo đức sinh y học", "example": "Bioethics addresses moral questions raised by advances in medicine and biotechnology."},
            {"word": "informed consent", "ipa": "/ɪnˈfɔːmd kənˈsent/", "meaning": "sự đồng ý có hiểu biết", "example": "Informed consent must be obtained before any medical procedure or research study."},
            {"word": "patient autonomy", "ipa": "/ˈpeɪ.ʃənt ɔːˈtɒn.ə.mi/", "meaning": "quyền tự quyết của bệnh nhân", "example": "Patient autonomy means respecting a person's right to make their own health decisions."},
            {"word": "medical negligence", "ipa": "/ˈmed.ɪ.kəl ˈneɡ.lɪ.dʒəns/", "meaning": "sơ suất y tế", "example": "Medical negligence can result in serious harm to patients and legal consequences for providers."},
            {"word": "triage protocol", "ipa": "/ˈtriː.ɑːʒ ˈprəʊ.tə.kɒl/", "meaning": "quy trình phân loại bệnh nhân ưu tiên", "example": "The triage protocol prioritizes patients by the severity of their condition."},
            {"word": "multimorbidity", "ipa": "/ˌmʌl.tɪ.mɔːˈbɪd.ɪ.ti/", "meaning": "đa bệnh", "example": "Multimorbidity, or having multiple chronic conditions, is increasingly common in older patients."},
            {"word": "syndemic", "ipa": "/sɪnˈdem.ɪk/", "meaning": "synemic (nhiều dịch bệnh tương tác)", "example": "A syndemic occurs when multiple epidemics interact and worsen each other's impact."},
            {"word": "planetary health", "ipa": "/ˈplæn.ɪ.tər.i helθ/", "meaning": "sức khỏe hành tinh", "example": "Planetary health studies the impact of human activities on the natural world and human well-being."},
            {"word": "one health approach", "ipa": "/wʌn helθ əˈprəʊtʃ/", "meaning": "tiếp cận Sức khỏe Một", "example": "The one health approach recognizes that human, animal, and environmental health are interconnected."},
            {"word": "clinical genomics", "ipa": "/ˈklɪn.ɪ.kəl dʒɪˈnəʊ.mɪks/", "meaning": "bộ gen học lâm sàng", "example": "Clinical genomics integrates genetic data into patient care to improve outcomes."},
            {"word": "immunogenomics", "ipa": "/ˌɪm.jʊ.nəʊ.dʒɪˈnəʊ.mɪks/", "meaning": "miễn dịch bộ gen học", "example": "Immunogenomics links genetic variation to immune response and disease susceptibility."},
            {"word": "adverse childhood experiences", "ipa": "/ˈæd.vɜːs ˈtʃaɪld.hʊd ɪkˈspɪər.i.ənsɪz/", "meaning": "trải nghiệm bất lợi thời thơ ấu", "example": "Adverse childhood experiences have lifelong effects on mental and physical health."},
            {"word": "allostatic load", "ipa": "/ˌæl.əˈstæt.ɪk ləʊd/", "meaning": "tải tích lũy của stress mãn tính", "example": "High allostatic load from chronic stress accelerates biological aging."},
            {"word": "neuroimmunology", "ipa": "/ˌnjʊər.əʊˌɪm.jʊˈnɒl.ə.dʒi/", "meaning": "miễn dịch thần kinh học", "example": "Neuroimmunology investigates the interaction between the nervous and immune systems."},
            {"word": "clinical decision support", "ipa": "/ˈklɪn.ɪ.kəl dɪˈsɪʒ.ən səˈpɔːt/", "meaning": "hỗ trợ quyết định lâm sàng", "example": "Clinical decision support systems alert doctors to potential drug interactions."},
            {"word": "real-world evidence", "ipa": "/ˌrɪəl wɜːld ˈev.ɪ.dəns/", "meaning": "bằng chứng thực tế", "example": "Real-world evidence from patient databases supplements clinical trial data."},
            {"word": "hospital-acquired infection", "ipa": "/ˈhɒs.pɪ.təl əˈkwaɪəd ɪnˈfek.ʃən/", "meaning": "nhiễm khuẩn bệnh viện", "example": "Hospital-acquired infections remain a significant challenge in healthcare settings."},
            {"word": "antimicrobial stewardship", "ipa": "/ˌæn.ti.maɪˈkrəʊ.bi.əl ˈstjuː.əd.ʃɪp/", "meaning": "quản lý sử dụng kháng sinh", "example": "Antimicrobial stewardship programs promote appropriate use of antibiotics."},
            {"word": "longitudinal biomarker study", "ipa": "/ˌlɒŋ.dʒɪˈtjuː.dɪ.nəl ˈbaɪ.əʊˌmɑː.kər ˈstʌd.i/", "meaning": "nghiên cứu dấu ấn sinh học dài hạn", "example": "A longitudinal biomarker study tracked inflammatory markers over five years."},
            {"word": "phenome-wide association study", "ipa": "/ˈfiː.nəʊm waɪd əˌsəʊ.siˈeɪ.ʃən ˈstʌd.i/", "meaning": "nghiên cứu hiệu ứng kiểu hình rộng", "example": "A phenome-wide association study identifies relationships between genetic variants and diverse traits."},
            {"word": "polygenic risk score", "ipa": "/ˌpɒl.iˈdʒen.ɪk rɪsk skɔːr/", "meaning": "điểm nguy cơ đa gen", "example": "A polygenic risk score estimates an individual's genetic predisposition to a disease."},
            {"word": "microfluidics in diagnostics", "ipa": "/ˌmaɪ.krəʊ.fluˈɪd.ɪks ɪn ˌdaɪ.əɡˈnɒs.tɪks/", "meaning": "vi lỏng học trong chẩn đoán", "example": "Microfluidics in diagnostics enables rapid testing with tiny amounts of blood."},
        ],
    },
    "interview": {
        "A1": [
            {"word": "name", "ipa": "/neɪm/", "meaning": "tên", "example": "Please tell me your name and where you are from."},
            {"word": "job", "ipa": "/ʤɑb/", "meaning": "công việc", "example": "I am looking for a job as a teacher."},
            {"word": "work", "ipa": "/wɜːk/", "meaning": "làm việc", "example": "She works at a hospital as a nurse."},
            {"word": "hello", "ipa": "/həˈləʊ/", "meaning": "xin chào", "example": "Hello! My name is Minh and I am applying for this position."},
            {"word": "please", "ipa": "/pliːz/", "meaning": "làm ơn", "example": "Please sit down and make yourself comfortable."},
            {"word": "thank you", "ipa": "/ˈθæŋk juː/", "meaning": "cảm ơn", "example": "Thank you for giving me this opportunity to interview."},
            {"word": "yes", "ipa": "/jes/", "meaning": "có, vâng", "example": "Yes, I have experience working in customer service."},
            {"word": "no", "ipa": "/nəʊ/", "meaning": "không", "example": "No, I have not worked in this field before, but I am eager to learn."},
            {"word": "school", "ipa": "/skuːl/", "meaning": "trường học", "example": "I graduated from school three years ago."},
            {"word": "study", "ipa": "/ˈstʌd.i/", "meaning": "học", "example": "I study English every day to improve my skills."},
            {"word": "learn", "ipa": "/lɜːn/", "meaning": "học hỏi", "example": "I am eager to learn new things in this position."},
            {"word": "speak", "ipa": "/spiːk/", "meaning": "nói", "example": "I can speak English and Vietnamese fluently."},
            {"word": "read", "ipa": "/riːd/", "meaning": "đọc", "example": "I read a lot to improve my professional knowledge."},
            {"word": "write", "ipa": "/raɪt/", "meaning": "viết", "example": "I can write clear reports and emails in English."},
            {"word": "help", "ipa": "/help/", "meaning": "giúp đỡ", "example": "I enjoy helping customers solve their problems."},
            {"word": "like", "ipa": "/laɪk/", "meaning": "thích", "example": "I like working with people and solving problems."},
            {"word": "team", "ipa": "/tiːm/", "meaning": "đội nhóm", "example": "I enjoy working as part of a team."},
            {"word": "office", "ipa": "/ˈɒf.ɪs/", "meaning": "văn phòng", "example": "I have experience working in an office environment."},
            {"word": "computer", "ipa": "/kəmˈpjuː.tər/", "meaning": "máy tính", "example": "I use a computer every day for my work."},
            {"word": "phone", "ipa": "/fəʊn/", "meaning": "điện thoại", "example": "I am comfortable communicating by phone with customers."},
            {"word": "email", "ipa": "/ˈiː.meɪl/", "meaning": "email", "example": "I respond to emails quickly and professionally."},
            {"word": "meeting", "ipa": "/ˈmiː.tɪŋ/", "meaning": "cuộc họp", "example": "I attend team meetings every Monday morning."},
            {"word": "question", "ipa": "/ˈkwes.tʃən/", "meaning": "câu hỏi", "example": "Do you have any questions for me?"},
            {"word": "answer", "ipa": "/ˈɑːn.sər/", "meaning": "câu trả lời", "example": "I will try to answer your questions honestly."},
            {"word": "salary", "ipa": "/ˈsæl.ər.i/", "meaning": "lương", "example": "My expected salary is around 15 million VND per month."},
            {"word": "hour", "ipa": "/aʊər/", "meaning": "giờ làm việc", "example": "I am available to work full-time, 40 hours a week."},
            {"word": "experience", "ipa": "/ɪkˈspɪər.i.əns/", "meaning": "kinh nghiệm", "example": "I have two years of experience in customer service."},
            {"word": "skill", "ipa": "/skɪl/", "meaning": "kỹ năng", "example": "I have strong communication and teamwork skills."},
            {"word": "strong", "ipa": "/strɒŋ/", "meaning": "mạnh mẽ; nổi bật", "example": "My strongest skill is my ability to work under pressure."},
            {"word": "start", "ipa": "/stɑːt/", "meaning": "bắt đầu", "example": "I can start the job as soon as next week."},
            {"word": "finish", "ipa": "/ˈfɪn.ɪʃ/", "meaning": "kết thúc; hoàn thành", "example": "I always finish my work before the deadline."},
            {"word": "good", "ipa": "/ɡʊd/", "meaning": "tốt, giỏi", "example": "I am good at organizing tasks and managing my time."},
            {"word": "problem", "ipa": "/ˈprɒb.ləm/", "meaning": "vấn đề", "example": "I enjoy finding creative solutions to difficult problems."},
            {"word": "friend", "ipa": "/frend/", "meaning": "đồng nghiệp; bạn bè", "example": "I get along well with friends and coworkers."},
            {"word": "happy", "ipa": "/ˈhæp.i/", "meaning": "vui vẻ; hài lòng", "example": "I am happy to take on new responsibilities."},
            {"word": "goal", "ipa": "/ɡəʊl/", "meaning": "mục tiêu", "example": "My goal is to grow professionally within this company."},
            {"word": "future", "ipa": "/ˈfjuː.tʃər/", "meaning": "tương lai", "example": "In the future, I hope to become a team leader."},
            {"word": "time", "ipa": "/taɪm/", "meaning": "thời gian", "example": "I manage my time well and always meet deadlines."},
            {"word": "day", "ipa": "/deɪ/", "meaning": "ngày (làm việc)", "example": "I work five days a week from Monday to Friday."},
            {"word": "city", "ipa": "/ˈsɪt.i/", "meaning": "thành phố", "example": "I am willing to relocate to another city for the right opportunity."},
            {"word": "travel", "ipa": "/ˈtræv.əl/", "meaning": "Đi du lịch, di chuyển", "example": "I love to travel to new countries."},
            {"word": "language", "ipa": "/ˈlæŋ.ɡwɪdʒ/", "meaning": "ngôn ngữ", "example": "I speak English and Vietnamese as working languages."},
            {"word": "university", "ipa": "/ˌjuː.nɪˈvɜː.sɪ.ti/", "meaning": "trường đại học", "example": "I graduated from the National University last year."},
            {"word": "degree", "ipa": "/dɪˈɡriː/", "meaning": "bằng cấp", "example": "I have a bachelor's degree in Business Administration."},
            {"word": "interview", "ipa": "/ˈɪn.tə.vjuː/", "meaning": "phỏng vấn", "example": "This is my first interview for a full-time position."},
            {"word": "company", "ipa": "/ˈkʌm.pə.ni/", "meaning": "công ty", "example": "I researched your company before attending this interview."},
            {"word": "position", "ipa": "/pəˈzɪʃ.ən/", "meaning": "vị trí công việc", "example": "I am applying for the marketing assistant position."},
            {"word": "apply", "ipa": "/əˈplaɪ/", "meaning": "ứng tuyển", "example": "I applied for this job because I believe in your company's mission."},
            {"word": "resume", "ipa": "/ˈrez.jʊ.meɪ/", "meaning": "CV, sơ yếu lý lịch", "example": "I brought a printed copy of my resume to the interview."},
            {"word": "introduce", "ipa": "/ˌɪn.trəˈdjuːs/", "meaning": "giới thiệu bản thân", "example": "Please allow me to introduce myself to the panel."},
        ],
        "A2": [
            {"word": "qualification", "ipa": "/ˌkwɒl.ɪ.fɪˈkeɪ.ʃən/", "meaning": "bằng cấp, chứng chỉ", "example": "She has excellent qualifications for this role."},
            {"word": "professional", "ipa": "/prəˈfeʃ.ən.əl/", "meaning": "chuyên nghiệp", "example": "I always maintain a professional attitude at work."},
            {"word": "responsibility", "ipa": "/rɪˌspɒn.sɪˈbɪl.ɪ.ti/", "meaning": "trách nhiệm", "example": "My main responsibility was handling customer complaints."},
            {"word": "achievement", "ipa": "/əˈtʃiːv.mənt/", "meaning": "thành tích", "example": "My greatest achievement was increasing sales by 30%."},
            {"word": "weakness", "ipa": "/ˈwiːk.nəs/", "meaning": "điểm yếu", "example": "My weakness is that I sometimes take on too many tasks at once."},
            {"word": "strength", "ipa": "/streŋθ/", "meaning": "điểm mạnh", "example": "My greatest strength is my ability to communicate clearly."},
            {"word": "challenge", "ipa": "/ˈʧælənʤ/", "meaning": "thách thức", "example": "I see challenges as opportunities to grow and improve."},
            {"word": "deadline", "ipa": "/ˈded.laɪn/", "meaning": "hạn chót", "example": "I always prioritize my tasks to meet deadlines."},
            {"word": "motivated", "ipa": "/ˈməʊ.tɪ.veɪ.tɪd/", "meaning": "có động lực", "example": "I am motivated by the opportunity to make a real impact."},
            {"word": "communicate", "ipa": "/kəˈmjuː.nɪ.keɪt/", "meaning": "giao tiếp", "example": "I communicate effectively with both clients and team members."},
            {"word": "flexible", "ipa": "/ˈflek.sɪ.bəl/", "meaning": "linh hoạt", "example": "I am flexible and can adapt to changing priorities."},
            {"word": "organized", "ipa": "/ˈɔː.ɡən.aɪzd/", "meaning": "có tổ chức", "example": "I am a very organized person who plans tasks carefully."},
            {"word": "problem-solving", "ipa": "/ˈprɒb.ləm ˌsɒl.vɪŋ/", "meaning": "giải quyết vấn đề", "example": "Problem-solving is one of my strongest skills."},
            {"word": "leadership", "ipa": "/ˈliː.də.ʃɪp/", "meaning": "lãnh đạo", "example": "I demonstrated leadership by managing a team of five people."},
            {"word": "punctual", "ipa": "/ˈpʌŋk.tʃu.əl/", "meaning": "đúng giờ", "example": "I am always punctual and respect others' time."},
            {"word": "adaptable", "ipa": "/əˈdæp.tə.bəl/", "meaning": "dễ thích nghi", "example": "I am adaptable and can work in different environments."},
            {"word": "initiative", "ipa": "/ɪˈnɪʃ.ə.tɪv/", "meaning": "sáng kiến; chủ động", "example": "I take initiative and don't wait to be told what to do."},
            {"word": "reference", "ipa": "/ˈref.ər.əns/", "meaning": "người tham khảo; thư giới thiệu", "example": "I can provide references from my previous employers."},
            {"word": "background", "ipa": "/ˈbæk.ɡraʊnd/", "meaning": "nền tảng", "example": "I have a strong background in sales and customer service."},
            {"word": "career", "ipa": "/kəˈrɪər/", "meaning": "sự nghiệp", "example": "I am passionate about building a long-term career in marketing."},
            {"word": "contribution", "ipa": "/ˌkɒn.trɪˈbjuː.ʃən/", "meaning": "đóng góp", "example": "I believe I can make a valuable contribution to your team."},
            {"word": "benefit", "ipa": "/ˈben.ɪ.fɪt/", "meaning": "phúc lợi, quyền lợi", "example": "I would like to know more about the employee benefits."},
            {"word": "promotion", "ipa": "/prəˈməʊ.ʃən/", "meaning": "thăng chức", "example": "I hope to earn a promotion after proving my abilities."},
            {"word": "training", "ipa": "/ˈtreɪ.nɪŋ/", "meaning": "đào tạo", "example": "I am committed to continuous learning and training."},
            {"word": "full-time", "ipa": "/ˌfʊlˈtaɪm/", "meaning": "toàn thời gian", "example": "I am looking for a full-time position with growth opportunities."},
            {"word": "part-time", "ipa": "/ˌpɑːtˈtaɪm/", "meaning": "bán thời gian", "example": "I am open to part-time work while I continue my studies."},
            {"word": "internship", "ipa": "/ˈɪn.tɜːn.ʃɪp/", "meaning": "thực tập", "example": "I completed a six-month internship at a marketing agency."},
            {"word": "volunteer", "ipa": "/ˌvɒl.ənˈtɪər/", "meaning": "tình nguyện", "example": "I volunteered at a local charity to gain work experience."},
            {"word": "project", "ipa": "/ˈprɒdʒ.ekt/", "meaning": "dự án", "example": "I managed a project that improved customer satisfaction by 20%."},
            {"word": "report", "ipa": "/rɪˈpɔːt/", "meaning": "báo cáo", "example": "I wrote weekly reports for my manager."},
            {"word": "customer", "ipa": "/ˈkʌs.tə.mər/", "meaning": "khách hàng", "example": "I enjoy working directly with customers to solve their problems."},
            {"word": "client", "ipa": "/ˈklaɪ.ənt/", "meaning": "khách hàng (thương mại)", "example": "I managed relationships with five major clients."},
            {"word": "supervisor", "ipa": "/ˈsuː.pə.vaɪ.zər/", "meaning": "người giám sát", "example": "My supervisor praised my attention to detail."},
            {"word": "colleague", "ipa": "/ˈkɒl.iːɡ/", "meaning": "đồng nghiệp", "example": "I enjoy collaborating with my colleagues on complex projects."},
            {"word": "workplace", "ipa": "/ˈwɜːk.pleɪs/", "meaning": "môi trường làm việc", "example": "I thrive in a positive and supportive workplace."},
            {"word": "culture", "ipa": "/ˈkʌl.tʃər/", "meaning": "văn hóa công ty", "example": "I researched your company culture before applying."},
            {"word": "passion", "ipa": "/ˈpæʃ.ən/", "meaning": "đam mê", "example": "I have a real passion for digital marketing."},
            {"word": "honest", "ipa": "/ˈɒn.ɪst/", "meaning": "trung thực", "example": "I believe in being honest and transparent in all my work."},
            {"word": "reliable", "ipa": "/rɪˈlaɪ.ə.bəl/", "meaning": "đáng tin cậy", "example": "My previous employer described me as reliable and hardworking."},
            {"word": "hardworking", "ipa": "/ˈhɑːdˌwɜː.kɪŋ/", "meaning": "chăm chỉ", "example": "I am hardworking and always give 100% effort to my tasks."},
            {"word": "creative", "ipa": "/kriˈeɪ.tɪv/", "meaning": "sáng tạo", "example": "I am a creative thinker who enjoys finding innovative solutions."},
            {"word": "analytical", "ipa": "/ˌæn.əˈlɪt.ɪ.kəl/", "meaning": "có tư duy phân tích", "example": "I have strong analytical skills developed through data analysis work."},
            {"word": "detail-oriented", "ipa": "/ˈdiː.teɪl ˌɔː.ri.en.tɪd/", "meaning": "chú ý đến chi tiết", "example": "I am very detail-oriented and rarely make careless mistakes."},
            {"word": "self-motivated", "ipa": "/ˌself ˈməʊ.tɪ.veɪ.tɪd/", "meaning": "tự thúc đẩy bản thân", "example": "I am self-motivated and do not need constant supervision."},
            {"word": "independent", "ipa": "/ˌɪn.dɪˈpen.dənt/", "meaning": "độc lập", "example": "I can work independently and manage my own workload."},
            {"word": "ambitious", "ipa": "/æmˈbɪʃ.əs/", "meaning": "tham vọng", "example": "I am ambitious and always look for ways to grow professionally."},
            {"word": "enthusiastic", "ipa": "/ɪnˌθjuː.ziˈæs.tɪk/", "meaning": "nhiệt tình", "example": "I am enthusiastic about the opportunity to join your team."},
            {"word": "curious", "ipa": "/ˈkjʊər.i.əs/", "meaning": "tò mò, ham học hỏi", "example": "I am naturally curious and always want to understand how things work."},
            {"word": "collaborative", "ipa": "/kəˈlæb.ər.ə.tɪv/", "meaning": "tinh thần hợp tác", "example": "I am collaborative and believe the best results come from teamwork."},
            {"word": "confident", "ipa": "/ˈkɒn.fɪ.dənt/", "meaning": "tự tin", "example": "I am confident in my ability to add value to your organization."},
        ],
        "B1": [
            {"word": "competency", "ipa": "/ˈkɒm.pɪ.tən.si/", "meaning": "năng lực cốt lõi", "example": "The interviewer assessed my competency in data analysis."},
            {"word": "behavioral interview", "ipa": "/bɪˈheɪ.vjər.əl ˈɪn.tə.vjuː/", "meaning": "phỏng vấn hành vi", "example": "A behavioral interview asks you to describe past experiences."},
            {"word": "STAR method", "ipa": "/stɑːr ˈmeθ.əd/", "meaning": "phương pháp STAR trả lời phỏng vấn", "example": "Use the STAR method to structure your answers: Situation, Task, Action, Result."},
            {"word": "transferable skills", "ipa": "/trænsˈfɜː.rə.bəl skɪlz/", "meaning": "kỹ năng chuyển đổi được", "example": "My transferable skills from retail include customer service and time management."},
            {"word": "value proposition", "ipa": "/ˈvæl.juː ˌprɒp.əˈzɪʃ.ən/", "meaning": "giá trị bản thân mang lại", "example": "Be clear about your value proposition when answering 'Why should we hire you?'"},
            {"word": "elevator pitch", "ipa": "/ˈel.ɪ.veɪ.tər pɪtʃ/", "meaning": "bài giới thiệu bản thân ngắn gọn", "example": "Prepare a 60-second elevator pitch about yourself for the interview."},
            {"word": "career trajectory", "ipa": "/kəˈrɪər trəˈdʒek.tər.i/", "meaning": "lộ trình sự nghiệp", "example": "The interviewer asked about my career trajectory over the next five years."},
            {"word": "gap year", "ipa": "/ɡæp jɪər/", "meaning": "năm nghỉ giữa công việc/học tập", "example": "I used my gap year to volunteer abroad and develop new skills."},
            {"word": "cover letter", "ipa": "/ˈkʌv.ər ˌlet.ər/", "meaning": "thư xin việc", "example": "A well-written cover letter sets you apart from other candidates."},
            {"word": "job description", "ipa": "/dʒɒb dɪˈskrɪp.ʃən/", "meaning": "mô tả công việc", "example": "I matched my skills carefully to the job description before applying."},
            {"word": "key performance indicators", "ipa": "/kiː pəˈfɔː.məns ˈɪn.dɪ.keɪ.tərz/", "meaning": "chỉ số hiệu suất chính", "example": "I exceeded my key performance indicators by 15% last quarter."},
            {"word": "soft skills", "ipa": "/sɒft skɪlz/", "meaning": "kỹ năng mềm", "example": "Employers value soft skills like communication and emotional intelligence."},
            {"word": "hard skills", "ipa": "/hɑːd skɪlz/", "meaning": "kỹ năng cứng", "example": "My hard skills include Python programming and data analysis."},
            {"word": "networking", "ipa": "/ˈnet.wɜː.kɪŋ/", "meaning": "xây dựng mạng lưới quan hệ", "example": "Networking helped me find out about this job opening."},
            {"word": "headhunter", "ipa": "/ˈhed.hʌn.tər/", "meaning": "chuyên viên tuyển dụng đầu ngành", "example": "A headhunter contacted me about an exciting opportunity."},
            {"word": "recruiter", "ipa": "/rɪˈkruː.tər/", "meaning": "người tuyển dụng", "example": "The recruiter explained the role and salary range in detail."},
            {"word": "panel interview", "ipa": "/ˈpæn.əl ˈɪn.tə.vjuː/", "meaning": "phỏng vấn hội đồng", "example": "A panel interview involves multiple interviewers asking questions simultaneously."},
            {"word": "follow-up email", "ipa": "/ˈfɒl.əʊ.ʌp ˈiː.meɪl/", "meaning": "email theo dõi sau phỏng vấn", "example": "Send a follow-up email within 24 hours of the interview."},
            {"word": "rejection", "ipa": "/rɪˈdʒek.ʃən/", "meaning": "bị từ chối (tuyển dụng)", "example": "A rejection is an opportunity to learn and improve for the next interview."},
            {"word": "offer letter", "ipa": "/ˈɒf.ər ˌlet.ər/", "meaning": "thư mời nhận việc", "example": "She received an offer letter with a competitive salary package."},
            {"word": "probation period", "ipa": "/prəˈbeɪ.ʃən ˌpɪər.i.əd/", "meaning": "thời gian thử việc", "example": "The probation period lasts three months before you become a permanent employee."},
            {"word": "onboarding", "ipa": "/ˈɒn.bɔː.dɪŋ/", "meaning": "quy trình tiếp nhận nhân viên mới", "example": "The onboarding process includes orientation, training, and team introductions."},
            {"word": "salary negotiation", "ipa": "/ˈsæl.ər.i nɪˌɡəʊ.ʃiˈeɪ.ʃən/", "meaning": "đàm phán lương", "example": "Don't be afraid to engage in salary negotiation when you receive an offer."},
            {"word": "notice period", "ipa": "/ˈnəʊ.tɪs ˌpɪər.i.əd/", "meaning": "thời gian báo trước khi nghỉ việc", "example": "My current notice period is one month."},
            {"word": "body language", "ipa": "/ˈbɒd.i ˌlæŋ.ɡwɪdʒ/", "meaning": "ngôn ngữ cơ thể", "example": "Good body language includes eye contact, a firm handshake, and upright posture."},
            {"word": "eye contact", "ipa": "/aɪ ˈkɒn.tækt/", "meaning": "giao tiếp bằng mắt", "example": "Maintaining eye contact shows confidence and engagement."},
            {"word": "active listening", "ipa": "/ˈæk.tɪv ˈlɪs.ən.ɪŋ/", "meaning": "lắng nghe chủ động", "example": "Active listening involves nodding, paraphrasing, and asking clarifying questions."},
            {"word": "structured interview", "ipa": "/ˈstrʌk.tʃərd ˈɪn.tə.vjuː/", "meaning": "phỏng vấn có cấu trúc", "example": "A structured interview uses the same set of questions for all candidates."},
            {"word": "unstructured interview", "ipa": "/ˈʌnˌstrʌk.tʃərd ˈɪn.tə.vjuː/", "meaning": "phỏng vấn không có cấu trúc", "example": "An unstructured interview is more like a natural conversation."},
            {"word": "case interview", "ipa": "/keɪs ˈɪn.tə.vjuː/", "meaning": "phỏng vấn tình huống", "example": "Management consulting firms often use case interviews to assess analytical skills."},
            {"word": "technical interview", "ipa": "/ˈtek.nɪ.kəl ˈɪn.tə.vjuː/", "meaning": "phỏng vấn kỹ thuật", "example": "I practiced coding problems to prepare for the technical interview."},
            {"word": "aptitude test", "ipa": "/ˈæp.tɪ.tjuːd test/", "meaning": "bài kiểm tra năng khiếu", "example": "The aptitude test measured my verbal and numerical reasoning skills."},
            {"word": "psychometric test", "ipa": "/ˌsaɪ.kəˈmet.rɪk test/", "meaning": "bài kiểm tra tâm lý", "example": "Many employers use psychometric tests to assess personality and cognitive ability."},
            {"word": "group discussion", "ipa": "/ɡruːp dɪˈskʌʃ.ən/", "meaning": "thảo luận nhóm", "example": "The group discussion assessed our teamwork and leadership skills."},
            {"word": "assessment center", "ipa": "/əˈses.mənt ˈsen.tər/", "meaning": "trung tâm đánh giá ứng viên", "example": "The assessment center involved exercises, role plays, and group activities."},
            {"word": "role play", "ipa": "/rəʊl pleɪ/", "meaning": "đóng vai tình huống", "example": "The role play exercise tested how I handle difficult customer situations."},
            {"word": "presentation skills", "ipa": "/ˌprez.ənˈteɪ.ʃən skɪlz/", "meaning": "kỹ năng thuyết trình", "example": "Strong presentation skills are essential for client-facing roles."},
            {"word": "critical thinking", "ipa": "/ˈkrɪt.ɪ.kəl ˈθɪŋk.ɪŋ/", "meaning": "tư duy phản biện", "example": "Critical thinking is highly valued in problem-solving roles."},
            {"word": "time management", "ipa": "/taɪm ˈmæn.ɪdʒ.mənt/", "meaning": "quản lý thời gian", "example": "I use time management techniques to prioritize my daily tasks."},
            {"word": "conflict resolution", "ipa": "/ˈkɒn.flɪkt ˌrez.əˈluː.ʃən/", "meaning": "giải quyết xung đột", "example": "I resolved a conflict between two colleagues through open communication."},
            {"word": "emotional intelligence", "ipa": "/ɪˌməʊ.ʃən.əl ɪnˈtel.ɪ.dʒəns/", "meaning": "trí tuệ cảm xúc", "example": "Emotional intelligence helps you manage relationships at work effectively."},
            {"word": "cultural fit", "ipa": "/ˈkʌl.tʃər.əl fɪt/", "meaning": "phù hợp văn hóa công ty", "example": "Interviewers assess cultural fit to ensure long-term employee satisfaction."},
            {"word": "work ethic", "ipa": "/wɜːk ˈeθ.ɪk/", "meaning": "đạo đức làm việc", "example": "I have a strong work ethic and always give my best effort."},
            {"word": "resilience", "ipa": "/rɪˈzɪl.i.əns/", "meaning": "sức bền tinh thần", "example": "Resilience is key to bouncing back from setbacks and challenges."},
            {"word": "growth mindset", "ipa": "/ɡrəʊθ ˈmaɪnd.set/", "meaning": "tư duy phát triển", "example": "I have a growth mindset and always look for opportunities to improve."},
            {"word": "self-awareness", "ipa": "/ˌself əˈweər.nəs/", "meaning": "tự nhận thức bản thân", "example": "Self-awareness helps me identify my weaknesses and work on them."},
            {"word": "mentoring", "ipa": "/ˈmen.tər.ɪŋ/", "meaning": "cố vấn, hướng dẫn", "example": "I benefited greatly from mentoring by an experienced senior colleague."},
            {"word": "upskilling", "ipa": "/ˌʌpˈskɪl.ɪŋ/", "meaning": "nâng cao kỹ năng", "example": "I invested in upskilling by completing online certifications."},
            {"word": "long-term vision", "ipa": "/lɒŋ tɜːm ˈvɪʒ.ən/", "meaning": "tầm nhìn dài hạn", "example": "My long-term vision is to lead a product team in a technology company."},
            {"word": "company values", "ipa": "/ˈkʌm.pə.ni ˈvæl.juːz/", "meaning": "giá trị cốt lõi công ty", "example": "I researched the company values and they align with my own principles."},
        ],
        "B2": [
            {"word": "executive search", "ipa": "/ɪɡˈzek.jʊ.tɪv sɜːtʃ/", "meaning": "tuyển dụng cấp điều hành", "example": "An executive search firm was engaged to find a new CEO."},
            {"word": "competency-based interview", "ipa": "/ˈkɒm.pɪ.tən.si beɪst ˈɪn.tə.vjuː/", "meaning": "phỏng vấn dựa trên năng lực", "example": "A competency-based interview uses structured questions to assess specific skills."},
            {"word": "situational judgment test", "ipa": "/ˌsɪtʃ.uˈeɪ.ʃən.əl ˈdʒʌdʒ.mənt test/", "meaning": "bài kiểm tra phán xét tình huống", "example": "A situational judgment test presents workplace scenarios to evaluate decision-making."},
            {"word": "employer branding", "ipa": "/ɪmˈplɔɪ.ər ˈbræn.dɪŋ/", "meaning": "thương hiệu nhà tuyển dụng", "example": "Strong employer branding helps attract top talent to the organization."},
            {"word": "talent acquisition", "ipa": "/ˈtæl.ənt ˌæk.wɪˈzɪʃ.ən/", "meaning": "thu hút và tuyển dụng tài năng", "example": "Talent acquisition is a strategic approach to finding the right people."},
            {"word": "succession planning", "ipa": "/səkˈseʃ.ən ˈplæn.ɪŋ/", "meaning": "kế hoạch kế nhiệm", "example": "Succession planning ensures continuity by identifying future leaders."},
            {"word": "organizational fit", "ipa": "/ˌɔː.ɡən.aɪˈzeɪ.ʃən.əl fɪt/", "meaning": "sự phù hợp với tổ chức", "example": "Organizational fit goes beyond skills — it includes values and work style."},
            {"word": "counter-offer", "ipa": "/ˌkaʊn.tərˈɒf.ər/", "meaning": "đề nghị đối nghịch (khi nhận việc)", "example": "She received a counter-offer from her current employer to stay."},
            {"word": "total compensation package", "ipa": "/ˈtəʊ.təl ˌkɒm.penˈseɪ.ʃən ˈpæk.ɪdʒ/", "meaning": "gói đãi ngộ toàn diện", "example": "The total compensation package includes salary, bonus, and stock options."},
            {"word": "equity compensation", "ipa": "/ˈek.wɪ.ti ˌkɒm.penˈseɪ.ʃən/", "meaning": "đãi ngộ bằng cổ phần", "example": "Equity compensation aligns employees' interests with the company's success."},
            {"word": "vesting schedule", "ipa": "/ˈves.tɪŋ ˈʃed.juːl/", "meaning": "lịch trình thực quyền cổ phần", "example": "The vesting schedule releases stock options over a four-year period."},
            {"word": "non-compete agreement", "ipa": "/nɒn kəmˈpiːt əˈɡriː.mənt/", "meaning": "thỏa thuận không cạnh tranh", "example": "She signed a non-compete agreement restricting her from joining rival firms."},
            {"word": "garden leave", "ipa": "/ˈɡɑː.dən liːv/", "meaning": "nghỉ phép có lương khi đang báo nghỉ việc", "example": "He was placed on garden leave during his notice period."},
            {"word": "headcount planning", "ipa": "/ˈhed.kaʊnt ˈplæn.ɪŋ/", "meaning": "lập kế hoạch nhân sự", "example": "Headcount planning ensures the organization has the right number of people."},
            {"word": "talent pipeline", "ipa": "/ˈtæl.ənt ˈpaɪp.laɪn/", "meaning": "nguồn ứng viên tiềm năng dự trữ", "example": "A strong talent pipeline ensures vacancies are filled quickly with quality candidates."},
            {"word": "unconscious bias", "ipa": "/ʌnˈkɒn.ʃəs ˈbaɪ.əs/", "meaning": "định kiến vô thức", "example": "Structured interviews help reduce unconscious bias in hiring decisions."},
            {"word": "diversity and inclusion", "ipa": "/daɪˈvɜː.sɪ.ti ənd ɪnˈkluː.ʒən/", "meaning": "đa dạng và hòa nhập", "example": "The company has a strong commitment to diversity and inclusion in hiring."},
            {"word": "blind recruitment", "ipa": "/blaɪnd rɪˈkruːt.mənt/", "meaning": "tuyển dụng ẩn danh thông tin", "example": "Blind recruitment removes identifying information to reduce bias."},
            {"word": "reference check", "ipa": "/ˈref.ər.əns tʃek/", "meaning": "kiểm tra thông tin tham chiếu", "example": "A reference check confirmed the candidate's experience and character."},
            {"word": "background check", "ipa": "/ˈbæk.ɡraʊnd tʃek/", "meaning": "kiểm tra lý lịch", "example": "All new hires must pass a background check before starting."},
            {"word": "employment gap", "ipa": "/ɪmˈplɔɪ.mənt ɡæp/", "meaning": "khoảng trống trong lịch sử công việc", "example": "Be prepared to explain any employment gap in your resume."},
            {"word": "career pivot", "ipa": "/kəˈrɪər ˈpɪv.ət/", "meaning": "chuyển hướng nghề nghiệp", "example": "She made a successful career pivot from finance to technology."},
            {"word": "skills gap", "ipa": "/skɪlz ɡæp/", "meaning": "khoảng cách kỹ năng", "example": "A skills gap assessment revealed training needs across the organization."},
            {"word": "human capital", "ipa": "/ˈhjuː.mən ˈkæp.ɪ.təl/", "meaning": "vốn nhân lực", "example": "Organizations that invest in human capital outperform their competitors."},
            {"word": "attrition rate", "ipa": "/əˈtrɪʃ.ən reɪt/", "meaning": "tỷ lệ nghỉ việc", "example": "The company reduced its attrition rate by improving employee satisfaction."},
            {"word": "retention strategy", "ipa": "/rɪˈten.ʃən ˈstræt.ɪ.dʒi/", "meaning": "chiến lược giữ chân nhân viên", "example": "Competitive salaries and flexible work are key retention strategies."},
            {"word": "employee engagement", "ipa": "/ɪmˈplɔɪ.iː ɪnˈɡeɪdʒ.mənt/", "meaning": "sự gắn kết của nhân viên", "example": "High employee engagement leads to better productivity and lower turnover."},
            {"word": "performance management", "ipa": "/pəˈfɔː.məns ˈmæn.ɪdʒ.mənt/", "meaning": "quản lý hiệu suất", "example": "Performance management includes regular reviews, feedback, and goal-setting."},
            {"word": "360-degree feedback", "ipa": "/θriː ˈhʌn.drəd ən ˈsɪk.sti dɪˈɡriː ˈfiːd.bæk/", "meaning": "phản hồi 360 độ", "example": "360-degree feedback collects input from peers, subordinates, and managers."},
            {"word": "organizational development", "ipa": "/ˌɔː.ɡən.aɪˈzeɪ.ʃən.əl dɪˈvel.əp.mənt/", "meaning": "phát triển tổ chức", "example": "Organizational development initiatives improve culture and productivity."},
            {"word": "competency framework", "ipa": "/ˈkɒm.pɪ.tən.si ˈfreɪm.wɜːk/", "meaning": "khung năng lực", "example": "The competency framework defines the skills expected at each level."},
            {"word": "work-life balance", "ipa": "/wɜːk laɪf ˈbæl.əns/", "meaning": "cân bằng công việc và cuộc sống", "example": "This company offers excellent work-life balance with flexible hours."},
            {"word": "remote work policy", "ipa": "/rɪˈməʊt wɜːk ˈpɒl.ɪ.si/", "meaning": "chính sách làm việc từ xa", "example": "The company's remote work policy allows two days at home per week."},
            {"word": "hybrid work model", "ipa": "/ˈhaɪ.brɪd wɜːk ˈmɒd.əl/", "meaning": "mô hình làm việc kết hợp", "example": "The hybrid work model combines office and remote working."},
            {"word": "total rewards", "ipa": "/ˈtəʊ.təl rɪˈwɔːdz/", "meaning": "tổng đãi ngộ (lương + phúc lợi)", "example": "Total rewards include base salary, bonuses, health benefits, and career development."},
            {"word": "pay equity", "ipa": "/peɪ ˈek.wɪ.ti/", "meaning": "công bằng về lương", "example": "Pay equity analysis ensures all employees are compensated fairly."},
            {"word": "employment contract", "ipa": "/ɪmˈplɔɪ.mənt ˈkɒn.trækt/", "meaning": "hợp đồng lao động", "example": "Read the employment contract carefully before signing."},
            {"word": "labor law compliance", "ipa": "/ˈleɪ.bər lɔː kəmˈplaɪ.əns/", "meaning": "tuân thủ luật lao động", "example": "HR ensures the company is always in compliance with labor laws."},
            {"word": "redundancy", "ipa": "/rɪˈdʌn.dən.si/", "meaning": "thôi việc do dư thừa nhân sự", "example": "She was offered a redundancy package when her department was restructured."},
            {"word": "outplacement services", "ipa": "/ˈaʊt.pleɪs.mənt ˈsɜː.vɪ.sɪz/", "meaning": "dịch vụ hỗ trợ tìm việc sau thôi việc", "example": "The company provided outplacement services to help redundant employees find new jobs."},
            {"word": "employer of choice", "ipa": "/ɪmˈplɔɪ.ər əv tʃɔɪs/", "meaning": "nhà tuyển dụng được ưu tiên", "example": "The company aspires to become an employer of choice in the industry."},
            {"word": "candidate experience", "ipa": "/ˈkæn.dɪ.dɪt ɪkˈspɪər.i.əns/", "meaning": "trải nghiệm ứng viên", "example": "A positive candidate experience improves the company's reputation as an employer."},
            {"word": "time-to-hire", "ipa": "/taɪm tə haɪər/", "meaning": "thời gian từ đăng tin đến tuyển xong", "example": "Reducing time-to-hire is a key goal for the recruitment team."},
            {"word": "cost-per-hire", "ipa": "/kɒst pər haɪər/", "meaning": "chi phí tuyển dụng mỗi nhân viên", "example": "The cost-per-hire includes advertising, agency fees, and onboarding costs."},
            {"word": "quality of hire", "ipa": "/ˈkwɒl.ɪ.ti əv haɪər/", "meaning": "chất lượng tuyển dụng", "example": "Quality of hire is measured by new employees' performance and retention rates."},
            {"word": "workforce planning", "ipa": "/ˈwɜːk.fɔːs ˈplæn.ɪŋ/", "meaning": "lập kế hoạch lực lượng lao động", "example": "Strategic workforce planning aligns staffing with business goals."},
            {"word": "talent management", "ipa": "/ˈtæl.ənt ˈmæn.ɪdʒ.mənt/", "meaning": "quản lý tài năng", "example": "Effective talent management develops and retains high-performing employees."},
            {"word": "leadership pipeline", "ipa": "/ˈliː.də.ʃɪp ˈpaɪp.laɪn/", "meaning": "nguồn lãnh đạo kế cận", "example": "A strong leadership pipeline ensures the organization has future leaders ready."},
            {"word": "job evaluation", "ipa": "/dʒɒb ɪˌvæl.juˈeɪ.ʃən/", "meaning": "đánh giá giá trị công việc", "example": "Job evaluation determines the relative value of roles within the organization."},
            {"word": "pay benchmarking", "ipa": "/peɪ ˈbentʃ.mɑː.kɪŋ/", "meaning": "so sánh mức lương thị trường", "example": "Pay benchmarking ensures salaries are competitive within the industry."},
        ],
        "C1": [
            {"word": "metacognitive interview technique", "ipa": "/ˌmet.əˈkɒɡ.nɪ.tɪv ˈɪn.tə.vjuː tekˈniːk/", "meaning": "kỹ thuật phỏng vấn siêu nhận thức", "example": "Metacognitive interview techniques ask candidates to reflect on their own thinking processes."},
            {"word": "organizational psychology", "ipa": "/ˌɔː.ɡən.aɪˈzeɪ.ʃən.əl saɪˈkɒl.ə.dʒi/", "meaning": "tâm lý học tổ chức", "example": "Organizational psychology informs how companies design roles and assess performance."},
            {"word": "person-organization fit", "ipa": "/ˈpɜː.sən ˌɔː.ɡən.aɪˈzeɪ.ʃən fɪt/", "meaning": "sự phù hợp người-tổ chức", "example": "Person-organization fit predicts job satisfaction and long-term commitment."},
            {"word": "structured behavioral interview validity", "ipa": "/ˈstrʌk.tʃərd bɪˈheɪ.vjər.əl ˈɪn.tə.vjuː vəˈlɪd.ɪ.ti/", "meaning": "tính hợp lệ của phỏng vấn hành vi có cấu trúc", "example": "Research confirms the high predictive validity of structured behavioral interviews."},
            {"word": "adverse impact", "ipa": "/ˈæd.vɜːs ˈɪm.pækt/", "meaning": "tác động bất lợi (phân biệt đối xử vô ý)", "example": "HR audits test whether selection procedures have an adverse impact on protected groups."},
            {"word": "situational interview", "ipa": "/ˌsɪtʃ.uˈeɪ.ʃən.əl ˈɪn.tə.vjuː/", "meaning": "phỏng vấn tình huống giả định", "example": "A situational interview asks candidates how they would handle hypothetical scenarios."},
            {"word": "criterion validity", "ipa": "/kraɪˈtɪər.i.ən vəˈlɪd.ɪ.ti/", "meaning": "tính hiệu lực tiêu chí", "example": "Criterion validity measures how well an assessment predicts actual job performance."},
            {"word": "construct validity", "ipa": "/ˈkɒn.strʌkt vəˈlɪd.ɪ.ti/", "meaning": "tính hiệu lực cấu trúc", "example": "Construct validity ensures a test measures the psychological trait it claims to assess."},
            {"word": "biographical data (biodata)", "ipa": "/ˌbaɪ.əˈɡræf.ɪ.kəl ˈdeɪ.tə/", "meaning": "dữ liệu tiểu sử ứng viên", "example": "Biodata uses life history information to predict future job performance."},
            {"word": "realistic job preview", "ipa": "/riˈæl.ɪs.tɪk dʒɒb ˈpriː.vjuː/", "meaning": "xem trước thực tế công việc", "example": "A realistic job preview helps candidates self-select out of unsuitable roles."},
            {"word": "social desirability bias", "ipa": "/ˌsəʊ.ʃəl dɪˈzaɪər.ə.bɪl.ɪ.ti ˈbaɪ.əs/", "meaning": "sai lệch do muốn tạo ấn tượng tốt", "example": "Social desirability bias occurs when candidates answer to impress rather than truthfully."},
            {"word": "impression management", "ipa": "/ɪmˈpreʃ.ən ˈmæn.ɪdʒ.mənt/", "meaning": "quản lý ấn tượng", "example": "Candidates engage in impression management to appear more favorable to interviewers."},
            {"word": "halo effect", "ipa": "/ˈheɪ.ləʊ ɪˈfekt/", "meaning": "hiệu ứng hào quang (trong đánh giá)", "example": "Interviewers must guard against the halo effect, where one positive trait colors the whole evaluation."},
            {"word": "recency bias", "ipa": "/ˈriː.sən.si ˈbaɪ.əs/", "meaning": "sai lệch ưu tiên gần đây", "example": "Recency bias causes interviewers to overweight the last things a candidate says."},
            {"word": "confirmatory bias", "ipa": "/kənˈfɜː.mə.tər.i ˈbaɪ.əs/", "meaning": "sai lệch xác nhận", "example": "Confirmatory bias leads interviewers to seek information that supports their first impression."},
            {"word": "anchor bias", "ipa": "/ˈæŋ.kər ˈbaɪ.əs/", "meaning": "sai lệch neo (định kiến ban đầu)", "example": "Anchor bias can distort salary negotiations if the first number stated is unreasonable."},
            {"word": "inter-rater reliability", "ipa": "/ˌɪn.tərˈreɪ.tər rɪˌlaɪ.əˈbɪl.ɪ.ti/", "meaning": "độ tin cậy giữa các đánh giá viên", "example": "Inter-rater reliability ensures different interviewers score candidates consistently."},
            {"word": "assessment validity coefficient", "ipa": "/əˈses.mənt vəˈlɪd.ɪ.ti ˌkəʊ.ɪˈfɪʃ.ənt/", "meaning": "hệ số tính hiệu lực đánh giá", "example": "Work samples have the highest assessment validity coefficient of any selection method."},
            {"word": "predictive analytics (HR)", "ipa": "/prɪˈdɪk.tɪv ˌæn.əˈlɪt.ɪks/", "meaning": "phân tích dự đoán (nhân sự)", "example": "Predictive analytics in HR forecasts which candidates are most likely to succeed."},
            {"word": "people analytics", "ipa": "/ˈpiː.pəl ˌæn.əˈlɪt.ɪks/", "meaning": "phân tích dữ liệu nhân sự", "example": "People analytics helps organizations make data-driven decisions about their workforce."},
            {"word": "AI-assisted recruitment", "ipa": "/ˌeɪˈaɪ əˌsɪs.tɪd rɪˈkruːt.mənt/", "meaning": "tuyển dụng hỗ trợ bởi AI", "example": "AI-assisted recruitment screens resumes faster but must be monitored for bias."},
            {"word": "algorithmic hiring", "ipa": "/ˌæl.ɡəˈrɪð.mɪk ˈhaɪər.ɪŋ/", "meaning": "tuyển dụng bằng thuật toán", "example": "Algorithmic hiring tools must be validated to ensure fair and accurate assessment."},
            {"word": "gamified assessment", "ipa": "/ˈɡeɪm.ɪ.faɪd əˈses.mənt/", "meaning": "đánh giá dạng trò chơi", "example": "Gamified assessments measure cognitive and behavioral traits in an engaging way."},
            {"word": "asynchronous video interview", "ipa": "/eɪˈsɪŋ.krə.nəs ˈvɪd.i.əʊ ˈɪn.tə.vjuː/", "meaning": "phỏng vấn video không đồng bộ", "example": "Asynchronous video interviews let candidates record answers at their own pace."},
            {"word": "neurodiversity in hiring", "ipa": "/ˌnjʊər.əʊ.daɪˈvɜː.sɪ.ti ɪn ˈhaɪər.ɪŋ/", "meaning": "đa dạng thần kinh trong tuyển dụng", "example": "Inclusive hiring processes accommodate neurodiversity to access wider talent pools."},
            {"word": "intersectionality (HR)", "ipa": "/ˌɪn.tə.sek.ʃəˈnæl.ɪ.ti/", "meaning": "giao thoa đa chiều bản sắc (nhân sự)", "example": "Intersectionality in HR recognizes that employees have multiple overlapping identities."},
            {"word": "psychological safety", "ipa": "/ˌsaɪ.kəˈlɒdʒ.ɪ.kəl ˈseɪf.ti/", "meaning": "sự an toàn tâm lý", "example": "Psychological safety allows employees to speak up without fear of judgment."},
            {"word": "values-based recruitment", "ipa": "/ˈvæl.juːz beɪst rɪˈkruːt.mənt/", "meaning": "tuyển dụng dựa trên giá trị", "example": "Values-based recruitment selects candidates who align with the company's mission."},
            {"word": "talent mobility", "ipa": "/ˈtæl.ənt məʊˈbɪl.ɪ.ti/", "meaning": "linh hoạt chuyển dịch nhân tài nội bộ", "example": "Talent mobility allows employees to move across roles and departments."},
            {"word": "gig economy workforce", "ipa": "/ɡɪɡ ɪˈkɒn.ə.mi ˈwɜːk.fɔːs/", "meaning": "lực lượng lao động kinh tế gig", "example": "Managing a gig economy workforce requires new HR policies and practices."},
            {"word": "strategic HR business partner", "ipa": "/strəˈtiː.dʒɪk ˌeɪtʃˈɑː ˈbɪz.nɪs ˌpɑːt.nər/", "meaning": "đối tác kinh doanh HR chiến lược", "example": "A strategic HR business partner aligns people strategy with business objectives."},
            {"word": "organizational resilience", "ipa": "/ˌɔː.ɡən.aɪˈzeɪ.ʃən.əl rɪˈzɪl.i.əns/", "meaning": "khả năng phục hồi tổ chức", "example": "Organizational resilience depends on having adaptable and well-prepared people."},
            {"word": "psychological contract", "ipa": "/ˌsaɪ.kəˈlɒdʒ.ɪ.kəl ˈkɒn.trækt/", "meaning": "hợp đồng tâm lý (kỳ vọng ngầm định)", "example": "Violating the psychological contract damages employee trust and engagement."},
            {"word": "employer value proposition", "ipa": "/ɪmˈplɔɪ.ər ˈvæl.juː ˌprɒp.əˈzɪʃ.ən/", "meaning": "đề xuất giá trị nhà tuyển dụng", "example": "A compelling employer value proposition attracts and retains top talent."},
            {"word": "total workforce management", "ipa": "/ˈtəʊ.təl ˈwɜːk.fɔːs ˈmæn.ɪdʒ.mənt/", "meaning": "quản lý tổng thể lực lượng lao động", "example": "Total workforce management encompasses employees, contractors, and gig workers."},
            {"word": "HR analytics maturity model", "ipa": "/ˌeɪtʃˈɑːr ˌæn.əˈlɪt.ɪks məˈtjʊər.ɪ.ti ˈmɒd.əl/", "meaning": "mô hình trưởng thành phân tích HR", "example": "An HR analytics maturity model maps an organization's progress from reporting to prediction."},
            {"word": "learning agility", "ipa": "/ˈlɜː.nɪŋ əˈdʒɪl.ɪ.ti/", "meaning": "sự nhanh nhạy trong học hỏi", "example": "Learning agility is highly predictive of leadership success in complex environments."},
            {"word": "ambiguity tolerance", "ipa": "/æmˈbɪɡ.jʊ.ɪ.ti ˈtɒl.ər.əns/", "meaning": "khả năng chịu đựng sự mơ hồ", "example": "High ambiguity tolerance allows leaders to make decisions with incomplete information."},
            {"word": "cognitive complexity", "ipa": "/ˈkɒɡ.nɪ.tɪv kəmˈplek.sɪ.ti/", "meaning": "độ phức tạp nhận thức", "example": "Cognitive complexity enables leaders to consider multiple perspectives simultaneously."},
            {"word": "systemic thinking", "ipa": "/sɪˈstem.ɪk ˈθɪŋ.kɪŋ/", "meaning": "tư duy hệ thống", "example": "Systemic thinking helps leaders understand how decisions affect the whole organization."},
            {"word": "transformational leadership potential", "ipa": "/trænsˌfɔː.mə.ʃən.əl ˈliː.də.ʃɪp pəˈten.ʃəl/", "meaning": "tiềm năng lãnh đạo chuyển đổi", "example": "Assessment centers identify candidates with high transformational leadership potential."},
            {"word": "executive presence", "ipa": "/ɪɡˈzek.jʊ.tɪv ˈprez.əns/", "meaning": "phong thái lãnh đạo", "example": "Executive presence involves confidence, communication, and the ability to inspire others."},
            {"word": "political savvy", "ipa": "/pəˈlɪt.ɪ.kəl ˈsæv.i/", "meaning": "sự nhạy bén chính trị tổ chức", "example": "Political savvy helps leaders navigate complex organizational dynamics."},
            {"word": "derailers (leadership)", "ipa": "/dɪˈreɪ.lərz/", "meaning": "yếu tố gây mất phương hướng lãnh đạo", "example": "Common leadership derailers include arrogance, micromanagement, and poor communication."},
            {"word": "dark triad (leadership)", "ipa": "/dɑːk ˈtraɪ.æd/", "meaning": "bộ ba tính cách tối (tâm lý lãnh đạo)", "example": "The dark triad of narcissism, psychopathy, and Machiavellianism poses risks in leaders."},
            {"word": "career anchors", "ipa": "/kəˈrɪər ˈæŋ.kərz/", "meaning": "neo nghề nghiệp (Schein)", "example": "Career anchors identify what individuals value most in their work and career."},
            {"word": "vocational identity", "ipa": "/vəʊˈkeɪ.ʃən.əl aɪˈden.tɪ.ti/", "meaning": "bản sắc nghề nghiệp", "example": "A strong vocational identity helps people make purposeful career choices."},
            {"word": "protean career", "ipa": "/ˈprəʊ.ti.ən kəˈrɪər/", "meaning": "sự nghiệp linh hoạt (tự định hướng)", "example": "A protean career is driven by personal values rather than organizational structures."},
            {"word": "boundaryless career", "ipa": "/ˈbaʊnd.ri.ləs kəˈrɪər/", "meaning": "sự nghiệp không giới hạn (qua nhiều tổ chức)", "example": "A boundaryless career involves moving across organizations and industries."},
            {"word": "organizational socialization", "ipa": "/ˌɔː.ɡən.aɪˈzeɪ.ʃən.əl ˌsəʊ.ʃəl.aɪˈzeɪ.ʃən/", "meaning": "xã hội hóa vào tổ chức", "example": "Effective organizational socialization helps new employees adapt to company culture."},
        ],
    },
    "job": {
        "A1": [
            {"word": "work", "ipa": "/wɜːk/", "meaning": "làm việc; công việc", "example": "I work from nine to five every day."},
            {"word": "job", "ipa": "/ʤɑb/", "meaning": "việc làm", "example": "She got a new job at a hospital."},
            {"word": "boss", "ipa": "/bɒs/", "meaning": "sếp, ông chủ", "example": "My boss is very kind and helpful."},
            {"word": "office", "ipa": "/ˈɒf.ɪs/", "meaning": "văn phòng", "example": "He goes to the office every morning."},
            {"word": "team", "ipa": "/tiːm/", "meaning": "đội, nhóm", "example": "Our team has five members."},
            {"word": "meeting", "ipa": "/ˈmiː.tɪŋ/", "meaning": "cuộc họp", "example": "We have a meeting at ten o'clock."},
            {"word": "money", "ipa": "/ˈmʌn.i/", "meaning": "tiền", "example": "She earns good money from her job."},
            {"word": "break", "ipa": "/breɪk/", "meaning": "giờ nghỉ", "example": "Let's take a break and have some coffee."},
            {"word": "labor", "ipa": "/ˈleɪbər/", "meaning": "làm việc; công việc", "example": "I work from nine to five every day."},
            {"word": "occupation", "ipa": "/ˌɑkjəˈpeɪʃən/", "meaning": "việc làm", "example": "She got a new job at a hospital."},
            {"word": "manager", "ipa": "/ˈmænɪʤər/", "meaning": "sếp, ông chủ", "example": "My boss is very kind and helpful."},
            {"word": "workplace", "ipa": "/ˈwərkˌpleɪs/", "meaning": "văn phòng", "example": "He goes to the office every morning."},
            {"word": "squad", "ipa": "/skwɑd/", "meaning": "đội, nhóm", "example": "Our team has five members."},
            {"word": "gathering", "ipa": "/ˈgæðərɪŋ/", "meaning": "cuộc họp", "example": "We have a meeting at ten o'clock."},
            {"word": "cash", "ipa": "/kæʃ/", "meaning": "tiền", "example": "She earns good money from her job."},
            {"word": "pause", "ipa": "/pɔz/", "meaning": "giờ nghỉ", "example": "Let's take a break and have some coffee."},
        ],
        "A2": [
            {"word": "salary", "ipa": "/ˈsæl.ər.i/", "meaning": "lương tháng", "example": "His salary is paid at the end of each month."},
            {"word": "colleague", "ipa": "/ˈkɒl.iːɡ/", "meaning": "đồng nghiệp", "example": "I have lunch with my colleagues every day."},
            {"word": "schedule", "ipa": "/ˈskɛʤʊl/", "meaning": "Lịch trình, thời khóa biểu", "example": "I need to check my work schedule."},
            {"word": "deadline", "ipa": "/ˈded.laɪn/", "meaning": "hạn chót", "example": "We must finish the report before the deadline."},
            {"word": "overtime", "ipa": "/ˈəʊ.və.taɪm/", "meaning": "Làm thêm giờ, thời gian làm thêm", "example": "He worked three hours of overtime yesterday."},
            {"word": "resume", "ipa": "/ˈrez.juː.meɪ/", "meaning": "sơ yếu lý lịch", "example": "Please send your resume to our HR department."},
            {"word": "apply", "ipa": "/əˈplaɪ/", "meaning": "nộp đơn, ứng tuyển", "example": "She decided to apply for the manager position."},
            {"word": "hire", "ipa": "/haɪər/", "meaning": "thuê, tuyển dụng", "example": "The company plans to hire ten new employees."},
            {"word": "wage", "ipa": "/weɪʤ/", "meaning": "lương tháng", "example": "His salary is paid at the end of each month."},
            {"word": "coworker", "ipa": "/ˈkoʊˈwərkər/", "meaning": "đồng nghiệp", "example": "I have lunch with my colleagues every day."},
            {"word": "timetable", "ipa": "/ˈtaɪmˌteɪbəl/", "meaning": "lịch trình", "example": "My schedule is very busy this week."},
            {"word": "time limit", "ipa": "/taɪm ˈlɪmət/", "meaning": "hạn chót", "example": "We must finish the report before the deadline."},
            {"word": "extra hours", "ipa": "/ˈɛkstrə aʊərz/", "meaning": "làm thêm giờ", "example": "He often works overtime to complete his projects."},
            {"word": "curriculum vitae", "ipa": "/kərˈɪkjələm ˈvaɪtə/", "meaning": "sơ yếu lý lịch", "example": "Please send your resume to our HR department."},
            {"word": "enroll", "ipa": "/ɪnˈroʊl/", "meaning": "nộp đơn, ứng tuyển", "example": "She decided to apply for the manager position."},
            {"word": "recruit", "ipa": "/rɪˈkrut/", "meaning": "thuê, tuyển dụng", "example": "The company plans to hire ten new employees."},
        ],
        "B1": [
            {"word": "career", "ipa": "/kəˈrɪər/", "meaning": "sự nghiệp", "example": "She has built a successful career in finance."},
            {"word": "promotion", "ipa": "/prəˈməʊ.ʃən/", "meaning": "thăng chức", "example": "He received a promotion after three years of hard work."},
            {"word": "freelancer", "ipa": "/ˈfriː.lɑːn.sər/", "meaning": "người làm tự do", "example": "As a freelancer, she can choose her own working hours."},
            {"word": "remote work", "ipa": "/rɪˌməʊt ˈwɜːk/", "meaning": "làm việc từ xa", "example": "Remote work has become more common since the pandemic."},
            {"word": "networking", "ipa": "/ˈnet.wɜː.kɪŋ/", "meaning": "xây dựng quan hệ nghề nghiệp", "example": "Networking events are great opportunities to meet industry professionals."},
            {"word": "skill set", "ipa": "/ˈskɪl set/", "meaning": "bộ kỹ năng", "example": "The job requires a diverse skill set including communication and analysis."},
            {"word": "reference", "ipa": "/ˈref.ər.əns/", "meaning": "người giới thiệu, tham chiếu", "example": "Please provide two professional references with your application."},
            {"word": "workplace", "ipa": "/ˈwɜːk.pleɪs/", "meaning": "nơi làm việc", "example": "A positive workplace environment improves employee satisfaction."},
            {"word": "profession", "ipa": "/prəˈfɛʃən/", "meaning": "sự nghiệp", "example": "She has built a successful career in finance."},
            {"word": "marketing", "ipa": "/ˈmɑrkətɪŋ/", "meaning": "thăng chức", "example": "He received a promotion after three years of hard work."},
            {"word": "independent contractor", "ipa": "/ˌɪndɪˈpɛndənt ˈkɑnˌtræktər/", "meaning": "người làm tự do", "example": "As a freelancer, she can choose her own working hours."},
            {"word": "telecommuting", "ipa": "/tɛləkəmˈjutɪŋ/", "meaning": "làm việc từ xa", "example": "Remote work has become more common since the pandemic."},
            {"word": "connecting", "ipa": "/kəˈnɛktɪŋ/", "meaning": "xây dựng quan hệ nghề nghiệp", "example": "Networking events are great opportunities to meet industry professionals."},
            {"word": "expertise", "ipa": "/ˌɛkspərˈtiz/", "meaning": "bộ kỹ năng", "example": "The job requires a diverse skill set including communication and analysis."},
            {"word": "recommendation", "ipa": "/ˌrɛkəmənˈdeɪʃən/", "meaning": "người giới thiệu, tham chiếu", "example": "Please provide two professional references with your application."},
            {"word": "workspace", "ipa": "/ˈwɜːk.pleɪs/", "meaning": "nơi làm việc", "example": "A positive workplace environment improves employee satisfaction."},
        ],
        "B2": [
            {"word": "compensation", "ipa": "/ˌkɒm.penˈseɪ.ʃən/", "meaning": "chế độ đãi ngộ, bồi thường", "example": "The compensation package includes health insurance and bonuses."},
            {"word": "corporate culture", "ipa": "/ˌkɔː.pər.ət ˈkʌl.tʃər/", "meaning": "văn hóa doanh nghiệp", "example": "A strong corporate culture attracts and retains talented employees."},
            {"word": "headhunter", "ipa": "/ˈhed.hʌn.tər/", "meaning": "người tuyển dụng cấp cao", "example": "A headhunter contacted her about a senior executive role."},
            {"word": "probation", "ipa": "/prəˈbeɪ.ʃən/", "meaning": "thời gian thử việc", "example": "New employees must complete a three-month probation period."},
            {"word": "redundancy", "ipa": "/rɪˈdʌn.dən.si/", "meaning": "sự sa thải do cắt giảm", "example": "The factory closure led to the redundancy of 200 workers."},
            {"word": "appraisal", "ipa": "/əˈpreɪ.zəl/", "meaning": "đánh giá năng lực", "example": "Annual appraisals help employees understand their strengths and areas for improvement."},
            {"word": "outsourcing", "ipa": "/ˈaʊt.sɔː.sɪŋ/", "meaning": "thuê ngoài", "example": "The company is outsourcing its IT support to reduce costs."},
            {"word": "turnover", "ipa": "/ˈtɜːn.əʊ.vər/", "meaning": "tỷ lệ nghỉ việc", "example": "High staff turnover can be a sign of poor management."},
            {"word": "remuneration", "ipa": "/ˌkɒm.penˈseɪ.ʃən/", "meaning": "chế độ đãi ngộ, bồi thường", "example": "The compensation package includes health insurance and bonuses."},
            {"word": "company culture", "ipa": "/ˌkɔː.pər.ət ˈkʌl.tʃər/", "meaning": "văn hóa doanh nghiệp", "example": "A strong corporate culture attracts and retains talented employees."},
            {"word": "recruiter", "ipa": "/rɪˈkrutər/", "meaning": "người tuyển dụng cấp cao", "example": "A headhunter contacted her about a senior executive role."},
            {"word": "trial period", "ipa": "/traɪəl ˈpɪriəd/", "meaning": "thời gian thử việc", "example": "New employees must complete a three-month probation period."},
            {"word": "layoff", "ipa": "/leɪɔf/", "meaning": "sự sa thải do cắt giảm", "example": "The factory closure led to the redundancy of 200 workers."},
            {"word": "evaluation", "ipa": "/ɪˌvæljuˈeɪʃən/", "meaning": "đánh giá năng lực", "example": "Annual appraisals help employees understand their strengths and areas for improvement."},
            {"word": "subcontracting", "ipa": "/ˌsəbkənˈtræktɪŋ/", "meaning": "thuê ngoài", "example": "The company is outsourcing its IT support to reduce costs."},
            {"word": "staff turnover", "ipa": "/ˈtɜːn.əʊ.vər/", "meaning": "tỷ lệ nghỉ việc", "example": "High staff turnover can be a sign of poor management."},
        ],
        "C1": [
            {"word": "meritocracy", "ipa": "/ˌmer.ɪˈtɒk.rə.si/", "meaning": "chế độ trọng dụng nhân tài", "example": "In a true meritocracy, promotions are based solely on ability and performance."},
            {"word": "glass ceiling", "ipa": "/ɡlɑːs ˈsiː.lɪŋ/", "meaning": "rào cản vô hình (trong thăng tiến)", "example": "Many women still face a glass ceiling when seeking top leadership roles."},
            {"word": "occupational hazard", "ipa": "/ˌɒk.jəˈpeɪ.ʃən.əl ˈhæz.əd/", "meaning": "rủi ro nghề nghiệp", "example": "Exposure to chemicals is an occupational hazard for factory workers."},
            {"word": "sabbatical", "ipa": "/səˈbæt.ɪ.kəl/", "meaning": "kỳ nghỉ phép dài hạn", "example": "She took a one-year sabbatical to travel and write a book."},
            {"word": "moonlighting", "ipa": "/ˈmuːn.laɪ.tɪŋ/", "meaning": "làm thêm việc ngoài giờ", "example": "Moonlighting as a consultant helped him pay off his student loans."},
            {"word": "golden parachute", "ipa": "/ˌɡəʊl.dən ˈpær.ə.ʃuːt/", "meaning": "khoản bồi thường hậu hĩnh khi bị sa thải", "example": "The CEO received a golden parachute worth millions after the merger."},
            {"word": "whistleblower", "ipa": "/ˈwɪs.əl.bləʊ.ər/", "meaning": "người tố giác sai phạm", "example": "The whistleblower revealed evidence of financial fraud within the company."},
            {"word": "non-compete clause", "ipa": "/ˌnɒn.kəmˈpiːt klɔːz/", "meaning": "điều khoản không cạnh tranh", "example": "His non-compete clause prevents him from working for rival firms for two years."},
            {"word": "skill-based system", "ipa": "/ˌmer.ɪˈtɒk.rə.si/", "meaning": "chế độ trọng dụng nhân tài", "example": "In a true meritocracy, promotions are based solely on ability and performance."},
            {"word": "invisible barrier", "ipa": "/ˌɪnˈvɪzəbəl ˈbɛriər/", "meaning": "rào cản vô hình (trong thăng tiến)", "example": "Many women still face a glass ceiling when seeking top leadership roles."},
            {"word": "workplace risk", "ipa": "/ˈwərkˌpleɪs rɪsk/", "meaning": "rủi ro nghề nghiệp", "example": "Exposure to chemicals is an occupational hazard for factory workers."},
            {"word": "leave of absence", "ipa": "/liv əv ˈæbsəns/", "meaning": "kỳ nghỉ phép dài hạn", "example": "She took a one-year sabbatical to travel and write a book."},
            {"word": "second job", "ipa": "/ˈsɛkənd ʤɑb/", "meaning": "làm thêm việc ngoài giờ", "example": "Moonlighting as a consultant helped him pay off his student loans."},
            {"word": "severance package", "ipa": "/ˈsɛˌvərəns ˈpækɪʤ/", "meaning": "khoản bồi thường hậu hĩnh khi bị sa thải", "example": "The CEO received a golden parachute worth millions after the merger."},
            {"word": "informant", "ipa": "/ˌɪnˈfɔrmənt/", "meaning": "người tố giác sai phạm", "example": "The whistleblower revealed evidence of financial fraud within the company."},
            {"word": "restriction clause", "ipa": "/riˈstrɪkʃən klɔz/", "meaning": "điều khoản không cạnh tranh", "example": "His non-compete clause prevents him from working for rival firms for two years."},
        ],
    },
    "marketing": {
        "A1": [
            {"word": "shop", "ipa": "/ʃɒp/", "meaning": "cửa hàng; mua sắm", "example": "I like to shop at the mall on weekends."},
            {"word": "buy", "ipa": "/baɪ/", "meaning": "mua", "example": "I want to buy a new pair of shoes."},
            {"word": "sell", "ipa": "/sel/", "meaning": "bán", "example": "They sell fresh fruit at the market."},
            {"word": "price", "ipa": "/praɪs/", "meaning": "giá cả", "example": "The price of this phone is very reasonable."},
            {"word": "cheap", "ipa": "/tʃiːp/", "meaning": "rẻ", "example": "This bag is cheap but looks nice."},
            {"word": "brand", "ipa": "/brænd/", "meaning": "thương hiệu", "example": "Nike is a famous brand around the world."},
            {"word": "advert", "ipa": "/ˈæd.vɜːt/", "meaning": "quảng cáo", "example": "I saw an advert for the new restaurant on TV."},
            {"word": "poster", "ipa": "/ˈpəʊ.stər/", "meaning": "áp phích", "example": "There is a poster on the wall about the sale event."},
            {"word": "store", "ipa": "/stɔr/", "meaning": "cửa hàng; mua sắm", "example": "I like to shop at the mall on weekends."},
            {"word": "purchase", "ipa": "/ˈpərʧəs/", "meaning": "mua", "example": "I want to buy a new pair of shoes."},
            {"word": "vend", "ipa": "/sel/", "meaning": "bán", "example": "They sell fresh fruit at the market."},
            {"word": "rate", "ipa": "/praɪs/", "meaning": "giá cả", "example": "The price of this phone is very reasonable."},
            {"word": "inexpensive", "ipa": "/ˌɪnɪkˈspɛnsɪv/", "meaning": "rẻ", "example": "This bag is cheap but looks nice."},
            {"word": "trademark", "ipa": "/ˈtreɪdˌmɑrk/", "meaning": "thương hiệu", "example": "Nike is a famous brand around the world."},
            {"word": "advertisement", "ipa": "/ˌædvərˈtaɪzmənt/", "meaning": "quảng cáo", "example": "I saw an advert for the new restaurant on TV."},
            {"word": "banner", "ipa": "/ˈbænər/", "meaning": "áp phích", "example": "There is a poster on the wall about the sale event."},
        ],
        "A2": [
            {"word": "customer", "ipa": "/ˈkʌs.tə.mər/", "meaning": "khách hàng", "example": "The shop has many loyal customers."},
            {"word": "product", "ipa": "/ˈprɒd.ʌkt/", "meaning": "sản phẩm", "example": "This product is made from natural materials."},
            {"word": "discount", "ipa": "/ˈdɪs.kaʊnt/", "meaning": "giảm giá", "example": "Students can get a 10% discount on all books."},
            {"word": "promotion", "ipa": "/prəˈməʊ.ʃən/", "meaning": "khuyến mãi; quảng bá", "example": "The store is running a special promotion this month."},
            {"word": "market", "ipa": "/ˈmɑː.kɪt/", "meaning": "thị trường", "example": "The company wants to enter the Asian market."},
            {"word": "survey", "ipa": "/ˈsɜː.veɪ/", "meaning": "khảo sát", "example": "We did a survey to find out what customers want."},
            {"word": "logo", "ipa": "/ˈləʊ.ɡəʊ/", "meaning": "biểu trưng, logo", "example": "The company changed its logo to look more modern."},
            {"word": "offer", "ipa": "/ˈɒf.ər/", "meaning": "ưu đãi; đề nghị", "example": "This is a limited-time offer — buy one, get one free."},
            {"word": "client", "ipa": "/klaɪənt/", "meaning": "khách hàng", "example": "The shop has many loyal customers."},
            {"word": "item", "ipa": "/ˈaɪtəm/", "meaning": "sản phẩm", "example": "This product is made from natural materials."},
            {"word": "reduction", "ipa": "/rɪˈdəkʃən/", "meaning": "giảm giá", "example": "Students can get a 10% discount on all books."},
            {"word": "marketing", "ipa": "/ˈmɑrkətɪŋ/", "meaning": "khuyến mãi; quảng bá", "example": "The store is running a special promotion this month."},
            {"word": "marketplace", "ipa": "/ˈmɑː.kɪt/", "meaning": "thị trường", "example": "The company wants to enter the Asian market."},
            {"word": "poll", "ipa": "/poʊl/", "meaning": "khảo sát", "example": "We did a survey to find out what customers want."},
            {"word": "emblem", "ipa": "/ˈɛmbləm/", "meaning": "biểu trưng, logo", "example": "The company changed its logo to look more modern."},
            {"word": "proposal", "ipa": "/prəˈpoʊzəl/", "meaning": "ưu đãi; đề nghị", "example": "This is a limited-time offer — buy one, get one free."},
        ],
        "B1": [
            {"word": "target audience", "ipa": "/ˌtɑː.ɡɪt ˈɔː.di.əns/", "meaning": "đối tượng mục tiêu", "example": "The target audience for this product is young professionals."},
            {"word": "campaign", "ipa": "/kæmˈpeɪn/", "meaning": "chiến dịch", "example": "The marketing campaign increased sales by 30 percent."},
            {"word": "branding", "ipa": "/ˈbræn.dɪŋ/", "meaning": "xây dựng thương hiệu", "example": "Good branding helps customers remember your company."},
            {"word": "analytics", "ipa": "/ˌæn.əˈlɪt.ɪks/", "meaning": "phân tích dữ liệu", "example": "We use analytics to track how visitors use our website."},
            {"word": "conversion", "ipa": "/kənˈvɜː.ʃən/", "meaning": "chuyển đổi (khách thành người mua)", "example": "The conversion rate improved after we redesigned the landing page."},
            {"word": "engagement", "ipa": "/ɪnˈɡeɪdʒ.mənt/", "meaning": "mức độ tương tác", "example": "Social media engagement is higher when we post videos."},
            {"word": "influencer", "ipa": "/ˈɪn.flu.ən.sər/", "meaning": "người có ảnh hưởng", "example": "The brand partnered with an influencer to promote its new collection."},
            {"word": "content marketing", "ipa": "/ˌkɒn.tent ˈmɑː.kɪ.tɪŋ/", "meaning": "tiếp thị nội dung", "example": "Content marketing focuses on creating valuable articles and videos for customers."},
            {"word": "target demographic", "ipa": "/ˈtərgət ˌdɛməˈgræfɪk/", "meaning": "đối tượng mục tiêu", "example": "The target audience for this product is young professionals."},
            {"word": "drive", "ipa": "/draɪv/", "meaning": "chiến dịch", "example": "The marketing campaign increased sales by 30 percent."},
            {"word": "identity", "ipa": "/aɪˈdɛntəˌti/", "meaning": "xây dựng thương hiệu", "example": "Good branding helps customers remember your company."},
            {"word": "data analysis", "ipa": "/ˌæn.əˈlɪt.ɪks/", "meaning": "phân tích dữ liệu", "example": "We use analytics to track how visitors use our website."},
            {"word": "transition", "ipa": "/trænˈzɪʃən/", "meaning": "chuyển đổi (khách thành người mua)", "example": "The conversion rate improved after we redesigned the landing page."},
            {"word": "interaction", "ipa": "/ˌɪnərˈækʃən/", "meaning": "mức độ tương tác", "example": "Social media engagement is higher when we post videos."},
            {"word": "trendsetter", "ipa": "/ˈtrɛndˌsɛtər/", "meaning": "Người dẫn đầu xu hướng", "example": "She is a trendsetter in the fashion industry."},
            {"word": "digital content", "ipa": "/ˈdɪʤɪtəl ˈkɑntɛnt/", "meaning": "tiếp thị nội dung", "example": "Content marketing focuses on creating valuable articles and videos for customers."},
        ],
        "B2": [
            {"word": "segmentation", "ipa": "/ˌseɡ.menˈteɪ.ʃən/", "meaning": "phân khúc thị trường", "example": "Market segmentation allows companies to tailor products to specific groups."},
            {"word": "market penetration", "ipa": "/ˌmɑː.kɪt ˌpen.ɪˈtreɪ.ʃən/", "meaning": "thâm nhập thị trường", "example": "The company achieved rapid market penetration through aggressive pricing."},
            {"word": "brand equity", "ipa": "/brænd ˈek.wɪ.ti/", "meaning": "giá trị thương hiệu", "example": "Apple has built strong brand equity over the past decades."},
            {"word": "omnichannel", "ipa": "/ˌɒm.niˈtʃæn.əl/", "meaning": "đa kênh tích hợp", "example": "An omnichannel strategy ensures a seamless customer experience across all platforms."},
            {"word": "lead generation", "ipa": "/liːd ˌdʒen.əˈreɪ.ʃən/", "meaning": "tạo khách hàng tiềm năng", "example": "Lead generation is the first step in building a strong sales pipeline."},
            {"word": "A/B testing", "ipa": "/ˌeɪ biː ˈtes.tɪŋ/", "meaning": "thử nghiệm A/B", "example": "A/B testing showed that the red button got more clicks than the blue one."},
            {"word": "ROI", "ipa": "/rɔɪ/", "meaning": "lợi tức đầu tư", "example": "We need to calculate the ROI before launching the new campaign."},
            {"word": "viral marketing", "ipa": "/ˌvaɪə.rəl ˈmɑː.kɪ.tɪŋ/", "meaning": "tiếp thị lan truyền", "example": "The video went viral, making it a perfect example of viral marketing."},
            {"word": "division", "ipa": "/dɪˈvɪʒən/", "meaning": "phân khúc thị trường", "example": "Market segmentation allows companies to tailor products to specific groups."},
            {"word": "market share", "ipa": "/ˈmɑrkɪt ʃɛr/", "meaning": "thâm nhập thị trường", "example": "The company achieved rapid market penetration through aggressive pricing."},
            {"word": "brand value", "ipa": "/brænd ˈek.wɪ.ti/", "meaning": "giá trị thương hiệu", "example": "Apple has built strong brand equity over the past decades."},
            {"word": "multichannel", "ipa": "/ˌɒm.niˈtʃæn.əl/", "meaning": "đa kênh tích hợp", "example": "An omnichannel strategy ensures a seamless customer experience across all platforms."},
            {"word": "lead capture", "ipa": "/lɛd ˈkæpʧər/", "meaning": "tạo khách hàng tiềm năng", "example": "Lead generation is the first step in building a strong sales pipeline."},
            {"word": "split testing", "ipa": "/ˌeɪ biː ˈtes.tɪŋ/", "meaning": "thử nghiệm A/B", "example": "A/B testing showed that the red button got more clicks than the blue one."},
            {"word": "return on investment", "ipa": "/rɪˈtərn ɔn ˌɪnˈvɛstmənt/", "meaning": "lợi tức đầu tư", "example": "We need to calculate the ROI before launching the new campaign."},
            {"word": "buzz marketing", "ipa": "/ˌvaɪə.rəl ˈmɑː.kɪ.tɪŋ/", "meaning": "tiếp thị lan truyền", "example": "The video went viral, making it a perfect example of viral marketing."},
        ],
        "C1": [
            {"word": "brand dilution", "ipa": "/brænd daɪˈluː.ʃən/", "meaning": "loãng thương hiệu", "example": "Launching too many sub-brands can lead to brand dilution."},
            {"word": "psychographics", "ipa": "/ˌsaɪ.kəʊˈɡræf.ɪks/", "meaning": "phân tích tâm lý khách hàng", "example": "Psychographics help marketers understand consumer attitudes and lifestyles."},
            {"word": "programmatic advertising", "ipa": "/ˌprəʊ.ɡræˈmæt.ɪk ˈæd.və.taɪ.zɪŋ/", "meaning": "quảng cáo tự động lập trình", "example": "Programmatic advertising uses AI to buy and place ads in real time."},
            {"word": "attribution modeling", "ipa": "/ˌæt.rɪˈbjuː.ʃən ˈmɒd.əl.ɪŋ/", "meaning": "mô hình phân bổ hiệu quả", "example": "Attribution modeling helps determine which marketing channels drive the most conversions."},
            {"word": "guerrilla marketing", "ipa": "/ɡəˌrɪl.ə ˈmɑː.kɪ.tɪŋ/", "meaning": "tiếp thị du kích", "example": "Guerrilla marketing uses unconventional tactics to surprise and engage consumers."},
            {"word": "neuromarketing", "ipa": "/ˌnjʊə.rəʊˈmɑː.kɪ.tɪŋ/", "meaning": "tiếp thị thần kinh học", "example": "Neuromarketing studies brain responses to understand consumer decision-making."},
            {"word": "customer lifetime value", "ipa": "/ˌkʌs.tə.mər ˈlaɪf.taɪm ˈvæl.juː/", "meaning": "giá trị trọn đời của khách hàng", "example": "Increasing customer lifetime value is more cost-effective than acquiring new customers."},
            {"word": "market saturation", "ipa": "/ˌmɑː.kɪt ˌsætʃ.əˈreɪ.ʃən/", "meaning": "bão hòa thị trường", "example": "Market saturation makes it difficult for new entrants to gain significant market share."},
            {"word": "brand weakening", "ipa": "/brænd ˈwikənɪŋ/", "meaning": "loãng thương hiệu", "example": "Launching too many sub-brands can lead to brand dilution."},
            {"word": "psychological profiling", "ipa": "/ˌsaɪkəˈlɑʤɪkəl ˈproʊˌfaɪlɪŋ/", "meaning": "phân tích tâm lý khách hàng", "example": "Psychographics help marketers understand consumer attitudes and lifestyles."},
            {"word": "automated ads", "ipa": "/ˈɔtəˌmeɪtɪd ædz/", "meaning": "quảng cáo tự động lập trình", "example": "Programmatic advertising uses AI to buy and place ads in real time."},
            {"word": "attribution analysis", "ipa": "/ˌæt.rɪˈbjuː.ʃən ˈmɒd.əl.ɪŋ/", "meaning": "mô hình phân bổ hiệu quả", "example": "Attribution modeling helps determine which marketing channels drive the most conversions."},
            {"word": "unconventional marketing", "ipa": "/ˌənkənˈvɛnʃənəl ˈmɑrkətɪŋ/", "meaning": "tiếp thị du kích", "example": "Guerrilla marketing uses unconventional tactics to surprise and engage consumers."},
            {"word": "consumer neuroscience", "ipa": "/kənˈsumər nˈjʊroʊˌsaɪəns/", "meaning": "tiếp thị thần kinh học", "example": "Neuromarketing studies brain responses to understand consumer decision-making."},
            {"word": "CLV", "ipa": "/ˌsiːɛlˈviː/", "meaning": "Giá trị trọn đời khách hàng", "example": "Increasing CLV is key to sustainable business growth."},
            {"word": "market capacity", "ipa": "/ˈmɑrkɪt kəˈpæsɪti/", "meaning": "bão hòa thị trường", "example": "Market saturation makes it difficult for new entrants to gain significant market share."},
        ],
    },
    "music": {
        "A1": [
            {"word": "song", "ipa": "/sɒŋ/", "meaning": "bài hát", "example": "She sang a beautiful song at the concert."},
            {"word": "sing", "ipa": "/sɪŋ/", "meaning": "hát", "example": "He loves to sing in the shower every morning."},
            {"word": "drum", "ipa": "/drʌm/", "meaning": "trống", "example": "He plays the drum in the school band."},
            {"word": "piano", "ipa": "/piˈæn.əʊ/", "meaning": "đàn piano", "example": "She has been learning the piano since she was five."},
            {"word": "guitar", "ipa": "/ɡɪˈtɑːr/", "meaning": "đàn guitar", "example": "He plays the guitar at parties and family gatherings."},
            {"word": "band", "ipa": "/bænd/", "meaning": "ban nhạc", "example": "The band performed three new songs at the festival."},
            {"word": "dance", "ipa": "/dɑːns/", "meaning": "nhảy múa; điệu nhảy", "example": "She loves to dance to her favorite music."},
            {"word": "loud", "ipa": "/laʊd/", "meaning": "to, ồn ào", "example": "The music was so loud that we couldn't hear each other."},
            {"word": "quiet", "ipa": "/ˈkwaɪ.ət/", "meaning": "nhẹ nhàng, yên tĩnh", "example": "The quiet music helped me relax after a stressful day."},
            {"word": "listen", "ipa": "/ˈlɪs.ən/", "meaning": "nghe", "example": "I listen to music while I study."},
            {"word": "radio", "ipa": "/ˈreɪ.di.əʊ/", "meaning": "đài phát thanh", "example": "They listen to music on the radio every morning."},
            {"word": "singer", "ipa": "/ˈsɪŋ.ər/", "meaning": "ca sĩ", "example": "She is my favorite singer of all time."},
            {"word": "music", "ipa": "/ˈmjuː.zɪk/", "meaning": "âm nhạc", "example": "Music makes me feel happy and relaxed."},
            {"word": "note", "ipa": "/nəʊt/", "meaning": "nốt nhạc", "example": "She practiced playing each note carefully on the piano."},
            {"word": "beat", "ipa": "/biːt/", "meaning": "nhịp điệu", "example": "The beat of the music made everyone want to dance."},
            {"word": "concert", "ipa": "/ˈkɒn.sət/", "meaning": "buổi hòa nhạc", "example": "We went to a rock concert last Saturday night."},
            {"word": "violin", "ipa": "/ˌvaɪ.əˈlɪn/", "meaning": "đàn vĩ cầm", "example": "She plays the violin in the school orchestra."},
            {"word": "flute", "ipa": "/fluːt/", "meaning": "sáo (nhạc cụ)", "example": "The flute has a light and beautiful sound."},
            {"word": "sound", "ipa": "/saʊnd/", "meaning": "âm thanh", "example": "I love the sound of rain and soft music together."},
            {"word": "voice", "ipa": "/vɔɪs/", "meaning": "giọng hát; giọng nói", "example": "She has an incredible voice that moves audiences to tears."},
            {"word": "album", "ipa": "/ˈæl.bəm/", "meaning": "album nhạc", "example": "The band released their new album last month."},
            {"word": "lyrics", "ipa": "/ˈlɪr.ɪks/", "meaning": "lời bài hát", "example": "She memorized the lyrics to all her favorite songs."},
            {"word": "microphone", "ipa": "/ˈmaɪ.krə.fəʊn/", "meaning": "micro", "example": "The singer held the microphone and walked across the stage."},
            {"word": "stage", "ipa": "/steɪdʒ/", "meaning": "sân khấu", "example": "Thousands of fans cheered as she stepped onto the stage."},
            {"word": "pop", "ipa": "/pɒp/", "meaning": "nhạc pop", "example": "Pop music is very popular among teenagers around the world."},
            {"word": "rock", "ipa": "/rɒk/", "meaning": "nhạc rock", "example": "He loves listening to classic rock from the 1970s."},
            {"word": "jazz", "ipa": "/dʒæz/", "meaning": "nhạc jazz", "example": "Jazz music originated in New Orleans in the early 20th century."},
            {"word": "trumpet", "ipa": "/ˈtrʌm.pɪt/", "meaning": "kèn trumpet", "example": "He plays the trumpet in a jazz band downtown."},
            {"word": "keyboard", "ipa": "/ˈkiː.bɔːd/", "meaning": "đàn phím điện tử", "example": "She plays the keyboard in the church choir."},
            {"word": "song", "ipa": "/sɒŋ/", "meaning": "bài hát", "example": "That song always reminds me of my childhood."},
            {"word": "melody", "ipa": "/ˈmel.ə.di/", "meaning": "giai điệu", "example": "The melody of the song stayed in my head all day."},
            {"word": "rhythm", "ipa": "/ˈrɪð.əm/", "meaning": "nhịp điệu", "example": "She has a great sense of rhythm when she dances."},
            {"word": "tune", "ipa": "/tjuːn/", "meaning": "giai điệu; bài nhạc", "example": "He hummed a cheerful tune as he walked home."},
            {"word": "play", "ipa": "/pleɪ/", "meaning": "chơi nhạc cụ", "example": "Can you play any musical instrument?"},
            {"word": "instrument", "ipa": "/ˈɪn.strə.mənt/", "meaning": "nhạc cụ", "example": "Learning a musical instrument takes patience and practice."},
            {"word": "choir", "ipa": "/ˈkwaɪər/", "meaning": "dàn hợp xướng", "example": "She joined the school choir and loves singing with others."},
            {"word": "bass", "ipa": "/beɪs/", "meaning": "âm trầm; đàn bass", "example": "The bass guitar gives the music a deep, powerful sound."},
            {"word": "headphones", "ipa": "/ˈhed.fəʊnz/", "meaning": "tai nghe", "example": "I wear headphones when I listen to music on the train."},
            {"word": "playlist", "ipa": "/ˈpleɪ.lɪst/", "meaning": "danh sách bài hát", "example": "She created a playlist of her favorite workout songs."},
            {"word": "volume", "ipa": "/ˈvɒl.juːm/", "meaning": "âm lượng", "example": "Please turn down the volume — I'm trying to sleep."},
            {"word": "classical", "ipa": "/ˈklæs.ɪ.kəl/", "meaning": "nhạc cổ điển", "example": "He prefers classical music to modern pop songs."},
            {"word": "tempo", "ipa": "/ˈtem.pəʊ/", "meaning": "tốc độ nhịp của bài nhạc", "example": "The conductor increased the tempo as the piece reached its climax."},
            {"word": "rap", "ipa": "/ræp/", "meaning": "nhạc rap", "example": "Rap music often tells stories about life in urban communities."},
            {"word": "hit", "ipa": "/hɪt/", "meaning": "bài hát ăn khách", "example": "That song became a massive hit worldwide."},
            {"word": "fan", "ipa": "/fæn/", "meaning": "người hâm mộ", "example": "She is a huge fan of that Korean pop group."},
            {"word": "live music", "ipa": "/laɪv ˈmjuː.zɪk/", "meaning": "nhạc sống", "example": "Nothing beats the energy of live music at a concert."},
            {"word": "acoustic", "ipa": "/əˈkuː.stɪk/", "meaning": "âm thanh không khuếch đại; giai điệu mộc", "example": "She performed an acoustic version of her famous song."},
            {"word": "verse", "ipa": "/vɜːs/", "meaning": "khổ thơ/đoạn ca", "example": "The first verse of the song describes a sad love story."},
            {"word": "chorus", "ipa": "/ˈkɔː.rəs/", "meaning": "điệp khúc", "example": "Everyone sang along when the chorus started."},
            {"word": "bridge", "ipa": "/brɪdʒ/", "meaning": "đoạn nối (trong bài hát)", "example": "The bridge of the song introduced a surprising key change."},
        ],
        "A2": [
            {"word": "orchestra", "ipa": "/ˈɔː.kɪ.strə/", "meaning": "dàn nhạc giao hưởng", "example": "She plays second violin in the city orchestra."},
            {"word": "rehearsal", "ipa": "/rɪˈhɜː.səl/", "meaning": "buổi tập dượt", "example": "The band had a rehearsal before the big concert."},
            {"word": "genre", "ipa": "/ˈʒɒn.rə/", "meaning": "thể loại nhạc", "example": "What genre of music do you enjoy listening to?"},
            {"word": "compose", "ipa": "/kəmˈpəʊz/", "meaning": "sáng tác nhạc", "example": "She composes her own songs and performs them live."},
            {"word": "musician", "ipa": "/mjuːˈzɪʃ.ən/", "meaning": "nhạc sĩ", "example": "He is a talented musician who plays five instruments."},
            {"word": "saxophone", "ipa": "/ˈsæk.sə.fəʊn/", "meaning": "kèn saxophone", "example": "The saxophonist played a beautiful solo during the jazz concert."},
            {"word": "record", "ipa": "/rɪˈkɔːd/", "meaning": "thu âm; đĩa nhạc", "example": "They recorded their first album in a small studio."},
            {"word": "studio", "ipa": "/ˈstjuː.di.əʊ/", "meaning": "phòng thu âm", "example": "The band spent three months in the studio recording their new album."},
            {"word": "performance", "ipa": "/pəˈfɔː.məns/", "meaning": "buổi biểu diễn", "example": "Her performance at the talent show was absolutely outstanding."},
            {"word": "applause", "ipa": "/əˈplɔːz/", "meaning": "tiếng vỗ tay", "example": "The audience gave a standing applause after the final song."},
            {"word": "conductor", "ipa": "/kənˈdʌk.tər/", "meaning": "nhạc trưởng", "example": "The conductor guided the orchestra through the complex symphony."},
            {"word": "harmony", "ipa": "/ˈhɑː.mə.ni/", "meaning": "sự hòa âm", "example": "Their voices blended in perfect harmony."},
            {"word": "pitch", "ipa": "/pɪtʃ/", "meaning": "cao độ giọng/nốt nhạc", "example": "She has perfect pitch and can identify any musical note."},
            {"word": "key", "ipa": "/kiː/", "meaning": "điệu nhạc (giọng)", "example": "The song is written in the key of C major."},
            {"word": "practice", "ipa": "/ˈpræk.tɪs/", "meaning": "luyện tập nhạc", "example": "He practices the piano for two hours every day."},
            {"word": "talent", "ipa": "/ˈtæl.ənt/", "meaning": "tài năng âm nhạc", "example": "She has incredible musical talent from a very young age."},
            {"word": "audition", "ipa": "/ɔːˈdɪʃ.ən/", "meaning": "thử giọng", "example": "She was nervous before her audition for the music school."},
            {"word": "solo", "ipa": "/ˈsəʊ.ləʊ/", "meaning": "độc tấu; biểu diễn một mình", "example": "The guitarist played an impressive solo in the middle of the song."},
            {"word": "note reading", "ipa": "/nəʊt ˈriː.dɪŋ/", "meaning": "đọc nốt nhạc", "example": "Note reading is an essential skill for any musician."},
            {"word": "music theory", "ipa": "/ˈmjuː.zɪk ˈθɪər.i/", "meaning": "lý thuyết âm nhạc", "example": "Music theory helps musicians understand how songs are structured."},
            {"word": "bass guitar", "ipa": "/beɪs ɡɪˈtɑːr/", "meaning": "đàn bass guitar", "example": "The bass guitar provides the low-frequency foundation of the music."},
            {"word": "electric guitar", "ipa": "/ɪˌlek.trɪk ɡɪˈtɑːr/", "meaning": "đàn guitar điện", "example": "He loves playing the electric guitar in his rock band."},
            {"word": "streaming", "ipa": "/ˈstriː.mɪŋ/", "meaning": "nghe nhạc trực tuyến", "example": "Millions of people access music through streaming platforms."},
            {"word": "download", "ipa": "/ˌdaʊnˈləʊd/", "meaning": "tải nhạc xuống", "example": "I downloaded her new album and listened to it all day."},
            {"word": "lyrics writing", "ipa": "/ˈlɪr.ɪks ˈraɪ.tɪŋ/", "meaning": "viết lời bài hát", "example": "Lyrics writing requires both poetic and emotional skills."},
            {"word": "background music", "ipa": "/ˈbæk.ɡraʊnd ˈmjuː.zɪk/", "meaning": "nhạc nền", "example": "Soft background music in restaurants makes dining more enjoyable."},
            {"word": "duet", "ipa": "/djuˈet/", "meaning": "song tấu; song ca", "example": "The two singers performed a beautiful duet on stage."},
            {"word": "encore", "ipa": "/ˈɒŋ.kɔːr/", "meaning": "màn hát lại theo yêu cầu khán giả", "example": "The crowd cheered for an encore after the final song."},
            {"word": "music festival", "ipa": "/ˈmjuː.zɪk ˈfes.tɪ.vəl/", "meaning": "lễ hội âm nhạc", "example": "We camped for three days at the outdoor music festival."},
            {"word": "songwriter", "ipa": "/ˈsɒŋˌraɪ.tər/", "meaning": "nhạc sĩ sáng tác", "example": "She is both a talented singer and a skilled songwriter."},
            {"word": "producer", "ipa": "/prəˈdjuː.sər/", "meaning": "nhà sản xuất âm nhạc", "example": "The producer worked with the band to create their signature sound."},
            {"word": "DJ", "ipa": "/ˌdiːˈdʒeɪ/", "meaning": "DJ (người phát nhạc)", "example": "The DJ kept the crowd dancing all night at the party."},
            {"word": "ballad", "ipa": "/ˈbæl.əd/", "meaning": "bài ballad; bài hát trữ tình", "example": "She sang a slow ballad that moved many people to tears."},
            {"word": "upbeat", "ipa": "/ˈʌp.biːt/", "meaning": "sôi động, vui tươi", "example": "The upbeat melody made everyone feel energized and happy."},
            {"word": "soundtrack", "ipa": "/ˈsaʊnd.træk/", "meaning": "nhạc phim", "example": "The soundtrack of that film is incredibly moving and beautiful."},
            {"word": "chart", "ipa": "/tʃɑːt/", "meaning": "bảng xếp hạng nhạc", "example": "Her new single reached the top of the music charts."},
            {"word": "debut album", "ipa": "/ˈdeɪ.bjuː ˈæl.bəm/", "meaning": "album đầu tay", "example": "His debut album sold over a million copies worldwide."},
            {"word": "single", "ipa": "/ˈsɪŋ.ɡəl/", "meaning": "đĩa đơn", "example": "They released a new single to promote the upcoming album."},
            {"word": "cover version", "ipa": "/ˈkʌv.ər ˈvɜː.ʃən/", "meaning": "bản cover", "example": "Her cover version of the classic song became a hit."},
            {"word": "music video", "ipa": "/ˈmjuː.zɪk ˈvɪd.i.əʊ/", "meaning": "video âm nhạc", "example": "The music video for the song has over 100 million views."},
            {"word": "bass line", "ipa": "/beɪs laɪn/", "meaning": "đường bass", "example": "The bass line in that song is incredibly catchy."},
            {"word": "sample", "ipa": "/ˈsɑːm.pəl/", "meaning": "đoạn nhạc mượn từ bài khác", "example": "The new track uses a sample from an old soul song."},
            {"word": "remix", "ipa": "/ˈriː.mɪks/", "meaning": "phiên bản phối lại", "example": "A popular DJ created a remix of the original song."},
            {"word": "mixtape", "ipa": "/ˈmɪks.teɪp/", "meaning": "băng nhạc tự làm; mixtape", "example": "He recorded a mixtape to share with his friends."},
            {"word": "vinyl record", "ipa": "/ˈvaɪ.nəl rɪˈkɔːd/", "meaning": "đĩa than", "example": "Vinyl records have made a comeback among music enthusiasts."},
            {"word": "pitch correction", "ipa": "/pɪtʃ kəˈrek.ʃən/", "meaning": "hiệu chỉnh cao độ giọng", "example": "Pitch correction software is commonly used in modern music production."},
            {"word": "open mic", "ipa": "/ˌəʊ.pən ˈmaɪk/", "meaning": "sự kiện biểu diễn tự do", "example": "He performed at an open mic night at the local café."},
            {"word": "setlist", "ipa": "/ˈset.lɪst/", "meaning": "danh sách bài hát trong buổi diễn", "example": "Fans were excited to see the setlist before the concert."},
            {"word": "soundcheck", "ipa": "/ˈsaʊnd.tʃek/", "meaning": "kiểm tra âm thanh trước buổi diễn", "example": "The band did a soundcheck an hour before the doors opened."},
            {"word": "groupie", "ipa": "/ˈɡruː.pi/", "meaning": "người hâm mộ cuồng nhiệt theo ban nhạc", "example": "She became a groupie and followed the band on their entire tour."},
        ],
        "B1": [
            {"word": "symphony", "ipa": "/ˈsɪm.fə.ni/", "meaning": "bản giao hưởng", "example": "Beethoven's Fifth Symphony is one of the most famous compositions in history."},
            {"word": "composition", "ipa": "/ˌkɒm.pəˈzɪʃ.ən/", "meaning": "tác phẩm âm nhạc", "example": "The young composer presented his first major composition at the music hall."},
            {"word": "harmonize", "ipa": "/ˈhɑː.mə.naɪz/", "meaning": "hòa âm", "example": "The singers harmonized beautifully throughout the entire performance."},
            {"word": "improvise", "ipa": "/ˈɪm.prə.vaɪz/", "meaning": "ứng tấu, ngẫu hứng", "example": "Jazz musicians often improvise solos based on the chord progression."},
            {"word": "chord progression", "ipa": "/kɔːd prəˈɡreʃ.ən/", "meaning": "tiến trình hợp âm", "example": "Many popular songs share the same four-chord progression."},
            {"word": "dynamics", "ipa": "/daɪˈnæm.ɪks/", "meaning": "sắc thái to nhỏ trong âm nhạc", "example": "The conductor emphasized the dynamics, going from soft to powerful."},
            {"word": "scale", "ipa": "/skeɪl/", "meaning": "gam nhạc", "example": "Students practice scales daily to improve their technical skills."},
            {"word": "major key", "ipa": "/ˈmeɪ.dʒər kiː/", "meaning": "giọng trưởng", "example": "Songs in a major key tend to sound happy and bright."},
            {"word": "minor key", "ipa": "/ˈmaɪ.nər kiː/", "meaning": "giọng thứ", "example": "Pieces in a minor key often convey sadness or tension."},
            {"word": "arrangement", "ipa": "/əˈreɪndʒ.mənt/", "meaning": "phần phối khí", "example": "The string arrangement added depth and emotion to the song."},
            {"word": "music notation", "ipa": "/ˈmjuː.zɪk nəʊˈteɪ.ʃən/", "meaning": "ký hiệu âm nhạc", "example": "Learning music notation allows musicians to read and write music."},
            {"word": "countermelody", "ipa": "/ˌkaʊn.tərˈmel.ə.di/", "meaning": "giai điệu phụ đối", "example": "The countermelody played by the flute complemented the main theme."},
            {"word": "syncopation", "ipa": "/ˌsɪŋ.kəˈpeɪ.ʃən/", "meaning": "đảo phách", "example": "The use of syncopation gives the rhythm a surprising, off-beat feel."},
            {"word": "modulation", "ipa": "/ˌmɒd.jʊˈleɪ.ʃən/", "meaning": "chuyển giọng", "example": "The unexpected modulation to a new key created an exciting moment."},
            {"word": "coda", "ipa": "/ˈkəʊ.də/", "meaning": "đoạn kết bài nhạc", "example": "The symphony ends with a dramatic coda that builds to a climax."},
            {"word": "interval", "ipa": "/ˈɪn.tə.vəl/", "meaning": "quãng (âm nhạc)", "example": "She practiced singing intervals to improve her pitch accuracy."},
            {"word": "staccato", "ipa": "/stəˈkɑː.təʊ/", "meaning": "kỹ thuật ngắt âm trong âm nhạc", "example": "The pianist played the opening phrase in sharp, staccato notes."},
            {"word": "legato", "ipa": "/lɪˈɡɑː.təʊ/", "meaning": "liền mạch, trơn tru (âm nhạc)", "example": "Play those notes legato to create a smooth, flowing sound."},
            {"word": "vibrato", "ipa": "/vɪˈbrɑː.təʊ/", "meaning": "kỹ thuật rung âm", "example": "Her vibrato gave the high notes a rich, warm quality."},
            {"word": "sight-reading", "ipa": "/saɪt ˈriː.dɪŋ/", "meaning": "đọc nhạc không qua luyện tập trước", "example": "Sight-reading is an important skill for professional musicians."},
            {"word": "music theory", "ipa": "/ˈmjuː.zɪk ˈθɪər.i/", "meaning": "lý thuyết âm nhạc", "example": "A solid understanding of music theory helps with composing and arranging."},
            {"word": "call and response", "ipa": "/kɔːl ənd rɪˈspɒns/", "meaning": "kỹ thuật hỏi-đáp trong âm nhạc", "example": "Call and response is a common technique in gospel and blues music."},
            {"word": "ostinato", "ipa": "/ˌɒs.tɪˈnɑː.təʊ/", "meaning": "mô-típ âm nhạc lặp đi lặp lại", "example": "The bass ostinato creates a hypnotic effect throughout the piece."},
            {"word": "rubato", "ipa": "/ruːˈbɑː.təʊ/", "meaning": "kỹ thuật linh hoạt tempo", "example": "She played the romantic ballad with expressive rubato."},
            {"word": "time signature", "ipa": "/taɪm ˈsɪɡ.nɪ.tʃər/", "meaning": "nhịp (ký hiệu thời gian)", "example": "A 3/4 time signature gives the music a waltz-like feel."},
            {"word": "fermata", "ipa": "/fɜːˈmɑː.tə/", "meaning": "dấu giữ nốt", "example": "The conductor held the fermata for several beats before releasing it."},
            {"word": "key signature", "ipa": "/kiː ˈsɪɡ.nɪ.tʃər/", "meaning": "giọng điệu (ký hiệu)", "example": "A key signature with four sharps indicates E major."},
            {"word": "transposition", "ipa": "/ˌtræn.spəˈzɪʃ.ən/", "meaning": "chuyển giọng/điều chỉnh khóa", "example": "Transposition allows a piece to be sung in a different key."},
            {"word": "pentatonic scale", "ipa": "/ˌpen.təˈtɒn.ɪk skeɪl/", "meaning": "gam ngũ âm", "example": "The pentatonic scale is widely used in folk and blues music."},
            {"word": "diatonic scale", "ipa": "/ˌdaɪ.əˈtɒn.ɪk skeɪl/", "meaning": "gam diatonic (7 âm)", "example": "Most Western classical music is based on the diatonic scale."},
            {"word": "music production", "ipa": "/ˈmjuː.zɪk prəˈdʌk.ʃən/", "meaning": "sản xuất âm nhạc", "example": "Music production involves recording, mixing, and mastering tracks."},
            {"word": "beat drop", "ipa": "/biːt drɒp/", "meaning": "đoạn nhạc bùng nổ (trong EDM)", "example": "The crowd went wild when the beat drop hit."},
            {"word": "looping", "ipa": "/ˈluː.pɪŋ/", "meaning": "lặp vòng âm thanh", "example": "He uses looping pedals to layer sounds during live performances."},
            {"word": "layering", "ipa": "/ˈleɪ.ər.ɪŋ/", "meaning": "chồng lớp âm thanh", "example": "Layering instruments creates a richer, more complex sound."},
            {"word": "recording session", "ipa": "/rɪˈkɔː.dɪŋ ˈseʃ.ən/", "meaning": "phiên thu âm", "example": "The recording session lasted 12 hours to capture the perfect sound."},
            {"word": "acoustic treatment", "ipa": "/əˈkuː.stɪk ˈtriːt.mənt/", "meaning": "xử lý âm học phòng thu", "example": "Acoustic treatment panels reduce unwanted sound reflections in a studio."},
            {"word": "mixing board", "ipa": "/ˈmɪk.sɪŋ bɔːd/", "meaning": "bàn trộn âm thanh", "example": "The sound engineer adjusted the levels on the mixing board."},
            {"word": "backing track", "ipa": "/ˈbæk.ɪŋ træk/", "meaning": "bản nhạc nền", "example": "She sang over a backing track during the live performance."},
            {"word": "reverb", "ipa": "/ˈriː.vɜːb/", "meaning": "hiệu ứng vang tiếng", "example": "Adding reverb to the vocals gives them a richer, fuller sound."},
            {"word": "EQ (equalization)", "ipa": "/ˌiː.kwəlaɪˈzeɪ.ʃən/", "meaning": "điều chỉnh tần số âm thanh", "example": "The sound engineer used EQ to balance the frequencies in the mix."},
            {"word": "mastering", "ipa": "/ˈmɑː.stər.ɪŋ/", "meaning": "xử lý cuối bản nhạc", "example": "Mastering is the final step before a song is released."},
            {"word": "overdubbing", "ipa": "/ˌəʊ.vəˈdʌb.ɪŋ/", "meaning": "thu chèn thêm âm", "example": "Overdubbing allows musicians to add new parts on top of existing recordings."},
            {"word": "music licensing", "ipa": "/ˈmjuː.zɪk ˈlaɪ.sən.sɪŋ/", "meaning": "cấp phép nhạc", "example": "Music licensing allows companies to legally use copyrighted songs in advertisements."},
            {"word": "royalties", "ipa": "/ˈrɔɪ.əl.tiz/", "meaning": "tiền bản quyền âm nhạc", "example": "Songwriters earn royalties every time their song is played on the radio."},
            {"word": "copyright", "ipa": "/ˈkɒp.i.raɪt/", "meaning": "bản quyền", "example": "Copyright law protects musicians from having their work copied without permission."},
            {"word": "music streaming", "ipa": "/ˈmjuː.zɪk ˈstriː.mɪŋ/", "meaning": "phát nhạc trực tuyến", "example": "Music streaming has changed how people discover and consume music."},
            {"word": "music charts", "ipa": "/ˈmjuː.zɪk tʃɑːts/", "meaning": "bảng xếp hạng âm nhạc", "example": "Her song climbed to number one on the music charts."},
            {"word": "genre blending", "ipa": "/ˈʒɒn.rə ˈblen.dɪŋ/", "meaning": "pha trộn thể loại nhạc", "example": "Genre blending creates exciting new musical styles."},
            {"word": "a cappella", "ipa": "/ˌæ kəˈpel.ə/", "meaning": "hát không nhạc đệm", "example": "The choir performed an impressive a cappella arrangement."},
            {"word": "music educator", "ipa": "/ˈmjuː.zɪk ˈed.jʊ.keɪ.tər/", "meaning": "giáo viên âm nhạc", "example": "A music educator inspires students to develop a lifelong love of music."},
        ],
        "B2": [
            {"word": "virtuoso", "ipa": "/vərʧuˈoʊsoʊ/", "meaning": "người bậc thầy nhạc cụ", "example": "The young virtuoso performed Paganini's concerto flawlessly."},
            {"word": "dissonance", "ipa": "/ˈdɪs.ə.nəns/", "meaning": "âm bất hòa", "example": "The composer used deliberate dissonance to create a sense of tension."},
            {"word": "crescendo", "ipa": "/krɪˈʃen.dəʊ/", "meaning": "đoạn nhạc tăng dần", "example": "The music built to a magnificent crescendo before the final silence."},
            {"word": "counterpoint", "ipa": "/ˈkaʊn.tə.pɔɪnt/", "meaning": "đối âm", "example": "Bach was a master of counterpoint, weaving multiple melodies together."},
            {"word": "syncopation", "ipa": "/ˌsɪŋ.kəˈpeɪ.ʃən/", "meaning": "đảo phách", "example": "The syncopation in jazz gives the music its characteristic swing feel."},
            {"word": "timbre", "ipa": "/ˈtæm.bər/", "meaning": "âm sắc", "example": "The timbre of a cello is richer and darker than that of a violin."},
            {"word": "music theory analysis", "ipa": "/ˈmjuː.zɪk ˈθɪər.i əˈnæl.ɪ.sɪs/", "meaning": "phân tích lý thuyết âm nhạc", "example": "Music theory analysis reveals the harmonic structure of complex compositions."},
            {"word": "enharmonic equivalent", "ipa": "/ˌen.ɑːˈmɒn.ɪk ɪˈkwɪv.ə.lənt/", "meaning": "âm đẳng hoà", "example": "C# and Db are enharmonic equivalents — same pitch, different notation."},
            {"word": "polyphony", "ipa": "/pəˈlɪf.ə.ni/", "meaning": "đa âm", "example": "Renaissance polyphony featured multiple independent vocal lines."},
            {"word": "homophony", "ipa": "/həˈmɒf.ə.ni/", "meaning": "đồng âm", "example": "Hymns are typically homophonic, with all voices moving together."},
            {"word": "modal harmony", "ipa": "/ˈməʊ.dəl ˈhɑː.mə.ni/", "meaning": "hòa âm theo thức", "example": "Modal harmony is widely used in folk music and certain jazz styles."},
            {"word": "extended technique", "ipa": "/ɪkˈsten.dɪd tekˈniːk/", "meaning": "kỹ thuật mở rộng nhạc cụ", "example": "Extended techniques include col legno bowing and harmonics on strings."},
            {"word": "spectral music", "ipa": "/ˈspek.trəl ˈmjuː.zɪk/", "meaning": "nhạc phổ âm học", "example": "Spectral music uses the harmonic series as the basis for composition."},
            {"word": "microtonality", "ipa": "/ˌmaɪ.krəʊ.təˈnæl.ɪ.ti/", "meaning": "vi âm (các âm nhỏ hơn nửa cung)", "example": "Microtonality explores pitches between the standard 12 semitones of Western music."},
            {"word": "aleatory music", "ipa": "/ˈeɪ.li.ə.tɒr.i ˈmjuː.zɪk/", "meaning": "nhạc ngẫu nhiên", "example": "Aleatory music leaves some elements to chance, such as the order of sections."},
            {"word": "music psychology", "ipa": "/ˈmjuː.zɪk saɪˈkɒl.ə.dʒi/", "meaning": "tâm lý học âm nhạc", "example": "Music psychology studies how music affects human emotions and behavior."},
            {"word": "cognitive neuroscience of music", "ipa": "/ˈkɒɡ.nɪ.tɪv ˌnjʊər.əʊˈsaɪəns əv ˈmjuː.zɪk/", "meaning": "thần kinh học nhận thức về âm nhạc", "example": "The cognitive neuroscience of music examines how the brain processes musical sounds."},
            {"word": "ethnomusicology", "ipa": "/ˌeθ.nəʊ.mjuː.zɪˈkɒl.ə.dʒi/", "meaning": "dân tộc nhạc học", "example": "Ethnomusicology studies music from different cultures around the world."},
            {"word": "music therapy", "ipa": "/ˈmjuː.zɪk ˈθer.ə.pi/", "meaning": "trị liệu bằng âm nhạc", "example": "Music therapy is used to help patients with anxiety and depression."},
            {"word": "soundscape", "ipa": "/ˈsaʊnd.skeɪp/", "meaning": "cảnh âm thanh", "example": "The composer created a rich soundscape using environmental sounds."},
            {"word": "ambient music", "ipa": "/ˈæm.bi.ənt ˈmjuː.zɪk/", "meaning": "nhạc ambient (nền)", "example": "Ambient music creates atmosphere without demanding the listener's full attention."},
            {"word": "minimalism", "ipa": "/ˈmɪn.ɪ.mə.lɪ.zəm/", "meaning": "chủ nghĩa tối giản trong âm nhạc", "example": "Minimalism in music uses repetitive patterns and gradual change."},
            {"word": "serialism", "ipa": "/ˈsɪər.i.ə.lɪ.zəm/", "meaning": "nhạc chuỗi âm", "example": "Serialism was developed by Schoenberg as an alternative to tonal music."},
            {"word": "twelve-tone technique", "ipa": "/twelv təʊn tekˈniːk/", "meaning": "kỹ thuật 12 nốt", "example": "The twelve-tone technique uses all 12 pitches equally to avoid tonality."},
            {"word": "neo-romanticism", "ipa": "/ˌniː.əʊ.rəʊˈmæn.tɪ.sɪ.zəm/", "meaning": "chủ nghĩa lãng mạn mới", "example": "Neo-romanticism in music revived expressive and emotional writing styles."},
            {"word": "impressionism", "ipa": "/ɪmˈpreʃ.ə.nɪ.zəm/", "meaning": "chủ nghĩa ấn tượng trong âm nhạc", "example": "Debussy is the most famous composer of musical impressionism."},
            {"word": "expressionism", "ipa": "/ɪkˈspreʃ.ə.nɪ.zəm/", "meaning": "chủ nghĩa biểu hiện trong âm nhạc", "example": "Musical expressionism sought to convey intense emotions through extreme dissonance."},
            {"word": "musique concrète", "ipa": "/mjuːˌziːk kɒnˈkret/", "meaning": "nhạc cụ thể", "example": "Musique concrète uses recorded sounds from everyday life as musical material."},
            {"word": "electroacoustic music", "ipa": "/ɪˌlek.trəʊ.əˈkuː.stɪk ˈmjuː.zɪk/", "meaning": "nhạc điện âm", "example": "Electroacoustic music blends electronic and acoustic sound sources."},
            {"word": "tape music", "ipa": "/teɪp ˈmjuː.zɪk/", "meaning": "nhạc băng từ", "example": "Tape music was an early form of electronic music using recorded and manipulated sounds."},
            {"word": "prepared piano", "ipa": "/prɪˈpeəd piˈæn.əʊ/", "meaning": "đàn piano cải biến", "example": "John Cage invented the prepared piano by placing objects between the strings."},
            {"word": "drone", "ipa": "/drəʊn/", "meaning": "âm nền kéo dài", "example": "The bagpipes create a constant drone beneath the melody."},
            {"word": "polyrhythm", "ipa": "/ˈpɒl.i.rɪð.əm/", "meaning": "đa nhịp", "example": "West African music is renowned for its complex polyrhythmic patterns."},
            {"word": "music licensing deal", "ipa": "/ˈmjuː.zɪk ˈlaɪ.sən.sɪŋ diːl/", "meaning": "thỏa thuận cấp phép nhạc", "example": "She signed a major music licensing deal with a Hollywood film studio."},
            {"word": "sync licensing", "ipa": "/sɪŋk ˈlaɪ.sən.sɪŋ/", "meaning": "cấp phép đồng bộ hóa", "example": "Sync licensing allows music to be used alongside visual media."},
            {"word": "performance rights organization", "ipa": "/pəˈfɔː.məns raɪts ˌɔː.ɡən.aɪˈzeɪ.ʃən/", "meaning": "tổ chức quyền biểu diễn", "example": "A performance rights organization collects royalties on behalf of songwriters."},
            {"word": "artist development", "ipa": "/ˈɑː.tɪst dɪˈvel.əp.mənt/", "meaning": "phát triển nghệ sĩ", "example": "Record labels invest heavily in artist development before releasing an album."},
            {"word": "360 deal", "ipa": "/360 dil/", "meaning": "hợp đồng âm nhạc toàn diện", "example": "A 360 deal gives the label a share of all of the artist's revenue streams."},
            {"word": "concept album", "ipa": "/ˈkɒn.sept ˈæl.bəm/", "meaning": "album theo chủ đề xuyên suốt", "example": "The band released a concept album that told a story across all 12 tracks."},
            {"word": "live recording", "ipa": "/laɪv rɪˈkɔː.dɪŋ/", "meaning": "thu âm trực tiếp", "example": "The live recording captured the energy of the concert perfectly."},
            {"word": "orchestration", "ipa": "/ˌɔː.kɪˈstreɪ.ʃən/", "meaning": "phối khí cho dàn nhạc", "example": "Her orchestration of the piece transformed a simple melody into a grand composition."},
            {"word": "harmonic analysis", "ipa": "/hɑːˈmɒn.ɪk əˈnæl.ɪ.sɪs/", "meaning": "phân tích hòa âm", "example": "Harmonic analysis of Beethoven reveals his revolutionary approach to tonality."},
            {"word": "voicing", "ipa": "/ˈvɔɪ.sɪŋ/", "meaning": "phân bổ các nốt trong hợp âm", "example": "The voicing of the chord gives it a warm, rich quality."},
            {"word": "voice leading", "ipa": "/vɔɪs ˈliː.dɪŋ/", "meaning": "dẫn dắt âm thanh giữa các nốt", "example": "Good voice leading ensures smooth transitions between chords."},
            {"word": "secondary dominant", "ipa": "/ˈsek.ən.dri ˈdɒm.ɪ.nənt/", "meaning": "âm chủ phụ", "example": "A secondary dominant creates tension before resolving to a new chord."},
            {"word": "deceptive cadence", "ipa": "/dɪˈsep.tɪv ˈkeɪ.dəns/", "meaning": "kết phách bất ngờ", "example": "The deceptive cadence surprised the listener with an unexpected resolution."},
            {"word": "non-functional harmony", "ipa": "/nɒn ˈfʌŋk.ʃən.əl ˈhɑː.mə.ni/", "meaning": "hòa âm phi chức năng", "example": "Non-functional harmony moves freely between chords without traditional rules."},
            {"word": "contrapuntal writing", "ipa": "/ˌkɒn.trəˈpʌn.təl ˈraɪ.tɪŋ/", "meaning": "viết đối âm", "example": "Contrapuntal writing requires each voice to be melodically independent."},
            {"word": "tonal center", "ipa": "/ˈtəʊ.nəl ˈsen.tər/", "meaning": "trung tâm giọng điệu", "example": "The tonal center of the piece shifts unexpectedly in the second movement."},
            {"word": "motivic development", "ipa": "/məʊˈtiː.vɪk dɪˈvel.əp.mənt/", "meaning": "phát triển mô-típ nhạc", "example": "Beethoven was famous for his motivic development of short musical ideas."},
        ],
        "C1": [
            {"word": "atonality", "ipa": "/ˌeɪ.təʊˈnæl.ɪ.ti/", "meaning": "phi điệu tính", "example": "Schoenberg's atonality abandoned the traditional hierarchy of tonal music."},
            {"word": "chromaticism", "ipa": "/krəˈmæt.ɪ.sɪ.zəm/", "meaning": "kỹ thuật nửa cung", "example": "Wagner's chromaticism pushed the boundaries of tonal harmony."},
            {"word": "leitmotif", "ipa": "/ˈlaɪt.məʊ.tiːf/", "meaning": "chủ đề âm nhạc gắn với nhân vật", "example": "Wagner used leitmotifs to represent characters and ideas in his operas."},
            {"word": "cadenza", "ipa": "/kəˈden.zə/", "meaning": "đoạn độc tấu phô diễn kỹ thuật", "example": "The pianist performed a brilliant cadenza in the first movement of the concerto."},
            {"word": "tessitura", "ipa": "/ˌtes.ɪˈtjʊər.ə/", "meaning": "vùng âm vực thoải mái của giọng hát", "example": "The tessitura of that aria is very high, suited only for lyric sopranos."},
            {"word": "dodecaphony", "ipa": "/ˌdəʊ.dɪˈkæf.ə.ni/", "meaning": "âm nhạc 12 nốt", "example": "Dodecaphony treats all 12 notes of the chromatic scale equally."},
            {"word": "musica ficta", "ipa": "/ˈmjuː.zɪ.kə ˈfɪk.tə/", "meaning": "âm nhạc giả (nốt bị thay đổi ngoài khóa)", "example": "Musica ficta refers to accidentals added to medieval music for smoother voice leading."},
            {"word": "set theory in music", "ipa": "/set ˈθɪər.i ɪn ˈmjuː.zɪk/", "meaning": "lý thuyết tập hợp trong âm nhạc", "example": "Set theory in music analyzes groups of pitches to reveal compositional patterns."},
            {"word": "spectral analysis", "ipa": "/ˈspek.trəl əˈnæl.ɪ.sɪs/", "meaning": "phân tích phổ âm thanh", "example": "Spectral analysis of a musical instrument reveals its overtone structure."},
            {"word": "acoustic ecology", "ipa": "/əˈkuː.stɪk ɪˈkɒl.ə.dʒi/", "meaning": "sinh thái âm thanh", "example": "Acoustic ecology studies the relationship between living organisms and the sounds of their environment."},
            {"word": "xenharmonic", "ipa": "/ˌzen.ɑːˈmɒn.ɪk/", "meaning": "ngoài hệ âm bình quân", "example": "Xenharmonic tuning systems explore pitches outside the standard 12-tone equal temperament."},
            {"word": "just intonation", "ipa": "/dʒʌst ˌɪn.təˈneɪ.ʃən/", "meaning": "điều chỉnh âm thanh theo tỷ lệ tự nhiên", "example": "Just intonation produces purer intervals by using simple frequency ratios."},
            {"word": "equal temperament", "ipa": "/ˈiː.kwəl ˈtem.pər.ə.mənt/", "meaning": "điều chỉnh âm bình quân 12 nửa cung", "example": "Equal temperament divides the octave into 12 equal semitones for consistent tuning."},
            {"word": "pitch class", "ipa": "/pɪtʃ klɑːs/", "meaning": "lớp cao độ", "example": "In set theory, a pitch class includes all octave equivalents of a note."},
            {"word": "aggregate completion", "ipa": "/ˈæɡ.rɪ.ɡɪt kəmˈpliː.ʃən/", "meaning": "hoàn tất tập hợp 12 âm", "example": "Serial composers aim for aggregate completion by using all 12 pitch classes."},
            {"word": "retrograde", "ipa": "/ˈret.rəʊ.ɡreɪd/", "meaning": "đọc ngược lại (âm nhạc)", "example": "Playing the theme in retrograde reverses the original sequence of notes."},
            {"word": "inversion (music)", "ipa": "/ˌɪnˈvərʒən (mˈjuzɪk)/", "meaning": "đảo ngược giai điệu", "example": "The inversion of the melody flips the intervals upside down."},
            {"word": "augmentation", "ipa": "/ˌɔːɡ.menˈteɪ.ʃən/", "meaning": "kéo dài giá trị nốt nhạc", "example": "Augmentation presents the theme with each note doubled in length."},
            {"word": "diminution", "ipa": "/ˌdɪm.ɪˈnjuː.ʃən/", "meaning": "rút ngắn giá trị nốt nhạc", "example": "Diminution speeds up the theme by halving the note values."},
            {"word": "canonic imitation", "ipa": "/kəˈnɒn.ɪk ˌɪm.ɪˈteɪ.ʃən/", "meaning": "bắt chước theo canon", "example": "The fugue opens with canonic imitation between the soprano and bass."},
            {"word": "stretto", "ipa": "/ˈstret.əʊ/", "meaning": "đoạn fugue chồng chủ đề", "example": "In the stretto, the subject entries overlap, creating great intensity."},
            {"word": "pedagogy (music)", "ipa": "/ˈpɛdəˌgoʊʤi (mˈjuzɪk)/", "meaning": "sư phạm âm nhạc", "example": "Music pedagogy encompasses teaching methods for all levels of learners."},
            {"word": "music cognition", "ipa": "/ˈmjuː.zɪk kɒɡˈnɪʃ.ən/", "meaning": "nhận thức âm nhạc", "example": "Music cognition research examines how humans perceive and understand music."},
            {"word": "timbral evolution", "ipa": "/ˈtæm.brəl ˌiː.vəˈluː.ʃən/", "meaning": "sự tiến hóa âm sắc", "example": "Timbral evolution in electronic music reflects advances in synthesis technology."},
            {"word": "spectral flux", "ipa": "/ˈspek.trəl flʌks/", "meaning": "biến đổi phổ âm", "example": "Spectral flux measures how the frequency content of a sound changes over time."},
            {"word": "noise music", "ipa": "/nɔɪz ˈmjuː.zɪk/", "meaning": "nhạc tiếng ồn", "example": "Noise music challenges traditional definitions of music by using sound as pure texture."},
            {"word": "idiomatic writing", "ipa": "/ˌɪd.i.əˈmæt.ɪk ˈraɪ.tɪŋ/", "meaning": "viết nhạc phù hợp với đặc tính nhạc cụ", "example": "Idiomatic writing takes full advantage of each instrument's unique capabilities."},
            {"word": "heterophony", "ipa": "/ˌhet.ə.ˈrɒf.ə.ni/", "meaning": "đa thanh đồng biến tấu", "example": "Heterophony is common in Middle Eastern and South Asian music traditions."},
            {"word": "isorhythm", "ipa": "/ˈaɪ.sə.rɪð.əm/", "meaning": "nhịp đẳng điệu (âm nhạc trung cổ)", "example": "Isorhythm uses repeating rhythmic patterns in medieval motets."},
            {"word": "hocket", "ipa": "/ˈhɒk.ɪt/", "meaning": "kỹ thuật hát ngắt quãng xen kẽ", "example": "In hocket, two voices alternate notes rapidly to create a single melody."},
            {"word": "phasing (music)", "ipa": "/ˈfeɪ.zɪŋ/", "meaning": "kỹ thuật lệch pha (âm nhạc)", "example": "Steve Reich's phasing technique gradually shifts identical patterns out of sync."},
            {"word": "prepared electronics", "ipa": "/prɪˈpeəd ɪˌlek.ˈtrɒn.ɪks/", "meaning": "điện tử chuẩn bị sẵn", "example": "Live performers use prepared electronics to modify and process sound in real time."},
            {"word": "algorithmic composition", "ipa": "/ˌæl.ɡəˈrɪð.mɪk ˌkɒm.pəˈzɪʃ.ən/", "meaning": "sáng tác bằng thuật toán", "example": "Algorithmic composition uses mathematical rules to generate musical material."},
            {"word": "generative music", "ipa": "/ˈdʒen.ər.ə.tɪv ˈmjuː.zɪk/", "meaning": "nhạc tự sinh", "example": "Generative music creates itself according to programmed rules, producing endless variations."},
            {"word": "corpus-based concatenative synthesis", "ipa": "/ˈkɔː.pəs beɪst kənˈkæt.ə.nə.tɪv ˈsɪn.θɪ.sɪs/", "meaning": "tổng hợp âm từ kho âm mẫu", "example": "Corpus-based synthesis selects and sequences sound units from a large database."},
            {"word": "timbral morphing", "ipa": "/ˈtæm.brəl ˈmɔː.fɪŋ/", "meaning": "biến đổi âm sắc dần dần", "example": "Timbral morphing smoothly transitions between different instrument sounds."},
            {"word": "electroacoustic improvisation", "ipa": "/ɪˌlek.trəʊ.əˈkuː.stɪk ɪmˌprɒv.ɪˈzeɪ.ʃən/", "meaning": "ứng tấu điện âm", "example": "Electroacoustic improvisation blends live instruments with real-time sound processing."},
            {"word": "music informatics", "ipa": "/ˈmjuː.zɪk ˌɪn.fəˈmæt.ɪks/", "meaning": "tin học âm nhạc", "example": "Music informatics applies computational methods to music analysis and retrieval."},
            {"word": "automatic music transcription", "ipa": "/ˌɔː.tə.mæt.ɪk ˈmjuː.zɪk træn.ˈskrɪp.ʃən/", "meaning": "chuyển âm thanh thành ký hiệu tự động", "example": "Automatic music transcription systems convert audio recordings into sheet music."},
            {"word": "source separation", "ipa": "/sɔːs ˌsep.əˈreɪ.ʃən/", "meaning": "tách nguồn âm", "example": "Source separation technology isolates individual instruments from a mixed recording."},
            {"word": "music affective computing", "ipa": "/ˈmjuː.zɪk əˈfek.tɪv kəmˈpjuː.tɪŋ/", "meaning": "tính toán cảm xúc qua âm nhạc", "example": "Music affective computing analyzes the emotional content of music automatically."},
            {"word": "generative adversarial network for music", "ipa": "/ˈdʒen.ər.ə.tɪv ədˈvɜː.sər.i.əl ˈnet.wɜːk fər ˈmjuː.zɪk/", "meaning": "mạng đối kháng sinh cho nhạc", "example": "Researchers use generative adversarial networks to compose original music."},
            {"word": "music semantics", "ipa": "/ˈmjuː.zɪk sɪˈmæn.tɪks/", "meaning": "ngữ nghĩa học âm nhạc", "example": "Music semantics studies how meaning is conveyed through musical structures."},
            {"word": "ontomusicology", "ipa": "/ˌɒn.tə.mjuː.zɪˈkɒl.ə.dʒi/", "meaning": "bản thể luận âm nhạc", "example": "Ontomusicology investigates the nature and being of musical works."},
            {"word": "cross-cultural musicology", "ipa": "/krɒs ˈkʌl.tʃər.əl mjuː.zɪˈkɒl.ə.dʒi/", "meaning": "âm nhạc học xuyên văn hóa", "example": "Cross-cultural musicology compares musical traditions from different societies."},
            {"word": "intertextuality in music", "ipa": "/ˌɪn.tə.teks.tʃuˈæl.ɪ.ti ɪn ˈmjuː.zɪk/", "meaning": "liên văn bản trong âm nhạc", "example": "Intertextuality in music occurs when a composer quotes or alludes to earlier works."},
            {"word": "music and identity", "ipa": "/ˈmjuː.zɪk ənd aɪˈden.tɪ.ti/", "meaning": "âm nhạc và bản sắc", "example": "Research on music and identity explores how musical preferences shape self-concept."},
            {"word": "digital signal processing", "ipa": "/ˈdɪdʒ.ɪ.təl ˈsɪɡ.nəl ˈprəʊ.ses.ɪŋ/", "meaning": "xử lý tín hiệu số", "example": "Digital signal processing enables real-time audio effects in music production."},
            {"word": "perceptual audio coding", "ipa": "/pəˈsep.tju.əl ˈɔː.di.əʊ ˈkəʊ.dɪŋ/", "meaning": "mã hóa âm thanh tri giác", "example": "Perceptual audio coding removes sounds that humans cannot hear to compress files."},
            {"word": "binaural audio", "ipa": "/baɪˈnjʊər.əl ˈɔː.di.əʊ/", "meaning": "âm thanh nhị nhĩ (3D audio)", "example": "Binaural audio creates a three-dimensional sound experience using headphones."},
            {"word": "adaptive music system", "ipa": "/əˈdæp.tɪv ˈmjuː.zɪk ˈsɪs.təm/", "meaning": "hệ thống nhạc thích nghi", "example": "An adaptive music system changes the soundtrack dynamically based on player actions."},
        ],
    },
    "social_media": {
        "A1": [
            {"word": "post", "ipa": "/pəʊst/", "meaning": "bài đăng; đăng lên", "example": "She posted a photo of her lunch on Instagram."},
            {"word": "like", "ipa": "/laɪk/", "meaning": "thích; nhấn like", "example": "He liked all of her photos on Instagram."},
            {"word": "share", "ipa": "/ʃeər/", "meaning": "chia sẻ bài viết", "example": "She shared the funny video with her friends."},
            {"word": "comment", "ipa": "/ˈkɒm.ənt/", "meaning": "bình luận", "example": "He left a kind comment on her birthday photo."},
            {"word": "follow", "ipa": "/ˈfɒl.əʊ/", "meaning": "theo dõi (tài khoản)", "example": "She follows over 500 people on Instagram."},
            {"word": "friend", "ipa": "/frend/", "meaning": "bạn bè (mạng xã hội)", "example": "She has 200 friends on Facebook."},
            {"word": "photo", "ipa": "/ˈfəʊ.təʊ/", "meaning": "ảnh", "example": "She uploads a new photo every day."},
            {"word": "video", "ipa": "/ˈvɪd.i.əʊ/", "meaning": "video", "example": "He watched a funny video on TikTok."},
            {"word": "story", "ipa": "/ˈstɔː.ri/", "meaning": "story (tin tức tạm thời 24h)", "example": "She posted a story of her morning run."},
            {"word": "profile", "ipa": "/ˈprəʊ.faɪl/", "meaning": "hồ sơ/trang cá nhân", "example": "He updated his profile picture on Facebook."},
            {"word": "message", "ipa": "/ˈmes.ɪdʒ/", "meaning": "tin nhắn", "example": "She sent him a message to say happy birthday."},
            {"word": "group", "ipa": "/ɡruːp/", "meaning": "nhóm mạng xã hội", "example": "She joined a Facebook group for English learners."},
            {"word": "hashtag", "ipa": "/ˈhæʃ.tæɡ/", "meaning": "hashtag (thẻ #)", "example": "She added hashtags to her post to reach more people."},
            {"word": "tag", "ipa": "/tæɡ/", "meaning": "gắn thẻ người dùng", "example": "She tagged her friends in the group photo."},
            {"word": "notification", "ipa": "/ˌnəʊ.tɪ.fɪˈkeɪ.ʃən/", "meaning": "thông báo", "example": "He turned off notifications to focus on studying."},
            {"word": "account", "ipa": "/əˈkaʊnt/", "meaning": "tài khoản mạng xã hội", "example": "She created a new account on TikTok."},
            {"word": "username", "ipa": "/ˈjuː.zər.neɪm/", "meaning": "tên người dùng", "example": "Her username is @happyvibes on Instagram."},
            {"word": "feed", "ipa": "/fiːd/", "meaning": "bảng tin (newsfeed)", "example": "He scrolls through his feed every morning."},
            {"word": "scroll", "ipa": "/skrəʊl/", "meaning": "cuộn (màn hình)", "example": "She spent an hour scrolling through her feed."},
            {"word": "upload", "ipa": "/ˌʌpˈləʊd/", "meaning": "tải lên", "example": "He uploaded a new video to his YouTube channel."},
            {"word": "download", "ipa": "/ˌdaʊnˈləʊd/", "meaning": "tải xuống", "example": "She downloaded the TikTok app on her phone."},
            {"word": "live", "ipa": "/laɪv/", "meaning": "phát trực tiếp", "example": "She went live on Instagram to chat with her followers."},
            {"word": "caption", "ipa": "/ˈkæp.ʃən/", "meaning": "chú thích ảnh/video", "example": "She wrote a funny caption for the beach photo."},
            {"word": "emoji", "ipa": "/ɪˈməʊ.dʒi/", "meaning": "biểu tượng cảm xúc", "example": "She added a heart emoji at the end of her comment."},
            {"word": "meme", "ipa": "/miːm/", "meaning": "meme hài hước", "example": "He shared a hilarious meme with his friends."},
            {"word": "reaction", "ipa": "/riˈæk.ʃən/", "meaning": "phản ứng cảm xúc (Facebook)", "example": "The post got thousands of reactions in one hour."},
            {"word": "repost", "ipa": "/ˌriːˈpəʊst/", "meaning": "đăng lại bài của người khác", "example": "She reposted the inspiring quote to her story."},
            {"word": "block", "ipa": "/blɒk/", "meaning": "chặn (người dùng)", "example": "She blocked the account that was sending spam."},
            {"word": "unfollow", "ipa": "/ʌnˈfɒl.əʊ/", "meaning": "hủy theo dõi", "example": "He unfollowed accounts that made him feel bad."},
            {"word": "subscribe", "ipa": "/səbˈskraɪb/", "meaning": "đăng ký kênh", "example": "She subscribed to her favorite cooking channel."},
            {"word": "channel", "ipa": "/ˈtʃæn.əl/", "meaning": "kênh (YouTube)", "example": "His YouTube channel has over 100,000 subscribers."},
            {"word": "view", "ipa": "/vjuː/", "meaning": "lượt xem", "example": "The video got one million views in 24 hours."},
            {"word": "viral", "ipa": "/ˈvaɪ.rəl/", "meaning": "lan truyền nhanh (viral)", "example": "The funny cat video went viral overnight."},
            {"word": "trend", "ipa": "/trend/", "meaning": "xu hướng mạng xã hội", "example": "She followed the latest TikTok dance trend."},
            {"word": "filter", "ipa": "/ˈfɪl.tər/", "meaning": "bộ lọc ảnh", "example": "She applied a vintage filter to the photo."},
            {"word": "reel", "ipa": "/riːl/", "meaning": "reel (video ngắn trên Instagram)", "example": "She posted a reel showing her morning routine."},
            {"word": "page", "ipa": "/peɪdʒ/", "meaning": "trang (Facebook page)", "example": "She liked the brand's Facebook page to follow updates."},
            {"word": "event", "ipa": "/ɪˈvent/", "meaning": "sự kiện (mạng xã hội)", "example": "He created a Facebook event for his birthday party."},
            {"word": "online", "ipa": "/ˈɒn.laɪn/", "meaning": "trực tuyến", "example": "She met her best friend online through a gaming group."},
            {"word": "private", "ipa": "/ˈpraɪ.vɪt/", "meaning": "riêng tư", "example": "She set her account to private so only friends can see."},
            {"word": "public", "ipa": "/ˈpʌb.lɪk/", "meaning": "công khai", "example": "His account is public, so anyone can follow him."},
            {"word": "link", "ipa": "/lɪŋk/", "meaning": "Liên kết, đường dẫn", "example": "Click the link to visit the website."},
            {"word": "app", "ipa": "/æp/", "meaning": "ứng dụng mạng xã hội", "example": "TikTok is the most downloaded app of the year."},
            {"word": "chat", "ipa": "/tʃæt/", "meaning": "trò chuyện", "example": "She chatted with her friends on Messenger."},
            {"word": "status", "ipa": "/ˈsteɪ.təs/", "meaning": "trạng thái (mạng xã hội)", "example": "She updated her Facebook status to share good news."},
            {"word": "bio", "ipa": "/ˈbaɪ.əʊ/", "meaning": "tiểu sử ngắn (profile)", "example": "Her Instagram bio says she loves travel and coffee."},
            {"word": "follower", "ipa": "/ˈfɒl.əʊ.ər/", "meaning": "người theo dõi", "example": "She gained 1,000 new followers after the post went viral."},
            {"word": "icon", "ipa": "/ˈaɪ.kɒn/", "meaning": "biểu tượng giao diện", "example": "Tap the heart icon to like the post."},
            {"word": "avatar", "ipa": "/ˈæv.ə.tɑːr/", "meaning": "ảnh đại diện", "example": "She chose a cartoon avatar for her profile picture."},
            {"word": "trending", "ipa": "/ˈtren.dɪŋ/", "meaning": "đang thịnh hành", "example": "The song is trending on TikTok right now."},
        ],
        "A2": [
            {"word": "influencer", "ipa": "/ˈɪn.fluː.ən.sər/", "meaning": "người có ảnh hưởng trên mạng", "example": "She is a popular beauty influencer with 2 million followers."},
            {"word": "content creator", "ipa": "/ˈkɒn.tent kriˈeɪ.tər/", "meaning": "người tạo nội dung", "example": "He is a content creator who makes daily travel videos."},
            {"word": "engagement", "ipa": "/ɪnˈɡeɪdʒ.mənt/", "meaning": "mức độ tương tác", "example": "Her posts have high engagement with lots of likes and comments."},
            {"word": "reach", "ipa": "/riːtʃ/", "meaning": "độ tiếp cận bài viết", "example": "The campaign reached 5 million people on social media."},
            {"word": "analytics", "ipa": "/ˌæn.əˈlɪt.ɪks/", "meaning": "phân tích số liệu mạng xã hội", "example": "She checks her analytics to understand her audience better."},
            {"word": "algorithm", "ipa": "/ˈæl.ɡə.rɪð.əm/", "meaning": "thuật toán mạng xã hội", "example": "The Instagram algorithm shows posts based on your interests."},
            {"word": "platform", "ipa": "/ˈplæt.fɔːm/", "meaning": "nền tảng mạng xã hội", "example": "She uses multiple platforms to share her content."},
            {"word": "community", "ipa": "/kəˈmjuː.nɪ.ti/", "meaning": "cộng đồng trực tuyến", "example": "She built a supportive online community around her cooking channel."},
            {"word": "audience", "ipa": "/ˈɔː.di.əns/", "meaning": "khán giả/đối tượng theo dõi", "example": "She creates content that resonates with her young audience."},
            {"word": "brand partnership", "ipa": "/brænd ˈpɑːt.nər.ʃɪp/", "meaning": "hợp tác thương hiệu", "example": "She earned money through brand partnerships with beauty companies."},
            {"word": "sponsorship", "ipa": "/ˈspɒn.sə.ʃɪp/", "meaning": "tài trợ", "example": "The YouTuber got a sponsorship from an online learning platform."},
            {"word": "promote", "ipa": "/prəˈməʊt/", "meaning": "quảng bá, tiếp thị", "example": "She promoted the new product through her Instagram stories."},
            {"word": "clickbait", "ipa": "/ˈklɪk.beɪt/", "meaning": "tiêu đề giật gân để thu hút click", "example": "The misleading headline was pure clickbait."},
            {"word": "troll", "ipa": "/trəʊl/", "meaning": "kẻ quấy rối trực tuyến", "example": "She reported the troll who left offensive comments."},
            {"word": "cyberbullying", "ipa": "/ˈsaɪ.bəˌbʊl.i.ɪŋ/", "meaning": "bắt nạt trực tuyến", "example": "Cyberbullying is a serious issue affecting many young people."},
            {"word": "spam", "ipa": "/spæm/", "meaning": "tin nhắn rác", "example": "She marked the unwanted email as spam."},
            {"word": "fake news", "ipa": "/feɪk njuːz/", "meaning": "tin tức giả mạo", "example": "Always verify information before sharing to avoid spreading fake news."},
            {"word": "misinformation", "ipa": "/ˌmɪs.ɪn.fəˈmeɪ.ʃən/", "meaning": "thông tin sai lệch", "example": "Social media has made it easier to spread misinformation."},
            {"word": "privacy settings", "ipa": "/ˈprɪv.ə.si ˈset.ɪŋz/", "meaning": "cài đặt quyền riêng tư", "example": "Review your privacy settings to control who sees your posts."},
            {"word": "data privacy", "ipa": "/ˈdeɪ.tə ˈprɪv.ə.si/", "meaning": "bảo mật dữ liệu cá nhân", "example": "Data privacy concerns are growing as platforms collect more user information."},
            {"word": "digital footprint", "ipa": "/ˈdɪdʒ.ɪ.təl ˈfʊt.prɪnt/", "meaning": "dấu chân số", "example": "Be careful about your digital footprint — everything you post stays online."},
            {"word": "unboxing", "ipa": "/ˌʌnˈbɒk.sɪŋ/", "meaning": "video mở hộp sản phẩm", "example": "Unboxing videos are extremely popular on YouTube."},
            {"word": "review", "ipa": "/rɪˈvjuː/", "meaning": "đánh giá sản phẩm/dịch vụ", "example": "She posted an honest review of the skincare product."},
            {"word": "tutorial", "ipa": "/tjuːˈtɔː.ri.əl/", "meaning": "video hướng dẫn", "example": "She posted a makeup tutorial that got 500,000 views."},
            {"word": "vlog", "ipa": "/vlɒɡ/", "meaning": "nhật ký video", "example": "She vlogs her daily life and shares it on YouTube."},
            {"word": "podcast", "ipa": "/ˈpɒd.kɑːst/", "meaning": "podcast (phát thanh số)", "example": "She launched a weekly podcast about personal finance."},
            {"word": "livestream", "ipa": "/ˈlaɪv.striːm/", "meaning": "phát trực tiếp", "example": "She does a cooking livestream every Sunday evening."},
            {"word": "short-form video", "ipa": "/ʃɔːt fɔːm ˈvɪd.i.əʊ/", "meaning": "video ngắn", "example": "TikTok popularized short-form video content worldwide."},
            {"word": "content calendar", "ipa": "/ˈkɒn.tent ˈkæl.ɪn.dər/", "meaning": "lịch đăng nội dung", "example": "She plans her posts using a content calendar."},
            {"word": "scheduling", "ipa": "/ˈskɛʤʊlɪŋ/", "meaning": "lên lịch đăng bài", "example": "She uses a tool for scheduling her Instagram posts in advance."},
            {"word": "cross-posting", "ipa": "/ˈkrɒs ˌpəʊs.tɪŋ/", "meaning": "đăng bài trên nhiều nền tảng cùng lúc", "example": "Cross-posting saves time by sharing content across multiple platforms."},
            {"word": "repurposing content", "ipa": "/ˌriːˈpɜː.pəs.ɪŋ ˈkɒn.tent/", "meaning": "tái sử dụng nội dung", "example": "She repurposed her blog posts into short Instagram carousels."},
            {"word": "engagement rate", "ipa": "/ɪnˈɡeɪdʒ.mənt reɪt/", "meaning": "tỷ lệ tương tác", "example": "Micro-influencers often have a higher engagement rate than celebrities."},
            {"word": "impressions", "ipa": "/ɪmˈpreʃ.ənz/", "meaning": "số lần hiển thị", "example": "The ad generated 2 million impressions in one week."},
            {"word": "click-through rate", "ipa": "/klɪk θruː reɪt/", "meaning": "tỷ lệ nhấp vào", "example": "A compelling call to action improves the click-through rate."},
            {"word": "conversion rate", "ipa": "/kənˈvɜː.ʃən reɪt/", "meaning": "tỷ lệ chuyển đổi", "example": "The campaign's conversion rate exceeded expectations."},
            {"word": "niche", "ipa": "/nɪʧ/", "meaning": "thị trường ngách", "example": "She focuses on a niche audience interested in sustainable living."},
            {"word": "micro-influencer", "ipa": "/ˈmaɪ.krəʊ ˈɪn.fluː.ən.sər/", "meaning": "người ảnh hưởng nhỏ (1K-100K followers)", "example": "Micro-influencers have loyal followings and high trust from their audience."},
            {"word": "nano-influencer", "ipa": "/ˈnæn.əʊ ˈɪn.fluː.ən.sər/", "meaning": "người ảnh hưởng siêu nhỏ (dưới 10K)", "example": "Nano-influencers have very personal connections with their small but engaged audience."},
            {"word": "UGC (user-generated content)", "ipa": "/ˌjuː.dʒiːˈsiː/", "meaning": "nội dung do người dùng tạo ra", "example": "Brands love UGC because it is authentic and trustworthy."},
            {"word": "call to action (CTA)", "ipa": "/kɔːl tə ˈæk.ʃən/", "meaning": "lời kêu gọi hành động", "example": "Every post should include a clear call to action."},
            {"word": "swipe up", "ipa": "/swaɪp ʌp/", "meaning": "vuốt lên để xem thêm", "example": "Swipe up on the story to see the full product page."},
            {"word": "link in bio", "ipa": "/lɪŋk ɪn ˈbaɪ.əʊ/", "meaning": "link trong bio profile", "example": "Check the link in bio for the full recipe."},
            {"word": "DM (direct message)", "ipa": "/ˌdiːˈem/", "meaning": "tin nhắn riêng tư", "example": "She received a DM from a brand asking for collaboration."},
            {"word": "pin", "ipa": "/pɪn/", "meaning": "ghim bài (Pinterest)", "example": "She pinned her favorite recipe to a board on Pinterest."},
            {"word": "tweet", "ipa": "/twiːt/", "meaning": "tweet (đăng lên Twitter/X)", "example": "He tweeted his opinion on the latest news."},
            {"word": "retweet", "ipa": "/ˌriːˈtwiːt/", "meaning": "retweet (chia sẻ tweet)", "example": "The celebrity retweeted her post about climate change."},
            {"word": "thread", "ipa": "/θred/", "meaning": "chuỗi tweet/bài viết liên quan", "example": "He wrote a long Twitter thread explaining the issue."},
            {"word": "subreddit", "ipa": "/ˈsʌb.red.ɪt/", "meaning": "diễn đàn con trên Reddit", "example": "She found helpful advice on a travel subreddit."},
            {"word": "trendsetter", "ipa": "/ˈtrɛndˌsɛtər/", "meaning": "Người dẫn đầu xu hướng", "example": "She is a trendsetter in the fashion industry."},
        ],
        "B1": [
            {"word": "social media marketing", "ipa": "/ˈsəʊ.ʃəl ˈmiː.di.ə ˈmɑː.kɪ.tɪŋ/", "meaning": "tiếp thị qua mạng xã hội", "example": "Social media marketing is now essential for every brand."},
            {"word": "content strategy", "ipa": "/ˈkɒn.tent ˈstræt.ɪ.dʒi/", "meaning": "chiến lược nội dung", "example": "A strong content strategy drives consistent audience growth."},
            {"word": "brand voice", "ipa": "/brænd vɔɪs/", "meaning": "giọng điệu thương hiệu", "example": "Wendy's Twitter brand voice is playful and witty."},
            {"word": "social listening", "ipa": "/ˈsəʊ.ʃəl ˈlɪs.ən.ɪŋ/", "meaning": "lắng nghe mạng xã hội", "example": "Social listening monitors what people say about your brand online."},
            {"word": "sentiment analysis", "ipa": "/ˈsen.tɪ.mənt əˈnæl.ɪ.sɪs/", "meaning": "phân tích cảm xúc người dùng", "example": "Sentiment analysis reveals whether brand mentions are positive or negative."},
            {"word": "community management", "ipa": "/kəˈmjuː.nɪ.ti ˈmæn.ɪdʒ.mənt/", "meaning": "quản lý cộng đồng trực tuyến", "example": "Community management involves responding to comments and fostering engagement."},
            {"word": "reputation management", "ipa": "/ˌrep.jʊˈteɪ.ʃən ˈmæn.ɪdʒ.mənt/", "meaning": "quản lý danh tiếng trực tuyến", "example": "Reputation management protects a brand's image during crises."},
            {"word": "crisis communication", "ipa": "/ˈkraɪ.sɪs kəˌmjuː.nɪˈkeɪ.ʃən/", "meaning": "truyền thông khủng hoảng", "example": "Effective crisis communication can save a brand's reputation."},
            {"word": "paid media", "ipa": "/peɪd ˈmiː.di.ə/", "meaning": "quảng cáo trả phí", "example": "Paid media includes promoted posts and sponsored ads on social platforms."},
            {"word": "organic reach", "ipa": "/ɔːˈɡæn.ɪk riːtʃ/", "meaning": "tiếp cận tự nhiên (không trả phí)", "example": "Organic reach has declined as platforms prioritize paid content."},
            {"word": "paid reach", "ipa": "/peɪd riːtʃ/", "meaning": "tiếp cận trả phí", "example": "Brands increase their visibility through paid reach on social media."},
            {"word": "boosted post", "ipa": "/ˈbuːst.ɪd pəʊst/", "meaning": "bài viết được quảng bá", "example": "She boosted her post to reach a wider audience."},
            {"word": "target audience", "ipa": "/ˈtɑː.ɡɪt ˈɔː.di.əns/", "meaning": "đối tượng mục tiêu", "example": "Define your target audience before launching a social media campaign."},
            {"word": "demographic targeting", "ipa": "/ˌdem.əˈɡræf.ɪk ˈtɑː.ɡɪ.tɪŋ/", "meaning": "nhắm mục tiêu theo nhân khẩu học", "example": "Demographic targeting delivers ads to the right age and gender groups."},
            {"word": "behavioral targeting", "ipa": "/bɪˈheɪ.vjər.əl ˈtɑː.ɡɪ.tɪŋ/", "meaning": "nhắm mục tiêu theo hành vi", "example": "Behavioral targeting shows ads based on user browsing and purchase history."},
            {"word": "retargeting", "ipa": "/ˌriːˈtɑː.ɡɪ.tɪŋ/", "meaning": "tiếp thị lại", "example": "Retargeting shows ads to users who have previously visited your website."},
            {"word": "lookalike audience", "ipa": "/ˈlʊk.ə.laɪk ˈɔː.di.əns/", "meaning": "đối tượng tương tự", "example": "Facebook's lookalike audience feature finds users similar to your existing customers."},
            {"word": "A/B testing (social media)", "ipa": "/ˌeɪˈbiː ˈtes.tɪŋ/", "meaning": "thử nghiệm A/B nội dung", "example": "A/B testing compares two versions of a post to see which performs better."},
            {"word": "key performance indicators", "ipa": "/kiː pəˈfɔː.məns ˈɪn.dɪ.keɪ.tərz/", "meaning": "chỉ số hiệu suất then chốt", "example": "Track KPIs like engagement rate and follower growth monthly."},
            {"word": "ROI (return on investment)", "ipa": "/rɔɪ (rɪˈtərn ɔn ˌɪnˈvɛstmənt)/", "meaning": "lợi nhuận trên đầu tư", "example": "Calculate the ROI of your social media campaigns to prove their value."},
            {"word": "social proof", "ipa": "/ˈsəʊ.ʃəl pruːf/", "meaning": "bằng chứng xã hội", "example": "Customer reviews and follower counts act as social proof for brands."},
            {"word": "FOMO (fear of missing out)", "ipa": "/ˈfəʊ.məʊ/", "meaning": "tâm lý sợ bị bỏ lỡ", "example": "Social media amplifies FOMO among users who compare their lives to others."},
            {"word": "doomscrolling", "ipa": "/ˈduːm.skrəʊ.lɪŋ/", "meaning": "cuộn mạng liên tục xem tin xấu", "example": "Doomscrolling through bad news can worsen anxiety and mental health."},
            {"word": "digital wellness", "ipa": "/ˈdɪdʒ.ɪ.təl ˈwel.nəs/", "meaning": "sức khỏe số", "example": "Digital wellness involves managing screen time and online habits mindfully."},
            {"word": "screen time", "ipa": "/skriːn taɪm/", "meaning": "thời gian sử dụng màn hình", "example": "She reduced her daily screen time to improve her sleep quality."},
            {"word": "social media detox", "ipa": "/ˈsəʊ.ʃəl ˈmiː.di.ə ˈdiː.tɒks/", "meaning": "cai nghiện mạng xã hội tạm thời", "example": "She went on a two-week social media detox and felt much calmer."},
            {"word": "attention economy", "ipa": "/əˈten.ʃən ɪˈkɒn.ə.mi/", "meaning": "nền kinh tế thu hút sự chú ý", "example": "The attention economy treats human attention as a scarce commodity."},
            {"word": "echo chamber", "ipa": "/ˈek.əʊ ˌtʃeɪm.bər/", "meaning": "buồng vọng (bong bóng thông tin)", "example": "Social media algorithms create echo chambers that reinforce existing beliefs."},
            {"word": "filter bubble", "ipa": "/ˈfɪl.tər ˌbʌb.əl/", "meaning": "bong bóng lọc thông tin", "example": "A filter bubble limits your exposure to diverse viewpoints online."},
            {"word": "viral marketing", "ipa": "/ˈvaɪ.rəl ˈmɑː.kɪ.tɪŋ/", "meaning": "tiếp thị lan truyền", "example": "Viral marketing encourages users to share content organically."},
            {"word": "guerrilla marketing", "ipa": "/ɡəˈrɪl.ə ˈmɑː.kɪ.tɪŋ/", "meaning": "tiếp thị du kích", "example": "The ice bucket challenge was a guerrilla marketing success."},
            {"word": "social commerce", "ipa": "/ˈsəʊ.ʃəl ˈkɒm.ɜːs/", "meaning": "mua sắm qua mạng xã hội", "example": "TikTok Shop is a leading example of social commerce."},
            {"word": "shoppable content", "ipa": "/ˈʃɒp.ə.bəl ˈkɒn.tent/", "meaning": "nội dung có thể mua hàng trực tiếp", "example": "Instagram's shoppable posts let users buy products directly from the app."},
            {"word": "influencer marketing", "ipa": "/ˈɪn.fluː.ən.sər ˈmɑː.kɪ.tɪŋ/", "meaning": "tiếp thị người ảnh hưởng", "example": "Influencer marketing can be more effective than traditional advertising."},
            {"word": "affiliate marketing", "ipa": "/əˈfɪl.i.ɪt ˈmɑː.kɪ.tɪŋ/", "meaning": "tiếp thị liên kết", "example": "She earns commission through affiliate marketing links in her videos."},
            {"word": "monetization", "ipa": "/ˌmɒn.ɪ.taɪˈzeɪ.ʃən/", "meaning": "kiếm tiền từ nội dung", "example": "YouTube offers several monetization options for creators."},
            {"word": "creator economy", "ipa": "/kriˈeɪ.tər ɪˈkɒn.ə.mi/", "meaning": "nền kinh tế người sáng tạo", "example": "The creator economy has empowered millions to earn income from content."},
            {"word": "brand deal", "ipa": "/brænd diːl/", "meaning": "thỏa thuận hợp tác thương hiệu", "example": "She negotiated a brand deal worth $10,000 for a single post."},
            {"word": "content moderation", "ipa": "/ˈkɒn.tent ˌmɒd.əˈreɪ.ʃən/", "meaning": "kiểm duyệt nội dung", "example": "Content moderation removes harmful posts from social platforms."},
            {"word": "algorithm update", "ipa": "/ˈæl.ɡə.rɪð.əm ˈʌp.deɪt/", "meaning": "cập nhật thuật toán", "example": "Every algorithm update affects creators' reach and strategy."},
            {"word": "platform dependency", "ipa": "/ˈplæt.fɔːm dɪˈpen.dən.si/", "meaning": "sự phụ thuộc vào nền tảng", "example": "Platform dependency is risky — one algorithm change can destroy a business."},
            {"word": "multi-platform strategy", "ipa": "/ˈmʌl.ti ˈplæt.fɔːm ˈstræt.ɪ.dʒi/", "meaning": "chiến lược đa nền tảng", "example": "A multi-platform strategy reduces dependence on any single social network."},
            {"word": "content pillars", "ipa": "/ˈkɒn.tent ˈpɪl.ərz/", "meaning": "chủ đề cốt lõi của nội dung", "example": "Her content pillars are travel, food, and sustainable living."},
            {"word": "evergreen content", "ipa": "/ˈev.ə.ɡriːn ˈkɒn.tent/", "meaning": "nội dung không lỗi thời", "example": "Evergreen content stays relevant and drives traffic long after posting."},
            {"word": "trending topic", "ipa": "/ˈtren.dɪŋ ˈtɒp.ɪk/", "meaning": "chủ đề đang hot", "example": "She creates content around trending topics to boost discoverability."},
            {"word": "SEO (social)", "ipa": "/ˈsioʊ (ˈsoʊʃəl)/", "meaning": "tối ưu hóa tìm kiếm trên mạng xã hội", "example": "Social SEO uses keywords in captions and hashtags to improve visibility."},
            {"word": "keyword optimization", "ipa": "/ˈkiː.wɜːd ˌɒp.tɪ.maɪˈzeɪ.ʃən/", "meaning": "tối ưu hóa từ khóa", "example": "Keyword optimization helps your content appear in more searches."},
            {"word": "collaboration post", "ipa": "/kəˌlæb.əˈreɪ.ʃən pəʊst/", "meaning": "bài đăng hợp tác", "example": "They created a collaboration post to grow both of their audiences."},
            {"word": "pinned post", "ipa": "/pɪnd pəʊst/", "meaning": "bài viết được ghim", "example": "She pinned her most important post to the top of her profile."},
            {"word": "social advertising", "ipa": "/ˈsəʊ.ʃəl ˈmiː.di.ə ˈmɑː.kɪ.tɪŋ/", "meaning": "tiếp thị qua mạng xã hội", "example": "Social media marketing is now essential for every brand."},
        ],
        "B2": [
            {"word": "social media governance", "ipa": "/ˈsəʊ.ʃəl ˈmiː.di.ə ˈɡʌv.ən.əns/", "meaning": "quản trị mạng xã hội", "example": "Social media governance sets policies for content, security, and compliance."},
            {"word": "platform regulation", "ipa": "/ˈplæt.fɔːm ˌreɡ.jʊˈleɪ.ʃən/", "meaning": "quy định pháp lý về nền tảng", "example": "Platform regulation is increasingly debated as social media's influence grows."},
            {"word": "Digital Services Act", "ipa": "/ˈdɪdʒ.ɪ.təl ˈsɜː.vɪsɪz ækt/", "meaning": "Đạo luật Dịch vụ Số EU", "example": "The EU's Digital Services Act imposes new obligations on large platforms."},
            {"word": "algorithmic accountability", "ipa": "/ˌæl.ɡəˈrɪð.mɪk əˌkaʊn.tɪˈbɪl.ɪ.ti/", "meaning": "trách nhiệm thuật toán", "example": "Algorithmic accountability requires platforms to explain how their systems work."},
            {"word": "algorithmic bias", "ipa": "/ˌæl.ɡəˈrɪð.mɪk ˈbaɪ.əs/", "meaning": "sai lệch thuật toán", "example": "Algorithmic bias can amplify discrimination in content recommendations."},
            {"word": "surveillance capitalism", "ipa": "/səˈveɪ.ləns ˈkæp.ɪ.tə.lɪ.zəm/", "meaning": "chủ nghĩa tư bản giám sát", "example": "Zuboff's concept of surveillance capitalism describes how platforms monetize user data."},
            {"word": "data harvesting", "ipa": "/ˈdeɪ.tə ˌhɑː.vɪs.tɪŋ/", "meaning": "thu thập dữ liệu người dùng", "example": "Data harvesting by social platforms raised serious privacy concerns."},
            {"word": "GDPR compliance", "ipa": "/ˌdʒiː.diːˌpiːˈɑːr kəmˈplaɪ.əns/", "meaning": "tuân thủ GDPR (bảo vệ dữ liệu EU)", "example": "Social media companies must ensure GDPR compliance in the European Union."},
            {"word": "terms of service", "ipa": "/tɜːmz əv ˈsɜː.vɪs/", "meaning": "điều khoản dịch vụ", "example": "Read the terms of service before agreeing to share your data."},
            {"word": "content takedown", "ipa": "/ˈkɒn.tent ˌteɪk.daʊn/", "meaning": "gỡ bỏ nội dung vi phạm", "example": "The platform issued a content takedown notice for the copyright violation."},
            {"word": "shadow banning", "ipa": "/ˈʃæd.əʊ ˌbæn.ɪŋ/", "meaning": "cấm ngầm (giảm hiển thị)", "example": "Shadow banning reduces a user's visibility without their knowledge."},
            {"word": "deplatforming", "ipa": "/ˌdiːˈplæt.fɔːm.ɪŋ/", "meaning": "xóa tài khoản/kênh", "example": "Deplatforming removes users who violate community guidelines."},
            {"word": "cancel culture", "ipa": "/ˈkæn.səl ˌkʌl.tʃər/", "meaning": "văn hóa tẩy chay", "example": "Cancel culture holds public figures accountable for their past actions."},
            {"word": "call-out culture", "ipa": "/ˈkɔːl.aʊt ˌkʌl.tʃər/", "meaning": "văn hóa chỉ trích công khai", "example": "Call-out culture publicly shames individuals for perceived wrongdoing."},
            {"word": "outrage economy", "ipa": "/ˈaʊt.reɪdʒ ɪˈkɒn.ə.mi/", "meaning": "nền kinh tế tức giận", "example": "The outrage economy rewards content that provokes strong emotional reactions."},
            {"word": "engagement farming", "ipa": "/ɪnˈɡeɪdʒ.mənt ˈfɑː.mɪŋ/", "meaning": "câu tương tác giả tạo", "example": "Engagement farming uses controversial content to bait reactions."},
            {"word": "dark patterns (UX)", "ipa": "/dɑːk ˈpæt.ənz/", "meaning": "mô hình giao diện thao túng người dùng", "example": "Dark patterns trick users into spending more time on apps than intended."},
            {"word": "infinite scroll", "ipa": "/ˈɪn.fɪ.nɪt skrəʊl/", "meaning": "cuộn vô hạn (thiết kế gây nghiện)", "example": "Infinite scroll is a design feature that encourages endless browsing."},
            {"word": "variable reward schedule", "ipa": "/ˈveər.i.ə.bəl rɪˈwɔːd ˈʃed.juːl/", "meaning": "lịch thưởng biến đổi (tâm lý học nghiện)", "example": "Social media uses variable reward schedules to create addictive checking behavior."},
            {"word": "social media addiction", "ipa": "/ˈsəʊ.ʃəl ˈmiː.di.ə əˈdɪk.ʃən/", "meaning": "nghiện mạng xã hội", "example": "Social media addiction is recognized as a growing mental health concern."},
            {"word": "technoference", "ipa": "/ˈtek.nɒf.ər.əns/", "meaning": "thiết bị công nghệ gây xáo trộn quan hệ", "example": "Technoference occurs when phone use interferes with face-to-face interactions."},
            {"word": "parasocial relationship", "ipa": "/ˌpær.ə.ˈsəʊ.ʃəl rɪˈleɪ.ʃən.ʃɪp/", "meaning": "quan hệ ảo (người hâm mộ-người nổi tiếng)", "example": "Many followers develop parasocial relationships with their favorite influencers."},
            {"word": "influencer fatigue", "ipa": "/ˈɪn.fluː.ən.sər fəˈtiːɡ/", "meaning": "mệt mỏi với quảng cáo influencer", "example": "Influencer fatigue is causing audiences to trust sponsored content less."},
            {"word": "authenticity (social media)", "ipa": "/ˌɔθənˈtɪsɪti (ˈsoʊʃəl ˈmidiə)/", "meaning": "tính xác thực trong nội dung", "example": "Audiences increasingly value authenticity over polished, curated content."},
            {"word": "deinfluencing", "ipa": "/ˌdiːˈɪn.fluː.ən.sɪŋ/", "meaning": "xu hướng không khuyến khích mua sắm", "example": "Deinfluencing is a trend where creators tell followers NOT to buy certain products."},
            {"word": "attention fragmentation", "ipa": "/əˈten.ʃən ˌfræɡ.menˈteɪ.ʃən/", "meaning": "sự phân tán chú ý", "example": "Constant notifications cause attention fragmentation and reduce productivity."},
            {"word": "platform power dynamics", "ipa": "/ˈplæt.fɔːm ˈpaʊər daɪˈnæm.ɪks/", "meaning": "động lực quyền lực nền tảng", "example": "Platform power dynamics determine which voices are amplified or suppressed."},
            {"word": "network effects", "ipa": "/ˈnet.wɜːk ɪˈfekts/", "meaning": "hiệu ứng mạng lưới", "example": "Network effects make platforms more valuable as more people join."},
            {"word": "Metcalfe's Law", "ipa": "/ˈmet.kɑːfz lɔː/", "meaning": "Luật Metcalfe (giá trị mạng lưới)", "example": "Metcalfe's Law states a network's value grows proportionally to the square of its users."},
            {"word": "platform economy", "ipa": "/ˈplæt.fɔːm ɪˈkɒn.ə.mi/", "meaning": "kinh tế nền tảng", "example": "The platform economy has created new forms of value creation and competition."},
            {"word": "digital public sphere", "ipa": "/ˈdɪdʒ.ɪ.təl ˈpʌb.lɪk sfɪər/", "meaning": "không gian công cộng số", "example": "Social media has become the primary digital public sphere for political debate."},
            {"word": "information disorder", "ipa": "/ˌɪn.fəˈmeɪ.ʃən dɪsˈɔː.dər/", "meaning": "rối loạn thông tin", "example": "Wardle distinguishes between misinformation, disinformation, and malinformation as forms of information disorder."},
            {"word": "disinformation campaign", "ipa": "/ˌdɪs.ɪn.fəˈmeɪ.ʃən kæmˈpeɪn/", "meaning": "chiến dịch thông tin sai lệch cố ý", "example": "Foreign actors used a disinformation campaign to influence the election."},
            {"word": "astroturfing", "ipa": "/ˈæs.trəʊ.tɜː.fɪŋ/", "meaning": "tạo phong trào giả (astroturfing)", "example": "Astroturfing creates the illusion of grassroots support using fake accounts."},
            {"word": "bot network", "ipa": "/bɒt ˈnet.wɜːk/", "meaning": "mạng lưới tài khoản bot", "example": "A bot network was used to artificially inflate a hashtag's popularity."},
            {"word": "deepfake", "ipa": "/ˈdiːp.feɪk/", "meaning": "video giả mạo bằng AI", "example": "Deepfake technology creates convincing but fabricated videos of real people."},
            {"word": "synthetic media", "ipa": "/sɪnˈθet.ɪk ˈmiː.di.ə/", "meaning": "phương tiện truyền thông tổng hợp (AI)", "example": "The rise of synthetic media challenges our ability to trust online content."},
            {"word": "content moderation at scale", "ipa": "/ˈkɒn.tent ˌmɒd.əˈreɪ.ʃən ət skeɪl/", "meaning": "kiểm duyệt nội dung quy mô lớn", "example": "Content moderation at scale relies on both AI tools and human reviewers."},
            {"word": "trust and safety", "ipa": "/trʌst ənd ˈseɪf.ti/", "meaning": "tin tưởng và an toàn (chính sách nền tảng)", "example": "The trust and safety team enforces community standards on the platform."},
            {"word": "digital rights", "ipa": "/ˈdɪdʒ.ɪ.təl raɪts/", "meaning": "quyền kỹ thuật số", "example": "Digital rights advocates push for freedom of expression online."},
            {"word": "right to erasure", "ipa": "/raɪt tə ɪˈreɪ.ʒər/", "meaning": "quyền xóa dữ liệu cá nhân", "example": "Under GDPR, users have the right to erasure of their personal data."},
            {"word": "social capital (digital)", "ipa": "/ˈsəʊ.ʃəl ˈkæp.ɪ.təl/", "meaning": "vốn xã hội kỹ thuật số", "example": "A large follower count represents digital social capital."},
            {"word": "virality coefficient", "ipa": "/vaɪˈræl.ɪ.ti ˌkəʊ.ɪˈfɪʃ.ənt/", "meaning": "hệ số lan truyền", "example": "A virality coefficient above 1 means the content grows exponentially."},
            {"word": "earned media", "ipa": "/ɜːnd ˈmiː.di.ə/", "meaning": "phương tiện truyền thông kiếm được (PR tự nhiên)", "example": "Positive press coverage and viral posts are examples of earned media."},
            {"word": "owned media", "ipa": "/əʊnd ˈmiː.di.ə/", "meaning": "phương tiện truyền thông sở hữu (kênh của mình)", "example": "Your website and email list are owned media that you fully control."},
            {"word": "dark social", "ipa": "/dɑːk ˈsəʊ.ʃəl/", "meaning": "chia sẻ qua kênh riêng tư không theo dõi được", "example": "Dark social refers to private sharing via messaging apps that analytics can't track."},
            {"word": "social graph", "ipa": "/ˈsəʊ.ʃəl ɡrɑːf/", "meaning": "đồ thị quan hệ xã hội", "example": "Facebook's social graph maps the connections between all its users."},
            {"word": "interest graph", "ipa": "/ˈɪn.trəst ɡrɑːf/", "meaning": "đồ thị sở thích người dùng", "example": "TikTok's interest graph connects users with content they are likely to enjoy."},
            {"word": "knowledge graph", "ipa": "/ˈnɒl.ɪdʒ ɡrɑːf/", "meaning": "đồ thị tri thức", "example": "Google's knowledge graph connects entities and their relationships."},
            {"word": "social media audit", "ipa": "/ˈsəʊ.ʃəl ˈmiː.di.ə ˈɔː.dɪt/", "meaning": "kiểm tra tổng thể hoạt động mạng xã hội", "example": "A social media audit reviews all your channels, content, and performance metrics."},
        ],
        "C1": [
            {"word": "networked individualism", "ipa": "/ˈnet.wɜːkt ˌɪn.dɪˈvɪdʒ.u.ə.lɪ.zəm/", "meaning": "chủ nghĩa cá nhân mạng lưới", "example": "Wellman's concept of networked individualism describes how people build personal networks rather than group communities."},
            {"word": "digital dualism", "ipa": "/ˈdɪdʒ.ɪ.təl ˈdjuː.ə.lɪ.zəm/", "meaning": "nhị nguyên số (tách biệt online/offline)", "example": "Jurgenson critiques digital dualism, arguing that online and offline lives are augmented realities."},
            {"word": "augmented reality of everyday life", "ipa": "/ɔːɡˈmen.tɪd riˈæl.ɪ.ti əv ˈev.ri.deɪ laɪf/", "meaning": "thực tại hỗ trợ của cuộc sống hàng ngày", "example": "Social media creates an augmented reality of everyday life that merges digital and physical experience."},
            {"word": "context collapse", "ipa": "/ˈkɒn.tekst kəˈlæps/", "meaning": "sụp đổ bối cảnh (nhiều khán giả khác nhau cùng xem)", "example": "Context collapse occurs when a post reaches multiple audiences with different expectations."},
            {"word": "social media epistemology", "ipa": "/ˈsəʊ.ʃəl ˈmiː.di.ə ɪˌpɪs.tɪˈmɒl.ə.dʒi/", "meaning": "nhận thức luận mạng xã hội", "example": "Social media epistemology examines how online platforms shape what we believe to be true."},
            {"word": "information ecology", "ipa": "/ˌɪn.fəˈmeɪ.ʃən ɪˈkɒl.ə.dʒi/", "meaning": "sinh thái thông tin", "example": "A healthy information ecology supports diverse, accurate, and accessible information."},
            {"word": "attention market", "ipa": "/əˈten.ʃən ˈmɑː.kɪt/", "meaning": "thị trường chú ý", "example": "Platforms compete in an attention market where human focus is the currency."},
            {"word": "platform capitalism", "ipa": "/ˈplæt.fɔːm ˈkæp.ɪ.tə.lɪ.zəm/", "meaning": "chủ nghĩa tư bản nền tảng", "example": "Platform capitalism extracts value from user data and network interactions."},
            {"word": "digital colonialism", "ipa": "/ˈdɪdʒ.ɪ.təl kəˈləʊ.ni.ə.lɪ.zəm/", "meaning": "chủ nghĩa thực dân số", "example": "Digital colonialism describes the dominance of Western tech companies over global data flows."},
            {"word": "techno-determinism", "ipa": "/ˈtek.nəʊ dɪˈtɜː.mɪ.nɪ.zəm/", "meaning": "thuyết quyết định công nghệ", "example": "Techno-determinism argues that technology independently drives social change."},
            {"word": "social constructivism (media)", "ipa": "/ˈsəʊ.ʃəl kənˈstrʌk.tɪ.vɪ.zəm/", "meaning": "chủ nghĩa kiến tạo xã hội (truyền thông)", "example": "Social constructivism argues that technology's effects are shaped by social contexts and choices."},
            {"word": "participatory culture", "ipa": "/pɑːˌtɪs.ɪ.pə.tər.i ˈkʌl.tʃər/", "meaning": "văn hóa tham gia", "example": "Jenkins' concept of participatory culture describes how media audiences become active producers."},
            {"word": "produsage", "ipa": "/ˈprɒd.juː.sɪdʒ/", "meaning": "sản xuất-sử dụng (người dùng vừa tạo vừa tiêu thụ nội dung)", "example": "Bruns coined produsage to describe collaborative online content creation."},
            {"word": "transmedia storytelling", "ipa": "/ˌtræns.ˈmiː.di.ə ˈstɔː.ri.tel.ɪŋ/", "meaning": "kể chuyện xuyên nền tảng", "example": "Transmedia storytelling unfolds a narrative across multiple platforms and formats."},
            {"word": "digital labor", "ipa": "/ˈdɪdʒ.ɪ.təl ˈleɪ.bər/", "meaning": "lao động kỹ thuật số (người dùng tạo giá trị miễn phí)", "example": "Digital labor theory argues that users' online activity creates value for platforms without compensation."},
            {"word": "immaterial labor", "ipa": "/ɪˈmæ.tɪər.i.əl ˈleɪ.bər/", "meaning": "lao động phi vật chất (sáng tạo, cảm xúc)", "example": "Lazzarato's immaterial labor describes cognitive and affective work in the digital economy."},
            {"word": "affective computing", "ipa": "/əˈfek.tɪv kəmˈpjuː.tɪŋ/", "meaning": "điện toán cảm xúc", "example": "Affective computing develops systems that recognize and respond to human emotions."},
            {"word": "sentiment engineering", "ipa": "/ˈsen.tɪ.mənt ˌen.dʒɪˈnɪər.ɪŋ/", "meaning": "kỹ thuật điều khiển cảm xúc người dùng", "example": "Platforms use sentiment engineering to maximize emotional engagement."},
            {"word": "persuasive technology", "ipa": "/pəˈsweɪ.sɪv tekˈnɒl.ə.dʒi/", "meaning": "công nghệ thuyết phục", "example": "Fogg's concept of persuasive technology describes systems designed to change behavior."},
            {"word": "dark nudge", "ipa": "/dɑːk nʌdʒ/", "meaning": "gợi ý tối (thiết kế thao túng)", "example": "A dark nudge exploits cognitive biases to push users toward choices benefiting the platform."},
            {"word": "choice architecture (digital)", "ipa": "/ʧɔɪs ˈɑrkəˌtɛkʧər (ˈdɪʤɪtəl)/", "meaning": "kiến trúc lựa chọn (thiết kế ảnh hưởng quyết định)", "example": "Choice architecture shapes how options are presented to influence user decisions."},
            {"word": "algorithmic curation", "ipa": "/ˌæl.ɡəˈrɪð.mɪk kjʊˈreɪ.ʃən/", "meaning": "tuyển chọn nội dung bằng thuật toán", "example": "Algorithmic curation determines what each user sees in their personal feed."},
            {"word": "recommendation system", "ipa": "/ˌrek.əmenˈdeɪ.ʃən ˈsɪs.təm/", "meaning": "hệ thống gợi ý nội dung", "example": "TikTok's recommendation system is widely considered the most powerful in social media."},
            {"word": "collaborative filtering", "ipa": "/kəˈlæb.ər.ə.tɪv ˈfɪl.tər.ɪŋ/", "meaning": "lọc cộng tác (gợi ý dựa trên người dùng tương tự)", "example": "Collaborative filtering recommends content based on similar users' preferences."},
            {"word": "content-based filtering", "ipa": "/ˈkɒn.tent beɪst ˈfɪl.tər.ɪŋ/", "meaning": "lọc dựa trên nội dung", "example": "Content-based filtering recommends items similar to what a user has previously liked."},
            {"word": "graph neural network (social)", "ipa": "/græf ˈnʊrəl ˈnɛtˌwərk (ˈsoʊʃəl)/", "meaning": "mạng nơ-ron đồ thị (mạng xã hội)", "example": "Graph neural networks model relationships within social networks for recommendations."},
            {"word": "digital identity", "ipa": "/ˈdɪdʒ.ɪ.təl aɪˈden.tɪ.ti/", "meaning": "danh tính kỹ thuật số", "example": "Managing your digital identity involves curating your online presence carefully."},
            {"word": "self-presentation theory", "ipa": "/self ˌprez.ənˈteɪ.ʃən ˈθɪər.i/", "meaning": "lý thuyết tự trình bày bản thân", "example": "Goffman's self-presentation theory explains how people manage impressions online."},
            {"word": "narrative identity (digital)", "ipa": "/ˈnær.ə.tɪv aɪˈden.tɪ.ti/", "meaning": "danh tính tự sự kỹ thuật số", "example": "People construct their narrative identity through curated social media posts."},
            {"word": "digital redlining", "ipa": "/ˈdɪdʒ.ɪ.təl ˈred.laɪn.ɪŋ/", "meaning": "phân biệt đối xử kỹ thuật số", "example": "Digital redlining provides unequal access to digital services based on race or class."},
            {"word": "algorithmic injustice", "ipa": "/ˌæl.ɡəˈrɪð.mɪk ɪnˈdʒʌs.tɪs/", "meaning": "bất công thuật toán", "example": "Algorithmic injustice occurs when automated systems systematically disadvantage certain groups."},
            {"word": "critical algorithm studies", "ipa": "/ˈkrɪt.ɪ.kəl ˈæl.ɡə.rɪð.əm ˈstʌd.iz/", "meaning": "nghiên cứu phê bình thuật toán", "example": "Critical algorithm studies investigates the social and political effects of algorithms."},
            {"word": "post-truth era", "ipa": "/ˌpəʊstˈtruːθ ˈɪər.ə/", "meaning": "thời đại hậu sự thật", "example": "In the post-truth era, emotions and beliefs often override objective facts in public discourse."},
            {"word": "infodemic", "ipa": "/ˌɪn.fəʊˈdem.ɪk/", "meaning": "đại dịch thông tin sai lệch", "example": "The WHO declared an infodemic alongside the COVID-19 pandemic."},
            {"word": "prebunking", "ipa": "/ˈpriː.bʌŋ.kɪŋ/", "meaning": "tiêm chủng nhận thức chống thông tin giả", "example": "Prebunking inoculates people against misinformation before they encounter it."},
            {"word": "inoculation theory (media)", "ipa": "/ɪˌnɒk.jʊˈleɪ.ʃən ˈθɪər.i/", "meaning": "lý thuyết tiêm chủng nhận thức", "example": "Inoculation theory suggests exposing people to weakened misinformation strengthens resistance."},
            {"word": "media literacy", "ipa": "/ˈmiː.di.ə ˈlɪt.ər.ə.si/", "meaning": "hiểu biết truyền thông số", "example": "Media literacy education helps people critically evaluate online content."},
            {"word": "digital citizenship", "ipa": "/ˈdɪdʒ.ɪ.təl ˈsɪt.ɪ.zən.ʃɪp/", "meaning": "công dân số", "example": "Digital citizenship involves responsible, ethical, and informed online behavior."},
            {"word": "platform studies", "ipa": "/ˈplæt.fɔːm ˈstʌd.iz/", "meaning": "nghiên cứu nền tảng", "example": "Platform studies examines how technical architectures shape cultural production."},
            {"word": "software studies", "ipa": "/ˈsɒft.weər ˈstʌd.iz/", "meaning": "nghiên cứu phần mềm", "example": "Software studies investigates code as a cultural and political artifact."},
            {"word": "computational propaganda", "ipa": "/ˌkɒm.pjʊˈteɪ.ʃən.əl ˈprɒp.ə.ɡæn.də/", "meaning": "tuyên truyền tính toán", "example": "Computational propaganda uses bots and algorithms to amplify political messages."},
            {"word": "sociotechnical system", "ipa": "/ˌsəʊ.si.əʊˈtek.nɪ.kəl ˈsɪs.təm/", "meaning": "hệ thống kỹ thuật-xã hội", "example": "Social media is a sociotechnical system where technology and social norms co-evolve."},
            {"word": "actor-network theory", "ipa": "/ˈæk.tər ˈnet.wɜːk ˈθɪər.i/", "meaning": "lý thuyết mạng diễn viên (ANT)", "example": "Actor-network theory treats both humans and technology as actants in social networks."},
            {"word": "digital phenomenology", "ipa": "/ˈdɪdʒ.ɪ.təl fɪˌnɒm.ɪˈnɒl.ə.dʒi/", "meaning": "hiện tượng học kỹ thuật số", "example": "Digital phenomenology examines the lived experience of being online."},
            {"word": "virtual community theory", "ipa": "/ˈvɜː.tʃu.əl kəˈmjuː.nɪ.ti ˈθɪər.i/", "meaning": "lý thuyết cộng đồng ảo", "example": "Rheingold's virtual community theory describes online groups as real social formations."},
            {"word": "networked publics", "ipa": "/ˈnet.wɜːkt ˈpʌb.lɪks/", "meaning": "công chúng mạng lưới", "example": "Boyd describes networked publics as spaces structured by persistence, searchability, and spreadability."},
            {"word": "spreadability (media)", "ipa": "/ˌspred.əˈbɪl.ɪ.ti/", "meaning": "khả năng lan truyền (Jenkins)", "example": "Jenkins argues spreadability replaces stickiness as the key metric of media success."},
            {"word": "connective action", "ipa": "/kəˈnek.tɪv ˈæk.ʃən/", "meaning": "hành động kết nối (phong trào xã hội số)", "example": "Bennett and Segerberg describe connective action as digitally enabled personalized political participation."},
            {"word": "hashtag activism", "ipa": "/ˈhæʃ.tæɡ ˈæk.tɪ.vɪ.zəm/", "meaning": "chủ nghĩa hành động qua hashtag", "example": "#MeToo and #BlackLivesMatter are powerful examples of hashtag activism."},
            {"word": "slacktivism", "ipa": "/ˈslæk.tɪ.vɪ.zəm/", "meaning": "chủ nghĩa tích cực hời hợt (like/share thay vì hành động)", "example": "Slacktivism describes low-effort online activities that substitute for real political engagement."},
        ],
    },
    "software": {
        "A1": [
            {"word": "computer", "ipa": "/kəmˈpjuː.tər/", "meaning": "máy tính", "example": "She uses a computer at work every day."},
            {"word": "phone", "ipa": "/fəʊn/", "meaning": "điện thoại", "example": "He downloaded the app on his phone."},
            {"word": "app", "ipa": "/æp/", "meaning": "ứng dụng", "example": "There is an app for almost everything nowadays."},
            {"word": "internet", "ipa": "/ˈɪn.tə.net/", "meaning": "mạng internet", "example": "She uses the internet to look up information."},
            {"word": "click", "ipa": "/klɪk/", "meaning": "bấm (chuột)", "example": "Click the button to start the program."},
            {"word": "open", "ipa": "/ˈəʊ.pən/", "meaning": "mở (file/chương trình)", "example": "Open the file by double-clicking on it."},
            {"word": "close", "ipa": "/kləʊz/", "meaning": "đóng (chương trình)", "example": "Close the program when you are done."},
            {"word": "save", "ipa": "/seɪv/", "meaning": "lưu (file)", "example": "Remember to save your work before closing the file."},
            {"word": "download", "ipa": "/ˌdaʊnˈləʊd/", "meaning": "tải xuống", "example": "Download the app from the official website."},
            {"word": "install", "ipa": "/ɪnˈstɔːl/", "meaning": "cài đặt", "example": "Install the software on your computer before using it."},
            {"word": "search", "ipa": "/sərʧ/", "meaning": "tìm kiếm", "example": "Search for the answer online using a search engine."},
            {"word": "password", "ipa": "/ˈpɑːs.wɜːd/", "meaning": "mật khẩu", "example": "Use a strong password to protect your account."},
            {"word": "screen", "ipa": "/skriːn/", "meaning": "màn hình", "example": "The laptop screen is too bright."},
            {"word": "keyboard", "ipa": "/ˈkiː.bɔːd/", "meaning": "bàn phím", "example": "She types very fast on her keyboard."},
            {"word": "mouse", "ipa": "/maʊs/", "meaning": "chuột máy tính", "example": "Move the mouse to control the cursor on screen."},
            {"word": "button", "ipa": "/ˈbʌt.ən/", "meaning": "nút bấm (giao diện)", "example": "Press the 'Submit' button to send the form."},
            {"word": "menu", "ipa": "/ˈmen.juː/", "meaning": "menu (giao diện)", "example": "Click on the menu to see all available options."},
            {"word": "folder", "ipa": "/ˈfəʊl.dər/", "meaning": "thư mục", "example": "Create a new folder to organize your files."},
            {"word": "file", "ipa": "/faɪl/", "meaning": "tập tin", "example": "Open the file and make the changes you need."},
            {"word": "email", "ipa": "/ˈiː.meɪl/", "meaning": "thư điện tử", "example": "She sent an email to her teacher asking a question."},
            {"word": "website", "ipa": "/ˈweb.saɪt/", "meaning": "trang web", "example": "Visit our website to learn more about our products."},
            {"word": "login", "ipa": "/ˈlɒɡ.ɪn/", "meaning": "đăng nhập", "example": "You need to login with your username and password."},
            {"word": "logout", "ipa": "/ˈlɒɡ.aʊt/", "meaning": "đăng xuất", "example": "Always logout when you finish using a shared computer."},
            {"word": "update", "ipa": "/ˈʌp.deɪt/", "meaning": "cập nhật", "example": "Update the app to get the latest features."},
            {"word": "delete", "ipa": "/dɪˈliːt/", "meaning": "xóa", "example": "Delete the files you no longer need to free up space."},
            {"word": "copy", "ipa": "/ˈkɒp.i/", "meaning": "sao chép", "example": "Copy the text and paste it into the new document."},
            {"word": "paste", "ipa": "/peɪst/", "meaning": "dán (nội dung)", "example": "Paste the image into the presentation."},
            {"word": "print", "ipa": "/prɪnt/", "meaning": "in ấn", "example": "Print the document and bring it to class."},
            {"word": "type", "ipa": "/taɪp/", "meaning": "gõ (văn bản)", "example": "Type your name in the text box."},
            {"word": "notification", "ipa": "/ˌnəʊ.tɪ.fɪˈkeɪ.ʃən/", "meaning": "thông báo", "example": "She turned off all app notifications to focus on work."},
            {"word": "battery", "ipa": "/ˈbæt.ər.i/", "meaning": "pin (thiết bị)", "example": "The phone battery is low — please charge it."},
            {"word": "charge", "ipa": "/ʧɑrʤ/", "meaning": "sạc (pin)", "example": "Charge your phone overnight so it's ready in the morning."},
            {"word": "WiFi", "ipa": "/ˈwiˌfi/", "meaning": "WiFi (mạng không dây)", "example": "Connect to the WiFi network to use the internet."},
            {"word": "signal", "ipa": "/ˈsɪɡ.nəl/", "meaning": "tín hiệu mạng", "example": "The internet signal is weak in this area."},
            {"word": "camera", "ipa": "/ˈkæm.ər.ə/", "meaning": "camera (thiết bị)", "example": "Open the camera app to take a photo."},
            {"word": "photo", "ipa": "/ˈfəʊ.təʊ/", "meaning": "ảnh chụp", "example": "She shared a photo with her friends online."},
            {"word": "video", "ipa": "/ˈvɪd.i.əʊ/", "meaning": "video", "example": "He watched a video tutorial on how to use the software."},
            {"word": "share", "ipa": "/ʃeər/", "meaning": "chia sẻ (nội dung)", "example": "Share the document with your classmates."},
            {"word": "link", "ipa": "/lɪŋk/", "meaning": "Liên kết, đường dẫn", "example": "Click the link to visit the website."},
            {"word": "upload", "ipa": "/ˌʌpˈləʊd/", "meaning": "tải lên", "example": "Upload your assignment to the school website."},
            {"word": "error", "ipa": "/ˈer.ər/", "meaning": "lỗi (phần mềm)", "example": "An error message appeared on the screen."},
            {"word": "crash", "ipa": "/kræʃ/", "meaning": "treo/sập chương trình", "example": "The app crashed and I lost all my work."},
            {"word": "restart", "ipa": "/ˌriːˈstɑːt/", "meaning": "khởi động lại", "example": "Restart the computer to apply the updates."},
            {"word": "settings", "ipa": "/ˈset.ɪŋz/", "meaning": "cài đặt (giao diện)", "example": "Go to settings to change your profile picture."},
            {"word": "profile", "ipa": "/ˈprəʊ.faɪl/", "meaning": "hồ sơ tài khoản", "example": "Update your profile with your latest information."},
            {"word": "account", "ipa": "/əˈkaʊnt/", "meaning": "tài khoản người dùng", "example": "Create an account to access all features."},
            {"word": "storage", "ipa": "/ˈstɔː.rɪdʒ/", "meaning": "bộ nhớ lưu trữ", "example": "The phone only has 2GB of storage left."},
            {"word": "memory", "ipa": "/ˈmem.ər.i/", "meaning": "RAM; bộ nhớ", "example": "The computer runs slowly because it needs more memory."},
            {"word": "software", "ipa": "/ˈsɒft.weər/", "meaning": "phần mềm", "example": "Install the latest version of the software."},
            {"word": "hardware", "ipa": "/ˈhɑːd.weər/", "meaning": "phần cứng", "example": "The computer needs new hardware to run the game."},
        ],
        "A2": [
            {"word": "program", "ipa": "/ˈprəʊ.ɡræm/", "meaning": "chương trình phần mềm", "example": "She downloaded a program to edit her photos."},
            {"word": "database", "ipa": "/ˈdeɪ.tə.beɪs/", "meaning": "cơ sở dữ liệu", "example": "The company stores all customer data in a secure database."},
            {"word": "network", "ipa": "/ˈnet.wɜːk/", "meaning": "mạng máy tính", "example": "All the computers in the office are connected to the same network."},
            {"word": "cloud", "ipa": "/klaʊd/", "meaning": "đám mây (lưu trữ)", "example": "She saves all her work documents in the cloud."},
            {"word": "backup", "ipa": "/ˈbæk.ʌp/", "meaning": "sao lưu dữ liệu", "example": "Always backup your files before making major changes."},
            {"word": "browser", "ipa": "/ˈbraʊ.zər/", "meaning": "trình duyệt web", "example": "She uses Chrome as her preferred web browser."},
            {"word": "operating system", "ipa": "/ˈɒp.ər.eɪ.tɪŋ ˈsɪs.təm/", "meaning": "hệ điều hành", "example": "Windows and macOS are the most popular operating systems."},
            {"word": "username", "ipa": "/ˈjuː.zər.neɪm/", "meaning": "tên đăng nhập", "example": "Enter your username and password to access the account."},
            {"word": "encryption", "ipa": "/ɪnˈkrɪp.ʃən/", "meaning": "mã hóa dữ liệu", "example": "The app uses encryption to protect user data."},
            {"word": "virus", "ipa": "/ˈvaɪ.rəs/", "meaning": "virus máy tính", "example": "Install antivirus software to protect against computer viruses."},
            {"word": "antivirus", "ipa": "/ˌæn.tiˈvaɪ.rəs/", "meaning": "phần mềm diệt virus", "example": "The antivirus software detected and removed the malware."},
            {"word": "firewall", "ipa": "/ˈfaɪər.wɔːl/", "meaning": "tường lửa bảo mật", "example": "The company's firewall blocks unauthorized network access."},
            {"word": "interface", "ipa": "/ˈɪn.tə.feɪs/", "meaning": "giao diện người dùng", "example": "The user interface of this app is very intuitive."},
            {"word": "icon", "ipa": "/ˈaɪ.kɒn/", "meaning": "biểu tượng (trên màn hình)", "example": "Double-click the icon to open the program."},
            {"word": "desktop", "ipa": "/ˈdesk.tɒp/", "meaning": "màn hình desktop", "example": "She organized all her files neatly on the desktop."},
            {"word": "shortcut", "ipa": "/ˈʃɔːt.kʌt/", "meaning": "phím tắt/đường dẫn nhanh", "example": "Press Ctrl+C as a shortcut to copy text."},
            {"word": "drag and drop", "ipa": "/dræɡ ənd drɒp/", "meaning": "kéo và thả (thao tác)", "example": "Drag and drop files to move them between folders."},
            {"word": "scroll", "ipa": "/skrəʊl/", "meaning": "cuộn (trang web/tài liệu)", "example": "Scroll down to see more content on the page."},
            {"word": "zoom", "ipa": "/zuːm/", "meaning": "phóng to/thu nhỏ", "example": "Zoom in to see the image more clearly."},
            {"word": "sync", "ipa": "/sɪŋk/", "meaning": "đồng bộ hóa", "example": "The app automatically syncs data across all your devices."},
            {"word": "plugin", "ipa": "/ˈplʌɡ.ɪn/", "meaning": "tiện ích bổ sung", "example": "Install the plugin to add extra features to the browser."},
            {"word": "version", "ipa": "/ˈvɜː.ʃən/", "meaning": "phiên bản phần mềm", "example": "Make sure you are using the latest version of the software."},
            {"word": "patch", "ipa": "/pætʃ/", "meaning": "bản vá lỗi phần mềm", "example": "The developer released a patch to fix the security bug."},
            {"word": "bug", "ipa": "/bəg/", "meaning": "lỗi phần mềm", "example": "The developer found and fixed several bugs in the app."},
            {"word": "debug", "ipa": "/diːˈbʌɡ/", "meaning": "gỡ lỗi phần mềm", "example": "She spent hours debugging the code before it finally worked."},
            {"word": "code", "ipa": "/kəʊd/", "meaning": "mã lập trình", "example": "He wrote the code for the new feature in Python."},
            {"word": "developer", "ipa": "/dɪˈvel.ə.pər/", "meaning": "lập trình viên", "example": "The developer updated the app to fix performance issues."},
            {"word": "user", "ipa": "/ˈjuː.zər/", "meaning": "người dùng", "example": "The app has over 10 million active users worldwide."},
            {"word": "data", "ipa": "/ˈdeɪ.tə/", "meaning": "dữ liệu", "example": "The app collects data about user behavior to improve the experience."},
            {"word": "server", "ipa": "/ˈsɜː.vər/", "meaning": "máy chủ", "example": "The website is hosted on a server in Singapore."},
            {"word": "bandwidth", "ipa": "/ˈbænd.wɪdθ/", "meaning": "băng thông mạng", "example": "Streaming HD video requires a lot of bandwidth."},
            {"word": "loading", "ipa": "/ˈləʊ.dɪŋ/", "meaning": "đang tải", "example": "The page is loading — please wait."},
            {"word": "cache", "ipa": "/kæʃ/", "meaning": "bộ nhớ đệm", "example": "Clear the cache if the website is not displaying correctly."},
            {"word": "cookie", "ipa": "/ˈkʊk.i/", "meaning": "cookie (dữ liệu trình duyệt)", "example": "The website uses cookies to remember your preferences."},
            {"word": "URL", "ipa": "/ˌjuː.ɑːˈel/", "meaning": "địa chỉ trang web", "example": "Type the URL in the address bar to visit the website."},
            {"word": "FAQ", "ipa": "/ˌef.eɪˈkjuː/", "meaning": "câu hỏi thường gặp", "example": "Check the FAQ section before contacting customer support."},
            {"word": "tutorial", "ipa": "/tjuːˈtɔː.ri.əl/", "meaning": "hướng dẫn sử dụng", "example": "She watched a video tutorial to learn how to use the software."},
            {"word": "feedback", "ipa": "/ˈfiːd.bæk/", "meaning": "phản hồi người dùng", "example": "Leave feedback to help the developers improve the app."},
            {"word": "feature", "ipa": "/ˈfiː.tʃər/", "meaning": "tính năng phần mềm", "example": "The new version includes several useful features."},
            {"word": "screenshot", "ipa": "/ˈskriːn.ʃɒt/", "meaning": "chụp màn hình", "example": "Take a screenshot of the error message to send to support."},
            {"word": "resolution", "ipa": "/ˌrez.əˈluː.ʃən/", "meaning": "độ phân giải màn hình", "example": "Set the screen resolution to 1080p for the best image quality."},
            {"word": "touchscreen", "ipa": "/ˈtʌtʃ.skriːn/", "meaning": "màn hình cảm ứng", "example": "She navigates the app using the touchscreen on her tablet."},
            {"word": "swipe", "ipa": "/swaɪp/", "meaning": "vuốt màn hình", "example": "Swipe left to see the next photo."},
            {"word": "tap", "ipa": "/tæp/", "meaning": "chạm (màn hình cảm ứng)", "example": "Tap the icon to open the app."},
            {"word": "pinch", "ipa": "/pɪntʃ/", "meaning": "chụm/kẹp ngón tay zoom", "example": "Pinch to zoom in on the map."},
            {"word": "voice assistant", "ipa": "/vɔɪs əˈsɪs.tənt/", "meaning": "trợ lý giọng nói", "example": "She asked her voice assistant to set a reminder."},
            {"word": "dark mode", "ipa": "/dɑːk məʊd/", "meaning": "chế độ tối", "example": "Enable dark mode to reduce eye strain at night."},
            {"word": "two-factor authentication", "ipa": "/tuː ˈfæk.tər ɔːˌθen.tɪˈkeɪ.ʃən/", "meaning": "xác thực hai yếu tố", "example": "Enable two-factor authentication for better account security."},
            {"word": "pop-up", "ipa": "/ˈpɒp.ʌp/", "meaning": "cửa sổ pop-up", "example": "A pop-up window appeared asking to confirm the action."},
            {"word": "subscription", "ipa": "/səbˈskrɪp.ʃən/", "meaning": "đăng ký (dịch vụ)", "example": "A monthly subscription gives you access to all premium features."},
        ],
        "B1": [
            {"word": "algorithm", "ipa": "/ˈæl.ɡə.rɪð.əm/", "meaning": "thuật toán", "example": "The search algorithm ranks results based on relevance."},
            {"word": "API", "ipa": "/ˌeɪ.piːˈaɪ/", "meaning": "giao diện lập trình ứng dụng", "example": "The developer used an API to connect the app to the payment gateway."},
            {"word": "backend", "ipa": "/ˈbæk.end/", "meaning": "phía máy chủ (backend)", "example": "The backend processes data and handles business logic."},
            {"word": "frontend", "ipa": "/ˈfrʌnt.end/", "meaning": "phía giao diện người dùng (frontend)", "example": "The frontend developer focuses on the visual design and user experience."},
            {"word": "framework", "ipa": "/ˈfreɪm.wɜːk/", "meaning": "khung phần mềm", "example": "They used React as their JavaScript framework for the project."},
            {"word": "library", "ipa": "/ˈlaɪ.brər.i/", "meaning": "thư viện lập trình", "example": "The developer imported a library to handle date formatting."},
            {"word": "repository", "ipa": "/rɪˈpɒz.ɪ.tər.i/", "meaning": "kho lưu trữ mã nguồn", "example": "The team uses GitHub as their code repository."},
            {"word": "version control", "ipa": "/ˈvɜː.ʃən kənˈtrəʊl/", "meaning": "quản lý phiên bản mã nguồn", "example": "Version control allows teams to track changes to the codebase."},
            {"word": "deployment", "ipa": "/dɪˈplɔɪ.mənt/", "meaning": "triển khai phần mềm", "example": "The deployment of the new version went smoothly without any downtime."},
            {"word": "sprint", "ipa": "/sprɪnt/", "meaning": "chu kỳ làm việc ngắn (Agile)", "example": "The team completes one sprint every two weeks."},
            {"word": "agile methodology", "ipa": "/ˈædʒ.aɪl meˌθɒd.ɒl.ə.dʒi/", "meaning": "phương pháp Agile", "example": "Agile methodology allows teams to adapt quickly to changing requirements."},
            {"word": "scrum", "ipa": "/skrʌm/", "meaning": "khung Scrum (quản lý dự án)", "example": "The team holds a daily scrum meeting to review progress."},
            {"word": "user story", "ipa": "/ˈjuː.zər ˈstɔː.ri/", "meaning": "câu chuyện người dùng (Agile)", "example": "Each user story describes a feature from the user's perspective."},
            {"word": "backlog", "ipa": "/ˈbæk.lɒɡ/", "meaning": "danh sách công việc tồn đọng", "example": "The product manager prioritizes items in the backlog each sprint."},
            {"word": "pull request", "ipa": "/pʊl rɪˈkwest/", "meaning": "yêu cầu gộp mã (Git)", "example": "She submitted a pull request to merge her changes into the main branch."},
            {"word": "merge", "ipa": "/mərʤ/", "meaning": "gộp mã nguồn", "example": "Merge the feature branch into the main branch after testing."},
            {"word": "branch", "ipa": "/brɑːntʃ/", "meaning": "nhánh mã nguồn", "example": "Create a new branch before making changes to the code."},
            {"word": "commit", "ipa": "/kəˈmɪt/", "meaning": "lưu thay đổi vào kho mã", "example": "Commit your changes with a clear and descriptive message."},
            {"word": "unit testing", "ipa": "/ˈjuː.nɪt ˈtes.tɪŋ/", "meaning": "kiểm thử đơn vị", "example": "Unit testing verifies that individual pieces of code work correctly."},
            {"word": "integration testing", "ipa": "/ˌɪn.tɪˈɡreɪ.ʃən ˈtes.tɪŋ/", "meaning": "kiểm thử tích hợp", "example": "Integration testing checks how different modules work together."},
            {"word": "code review", "ipa": "/kəʊd rɪˈvjuː/", "meaning": "xem xét mã nguồn", "example": "Code review helps identify bugs and improve code quality."},
            {"word": "refactoring", "ipa": "/ˌriːˈfæk.tər.ɪŋ/", "meaning": "tái cấu trúc mã nguồn", "example": "Refactoring improves code readability without changing its behavior."},
            {"word": "scalability", "ipa": "/ˌskeɪ.ləˈbɪl.ɪ.ti/", "meaning": "khả năng mở rộng", "example": "The application is designed for scalability to handle millions of users."},
            {"word": "performance optimization", "ipa": "/pəˈfɔː.məns ˌɒp.tɪ.maɪˈzeɪ.ʃən/", "meaning": "tối ưu hiệu suất", "example": "Performance optimization reduced the page load time by 50%."},
            {"word": "microservices", "ipa": "/ˈmaɪ.krəʊˌsɜː.vɪsɪz/", "meaning": "kiến trúc vi dịch vụ", "example": "The application was rebuilt using a microservices architecture."},
            {"word": "monolith", "ipa": "/ˈmɒn.ə.lɪθ/", "meaning": "ứng dụng nguyên khối", "example": "They migrated from a monolith to microservices for better scalability."},
            {"word": "containerization", "ipa": "/kənˌteɪ.nər.aɪˈzeɪ.ʃən/", "meaning": "đóng gói ứng dụng vào container", "example": "Containerization using Docker makes deployment consistent across environments."},
            {"word": "CI/CD pipeline", "ipa": "/ˌsiː.aɪ ˌsiːˈdiː ˈpaɪp.laɪn/", "meaning": "quy trình tích hợp/triển khai liên tục", "example": "The CI/CD pipeline automatically tests and deploys code changes."},
            {"word": "load balancer", "ipa": "/ləʊd ˈbæl.əns.ər/", "meaning": "bộ cân bằng tải", "example": "A load balancer distributes traffic across multiple servers."},
            {"word": "CDN (Content Delivery Network)", "ipa": "/ˌsiː.diːˈen/", "meaning": "mạng phân phối nội dung", "example": "A CDN delivers content faster by caching it on servers close to the user."},
            {"word": "REST API", "ipa": "/rest ˌeɪ.piːˈaɪ/", "meaning": "API kiểu REST", "example": "The mobile app communicates with the server using a REST API."},
            {"word": "JSON", "ipa": "/ˈdʒeɪ.sɒn/", "meaning": "định dạng dữ liệu JSON", "example": "The API returns data in JSON format."},
            {"word": "authentication", "ipa": "/ɔːˌθen.tɪˈkeɪ.ʃən/", "meaning": "xác thực người dùng", "example": "The system uses JWT tokens for user authentication."},
            {"word": "authorization", "ipa": "/ˌɔː.θər.aɪˈzeɪ.ʃən/", "meaning": "phân quyền truy cập", "example": "Authorization determines what each user is allowed to do."},
            {"word": "SQL", "ipa": "/ˌes.kjuːˈel/", "meaning": "ngôn ngữ truy vấn SQL", "example": "She wrote an SQL query to retrieve data from the database."},
            {"word": "NoSQL", "ipa": "/ˌnəʊ.ˈes.kjuːˈel/", "meaning": "cơ sở dữ liệu phi quan hệ", "example": "MongoDB is a popular NoSQL database for storing unstructured data."},
            {"word": "DevOps", "ipa": "/ˈdev.ɒps/", "meaning": "DevOps (kết hợp phát triển và vận hành)", "example": "The DevOps team manages both development and system operations."},
            {"word": "debugging tools", "ipa": "/diːˈbʌɡ.ɪŋ tuːlz/", "meaning": "công cụ gỡ lỗi", "example": "She used browser debugging tools to identify the JavaScript error."},
            {"word": "responsive design", "ipa": "/rɪˈspɒn.sɪv dɪˈzaɪn/", "meaning": "thiết kế giao diện thích ứng", "example": "Responsive design ensures the website looks good on all screen sizes."},
            {"word": "UX design", "ipa": "/ˌjuːˈeks dɪˈzaɪn/", "meaning": "thiết kế trải nghiệm người dùng", "example": "Good UX design makes software intuitive and easy to use."},
            {"word": "UI design", "ipa": "/ˌjuːˈaɪ dɪˈzaɪn/", "meaning": "thiết kế giao diện người dùng", "example": "UI design focuses on the visual elements of the interface."},
            {"word": "wireframe", "ipa": "/ˈwaɪər.freɪm/", "meaning": "khung giao diện sơ bộ", "example": "The designer created wireframes before building the actual interface."},
            {"word": "prototype", "ipa": "/ˈprəʊ.tə.taɪp/", "meaning": "nguyên mẫu phần mềm", "example": "They built a prototype to test the concept with users."},
            {"word": "user acceptance testing", "ipa": "/ˈjuː.zər əkˈsep.təns ˈtes.tɪŋ/", "meaning": "kiểm thử chấp nhận người dùng", "example": "User acceptance testing ensures the software meets user requirements."},
            {"word": "regression testing", "ipa": "/rɪˈɡreʃ.ən ˈtes.tɪŋ/", "meaning": "kiểm thử hồi quy", "example": "Regression testing ensures that new changes haven't broken existing features."},
            {"word": "open source", "ipa": "/ˌəʊ.pən ˈsɔːs/", "meaning": "mã nguồn mở", "example": "Linux is the most widely used open source operating system."},
            {"word": "documentation", "ipa": "/ˌdɒk.jʊ.menˈteɪ.ʃən/", "meaning": "tài liệu kỹ thuật", "example": "Good documentation makes it easier for new developers to understand the code."},
            {"word": "tech debt", "ipa": "/tek det/", "meaning": "nợ kỹ thuật (code tệ tích tụ)", "example": "Accumulating tech debt makes future development slower and more expensive."},
            {"word": "release candidate", "ipa": "/rɪˈliːs ˈkæn.dɪ.dɪt/", "meaning": "phiên bản ứng viên phát hành", "example": "The team tested the release candidate before the final launch."},
            {"word": "SaaS (Software as a Service)", "ipa": "/sæs/", "meaning": "phần mềm dưới dạng dịch vụ", "example": "Many companies now prefer SaaS solutions over traditional installed software."},
        ],
        "B2": [
            {"word": "distributed systems", "ipa": "/dɪˈstrɪb.juː.tɪd ˈsɪs.təmz/", "meaning": "hệ thống phân tán", "example": "Distributed systems spread computation across multiple machines."},
            {"word": "concurrency", "ipa": "/kənˈkɜː.ən.si/", "meaning": "xử lý đồng thời", "example": "Concurrency allows multiple operations to run at the same time."},
            {"word": "race condition", "ipa": "/reɪs kənˈdɪʃ.ən/", "meaning": "điều kiện tranh chấp (lập trình)", "example": "A race condition occurs when two threads access shared data simultaneously."},
            {"word": "deadlock", "ipa": "/ˈded.lɒk/", "meaning": "bế tắc (lập trình đồng thời)", "example": "A deadlock occurs when two processes each wait for the other to release a resource."},
            {"word": "eventual consistency", "ipa": "/ɪˈventʃ.uəl kənˈsɪs.tən.si/", "meaning": "nhất quán cuối cùng", "example": "Eventual consistency allows distributed systems to converge over time."},
            {"word": "CAP theorem", "ipa": "/kæp ˈθɪər.əm/", "meaning": "định lý CAP (hệ thống phân tán)", "example": "The CAP theorem states a distributed system can only guarantee two of three properties."},
            {"word": "sharding", "ipa": "/ˈʃɑː.dɪŋ/", "meaning": "phân mảnh cơ sở dữ liệu", "example": "Database sharding distributes data across multiple servers for performance."},
            {"word": "indexing (database)", "ipa": "/ˈɪndɛksɪŋ (ˈdætəˌbeɪs)/", "meaning": "đánh chỉ mục cơ sở dữ liệu", "example": "Proper indexing dramatically speeds up database query performance."},
            {"word": "message queue", "ipa": "/ˈmes.ɪdʒ kjuː/", "meaning": "hàng đợi tin nhắn", "example": "A message queue decouples services and enables asynchronous communication."},
            {"word": "event-driven architecture", "ipa": "/ɪˈvent ˌdrɪv.ən ˈɑː.kɪ.tek.tʃər/", "meaning": "kiến trúc hướng sự kiện", "example": "Event-driven architecture allows services to react to events in real time."},
            {"word": "service mesh", "ipa": "/ˈsɜː.vɪs meʃ/", "meaning": "lưới dịch vụ", "example": "A service mesh manages communication between microservices."},
            {"word": "Kubernetes", "ipa": "/ˌkjuː.bərˈneɪ.tɪs/", "meaning": "Kubernetes (quản lý container)", "example": "Kubernetes orchestrates the deployment and scaling of containerized applications."},
            {"word": "infrastructure as code", "ipa": "/ˈɪn.frə.strʌk.tʃər əz kəʊd/", "meaning": "hạ tầng dưới dạng mã", "example": "Infrastructure as code allows servers to be provisioned automatically."},
            {"word": "serverless computing", "ipa": "/ˈsɜː.vər.ləs kəmˈpjuː.tɪŋ/", "meaning": "điện toán không máy chủ", "example": "Serverless computing lets developers run code without managing infrastructure."},
            {"word": "GraphQL", "ipa": "/ˈɡræf.kjuːˈel/", "meaning": "ngôn ngữ truy vấn GraphQL", "example": "GraphQL gives clients more precise control over the data they request."},
            {"word": "WebSocket", "ipa": "/ˈwebˌsɒk.ɪt/", "meaning": "WebSocket (kết nối thời gian thực)", "example": "WebSocket enables real-time bidirectional communication between client and server."},
            {"word": "OAuth", "ipa": "/ˈəʊ.ɔːθ/", "meaning": "giao thức ủy quyền OAuth", "example": "OAuth allows users to log in with their Google or Facebook account."},
            {"word": "JWT (JSON Web Token)", "ipa": "/ˌdʒeɪ.sɒn web ˈtəʊ.kən/", "meaning": "mã thông báo JSON Web", "example": "JWT is used to securely transmit user information between client and server."},
            {"word": "HTTPS", "ipa": "/ˌeɪtʃ.tiː.tiː.piːˈes/", "meaning": "giao thức web bảo mật", "example": "All websites should use HTTPS to encrypt data in transit."},
            {"word": "TLS (Transport Layer Security)", "ipa": "/tiː.el.ˈes/", "meaning": "bảo mật lớp truyền tải", "example": "TLS encrypts communication between the browser and server."},
            {"word": "SQL injection", "ipa": "/ˌes.kjuːˈel ɪnˈdʒek.ʃən/", "meaning": "tấn công SQL injection", "example": "SQL injection can compromise a database if inputs are not sanitized."},
            {"word": "XSS (Cross-Site Scripting)", "ipa": "/ˌekˌes.ˈes/", "meaning": "tấn công XSS", "example": "XSS attacks inject malicious scripts into web pages viewed by users."},
            {"word": "CSRF", "ipa": "/ˌsiː.es.ɑːˈef/", "meaning": "tấn công giả mạo yêu cầu", "example": "CSRF attacks trick users into submitting unauthorized requests."},
            {"word": "penetration testing", "ipa": "/ˌpen.ɪˈtreɪ.ʃən ˈtes.tɪŋ/", "meaning": "kiểm thử xâm nhập", "example": "Penetration testing identifies security vulnerabilities in a system."},
            {"word": "zero-day vulnerability", "ipa": "/ˈzɪər.əʊ deɪ ˌvʌl.nər.əˈbɪl.ɪ.ti/", "meaning": "lỗ hổng zero-day", "example": "A zero-day vulnerability is exploited before developers can patch it."},
            {"word": "machine learning pipeline", "ipa": "/məˈʃiːn ˈlɜː.nɪŋ ˈpaɪp.laɪn/", "meaning": "quy trình học máy", "example": "The machine learning pipeline includes data ingestion, training, and deployment."},
            {"word": "feature engineering", "ipa": "/ˈfiː.tʃər ˌen.dʒɪˈnɪər.ɪŋ/", "meaning": "kỹ thuật tạo đặc trưng", "example": "Feature engineering transforms raw data into meaningful inputs for ML models."},
            {"word": "model training", "ipa": "/ˈmɒd.əl ˈtreɪ.nɪŋ/", "meaning": "huấn luyện mô hình ML", "example": "Model training requires large datasets and significant computing power."},
            {"word": "overfitting", "ipa": "/ˌəʊ.vəˈfɪt.ɪŋ/", "meaning": "quá khớp (ML)", "example": "Overfitting occurs when a model learns noise rather than general patterns."},
            {"word": "underfitting", "ipa": "/ˌʌn.dəˈfɪt.ɪŋ/", "meaning": "chưa khớp (ML)", "example": "Underfitting occurs when the model is too simple to capture the data patterns."},
            {"word": "hyperparameter tuning", "ipa": "/ˌhaɪ.pəˈpær.ə.mɪ.tər ˈtjuː.nɪŋ/", "meaning": "điều chỉnh siêu tham số", "example": "Hyperparameter tuning improves model accuracy through systematic search."},
            {"word": "A/B testing", "ipa": "/ˌeɪ.biː ˈtes.tɪŋ/", "meaning": "thử nghiệm A/B", "example": "A/B testing compares two versions of a feature to see which performs better."},
            {"word": "observability", "ipa": "/əbˌzɜː.vəˈbɪl.ɪ.ti/", "meaning": "khả năng quan sát hệ thống", "example": "Observability tools provide insights into system health and performance."},
            {"word": "chaos engineering", "ipa": "/ˈkeɪ.ɒs ˌen.dʒɪˈnɪər.ɪŋ/", "meaning": "kỹ thuật kiểm thử hệ thống hỗn loạn", "example": "Chaos engineering deliberately introduces failures to test system resilience."},
            {"word": "SLA (Service Level Agreement)", "ipa": "/ˌes.el.ˈeɪ/", "meaning": "thỏa thuận mức dịch vụ", "example": "The SLA guarantees 99.9% uptime for the cloud service."},
            {"word": "SLO (Service Level Objective)", "ipa": "/ˌes.el.ˈəʊ/", "meaning": "mục tiêu mức dịch vụ", "example": "The team set an SLO of 99.5% successful requests per month."},
            {"word": "incident management", "ipa": "/ˈɪn.sɪ.dənt ˈmæn.ɪdʒ.mənt/", "meaning": "quản lý sự cố", "example": "Good incident management minimizes the impact of system outages."},
            {"word": "on-call rotation", "ipa": "/ɒn kɔːl rəʊˈteɪ.ʃən/", "meaning": "lịch trực sự cố", "example": "The team shares an on-call rotation to handle production incidents."},
            {"word": "postmortem analysis", "ipa": "/ˌpəʊst.ˈmɔː.təm əˈnæl.ɪ.sɪs/", "meaning": "phân tích sau sự cố", "example": "A postmortem analysis identifies the root cause of the system failure."},
            {"word": "dependency injection", "ipa": "/dɪˈpen.dən.si ɪnˈdʒek.ʃən/", "meaning": "tiêm phụ thuộc (lập trình)", "example": "Dependency injection makes code more testable and loosely coupled."},
            {"word": "design patterns", "ipa": "/dɪˈzaɪn ˈpæt.ənz/", "meaning": "mẫu thiết kế phần mềm", "example": "Design patterns provide reusable solutions to common software problems."},
            {"word": "SOLID principles", "ipa": "/ˈsɒl.ɪd ˈprɪn.sɪ.pəlz/", "meaning": "nguyên tắc SOLID (OOP)", "example": "SOLID principles guide developers towards maintainable and scalable code."},
            {"word": "domain-driven design", "ipa": "/dəˈmeɪn ˌdrɪv.ən dɪˈzaɪn/", "meaning": "thiết kế hướng miền nghiệp vụ", "example": "Domain-driven design aligns software structure with business concepts."},
            {"word": "functional programming", "ipa": "/ˈfʌŋk.ʃən.əl ˈprəʊ.ɡræm.ɪŋ/", "meaning": "lập trình hàm", "example": "Functional programming avoids mutable state and side effects."},
            {"word": "reactive programming", "ipa": "/riˈæk.tɪv ˈprəʊ.ɡræm.ɪŋ/", "meaning": "lập trình phản ứng", "example": "Reactive programming models data as streams that change over time."},
            {"word": "event sourcing", "ipa": "/ɪˈvent ˈsɔː.sɪŋ/", "meaning": "lưu trữ sự kiện (kiến trúc)", "example": "Event sourcing stores the history of all changes as a sequence of events."},
            {"word": "CQRS (Command Query Responsibility Segregation)", "ipa": "/ˌsiː.kjuː.ɑːˈes/", "meaning": "tách biệt đọc/ghi dữ liệu", "example": "CQRS separates read and write operations for better performance."},
            {"word": "strangler fig pattern", "ipa": "/ˈstræŋ.ɡlər fɪɡ ˈpæt.ən/", "meaning": "mô hình tái cấu trúc dần dần", "example": "The strangler fig pattern gradually replaces a legacy system with new components."},
            {"word": "hexagonal architecture", "ipa": "/hekˈsæɡ.ə.nəl ˈɑː.kɪ.tek.tʃər/", "meaning": "kiến trúc lục giác", "example": "Hexagonal architecture isolates business logic from external concerns."},
            {"word": "technical roadmap", "ipa": "/ˈtek.nɪ.kəl ˈrəʊd.mæp/", "meaning": "lộ trình kỹ thuật", "example": "The technical roadmap outlines the team's development priorities for the year."},
        ],
        "C1": [
            {"word": "formal verification", "ipa": "/ˈfɔː.məl ˌver.ɪ.fɪˈkeɪ.ʃən/", "meaning": "kiểm chứng hình thức (toán học)", "example": "Formal verification uses mathematical proofs to guarantee software correctness."},
            {"word": "type theory", "ipa": "/taɪp ˈθɪər.i/", "meaning": "lý thuyết kiểu (lập trình)", "example": "Type theory provides a formal framework for programming language semantics."},
            {"word": "lambda calculus", "ipa": "/ˈlæm.də ˈkæl.kjʊ.ləs/", "meaning": "phép tính lambda", "example": "Lambda calculus is the theoretical foundation of functional programming."},
            {"word": "Turing completeness", "ipa": "/ˈtjʊər.ɪŋ kəmˈpliːt.nəs/", "meaning": "tính Turing đầy đủ", "example": "A Turing complete system can simulate any computation."},
            {"word": "NP-completeness", "ipa": "/ˌen.piː kəmˈpliːt.nəs/", "meaning": "độ phức tạp NP-đầy đủ", "example": "NP-completeness means a problem is computationally intractable for large inputs."},
            {"word": "Byzantine fault tolerance", "ipa": "/ˌbɪz.ənˈtiːn fɔːlt ˈtɒl.ər.əns/", "meaning": "dung sai lỗi Byzantine", "example": "Byzantine fault tolerance allows a system to work even with malicious or faulty nodes."},
            {"word": "consensus algorithm", "ipa": "/kənˈsen.səs ˈæl.ɡə.rɪð.əm/", "meaning": "thuật toán đồng thuận", "example": "Consensus algorithms like Paxos and Raft ensure agreement in distributed systems."},
            {"word": "homomorphic encryption", "ipa": "/ˌhɒm.əˈmɔː.fɪk ɪnˈkrɪp.ʃən/", "meaning": "mã hóa đồng cấu", "example": "Homomorphic encryption allows computation on encrypted data without decrypting it."},
            {"word": "zero-knowledge proof", "ipa": "/ˈzɪər.əʊ ˈnɒl.ɪdʒ pruːf/", "meaning": "bằng chứng không tiết lộ thông tin", "example": "A zero-knowledge proof allows one party to prove knowledge without revealing it."},
            {"word": "differential privacy", "ipa": "/ˌdɪf.ərˈen.ʃəl ˈprɪ.və.si/", "meaning": "bảo mật vi phân", "example": "Differential privacy adds noise to data to protect individual information."},
            {"word": "federated learning", "ipa": "/ˈfed.ər.eɪ.tɪd ˈlɜː.nɪŋ/", "meaning": "học liên kết phân tán", "example": "Federated learning trains models on distributed data without sharing raw data."},
            {"word": "transformer architecture", "ipa": "/trænsˈfɔː.mər ˈɑː.kɪ.tek.tʃər/", "meaning": "kiến trúc transformer (AI)", "example": "The transformer architecture powers modern large language models like GPT."},
            {"word": "attention mechanism", "ipa": "/əˈtenʃən ˈmɛkənɪzəm/", "meaning": "Cơ chế chú ý trong AI", "example": "The attention mechanism allows the model to focus on relevant parts of the input."},
            {"word": "gradient descent", "ipa": "/ˈɡreɪdiənt dɪˈsɛnt/", "meaning": "Phương pháp hạ gradient (tối ưu hóa)", "example": "Gradient descent is used to minimize the loss function in training."},
            {"word": "backpropagation", "ipa": "/ˌbæk.prɒp.əˈɡeɪ.ʃən/", "meaning": "lan truyền ngược (neural network)", "example": "Backpropagation computes gradients to update weights in neural networks."},
            {"word": "loss function", "ipa": "/lɒs ˈfʌŋk.ʃən/", "meaning": "hàm mất mát (ML)", "example": "The loss function measures how well the model's predictions match the true values."},
            {"word": "regularization", "ipa": "/ˌreɡ.jʊ.lər.aɪˈzeɪ.ʃən/", "meaning": "chính quy hóa (ML)", "example": "Regularization prevents overfitting by adding a penalty to the model complexity."},
            {"word": "convolutional neural network", "ipa": "/ˌkɒn.vəˈluː.ʃən.əl ˈnjʊər.əl ˈnet.wɜːk/", "meaning": "mạng nơ-ron tích chập", "example": "Convolutional neural networks are widely used for image recognition tasks."},
            {"word": "recurrent neural network", "ipa": "/rɪˈkɜː.ənt ˈnjʊər.əl ˈnet.wɜːk/", "meaning": "mạng nơ-ron hồi quy", "example": "Recurrent neural networks process sequential data like text and speech."},
            {"word": "generative adversarial network", "ipa": "/ˈdʒen.ər.ə.tɪv ədˈvɜː.sər.i.əl ˈnet.wɜːk/", "meaning": "mạng đối kháng sinh", "example": "Generative adversarial networks can create realistic synthetic images."},
            {"word": "reinforcement learning", "ipa": "/ˌriːɪnˈfɔːs.mənt ˈlɜː.nɪŋ/", "meaning": "học tăng cường", "example": "Reinforcement learning trains agents to maximize cumulative reward through interaction."},
            {"word": "transfer learning", "ipa": "/ˈtræns.fɜː ˈlɜː.nɪŋ/", "meaning": "học chuyển tiếp", "example": "Transfer learning applies knowledge from one task to improve performance on another."},
            {"word": "multimodal AI", "ipa": "/ˌmʌl.tiˈməʊ.dəl ˌeɪˈaɪ/", "meaning": "AI đa phương thức", "example": "Multimodal AI processes and generates text, images, and audio simultaneously."},
            {"word": "prompt engineering", "ipa": "/prɒmpt ˌen.dʒɪˈnɪər.ɪŋ/", "meaning": "kỹ thuật thiết kế lệnh (AI)", "example": "Prompt engineering crafts inputs to elicit optimal responses from large language models."},
            {"word": "RAG (Retrieval-Augmented Generation)", "ipa": "/ræɡ/", "meaning": "sinh tạo tăng cường bằng truy xuất", "example": "RAG combines a retrieval system with a language model to produce grounded answers."},
            {"word": "model quantization", "ipa": "/ˈmɒd.əl ˌkwɒn.tɪˈzeɪ.ʃən/", "meaning": "lượng hóa mô hình ML", "example": "Model quantization reduces model size by representing weights with fewer bits."},
            {"word": "model distillation", "ipa": "/ˈmɒd.əl ˌdɪs.tɪˈleɪ.ʃən/", "meaning": "chưng cất mô hình ML", "example": "Model distillation trains a smaller student model to mimic a larger teacher model."},
            {"word": "neural architecture search", "ipa": "/ˈnjʊər.əl ˈɑː.kɪ.tek.tʃər sɜːtʃ/", "meaning": "tìm kiếm kiến trúc nơ-ron", "example": "Neural architecture search automates the design of optimal neural network structures."},
            {"word": "software entropy", "ipa": "/ˈsɒft.weər ˈen.trə.pi/", "meaning": "sự hỗn loạn mã nguồn theo thời gian", "example": "Software entropy increases over time as systems grow in complexity."},
            {"word": "Conway's Law", "ipa": "/ˈkɒn.weɪz lɔː/", "meaning": "Luật Conway (tổ chức phần mềm)", "example": "Conway's Law states that software architecture mirrors the communication structure of the team."},
            {"word": "Amdahl's Law", "ipa": "/ˈæm.dɑːlz lɔː/", "meaning": "Luật Amdahl (giới hạn song song)", "example": "Amdahl's Law predicts the speedup achievable through parallelization."},
            {"word": "Little's Law", "ipa": "/ˈlɪt.əlz lɔː/", "meaning": "Luật Little (lý thuyết hàng đợi)", "example": "Little's Law relates the average number of items in a queuing system to arrival rate and time."},
            {"word": "context switching overhead", "ipa": "/ˈkɒn.tekst ˈswɪtʃ.ɪŋ ˌəʊ.vəˈhed/", "meaning": "chi phí chuyển ngữ cảnh", "example": "Excessive context switching overhead degrades multi-threaded application performance."},
            {"word": "memory fragmentation", "ipa": "/ˈmem.ər.i ˌfræɡ.menˈteɪ.ʃən/", "meaning": "phân mảnh bộ nhớ", "example": "Memory fragmentation occurs when free memory is broken into small, non-contiguous blocks."},
            {"word": "garbage collection", "ipa": "/ˈɡɑː.bɪdʒ kəˈlek.ʃən/", "meaning": "thu gom rác (quản lý bộ nhớ)", "example": "Garbage collection automatically reclaims memory that is no longer in use."},
            {"word": "tail latency", "ipa": "/teɪl ˈleɪ.tən.si/", "meaning": "độ trễ đuôi (phần trăm cao)", "example": "Tail latency refers to the worst-case response times at the 99th percentile."},
            {"word": "cache coherence", "ipa": "/kæʃ ˈkəʊ.hɪər.əns/", "meaning": "tính nhất quán bộ nhớ đệm", "example": "Cache coherence ensures all processors have a consistent view of shared memory."},
            {"word": "memory-mapped I/O", "ipa": "/ˈmem.ər.i mæpt ˌaɪˈəʊ/", "meaning": "I/O ánh xạ bộ nhớ", "example": "Memory-mapped I/O allows device registers to be accessed like regular memory."},
            {"word": "branch prediction", "ipa": "/brɑːntʃ prɪˈdɪk.ʃən/", "meaning": "dự đoán nhánh (CPU)", "example": "Branch prediction allows CPUs to speculatively execute instructions before a branch is resolved."},
            {"word": "superscalar execution", "ipa": "/ˌsuː.pəˈskeɪ.lər ˌek.sɪˈkjuː.ʃən/", "meaning": "thực thi siêu vô hướng (CPU)", "example": "Superscalar execution allows a CPU to dispatch multiple instructions per clock cycle."},
            {"word": "speculative execution", "ipa": "/ˌspek.jʊˈleɪ.tɪv ˌek.sɪˈkjuː.ʃən/", "meaning": "thực thi đầu cơ (CPU)", "example": "Speculative execution was exploited by the Meltdown and Spectre vulnerabilities."},
            {"word": "NUMA (Non-Uniform Memory Access)", "ipa": "/ˈnjuː.mə/", "meaning": "truy cập bộ nhớ không đồng đều", "example": "NUMA architectures have different memory access times depending on processor location."},
            {"word": "lock-free data structures", "ipa": "/lɒk friː ˈdeɪ.tə ˈstrʌk.tʃərz/", "meaning": "cấu trúc dữ liệu không khóa", "example": "Lock-free data structures avoid bottlenecks caused by mutex contention."},
            {"word": "software transactional memory", "ipa": "/ˈsɒft.weər trænˈzæk.ʃən.əl ˈmem.ər.i/", "meaning": "bộ nhớ giao dịch phần mềm", "example": "Software transactional memory simplifies concurrent programming by managing shared state."},
            {"word": "coroutine", "ipa": "/ˈkɒ.rəʊ.tiːn/", "meaning": "coroutine (luồng hợp tác)", "example": "Coroutines allow asynchronous code to be written in a sequential style."},
            {"word": "dataflow programming", "ipa": "/ˈdeɪ.tə.fləʊ ˈprəʊ.ɡræm.ɪŋ/", "meaning": "lập trình luồng dữ liệu", "example": "Dataflow programming models computation as a directed graph of data transformations."},
            {"word": "program synthesis", "ipa": "/ˈprəʊ.ɡræm ˈsɪn.θɪ.sɪs/", "meaning": "tổng hợp chương trình tự động", "example": "Program synthesis automatically generates code from high-level specifications."},
            {"word": "static analysis", "ipa": "/ˈstæt.ɪk əˈnæl.ɪ.sɪs/", "meaning": "phân tích tĩnh mã nguồn", "example": "Static analysis tools detect potential bugs without executing the code."},
            {"word": "abstract interpretation", "ipa": "/ˈæb.strækt ɪnˌtɜː.prɪˈteɪ.ʃən/", "meaning": "thông dịch trừu tượng", "example": "Abstract interpretation approximates program behavior for static analysis."},
            {"word": "symbolic execution", "ipa": "/ˈsɪm.bɒl.ɪk ˌek.sɪˈkjuː.ʃən/", "meaning": "thực thi ký hiệu", "example": "Symbolic execution explores all possible paths through a program for testing."},
        ],
    },
    "sports": {
        "A1": [
            {"word": "ball", "ipa": "/bɔːl/", "meaning": "quả bóng", "example": "Kick the ball into the goal to score a point."},
            {"word": "run", "ipa": "/rʌn/", "meaning": "chạy", "example": "She likes to run in the park every morning."},
            {"word": "swim", "ipa": "/swɪm/", "meaning": "bơi", "example": "He can swim very fast in the pool."},
            {"word": "team", "ipa": "/tiːm/", "meaning": "đội", "example": "Our team won the football match last night."},
            {"word": "win", "ipa": "/wɪn/", "meaning": "chiến thắng", "example": "They worked hard to win the championship."},
            {"word": "play", "ipa": "/pleɪ/", "meaning": "chơi (thể thao)", "example": "The children play basketball after school."},
            {"word": "goal", "ipa": "/ɡəʊl/", "meaning": "bàn thắng; khung thành", "example": "He scored the winning goal in the final minute."},
            {"word": "race", "ipa": "/reɪs/", "meaning": "cuộc đua", "example": "She finished first in the 100-meter race."},
            {"word": "jump", "ipa": "/dʒʌmp/", "meaning": "nhảy", "example": "Can you jump over that hurdle?"},
            {"word": "kick", "ipa": "/kɪk/", "meaning": "đá", "example": "He kicked the ball across the field."},
            {"word": "throw", "ipa": "/θrəʊ/", "meaning": "ném", "example": "She can throw the ball very far."},
            {"word": "catch", "ipa": "/kætʃ/", "meaning": "bắt (bóng)", "example": "The goalkeeper caught the ball easily."},
            {"word": "hit", "ipa": "/hɪt/", "meaning": "đánh (bóng)", "example": "The tennis player hit the ball over the net."},
            {"word": "sport", "ipa": "/spɔːt/", "meaning": "môn thể thao", "example": "Swimming is my favorite sport."},
            {"word": "game", "ipa": "/ɡeɪm/", "meaning": "trận đấu; trò chơi", "example": "The game starts at 7 o'clock tonight."},
            {"word": "field", "ipa": "/fiːld/", "meaning": "sân vận động, bãi tập", "example": "The players are warming up on the field."},
            {"word": "gym", "ipa": "/dʒɪm/", "meaning": "phòng tập thể dục", "example": "I go to the gym three times a week."},
            {"word": "bike", "ipa": "/baɪk/", "meaning": "xe đạp", "example": "He rides his bike to school every day."},
            {"word": "pool", "ipa": "/puːl/", "meaning": "hồ bơi", "example": "The swimming pool is open from 6 am to 10 pm."},
            {"word": "fast", "ipa": "/fɑːst/", "meaning": "nhanh", "example": "She is the fastest runner in the class."},
            {"word": "strong", "ipa": "/strɒŋ/", "meaning": "mạnh mẽ", "example": "You need to be strong to lift those weights."},
            {"word": "tired", "ipa": "/taɪəd/", "meaning": "mệt mỏi", "example": "He felt very tired after the long race."},
            {"word": "water", "ipa": "/ˈwɔː.tər/", "meaning": "nước", "example": "Drink plenty of water during exercise."},
            {"word": "match", "ipa": "/mæʧ/", "meaning": "Trận đấu; diêm quẹt", "example": "The match between the two teams was exciting."},
            {"word": "lose", "ipa": "/luːz/", "meaning": "thua", "example": "Nobody wants to lose the final game."},
            {"word": "dance", "ipa": "/dɑːns/", "meaning": "nhảy múa", "example": "She loves to dance as a form of exercise."},
            {"word": "walk", "ipa": "/wɔːk/", "meaning": "đi bộ", "example": "We walk for 30 minutes every evening."},
            {"word": "jump rope", "ipa": "/dʒʌmp rəʊp/", "meaning": "nhảy dây", "example": "Jumping rope is great exercise for children."},
            {"word": "net", "ipa": "/nɛt/", "meaning": "Lưới; mạng lưới", "example": "The fisherman cast his net into the sea."},
            {"word": "court", "ipa": "/kɔːt/", "meaning": "sân (tennis, bóng rổ...)", "example": "The tennis court is wet after the rain."},
            {"word": "cap", "ipa": "/kæp/", "meaning": "mũ lưỡi trai; số lần ra sân đội tuyển", "example": "He earned his first international cap last month."},
            {"word": "jersey", "ipa": "/ˈʤərzi/", "meaning": "áo đồng phục thể thao", "example": "All players wear the same jersey during a match."},
            {"word": "score", "ipa": "/skɔːr/", "meaning": "tỉ số; ghi điểm", "example": "The final score was 3-1 in our favor."},
            {"word": "player", "ipa": "/ˈpleɪ.ər/", "meaning": "cầu thủ; vận động viên", "example": "She is the best player on the team."},
            {"word": "train", "ipa": "/treɪn/", "meaning": "luyện tập", "example": "Athletes train hard every day to improve their performance."},
            {"word": "tired", "ipa": "/taɪəd/", "meaning": "mệt mỏi", "example": "He felt very tired after the long race."},
            {"word": "fun", "ipa": "/fʌn/", "meaning": "vui vẻ", "example": "Playing sports is fun and keeps you healthy."},
            {"word": "cup", "ipa": "/kʌp/", "meaning": "cúp, cup", "example": "Our team won the national cup last year."},
            {"word": "final", "ipa": "/ˈfaɪ.nəl/", "meaning": "trận chung kết", "example": "They reached the final of the world championship."},
            {"word": "swim cap", "ipa": "/swɪm kæp/", "meaning": "mũ bơi", "example": "You must wear a swim cap in this pool."},
            {"word": "helmet", "ipa": "/ˈhel.mɪt/", "meaning": "mũ bảo hiểm", "example": "Always wear a helmet when riding a bike."},
            {"word": "gloves", "ipa": "/ɡlʌvz/", "meaning": "găng tay", "example": "Boxing gloves protect the hands during a fight."},
            {"word": "shorts", "ipa": "/ʃɔːts/", "meaning": "quần short thể thao", "example": "Wear comfortable shorts when you exercise."},
            {"word": "sneakers", "ipa": "/ˈsniː.kərz/", "meaning": "giày thể thao", "example": "Good sneakers are important for running."},
            {"word": "trophy", "ipa": "/ˈtrəʊ.fi/", "meaning": "cúp chiến thắng", "example": "The team lifted the trophy after winning the final."},
            {"word": "draw", "ipa": "/drɔː/", "meaning": "trận hòa", "example": "The match ended in a draw, 2-2."},
            {"word": "throw-in", "ipa": "/ˈθrəʊ.ɪn/", "meaning": "ném biên", "example": "He took a throw-in after the ball went out of play."},
            {"word": "whistle", "ipa": "/ˈwɪs.əl/", "meaning": "còi; thổi còi", "example": "The referee blew the whistle to end the match."},
            {"word": "foul", "ipa": "/faʊl/", "meaning": "phạm lỗi", "example": "The player received a yellow card for a foul."},
            {"word": "offside", "ipa": "/ˌɒfˈsaɪd/", "meaning": "việt vị", "example": "The goal was disallowed because the player was offside."},
        ],
        "A2": [
            {"word": "coach", "ipa": "/kəʊtʃ/", "meaning": "Huấn luyện viên", "example": "She hired a personal coach to improve her tennis skills."},
            {"word": "athlete", "ipa": "/ˈæθ.liːt/", "meaning": "vận động viên", "example": "She is a dedicated athlete who trains six days a week."},
            {"word": "champion", "ipa": "/ˈtʃæm.pi.ən/", "meaning": "nhà vô địch", "example": "He is the current world champion in the 200-meter sprint."},
            {"word": "exercise", "ipa": "/ˈek.sə.saɪz/", "meaning": "tập thể dục", "example": "Regular exercise is important for good health."},
            {"word": "stadium", "ipa": "/ˈsteɪ.di.əm/", "meaning": "sân vận động", "example": "The stadium was full of fans cheering loudly."},
            {"word": "tournament", "ipa": "/ˈtʊə.nə.mənt/", "meaning": "giải đấu", "example": "Our school team entered the regional basketball tournament."},
            {"word": "referee", "ipa": "/ˌref.əˈriː/", "meaning": "trọng tài", "example": "The referee awarded a penalty to the home team."},
            {"word": "opponent", "ipa": "/əˈpəʊ.nənt/", "meaning": "đối thủ", "example": "She defeated her opponent in three sets."},
            {"word": "practice", "ipa": "/ˈpræk.tɪs/", "meaning": "luyện tập", "example": "They have football practice every Tuesday afternoon."},
            {"word": "competition", "ipa": "/ˌkɒm.pɪˈtɪʃ.ən/", "meaning": "cuộc thi đấu", "example": "The swimming competition attracts athletes from 20 countries."},
            {"word": "medal", "ipa": "/ˈmed.əl/", "meaning": "huy chương", "example": "She won a gold medal at the national championships."},
            {"word": "fitness", "ipa": "/ˈfɪt.nəs/", "meaning": "thể lực, sức khỏe thể chất", "example": "Fitness tests are conducted at the beginning of every season."},
            {"word": "warm-up", "ipa": "/ˈwɔːm.ʌp/", "meaning": "khởi động", "example": "Always do a warm-up before starting intense exercise."},
            {"word": "cool-down", "ipa": "/ˈkuːl.daʊn/", "meaning": "hạ nhiệt sau tập", "example": "A cool-down helps reduce muscle soreness after exercise."},
            {"word": "penalty", "ipa": "/ˈpen.əl.ti/", "meaning": "phạt đền", "example": "The team scored from the penalty spot to win the game."},
            {"word": "league", "ipa": "/liːɡ/", "meaning": "giải bóng đá", "example": "Our team plays in the national football league."},
            {"word": "championship", "ipa": "/ˈtʃæm.pi.ən.ʃɪp/", "meaning": "giải vô địch", "example": "The championship will be held in Paris next summer."},
            {"word": "sprint", "ipa": "/sprɪnt/", "meaning": "chạy nước rút", "example": "He did a sprint at the end of the race to overtake his rival."},
            {"word": "stretch", "ipa": "/stretʃ/", "meaning": "khởi động giãn cơ", "example": "Stretch your muscles before and after every workout."},
            {"word": "team captain", "ipa": "/tiːm ˈkæp.tɪn/", "meaning": "đội trưởng", "example": "The team captain led by example on the field."},
            {"word": "goalkeeper", "ipa": "/ˈɡəʊlˌkiː.pər/", "meaning": "thủ môn", "example": "The goalkeeper made three incredible saves in the match."},
            {"word": "substitute", "ipa": "/ˈsʌb.stɪ.tjuːt/", "meaning": "cầu thủ dự bị", "example": "The coach brought on a substitute in the second half."},
            {"word": "injury", "ipa": "/ˈɪn.dʒər.i/", "meaning": "chấn thương", "example": "He missed the final due to a knee injury."},
            {"word": "lap", "ipa": "/læp/", "meaning": "vòng đua", "example": "She completed 10 laps of the swimming pool."},
            {"word": "track", "ipa": "/træk/", "meaning": "đường đua", "example": "The runners lined up at the start of the track."},
            {"word": "baseline", "ipa": "/ˈbeɪs.laɪn/", "meaning": "đường biên ngang (tennis)", "example": "She played most of her shots from the baseline."},
            {"word": "dribble", "ipa": "/ˈdrɪb.əl/", "meaning": "rê bóng", "example": "He dribbled past three defenders before scoring."},
            {"word": "tackle", "ipa": "/ˈtæk.əl/", "meaning": "tranh bóng, cản phá", "example": "The defender made a perfect tackle to stop the attack."},
            {"word": "serve", "ipa": "/sɜːv/", "meaning": "giao bóng (tennis/volleyball)", "example": "Her serve is one of the fastest in the tournament."},
            {"word": "pass", "ipa": "/pɑːs/", "meaning": "Thẻ thông hành, thẻ ra vào", "example": "You must show your security pass to enter."},
            {"word": "header", "ipa": "/ˈhed.ər/", "meaning": "cú đánh đầu", "example": "She scored with a brilliant header from the corner kick."},
            {"word": "cross", "ipa": "/krɒs/", "meaning": "đường tạt biên", "example": "The winger sent in a perfect cross for the striker."},
            {"word": "freefall", "ipa": "/ˈfriː.fɔːl/", "meaning": "nhảy tự do", "example": "The skydiver entered freefall after jumping from the plane."},
            {"word": "marathon", "ipa": "/ˈmær.ə.θən/", "meaning": "cuộc chạy marathon", "example": "She trained for six months to complete a marathon."},
            {"word": "boxing", "ipa": "/ˈbɒk.sɪŋ/", "meaning": "quyền anh", "example": "Boxing requires both physical strength and mental focus."},
            {"word": "cycling", "ipa": "/ˈsaɪ.klɪŋ/", "meaning": "đua xe đạp", "example": "Cycling is both a sport and a popular form of transport."},
            {"word": "rowing", "ipa": "/ˈrəʊ.ɪŋ/", "meaning": "chèo thuyền", "example": "She competes in rowing events at the national level."},
            {"word": "wrestling", "ipa": "/ˈres.lɪŋ/", "meaning": "đấu vật", "example": "Wrestling requires great strength and technique."},
            {"word": "gymnastics", "ipa": "/dʒɪmˈnæs.tɪks/", "meaning": "thể dục dụng cụ", "example": "She started gymnastics training at the age of four."},
            {"word": "volleyball", "ipa": "/ˈvɒl.i.bɔːl/", "meaning": "bóng chuyền", "example": "Volleyball is very popular on beaches in summer."},
            {"word": "badminton", "ipa": "/ˈbæd.mɪn.tən/", "meaning": "cầu lông", "example": "We play badminton together every weekend."},
            {"word": "archery", "ipa": "/ˈɑː.tʃər.i/", "meaning": "bắn cung", "example": "Archery requires excellent concentration and steady hands."},
            {"word": "surfing", "ipa": "/ˈsɜː.fɪŋ/", "meaning": "lướt sóng", "example": "She learned surfing during her holiday in Hawaii."},
            {"word": "skiing", "ipa": "/ˈskiː.ɪŋ/", "meaning": "trượt tuyết", "example": "Skiing is popular in the Alps during winter."},
            {"word": "judo", "ipa": "/ˈdʒuː.dəʊ/", "meaning": "judo", "example": "He has a black belt in judo."},
            {"word": "karate", "ipa": "/kəˈrɑː.ti/", "meaning": "karate", "example": "She practices karate three times a week."},
            {"word": "weight lifting", "ipa": "/weɪt ˈlɪf.tɪŋ/", "meaning": "cử tạ", "example": "Weight lifting builds muscle strength and bone density."},
            {"word": "long jump", "ipa": "/lɒŋ dʒʌmp/", "meaning": "nhảy xa", "example": "He broke the school record in the long jump."},
            {"word": "high jump", "ipa": "/haɪ dʒʌmp/", "meaning": "nhảy cao", "example": "She cleared 1.80 meters in the high jump."},
            {"word": "decathlon", "ipa": "/dɪˈkæθ.lɒn/", "meaning": "mười môn phối hợp", "example": "The decathlon is considered the ultimate test of athletic ability."},
        ],
        "B1": [
            {"word": "endurance", "ipa": "/ɪnˈdjʊər.əns/", "meaning": "sức bền", "example": "Marathon runners need exceptional endurance to complete the 42km race."},
            {"word": "stamina", "ipa": "/ˈstæm.ɪ.nə/", "meaning": "thể lực bền bỉ", "example": "Building stamina takes months of consistent training."},
            {"word": "sportsmanship", "ipa": "/ˈspɔːts.mən.ʃɪp/", "meaning": "tinh thần thể thao", "example": "He congratulated his opponent, showing great sportsmanship."},
            {"word": "relay race", "ipa": "/ˈriː.leɪ reɪs/", "meaning": "đua tiếp sức", "example": "The relay race requires smooth baton exchanges between teammates."},
            {"word": "knockout", "ipa": "/ˈnɒk.aʊt/", "meaning": "đấm knock-out; hạ gục đối thủ", "example": "The boxer won by knockout in the third round."},
            {"word": "qualifying round", "ipa": "/ˈkwɒl.ɪ.faɪ.ɪŋ raʊnd/", "meaning": "vòng loại", "example": "She easily passed the qualifying round and reached the semifinals."},
            {"word": "overtime", "ipa": "/ˈəʊ.və.taɪm/", "meaning": "Làm thêm giờ, thời gian làm thêm", "example": "He worked three hours of overtime yesterday."},
            {"word": "underdog", "ipa": "/ˈʌn.də.dɒɡ/", "meaning": "đội/người yếu thế", "example": "The underdog team surprised everyone by beating the champions."},
            {"word": "aggregate score", "ipa": "/ˈæɡ.rɪ.ɡɪt skɔːr/", "meaning": "tổng tỉ số hai lượt", "example": "The aggregate score over both legs was 4-3."},
            {"word": "relegation", "ipa": "/ˌrel.ɪˈɡeɪ.ʃən/", "meaning": "xuống hạng", "example": "The team avoided relegation by winning their last three matches."},
            {"word": "promotion", "ipa": "/prəˈməʊ.ʃən/", "meaning": "thăng hạng", "example": "Winning the second division earned them promotion to the top league."},
            {"word": "squad", "ipa": "/skwɒd/", "meaning": "đội hình cầu thủ", "example": "The national squad was announced ahead of the World Cup."},
            {"word": "fixture", "ipa": "/ˈfɪks.tʃər/", "meaning": "lịch thi đấu", "example": "The fixture list for the new season has been released."},
            {"word": "clean sheet", "ipa": "/kliːn ʃiːt/", "meaning": "không để thủng lưới", "example": "The goalkeeper kept a clean sheet throughout the tournament."},
            {"word": "hat-trick", "ipa": "/ˈhæt.trɪk/", "meaning": "ghi ba bàn thắng trong một trận", "example": "He scored a hat-trick in just 20 minutes."},
            {"word": "offsides trap", "ipa": "/ˈɒf.saɪdz træp/", "meaning": "bẫy việt vị", "example": "The defenders set an offsides trap to catch the striker."},
            {"word": "possession", "ipa": "/pəˈzeʃ.ən/", "meaning": "sự kiểm soát bóng", "example": "The home team had 65% ball possession during the match."},
            {"word": "counterattack", "ipa": "/ˌkaʊn.tərəˈtæk/", "meaning": "phản công", "example": "They scored on a quick counterattack after winning the ball back."},
            {"word": "set piece", "ipa": "/set piːs/", "meaning": "tình huống cố định (phạt góc, phạt trực tiếp)", "example": "Their coach has developed effective set piece routines."},
            {"word": "injury time", "ipa": "/ˈɪn.dʒər.i taɪm/", "meaning": "giờ bù giờ", "example": "The winning goal was scored in injury time."},
            {"word": "debut", "ipa": "/ˈdeɪ.bjuː/", "meaning": "lần ra sân/thi đấu đầu tiên", "example": "She made her international debut at the age of 17."},
            {"word": "veteran", "ipa": "/ˈvet.ər.ən/", "meaning": "cầu thủ kỳ cựu", "example": "The veteran midfielder brought experience and leadership to the team."},
            {"word": "personal best", "ipa": "/ˈpɜː.sən.əl best/", "meaning": "thành tích cá nhân tốt nhất", "example": "She ran a personal best in the 1500m race."},
            {"word": "sports nutrition", "ipa": "/spɔːts njuːˈtrɪʃ.ən/", "meaning": "dinh dưỡng thể thao", "example": "Proper sports nutrition helps athletes recover faster after training."},
            {"word": "physiotherapy", "ipa": "/ˌfɪz.i.əʊˈθer.ə.pi/", "meaning": "vật lý trị liệu", "example": "He needed physiotherapy to recover from his hamstring injury."},
            {"word": "scouting", "ipa": "/ˈskaʊ.tɪŋ/", "meaning": "tìm kiếm tài năng", "example": "The club's scouting network identified young talent from across the country."},
            {"word": "transfer fee", "ipa": "/ˈtræns.fər fiː/", "meaning": "phí chuyển nhượng", "example": "The transfer fee for the striker was a record $100 million."},
            {"word": "contract extension", "ipa": "/ˈkɒn.trækt ɪkˈsten.ʃən/", "meaning": "gia hạn hợp đồng", "example": "The club offered the captain a contract extension for two more years."},
            {"word": "concede", "ipa": "/kənˈsiːd/", "meaning": "thủng lưới; để thua", "example": "The team conceded three goals in the second half."},
            {"word": "attacking midfielder", "ipa": "/əˈtæk.ɪŋ ˈmɪd.fiːl.dər/", "meaning": "tiền vệ tấn công", "example": "The attacking midfielder created most of the team's scoring opportunities."},
            {"word": "defensive line", "ipa": "/dɪˈfen.sɪv laɪn/", "meaning": "hàng phòng thủ", "example": "Their defensive line was solid throughout the tournament."},
            {"word": "free kick", "ipa": "/ˈfriː kɪk/", "meaning": "đá phạt trực tiếp", "example": "He curled the free kick into the top corner."},
            {"word": "corner kick", "ipa": "/ˈkɔː.nər kɪk/", "meaning": "phạt góc", "example": "She swung in a dangerous corner kick that led to a goal."},
            {"word": "offside", "ipa": "/ˌɒfˈsaɪd/", "meaning": "việt vị", "example": "The goal was ruled out due to an offside decision."},
            {"word": "yellow card", "ipa": "/ˈjel.əʊ kɑːd/", "meaning": "thẻ vàng", "example": "The player received a yellow card for a reckless tackle."},
            {"word": "red card", "ipa": "/red kɑːd/", "meaning": "thẻ đỏ", "example": "He was shown a red card and sent off in the 70th minute."},
            {"word": "extra time", "ipa": "/ˈek.strə taɪm/", "meaning": "hiệp phụ", "example": "The match went into extra time after 90 minutes."},
            {"word": "penalty shootout", "ipa": "/ˈpen.əl.ti ˈʃuː.taʊt/", "meaning": "loạt sút phạt đền", "example": "England were eliminated in a penalty shootout."},
            {"word": "formation", "ipa": "/fɔːˈmeɪ.ʃən/", "meaning": "đội hình chiến thuật", "example": "The coach switched to a 4-3-3 formation for the second half."},
            {"word": "pressing", "ipa": "/ˈpres.ɪŋ/", "meaning": "chiến thuật pressing", "example": "High pressing forces opponents to make mistakes in their own half."},
            {"word": "tiki-taka", "ipa": "/ˌtɪk.iˈtɑː.kə/", "meaning": "phong cách chơi trao đổi bóng ngắn liên tục", "example": "Barcelona's tiki-taka style dominated world football for a decade."},
            {"word": "sweeper", "ipa": "/ˈswiː.pər/", "meaning": "hậu vệ quét (libero)", "example": "The sweeper is positioned behind the defensive line to cover mistakes."},
            {"word": "winger", "ipa": "/ˈwɪŋ.ər/", "meaning": "cầu thủ chạy cánh", "example": "The winger's pace and dribbling caused constant problems for defenders."},
            {"word": "striker", "ipa": "/ˈstraɪ.kər/", "meaning": "tiền đạo trung tâm", "example": "The striker scored 30 goals this season."},
            {"word": "man-to-man marking", "ipa": "/mæn tə mæn ˈmɑː.kɪŋ/", "meaning": "kèm người", "example": "The coach employed man-to-man marking to neutralize the opposition's star player."},
            {"word": "throw-in", "ipa": "/ˈθrəʊ.ɪn/", "meaning": "ném biên", "example": "The throw-in was taken quickly to maintain the team's momentum."},
            {"word": "header", "ipa": "/ˈhed.ər/", "meaning": "cú đánh đầu", "example": "He scored with a powerful header from a corner kick."},
            {"word": "pace", "ipa": "/peɪs/", "meaning": "tốc độ", "example": "The winger's pace was too much for the defenders to handle."},
            {"word": "agility", "ipa": "/əˈdʒɪl.ɪ.ti/", "meaning": "sự linh hoạt, nhanh nhẹn", "example": "Agility drills help footballers change direction quickly."},
            {"word": "muscle cramp", "ipa": "/ˈmʌs.əl kræmp/", "meaning": "chuột rút", "example": "He had to leave the field due to a muscle cramp."},
            {"word": "training camp", "ipa": "/ˈtreɪ.nɪŋ kæmp/", "meaning": "trại tập huấn", "example": "The national team held a training camp before the World Cup qualifiers."},
        ],
        "B2": [
            {"word": "doping", "ipa": "/ˈdəʊ.pɪŋ/", "meaning": "dùng chất kích thích trong thể thao", "example": "The athlete was banned for two years after testing positive for doping."},
            {"word": "biomechanics", "ipa": "/ˌbaɪ.əʊ.mɪˈkæn.ɪks/", "meaning": "cơ sinh học", "example": "Biomechanics analysis helps athletes optimize their running technique."},
            {"word": "sports psychology", "ipa": "/spɔːts saɪˈkɒl.ə.dʒi/", "meaning": "tâm lý học thể thao", "example": "Sports psychology helps athletes manage pressure and improve focus."},
            {"word": "periodization", "ipa": "/ˌpɪər.i.ə.daɪˈzeɪ.ʃən/", "meaning": "lập kế hoạch chu kỳ luyện tập", "example": "Periodization divides training into specific phases to peak at the right time."},
            {"word": "anthropometry", "ipa": "/ˌæn.θrəˈpɒm.ɪ.tri/", "meaning": "đo nhân trắc học", "example": "Anthropometry measures an athlete's body dimensions to optimize performance."},
            {"word": "overtraining syndrome", "ipa": "/ˌəʊ.vəˈtreɪ.nɪŋ ˈsɪn.drəʊm/", "meaning": "hội chứng tập luyện quá mức", "example": "Overtraining syndrome leads to performance decline and chronic fatigue."},
            {"word": "lactate threshold", "ipa": "/ˈlæk.teɪt ˈθreʃ.həʊld/", "meaning": "ngưỡng axit lactic", "example": "Training at the lactate threshold improves endurance capacity."},
            {"word": "concussion", "ipa": "/kənˈkʌʃ.ən/", "meaning": "chấn thương não", "example": "He suffered a concussion and was substituted immediately."},
            {"word": "ligament tear", "ipa": "/ˈlɪɡ.ə.mənt teər/", "meaning": "đứt dây chằng", "example": "A ligament tear kept him out of the game for six months."},
            {"word": "sports analytics", "ipa": "/spɔːts ˌæn.əˈlɪt.ɪks/", "meaning": "phân tích dữ liệu thể thao", "example": "Sports analytics uses data to improve team tactics and player performance."},
            {"word": "wearable technology", "ipa": "/ˈweər.ə.bəl tekˈnɒl.ə.dʒi/", "meaning": "công nghệ đeo trên người", "example": "Wearable technology tracks heart rate and distance during training."},
            {"word": "biomechanical analysis", "ipa": "/ˌbaɪ.əʊ.mɪˈkæn.ɪ.kəl əˈnæl.ɪ.sɪs/", "meaning": "phân tích cơ sinh học", "example": "Biomechanical analysis helped the swimmer improve her stroke technique."},
            {"word": "altitude training", "ipa": "/ˈæl.tɪ.tjuːd ˈtreɪ.nɪŋ/", "meaning": "tập luyện ở độ cao", "example": "Altitude training increases red blood cell production and oxygen capacity."},
            {"word": "sprint interval training", "ipa": "/sprɪnt ˈɪn.tə.vəl ˈtreɪ.nɪŋ/", "meaning": "tập luyện cường độ cao ngắt quãng", "example": "Sprint interval training is very effective for improving cardiovascular fitness."},
            {"word": "functional movement screening", "ipa": "/ˈfʌŋk.ʃən.əl ˈmuːv.mənt ˈskriː.nɪŋ/", "meaning": "kiểm tra chuyển động chức năng", "example": "Functional movement screening identifies injury risk factors in athletes."},
            {"word": "performance enhancement", "ipa": "/pəˈfɔː.məns ɪnˈhɑːns.mənt/", "meaning": "nâng cao thành tích", "example": "Performance enhancement techniques include mental visualization and strength training."},
            {"word": "video analysis", "ipa": "/ˈvɪd.i.əʊ əˈnæl.ɪ.sɪs/", "meaning": "phân tích video", "example": "The coach used video analysis to review the team's defensive errors."},
            {"word": "offseason training", "ipa": "/ˈɒf.siː.zən ˈtreɪ.nɪŋ/", "meaning": "tập luyện ngoài mùa giải", "example": "Offseason training is crucial for maintaining fitness and developing new skills."},
            {"word": "hamstring injury", "ipa": "/ˈhæm.strɪŋ ˈɪn.dʒər.i/", "meaning": "chấn thương gân kheo", "example": "He suffered a hamstring injury while sprinting and had to leave the pitch."},
            {"word": "match fitness", "ipa": "/mætʃ ˈfɪt.nəs/", "meaning": "thể lực thi đấu", "example": "The player needed several weeks to regain his match fitness after injury."},
            {"word": "tactical flexibility", "ipa": "/ˈtæk.tɪ.kəl ˌflek.sɪˈbɪl.ɪ.ti/", "meaning": "linh hoạt chiến thuật", "example": "Tactical flexibility allows teams to adapt to different opponents."},
            {"word": "sports medicine", "ipa": "/spɔːts ˈmed.ɪ.sɪn/", "meaning": "y học thể thao", "example": "Sports medicine specialists help athletes recover from injuries faster."},
            {"word": "recovery protocol", "ipa": "/rɪˈkʌv.ər.i ˈprəʊ.tə.kɒl/", "meaning": "quy trình phục hồi", "example": "The team follows a strict recovery protocol after every match."},
            {"word": "player tracking", "ipa": "/ˈpleɪ.ər ˈtræk.ɪŋ/", "meaning": "theo dõi cầu thủ", "example": "Player tracking systems measure distance covered and sprint speed."},
            {"word": "technical director", "ipa": "/ˈtek.nɪ.kəl daɪˈrek.tər/", "meaning": "giám đốc kỹ thuật", "example": "The technical director oversees youth development and coaching standards."},
            {"word": "pre-season", "ipa": "/ˌpriːˈsiː.zən/", "meaning": "giai đoạn tiền mùa giải", "example": "The team went on a pre-season tour to Asia."},
            {"word": "athlete sponsorship", "ipa": "/ˈæθ.liːt ˈspɒn.sər.ʃɪp/", "meaning": "tài trợ cho vận động viên", "example": "She secured an athlete sponsorship deal worth two million dollars."},
            {"word": "drug testing", "ipa": "/drʌɡ ˈtes.tɪŋ/", "meaning": "kiểm tra doping", "example": "Random drug testing helps keep sport clean and fair."},
            {"word": "anti-doping agency", "ipa": "/ˌæn.tiˈdəʊ.pɪŋ ˈeɪ.dʒən.si/", "meaning": "cơ quan chống doping", "example": "The anti-doping agency conducted tests at the international competition."},
            {"word": "sports governance", "ipa": "/spɔːts ˈɡʌv.ən.əns/", "meaning": "quản trị thể thao", "example": "Good sports governance ensures fair competition and transparency."},
            {"word": "talent identification", "ipa": "/ˈtæl.ənt aɪˌden.tɪ.fɪˈkeɪ.ʃən/", "meaning": "nhận diện tài năng", "example": "Talent identification programs spot promising athletes at an early age."},
            {"word": "proprioception", "ipa": "/ˌprəʊ.pri.əˈsep.ʃən/", "meaning": "cảm nhận vị trí cơ thể", "example": "Good proprioception helps athletes maintain balance during dynamic movements."},
            {"word": "plyometrics", "ipa": "/ˌplaɪ.əˈmet.rɪks/", "meaning": "tập luyện nhảy bật", "example": "Plyometrics training improves explosive power in sprinters."},
            {"word": "anaerobic threshold", "ipa": "/ˌæn.eər.ˈəʊ.bɪk ˈθreʃ.həʊld/", "meaning": "ngưỡng yếm khí", "example": "Pushing past the anaerobic threshold leads to rapid fatigue."},
            {"word": "neuromuscular coordination", "ipa": "/ˌnjʊər.əʊˈmʌs.kjʊ.lər kəʊˌɔː.dɪˈneɪ.ʃən/", "meaning": "phối hợp thần kinh cơ", "example": "Good neuromuscular coordination allows precise and powerful movements."},
            {"word": "heat acclimatization", "ipa": "/hiːt əˌklaɪ.mə.taɪˈzeɪ.ʃən/", "meaning": "thích nghi với nhiệt độ cao", "example": "Heat acclimatization training prepares athletes for competitions in hot climates."},
            {"word": "reactive strength", "ipa": "/riˈæk.tɪv streŋθ/", "meaning": "sức mạnh phản xạ", "example": "Reactive strength is important for quick changes of direction in team sports."},
            {"word": "force plate analysis", "ipa": "/fɔːs pleɪt əˈnæl.ɪ.sɪs/", "meaning": "phân tích bàn lực", "example": "Force plate analysis measures ground reaction forces during jumping."},
            {"word": "oxygen uptake", "ipa": "/ˈɒk.sɪ.dʒən ˈʌp.teɪk/", "meaning": "hấp thụ oxy (VO2)", "example": "Maximum oxygen uptake is a key measure of aerobic fitness."},
            {"word": "anthropometric testing", "ipa": "/ˌæn.θrəˌpɒmˈet.rɪk ˈtes.tɪŋ/", "meaning": "kiểm tra nhân trắc học", "example": "Anthropometric testing assesses body composition in elite athletes."},
            {"word": "velocity-based training", "ipa": "/vɪˈlɒs.ɪ.ti beɪst ˈtreɪ.nɪŋ/", "meaning": "tập luyện theo tốc độ", "example": "Velocity-based training monitors bar speed to optimize strength gains."},
            {"word": "myofascial release", "ipa": "/ˌmaɪ.əʊˈfæʃ.i.əl rɪˈliːs/", "meaning": "giải phóng mô cơ", "example": "Myofascial release techniques help reduce muscle stiffness after training."},
            {"word": "eccentric loading", "ipa": "/ɪkˈsen.trɪk ˈləʊ.dɪŋ/", "meaning": "tải trọng lệch tâm", "example": "Eccentric loading exercises strengthen tendons and prevent injuries."},
            {"word": "deload week", "ipa": "/ˈdiː.ləʊd wiːk/", "meaning": "tuần giảm tải", "example": "A deload week allows the body to recover from accumulated training stress."},
            {"word": "high-performance center", "ipa": "/haɪ pəˈfɔː.məns ˈsen.tər/", "meaning": "trung tâm thể thao hiệu suất cao", "example": "The high-performance center uses advanced technology to optimize athlete development."},
            {"word": "tactical periodization", "ipa": "/ˈtæk.tɪ.kəl ˌpɪər.i.ə.daɪˈzeɪ.ʃən/", "meaning": "lập lịch theo chiến thuật", "example": "Tactical periodization integrates game principles into every training session."},
            {"word": "match analysis software", "ipa": "/mætʃ əˈnæl.ɪ.sɪs ˈsɒft.weər/", "meaning": "phần mềm phân tích trận đấu", "example": "Match analysis software helps coaches prepare detailed tactical reports."},
            {"word": "conditioning coach", "ipa": "/kənˈdɪʃ.ən.ɪŋ kəʊtʃ/", "meaning": "huấn luyện viên thể lực", "example": "The conditioning coach designs fitness programs for the entire squad."},
            {"word": "game intelligence", "ipa": "/ɡeɪm ɪnˈtel.ɪ.dʒəns/", "meaning": "hiểu biết chiến thuật trên sân", "example": "Game intelligence allows experienced players to read situations quickly."},
            {"word": "mental toughness", "ipa": "/ˈmen.təl ˈtʌf.nəs/", "meaning": "sức mạnh tinh thần", "example": "Mental toughness separates elite athletes from good ones under pressure."},
        ],
        "C1": [
            {"word": "kinaesthesia", "ipa": "/ˌkɪn.esˈθiː.zi.ə/", "meaning": "cảm giác vận động cơ thể", "example": "Kinaesthesia allows athletes to sense body position without looking."},
            {"word": "ergogenic aids", "ipa": "/ˌɜː.ɡəˈdʒen.ɪk eɪdz/", "meaning": "chất/biện pháp tăng cường hiệu suất", "example": "Legal ergogenic aids include caffeine, creatine, and carbohydrate loading."},
            {"word": "calisthenics", "ipa": "/ˌkæl.ɪsˈθen.ɪks/", "meaning": "thể dục tự do không dụng cụ", "example": "Calisthenics builds functional strength using only bodyweight exercises."},
            {"word": "sport-specific conditioning", "ipa": "/spɔːt spɪˈsɪf.ɪk kənˈdɪʃ.ən.ɪŋ/", "meaning": "điều kiện thể chất đặc thù từng môn", "example": "Sport-specific conditioning prepares athletes for the unique demands of their sport."},
            {"word": "neurocognitive training", "ipa": "/ˌnjʊər.əʊˈkɒɡ.nɪ.tɪv ˈtreɪ.nɪŋ/", "meaning": "huấn luyện thần kinh nhận thức", "example": "Neurocognitive training improves reaction time and decision-making on the field."},
            {"word": "isokinetic testing", "ipa": "/ˌaɪ.səʊ.kɪˈnet.ɪk ˈtes.tɪŋ/", "meaning": "kiểm tra sức mạnh đẳng động học", "example": "Isokinetic testing measures muscle strength at controlled speeds of movement."},
            {"word": "tendinopathy", "ipa": "/ˌten.dɪˈnɒp.ə.θi/", "meaning": "bệnh lý gân", "example": "Tendinopathy in the Achilles tendon is common in distance runners."},
            {"word": "rhabdomyolysis", "ipa": "/ˌræb.dəʊ.maɪˈɒl.ɪ.sɪs/", "meaning": "tiêu cơ vân", "example": "Severe overtraining can lead to rhabdomyolysis, a dangerous breakdown of muscle tissue."},
            {"word": "gene doping", "ipa": "/dʒiːn ˈdəʊ.pɪŋ/", "meaning": "doping gen", "example": "Gene doping is banned but increasingly difficult to detect."},
            {"word": "sports biomechatronics", "ipa": "/spɔːts ˌbaɪ.əʊ.mekəˈtrɒn.ɪks/", "meaning": "cơ điện tử sinh học thể thao", "example": "Sports biomechatronics combines engineering and biology to design prosthetics for para-athletes."},
            {"word": "stochastic resonance", "ipa": "/stəˈkæs.tɪk ˈrez.ə.nəns/", "meaning": "cộng hưởng ngẫu nhiên", "example": "Stochastic resonance training uses mild vibration to improve balance in athletes."},
            {"word": "motor learning theory", "ipa": "/ˈməʊ.tər ˈlɜː.nɪŋ ˈθɪər.i/", "meaning": "lý thuyết học vận động", "example": "Motor learning theory guides how coaches teach technical skills to athletes."},
            {"word": "detraining effect", "ipa": "/diːˈtreɪ.nɪŋ ɪˈfekt/", "meaning": "tác động của ngừng luyện tập", "example": "The detraining effect can cause significant fitness loss within two weeks."},
            {"word": "cortisol response", "ipa": "/ˈkɔː.tɪ.sɒl rɪˈspɒns/", "meaning": "phản ứng cortisol", "example": "Monitoring cortisol response helps coaches avoid overtraining in athletes."},
            {"word": "parasympathetic recovery", "ipa": "/ˌpær.ə.sɪmˌpæθ.ə.tɪk rɪˈkʌv.ər.i/", "meaning": "phục hồi phó giao cảm", "example": "Parasympathetic recovery techniques like meditation reduce post-exercise stress hormones."},
            {"word": "sport-induced immunosuppression", "ipa": "/spɔːt ɪnˈdjuːst ɪˌmjuː.nəʊ.səˈpreʃ.ən/", "meaning": "suy giảm miễn dịch do thể thao", "example": "Intense exercise can cause sport-induced immunosuppression, increasing infection risk."},
            {"word": "delayed onset muscle soreness", "ipa": "/dɪˈleɪd ˈɒn.set ˈmʌs.əl ˈsɔː.nəs/", "meaning": "đau cơ khởi phát muộn", "example": "Delayed onset muscle soreness typically peaks 24-72 hours after intense exercise."},
            {"word": "glycogen depletion", "ipa": "/ˈɡlaɪ.kə.dʒən dɪˈpliː.ʃən/", "meaning": "cạn kiệt glycogen", "example": "Glycogen depletion causes fatigue in endurance athletes during long races."},
            {"word": "tendon stiffness adaptation", "ipa": "/ˈten.dən ˈstɪf.nəs ˌæd.æpˈteɪ.ʃən/", "meaning": "thích nghi độ cứng gân", "example": "Tendon stiffness adaptation improves force transmission in trained athletes."},
            {"word": "high-intensity interval training", "ipa": "/haɪ ɪnˈten.sɪ.ti ˈɪn.tə.vəl ˈtreɪ.nɪŋ/", "meaning": "tập luyện cường độ cao ngắt quãng", "example": "High-intensity interval training is very effective for improving cardiovascular fitness."},
            {"word": "electromyography", "ipa": "/ɪˌlek.trəʊ.maɪˈɒɡ.rə.fi/", "meaning": "điện cơ đồ", "example": "Electromyography measures electrical activity in muscles during movement."},
            {"word": "force-velocity relationship", "ipa": "/fɔːs vɪˈlɒs.ɪ.ti rɪˈleɪ.ʃən.ʃɪp/", "meaning": "mối quan hệ lực-tốc độ", "example": "Understanding the force-velocity relationship is key to power development."},
            {"word": "intermittent hypoxic training", "ipa": "/ˌɪn.təˈmɪt.ənt haɪˈpɒk.sɪk ˈtreɪ.nɪŋ/", "meaning": "tập luyện thiếu oxy ngắt quãng", "example": "Intermittent hypoxic training simulates altitude conditions to boost endurance."},
            {"word": "postactivation potentiation", "ipa": "/pəʊstˌæk.tɪˈveɪ.ʃən pəˌten.ʃiˈeɪ.ʃən/", "meaning": "tăng cường hoạt hóa sau kích thích", "example": "Postactivation potentiation uses heavy lifts to enhance subsequent explosive movements."},
            {"word": "mental imagery", "ipa": "/ˈmen.təl ˈɪm.ɪ.dʒər.i/", "meaning": "hình dung tinh thần", "example": "Athletes use mental imagery to mentally rehearse perfect performances."},
            {"word": "psychological periodization", "ipa": "/ˌsaɪ.kəˈlɒdʒ.ɪ.kəl ˌpɪər.i.ə.daɪˈzeɪ.ʃən/", "meaning": "lập kế hoạch tâm lý theo chu kỳ", "example": "Psychological periodization schedules mental skills training alongside physical preparation."},
            {"word": "reactive neuromuscular training", "ipa": "/riˈæk.tɪv ˌnjʊər.əʊˈmʌs.kjʊ.lər ˈtreɪ.nɪŋ/", "meaning": "tập luyện thần kinh cơ phản xạ", "example": "Reactive neuromuscular training improves an athlete's ability to respond to unpredictable stimuli."},
            {"word": "epigenetic adaptation", "ipa": "/ˌep.ɪ.dʒɪˈnet.ɪk ˌæd.æpˈteɪ.ʃən/", "meaning": "thích nghi biểu sinh học", "example": "Epigenetic adaptation to exercise can influence gene expression in athletes."},
            {"word": "cardiometabolic fitness", "ipa": "/ˌkɑː.di.əʊˌmet.əˈbɒl.ɪk ˈfɪt.nəs/", "meaning": "thể lực tim mạch chuyển hóa", "example": "High cardiometabolic fitness reduces the risk of chronic disease."},
            {"word": "load management", "ipa": "/ləʊd ˈmæn.ɪdʒ.mənt/", "meaning": "quản lý tải luyện tập", "example": "Load management prevents overuse injuries in professional athletes."},
            {"word": "perceptual-motor skills", "ipa": "/pəˈsep.tju.əl ˈməʊ.tər skɪlz/", "meaning": "kỹ năng nhận thức-vận động", "example": "Perceptual-motor skills allow athletes to respond effectively to game situations."},
            {"word": "sport-specific agility", "ipa": "/spɔːt spɪˈsɪf.ɪk əˈdʒɪl.ɪ.ti/", "meaning": "sự nhanh nhẹn đặc thù môn thể thao", "example": "Sport-specific agility drills mimic the movement demands of actual competition."},
            {"word": "metabolic conditioning", "ipa": "/ˌmet.əˈbɒl.ɪk kənˈdɪʃ.ən.ɪŋ/", "meaning": "điều kiện hóa chuyển hóa", "example": "Metabolic conditioning workouts improve energy system efficiency."},
            {"word": "prehabilitation", "ipa": "/ˌpriː.həˌbɪl.ɪˈteɪ.ʃən/", "meaning": "phục hồi phòng ngừa trước chấn thương", "example": "Prehabilitation exercises reduce the risk of common sports injuries."},
            {"word": "eccentric overload training", "ipa": "/ɪkˈsen.trɪk ˈəʊ.və.ləʊd ˈtreɪ.nɪŋ/", "meaning": "tập luyện quá tải lệch tâm", "example": "Eccentric overload training is highly effective for increasing muscle hypertrophy."},
            {"word": "resisted sprint training", "ipa": "/rɪˈzɪs.tɪd sprɪnt ˈtreɪ.nɪŋ/", "meaning": "tập luyện chạy nước rút có kháng lực", "example": "Resisted sprint training with parachutes and sleds builds explosive speed."},
            {"word": "hypnotherapy in sport", "ipa": "/ˌhɪp.nəʊˈθer.ə.pi ɪn spɔːt/", "meaning": "liệu pháp thôi miên trong thể thao", "example": "Hypnotherapy in sport can help athletes overcome performance anxiety."},
            {"word": "neurorehabilitation", "ipa": "/ˌnjʊər.əʊ.rɪˌhæb.ɪˈleɪ.ʃən/", "meaning": "phục hồi chức năng thần kinh", "example": "Neurorehabilitation after a concussion helps athletes safely return to play."},
            {"word": "oxidative stress biomarker", "ipa": "/ˈɒk.sɪ.deɪ.tɪv stres ˈbaɪ.əʊˌmɑː.kər/", "meaning": "dấu ấn sinh học stress oxy hóa", "example": "Oxidative stress biomarkers help monitor the physiological impact of intense training."},
            {"word": "thermoregulation", "ipa": "/ˌθɜː.məʊˌreɡ.jʊˈleɪ.ʃən/", "meaning": "điều hòa nhiệt độ cơ thể", "example": "Effective thermoregulation is essential for performance in hot conditions."},
            {"word": "cardiac output", "ipa": "/ˈkɑː.di.æk ˈaʊt.pʊt/", "meaning": "cung lượng tim", "example": "Elite endurance athletes have exceptionally high cardiac output."},
            {"word": "sport pharmacology", "ipa": "/spɔːt ˌfɑː.məˈkɒl.ə.dʒi/", "meaning": "dược lý học thể thao", "example": "Sport pharmacology examines how drugs affect athletic performance and health."},
            {"word": "overreaching", "ipa": "/ˌəʊ.vəˈriː.tʃɪŋ/", "meaning": "tập luyện vượt mức có kiểm soát", "example": "Short-term overreaching can lead to performance gains if followed by adequate recovery."},
            {"word": "sport specialization", "ipa": "/spɔːt ˌspeʃ.əl.aɪˈzeɪ.ʃən/", "meaning": "chuyên hóa sớm trong thể thao", "example": "Early sport specialization may increase injury risk and burnout in young athletes."},
            {"word": "relative energy deficiency in sport", "ipa": "/ˈrel.ə.tɪv ˈen.ə.dʒi dɪˈfɪʃ.ən.si ɪn spɔːt/", "meaning": "thiếu hụt năng lượng tương đối trong thể thao", "example": "Relative energy deficiency in sport is a syndrome common in endurance athletes."},
            {"word": "sport integrity", "ipa": "/spɔːt ɪnˈteɡ.rɪ.ti/", "meaning": "tính liêm chính trong thể thao", "example": "Sport integrity initiatives combat match-fixing and corruption in professional leagues."},
            {"word": "athlete welfare", "ipa": "/ˈæθ.liːt ˈwel.feər/", "meaning": "phúc lợi vận động viên", "example": "Athlete welfare programs address mental health and financial security after retirement."},
            {"word": "flow state", "ipa": "/fləʊ steɪt/", "meaning": "trạng thái nhập tâm tối ưu", "example": "Athletes describe being in a flow state as performing effortlessly and instinctively."},
            {"word": "choking under pressure", "ipa": "/ˈtʃəʊ.kɪŋ ˈʌn.dər ˈpreʃ.ər/", "meaning": "mất bình tĩnh dưới áp lực", "example": "Research into choking under pressure helps coaches prepare athletes for high-stakes moments."},
            {"word": "sport sociology", "ipa": "/spɔːt səˈʃɪ.ɒl.ə.dʒi/", "meaning": "xã hội học thể thao", "example": "Sport sociology examines the relationship between sport and social structures."},
        ],
    },
    "tech": {
        "A1": [
            {"word": "phone", "ipa": "/fəʊn/", "meaning": "điện thoại", "example": "I use my phone to call my friends."},
            {"word": "screen", "ipa": "/skriːn/", "meaning": "màn hình", "example": "The screen on this laptop is very bright."},
            {"word": "camera", "ipa": "/ˈkæm.ər.ə/", "meaning": "máy ảnh, máy quay", "example": "She took a photo with her camera."},
            {"word": "tablet", "ipa": "/ˈtæb.lɪt/", "meaning": "máy tính bảng", "example": "He reads books on his tablet."},
            {"word": "video", "ipa": "/ˈvɪd.i.əʊ/", "meaning": "video, phim", "example": "We watched a funny video online."},
            {"word": "game", "ipa": "/ɡeɪm/", "meaning": "trò chơi", "example": "This game is very popular with children."},
            {"word": "internet", "ipa": "/ˈɪn.tə.net/", "meaning": "mạng Internet", "example": "I need the internet to do my homework."},
            {"word": "email", "ipa": "/ˈiː.meɪl/", "meaning": "thư điện tử", "example": "Please send me an email with the details."},
            {"word": "telephone", "ipa": "/ˈtɛlɪfoʊn/", "meaning": "Điện thoại (cố định)", "example": "He called me on the telephone to confirm the meeting."},
            {"word": "display", "ipa": "/dɪˈspleɪ/", "meaning": "Màn hình hiển thị", "example": "The new phone has a sharp, high-resolution display."},
            {"word": "lens", "ipa": "/lɛnz/", "meaning": "Ống kính máy ảnh; thấu kính", "example": "She bought a new wide-angle lens for her camera."},
            {"word": "pad", "ipa": "/pæd/", "meaning": "Miếng lót, tập giấy ghi chú", "example": "She wrote a note on her notepad."},
            {"word": "clip", "ipa": "/klɪp/", "meaning": "Đoạn video ngắn; kẹp giấy", "example": "She shared a funny clip on social media."},
            {"word": "match", "ipa": "/mæʧ/", "meaning": "Trận đấu; diêm quẹt", "example": "The match between the two teams was exciting."},
            {"word": "net", "ipa": "/nɛt/", "meaning": "Lưới; mạng lưới", "example": "The fisherman cast his net into the sea."},
            {"word": "electronic mail", "ipa": "/ɪˌlɛkˈtrɒnɪk meɪl/", "meaning": "Thư điện tử", "example": "Send me the report by electronic mail."},
        ],
        "A2": [
            {"word": "smartphone", "ipa": "/ˈsmɑːt.fəʊn/", "meaning": "điện thoại thông minh", "example": "Most people have a smartphone these days."},
            {"word": "battery", "ipa": "/ˈbæt.ər.i/", "meaning": "pin", "example": "My battery is low, I need to charge my phone."},
            {"word": "download", "ipa": "/ˌdaʊnˈləʊd/", "meaning": "tải xuống", "example": "You can download the app for free."},
            {"word": "website", "ipa": "/ˈweb.saɪt/", "meaning": "trang web", "example": "Visit our website for more information."},
            {"word": "password", "ipa": "/ˈpɑːs.wɜːd/", "meaning": "mật khẩu", "example": "Don't share your password with anyone."},
            {"word": "update", "ipa": "/ʌpˈdeɪt/", "meaning": "cập nhật", "example": "You should update your software regularly."},
            {"word": "connect", "ipa": "/kəˈnekt/", "meaning": "kết nối", "example": "I can't connect to the Wi-Fi network."},
            {"word": "message", "ipa": "/ˈmes.ɪdʒ/", "meaning": "tin nhắn", "example": "She sent me a message on social media."},
            {"word": "mobile", "ipa": "/ˈmoʊbəl/", "meaning": "Điện thoại di động", "example": "She checked her messages on her mobile."},
            {"word": "power cell", "ipa": "/ˈpaʊər sɛl/", "meaning": "Pin, nguồn điện dự phòng", "example": "This device uses a rechargeable power cell."},
            {"word": "fetch", "ipa": "/fɛʧ/", "meaning": "Lấy về, tải về", "example": "The browser will fetch the data from the server."},
            {"word": "site", "ipa": "/saɪt/", "meaning": "Địa điểm; trang web", "example": "We visited the historic site in the city center."},
            {"word": "passcode", "ipa": "/ˈpæsˌkoʊd/", "meaning": "Mã PIN, mật khẩu số", "example": "Enter your passcode to unlock the phone."},
            {"word": "upgrade", "ipa": "/ˈʌpˌɡreɪd/", "meaning": "Nâng cấp lên phiên bản mới hơn", "example": "It's time to upgrade your computer's operating system."},
            {"word": "link", "ipa": "/lɪŋk/", "meaning": "Liên kết, đường dẫn", "example": "Click the link to visit the website."},
            {"word": "text", "ipa": "/tɛkst/", "meaning": "Tin nhắn văn bản; văn bản", "example": "She sent a text to her friend after the meeting."},
        ],
        "B1": [
            {"word": "innovation", "ipa": "/ˌɪn.əˈveɪ.ʃən/", "meaning": "sự đổi mới, sáng tạo", "example": "Innovation drives the technology industry forward."},
            {"word": "bandwidth", "ipa": "/ˈbænd.wɪdθ/", "meaning": "băng thông", "example": "We need more bandwidth to stream high-quality videos."},
            {"word": "cybersecurity", "ipa": "/ˌsaɪ.bə.sɪˈkjʊə.rə.ti/", "meaning": "an ninh mạng", "example": "Cybersecurity is essential for protecting personal data."},
            {"word": "cloud computing", "ipa": "/klaʊd kəmˈpjuː.tɪŋ/", "meaning": "điện toán đám mây", "example": "Many companies use cloud computing to store their data."},
            {"word": "virtual reality", "ipa": "/ˌvɜː.tʃu.əl riˈæl.ə.ti/", "meaning": "thực tế ảo", "example": "Virtual reality games make you feel like you are inside the game."},
            {"word": "wearable", "ipa": "/ˈweə.rə.bəl/", "meaning": "thiết bị đeo được", "example": "Smartwatches are the most common type of wearable technology."},
            {"word": "streaming", "ipa": "/ˈstriː.mɪŋ/", "meaning": "phát trực tuyến", "example": "Music streaming services have changed how we listen to songs."},
            {"word": "gadget", "ipa": "/ˈgæʤət/", "meaning": "thiết bị điện tử nhỏ", "example": "He loves buying the latest gadgets from tech stores."},
            {"word": "invention", "ipa": "/ˌɪn.əˈveɪ.ʃən/", "meaning": "sự đổi mới, sáng tạo", "example": "Innovation drives the technology industry forward."},
            {"word": "capacity", "ipa": "/kəˈpæsɪti/", "meaning": "Dung lượng; năng lực", "example": "The hard drive has a storage capacity of 1 terabyte."},
            {"word": "IT security", "ipa": "/ˌaɪˈtiː sɪˈkjʊərɪti/", "meaning": "Bảo mật hệ thống công nghệ thông tin", "example": "IT security teams protect company data from cyberattacks."},
            {"word": "cloud tech", "ipa": "/klaʊd kəmˈpjuː.tɪŋ/", "meaning": "điện toán đám mây", "example": "Many companies use cloud computing to store their data."},
            {"word": "VR", "ipa": "/ˌvɜː.tʃu.əl riˈæl.ə.ti/", "meaning": "thực tế ảo", "example": "Virtual reality games make you feel like you are inside the game."},
            {"word": "smart tech", "ipa": "/smɑːrt tɛk/", "meaning": "Công nghệ thông minh", "example": "Wearable smart tech can monitor your heart rate and steps."},
            {"word": "broadcasting", "ipa": "/ˈbrɔːdkɑːstɪŋ/", "meaning": "Phát sóng, truyền hình/phát thanh", "example": "The live broadcasting of the match attracted millions of viewers."},
            {"word": "device", "ipa": "/dɪˈvaɪs/", "meaning": "Thiết bị điện tử", "example": "Every device in the smart home is connected to the internet."},
        ],
        "B2": [
            {"word": "augmented reality", "ipa": "/ɔːɡˌmen.tɪd riˈæl.ə.ti/", "meaning": "thực tế tăng cường", "example": "Augmented reality overlays digital information onto the real world."},
            {"word": "blockchain", "ipa": "/ˈblɒk.tʃeɪn/", "meaning": "chuỗi khối", "example": "Blockchain technology ensures secure and transparent transactions."},
            {"word": "quantum computing", "ipa": "/ˌkwɒn.təm kəmˈpjuː.tɪŋ/", "meaning": "điện toán lượng tử", "example": "Quantum computing could revolutionize drug discovery and cryptography."},
            {"word": "biometrics", "ipa": "/ˌbaɪ.əʊˈmet.rɪks/", "meaning": "sinh trắc học", "example": "Biometrics such as fingerprint scanning improve device security."},
            {"word": "IoT", "ipa": "/ˌaɪ.əʊˈtiː/", "meaning": "Internet vạn vật", "example": "IoT devices can automate many tasks in a smart home."},
            {"word": "encryption", "ipa": "/ɪnˈkrɪp.ʃən/", "meaning": "mã hóa", "example": "End-to-end encryption protects your messages from being intercepted."},
            {"word": "scalability", "ipa": "/ˌskeɪ.ləˈbɪl.ə.ti/", "meaning": "khả năng mở rộng", "example": "Scalability is a key factor when choosing a cloud platform."},
            {"word": "microchip", "ipa": "/ˈmaɪ.krəʊ.tʃɪp/", "meaning": "vi mạch", "example": "Modern microchips contain billions of transistors."},
            {"word": "AR", "ipa": "/ɑr/", "meaning": "thực tế tăng cường", "example": "Augmented reality overlays digital information onto the real world."},
            {"word": "distributed ledger", "ipa": "/dɪˈstrɪbjətəd ˈlɛʤər/", "meaning": "chuỗi khối", "example": "Blockchain technology ensures secure and transparent transactions."},
            {"word": "quantum tech", "ipa": "/ˌkwɒn.təm kəmˈpjuː.tɪŋ/", "meaning": "điện toán lượng tử", "example": "Quantum computing could revolutionize drug discovery and cryptography."},
            {"word": "biometric scanning", "ipa": "/ˌbaɪ.əʊˈmet.rɪks/", "meaning": "sinh trắc học", "example": "Biometrics such as fingerprint scanning improve device security."},
            {"word": "Internet of Things", "ipa": "/ˈɪntərˌnɛt əv θɪŋz/", "meaning": "Internet vạn vật", "example": "IoT devices can automate many tasks in a smart home."},
            {"word": "cryptography", "ipa": "/ɪnˈkrɪp.ʃən/", "meaning": "mã hóa", "example": "End-to-end encryption protects your messages from being intercepted."},
            {"word": "adaptability", "ipa": "/ˌskeɪ.ləˈbɪl.ə.ti/", "meaning": "khả năng mở rộng", "example": "Scalability is a key factor when choosing a cloud platform."},
            {"word": "processor", "ipa": "/ˈprɑˌsɛsər/", "meaning": "vi mạch", "example": "Modern microchips contain billions of transistors."},
        ],
        "C1": [
            {"word": "ubiquitous computing", "ipa": "/juːˌbɪk.wɪ.təs kəmˈpjuː.tɪŋ/", "meaning": "điện toán phổ biến khắp nơi", "example": "Ubiquitous computing envisions technology seamlessly embedded in everyday objects."},
            {"word": "disruptive technology", "ipa": "/dɪsˌrʌp.tɪv tekˈnɒl.ə.dʒi/", "meaning": "công nghệ đột phá", "example": "Smartphones were a disruptive technology that transformed the mobile industry."},
            {"word": "nanotechnology", "ipa": "/ˌnæn.əʊ.tekˈnɒl.ə.dʒi/", "meaning": "công nghệ nano", "example": "Nanotechnology has promising applications in medicine and materials science."},
            {"word": "algorithmic bias", "ipa": "/ˌæl.ɡəˌrɪð.mɪk ˈbaɪ.əs/", "meaning": "thiên kiến thuật toán", "example": "Algorithmic bias can lead to unfair outcomes in hiring and lending decisions."},
            {"word": "digital sovereignty", "ipa": "/ˌdɪdʒ.ɪ.təl ˈsɒv.rən.ti/", "meaning": "chủ quyền số", "example": "Many nations are pursuing digital sovereignty to control their own data infrastructure."},
            {"word": "transhumanism", "ipa": "/trænzˈhjuː.mə.nɪ.zəm/", "meaning": "chủ nghĩa siêu nhân học", "example": "Transhumanism explores using technology to enhance human physical and cognitive abilities."},
            {"word": "interoperability", "ipa": "/ˌɪn.tər.ɒp.ər.əˈbɪl.ə.ti/", "meaning": "khả năng tương tác liên hệ thống", "example": "Interoperability between platforms allows different systems to work together smoothly."},
            {"word": "proprietary", "ipa": "/prəˈpraɪ.ə.tər.i/", "meaning": "độc quyền, bản quyền riêng", "example": "The company uses proprietary software that cannot be modified by outside developers."},
            {"word": "pervasive computing", "ipa": "/juːˌbɪk.wɪ.təs kəmˈpjuː.tɪŋ/", "meaning": "điện toán phổ biến khắp nơi", "example": "Ubiquitous computing envisions technology seamlessly embedded in everyday objects."},
            {"word": "groundbreaking tech", "ipa": "/ˈgraʊnˌbreɪkɪŋ tɛk/", "meaning": "công nghệ đột phá", "example": "Smartphones were a disruptive technology that transformed the mobile industry."},
            {"word": "nanotech", "ipa": "/ˌnæn.əʊ.tekˈnɒl.ə.dʒi/", "meaning": "công nghệ nano", "example": "Nanotechnology has promising applications in medicine and materials science."},
            {"word": "AI bias", "ipa": "/ˌæl.ɡəˌrɪð.mɪk ˈbaɪ.əs/", "meaning": "thiên kiến thuật toán", "example": "Algorithmic bias can lead to unfair outcomes in hiring and lending decisions."},
            {"word": "digital autonomy", "ipa": "/ˌdɪdʒ.ɪ.təl ˈsɒv.rən.ti/", "meaning": "chủ quyền số", "example": "Many nations are pursuing digital sovereignty to control their own data infrastructure."},
            {"word": "posthumanism", "ipa": "/trænzˈhjuː.mə.nɪ.zəm/", "meaning": "chủ nghĩa siêu nhân học", "example": "Transhumanism explores using technology to enhance human physical and cognitive abilities."},
            {"word": "compatibility", "ipa": "/ˌɪn.tər.ɒp.ər.əˈbɪl.ə.ti/", "meaning": "khả năng tương tác liên hệ thống", "example": "Interoperability between platforms allows different systems to work together smoothly."},
            {"word": "patented", "ipa": "/ˈpætəntɪd/", "meaning": "độc quyền, bản quyền riêng", "example": "The company uses proprietary software that cannot be modified by outside developers."},
        ],
    },
    "travel": {
        "A1": [
            {"word": "Ticket", "ipa": "/ˈtɪkɪt/", "meaning": "Vé xe/tàu/máy bay", "example": "Please show your ticket at the gate."},
            {"word": "Hotel", "ipa": "/həʊˈtel/", "meaning": "Khách sạn", "example": "We booked a room at the central hotel."},
            {"word": "Bus", "ipa": "/bʌs/", "meaning": "Xe buýt", "example": "I go to school by bus every day."},
            {"word": "Map", "ipa": "/mæp/", "meaning": "Bản đồ", "example": "We need a map to find our way."},
            {"word": "Passport", "ipa": "/ˈpɑːspɔːt/", "meaning": "Hộ chiếu", "example": "Don't forget to pack your passport."},
            {"word": "Fly", "ipa": "/flaɪ/", "meaning": "Bay, đi máy bay", "example": "I will fly to Paris tomorrow."},
            {"word": "Beach", "ipa": "/biːtʃ/", "meaning": "Bãi biển", "example": "We played soccer on the beach."},
            {"word": "Bag", "ipa": "/bæɡ/", "meaning": "Túi xách, ba lô", "example": "Put your camera in the bag."},
            {"word": "Pass", "ipa": "/pɑːs/", "meaning": "Thẻ thông hành, thẻ ra vào", "example": "You must show your security pass to enter."},
            {"word": "Inn", "ipa": "/ɪn/", "meaning": "Quán trọ, nhà nghỉ nhỏ", "example": "We spent the night at a cozy inn near the forest."},
            {"word": "Coach", "ipa": "/kəʊtʃ/", "meaning": "Huấn luyện viên", "example": "She hired a personal coach to improve her tennis skills."},
            {"word": "Atlas", "ipa": "/ˈæt.ləs/", "meaning": "Bản đồ, tập bản đồ", "example": "We need an atlas to find our way."},
            {"word": "Visa", "ipa": "/ˈviːzə/", "meaning": "Thị thực nhập cảnh", "example": "You need a valid visa to enter the United States."},
            {"word": "Travel", "ipa": "/ˈtræv.əl/", "meaning": "Đi du lịch, di chuyển", "example": "I love to travel to new countries."},
            {"word": "Coast", "ipa": "/kəʊst/", "meaning": "Bờ biển", "example": "We played soccer on the coast."},
            {"word": "Luggage", "ipa": "/ˈləgɪʤ/", "meaning": "Hành lý", "example": "They helped me carry my luggage."},
        ],
        "A2": [
            {"word": "Airport", "ipa": "/ˈeəpɔːt/", "meaning": "Sân bay", "example": "We arrived at the airport two hours early."},
            {"word": "Luggage", "ipa": "/ˈləgɪʤ/", "meaning": "Hành lý", "example": "They helped me carry my luggage."},
            {"word": "Journey", "ipa": "/ˈdʒɜːni/", "meaning": "Hành trình dài, chuyến đi", "example": "The journey from Hanoi to Ho Chi Minh City takes about two hours by plane."},
            {"word": "Tourist", "ipa": "/ˈtʊərɪst/", "meaning": "Khách du lịch", "example": "The city is full of tourists in summer."},
            {"word": "Flight", "ipa": "/flaɪt/", "meaning": "Chuyến bay", "example": "Our flight was delayed for three hours."},
            {"word": "Station", "ipa": "/ˈsteɪʃn/", "meaning": "Nhà ga, trạm", "example": "Let's meet at the train station."},
            {"word": "Guide", "ipa": "/ɡaɪd/", "meaning": "Hướng dẫn viên, sách hướng dẫn", "example": "Our tour guide was very knowledgeable."},
            {"word": "Souvenir", "ipa": "/ˌsuːvəˈnɪə(r)/", "meaning": "Quà lưu niệm", "example": "She bought a small souvenir from Rome."},
            {"word": "Aerodrome", "ipa": "/ˈɛrəˌdroʊm/", "meaning": "Sân bay", "example": "We arrived at the airport two hours early."},
            {"word": "Baggage", "ipa": "/ˈbægɪʤ/", "meaning": "Hành lý", "example": "They lost my luggage on the flight."},
            {"word": "Voyage", "ipa": "/vɔɪəʤ/", "meaning": "Hành trình, chuyến đi", "example": "Learning English is a journey."},
            {"word": "Visitor", "ipa": "/ˈvɪzɪtər/", "meaning": "Khách du lịch", "example": "The city is full of tourists in summer."},
            {"word": "Aviation", "ipa": "/ˌeɪviˈeɪʃən/", "meaning": "Chuyến bay", "example": "Our flight was delayed for three hours."},
            {"word": "Terminal", "ipa": "/ˈtərmənəl/", "meaning": "Nhà ga, trạm", "example": "Let's meet at the train station."},
            {"word": "Escort", "ipa": "/ˈɛskɔrt/", "meaning": "Hướng dẫn viên, sách hướng dẫn", "example": "Our tour guide was very knowledgeable."},
            {"word": "Keepsake", "ipa": "/ˈkipˌseɪk/", "meaning": "Quà lưu niệm", "example": "She bought a small souvenir from Rome."},
        ],
        "B1": [
            {"word": "Destination", "ipa": "/ˌdestɪˈneɪʃn/", "meaning": "Điểm đến", "example": "What is your final travel destination?"},
            {"word": "Itinerary", "ipa": "/aɪˈtɪnərəri/", "meaning": "Lịch trình chuyến đi", "example": "We planned our itinerary in detail."},
            {"word": "Accommodation", "ipa": "/əˌkɒməˈdeɪʃn/", "meaning": "Chỗ ở, nơi lưu trú", "example": "The hostel offers cheap accommodation."},
            {"word": "Explore", "ipa": "/ɪkˈsplɔː(r)/", "meaning": "Khám phá, thám hiểm", "example": "We spent the afternoon exploring the ancient temple."},
            {"word": "Reservation", "ipa": "/ˌrezəˈveɪʃn/", "meaning": "Sự đặt trước", "example": "I made a hotel reservation online."},
            {"word": "Adventure", "ipa": "/ədˈventʃə(r)/", "meaning": "Cuộc phiêu lưu", "example": "He wrote a book about his desert adventure."},
            {"word": "Excursion", "ipa": "/ɪkˈskɜːʃn/", "meaning": "Chuyến tham quan ngắn", "example": "We went on a day excursion to the island."},
            {"word": "Passenger", "ipa": "/ˈpæsɪndʒə(r)/", "meaning": "Hành khách", "example": "All passengers must fasten their seatbelts."},
            {"word": "Attraction", "ipa": "/əˈtrækʃən/", "meaning": "Điểm tham quan, địa điểm hấp dẫn", "example": "The Eiffel Tower is Paris's most famous tourist attraction."},
            {"word": "Schedule", "ipa": "/ˈskɛʤʊl/", "meaning": "Lịch trình, thời khóa biểu", "example": "I need to check my work schedule."},
            {"word": "Lodging", "ipa": "/ˈlɒdʒɪŋ/", "meaning": "Chỗ trọ, nơi ở tạm", "example": "The hotel provides comfortable lodging for tourists."},
            {"word": "Discover", "ipa": "/dɪˈskʌvər/", "meaning": "Phát hiện ra, tìm thấy điều mới", "example": "Explorers discovered new lands in the 15th century."},
            {"word": "Booking", "ipa": "/ˈbʊkɪŋ/", "meaning": "Đặt chỗ, đặt phòng trước", "example": "Please confirm your booking at least 24 hours in advance."},
            {"word": "Journey", "ipa": "/ˈdʒɜːni/", "meaning": "Hành trình dài, chuyến đi", "example": "The journey from Hanoi to Ho Chi Minh City takes about two hours by plane."},
            {"word": "Outing", "ipa": "/ˈaʊtɪŋ/", "meaning": "Chuyến dã ngoại, đi chơi ngoài", "example": "The whole family went on an outing to the countryside."},
            {"word": "Traveler", "ipa": "/ˈtræv.əl.ər/", "meaning": "Người đi du lịch, lữ khách", "example": "The traveler packed light for the long trip."},
        ],
        "B2": [
            {"word": "Expedition", "ipa": "/ˌekspəˈdɪʃn/", "meaning": "Cuộc thám hiểm", "example": "They organized an expedition to Antarctica."},
            {"word": "Picturesque", "ipa": "/ˌpɪktʃəˈresk/", "meaning": "Đẹp như tranh vẽ", "example": "We visited a picturesque seaside village."},
            {"word": "Breathtaking", "ipa": "/ˈbreθteɪkɪŋ/", "meaning": "Đẹp đến ngạt thở", "example": "The view from the top of the mountain was breathtaking."},
            {"word": "Hospitable", "ipa": "/hɒˈspɪtəbl/", "meaning": "Hiếu khách, mến khách", "example": "The local people were exceptionally hospitable."},
            {"word": "Spectacular", "ipa": "/spekˈtækjələ(r)/", "meaning": "Ngoạn mục, hùng vĩ", "example": "The fireworks display was truly spectacular."},
            {"word": "Wilderness", "ipa": "/ˈwɪldənəs/", "meaning": "Vùng hoang dã", "example": "They love camping in the deep wilderness."},
            {"word": "Sightseeing", "ipa": "/ˈsaɪtsiːɪŋ/", "meaning": "Sự tham quan ngắm cảnh", "example": "We did a lot of sightseeing in Paris."},
            {"word": "Transcontinental", "ipa": "/ˌtrænzˌkɒntɪˈnentl/", "meaning": "Xuyên lục địa", "example": "They took a transcontinental train trip."},
            {"word": "Trek", "ipa": "/trɛk/", "meaning": "Cuộc thám hiểm", "example": "They organized an expedition to Antarctica."},
            {"word": "Scenic", "ipa": "/ˈsinɪk/", "meaning": "Đẹp như tranh vẽ", "example": "We visited a picturesque seaside village."},
            {"word": "Stunning", "ipa": "/ˈstənɪŋ/", "meaning": "Đẹp đến ngạt thở", "example": "The view from the top of the mountain was breathtaking."},
            {"word": "Welcoming", "ipa": "/ˈwɛlkəmɪŋ/", "meaning": "Hiếu khách, mến khách", "example": "The local people were exceptionally hospitable."},
            {"word": "Magnificent", "ipa": "/mægˈnɪfɪsənt/", "meaning": "Ngoạn mục, hùng vĩ", "example": "The fireworks display was truly spectacular."},
            {"word": "Outback", "ipa": "/ˈaʊtˌbæk/", "meaning": "Vùng hoang dã", "example": "They love camping in the deep wilderness."},
            {"word": "Touring", "ipa": "/ˈtʊrɪŋ/", "meaning": "Sự tham quan ngắm cảnh", "example": "We did a lot of sightseeing in Paris."},
            {"word": "Cross-country", "ipa": "/ˈkrɔˌskəntri/", "meaning": "Xuyên lục địa", "example": "They took a transcontinental train trip."},
        ],
        "C1": [
            {"word": "Sojourn", "ipa": "/ˈsoʊʤərn/", "meaning": "Sự lưu trú tạm thời", "example": "Our brief sojourn in Rome was delightful."},
            {"word": "Uncharted", "ipa": "/ˌʌnˈtʃɑːtɪd/", "meaning": "Chưa được thám hiểm, xa lạ", "example": "They sailed into uncharted waters."},
            {"word": "Peregrination", "ipa": "/ˌperəɡrɪˈneɪʃn/", "meaning": "Hành trình dài ngày, sự ngao du", "example": "His artistic style evolved during his long peregrinations."},
            {"word": "Globetrotter", "ipa": "/ˈɡləʊbtrɒtə(r)/", "meaning": "Người đi du lịch khắp thế giới", "example": "She has been a globetrotter since graduating from university."},
            {"word": "Bespoke", "ipa": "/bɪˈspəʊk/", "meaning": "Được thiết kế riêng, độc bản", "example": "The agency designs bespoke travel experiences."},
            {"word": "Wanderlust", "ipa": "/ˈwɒndəlʌst/", "meaning": "Sự cuồng đi, đam mê du lịch", "example": "Her wanderlust led her to visit fifty countries."},
            {"word": "Unspoiled", "ipa": "/ˌʌnˈspɔɪld/", "meaning": "Hoang sơ, chưa bị đô thị hóa", "example": "We found a quiet, unspoiled island in Greece."},
            {"word": "Vagabond", "ipa": "/ˈvæɡəbɒnd/", "meaning": "Kẻ ngao du, người đi đây đi đó", "example": "He lived a vagabond lifestyle, moving from town to town."},
            {"word": "Stay", "ipa": "/steɪ/", "meaning": "Sự lưu trú tạm thời", "example": "Our brief sojourn in Rome was delightful."},
            {"word": "Undiscovered", "ipa": "/ˌəndɪˈskəvərd/", "meaning": "Chưa được thám hiểm, xa lạ", "example": "They sailed into uncharted waters."},
            {"word": "Roaming", "ipa": "/ˈroʊmɪŋ/", "meaning": "Hành trình dài ngày, sự ngao du", "example": "His artistic style evolved during his long peregrinations."},
            {"word": "World traveler", "ipa": "/wərld ˈtrævələr/", "meaning": "Người đi du lịch khắp thế giới", "example": "She has been a globetrotter since graduating from university."},
            {"word": "Custom-made", "ipa": "/bɪˈspəʊk/", "meaning": "Được thiết kế riêng, độc bản", "example": "The agency designs bespoke travel experiences."},
            {"word": "Travel bug", "ipa": "/ˈtrævəl bəg/", "meaning": "Sự cuồng đi, đam mê du lịch", "example": "Her wanderlust led her to visit fifty countries."},
            {"word": "Pristine", "ipa": "/ˈprɪstin/", "meaning": "Hoang sơ, chưa bị đô thị hóa", "example": "We found a quiet, unspoiled island in Greece."},
            {"word": "Nomad", "ipa": "/ˈnoʊˌmæd/", "meaning": "Kẻ ngao du, người đi đây đi đó", "example": "He lived a vagabond lifestyle, moving from town to town."},
        ],
    },
}

@router.get("/vocabulary/topics")
def get_vocabulary_topics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    API Lấy danh sách 15 chủ đề từ vựng kèm theo tiến trình học tập của user.
    """
    from app.models.models import VocabularyTopic, VocabularyTopicProgress
    
    # Đảm bảo topics mặc định đã tồn tại trong DB
    for t in default_topics:
        topic_in_db = db.query(VocabularyTopic).filter(VocabularyTopic.code == t["code"]).first()
        if not topic_in_db:
            db_topic = VocabularyTopic(
                name=t["name"],
                code=t["code"],
                icon=t["icon"],
                description=t["description"]
            )
            db.add(db_topic)
    db.commit()

    db_topics = db.query(VocabularyTopic).all()
    
    # Lấy tiến độ học của user
    progresses = db.query(VocabularyTopicProgress).filter(VocabularyTopicProgress.user_id == current_user.id).all()
    progress_map = {p.topic_code: p for p in progresses}

    result = []
    for t in db_topics:
        prog = progress_map.get(t.code)
        mastered = prog.mastered_count if prog else 0
        total = prog.total_count if prog else 10 # Giả định mặc định 10 từ mỗi chủ đề

        result.append({
            "id": t.id,
            "name": t.name,
            "code": t.code,
            "icon": t.icon,
            "description": t.description,
            "progress": {
                "mastered_count": mastered,
                "total_count": total,
                "percentage": round((mastered / total * 100.0) if total > 0 else 0.0, 1)
            }
        })
        
    return result

@router.get("/vocabulary/topic/{topic_code}")
def get_vocabulary_by_topic(
    topic_code: str,
    level: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    API Lấy từ vựng theo chủ đề: Tự động phân tích trình độ người học (Adaptive Level Selection)
    và tăng độ khó nếu người học đã tiến bộ vượt trội.
    """
    from app.models.models import Vocabulary, UserSkillLevel, VocabularyMasteredWord, VocabularyTopicProgress
    
    # 1. AI Adaptive Level: Chọn level thích hợp cho người dùng
    user_level = level
    if not user_level:
        # Đọc level từ User profile
        user_level = current_user.level or "B1"

    # Kiểm tra tiến độ để tăng độ khó tự động (Adaptive Difficulty)
    # Lấy số từ đã mastered của chủ đề này
    mastered_in_db = db.query(VocabularyMasteredWord).filter(
        VocabularyMasteredWord.user_id == current_user.id
    ).all()
    mastered_words = {m.word.lower() for m in mastered_in_db}

    # Lấy từ vựng thuộc topic này từ DB
    vocab_items = db.query(Vocabulary).filter(
        Vocabulary.topic == topic_code,
        Vocabulary.level == user_level,
        Vocabulary.is_active == True
    ).all()

    # Kiểm tra tính nhất quán dữ liệu từ vựng trong DB so với topic_vocab_db chuẩn
    fallback_topic = topic_vocab_db.get(topic_code, topic_vocab_db["travel"])
    fallback_level_items = fallback_topic.get(user_level, fallback_topic.get("B1", []))
    expected_count = len(fallback_level_items)
    
    # Kiểm tra xem từ vựng trong DB có thực sự khớp với bộ từ chuẩn của topic đó không
    db_word_set = {v.word.lower() for v in vocab_items}
    expected_word_set = {item["word"].lower() for item in fallback_level_items}
    
    is_mismatched = False
    if vocab_items:
        # Nếu có bất kỳ từ nào trong DB không thuộc danh sách từ chuẩn của chủ đề này, đánh dấu bị mismatch
        for w_low in db_word_set:
            if w_low not in expected_word_set:
                is_mismatched = True
                break
    
    # Nếu DB chỉ chứa ít hơn dữ liệu chuẩn (thiếu hụt) hoặc dữ liệu bị sai lệch chủ đề (mismatched), tự động xóa sạch để sinh lại 100% chuẩn xác
    if is_mismatched or (vocab_items and len(vocab_items) < expected_count):
        db.query(Vocabulary).filter(
            Vocabulary.topic == topic_code,
            Vocabulary.level == user_level
        ).delete()
        db.commit()
        vocab_items = []

    # Nếu DB trống, ta sinh từ vựng mẫu cho chủ đề này từ topic_vocab_db
    if not vocab_items:
        # Đưa vào db để duy trì lâu dài
        for item in fallback_level_items:
            db_v = Vocabulary(
                word=item["word"],
                ipa=item["ipa"],
                meaning=item["meaning"],
                level=user_level,
                example=item["example"],
                topic=topic_code,
                is_active=True
            )
            db.add(db_v)
        db.commit()
        
        vocab_items = db.query(Vocabulary).filter(
            Vocabulary.topic == topic_code,
            Vocabulary.level == user_level,
            Vocabulary.is_active == True
        ).all()

    # Tính toán tiến trình
    total_count = len(vocab_items)
    mastered_count = sum(1 for v in vocab_items if v.word.lower() in mastered_words)

    # Nếu người dùng đã thuộc trên 80% số từ thuộc level hiện tại, AI sẽ khuyên chuyển lên level tiếp theo
    recommend_next_level = False
    next_level_map = {"A1": "A2", "A2": "B1", "B1": "B2", "B2": "C1", "C1": "C2"}
    if total_count > 0 and (mastered_count / total_count) >= 0.8:
        if user_level in next_level_map:
            recommend_next_level = True
            # Tự động nâng level để tăng độ khó thích ứng
            if not level: # Chỉ tự động nâng cấp độ khó nếu người dùng không chọn thủ công
                user_level = next_level_map[user_level]
                # Gọi lại việc tải từ vựng ở level mới
                return get_vocabulary_by_topic(topic_code=topic_code, level=user_level, db=db, current_user=current_user)

    # Cập nhật bảng VocabularyTopicProgress
    prog = db.query(VocabularyTopicProgress).filter(
        VocabularyTopicProgress.user_id == current_user.id,
        VocabularyTopicProgress.topic_code == topic_code,
        VocabularyTopicProgress.level == user_level
    ).first()

    if not prog:
        prog = VocabularyTopicProgress(
            user_id=current_user.id,
            topic_code=topic_code,
            level=user_level,
            mastered_count=mastered_count,
            total_count=total_count
        )
        db.add(prog)
    else:
        prog.mastered_count = mastered_count
        prog.total_count = total_count
    db.commit()

    result_words = []
    for v in vocab_items:
        is_mastered = v.word.lower() in mastered_words
        result_words.append({
            "word": v.word,
            "ipa": v.ipa,
            "meaning": v.meaning,
            "level": v.level,
            "status": "Mastered" if is_mastered else "Learning",
            "example": v.example
        })

    return {
        "topic": topic_code,
        "selected_level": user_level,
        "recommend_next_level": recommend_next_level,
        "progress": {
            "mastered_count": mastered_count,
            "total_count": total_count,
            "percentage": round((mastered_count / total_count * 100.0) if total_count > 0 else 0.0, 1)
        },
        "words": result_words
    }
