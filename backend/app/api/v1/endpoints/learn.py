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
topic_vocab_db = {   'ai': {   'A1': [   {   'example': 'The factory uses robots to build cars.',
                            'ipa': '/ˈrəʊbɒt/',
                            'meaning': 'Người máy',
                            'word': 'Robot'},
                        {   'example': 'He has a smart TV in his living room.',
                            'ipa': '/smɑːt/',
                            'meaning': 'Thông minh',
                            'word': 'Smart'},
                        {   'example': 'All customer data is encrypted.',
                            'ipa': '/ˈdeɪtə/',
                            'meaning': 'Dữ liệu',
                            'word': 'Data'},
                        {   'example': 'I wrote a few lines of code today.',
                            'ipa': '/kəʊd/',
                            'meaning': 'Mã lập trình',
                            'word': 'Code'},
                        {   'example': 'You can download the app for free.',
                            'ipa': '/æp/',
                            'meaning': 'Ứng dụng',
                            'word': 'App'},
                        {   'example': 'The system has active users globally.',
                            'ipa': '/ˈjuːzə(r)/',
                            'meaning': 'Người dùng',
                            'word': 'User'},
                        {   'example': 'We search the web for answers.',
                            'ipa': '/web/',
                            'meaning': 'Trang mạng, mạng lưới',
                            'word': 'Web'},
                        {   'example': 'This computer is extremely fast.',
                            'ipa': '/fɑːst/',
                            'meaning': 'Nhanh',
                            'word': 'Fast'},
                        {   'example': 'The printing machine produces hundreds '
                                       'of books per hour.',
                            'ipa': '/məˈʃiːn/',
                            'meaning': 'Máy móc, thiết bị cơ khí',
                            'word': 'Machine'},
                        {   'example': 'She came up with a clever solution to '
                                       'the math problem.',
                            'ipa': '/ˈklev.ər/',
                            'meaning': 'Thông minh, khôn khéo, nhanh trí',
                            'word': 'Clever'},
                        {   'example': 'The report is based on hard facts and '
                                       'figures.',
                            'ipa': '/fækts/',
                            'meaning': 'Sự thật, số liệu thực tế',
                            'word': 'Facts'},
                        {   'example': 'I ran a simple python script to clean '
                                       'the data.',
                            'ipa': '/skrɪpt/',
                            'meaning': 'Kịch bản mã lệnh, đoạn mã script',
                            'word': 'Script'},
                        {   'example': 'Computers are essential tools for '
                                       'modern education.',
                            'ipa': '/tuːl/',
                            'meaning': 'Công cụ, dụng cụ làm việc',
                            'word': 'Tool'},
                        {   'example': 'The lawyer met with her client to '
                                       'discuss the case.',
                            'ipa': '/ˈklaɪ.ənt/',
                            'meaning': 'Khách hàng của công ty, máy khách',
                            'word': 'Client'},
                        {   'example': 'The fisherman cast his net into the '
                                       'sea.',
                            'ipa': '/nɛt/',
                            'meaning': 'Lưới; mạng lưới',
                            'word': 'Net'},
                        {   'example': 'We had a quick lunch and returned to '
                                       'work.',
                            'ipa': '/kwɪk/',
                            'meaning': 'Nhanh chóng, mau lẹ',
                            'word': 'Quick'},
                        {   'example': 'Machines can learn from data.',
                            'ipa': '/lɜːrn/',
                            'meaning': 'học, tiếp thu kiến thức',
                            'word': 'learn'},
                        {   'example': 'Can computers think like humans?',
                            'ipa': '/θɪŋk/',
                            'meaning': 'suy nghĩ, phân tích',
                            'word': 'think'},
                        {   'example': 'The AI can talk back to you.',
                            'ipa': '/tɔːk/',
                            'meaning': 'nói chuyện, giao tiếp',
                            'word': 'talk'},
                        {   'example': 'The AI recognizes your voice.',
                            'ipa': '/vɔɪs/',
                            'meaning': 'giọng nói',
                            'word': 'voice'},
                        {   'example': 'The AI reads text quickly.',
                            'ipa': '/tɛkst/',
                            'meaning': 'văn bản, chữ viết',
                            'word': 'text'},
                        {   'example': 'AI can help you find answers.',
                            'ipa': '/hɛlp/',
                            'meaning': 'hỗ trợ, trợ giúp',
                            'word': 'help'},
                        {   'example': 'Use AI to search for information.',
                            'ipa': '/sɜːrtʃ/',
                            'meaning': 'tìm kiếm thông tin',
                            'word': 'search'},
                        {   'example': 'AI can find patterns in large '
                                       'datasets.',
                            'ipa': '/faɪnd/',
                            'meaning': 'tìm thấy, phát hiện ra',
                            'word': 'find'},
                        {   'example': 'AI makes tasks easy for people.',
                            'ipa': '/ˈiː.zi/',
                            'meaning': 'dễ dàng, thuận tiện',
                            'word': 'easy'},
                        {   'example': 'You can type a question for the AI.',
                            'ipa': '/taɪp/',
                            'meaning': 'gõ phím, đánh máy',
                            'word': 'type'},
                        {   'example': 'Send a message to the chatbot.',
                            'ipa': '/sɛnd/',
                            'meaning': 'gửi đi, truyền tải',
                            'word': 'send'},
                        {   'example': 'The AI gave a quick answer.',
                            'ipa': '/ˈæn.sər/',
                            'meaning': 'câu trả lời, trả lời',
                            'word': 'answer'},
                        {   'example': 'Ask the AI assistant anything.',
                            'ipa': '/æsk/',
                            'meaning': 'đặt câu hỏi',
                            'word': 'ask'},
                        {   'example': 'Open the AI app on your phone.',
                            'ipa': '/ˈoʊ.pən/',
                            'meaning': 'mở ra, khởi chạy',
                            'word': 'open'},
                        {   'example': 'Close the app when you are done.',
                            'ipa': '/kloʊz/',
                            'meaning': 'đóng lại, tắt',
                            'word': 'close'},
                        {   'example': 'Enter a number to start the '
                                       'calculation.',
                            'ipa': '/ˈnʌm.bər/',
                            'meaning': 'con số, số liệu',
                            'word': 'number'},
                        {   'example': 'The AI understands every word you '
                                       'type.',
                            'ipa': '/wɜːrd/',
                            'meaning': 'từ ngữ trong văn bản',
                            'word': 'word'},
                        {   'example': 'We use AI every day now.',
                            'ipa': '/juːz/',
                            'meaning': 'sử dụng, dùng',
                            'word': 'use'},
                        {   'example': 'AI can make images from text.',
                            'ipa': '/meɪk/',
                            'meaning': 'tạo ra, làm ra',
                            'word': 'make'},
                        {   'example': 'We need to test the new model.',
                            'ipa': '/tɛst/',
                            'meaning': 'kiểm tra, thử nghiệm',
                            'word': 'test'},
                        {   'example': 'The scanner can read barcodes '
                                       'automatically.',
                            'ipa': '/riːd/',
                            'meaning': 'đọc, nhận dạng văn bản',
                            'word': 'read'},
                        {   'example': 'AI can write short paragraphs.',
                            'ipa': '/raɪt/',
                            'meaning': 'viết, soạn thảo văn bản',
                            'word': 'write'},
                        {   'example': 'The AI can play chess better than '
                                       'humans.',
                            'ipa': '/pleɪ/',
                            'meaning': 'chơi game, tương tác',
                            'word': 'play'},
                        {   'example': 'Cameras let AI see the world.',
                            'ipa': '/siː/',
                            'meaning': 'nhìn thấy, nhận dạng hình ảnh',
                            'word': 'see'},
                        {   'example': 'The device can hear your commands.',
                            'ipa': '/hɪər/',
                            'meaning': 'nghe, nhận dạng giọng nói',
                            'word': 'hear'},
                        {   'example': 'The AI can analyze a picture.',
                            'ipa': '/ˈpɪk.tʃər/',
                            'meaning': 'hình ảnh',
                            'word': 'picture'},
                        {   'example': 'The AI processes sound input.',
                            'ipa': '/saʊnd/',
                            'meaning': 'âm thanh',
                            'word': 'sound'},
                        {   'example': 'Press the button to start the AI.',
                            'ipa': '/ˈbʌt.ən/',
                            'meaning': 'nút nhấn, nút bấm',
                            'word': 'button'},
                        {   'example': 'The input is processed by the AI.',
                            'ipa': '/ˈɪn.pʊt/',
                            'meaning': 'dữ liệu đầu vào',
                            'word': 'input'},
                        {   'example': 'The AI output was very accurate.',
                            'ipa': '/ˈaʊt.pʊt/',
                            'meaning': 'kết quả đầu ra',
                            'word': 'output'},
                        {   'example': 'AI can understand many languages.',
                            'ipa': '/ˈlæŋ.ɡwɪdʒ/',
                            'meaning': 'ngôn ngữ tự nhiên',
                            'word': 'language'},
                        {   'example': 'AI is designed to help humans.',
                            'ipa': '/ˈhjuː.mən/',
                            'meaning': 'con người, loài người',
                            'word': 'human'},
                        {   'example': 'Ask the chatbot a question.',
                            'ipa': '/ˈkwɛs.tʃən/',
                            'meaning': 'câu hỏi cần giải đáp',
                            'word': 'question'},
                        {   'example': 'The AI identifies objects in an image.',
                            'ipa': '/ˈɪm.ɪdʒ/',
                            'meaning': 'hình ảnh kỹ thuật số',
                            'word': 'image'},
                        {   'example': 'Chat with the AI assistant today.',
                            'ipa': '/tʃæt/',
                            'meaning': 'trò chuyện trực tuyến',
                            'word': 'chat'},
                        {   'example': 'The sensor detects motion and sound.',
                            'ipa': '/ˈsɛn.sər/',
                            'meaning': 'cảm biến điện tử',
                            'word': 'sensor'},
                        {   'example': 'Give the voice command to start.',
                            'ipa': '/kəˈmænd/',
                            'meaning': 'lệnh điều khiển',
                            'word': 'command'},
                        {   'example': 'The AI produced an accurate result.',
                            'ipa': '/rɪˈzʌlt/',
                            'meaning': 'kết quả đầu ra',
                            'word': 'result'}],
              'A2': [   {   'example': 'I use my computer for coding.',
                            'ipa': '/kəmˈpjuːtə(r)/',
                            'meaning': 'Máy tính',
                            'word': 'Computer'},
                        {   'example': 'The computer system needs an update.',
                            'ipa': '/ˈsɪstəm/',
                            'meaning': 'Hệ thống',
                            'word': 'System'},
                        {   'example': 'The social network connects millions '
                                       'of people.',
                            'ipa': '/ˈnetwɜːk/',
                            'meaning': 'Mạng lưới, mạng kết nối',
                            'word': 'Network'},
                        {   'example': 'This program helps detect grammar '
                                       'errors.',
                            'ipa': '/ˈprəʊɡræm/',
                            'meaning': 'Chương trình máy tính',
                            'word': 'Program'},
                        {   'example': 'We are living in a digital age.',
                            'ipa': '/ˈdɪdʒɪtl/',
                            'meaning': 'Kỹ thuật số',
                            'word': 'Digital'},
                        {   'example': 'Every device in the smart home is '
                                       'connected to the internet.',
                            'ipa': '/dɪˈvaɪs/',
                            'meaning': 'Thiết bị điện tử',
                            'word': 'Device'},
                        {   'example': 'This cloud storage is highly secure.',
                            'ipa': '/ˈstɔːrɪdʒ/',
                            'meaning': 'Bộ nhớ lưu trữ',
                            'word': 'Storage'},
                        {   'example': 'The CPU processes information quickly.',
                            'ipa': '/ˈprəʊses/',
                            'meaning': 'Xử lý, quy trình',
                            'word': 'Process'},
                        {   'example': 'The new chip is the fastest mobile '
                                       'processor in the world.',
                            'ipa': '/ˈprəʊ.ses.ər/',
                            'meaning': 'Bộ vi xử lý thông tin',
                            'word': 'Processor'},
                        {   'example': 'The structural strength of the bridge '
                                       'was tested thoroughly.',
                            'ipa': '/ˈstrʌk.tʃər/',
                            'meaning': 'Cấu trúc, kết cấu hệ thống',
                            'word': 'Structure'},
                        {   'example': 'There is a poor internet connection in '
                                       'this room.',
                            'ipa': '/kəˈnek.ʃən/',
                            'meaning': 'Sự kết nối, mối liên kết',
                            'word': 'Connection'},
                        {   'example': 'He installs free open-source software '
                                       'on his laptop.',
                            'ipa': '/ˈsɒft.weər/',
                            'meaning': 'phần mềm máy tính',
                            'word': 'application_1'},
                        {   'example': 'Electronic commerce has grown rapidly '
                                       'over the years.',
                            'ipa': '/ˌel.ekˈtrɒn.ɪk/',
                            'meaning': 'Thuộc về điện tử',
                            'word': 'Electronic'},
                        {   'example': 'All laboratory equipment must be kept '
                                       'clean and organized.',
                            'ipa': '/ɪˈkwɪp.mənt/',
                            'meaning': 'Trang thiết bị máy móc',
                            'word': 'Equipment'},
                        {   'example': 'The camera stores photos in its '
                                       'internal flash memory.',
                            'ipa': '/ˈmem.ər.i/',
                            'meaning': 'Bộ nhớ lưu trữ thông tin',
                            'word': 'Memory'},
                        {   'example': 'She knows how to handle difficult '
                                       'customer queries.',
                            'ipa': '/ˈhæn.dəl/',
                            'meaning': 'Xử lý, đối phó, giải quyết',
                            'word': 'Handle'},
                        {   'example': 'We trained a language model.',
                            'ipa': '/ˈmɒd.əl/',
                            'meaning': 'mô hình AI được huấn luyện',
                            'word': 'model'},
                        {   'example': 'The model can predict stock prices.',
                            'ipa': '/prɪˈdɪkt/',
                            'meaning': 'dự đoán kết quả',
                            'word': 'predict'},
                        {   'example': 'The model achieved 95% accuracy.',
                            'ipa': '/ˈæk.jʊ.rə.si/',
                            'meaning': 'độ chính xác của mô hình',
                            'word': 'accuracy'},
                        {   'example': 'The robot arm assembles car parts.',
                            'ipa': '/ˈroʊ.bɒt ɑːrm/',
                            'meaning': 'cánh tay robot công nghiệp',
                            'word': 'robot arm'},
                        {   'example': 'The chatbot answers customer '
                                       'questions.',
                            'ipa': '/ˈtʃæt.bɒt/',
                            'meaning': 'trợ lý ảo chat tự động',
                            'word': 'chatbot'},
                        {   'example': 'The AI finds patterns in the data.',
                            'ipa': '/ˈpæt.ərn/',
                            'meaning': 'mẫu dữ liệu, xu hướng',
                            'word': 'pattern'},
                        {   'example': 'The AI makes decisions automatically.',
                            'ipa': '/dɪˈsɪʒ.ən/',
                            'meaning': 'quyết định tự động',
                            'word': 'decision'},
                        {   'example': 'Speech recognition is now very '
                                       'accurate.',
                            'ipa': '/spiːtʃ/',
                            'meaning': 'lời nói, giọng nói',
                            'word': 'speech'},
                        {   'example': 'Face recognition unlocks the phone.',
                            'ipa': '/ˌrɛk.əɡˈnɪʃ.ən/',
                            'meaning': 'nhận dạng đối tượng, giọng nói',
                            'word': 'recognition'},
                        {   'example': 'AI can translate between 100 '
                                       'languages.',
                            'ipa': '/trænsˈleɪt/',
                            'meaning': 'dịch thuật tự động',
                            'word': 'translate'},
                        {   'example': 'The AI translation was very accurate.',
                            'ipa': '/trænsˈleɪʃ.ən/',
                            'meaning': 'bản dịch tự động',
                            'word': 'translation'},
                        {   'example': 'The system uses object detection.',
                            'ipa': '/dɪˈtɛk.ʃən/',
                            'meaning': 'phát hiện và nhận diện',
                            'word': 'detection'},
                        {   'example': 'The spam filter removes unwanted '
                                       'emails.',
                            'ipa': '/ˈfɪl.tər/',
                            'meaning': 'lọc dữ liệu, lọc nội dung',
                            'word': 'filter'},
                        {   'example': 'We need to reduce model errors.',
                            'ipa': '/ˈɛr.ər/',
                            'meaning': 'lỗi, sai số trong mô hình',
                            'word': 'error'},
                        {   'example': 'The latest version is more accurate.',
                            'ipa': '/ˈvɜːr.ʒən/',
                            'meaning': 'phiên bản phần mềm',
                            'word': 'version'},
                        {   'example': 'This AI feature saves hours of work.',
                            'ipa': '/ˈfiː.tʃər/',
                            'meaning': 'tính năng của phần mềm',
                            'word': 'feature'},
                        {   'example': 'The AI can generate realistic images.',
                            'ipa': '/ˈdʒɛn.ər.eɪt/',
                            'meaning': 'tạo ra nội dung, dữ liệu',
                            'word': 'generate'},
                        {   'example': 'The chatbot response was helpful.',
                            'ipa': '/rɪˈspɒns/',
                            'meaning': 'phản hồi của hệ thống AI',
                            'word': 'response'},
                        {   'example': 'The processing speed is impressive.',
                            'ipa': '/spiːd/',
                            'meaning': 'tốc độ xử lý',
                            'word': 'speed'},
                        {   'example': 'We store AI models in the cloud.',
                            'ipa': '/klaʊd/',
                            'meaning': 'điện toán đám mây',
                            'word': 'cloud'},
                        {   'example': 'The server runs the AI model 24/7.',
                            'ipa': '/ˈsɜːr.vər/',
                            'meaning': 'máy chủ, server',
                            'word': 'server'},
                        {   'example': 'Each image needs a correct label.',
                            'ipa': '/ˈleɪ.bəl/',
                            'meaning': 'nhãn dữ liệu gán cho mẫu',
                            'word': 'label'},
                        {   'example': 'The model predicts the correct class.',
                            'ipa': '/klæs/',
                            'meaning': 'lớp phân loại dữ liệu',
                            'word': 'class'},
                        {   'example': 'The AI completes the task quickly.',
                            'ipa': '/tæsk/',
                            'meaning': 'nhiệm vụ cụ thể của AI',
                            'word': 'task'},
                        {   'example': 'Image recognition is used in '
                                       'smartphones.',
                            'ipa': '/ˈɪm.ɪdʒ ˌrɛk.əɡˈnɪʃ.ən/',
                            'meaning': 'nhận dạng hình ảnh tự động',
                            'word': 'image recognition'},
                        {   'example': 'AI builds a profile based on behavior.',
                            'ipa': '/ˈproʊ.faɪl/',
                            'meaning': 'hồ sơ người dùng',
                            'word': 'profile'},
                        {   'example': 'AI analyzes user behavior data.',
                            'ipa': '/bɪˈheɪ.vjər/',
                            'meaning': 'hành vi người dùng',
                            'word': 'behavior'},
                        {   'example': 'Follow the instructions carefully.',
                            'ipa': '/ɪnˈstrʌk.ʃən/',
                            'meaning': 'hướng dẫn sử dụng',
                            'word': 'instruction'},
                        {   'example': 'We evaluate models with test data.',
                            'ipa': '/tɛst ˈdeɪ.tə/',
                            'meaning': 'dữ liệu kiểm thử mô hình',
                            'word': 'test data'},
                        {   'example': 'Training data quality is crucial.',
                            'ipa': '/ˈtreɪ.nɪŋ ˈdeɪ.tə/',
                            'meaning': 'dữ liệu dùng để huấn luyện',
                            'word': 'training data'},
                        {   'example': "Track the model's performance daily.",
                            'ipa': '/pərˈfɔːr.məns/',
                            'meaning': 'hiệu suất vận hành của mô hình',
                            'word': 'performance'},
                        {   'example': 'AI runs a physical simulation.',
                            'ipa': '/ˌsɪm.jʊˈleɪ.ʃən/',
                            'meaning': 'mô phỏng thực tế ảo',
                            'word': 'simulation'},
                        {   'example': 'The virtual assistant is always '
                                       'available.',
                            'ipa': '/ˈvɜːr.tʃʊ.əl/',
                            'meaning': 'ảo, môi trường kỹ thuật số',
                            'word': 'virtual'},
                        {   'example': 'Real-time AI provides instant '
                                       'responses.',
                            'ipa': '/ˌriːl ˈtaɪm/',
                            'meaning': 'xử lý theo thời gian thực',
                            'word': 'real-time'},
                        {   'example': 'The AI processes audio files '
                                       'instantly.',
                            'ipa': '/ˈɔː.di.oʊ/',
                            'meaning': 'dữ liệu âm thanh đầu vào',
                            'word': 'audio'},
                        {   'example': 'We need more data to train the model.',
                            'ipa': '/treɪn/',
                            'meaning': 'huấn luyện mô hình AI',
                            'word': 'train'}],
              'B1': [   {   'example': 'Automation will change the future of '
                                       'work.',
                            'ipa': '/ˌɔːtəˈmeɪʃn/',
                            'meaning': 'Tự động hóa',
                            'word': 'Automation'},
                        {   'example': 'The customer records are in the '
                                       'database.',
                            'ipa': '/ˈdeɪtəbeɪs/',
                            'meaning': 'Cơ sở dữ liệu',
                            'word': 'Database'},
                        {   'example': 'They design software for language '
                                       'learning.',
                            'ipa': '/ˈsɒftweə(r)/',
                            'meaning': 'Phần mềm',
                            'word': 'Software'},
                        {   'example': 'The user interface is very clean.',
                            'ipa': '/ˈɪntəfeɪs/',
                            'meaning': 'Giao diện',
                            'word': 'Interface'},
                        {   'example': 'Siri is a virtual assistant on iOS.',
                            'ipa': '/əˈsɪstənt/',
                            'meaning': 'Trợ lý',
                            'word': 'Assistant'},
                        {   'example': 'We use AI to analyze pronunciation.',
                            'ipa': '/ˈænəlaɪz/',
                            'meaning': 'Phân tích',
                            'word': 'Analyze'},
                        {   'example': 'AI makes a prediction based on trends.',
                            'ipa': '/prɪˈdɪkʃn/',
                            'meaning': 'Sự dự đoán',
                            'word': 'Prediction'},
                        {   'example': 'Mechanization replaced many manual '
                                       'labor jobs in factories.',
                            'ipa': '/ˌmɛkənəˈzeɪʃən/',
                            'meaning': 'Cơ giới hóa sản xuất',
                            'word': 'Mechanization'},
                        {   'example': "The university's online repository "
                                       'contains thousands of research papers.',
                            'ipa': '/rɪˈpɒz.ɪ.tər.i/',
                            'meaning': 'Kho lưu trữ dữ liệu, kho chứa',
                            'word': 'Repository_1'},
                        {   'example': 'You can install this mobile '
                                       'application on your tablet.',
                            'ipa': '/ˌæp.lɪˈkeɪ.ʃən/',
                            'meaning': 'Ứng dụng, chương trình phần mềm',
                            'word': 'Application'},
                        {   'example': 'The sales team monitors metrics on a '
                                       'real-time dashboard.',
                            'ipa': '/ˈdæʃ.bɔːd/',
                            'meaning': 'Bảng điều khiển giao diện',
                            'word': 'Dashboard'},
                        {   'example': 'She works as a kitchen helper at a '
                                       'local restaurant.',
                            'ipa': '/ˈhel.pər/',
                            'meaning': 'Người trợ giúp, người giúp đỡ',
                            'word': 'Helper'},
                        {   'example': 'The doctor will examine the patient to '
                                       'determine the cause.',
                            'ipa': '/ɪɡˈzæm.ɪn/',
                            'meaning': 'Xem xét kỹ lưỡng, khảo sát',
                            'word': 'Examine'},
                        {   'example': 'The economic forecast suggests '
                                       'inflation will slow down.',
                            'ipa': '/ˈfɔː.kɑːst/',
                            'meaning': 'Sự dự báo thời tiết hoặc kinh tế',
                            'word': 'Forecast'},
                        {   'example': 'You must follow the standard safety '
                                       'procedure in the lab.',
                            'ipa': '/prəˈsiː.dʒər/',
                            'meaning': 'Thủ tục, quy trình thực hiện',
                            'word': 'Procedure'},
                        {   'example': 'Supervised learning uses labeled data.',
                            'ipa': '/ˌsuː.pər.vaɪzd ˈlɜːr.nɪŋ/',
                            'meaning': 'học có giám sát dùng dữ liệu gán nhãn',
                            'word': 'supervised learning'},
                        {   'example': 'Unsupervised learning finds hidden '
                                       'patterns.',
                            'ipa': '/ˌʌn.suː.pər.vaɪzd ˈlɜːr.nɪŋ/',
                            'meaning': 'học không giám sát tự phát hiện mẫu',
                            'word': 'unsupervised learning'},
                        {   'example': 'Reinforcement learning trains '
                                       'game-playing AI.',
                            'ipa': '/rɪˈɪn.fɔːrs.mənt ˈlɜːr.nɪŋ/',
                            'meaning': 'học tăng cường qua thưởng phạt',
                            'word': 'reinforcement learning'},
                        {   'example': 'Model training requires significant '
                                       'computing power.',
                            'ipa': '/ˈtreɪ.nɪŋ/',
                            'meaning': 'quá trình huấn luyện mô hình',
                            'word': 'training'},
                        {   'example': 'Inference speed must be fast for '
                                       'real-time apps.',
                            'ipa': '/ˈɪn.fər.əns/',
                            'meaning': 'suy diễn, dự đoán của mô hình',
                            'word': 'inference'},
                        {   'example': 'Overfitting reduces model '
                                       'generalization.',
                            'ipa': '/ˌoʊ.vərˈfɪt.ɪŋ/',
                            'meaning': 'hiện tượng mô hình học quá khớp',
                            'word': 'overfitting'},
                        {   'example': 'Underfitting causes poor predictions.',
                            'ipa': '/ˌʌn.dərˈfɪt.ɪŋ/',
                            'meaning': 'hiện tượng mô hình học chưa đủ',
                            'word': 'underfitting'},
                        {   'example': 'Validation data checks model '
                                       'performance.',
                            'ipa': '/ˌvæl.ɪˈdeɪ.ʃən/',
                            'meaning': 'kiểm định hiệu suất mô hình',
                            'word': 'validation'},
                        {   'example': 'Tune hyperparameters to improve '
                                       'accuracy.',
                            'ipa': '/ˌhaɪ.pər.pəˈræm.ɪ.tər/',
                            'meaning': 'siêu tham số thiết lập cho mô hình',
                            'word': 'hyperparameter'},
                        {   'example': 'Training for more epochs can improve '
                                       'results.',
                            'ipa': '/ˈiː.pɒk/',
                            'meaning': 'một vòng huấn luyện qua toàn bộ data',
                            'word': 'epoch'},
                        {   'example': 'Process data in small batches.',
                            'ipa': '/bætʃ/',
                            'meaning': 'lô dữ liệu nhỏ cho từng bước học',
                            'word': 'batch'},
                        {   'example': 'Minimize the loss function during '
                                       'training.',
                            'ipa': '/lɒs ˈfʌŋk.ʃən/',
                            'meaning': 'hàm mất mát đo độ sai của mô hình',
                            'word': 'loss function'},
                        {   'example': 'Adam is a popular AI optimizer.',
                            'ipa': '/ˈɒp.tɪ.maɪ.zər/',
                            'meaning': 'bộ tối ưu hóa tham số mô hình',
                            'word': 'optimizer'},
                        {   'example': 'Gradient descent updates model '
                                       'weights.',
                            'ipa': '/ˈɡreɪ.di.ənt dɪˈsɛnt/',
                            'meaning': 'phương pháp tối ưu hóa học máy',
                            'word': 'gradient descent'},
                        {   'example': 'Word embeddings capture semantic '
                                       'meaning.',
                            'ipa': '/ɪmˈbɛd.ɪŋ/',
                            'meaning': 'biểu diễn vector từ trong không gian '
                                       'số',
                            'word': 'embedding'},
                        {   'example': 'Each word is represented as a vector.',
                            'ipa': '/ˈvɛk.tər/',
                            'meaning': 'véc-tơ biểu diễn dữ liệu số học',
                            'word': 'vector'},
                        {   'example': 'The model returns prediction '
                                       'probabilities.',
                            'ipa': '/ˌprɒb.əˈbɪl.ɪ.ti/',
                            'meaning': 'xác suất xảy ra của một sự kiện',
                            'word': 'probability'},
                        {   'example': 'Set the threshold for classification.',
                            'ipa': '/ˈθrɛʃ.hoʊld/',
                            'meaning': 'ngưỡng quyết định phân loại',
                            'word': 'threshold'},
                        {   'example': 'High precision reduces false '
                                       'positives.',
                            'ipa': '/prɪˈsɪʒ.ən/',
                            'meaning': 'độ chính xác dương tính của mô hình',
                            'word': 'precision'},
                        {   'example': 'High recall reduces missed detections.',
                            'ipa': '/rɪˈkɔːl/',
                            'meaning': 'độ phủ dương tính của mô hình',
                            'word': 'recall'},
                        {   'example': 'Tokenization splits text into smaller '
                                       'units.',
                            'ipa': '/ˌtoʊ.kə.naɪˈzeɪ.ʃən/',
                            'meaning': 'quá trình tách văn bản thành token',
                            'word': 'tokenization'},
                        {   'example': 'Each word is broken into tokens.',
                            'ipa': '/ˈtoʊ.kən/',
                            'meaning': 'đơn vị ngôn ngữ cơ bản trong NLP',
                            'word': 'token'},
                        {   'example': 'Object detection locates items in '
                                       'photos.',
                            'ipa': '/ˈɒb.dʒɪkt dɪˈtɛk.ʃən/',
                            'meaning': 'nhận dạng và khoanh vùng đối tượng',
                            'word': 'object detection'},
                        {   'example': 'Generative AI creates new music and '
                                       'art.',
                            'ipa': '/ˈdʒɛn.ər.ə.tɪv eɪ aɪ/',
                            'meaning': 'AI tạo sinh nội dung sáng tạo',
                            'word': 'generative AI'},
                        {   'example': 'A language model predicts the next '
                                       'word.',
                            'ipa': '/ˈlæŋ.ɡwɪdʒ ˈmɒd.əl/',
                            'meaning': 'mô hình ngôn ngữ xử lý văn bản',
                            'word': 'language model'},
                        {   'example': 'Write a clear prompt for better '
                                       'results.',
                            'ipa': '/prɒmpt/',
                            'meaning': 'câu lệnh đầu vào cho mô hình AI',
                            'word': 'prompt'},
                        {   'example': 'Context helps AI give better answers.',
                            'ipa': '/ˈkɒn.tɛkst/',
                            'meaning': 'ngữ cảnh giúp AI hiểu đúng ý nghĩa',
                            'word': 'context'},
                        {   'example': 'Fine-tuning adapts a model to a new '
                                       'task.',
                            'ipa': '/ˈfaɪn ˌtjuː.nɪŋ/',
                            'meaning': 'tinh chỉnh mô hình cho tác vụ cụ thể',
                            'word': 'fine-tuning'},
                        {   'example': 'Use a pretrained model to save time.',
                            'ipa': '/priːˈtreɪnd ˈmɒd.əl/',
                            'meaning': 'mô hình đã huấn luyện sẵn trên data '
                                       'lớn',
                            'word': 'pretrained model'},
                        {   'example': 'Transfer learning speeds up model '
                                       'training.',
                            'ipa': '/ˈtræns.fɜːr ˈlɜːr.nɪŋ/',
                            'meaning': 'học chuyển tiếp dùng kiến thức đã học',
                            'word': 'transfer learning'},
                        {   'example': 'Convolutional layers process image '
                                       'features.',
                            'ipa': '/ˌkɒn.vəˈluː.ʃən.əl/',
                            'meaning': 'tích chập dùng trong mạng thị giác',
                            'word': 'convolutional'},
                        {   'example': 'Recurrent networks handle sequential '
                                       'data.',
                            'ipa': '/rɪˈkɜːr.ənt/',
                            'meaning': 'hồi quy dùng cho dữ liệu tuần tự',
                            'word': 'recurrent'},
                        {   'example': 'SQL databases store structured data.',
                            'ipa': '/ˈstrʌk.tʃərd ˈdeɪ.tə/',
                            'meaning': 'dữ liệu có cấu trúc dạng bảng biểu',
                            'word': 'structured data'},
                        {   'example': 'Emails and images are unstructured '
                                       'data.',
                            'ipa': '/ˌʌnˈstrʌk.tʃərd ˈdeɪ.tə/',
                            'meaning': 'dữ liệu phi cấu trúc như văn bản hình '
                                       'ảnh',
                            'word': 'unstructured data'},
                        {   'example': 'Signal processing cleans audio before '
                                       'AI analysis.',
                            'ipa': '/ˈsɪɡ.nəl ˈprəʊ.sɛs.ɪŋ/',
                            'meaning': 'xử lý tín hiệu số cho AI phân tích',
                            'word': 'signal processing'}],
              'B2': [   {   'example': 'AI is built on neural networks.',
                            'ipa': '/ˈnjʊərəl ˈnetwɜːk/',
                            'meaning': 'Mạng nơ-ron',
                            'word': 'Neural network'},
                        {   'example': 'Machine learning is a subset of AI.',
                            'ipa': '/məˈʃiːn ˈlɜːnɪŋ/',
                            'meaning': 'Học máy',
                            'word': 'Machine learning'},
                        {   'example': 'The model was trained on a massive '
                                       'dataset.',
                            'ipa': '/ˈdeɪtəset/',
                            'meaning': 'Tập dữ liệu',
                            'word': 'Dataset'},
                        {   'example': 'We perform optimization on the search '
                                       'logic.',
                            'ipa': '/ˌɒptɪmaɪˈzeɪʃn/',
                            'meaning': 'Sự tối ưu hóa',
                            'word': 'Optimization'},
                        {   'example': 'The algorithm handles image '
                                       'classification.',
                            'ipa': '/ˌklæsɪfɪˈkeɪʃn/',
                            'meaning': 'Sự phân loại',
                            'word': 'Classification'},
                        {   'example': 'ChatGPT is a popular generative AI '
                                       'application.',
                            'ipa': '/ˈdʒenərətɪv/',
                            'meaning': 'Tạo sinh',
                            'word': 'Generative'},
                        {   'example': 'Autonomous vehicles are being tested '
                                       'on public roads.',
                            'ipa': '/ɔːˈtɒnəməs/',
                            'meaning': 'Tự trị, tự lái',
                            'word': 'Autonomous'},
                        {   'example': 'A deep network can learn complex '
                                       'patterns from large datasets.',
                            'ipa': '/diːp ˈnɛtwɜːk/',
                            'meaning': 'Mạng nơ-ron sâu nhiều lớp',
                            'word': 'Deep network'},
                        {   'example': 'Pattern recognition is widely used in '
                                       'facial scan technology.',
                            'ipa': '/ˈpæt.ən ˌrek.əɡˈnɪʃ.ən/',
                            'meaning': 'Sự nhận dạng khuôn mẫu',
                            'word': 'Pattern recognition'},
                        {   'example': 'Linguists use a corpus to study '
                                       'language patterns.',
                            'ipa': '/ˈkɔːpəs/',
                            'meaning': 'Kho ngữ liệu văn bản',
                            'word': 'Corpus'},
                        {   'example': 'Engine tuning can improve fuel '
                                       'efficiency and performance.',
                            'ipa': '/ˈtʃuː.nɪŋ/',
                            'meaning': 'Sự căn chỉnh, tinh chỉnh hiệu năng',
                            'word': 'Tuning'},
                        {   'example': 'The library uses a strict system for '
                                       'book categorization.',
                            'ipa': '/ˌkæt.ə.ɡər.aɪˈzeɪ.ʃən/',
                            'meaning': 'Sự chia nhóm, phân loại danh mục',
                            'word': 'Categorization'},
                        {   'example': 'You can import this python library to '
                                       'handle HTTP requests.',
                            'ipa': '/ˈlaɪ.brər.i/',
                            'meaning': 'Thư viện mã nguồn phần mềm',
                            'word': 'Library_1'},
                        {   'example': 'She has many creative ideas for the '
                                       'new marketing campaign.',
                            'ipa': '/kriˈeɪ.tɪv/',
                            'meaning': 'Sáng tạo, mang tính sáng tạo',
                            'word': 'Creative'},
                        {   'example': 'Self-driving cars are expected to '
                                       'reduce traffic accidents.',
                            'ipa': '/ˌselfˈdraɪ.vɪŋ/',
                            'meaning': 'Tự lái, tự điều khiển hành trình',
                            'word': 'Self-driving'},
                        {   'example': 'Transformer architecture powers modern '
                                       'AI.',
                            'ipa': '/trænsˈfɔːr.mər ˈɑːr.kɪ.tɛk.tʃər/',
                            'meaning': 'kiến trúc transformer nền tảng cho GPT',
                            'word': 'transformer architecture'},
                        {   'example': 'Self-attention weighs word '
                                       'relationships.',
                            'ipa': '/sɛlf əˈtɛn.ʃən/',
                            'meaning': 'cơ chế tự chú ý trong transformer',
                            'word': 'self-attention'},
                        {   'example': 'The encoder maps text to a vector.',
                            'ipa': '/ɪnˈkoʊ.dər/',
                            'meaning': 'bộ mã hóa biểu diễn đầu vào',
                            'word': 'encoder'},
                        {   'example': 'The decoder generates output text.',
                            'ipa': '/dɪˈkoʊ.dər/',
                            'meaning': 'bộ giải mã tạo ra đầu ra',
                            'word': 'decoder'},
                        {   'example': 'Regularization prevents overfitting.',
                            'ipa': '/ˌrɛɡ.jʊ.lər.aɪˈzeɪ.ʃən/',
                            'meaning': 'điều chuẩn hóa tránh quá khớp mô hình',
                            'word': 'regularization'},
                        {   'example': 'Dropout reduces overfitting in '
                                       'networks.',
                            'ipa': '/ˈdrɒp.aʊt/',
                            'meaning': 'kỹ thuật bỏ ngẫu nhiên nơ-ron học',
                            'word': 'dropout'},
                        {   'example': 'ReLU is a common activation function.',
                            'ipa': '/ˌæk.tɪˈveɪ.ʃən ˈfʌŋk.ʃən/',
                            'meaning': 'hàm kích hoạt phi tuyến trong mạng',
                            'word': 'activation function'},
                        {   'example': 'Weights are updated during training.',
                            'ipa': '/weɪt/',
                            'meaning': 'trọng số của kết nối nơ-ron',
                            'word': 'weight'},
                        {   'example': 'Reduce bias to improve fairness.',
                            'ipa': '/ˈbaɪ.əs/',
                            'meaning': 'sai lệch trong mô hình thống kê',
                            'word': 'bias'},
                        {   'example': 'Explainability is crucial for medical '
                                       'AI.',
                            'ipa': '/ɪkˌspleɪ.nə.ˈbɪl.ɪ.ti/',
                            'meaning': 'khả năng giải thích quyết định AI',
                            'word': 'explainability'},
                        {   'example': 'Model interpretability builds user '
                                       'trust.',
                            'ipa': '/ɪnˌtɜːr.prɪ.tə.ˈbɪl.ɪ.ti/',
                            'meaning': 'khả năng diễn giải hành vi mô hình',
                            'word': 'interpretability'},
                        {   'example': 'Ensure fairness in AI hiring tools.',
                            'ipa': '/ˈfɛr.nɪs/',
                            'meaning': 'tính công bằng trong quyết định AI',
                            'word': 'fairness'},
                        {   'example': 'Large models can hallucinate facts.',
                            'ipa': '/həˌluː.sɪˈneɪ.ʃən/',
                            'meaning': 'hiện tượng AI bịa đặt thông tin sai',
                            'word': 'hallucination'},
                        {   'example': 'Grounding reduces AI hallucinations.',
                            'ipa': '/ˈɡraʊn.dɪŋ/',
                            'meaning': 'neo đậu AI vào thực tế đáng tin cậy',
                            'word': 'grounding'},
                        {   'example': 'Multimodal AI understands text and '
                                       'images.',
                            'ipa': '/ˌmʌl.tɪˈmoʊ.dəl/',
                            'meaning': 'đa phương thức xử lý văn bản và hình '
                                       'ảnh',
                            'word': 'multimodal'},
                        {   'example': 'Zero-shot learning requires no '
                                       'training examples.',
                            'ipa': '/ˈzɪər.oʊ ʃɒt ˈlɜːr.nɪŋ/',
                            'meaning': 'học không cần ví dụ mẫu huấn luyện',
                            'word': 'zero-shot learning'},
                        {   'example': 'Few-shot learning needs minimal data.',
                            'ipa': '/fjuː ʃɒt ˈlɜːr.nɪŋ/',
                            'meaning': 'học từ rất ít ví dụ mẫu nhỏ',
                            'word': 'few-shot learning'},
                        {   'example': 'In-context learning uses examples in '
                                       'prompts.',
                            'ipa': '/ɪn ˈkɒn.tɛkst ˈlɜːr.nɪŋ/',
                            'meaning': 'học từ ngữ cảnh trong prompt đầu vào',
                            'word': 'in-context learning'},
                        {   'example': 'RAG improves factual accuracy in '
                                       'chatbots.',
                            'ipa': '/rɪˈtriː.vəl ˈɔːɡ.mɛn.tɪd ˌdʒɛn.əˈreɪ.ʃən/',
                            'meaning': 'tăng cường tạo sinh bằng truy xuất '
                                       'thông tin',
                            'word': 'retrieval-augmented generation'},
                        {   'example': 'Knowledge graphs support AI reasoning.',
                            'ipa': '/ˈnɒl.ɪdʒ ɡrɑːf/',
                            'meaning': 'đồ thị tri thức liên kết các thực thể',
                            'word': 'knowledge graph'},
                        {   'example': 'GPT is a large foundation model.',
                            'ipa': '/faʊnˈdeɪ.ʃən ˈmɒd.əl/',
                            'meaning': 'mô hình nền tảng lớn cho nhiều tác vụ',
                            'word': 'foundation model'},
                        {   'example': "Stay within the model's token limit.",
                            'ipa': '/ˈtoʊ.kən ˈlɪm.ɪt/',
                            'meaning': 'giới hạn số token đầu vào mô hình',
                            'word': 'token limit'},
                        {   'example': 'Reduce latency for a faster user '
                                       'experience.',
                            'ipa': '/ˈleɪ.tən.si/',
                            'meaning': 'độ trễ phản hồi của hệ thống AI',
                            'word': 'latency'},
                        {   'example': 'High throughput is needed for '
                                       'large-scale AI.',
                            'ipa': '/ˈθruː.pʊt/',
                            'meaning': 'lưu lượng xử lý của hệ thống AI',
                            'word': 'throughput'},
                        {   'example': 'Model pruning reduces inference cost.',
                            'ipa': '/ˈpruː.nɪŋ/',
                            'meaning': 'cắt tỉa mô hình giảm kích thước và chi '
                                       'phí',
                            'word': 'pruning'},
                        {   'example': 'Quantization compresses model size.',
                            'ipa': '/ˌkwɒn.tɪˈzeɪ.ʃən/',
                            'meaning': 'lượng hóa giảm độ chính xác để tiết '
                                       'kiệm',
                            'word': 'quantization'},
                        {   'example': 'Knowledge distillation creates smaller '
                                       'models.',
                            'ipa': '/ˌdɪs.tɪˈleɪ.ʃən/',
                            'meaning': 'chắt lọc kiến thức từ mô hình lớn sang '
                                       'nhỏ',
                            'word': 'distillation'},
                        {   'example': 'Synthetic data augments training '
                                       'datasets.',
                            'ipa': '/sɪnˈθɛt.ɪk ˈdeɪ.tə/',
                            'meaning': 'dữ liệu tổng hợp nhân tạo thay thế '
                                       'thật',
                            'word': 'synthetic data'},
                        {   'example': 'Data augmentation improves model '
                                       'robustness.',
                            'ipa': '/ˈdeɪ.tə ˌɔːɡ.mɛnˈteɪ.ʃən/',
                            'meaning': 'tăng cường dữ liệu mở rộng tập huấn '
                                       'luyện',
                            'word': 'data augmentation'},
                        {   'example': 'Anomaly detection flags unusual '
                                       'behavior.',
                            'ipa': '/əˈnɒm.ə.li dɪˈtɛk.ʃən/',
                            'meaning': 'phát hiện bất thường trong dữ liệu',
                            'word': 'anomaly detection'},
                        {   'example': 'Clustering groups similar data points.',
                            'ipa': '/ˈklʌs.tər.ɪŋ/',
                            'meaning': 'phân cụm dữ liệu không có nhãn',
                            'word': 'clustering'},
                        {   'example': 'PCA is a dimensionality reduction '
                                       'technique.',
                            'ipa': '/daɪˌmɛn.ʃəˈnæl.ɪ.ti rɪˈdʌk.ʃən/',
                            'meaning': 'giảm số chiều dữ liệu trong học máy',
                            'word': 'dimensionality reduction'},
                        {   'example': 'More attention heads improve '
                                       'performance.',
                            'ipa': '/əˈtɛn.ʃən hɛd/',
                            'meaning': 'đầu chú ý trong kiến trúc transformer',
                            'word': 'attention head'},
                        {   'example': 'Positional encoding helps model '
                                       'understand order.',
                            'ipa': '/pəˈzɪʃ.ən.əl ɪnˈkoʊ.dɪŋ/',
                            'meaning': 'mã hóa vị trí token trong transformer',
                            'word': 'positional encoding'},
                        {   'example': 'Knowledge distillation creates '
                                       'efficient small models.',
                            'ipa': '/ˈnɒl.ɪdʒ ˌdɪs.tɪˈleɪ.ʃən/',
                            'meaning': 'chắt lọc tri thức từ mô hình lớn sang '
                                       'nhỏ',
                            'word': 'knowledge distillation'}],
              'C1': [   {   'example': 'Cognitive computing mimics human '
                                       'thought.',
                            'ipa': '/ˈkɒɡnətɪv kəmˈpjuːtɪŋ/',
                            'meaning': 'Điện toán nhận thức',
                            'word': 'Cognitive computing'},
                        {   'example': 'Deep learning achieves state of the '
                                       'art results.',
                            'ipa': '/diːp ˈlɜːnɪŋ/',
                            'meaning': 'Học sâu',
                            'word': 'Deep learning'},
                        {   'example': 'AlphaGo uses reinforcement learning.',
                            'ipa': '/ˌriːɪnˈfɔːsmənt/',
                            'meaning': 'Sự tăng cường',
                            'word': 'Reinforcement'},
                        {   'example': 'Modern LLMs are built on the '
                                       'Transformer architecture.',
                            'ipa': '/trænsˈfɔːməs/',
                            'meaning': 'Mô hình Transformer',
                            'word': 'Transformers'},
                        {   'example': 'Supervised learning requires labeled '
                                       'training data.',
                            'ipa': '/ˈsuːpəvaɪzd/',
                            'meaning': 'Có giám sát',
                            'word': 'Supervised'},
                        {   'example': 'Natural Language Processing makes '
                                       'chatbots smarter.',
                            'ipa': '/ˈnætʃrəl ˈlæŋɡwɪdʒ/',
                            'meaning': 'Ngôn ngữ tự nhiên',
                            'word': 'Natural Language'},
                        {   'example': 'Tuning hyperparameters is essential '
                                       'for model training.',
                            'ipa': '/ˌhaɪpəpəˈræmɪtəz/',
                            'meaning': 'Siêu tham số',
                            'word': 'Hyperparameters'},
                        {   'example': 'Backpropagation is used to train deep '
                                       'neural networks.',
                            'ipa': '/ˌbækprɒpəˈɡeɪʃn/',
                            'meaning': 'Lan truyền ngược',
                            'word': 'Backpropagation'},
                        {   'example': 'Researchers are developing an '
                                       'artificial brain to simulate human '
                                       'cognition.',
                            'ipa': '/ɑːˈtɪfɪʃəl breɪn/',
                            'meaning': 'Não bộ nhân tạo, trí tuệ nhân tạo',
                            'word': 'Artificial brain'},
                        {   'example': 'Representation learning discovers '
                                       'useful patterns in raw data.',
                            'ipa': '/ˌrep.rɪ.zenˈteɪ.ʃən ˈlɜː.nɪŋ/',
                            'meaning': 'Học biểu diễn tính năng',
                            'word': 'Representation learning'},
                        {   'example': 'Positive feedback loops can accelerate '
                                       'system growth.',
                            'ipa': '/ˈfiːd.bæk luːps/',
                            'meaning': 'Vòng phản hồi điều khiển',
                            'word': 'Feedback loops'},
                        {   'example': 'Attention mechanisms help neural '
                                       'networks focus on relevant words.',
                            'ipa': '/əˈten.ʃən ˈmek.ə.nɪz.əmz/',
                            'meaning': 'Cơ chế chú ý trong mạng nơ-ron',
                            'word': 'Attention mechanisms'},
                        {   'example': 'Labeled learning is highly accurate '
                                       'but requires manual effort.',
                            'ipa': '/ˈleɪ.bəld ˈlɜː.nɪŋ/',
                            'meaning': 'Học máy có gắn nhãn dữ liệu',
                            'word': 'Labeled learning'},
                        {   'example': 'The computer system can transcribe '
                                       'human speech in real time.',
                            'ipa': '/ˈhjuː.mən spiːtʃ/',
                            'meaning': 'Tiếng nói của con người',
                            'word': 'Human speech'},
                        {   'example': 'Adjusting model settings can '
                                       'significantly change the accuracy.',
                            'ipa': '/ˈmɒd.əl ˈset.ɪŋz/',
                            'meaning': 'Thiết lập cấu hình mô hình',
                            'word': 'Model settings'},
                        {   'example': 'Error propagation during calculations '
                                       'can lead to incorrect results.',
                            'ipa': '/ˈer.ər ˌprɒp.əˈɡeɪ.ʃən/',
                            'meaning': 'Sự lan truyền sai số',
                            'word': 'Error propagation'},
                        {   'example': 'AI alignment ensures safe behavior.',
                            'ipa': '/əˈlaɪn.mənt/',
                            'meaning': 'căn chỉnh AI với giá trị con người',
                            'word': 'alignment'},
                        {   'example': 'Constitutional AI reduces harmful '
                                       'outputs.',
                            'ipa': '/ˌkɒn.stɪˈtjuː.ʃən.əl eɪ aɪ/',
                            'meaning': 'AI tuân theo bộ nguyên tắc đạo đức cố '
                                       'định',
                            'word': 'constitutional AI'},
                        {   'example': 'RLHF aligns ChatGPT to human '
                                       'preferences.',
                            'ipa': '/ˌɑːr.ɛl.eɪtʃˈɛf/',
                            'meaning': 'học tăng cường từ phản hồi của con '
                                       'người',
                            'word': 'RLHF'},
                        {   'example': 'Emergent behavior appears at scale.',
                            'ipa': '/ɪˈmɜːr.dʒənt bɪˈheɪ.vjər/',
                            'meaning': 'hành vi nổi sinh bất ngờ từ mô hình '
                                       'lớn',
                            'word': 'emergent behavior'},
                        {   'example': 'Chain-of-thought prompting improves '
                                       'reasoning.',
                            'ipa': '/tʃeɪn əv θɔːt/',
                            'meaning': 'kỹ thuật prompt khai thác lý luận tuần '
                                       'tự',
                            'word': 'chain-of-thought'},
                        {   'example': 'Advanced AI demonstrates multi-step '
                                       'reasoning.',
                            'ipa': '/ˈriː.zən.ɪŋ/',
                            'meaning': 'suy luận logic từng bước của AI',
                            'word': 'reasoning'},
                        {   'example': 'Meta-learning enables faster '
                                       'adaptation.',
                            'ipa': '/ˈmɛt.ə ˈlɜːr.nɪŋ/',
                            'meaning': 'học cách học nhanh hơn với ít dữ liệu',
                            'word': 'meta-learning'},
                        {   'example': 'Continual learning avoids catastrophic '
                                       'forgetting.',
                            'ipa': '/kənˈtɪn.jʊ.əl ˈlɜːr.nɪŋ/',
                            'meaning': 'học liên tục mà không quên kiến thức '
                                       'cũ',
                            'word': 'continual learning'},
                        {   'example': 'Federated learning protects user '
                                       'privacy.',
                            'ipa': '/ˈfɛd.ər.eɪ.tɪd ˈlɜːr.nɪŋ/',
                            'meaning': 'học liên kết bảo toàn riêng tư dữ liệu',
                            'word': 'federated learning'},
                        {   'example': 'Differential privacy adds statistical '
                                       'noise.',
                            'ipa': '/ˌdɪf.ər.ˈɛn.ʃəl ˈprɪv.ə.si/',
                            'meaning': 'quyền riêng tư vi phân bảo vệ dữ liệu',
                            'word': 'differential privacy'},
                        {   'example': 'Adversarial attacks fool image '
                                       'classifiers.',
                            'ipa': '/ˌæd.vəˈseər.i.əl əˈtæk/',
                            'meaning': 'tấn công đối kháng nhằm đánh lừa mô '
                                       'hình',
                            'word': 'adversarial attack'},
                        {   'example': 'Model robustness is tested with edge '
                                       'cases.',
                            'ipa': '/roʊˈbʌst.nɪs/',
                            'meaning': 'tính bền vững trước các đầu vào bất '
                                       'thường',
                            'word': 'robustness'},
                        {   'example': 'Good generalization is key for '
                                       'deployment.',
                            'ipa': '/ˌdʒɛn.ər.əl.aɪˈzeɪ.ʃən/',
                            'meaning': 'khả năng tổng quát hóa sang dữ liệu '
                                       'mới',
                            'word': 'generalization'},
                        {   'example': 'CNNs have a strong inductive bias for '
                                       'images.',
                            'ipa': '/ɪnˈdʌk.tɪv ˈbaɪ.əs/',
                            'meaning': 'thiên kiến quy nạp trong kiến trúc mô '
                                       'hình',
                            'word': 'inductive bias'},
                        {   'example': 'Causal inference goes beyond '
                                       'correlation.',
                            'ipa': '/ˈkɔː.zəl ˈɪn.fər.əns/',
                            'meaning': 'suy luận nhân quả phân biệt nguyên '
                                       'nhân kết quả',
                            'word': 'causal inference'},
                        {   'example': 'Counterfactual reasoning asks what if '
                                       'scenarios.',
                            'ipa': '/ˌkaʊn.tərˈfæk.tʃʊ.əl ˈriː.zən.ɪŋ/',
                            'meaning': 'lý luận phản thực tế về tình huống giả '
                                       'định',
                            'word': 'counterfactual reasoning'},
                        {   'example': 'Mechanistic interpretability reveals '
                                       'model circuits.',
                            'ipa': '/ˌmɛk.ə.ˈnɪs.tɪk ɪnˌtɜːr.prɪ.tə.ˈbɪl.ɪ.ti/',
                            'meaning': 'diễn giải cơ chế nội tại của mô hình',
                            'word': 'mechanistic interpretability'},
                        {   'example': 'Superalignment research aims to '
                                       'control AGI.',
                            'ipa': '/ˌsuː.pər.əˈlaɪn.mənt/',
                            'meaning': 'căn chỉnh AI siêu thông minh với lợi '
                                       'ích nhân loại',
                            'word': 'superalignment'},
                        {   'example': 'AGI would match human-level cognition.',
                            'ipa': '/ˌeɪ.dʒiːˈaɪ/',
                            'meaning': 'trí tuệ tổng hợp ở mức độ con người',
                            'word': 'AGI'},
                        {   'example': 'ASI could surpass all human '
                                       'intelligence.',
                            'ipa': '/ˌeɪ.ɛsˈaɪ/',
                            'meaning': 'trí tuệ siêu việt vượt trội hơn con '
                                       'người',
                            'word': 'ASI'},
                        {   'example': 'Mixture of experts scales model '
                                       'capacity.',
                            'ipa': '/ˈmɪks.tʃər əv ˈɛk.spɜːrts/',
                            'meaning': 'kiến trúc kết hợp nhiều mô hình chuyên '
                                       'biệt',
                            'word': 'mixture of experts'},
                        {   'example': 'Sparse models reduce computation cost.',
                            'ipa': '/spɑːrs ˈmɒd.əl/',
                            'meaning': 'mô hình thưa chỉ kích hoạt một phần',
                            'word': 'sparse model'},
                        {   'example': 'A larger context window handles longer '
                                       'texts.',
                            'ipa': '/ˈkɒn.tɛkst ˈwɪn.doʊ/',
                            'meaning': 'cửa sổ ngữ cảnh tối đa mô hình xử lý '
                                       'được',
                            'word': 'context window'},
                        {   'example': 'Tool use lets AI search the web.',
                            'ipa': '/tuːl juːz/',
                            'meaning': 'khả năng AI gọi công cụ bên ngoài tự '
                                       'động',
                            'word': 'tool use'},
                        {   'example': 'Agentic AI plans and executes '
                                       'multi-step tasks.',
                            'ipa': '/eɪˈdʒɛn.tɪk eɪ aɪ/',
                            'meaning': 'AI hành động tự chủ hoàn thành mục '
                                       'tiêu',
                            'word': 'agentic AI'},
                        {   'example': 'Multi-agent systems coordinate '
                                       'specialized AIs.',
                            'ipa': '/ˌmʌl.tiˈeɪ.dʒənt ˈsɪs.təm/',
                            'meaning': 'hệ thống nhiều agent AI phối hợp hoạt '
                                       'động',
                            'word': 'multi-agent system'},
                        {   'example': "Reward shaping guides the agent's "
                                       'learning.',
                            'ipa': '/rɪˈwɔːrd ˈʃeɪ.pɪŋ/',
                            'meaning': 'tạo hình phần thưởng học tăng cường '
                                       'tinh vi',
                            'word': 'reward shaping'},
                        {   'example': 'Policy gradient methods train RL '
                                       'agents.',
                            'ipa': '/ˈpɒl.ɪ.si ˈɡreɪ.di.ənt/',
                            'meaning': 'gradient chính sách tối ưu hóa hành '
                                       'động',
                            'word': 'policy gradient'},
                        {   'example': 'The value function estimates long-term '
                                       'reward.',
                            'ipa': '/ˈvæl.juː ˈfʌŋk.ʃən/',
                            'meaning': 'hàm giá trị ước tính lợi ích trạng '
                                       'thái',
                            'word': 'value function'},
                        {   'example': 'Monte Carlo methods estimate expected '
                                       'returns.',
                            'ipa': '/ˌmɒn.ti ˈkɑːr.loʊ/',
                            'meaning': 'phương pháp lấy mẫu ngẫu nhiên trong '
                                       'RL',
                            'word': 'Monte Carlo'},
                        {   'example': 'More compute leads to better AI '
                                       'models.',
                            'ipa': '/kəmˈpjuːt/',
                            'meaning': 'sức mạnh tính toán phần cứng cho AI',
                            'word': 'compute'},
                        {   'example': 'Training GPT-4 required quadrillions '
                                       'of FLOPs.',
                            'ipa': '/flɒp/',
                            'meaning': 'phép tính dấu phẩy động đo lường tính '
                                       'toán',
                            'word': 'FLOP'},
                        {   'example': 'Scaling laws predict model '
                                       'improvements.',
                            'ipa': '/ˈskeɪ.lɪŋ lɔː/',
                            'meaning': 'quy luật mở rộng hiệu suất AI theo tài '
                                       'nguyên',
                            'word': 'scaling law'},
                        {   'example': 'Capability elicitation finds hidden '
                                       'model skills.',
                            'ipa': '/ˌkeɪ.pə.ˈbɪl.ɪ.ti ɪˌlɪs.ɪˈteɪ.ʃən/',
                            'meaning': 'khai thác khả năng tiềm ẩn của mô hình',
                            'word': 'capability elicitation'}]},
    'business': {   'A1': [   {   'example': 'The profit margin is 20%.',
                                  'ipa': '/ˈprɒf.ɪt/',
                                  'meaning': 'lợi nhuận sau chi phí',
                                  'word': 'profit'},
                              {   'example': 'The company made a loss last '
                                             'year.',
                                  'ipa': '/lɒs/',
                                  'meaning': 'thua lỗ kinh doanh',
                                  'word': 'loss'},
                              {   'example': 'Keep money in the bank.',
                                  'ipa': '/bæŋk/',
                                  'meaning': 'ngân hàng tài chính',
                                  'word': 'bank'},
                              {   'example': 'Take a loan to start business.',
                                  'ipa': '/loʊn/',
                                  'meaning': 'khoản vay ngân hàng',
                                  'word': 'loan'},
                              {   'example': 'Send an invoice to the client.',
                                  'ipa': '/ˈɪn.vɔɪs/',
                                  'meaning': 'hóa đơn xuất bán',
                                  'word': 'invoice'},
                              {   'example': 'Receive payment within 30 days.',
                                  'ipa': '/ˈpeɪ.mənt/',
                                  'meaning': 'khoản thanh toán',
                                  'word': 'payment'},
                              {   'example': 'Find a reliable business '
                                             'partner.',
                                  'ipa': '/ˈpɑːrt.nər/',
                                  'meaning': 'đối tác kinh doanh',
                                  'word': 'partner'},
                              {   'example': 'Write a business plan.',
                                  'ipa': '/plæn/',
                                  'meaning': 'kế hoạch kinh doanh',
                                  'word': 'plan'},
                              {   'example': 'Set clear business goals.',
                                  'ipa': '/ɡoʊl/',
                                  'meaning': 'mục tiêu kinh doanh',
                                  'word': 'goal'},
                              {   'example': 'Aim for 20% growth.',
                                  'ipa': '/ɡroʊθ/',
                                  'meaning': 'tăng trưởng doanh nghiệp',
                                  'word': 'growth'},
                              {   'example': 'Success requires hard work.',
                                  'ipa': '/səkˈsɛs/',
                                  'meaning': 'thành công kinh doanh',
                                  'word': 'success'},
                              {   'example': 'Learn from every failure.',
                                  'ipa': '/feɪl/',
                                  'meaning': 'thất bại trong kinh doanh',
                                  'word': 'fail'},
                              {   'example': 'Earn more by working smart.',
                                  'ipa': '/ɜːrn/',
                                  'meaning': 'kiếm tiền thu nhập',
                                  'word': 'earn'},
                              {   'example': 'Spend wisely on marketing.',
                                  'ipa': '/spɛnd/',
                                  'meaning': 'tiêu tiền chi phí',
                                  'word': 'spend'},
                              {   'example': 'Invest in good people.',
                                  'ipa': '/ɪnˈvɛst/',
                                  'meaning': 'đầu tư tạo lợi nhuận',
                                  'word': 'invest'},
                              {   'example': 'Stick to the monthly budget.',
                                  'ipa': '/ˈbʌdʒ.ɪt/',
                                  'meaning': 'ngân sách phân bổ chi tiêu',
                                  'word': 'budget'},
                              {   'example': 'Keep every receipt for taxes.',
                                  'ipa': '/rɪˈsiːt/',
                                  'meaning': 'hóa đơn biên lai mua hàng',
                                  'word': 'receipt'},
                              {   'example': 'Offer fast free delivery.',
                                  'ipa': '/dɪˈlɪv.ər.i/',
                                  'meaning': 'giao hàng đến khách',
                                  'word': 'delivery'},
                              {   'example': 'The owner manages the team.',
                                  'ipa': '/ˈoʊ.nər/',
                                  'meaning': 'chủ doanh nghiệp',
                                  'word': 'owner'},
                              {   'example': 'Hire friendly staff.',
                                  'ipa': '/stɑːf/',
                                  'meaning': 'đội ngũ nhân viên',
                                  'word': 'staff'},
                              {   'example': 'Fire employees who underperform.',
                                  'ipa': '/faɪər/',
                                  'meaning': 'sa thải nhân viên',
                                  'word': 'fire'},
                              {   'example': 'Grow the business steadily.',
                                  'ipa': '/ɡroʊ/',
                                  'meaning': 'mở rộng tăng trưởng',
                                  'word': 'grow'},
                              {   'example': 'Trade between countries benefits '
                                             'everyone.',
                                  'ipa': '/treɪd/',
                                  'meaning': 'giao thương buôn bán',
                                  'word': 'trade'},
                              {   'example': 'We import goods from China.',
                                  'ipa': '/ɡʊdz/',
                                  'meaning': 'hàng hóa vật chất',
                                  'word': 'goods'},
                              {   'example': 'The tech industry grows fast.',
                                  'ipa': '/ˈɪn.dəs.tri/',
                                  'meaning': 'ngành công nghiệp kinh doanh',
                                  'word': 'industry'},
                              {   'example': 'We export goods to Europe.',
                                  'ipa': '/ˈɛks.pɔːt/',
                                  'meaning': 'xuất khẩu hàng hóa',
                                  'word': 'export'},
                              {   'example': 'We import raw materials.',
                                  'ipa': '/ˈɪm.pɔːt/',
                                  'meaning': 'nhập khẩu hàng hóa',
                                  'word': 'import'},
                              {   'example': 'Check the price tag first.',
                                  'ipa': '/praɪs tæɡ/',
                                  'meaning': 'nhãn giá sản phẩm',
                                  'word': 'price tag'},
                              {   'example': 'Both parties agree on the price.',
                                  'ipa': '/əˈɡriː/',
                                  'meaning': 'đồng ý thỏa thuận',
                                  'word': 'agree'},
                              {   'example': 'Sign the agreement today.',
                                  'ipa': '/saɪn/',
                                  'meaning': 'ký tên hợp đồng',
                                  'word': 'sign'},
                              {   'example': 'Send a business letter.',
                                  'ipa': '/ˈlɛt.ər/',
                                  'meaning': 'thư từ công văn',
                                  'word': 'letter'},
                              {   'example': 'Write your business address.',
                                  'ipa': '/ˈæd.rɛs/',
                                  'meaning': 'địa chỉ văn phòng',
                                  'word': 'address'},
                              {   'example': 'Make a phone call to the client.',
                                  'ipa': '/foʊn kɔːl/',
                                  'meaning': 'cuộc gọi điện thoại',
                                  'word': 'phone call'},
                              {   'example': 'Solve the customer problem fast.',
                                  'ipa': '/ˈprɒb.ləm/',
                                  'meaning': 'vấn đề kinh doanh cần giải quyết',
                                  'word': 'problem'},
                              {   'example': 'Find a solution quickly.',
                                  'ipa': '/səˈluː.ʃən/',
                                  'meaning': 'giải pháp kinh doanh hiệu quả',
                                  'word': 'solution'},
                              {   'example': 'Share your business idea.',
                                  'ipa': '/aɪˈdɪər/',
                                  'meaning': 'ý tưởng kinh doanh mới',
                                  'word': 'idea'},
                              {   'example': 'Change the strategy if needed.',
                                  'ipa': '/tʃeɪndʒ/',
                                  'meaning': 'sự thay đổi kinh doanh',
                                  'word': 'change'},
                              {   'example': 'Make a list of tasks.',
                                  'ipa': '/lɪst/',
                                  'meaning': 'danh sách công việc cần làm',
                                  'word': 'list'},
                              {   'example': 'Make the right business choice.',
                                  'ipa': '/tʃɔɪs/',
                                  'meaning': 'lựa chọn quyết định kinh doanh',
                                  'word': 'choice'},
                              {   'example': 'Build a strong brand name.',
                                  'ipa': '/brænd neɪm/',
                                  'meaning': 'tên thương hiệu sản phẩm',
                                  'word': 'brand name'},
                              {   'example': 'Give your business card to '
                                             'clients.',
                                  'ipa': '/ˈbɪz.nɪs kɑːrd/',
                                  'meaning': 'danh thiếp kinh doanh',
                                  'word': 'business card'},
                              {   'example': 'Use a cash register at checkout.',
                                  'ipa': '/kæʃ ˈrɛdʒ.ɪs.tər/',
                                  'meaning': 'máy tính tiền thu ngân',
                                  'word': 'cash register'},
                              {   'example': 'Check the price list before '
                                             'ordering.',
                                  'ipa': '/praɪs lɪst/',
                                  'meaning': 'bảng giá sản phẩm',
                                  'word': 'price list'},
                              {   'example': 'Profit sharing motivates staff.',
                                  'ipa': '/ˈprɒf.ɪt ˈʃɛər.ɪŋ/',
                                  'meaning': 'chia sẻ lợi nhuận với nhân viên',
                                  'word': 'profit sharing'},
                              {   'example': 'Working hours are nine to five.',
                                  'ipa': '/ˈwɜːr.kɪŋ aʊərz/',
                                  'meaning': 'giờ làm việc hành chính',
                                  'word': 'working hours'},
                              {   'example': 'Apply for a business license '
                                             'first.',
                                  'ipa': '/ˈbɪz.nɪs ˈlaɪ.səns/',
                                  'meaning': 'giấy phép kinh doanh',
                                  'word': 'business license'},
                              {   'example': 'The opening hours are posted on '
                                             'the door.',
                                  'ipa': '/ˈoʊ.pən.ɪŋ aʊərz/',
                                  'meaning': 'giờ mở cửa kinh doanh',
                                  'word': 'opening hours'},
                              {   'example': 'Reach your monthly sales target.',
                                  'ipa': '/seɪlz ˈtɑːr.ɡɪt/',
                                  'meaning': 'mục tiêu doanh số bán hàng',
                                  'word': 'sales target'},
                              {   'example': 'Calculate your net income '
                                             'monthly.',
                                  'ipa': '/nɛt ˈɪn.kʌm/',
                                  'meaning': 'thu nhập ròng sau thuế',
                                  'word': 'net income'},
                              {   'example': 'Identify multiple revenue '
                                             'streams.',
                                  'ipa': '/ˈrɛv.ɪ.njuː striːm/',
                                  'meaning': 'dòng doanh thu của doanh nghiệp',
                                  'word': 'revenue stream'}],
                    'A2': [   {   'example': 'Cut unnecessary expenses.',
                                  'ipa': '/ɪkˈspɛn.sɪz/',
                                  'meaning': 'chi phí vận hành',
                                  'word': 'expenses'},
                              {   'example': 'Net profit is what you keep.',
                                  'ipa': '/nɛt ˈprɒf.ɪt/',
                                  'meaning': 'lợi nhuận ròng sau tất cả chi '
                                             'phí',
                                  'word': 'net profit'},
                              {   'example': 'We reached breakeven in six '
                                             'months.',
                                  'ipa': '/ˌbreɪkˈiː.vən/',
                                  'meaning': 'hòa vốn không lãi không lỗ',
                                  'word': 'breakeven'},
                              {   'example': 'Raise startup capital from '
                                             'investors.',
                                  'ipa': '/ˈstɑːr.tʌp ˈkæp.ɪ.təl/',
                                  'meaning': 'vốn ban đầu khởi nghiệp',
                                  'word': 'startup capital'},
                              {   'example': 'Find an angel investor.',
                                  'ipa': '/ɪnˈvɛs.tər/',
                                  'meaning': 'nhà đầu tư rót vốn',
                                  'word': 'investor'},
                              {   'example': 'The startup valuation is 10 '
                                             'million.',
                                  'ipa': '/ˌvæl.jʊˈeɪ.ʃən/',
                                  'meaning': 'định giá doanh nghiệp',
                                  'word': 'valuation'},
                              {   'example': 'Secure funding before launching.',
                                  'ipa': '/ˈfʌn.dɪŋ/',
                                  'meaning': 'nguồn tài trợ vốn',
                                  'word': 'funding'},
                              {   'example': 'The company plans an IPO next '
                                             'year.',
                                  'ipa': '/ˌaɪ.piːˈoʊ/',
                                  'meaning': 'phát hành cổ phiếu lần đầu ra '
                                             'công chúng',
                                  'word': 'IPO'},
                              {   'example': 'Obtain a business license first.',
                                  'ipa': '/ˈlaɪ.səns/',
                                  'meaning': 'giấy phép kinh doanh',
                                  'word': 'license'},
                              {   'example': 'A sole trader has full control.',
                                  'ipa': '/soʊl ˈtreɪ.dər/',
                                  'meaning': 'cá nhân kinh doanh một mình',
                                  'word': 'sole trader'},
                              {   'example': 'Register as a limited company.',
                                  'ipa': '/ˈlɪm.ɪ.tɪd ˈkʌm.pə.ni/',
                                  'meaning': 'công ty trách nhiệm hữu hạn',
                                  'word': 'limited company'},
                              {   'example': 'They run a nonprofit '
                                             'organization.',
                                  'ipa': '/nɒnˈprɒf.ɪt/',
                                  'meaning': 'tổ chức phi lợi nhuận',
                                  'word': 'nonprofit'},
                              {   'example': 'The corporation has global '
                                             'offices.',
                                  'ipa': '/ˌkɔːr.pəˈreɪ.ʃən/',
                                  'meaning': 'tập đoàn công ty lớn',
                                  'word': 'corporation'},
                              {   'example': 'Choose vendors carefully.',
                                  'ipa': '/ˈvɛn.dər/',
                                  'meaning': 'nhà cung cấp dịch vụ hàng hóa',
                                  'word': 'vendor'},
                              {   'example': 'Build strong supplier '
                                             'relationships.',
                                  'ipa': '/səˈplaɪ.ər/',
                                  'meaning': 'nhà cung ứng nguyên vật liệu',
                                  'word': 'supplier'},
                              {   'example': 'Offshoring lowers labor costs.',
                                  'ipa': '/ˈɒf.ʃɔːr.ɪŋ/',
                                  'meaning': 'chuyển hoạt động ra nước ngoài',
                                  'word': 'offshoring'},
                              {   'example': 'We operate in the B2B sector.',
                                  'ipa': '/ˌbiː.tuːˈbiː/',
                                  'meaning': 'doanh nghiệp bán cho doanh '
                                             'nghiệp',
                                  'word': 'B2B'},
                              {   'example': 'B2C needs strong branding.',
                                  'ipa': '/ˌbiː.tuːˈsiː/',
                                  'meaning': 'doanh nghiệp bán cho người tiêu '
                                             'dùng',
                                  'word': 'B2C'},
                              {   'example': 'E-commerce grew 40% last year.',
                                  'ipa': '/ˈiː.kɒm.ɜːrs/',
                                  'meaning': 'thương mại điện tử mua bán '
                                             'online',
                                  'word': 'e-commerce'},
                              {   'example': 'Brick and mortar stores still '
                                             'matter.',
                                  'ipa': '/brɪk ænd ˈmɔːr.tər/',
                                  'meaning': 'cửa hàng thực tế không phải '
                                             'online',
                                  'word': 'brick and mortar'},
                              {   'example': 'Build a strong distribution '
                                             'network.',
                                  'ipa': '/ˌdɪs.trɪˈbjuː.ʃən/',
                                  'meaning': 'phân phối hàng hóa đến khách',
                                  'word': 'distribution'},
                              {   'example': 'Efficient logistics saves money.',
                                  'ipa': '/ləˈdʒɪs.tɪks/',
                                  'meaning': 'hậu cần vận chuyển hàng hóa',
                                  'word': 'logistics'},
                              {   'example': 'Track inventory in real time.',
                                  'ipa': '/ˈɪn.vən.tɒr.i/',
                                  'meaning': 'hàng tồn kho quản lý',
                                  'word': 'inventory'},
                              {   'example': 'The warehouse holds 10,000 '
                                             'items.',
                                  'ipa': '/ˈweər.haʊs/',
                                  'meaning': 'kho hàng lưu trữ',
                                  'word': 'warehouse'},
                              {   'example': 'Improve margins by cutting '
                                             'waste.',
                                  'ipa': '/ˈmɑːr.dʒɪn/',
                                  'meaning': 'biên lợi nhuận',
                                  'word': 'margin'},
                              {   'example': 'A 50% markup covers overhead '
                                             'costs.',
                                  'ipa': '/ˈmɑːr.kʌp/',
                                  'meaning': 'mức tăng giá bán so với giá gốc',
                                  'word': 'markup'},
                              {   'example': 'Cut operating costs this '
                                             'quarter.',
                                  'ipa': '/ˈɒp.ər.eɪ.tɪŋ kɒst/',
                                  'meaning': 'chi phí hoạt động hàng ngày',
                                  'word': 'operating cost'},
                              {   'example': 'Rent is a fixed cost.',
                                  'ipa': '/fɪkst kɒst/',
                                  'meaning': 'chi phí cố định không đổi',
                                  'word': 'fixed cost'},
                              {   'example': 'Materials are variable costs.',
                                  'ipa': '/ˈveər.i.ə.bəl kɒst/',
                                  'meaning': 'chi phí biến đổi theo sản lượng',
                                  'word': 'variable cost'},
                              {   'example': 'Become the market leader.',
                                  'ipa': '/ˈmɑːr.kɪt ˈliː.dər/',
                                  'meaning': 'dẫn đầu thị trường trong ngành',
                                  'word': 'market leader'},
                              {   'example': 'Plan your market entry strategy.',
                                  'ipa': '/ˈmɑːr.kɪt ˈɛn.tri/',
                                  'meaning': 'gia nhập thị trường mới',
                                  'word': 'market entry'},
                              {   'example': 'Set a clear business strategy.',
                                  'ipa': '/ˈbɪz.nɪs ˈstræt.ɪ.dʒi/',
                                  'meaning': 'chiến lược kinh doanh tổng thể',
                                  'word': 'business strategy'},
                              {   'example': 'Write a detailed business plan.',
                                  'ipa': '/ˈbɪz.nɪs plæn/',
                                  'meaning': 'kế hoạch kinh doanh chi tiết',
                                  'word': 'business plan'},
                              {   'example': 'List all company assets.',
                                  'ipa': '/ˈæs.ɛt/',
                                  'meaning': 'tài sản của doanh nghiệp',
                                  'word': 'asset'},
                              {   'example': 'Reduce long-term liabilities.',
                                  'ipa': '/ˌlaɪ.əˈbɪl.ɪ.ti/',
                                  'meaning': 'khoản nợ nghĩa vụ tài chính',
                                  'word': 'liability'},
                              {   'example': 'Amortize intangible assets '
                                             'correctly.',
                                  'ipa': '/əˌmɔːr.tɪˈzeɪ.ʃən/',
                                  'meaning': 'phân bổ dần chi phí vô hình',
                                  'word': 'amortization'},
                              {   'example': 'Release the quarterly report.',
                                  'ipa': '/ˈkwɔːr.tər.li rɪˈpɔːrt/',
                                  'meaning': 'báo cáo tài chính hàng quý',
                                  'word': 'quarterly report'},
                              {   'example': 'Annual revenue reached 1 '
                                             'million.',
                                  'ipa': '/ˈæn.jʊ.əl ˈrɛv.ɪ.njuː/',
                                  'meaning': 'doanh thu hàng năm tổng cộng',
                                  'word': 'annual revenue'},
                              {   'example': 'The interest rate is 5% per '
                                             'year.',
                                  'ipa': '/ˈɪn.trɪst reɪt/',
                                  'meaning': 'lãi suất vay mượn ngân hàng',
                                  'word': 'interest rate'},
                              {   'example': 'Inflation affects purchasing '
                                             'power.',
                                  'ipa': '/ɪnˈfleɪ.ʃən/',
                                  'meaning': 'lạm phát giá cả tăng cao',
                                  'word': 'inflation'},
                              {   'example': 'Plan for a possible recession.',
                                  'ipa': '/rɪˈsɛʃ.ən/',
                                  'meaning': 'suy thoái kinh tế giai đoạn',
                                  'word': 'recession'},
                              {   'example': 'The revenue projection is '
                                             'optimistic.',
                                  'ipa': '/prəˈdʒɛk.ʃən/',
                                  'meaning': 'ước tính số liệu tài chính',
                                  'word': 'projection'},
                              {   'example': 'Set the operating budget '
                                             'carefully.',
                                  'ipa': '/ˈɒp.ər.eɪ.tɪŋ ˈbʌdʒ.ɪt/',
                                  'meaning': 'ngân sách hoạt động hàng năm',
                                  'word': 'operating budget'},
                              {   'example': 'Conduct a market analysis first.',
                                  'ipa': '/ˈmɑːr.kɪt əˈnæl.ɪ.sɪs/',
                                  'meaning': 'phân tích thị trường chi tiết',
                                  'word': 'market analysis'},
                              {   'example': 'Plan a market expansion '
                                             'strategy.',
                                  'ipa': '/ˈmɑːr.kɪt ɪkˈspæn.ʃən/',
                                  'meaning': 'mở rộng thị trường mới',
                                  'word': 'market expansion'},
                              {   'example': 'The profit forecast looks '
                                             'optimistic.',
                                  'ipa': '/ˈprɒf.ɪt ˈfɔːr.kæst/',
                                  'meaning': 'dự báo lợi nhuận tương lai',
                                  'word': 'profit forecast'},
                              {   'example': 'Review the financial report '
                                             'quarterly.',
                                  'ipa': '/faɪˈnæn.ʃəl rɪˈpɔːrt/',
                                  'meaning': 'báo cáo tài chính doanh nghiệp',
                                  'word': 'financial report'},
                              {   'example': 'Report gross revenue to '
                                             'investors.',
                                  'ipa': '/ɡroʊs ˈrɛv.ɪ.njuː/',
                                  'meaning': 'tổng doanh thu chưa trừ chi phí',
                                  'word': 'gross revenue'},
                              {   'example': 'Set clear business objectives.',
                                  'ipa': '/ˈbɪz.nɪs əbˈdʒɛk.tɪv/',
                                  'meaning': 'mục tiêu kinh doanh cụ thể',
                                  'word': 'business objective'},
                              {   'example': 'Operating profit excludes '
                                             'interest and tax.',
                                  'ipa': '/ˈɒp.ər.eɪ.tɪŋ ˈprɒf.ɪt/',
                                  'meaning': 'lợi nhuận từ hoạt động kinh '
                                             'doanh chính',
                                  'word': 'operating profit'}],
                    'B1': [   {   'example': 'She became a successful '
                                             'entrepreneur after launching her '
                                             'first startup.',
                                  'ipa': '/ˌɒn.trə.prəˈnɜːr/',
                                  'meaning': 'doanh nhân khởi nghiệp',
                                  'word': 'entrepreneur'},
                              {   'example': 'His startup raised $2 million in '
                                             'seed funding this year.',
                                  'ipa': '/ˈstɑːt.ʌp/',
                                  'meaning': 'công ty khởi nghiệp',
                                  'word': 'startup'},
                              {   'example': 'The company needs a clear '
                                             'strategy to enter the Asian '
                                             'market.',
                                  'ipa': '/ˈstræt.ə.dʒi/',
                                  'meaning': 'chiến lược',
                                  'word': 'strategy'},
                              {   'example': "The company's annual revenue "
                                             'increased by 20% last quarter.',
                                  'ipa': '/ˈrev.ən.juː/',
                                  'meaning': 'doanh thu',
                                  'word': 'revenue'},
                              {   'example': 'All stakeholders must approve '
                                             'the new business plan before '
                                             'implementation.',
                                  'ipa': '/ˈsteɪk.həʊl.dər/',
                                  'meaning': 'bên liên quan',
                                  'word': 'stakeholder'},
                              {   'example': 'The startup secured venture '
                                             'capital funding from a Silicon '
                                             'Valley firm.',
                                  'ipa': '/ˈven.tʃər ˈkæp.ɪ.təl/',
                                  'meaning': 'vốn đầu tư mạo hiểm',
                                  'word': 'venture capital'},
                              {   'example': 'The merger of the two banks '
                                             'created one of the largest '
                                             'financial institutions.',
                                  'ipa': '/ˈmɜː.dʒər/',
                                  'meaning': 'sự sáp nhập',
                                  'word': 'merger'},
                              {   'example': 'He opened a franchise restaurant '
                                             'in the city center.',
                                  'ipa': '/ˈfræn.tʃaɪz/',
                                  'meaning': 'nhượng quyền thương mại',
                                  'word': 'franchise'},
                              {   'example': 'The salary negotiation lasted '
                                             'two hours before both sides '
                                             'agreed.',
                                  'ipa': '/nɪˌɡəʊ.ʃiˈeɪ.ʃən/',
                                  'meaning': 'đàm phán',
                                  'word': 'negotiation'},
                              {   'example': 'The company maintains a high '
                                             'profit margin by keeping costs '
                                             'low.',
                                  'ipa': '/ˈprɒf.ɪt ˌmɑː.dʒɪn/',
                                  'meaning': 'biên lợi nhuận',
                                  'word': 'profit margin'},
                              {   'example': 'Apple has a large market share '
                                             'in the premium smartphone '
                                             'segment.',
                                  'ipa': '/ˈmɑː.kɪt ʃeər/',
                                  'meaning': 'thị phần',
                                  'word': 'market share'},
                              {   'example': 'The pandemic disrupted global '
                                             'supply chains significantly.',
                                  'ipa': '/səˈplaɪ tʃeɪn/',
                                  'meaning': 'chuỗi cung ứng',
                                  'word': 'supply chain'},
                              {   'example': 'Good cash flow management is '
                                             'essential for any small '
                                             'business.',
                                  'ipa': '/kæʃ fləʊ/',
                                  'meaning': 'dòng tiền',
                                  'word': 'cash flow'},
                              {   'example': 'Their subscription-based '
                                             'business model generates '
                                             'predictable monthly revenue.',
                                  'ipa': '/ˈbɪz.nɪs ˌmɒd.əl/',
                                  'meaning': 'mô hình kinh doanh',
                                  'word': 'business model'},
                              {   'example': 'The two companies formed a '
                                             'strategic partnership to expand '
                                             'globally.',
                                  'ipa': '/ˈpɑːt.nər.ʃɪp/',
                                  'meaning': 'quan hệ đối tác',
                                  'word': 'partnership'},
                              {   'example': 'The company registered its logo '
                                             'as a trademark to prevent '
                                             'copying.',
                                  'ipa': '/ˈtreɪd.mɑːk/',
                                  'meaning': 'nhãn hiệu thương mại',
                                  'word': 'trademark'},
                              {   'example': 'The inventor applied for a '
                                             'patent to protect her new '
                                             'technology.',
                                  'ipa': '/ˈpeɪ.tənt/',
                                  'meaning': 'bằng sáng chế',
                                  'word': 'patent'},
                              {   'example': 'The firm opened a subsidiary in '
                                             'Germany to expand into Europe.',
                                  'ipa': '/səbˈsɪd.i.ər.i/',
                                  'meaning': 'công ty con',
                                  'word': 'subsidiary'},
                              {   'example': 'Shareholders will vote on the '
                                             'new acquisition at the annual '
                                             'meeting.',
                                  'ipa': '/ˈʃeər.həʊl.dər/',
                                  'meaning': 'cổ đông',
                                  'word': 'shareholder'},
                              {   'example': 'The company paid a generous '
                                             'dividend to its shareholders '
                                             'last year.',
                                  'ipa': '/ˈdɪv.ɪ.dend/',
                                  'meaning': 'cổ tức',
                                  'word': 'dividend'},
                              {   'example': 'An independent audit confirmed '
                                             "that the company's finances were "
                                             'in order.',
                                  'ipa': '/ˈɔː.dɪt/',
                                  'meaning': 'kiểm toán',
                                  'word': 'audit'},
                              {   'example': 'All employees must complete '
                                             'compliance training to meet '
                                             'regulatory requirements.',
                                  'ipa': '/kəmˈplaɪ.əns/',
                                  'meaning': 'sự tuân thủ',
                                  'word': 'compliance'},
                              {   'example': 'The company reduced costs by '
                                             'outsourcing customer service to '
                                             'a third party.',
                                  'ipa': '/ˈaʊt.sɔː.sɪŋ/',
                                  'meaning': 'thuê ngoài',
                                  'word': 'outsourcing'},
                              {   'example': 'They reduced overhead costs by '
                                             'moving to a smaller office '
                                             'space.',
                                  'ipa': '/ˈəʊ.vər.hed/',
                                  'meaning': 'chi phí cố định',
                                  'word': 'overhead'},
                              {   'example': 'The platform is highly scalable '
                                             'and can handle millions of '
                                             'users.',
                                  'ipa': '/ˈskeɪ.lə.bəl/',
                                  'meaning': 'có khả năng mở rộng',
                                  'word': 'scalable'},
                              {   'example': 'Their proprietary technology '
                                             'gives them a competitive '
                                             'advantage in the market.',
                                  'ipa': '/kəmˌpet.ɪ.tɪv ədˈvɑːn.tɪdʒ/',
                                  'meaning': 'lợi thế cạnh tranh',
                                  'word': 'competitive advantage'},
                              {   'example': 'The team conducted extensive '
                                             'market research before launching '
                                             'the new product.',
                                  'ipa': '/ˈmɑː.kɪt rɪˈsɜːtʃ/',
                                  'meaning': 'nghiên cứu thị trường',
                                  'word': 'market research'},
                              {   'example': 'Social media campaigns can '
                                             'significantly increase brand '
                                             'awareness.',
                                  'ipa': '/brænd əˈweər.nəs/',
                                  'meaning': 'nhận thức thương hiệu',
                                  'word': 'brand awareness'},
                              {   'example': 'Good customer service is key to '
                                             'improving customer retention '
                                             'rates.',
                                  'ipa': '/ˈkʌs.tə.mər rɪˈten.ʃən/',
                                  'meaning': 'giữ chân khách hàng',
                                  'word': 'customer retention'},
                              {   'example': 'The product launch attracted '
                                             'hundreds of journalists and '
                                             'industry experts.',
                                  'ipa': '/ˈprɒd.ʌkt lɔːntʃ/',
                                  'meaning': 'ra mắt sản phẩm',
                                  'word': 'product launch'},
                              {   'example': 'A clear value proposition helps '
                                             'customers understand why to '
                                             'choose your product.',
                                  'ipa': '/ˈvæl.juː ˌprɒp.əˈzɪʃ.ən/',
                                  'meaning': 'đề xuất giá trị',
                                  'word': 'value proposition'},
                              {   'example': 'The startup expects to reach '
                                             'break-even point within the '
                                             'first two years.',
                                  'ipa': '/breɪk ˈiː.vən pɔɪnt/',
                                  'meaning': 'điểm hòa vốn',
                                  'word': 'break-even point'},
                              {   'example': 'The company reported strong '
                                             'gross profit despite rising '
                                             'material costs.',
                                  'ipa': '/ɡrəʊs ˈprɒf.ɪt/',
                                  'meaning': 'lợi nhuận gộp',
                                  'word': 'gross profit'},
                              {   'example': 'The marketing campaign delivered '
                                             'an excellent return on '
                                             'investment.',
                                  'ipa': '/rɪˈtɜːn ɒn ɪnˈvest.mənt/',
                                  'meaning': 'tỷ suất hoàn vốn',
                                  'word': 'return on investment'},
                              {   'example': 'Business ethics are increasingly '
                                             'important to consumers and '
                                             'investors.',
                                  'ipa': '/ˈbɪz.nɪs ˈeθ.ɪks/',
                                  'meaning': 'đạo đức kinh doanh',
                                  'word': 'business ethics'},
                              {   'example': 'Strong corporate governance '
                                             "protects shareholders' interests "
                                             'and ensures transparency.',
                                  'ipa': '/ˈkɔː.pər.ɪt ˈɡʌv.ən.əns/',
                                  'meaning': 'quản trị doanh nghiệp',
                                  'word': 'corporate governance'},
                              {   'example': 'The team completed a thorough '
                                             'risk assessment before entering '
                                             'the new market.',
                                  'ipa': '/rɪsk əˈses.mənt/',
                                  'meaning': 'đánh giá rủi ro',
                                  'word': 'risk assessment'},
                              {   'example': 'Key performance indicators help '
                                             'managers track progress towards '
                                             'business goals.',
                                  'ipa': '/pəˈfɔː.məns ˈɪn.dɪ.keɪ.tər/',
                                  'meaning': 'chỉ số hiệu suất',
                                  'word': 'performance indicator'},
                              {   'example': 'The annual report showed '
                                             'significant growth in both '
                                             'revenue and net profit.',
                                  'ipa': '/ˈæn.ju.əl rɪˈpɔːt/',
                                  'meaning': 'báo cáo thường niên',
                                  'word': 'annual report'},
                              {   'example': 'The board of directors approved '
                                             'the new expansion strategy '
                                             'unanimously.',
                                  'ipa': '/bɔːd əv daɪˈrek.tərz/',
                                  'meaning': 'hội đồng quản trị',
                                  'word': 'board of directors'},
                              {   'example': 'The two companies formed a joint '
                                             'venture to develop new '
                                             'technology together.',
                                  'ipa': '/dʒɔɪnt ˈven.tʃər/',
                                  'meaning': 'liên doanh',
                                  'word': 'joint venture'},
                              {   'example': 'The business development team '
                                             'identifies new partnership '
                                             'opportunities.',
                                  'ipa': '/ˈbɪz.nɪs dɪˈvel.əp.mənt/',
                                  'meaning': 'phát triển kinh doanh',
                                  'word': 'business development'},
                              {   'example': 'Cost reduction measures helped '
                                             'the company become profitable.',
                                  'ipa': '/kɒst rɪˈdʌk.ʃən/',
                                  'meaning': 'cắt giảm chi phí',
                                  'word': 'cost reduction'},
                              {   'example': 'They expanded their distribution '
                                             'channel to reach rural markets.',
                                  'ipa': '/ˌdɪs.trɪˈbjuː.ʃən ˈtʃæn.əl/',
                                  'meaning': 'kênh phân phối',
                                  'word': 'distribution channel'},
                              {   'example': 'The financial forecast predicts '
                                             '15% revenue growth next year.',
                                  'ipa': '/faɪˈnæn.ʃəl ˈfɔː.kɑːst/',
                                  'meaning': 'dự báo tài chính',
                                  'word': 'financial forecast'},
                              {   'example': 'A competitive analysis helps '
                                             'businesses understand their '
                                             'position in the market.',
                                  'ipa': '/kəmˈpet.ɪ.tɪv əˈnæl.ə.sɪs/',
                                  'meaning': 'phân tích cạnh tranh',
                                  'word': 'competitive analysis'},
                              {   'example': 'Automation improved operational '
                                             'efficiency across all '
                                             'departments.',
                                  'ipa': '/ˌɒp.ər.ˈeɪ.ʃən.əl ɪˈfɪʃ.ən.si/',
                                  'meaning': 'hiệu quả vận hành',
                                  'word': 'operational efficiency'},
                              {   'example': 'The product development cycle '
                                             'typically takes 12 to 18 months.',
                                  'ipa': '/ˈprɒd.ʌkt dɪˈvel.əp.mənt/',
                                  'meaning': 'phát triển sản phẩm',
                                  'word': 'product development'},
                              {   'example': 'Their aggressive pricing '
                                             'strategy helped achieve rapid '
                                             'market penetration.',
                                  'ipa': '/ˈmɑː.kɪt ˌpen.ɪˈtreɪ.ʃən/',
                                  'meaning': 'thâm nhập thị trường',
                                  'word': 'market penetration'},
                              {   'example': 'The sales team set a new '
                                             'benchmark for monthly '
                                             'performance targets.',
                                  'ipa': '/ˈbentʃ.mɑːk/',
                                  'meaning': 'tiêu chuẩn so sánh',
                                  'word': 'benchmark'}],
                    'B2': [   {   'example': 'Porter defines three competitive '
                                             'strategies.',
                                  'ipa': '/kəmˈpɛt.ɪ.tɪv ˈstræt.ɪ.dʒi/',
                                  'meaning': 'chiến lược cạnh tranh bền vững',
                                  'word': 'competitive strategy'},
                              {   'example': 'Value chain analysis identifies '
                                             'cost drivers.',
                                  'ipa': '/ˈvæl.juː tʃeɪn əˈnæl.ɪ.sɪs/',
                                  'meaning': 'phân tích chuỗi giá trị doanh '
                                             'nghiệp',
                                  'word': 'value chain analysis'},
                              {   'example': 'Identify your core competencies.',
                                  'ipa': '/kɔːr kəmˈpɛt.ən.si/',
                                  'meaning': 'năng lực cốt lõi khác biệt hóa',
                                  'word': 'core competency'},
                              {   'example': 'Business model innovation '
                                             'disrupts markets.',
                                  'ipa': '/ˈbɪz.nɪs ˈmɒd.əl ˌɪn.əˈveɪ.ʃən/',
                                  'meaning': 'đổi mới mô hình kinh doanh',
                                  'word': 'business model innovation'},
                              {   'example': 'Amazon uses a platform business '
                                             'model.',
                                  'ipa': '/ˈplæt.fɔːrm ˈbɪz.nɪs ˈmɒd.əl/',
                                  'meaning': 'mô hình kinh doanh nền tảng hai '
                                             'mặt',
                                  'word': 'platform business model'},
                              {   'example': 'Network effects create '
                                             'winner-take-all markets.',
                                  'ipa': '/ˈnɛt.wɜːrk ɪˈfɛkts/',
                                  'meaning': 'hiệu ứng mạng lưới tăng giá trị '
                                             'theo người dùng',
                                  'word': 'network effects'},
                              {   'example': 'Economies of scale lower unit '
                                             'costs.',
                                  'ipa': '/ɪˈkɒn.ə.miz əv skeɪl/',
                                  'meaning': 'kinh tế quy mô giảm chi phí khi '
                                             'tăng sản lượng',
                                  'word': 'economies of scale'},
                              {   'example': 'Economies of scope benefit '
                                             'diversified firms.',
                                  'ipa': '/ɪˈkɒn.ə.miz əv skoʊp/',
                                  'meaning': 'kinh tế phạm vi tiết kiệm sản '
                                             'xuất đa ngành',
                                  'word': 'economies of scope'},
                              {   'example': 'Strong market positioning builds '
                                             'loyalty.',
                                  'ipa': '/ˈmɑːr.kɪt pəˈzɪʃ.ən.ɪŋ/',
                                  'meaning': 'định vị thị trường trong tâm trí '
                                             'khách hàng',
                                  'word': 'market positioning'},
                              {   'example': 'Define the go-to-market before '
                                             'launch.',
                                  'ipa': '/ˌɡoʊ.tʊˈmɑːr.kɪt/',
                                  'meaning': 'chiến lược tiếp cận thị trường '
                                             'mới',
                                  'word': 'go-to-market'},
                              {   'example': 'Build a scalable business from '
                                             'day one.',
                                  'ipa': '/ˈskeɪ.lə.bəl ˈbɪz.nɪs/',
                                  'meaning': 'kinh doanh có khả năng mở rộng '
                                             'quy mô',
                                  'word': 'scalable business'},
                              {   'example': 'Choose the right revenue model.',
                                  'ipa': '/ˈrɛv.ɪ.njuː ˈmɒd.əl/',
                                  'meaning': 'mô hình doanh thu của doanh '
                                             'nghiệp',
                                  'word': 'revenue model'},
                              {   'example': 'Understand unit economics before '
                                             'scaling.',
                                  'ipa': '/ˈjuː.nɪt ˌɪ.kəˈnɒm.ɪks/',
                                  'meaning': 'kinh tế đơn vị sản phẩm lãi lỗ',
                                  'word': 'unit economics'},
                              {   'example': 'Lower customer acquisition cost '
                                             'improves margins.',
                                  'ipa': '/ˈkʌs.tə.mər ˌæk.wɪˈzɪʃ.ən kɒst/',
                                  'meaning': 'chi phí có được một khách hàng '
                                             'mới',
                                  'word': 'customer acquisition cost'},
                              {   'example': 'High LTV justifies higher '
                                             'acquisition spend.',
                                  'ipa': '/ˈlaɪf.taɪm ˈvæl.juː/',
                                  'meaning': 'giá trị vòng đời của khách hàng',
                                  'word': 'lifetime value'},
                              {   'example': 'Reduce churn to improve '
                                             'retention.',
                                  'ipa': '/tʃɜːrn/',
                                  'meaning': 'tỷ lệ khách hàng rời bỏ dịch vụ',
                                  'word': 'churn'},
                              {   'example': 'A high retention rate signals '
                                             'loyalty.',
                                  'ipa': '/rɪˈtɛn.ʃən reɪt/',
                                  'meaning': 'tỷ lệ giữ chân khách hàng lâu '
                                             'dài',
                                  'word': 'retention rate'},
                              {   'example': 'Expansion revenue grows without '
                                             'new customers.',
                                  'ipa': '/ɪkˈspæn.ʃən ˈrɛv.ɪ.njuː/',
                                  'meaning': 'doanh thu từ khách hàng mở rộng '
                                             'sử dụng',
                                  'word': 'expansion revenue'},
                              {   'example': 'ARR is the key SaaS metric.',
                                  'ipa': '/ˈæn.jʊ.əl rɪˈkɜːr.ɪŋ ˈrɛv.ɪ.njuː/',
                                  'meaning': 'doanh thu định kỳ hàng năm ổn '
                                             'định',
                                  'word': 'annual recurring revenue'},
                              {   'example': 'Track MRR to measure growth.',
                                  'ipa': '/ˈmʌnθ.li rɪˈkɜːr.ɪŋ ˈrɛv.ɪ.njuː/',
                                  'meaning': 'doanh thu định kỳ hàng tháng',
                                  'word': 'monthly recurring revenue'},
                              {   'example': 'EBITDA measures operational '
                                             'profitability.',
                                  'ipa': '/ɪˈbɪt.də/',
                                  'meaning': 'lợi nhuận trước lãi vay thuế '
                                             'khấu hao',
                                  'word': 'EBITDA'},
                              {   'example': 'Manage working capital '
                                             'carefully.',
                                  'ipa': '/ˈwɜːr.kɪŋ ˈkæp.ɪ.təl/',
                                  'meaning': 'vốn lưu động hoạt động hàng ngày',
                                  'word': 'working capital'},
                              {   'example': 'Solvency ensures long-term '
                                             'viability.',
                                  'ipa': '/ˈsɒl.vən.si/',
                                  'meaning': 'khả năng thanh toán nợ dài hạn',
                                  'word': 'solvency'},
                              {   'example': 'Assess credit risk before '
                                             'extending terms.',
                                  'ipa': '/ˈkrɛd.ɪt rɪsk/',
                                  'meaning': 'rủi ro tín dụng khách không trả '
                                             'nợ',
                                  'word': 'credit risk'},
                              {   'example': 'Hedging protects against '
                                             'currency risk.',
                                  'ipa': '/ˈhɛdʒ.ɪŋ/',
                                  'meaning': 'phòng ngừa rủi ro tài chính',
                                  'word': 'hedging'},
                              {   'example': 'Conduct due diligence before '
                                             'acquisition.',
                                  'ipa': '/djuː ˈdɪl.ɪ.dʒəns/',
                                  'meaning': 'thẩm định kỹ lưỡng trước khi đầu '
                                             'tư',
                                  'word': 'due diligence'},
                              {   'example': 'Review the term sheet carefully.',
                                  'ipa': '/tɜːrm ʃiːt/',
                                  'meaning': 'bản điều khoản đầu tư sơ bộ',
                                  'word': 'term sheet'},
                              {   'example': 'Manage your cap table carefully.',
                                  'ipa': '/kæp ˈteɪ.bəl/',
                                  'meaning': 'bảng phân bổ vốn cổ phần',
                                  'word': 'cap table'},
                              {   'example': 'The vesting schedule spans four '
                                             'years.',
                                  'ipa': '/ˈvɛs.tɪŋ ˈʃɛd.juːl/',
                                  'meaning': 'lịch trình trao quyền cổ phần '
                                             'theo thời gian',
                                  'word': 'vesting schedule'},
                              {   'example': 'Monitor burn rate to extend '
                                             'runway.',
                                  'ipa': '/bɜːrn reɪt/',
                                  'meaning': 'tốc độ đốt tiền hàng tháng',
                                  'word': 'burn rate'},
                              {   'example': 'We have 18 months of runway.',
                                  'ipa': '/ˈrʌn.weɪ/',
                                  'meaning': 'thời gian sống sót còn lại của '
                                             'startup',
                                  'word': 'runway'},
                              {   'example': 'Demonstrate traction before '
                                             'raising.',
                                  'ipa': '/ˈtræk.ʃən/',
                                  'meaning': 'sức kéo tăng trưởng chứng minh '
                                             'được',
                                  'word': 'traction'},
                              {   'example': 'Share the product roadmap with '
                                             'investors.',
                                  'ipa': '/ˈprɒd.ʌkt ˈroʊd.mæp/',
                                  'meaning': 'lộ trình phát triển sản phẩm',
                                  'word': 'product roadmap'},
                              {   'example': 'The board meeting is quarterly.',
                                  'ipa': '/bɔːrd ˈmiː.tɪŋ/',
                                  'meaning': 'cuộc họp hội đồng quản trị',
                                  'word': 'board meeting'},
                              {   'example': 'Stakeholder management prevents '
                                             'conflict.',
                                  'ipa': '/ˈsteɪk.hoʊl.dər ˈmæn.ɪdʒ.mənt/',
                                  'meaning': 'quản lý kỳ vọng các bên liên '
                                             'quan',
                                  'word': 'stakeholder management'},
                              {   'example': 'Plan an exit strategy from the '
                                             'start.',
                                  'ipa': '/ˈɛk.sɪt ˈstræt.ɪ.dʒi/',
                                  'meaning': 'chiến lược thoát vốn cho nhà đầu '
                                             'tư',
                                  'word': 'exit strategy'},
                              {   'example': 'M&A activity increased last '
                                             'quarter.',
                                  'ipa': '/ˌɛm.ænˈeɪ/',
                                  'meaning': 'mua bán và sáp nhập doanh nghiệp',
                                  'word': 'M&A'},
                              {   'example': 'A leveraged buyout uses debt '
                                             'financing.',
                                  'ipa': '/ˈlɛv.ər.ɪdʒd ˈbaɪ.aʊt/',
                                  'meaning': 'mua lại doanh nghiệp bằng đòn '
                                             'bẩy nợ',
                                  'word': 'leveraged buyout'},
                              {   'example': 'Private equity firms acquire '
                                             'mature companies.',
                                  'ipa': '/ˈpraɪ.vɪt ˈɛk.wɪ.ti/',
                                  'meaning': 'vốn tư nhân đầu tư vào công ty '
                                             'chưa niêm yết',
                                  'word': 'private equity'},
                              {   'example': 'Raise Series A after proving '
                                             'growth.',
                                  'ipa': '/ˈsɪər.iːz eɪ biː siː/',
                                  'meaning': 'vòng gọi vốn từ A đến C cho '
                                             'startup',
                                  'word': 'Series A/B/C'},
                              {   'example': 'An angel investor backs early '
                                             'startups.',
                                  'ipa': '/ˈeɪn.dʒəl ɪnˈvɛs.tər/',
                                  'meaning': 'nhà đầu tư thiên thần giai đoạn '
                                             'đầu',
                                  'word': 'angel investor'},
                              {   'example': 'Bootstrapping avoids equity '
                                             'dilution.',
                                  'ipa': '/ˈbuːt.stræp.ɪŋ/',
                                  'meaning': 'tự tài trợ không cần vốn bên '
                                             'ngoài',
                                  'word': 'bootstrapping'},
                              {   'example': 'Crowdfunding validates product '
                                             'demand.',
                                  'ipa': '/ˈkraʊd.fʌn.dɪŋ/',
                                  'meaning': 'gọi vốn từ đông đảo cộng đồng '
                                             'nhỏ lẻ',
                                  'word': 'crowdfunding'},
                              {   'example': 'A convertible note delays '
                                             'valuation.',
                                  'ipa': '/kənˈvɜːr.tɪ.bəl noʊt/',
                                  'meaning': 'trái phiếu chuyển đổi thành cổ '
                                             'phần',
                                  'word': 'convertible note'},
                              {   'example': 'A SAFE is simpler than a '
                                             'convertible note.',
                                  'ipa': '/seɪf əˈɡriː.mənt/',
                                  'meaning': 'thỏa thuận vốn đơn giản cho nhà '
                                             'đầu tư tương lai',
                                  'word': 'SAFE agreement'},
                              {   'example': 'The pre-money valuation was 5 '
                                             'million.',
                                  'ipa': '/priːˈmʌn.i ˌvæl.jʊˈeɪ.ʃən/',
                                  'meaning': 'định giá trước khi nhận vốn đầu '
                                             'tư',
                                  'word': 'pre-money valuation'},
                              {   'example': 'The post-money valuation reached '
                                             '7 million.',
                                  'ipa': '/poʊstˈmʌn.i ˌvæl.jʊˈeɪ.ʃən/',
                                  'meaning': 'định giá sau khi nhận vốn đầu tư',
                                  'word': 'post-money valuation'},
                              {   'example': 'New funding causes equity '
                                             'dilution.',
                                  'ipa': '/daɪˈluː.ʃən/',
                                  'meaning': 'pha loãng cổ phần khi phát hành '
                                             'thêm',
                                  'word': 'dilution'},
                              {   'example': 'Mezzanine financing bridges debt '
                                             'and equity.',
                                  'ipa': '/ˈmɛz.ə.niːn ˈfaɪ.næn.sɪŋ/',
                                  'meaning': 'tài chính trung gian giữa nợ và '
                                             'vốn',
                                  'word': 'mezzanine financing'},
                              {   'example': 'An earnout links payment to '
                                             'future performance.',
                                  'ipa': '/ˈɜːrn.aʊt/',
                                  'meaning': 'điều khoản thanh toán dựa trên '
                                             'hiệu suất tương lai',
                                  'word': 'earnout'}],
                    'C1': [   {   'example': 'Directors have a fiduciary duty '
                                             'to shareholders.',
                                  'ipa': '/fɪˈdjuː.ʃi.ər.i ˈdjuː.ti/',
                                  'meaning': 'nghĩa vụ ủy thác trung thành với '
                                             'cổ đông',
                                  'word': 'fiduciary duty'},
                              {   'example': 'The agency problem arises from '
                                             'ownership separation.',
                                  'ipa': '/ˈeɪ.dʒən.si ˈprɒb.ləm/',
                                  'meaning': 'vấn đề đại lý xung đột lợi ích '
                                             'quản lý-cổ đông',
                                  'word': 'agency problem'},
                              {   'example': 'Asymmetric information causes '
                                             'market failures.',
                                  'ipa': '/ˌeɪ.sɪˈmɛt.rɪk ˌɪn.fəˈmeɪ.ʃən/',
                                  'meaning': 'thông tin bất cân xứng giữa các '
                                             'bên giao dịch',
                                  'word': 'asymmetric information'},
                              {   'example': 'The principal-agent relationship '
                                             'creates incentive issues.',
                                  'ipa': '/ˈprɪn.sɪ.pəl ˈeɪ.dʒənt '
                                         'rɪˈleɪ.ʃən.ʃɪp/',
                                  'meaning': 'quan hệ ủy nhiệm giữa chủ sở hữu '
                                             'và người quản lý',
                                  'word': 'principal-agent relationship'},
                              {   'example': 'Insurance creates a moral '
                                             'hazard.',
                                  'ipa': '/ˈmɒr.əl ˈhæz.ərd/',
                                  'meaning': 'rủi ro đạo đức khi người được '
                                             'bảo vệ hành xử rủi ro',
                                  'word': 'moral hazard'},
                              {   'example': 'Adverse selection plagues '
                                             'insurance markets.',
                                  'ipa': '/ˈæd.vɜːrs sɪˈlɛk.ʃən/',
                                  'meaning': 'lựa chọn ngược lại khi thông tin '
                                             'bất cân xứng',
                                  'word': 'adverse selection'},
                              {   'example': 'Transaction cost economics '
                                             'explains firm boundaries.',
                                  'ipa': '/trænsˈæk.ʃən kɒst ˌɪ.kəˈnɒm.ɪks/',
                                  'meaning': 'kinh tế học chi phí giao dịch '
                                             'của Coase',
                                  'word': 'transaction cost economics'},
                              {   'example': 'Institutional theory explains '
                                             'why firms mimic each other.',
                                  'ipa': '/ˌɪn.stɪˈtjuː.ʃən.əl ˈθɪər.i/',
                                  'meaning': 'lý thuyết thể chế giải thích '
                                             'hành vi tổ chức',
                                  'word': 'institutional theory'},
                              {   'example': 'The resource-based view focuses '
                                             'on unique assets.',
                                  'ipa': '/rɪˈzɔːrs beɪst vjuː/',
                                  'meaning': 'quan điểm nguồn lực lợi thế cạnh '
                                             'tranh bền vững',
                                  'word': 'resource-based view'},
                              {   'example': 'Dynamic capabilities enable '
                                             'adaptation to change.',
                                  'ipa': '/daɪˈnæm.ɪk ˌkeɪ.pə.ˈbɪl.ɪ.tɪz/',
                                  'meaning': 'năng lực động để thích nghi và '
                                             'đổi mới',
                                  'word': 'dynamic capabilities'},
                              {   'example': 'Absorptive capacity enables '
                                             'external knowledge use.',
                                  'ipa': '/əbˈzɔːrp.tɪv kəˈpæs.ɪ.ti/',
                                  'meaning': 'năng lực hấp thụ tri thức mới từ '
                                             'bên ngoài',
                                  'word': 'absorptive capacity'},
                              {   'example': 'Open innovation leverages '
                                             'external ideas.',
                                  'ipa': '/ˈoʊ.pən ˌɪn.əˈveɪ.ʃən/',
                                  'meaning': 'đổi mới mở hợp tác với bên ngoài',
                                  'word': 'open innovation'},
                              {   'example': 'Ambidexterity balances '
                                             'efficiency and innovation.',
                                  'ipa': '/ˌæm.bɪˈdɛks.tər.ɪ.ti/',
                                  'meaning': 'tính thuận hai tay cân bằng khai '
                                             'thác và khám phá',
                                  'word': 'ambidexterity'},
                              {   'example': 'Organizational learning drives '
                                             'continuous improvement.',
                                  'ipa': '/ˌɔːr.ɡən.aɪˈzeɪ.ʃən.əl ˈlɜːr.nɪŋ/',
                                  'meaning': 'học hỏi tổ chức cải thiện năng '
                                             'lực theo thời gian',
                                  'word': 'organizational learning'},
                              {   'example': 'Institutional isomorphism makes '
                                             'firms look similar.',
                                  'ipa': '/ˌɪn.stɪˈtjuː.ʃən.əl '
                                         'ˌaɪ.sə.ˈmɔːr.fɪ.zəm/',
                                  'meaning': 'đồng hình thể chế các tổ chức '
                                             'trở nên giống nhau',
                                  'word': 'institutional isomorphism'},
                              {   'example': 'Strategic alignment ensures '
                                             'coordinated execution.',
                                  'ipa': '/strəˈtiː.dʒɪk əˈlaɪn.mənt/',
                                  'meaning': 'căn chỉnh chiến lược giữa các '
                                             'cấp doanh nghiệp',
                                  'word': 'strategic alignment'},
                              {   'example': 'Use the value proposition canvas '
                                             'for product fit.',
                                  'ipa': '/ˈvæl.juː ˌprɒp.əˈzɪʃ.ən ˈkæn.vəs/',
                                  'meaning': 'khung đề xuất giá trị cho khách '
                                             'hàng',
                                  'word': 'value proposition canvas'},
                              {   'example': 'Map your business using the '
                                             'business model canvas.',
                                  'ipa': '/ˈbɪz.nɪs ˈmɒd.əl ˈkæn.vəs/',
                                  'meaning': 'khung mô hình kinh doanh chín '
                                             'khối',
                                  'word': 'business model canvas'},
                              {   'example': 'The lean startup method '
                                             'minimizes waste.',
                                  'ipa': '/liːn ˈstɑːr.tʌp/',
                                  'meaning': 'phương pháp khởi nghiệp tinh gọn '
                                             'học nhanh',
                                  'word': 'lean startup'},
                              {   'example': 'Design thinking solves complex '
                                             'business problems.',
                                  'ipa': '/dɪˈzaɪn ˈθɪŋ.kɪŋ/',
                                  'meaning': 'tư duy thiết kế lấy con người '
                                             'làm trung tâm',
                                  'word': 'design thinking'},
                              {   'example': 'Jobs to be done theory explains '
                                             'buying behavior.',
                                  'ipa': '/dʒɒbz tʊ biː dʌn/',
                                  'meaning': 'lý thuyết công việc cần hoàn '
                                             'thành của khách hàng',
                                  'word': 'jobs to be done'},
                              {   'example': 'Disruptive innovation creates '
                                             'new markets.',
                                  'ipa': '/dɪsˈrʌp.tɪv ˌɪn.əˈveɪ.ʃən/',
                                  'meaning': 'đổi mới đột phá thay thế thị '
                                             'trường hiện có',
                                  'word': 'disruptive innovation'},
                              {   'example': 'Sustaining innovation improves '
                                             'existing products.',
                                  'ipa': '/səˈsteɪ.nɪŋ ˌɪn.əˈveɪ.ʃən/',
                                  'meaning': 'đổi mới duy trì cải thiện sản '
                                             'phẩm hiện tại',
                                  'word': 'sustaining innovation'},
                              {   'example': 'Stakeholder capitalism considers '
                                             'all parties.',
                                  'ipa': '/ˈsteɪk.hoʊl.dər ˈkæp.ɪ.tə.lɪzm/',
                                  'meaning': 'chủ nghĩa tư bản các bên liên '
                                             'quan rộng hơn',
                                  'word': 'stakeholder capitalism'},
                              {   'example': 'ESG factors affect investment '
                                             'decisions.',
                                  'ipa': '/ˌiː.ɛsˈdʒiː/',
                                  'meaning': 'môi trường xã hội quản trị doanh '
                                             'nghiệp bền vững',
                                  'word': 'ESG'},
                              {   'example': 'A circular economy eliminates '
                                             'waste.',
                                  'ipa': '/ˈsɜːr.kjʊ.lər ɪˈkɒn.ə.mi/',
                                  'meaning': 'kinh tế tuần hoàn tái sử dụng '
                                             'không lãng phí',
                                  'word': 'circular economy'},
                              {   'example': 'A social enterprise balances '
                                             'profit and purpose.',
                                  'ipa': '/ˈsoʊ.ʃəl ˈɛn.tər.praɪz/',
                                  'meaning': 'doanh nghiệp xã hội lợi nhuận và '
                                             'sứ mệnh',
                                  'word': 'social enterprise'},
                              {   'example': 'Shared value creation aligns '
                                             'business with society.',
                                  'ipa': '/ʃɛərd ˈvæl.juː kriˈeɪ.ʃən/',
                                  'meaning': 'tạo giá trị chung cho doanh '
                                             'nghiệp và xã hội',
                                  'word': 'shared value creation'},
                              {   'example': 'Impact investing seeks financial '
                                             'and social returns.',
                                  'ipa': '/ˈɪm.pækt ɪnˈvɛs.tɪŋ/',
                                  'meaning': 'đầu tư tạo ra tác động xã hội '
                                             'tích cực',
                                  'word': 'impact investing'},
                              {   'example': 'The triple bottom line measures '
                                             'people, planet, profit.',
                                  'ipa': '/ˈtrɪp.əl ˈbɒt.əm laɪn/',
                                  'meaning': 'ba nền tảng lợi nhuận con người '
                                             'hành tinh',
                                  'word': 'triple bottom line'},
                              {   'example': 'Regenerative business goes '
                                             'beyond sustainability.',
                                  'ipa': '/rɪˈdʒɛn.ər.ə.tɪv ˈbɪz.nɪs/',
                                  'meaning': 'kinh doanh tái sinh phục hồi hệ '
                                             'sinh thái',
                                  'word': 'regenerative business'},
                              {   'example': 'B Corp certification signals '
                                             'social commitment.',
                                  'ipa': '/biː kɔːrp ˌsɜːr.tɪ.fɪˈkeɪ.ʃən/',
                                  'meaning': 'chứng nhận doanh nghiệp vì lợi '
                                             'ích xã hội',
                                  'word': 'B Corp certification'},
                              {   'example': 'Shareholder primacy is '
                                             'questioned today.',
                                  'ipa': '/ˈʃɛər.hoʊl.dər ˈpraɪ.mə.si/',
                                  'meaning': 'ưu tiên tối đa hóa giá trị cổ '
                                             'đông',
                                  'word': 'shareholder primacy'},
                              {   'example': 'Purpose-driven businesses '
                                             'attract loyal employees.',
                                  'ipa': '/ˈpɜːr.pəs ˈdrɪv.ən ˈbɪz.nɪs/',
                                  'meaning': 'kinh doanh có mục đích sứ mệnh ý '
                                             'nghĩa',
                                  'word': 'purpose-driven business'},
                              {   'example': 'Organizational agility enables '
                                             'rapid pivots.',
                                  'ipa': '/ˌɔːr.ɡən.aɪˈzeɪ.ʃən.əl əˈdʒɪl.ɪ.ti/',
                                  'meaning': 'sự linh hoạt tổ chức thích nghi '
                                             'nhanh chóng',
                                  'word': 'organizational agility'},
                              {   'example': 'A resilient supply chain '
                                             'withstands disruptions.',
                                  'ipa': '/rɪˈzɪl.i.ənt səˈplaɪ tʃeɪn/',
                                  'meaning': 'chuỗi cung ứng bền vững chịu '
                                             'đựng gián đoạn',
                                  'word': 'resilient supply chain'},
                              {   'example': 'Geopolitical risk affects global '
                                             'supply chains.',
                                  'ipa': '/ˌdʒiː.oʊ.pəˈlɪt.ɪ.kəl rɪsk/',
                                  'meaning': 'rủi ro địa chính trị ảnh hưởng '
                                             'kinh doanh',
                                  'word': 'geopolitical risk'},
                              {   'example': 'Deglobalization reshapes trade '
                                             'patterns.',
                                  'ipa': '/diːˌɡloʊ.bəl.aɪˈzeɪ.ʃən/',
                                  'meaning': 'phi toàn cầu hóa rút về sản xuất '
                                             'trong nước',
                                  'word': 'deglobalization'},
                              {   'example': 'Nearshoring reduces supply chain '
                                             'risk.',
                                  'ipa': '/ˈnɪər.ʃɔːr.ɪŋ/',
                                  'meaning': 'chuyển sản xuất về nước gần địa '
                                             'lý',
                                  'word': 'nearshoring'},
                              {   'example': 'Regulatory compliance avoids '
                                             'costly fines.',
                                  'ipa': '/ˌrɛɡ.jʊ.lə.tər.i kəmˈplaɪ.əns/',
                                  'meaning': 'tuân thủ quy định pháp lý của cơ '
                                             'quan chức năng',
                                  'word': 'regulatory compliance'},
                              {   'example': 'Antitrust law prevents '
                                             'monopolistic behavior.',
                                  'ipa': '/ˈæn.ti.trʌst lɔː/',
                                  'meaning': 'luật chống độc quyền bảo vệ cạnh '
                                             'tranh',
                                  'word': 'antitrust law'},
                              {   'example': 'High market concentration '
                                             'reduces competition.',
                                  'ipa': '/ˈmɑːr.kɪt ˌkɒn.sənˈtreɪ.ʃən/',
                                  'meaning': 'tập trung thị trường ít công ty '
                                             'chi phối',
                                  'word': 'market concentration'},
                              {   'example': 'A contestable market has low '
                                             'entry barriers.',
                                  'ipa': '/kənˈtɛs.tə.bəl ˈmɑːr.kɪt/',
                                  'meaning': 'thị trường có thể tranh chấp dễ '
                                             'gia nhập',
                                  'word': 'contestable market'},
                              {   'example': 'Asymmetric bargaining power '
                                             'harms smaller firms.',
                                  'ipa': '/ˌeɪ.sɪˈmɛt.rɪk ˈbɑːr.ɡɪ.nɪŋ ˈpaʊər/',
                                  'meaning': 'quyền lực thương lượng bất cân '
                                             'xứng giữa các bên',
                                  'word': 'asymmetric bargaining power'},
                              {   'example': 'The principal hierarchy '
                                             'clarifies accountability.',
                                  'ipa': '/ˈprɪn.sɪ.pəl ˈhaɪ.ər.ɑːr.ki/',
                                  'meaning': 'hệ thống cấp bậc ủy thác trong '
                                             'tổ chức',
                                  'word': 'principal hierarchy'},
                              {   'example': 'Governance failure caused the '
                                             'financial crisis.',
                                  'ipa': '/ˈɡʌv.ər.nəns ˈfeɪ.ljər/',
                                  'meaning': 'thất bại quản trị dẫn đến tổn '
                                             'thất lớn',
                                  'word': 'governance failure'},
                              {   'example': 'Systemic risk requires '
                                             'regulatory intervention.',
                                  'ipa': '/sɪˈstɛm.ɪk rɪsk/',
                                  'meaning': 'rủi ro hệ thống đe dọa toàn bộ '
                                             'kinh tế',
                                  'word': 'systemic risk'},
                              {   'example': 'Creative destruction drives '
                                             'capitalist progress.',
                                  'ipa': '/kriˈeɪ.tɪv dɪˈstrʌk.ʃən/',
                                  'meaning': 'hủy diệt sáng tạo Schumpeter đổi '
                                             'mới phá hủy cũ',
                                  'word': 'creative destruction'},
                              {   'example': 'Heterodox economics challenges '
                                             'mainstream theory.',
                                  'ipa': '/ˌhɛt.ər.əˈdɒks ˌɪ.kəˈnɒm.ɪks/',
                                  'meaning': 'kinh tế học phi chính thống '
                                             'thách thức dòng chính',
                                  'word': 'heterodox economics'},
                              {   'example': 'Market microstructure affects '
                                             'price discovery.',
                                  'ipa': '/ˈmɑːr.kɪt ˈmaɪ.krəʊ.strʌk.tʃər/',
                                  'meaning': 'vi cấu trúc thị trường cơ chế '
                                             'giao dịch',
                                  'word': 'market microstructure'}]},
    'cooking': {   'B1': [   {   'example': 'Sous vide cooking produces '
                                            'perfectly cooked meat by '
                                            'controlling temperature '
                                            'precisely.',
                                 'ipa': '/suː ˈviːd/',
                                 'meaning': 'kỹ thuật nấu chân không nhiệt độ '
                                            'thấp',
                                 'word': 'sous vide'},
                             {   'example': 'Blanch the spinach for 30 seconds '
                                            'and then transfer to ice water.',
                                 'ipa': '/blɑːntʃ/',
                                 'meaning': 'chần nhanh qua nước sôi',
                                 'word': 'blanch'},
                             {   'example': 'Deglaze the pan with white wine '
                                            'to release all the caramelized '
                                            'bits.',
                                 'ipa': '/diːˈɡleɪz/',
                                 'meaning': 'hòa tan cặn nồi bằng chất lỏng',
                                 'word': 'deglaze'},
                             {   'example': 'Render the bacon fat before '
                                            'adding the vegetables to the pan.',
                                 'ipa': '/ˈren.dər/',
                                 'meaning': 'rán chảy mỡ',
                                 'word': 'render'},
                             {   'example': 'Whisk the oil and vinegar '
                                            'together to emulsify the '
                                            'dressing.',
                                 'ipa': '/ɪˈmʌl.sɪ.faɪ/',
                                 'meaning': 'nhũ hóa',
                                 'word': 'emulsify'},
                             {   'example': 'Make a balsamic reduction to '
                                            'drizzle over the steak.',
                                 'ipa': '/rɪˈdʌk.ʃən/',
                                 'meaning': 'nước sốt cô đặc',
                                 'word': 'reduction'},
                             {   'example': 'Caramelize the onions slowly over '
                                            'low heat for extra sweetness.',
                                 'ipa': '/ˈkær.ə.mə.laɪz/',
                                 'meaning': 'làm vàng/caramel',
                                 'word': 'caramelize'},
                             {   'example': 'Sauté the mushrooms in butter '
                                            'until they are golden brown.',
                                 'ipa': '/ˈsɒt.eɪ/',
                                 'meaning': 'xào nhẹ trong bơ/dầu',
                                 'word': 'sauté'},
                             {   'example': 'Braise the short ribs in red wine '
                                            'for three hours.',
                                 'ipa': '/breɪz/',
                                 'meaning': 'hầm (bít tết...)',
                                 'word': 'braise'},
                             {   'example': 'Poach the eggs gently in '
                                            'simmering water.',
                                 'ipa': '/pəʊtʃ/',
                                 'meaning': 'luộc nhẹ trong nước/sữa',
                                 'word': 'poach'},
                             {   'example': 'Salmon is cured with salt and '
                                            'sugar to make gravlax.',
                                 'ipa': '/kjʊər/',
                                 'meaning': 'ướp muối bảo quản',
                                 'word': 'cure'},
                             {   'example': 'They smoke the ribs over hickory '
                                            'wood for six hours.',
                                 'ipa': '/sməʊk/',
                                 'meaning': 'hun khói',
                                 'word': 'smoke'},
                             {   'example': 'Kimchi is made by fermenting '
                                            'vegetables with spices.',
                                 'ipa': '/fɜːˈment/',
                                 'meaning': 'lên men',
                                 'word': 'ferment'},
                             {   'example': 'She pickled cucumbers in a '
                                            'mixture of vinegar and spices.',
                                 'ipa': '/ˈpɪk.əl/',
                                 'meaning': 'muối chua',
                                 'word': 'pickle'},
                             {   'example': 'Infuse the milk with vanilla '
                                            'beans before making the custard.',
                                 'ipa': '/ɪnˈfjuːz/',
                                 'meaning': 'hãm/ngâm để lấy hương vị',
                                 'word': 'infuse'},
                             {   'example': 'Tempering chocolate gives it a '
                                            'glossy finish and a satisfying '
                                            'snap.',
                                 'ipa': '/ˈtem.pər.ɪŋ/',
                                 'meaning': 'điều hòa nhiệt độ (chocolate)',
                                 'word': 'tempering'},
                             {   'example': 'Professional chefs always '
                                            'practice mise en place for '
                                            'efficiency.',
                                 'ipa': '/ˌmiːz ɒn ˈplɑːs/',
                                 'meaning': 'chuẩn bị nguyên liệu trước khi '
                                            'nấu',
                                 'word': 'mise en place'},
                             {   'example': 'Julienne the carrots into thin '
                                            'matchstick-sized strips.',
                                 'ipa': '/ˌdʒuː.liˈen/',
                                 'meaning': 'thái chỉ mỏng',
                                 'word': 'julienne'},
                             {   'example': 'A brunoise cut produces tiny '
                                            '1-2mm cubes for garnishes.',
                                 'ipa': '/ˈbruː.nwɑːz/',
                                 'meaning': 'thái hạt lựu cực nhỏ',
                                 'word': 'brunoise'},
                             {   'example': 'Roll the basil leaves and cut '
                                            'into a fine chiffonade.',
                                 'ipa': '/ˌʃɪf.əˈnɑːd/',
                                 'meaning': 'thái chỉ lá rau thơm',
                                 'word': 'chiffonade'},
                             {   'example': 'Macerate the strawberries in '
                                            'sugar and balsamic for one hour.',
                                 'ipa': '/ˈmæs.ə.reɪt/',
                                 'meaning': 'ngâm mềm (trái cây) trong '
                                            'đường/rượu',
                                 'word': 'macerate'},
                             {   'example': 'Carefully fold the egg whites '
                                            'into the batter.',
                                 'ipa': '/fəʊld/',
                                 'meaning': 'trộn nhẹ nhàng (không phá vỡ bọt '
                                            'khí)',
                                 'word': 'fold'},
                             {   'example': 'Let the dough proof for one hour '
                                            'before baking.',
                                 'ipa': '/pruːf/',
                                 'meaning': 'ủ bột lên men',
                                 'word': 'proof'},
                             {   'example': 'Score the fish skin to prevent it '
                                            'from curling during cooking.',
                                 'ipa': '/skɔːr/',
                                 'meaning': 'khía rạch (thịt/cá)',
                                 'word': 'score'},
                             {   'example': 'Truss the chicken before roasting '
                                            'to ensure even cooking.',
                                 'ipa': '/trʌs/',
                                 'meaning': 'buộc (thịt gà) trước khi quay',
                                 'word': 'truss'},
                             {   'example': 'Baste the turkey with its own '
                                            'juices every 30 minutes.',
                                 'ipa': '/beɪst/',
                                 'meaning': 'tưới nước thịt lên khi nướng',
                                 'word': 'baste'},
                             {   'example': 'Always rest the meat for 10 '
                                            'minutes after cooking for juicier '
                                            'results.',
                                 'ipa': '/ˈres.tɪŋ miːt/',
                                 'meaning': 'để thịt nghỉ sau khi nấu',
                                 'word': 'resting meat'},
                             {   'example': 'Food safety guidelines prevent '
                                            'contamination and foodborne '
                                            'illness.',
                                 'ipa': '/fuːd ˈseɪf.ti/',
                                 'meaning': 'an toàn thực phẩm',
                                 'word': 'food safety'},
                             {   'example': 'Use separate boards to avoid '
                                            'cross-contamination between meat '
                                            'and produce.',
                                 'ipa': '/ˈkrɒs kənˌtæm.ɪˈneɪ.ʃən/',
                                 'meaning': 'nhiễm chéo vi khuẩn',
                                 'word': 'cross-contamination'},
                             {   'example': 'The chef was careful to avoid nut '
                                            'contamination for guests with a '
                                            'food allergy.',
                                 'ipa': '/fuːd ˈæl.ə.dʒi/',
                                 'meaning': 'dị ứng thực phẩm',
                                 'word': 'food allergy'},
                             {   'example': 'Always ask guests about dietary '
                                            'restrictions before planning the '
                                            'menu.',
                                 'ipa': '/ˈdaɪ.ɪ.tər.i rɪˈstrɪk.ʃən/',
                                 'meaning': 'hạn chế ăn uống',
                                 'word': 'dietary restriction'},
                             {   'example': 'Parmesan cheese and miso add deep '
                                            'umami flavor to dishes.',
                                 'ipa': '/uːˈmɑː.mi/',
                                 'meaning': 'vị umami (vị ngon đặc biệt)',
                                 'word': 'umami'},
                             {   'example': 'The Maillard reaction gives bread '
                                            'and meat their characteristic '
                                            'brown crust.',
                                 'ipa': '/maɪˈjɑːr riˈæk.ʃən/',
                                 'meaning': 'phản ứng Maillard (tạo vỏ vàng)',
                                 'word': 'maillard reaction'},
                             {   'example': 'She trained as a pastry chef and '
                                            'specializes in French desserts.',
                                 'ipa': '/ˈpeɪ.stri/',
                                 'meaning': 'bánh ngọt làm từ bột',
                                 'word': 'pastry'},
                             {   'example': 'Gluten gives bread its chewy, '
                                            'elastic texture.',
                                 'ipa': '/ˈɡluː.tən/',
                                 'meaning': 'gluten (protein trong bột mì)',
                                 'word': 'gluten'},
                             {   'example': 'Add active yeast to the warm '
                                            'water to activate it before '
                                            'using.',
                                 'ipa': '/jiːst/',
                                 'meaning': 'men nở (làm bánh mì)',
                                 'word': 'yeast'},
                             {   'example': 'Add baking powder to the batter '
                                            'to make the cake rise.',
                                 'ipa': '/ˈbeɪ.kɪŋ ˌpaʊ.dər/',
                                 'meaning': 'bột nở',
                                 'word': 'baking powder'},
                             {   'example': 'Dissolve gelatin in warm water '
                                            'before adding it to the mousse.',
                                 'ipa': '/ˈdʒel.ə.tɪn/',
                                 'meaning': 'gelatin',
                                 'word': 'gelatin'},
                             {   'example': 'Whisk together oil, vinegar, and '
                                            'mustard to make a simple '
                                            'vinaigrette.',
                                 'ipa': '/ˌvɪn.ɪˈɡret/',
                                 'meaning': 'sốt dấm dầu',
                                 'word': 'vinaigrette'},
                             {   'example': 'A gastrique is a sweet and sour '
                                            'reduction used to finish savory '
                                            'dishes.',
                                 'ipa': '/ɡæˈstriːk/',
                                 'meaning': 'sốt caramel chua ngọt',
                                 'word': 'gastrique'},
                             {   'example': 'Serve the chocolate cake with a '
                                            'raspberry coulis.',
                                 'ipa': '/ˈkuː.li/',
                                 'meaning': 'sốt trái cây xay',
                                 'word': 'coulis'},
                             {   'example': 'She made a light chocolate mousse '
                                            'for the dinner party.',
                                 'ipa': '/muːs/',
                                 'meaning': 'kem bọt (bánh mousse)',
                                 'word': 'mousse'},
                             {   'example': 'A cheese soufflé must be served '
                                            'immediately or it will collapse.',
                                 'ipa': '/ˈsuː.fleɪ/',
                                 'meaning': 'bánh soufflé (phồng)',
                                 'word': 'soufflé'},
                             {   'example': 'She torched the sugar on the '
                                            'crème brûlée to create the '
                                            'caramel topping.',
                                 'ipa': '/ˌkrem bruːˈleɪ/',
                                 'meaning': 'bánh kem brûlée',
                                 'word': 'crème brûlée'},
                             {   'example': 'The chef prepared a country-style '
                                            'terrine with pork and herbs.',
                                 'ipa': '/təˈriːn/',
                                 'meaning': 'pâté khuôn terrine',
                                 'word': 'terrine'},
                             {   'example': 'The mushroom pâté was served on '
                                            'toasted bread as an appetizer.',
                                 'ipa': '/ˈpæt.eɪ/',
                                 'meaning': 'pâté (gan thịt xay nhuyễn)',
                                 'word': 'pâté'},
                             {   'example': 'Spread tapenade on the bread as a '
                                            'simple but flavorful appetizer.',
                                 'ipa': '/ˈtæp.ɪ.neɪd/',
                                 'meaning': 'sốt ô-liu đen',
                                 'word': 'tapenade'},
                             {   'example': "The chef's artistic plating "
                                            'turned the dish into a visual '
                                            'masterpiece.',
                                 'ipa': '/ˌmiːz ɒn ˈsen/',
                                 'meaning': 'nghệ thuật trình bày đĩa',
                                 'word': 'mise en scène (plating)'},
                             {   'example': 'A good wine pairing enhances the '
                                            'flavors of the meal.',
                                 'ipa': '/ˈpeər.ɪŋ/',
                                 'meaning': 'ghép đôi (rượu + món ăn)',
                                 'word': 'pairing'},
                             {   'example': 'The restaurant offers an '
                                            'eight-course tasting menu on '
                                            'Friday evenings.',
                                 'ipa': '/ˈteɪ.stɪŋ ˈmen.juː/',
                                 'meaning': 'thực đơn thử nhiều món nhỏ',
                                 'word': 'tasting menu'}]},
    'fashion': {   'B1': [   {   'example': 'Haute couture garments are '
                                            "handmade to the client's exact "
                                            'measurements.',
                                 'ipa': '/ˌəʊt kuːˈtjʊər/',
                                 'meaning': 'thời trang cao cấp đặt riêng',
                                 'word': 'haute couture'},
                             {   'example': 'Prêt-à-porter bridges the gap '
                                            'between haute couture and mass '
                                            'market fashion.',
                                 'ipa': '/ˌpret ɑː pɔːˈteɪ/',
                                 'meaning': 'thời trang may sẵn cao cấp',
                                 'word': 'prêt-à-porter'},
                             {   'example': 'Fast fashion produces cheap, '
                                            'trend-led clothing at high '
                                            'volume.',
                                 'ipa': '/fɑːst ˈfæʃ.ən/',
                                 'meaning': 'thời trang nhanh, giá rẻ',
                                 'word': 'fast fashion'},
                             {   'example': 'Slow fashion advocates for '
                                            'quality, durability, and ethical '
                                            'production.',
                                 'ipa': '/sləʊ ˈfæʃ.ən/',
                                 'meaning': 'thời trang chậm, bền vững',
                                 'word': 'slow fashion'},
                             {   'example': 'Sustainable fashion uses '
                                            'eco-friendly materials and '
                                            'ethical labor practices.',
                                 'ipa': '/səˈsteɪ.nə.bəl ˈfæʃ.ən/',
                                 'meaning': 'thời trang bền vững',
                                 'word': 'sustainable fashion'},
                             {   'example': 'She upcycled old jeans into '
                                            'stylish shorts to reduce waste.',
                                 'ipa': '/ˈʌp.saɪ.klɪŋ/',
                                 'meaning': 'tái chế sáng tạo quần áo',
                                 'word': 'upcycling (fashion)'},
                             {   'example': 'The designer launched a capsule '
                                            'collection of ten essential '
                                            'pieces.',
                                 'ipa': '/ˈkæp.sjuːl kəˈlek.ʃən/',
                                 'meaning': 'bộ sưu tập giới hạn',
                                 'word': 'capsule collection'},
                             {   'example': 'The brand released a stunning '
                                            'lookbook for its spring '
                                            'collection.',
                                 'ipa': '/ˈlʊk.bʊk/',
                                 'meaning': 'sách ảnh trang phục mẫu',
                                 'word': 'lookbook'},
                             {   'example': 'She was featured in a Vogue '
                                            'fashion editorial.',
                                 'ipa': '/ˌɛdəˈtɔriəl (ˈfæʃən)/',
                                 'meaning': 'ảnh thời trang tạp chí',
                                 'word': 'editorial (fashion)'},
                             {   'example': 'The designer favors a slim, '
                                            'tailored silhouette.',
                                 'ipa': '/ˌsɪl.uˈet/',
                                 'meaning': 'dáng (thiết kế quần áo)',
                                 'word': 'silhouette'},
                             {   'example': 'The silk dress has a beautiful '
                                            'drape that flatters the figure.',
                                 'ipa': '/dreɪp/',
                                 'meaning': 'cách vải buông, rủ',
                                 'word': 'drape'},
                             {   'example': 'The fit and flare dress is '
                                            'universally flattering on all '
                                            'body types.',
                                 'ipa': '/fɪt ənd fleər/',
                                 'meaning': 'dáng ôm trên, xòe dưới',
                                 'word': 'fit and flare'},
                             {   'example': 'She chose an A-line skirt for the '
                                            'wedding.',
                                 'ipa': '/ˈeɪ laɪn/',
                                 'meaning': 'dáng chữ A',
                                 'word': 'A-line'},
                             {   'example': 'A peplum top creates an hourglass '
                                            'silhouette.',
                                 'ipa': '/ˈpep.ləm/',
                                 'meaning': 'kiểu áo xòe ở eo',
                                 'word': 'peplum'},
                             {   'example': 'Midi skirts are a versatile and '
                                            'elegant choice.',
                                 'ipa': '/ˈmɪd.i/',
                                 'meaning': 'độ dài midi (đến bắp chân)',
                                 'word': 'midi'},
                             {   'example': 'She wore a flowing maxi dress to '
                                            'the beach wedding.',
                                 'ipa': '/ˈmæk.si/',
                                 'meaning': 'váy/áo dài đến mắt cá',
                                 'word': 'maxi'},
                             {   'example': 'Mini skirts were iconic in the '
                                            '1960s fashion revolution.',
                                 'ipa': '/ˈmɪn.i/',
                                 'meaning': 'váy/áo ngắn',
                                 'word': 'mini'},
                             {   'example': 'She paired a cropped top with '
                                            'high-waisted trousers.',
                                 'ipa': '/krɒpt/',
                                 'meaning': 'áo ngắn cắt gọn',
                                 'word': 'cropped'},
                             {   'example': 'Oversized blazers are a staple of '
                                            'contemporary streetwear.',
                                 'ipa': '/ˌəʊ.vəˈsaɪzd/',
                                 'meaning': 'quá khổ, rộng thùng thình',
                                 'word': 'oversized'},
                             {   'example': 'A tailored suit always looks '
                                            'professional and sharp.',
                                 'ipa': '/ˈteɪ.ləd/',
                                 'meaning': 'may đo vừa vặn, trang nhã',
                                 'word': 'tailored'},
                             {   'example': 'He had a bespoke suit made for '
                                            'his wedding day.',
                                 'ipa': '/bɪˈspəʊk/',
                                 'meaning': 'đặt may riêng theo yêu cầu',
                                 'word': 'bespoke'},
                             {   'example': 'She bought an off-the-rack blazer '
                                            'and had it altered.',
                                 'ipa': '/ˌɒf.ðəˈræk/',
                                 'meaning': 'quần áo may sẵn',
                                 'word': 'off-the-rack'},
                             {   'example': 'Athleisure blends athletic wear '
                                            'with casual everyday fashion.',
                                 'ipa': '/ˈæθ.liːʒ.ər/',
                                 'meaning': 'phong cách thể thao-thời trang',
                                 'word': 'athleisure'},
                             {   'example': 'Brands like Supreme and Off-White '
                                            'dominate the streetwear market.',
                                 'ipa': '/ˈstriːt.weər/',
                                 'meaning': 'thời trang đường phố',
                                 'word': 'streetwear'},
                             {   'example': 'She loves the boho style with '
                                            'flowy fabrics and earthy tones.',
                                 'ipa': '/ˈbəʊ.həʊ/',
                                 'meaning': 'phong cách bohemian',
                                 'word': 'boho'},
                             {   'example': 'Her minimalist fashion choices '
                                            'focus on clean lines and neutral '
                                            'colors.',
                                 'ipa': '/ˈmɪn.ɪ.mə.lɪst ˈfæʃ.ən/',
                                 'meaning': 'thời trang tối giản',
                                 'word': 'minimalist fashion'},
                             {   'example': 'Maximalist fashion embraces bold '
                                            'colors, prints, and accessories.',
                                 'ipa': '/ˈmæk.sɪ.mə.lɪst ˈfæʃ.ən/',
                                 'meaning': 'thời trang tối đa (nhiều màu, hoạ '
                                            'tiết)',
                                 'word': 'maximalist fashion'},
                             {   'example': 'Gender-neutral fashion challenges '
                                            'traditional clothing norms.',
                                 'ipa': '/ˈdʒen.dər ˌnjuː.trəl ˈfæʃ.ən/',
                                 'meaning': 'thời trang phi giới tính',
                                 'word': 'gender-neutral fashion'},
                             {   'example': 'She embraces an androgynous style '
                                            'with sharp suits and bold '
                                            'accessories.',
                                 'ipa': '/ænˈdrɒdʒ.ɪ.nəs staɪl/',
                                 'meaning': 'phong cách lưỡng tính',
                                 'word': 'androgynous style'},
                             {   'example': 'Capsule wardrobe planning helps '
                                            'you dress better with fewer '
                                            'items.',
                                 'ipa': '/ˈkæp.sjuːl ˈwɔː.drəʊb ˈplæn.ɪŋ/',
                                 'meaning': 'lên kế hoạch tủ đồ tối giản',
                                 'word': 'capsule wardrobe planning'},
                             {   'example': 'Understanding color theory helps '
                                            'you create harmonious outfits.',
                                 'ipa': '/ˈkʌl.ər ˈθɪər.i/',
                                 'meaning': 'lý thuyết màu sắc ứng dụng thời '
                                            'trang',
                                 'word': 'color theory (fashion)'},
                             {   'example': 'Blue and orange are complementary '
                                            'colors that create a striking '
                                            'contrast.',
                                 'ipa': '/ˌkɒm.plɪˈmen.tər.i ˈkʌl.ərz/',
                                 'meaning': 'màu bổ trợ (tương phản)',
                                 'word': 'complementary colors'},
                             {   'example': 'She hired a personal shopper to '
                                            'help update her wardrobe.',
                                 'ipa': '/ˈpɜː.sən.əl ˈʃɒp.ər/',
                                 'meaning': 'người mua sắm cá nhân',
                                 'word': 'personal shopper'},
                             {   'example': "The celebrity's fashion stylist "
                                            'chooses all her red-carpet '
                                            'outfits.',
                                 'ipa': '/ˈfæʃ.ən ˈstaɪ.lɪst/',
                                 'meaning': 'chuyên gia phong cách thời trang',
                                 'word': 'fashion stylist'},
                             {   'example': 'The fashion photographer worked '
                                            'with Vogue for 20 years.',
                                 'ipa': '/ˈfæʃ.ən fəˈtɒɡ.rə.fər/',
                                 'meaning': 'nhiếp ảnh gia thời trang',
                                 'word': 'fashion photographer'},
                             {   'example': 'The four major fashion weeks are '
                                            'held in New York, London, Milan, '
                                            'and Paris.',
                                 'ipa': '/ˈfæʃ.ən wiːk/',
                                 'meaning': 'tuần lễ thời trang',
                                 'word': 'fashion week'},
                             {   'example': 'The models walked the catwalk to '
                                            'showcase the new collection.',
                                 'ipa': '/ˈkæt.wɔːk/',
                                 'meaning': 'sàn trình diễn thời trang',
                                 'word': 'catwalk'},
                             {   'example': 'She got a designer dress at a '
                                            'fraction of the price at a sample '
                                            'sale.',
                                 'ipa': '/ˈsɑːm.pəl seɪl/',
                                 'meaning': 'bán hàng mẫu giảm giá',
                                 'word': 'sample sale'},
                             {   'example': 'She buys preloved luxury handbags '
                                            'to save money.',
                                 'ipa': '/ˌpriːˈlʌvd/',
                                 'meaning': 'đồ đã qua sử dụng (mua lại)',
                                 'word': 'preloved'},
                             {   'example': 'She found a stunning vintage '
                                            'dress at the thrift shop for $5.',
                                 'ipa': '/θrɪft ʃɒp/',
                                 'meaning': 'cửa hàng đồ cũ từ thiện',
                                 'word': 'thrift shop'},
                             {   'example': 'She became a successful fashion '
                                            'influencer through her Instagram '
                                            'posts.',
                                 'ipa': '/ˈfæʃ.ən ˈɪn.fluː.ən.sər/',
                                 'meaning': 'người ảnh hưởng về thời trang',
                                 'word': 'fashion influencer'},
                             {   'example': 'She posts her OOTD on Instagram '
                                            'every morning.',
                                 'ipa': '/ˈaʊt.fɪt əv ðə deɪ/',
                                 'meaning': 'trang phục hôm nay',
                                 'word': 'outfit of the day (OOTD)'},
                             {   'example': 'She started as a fashion blogger '
                                            'and grew to 1 million followers.',
                                 'ipa': '/ˈfæʃ.ən ˈblɒɡ.ər/',
                                 'meaning': 'blogger thời trang',
                                 'word': 'fashion blogger'},
                             {   'example': 'She receives a monthly '
                                            'subscription box with curated '
                                            'clothing items.',
                                 'ipa': '/səbˈskrɪp.ʃən bɒks/',
                                 'meaning': 'hộp quần áo đăng ký',
                                 'word': 'subscription box (fashion)'},
                             {   'example': 'Rental fashion services let you '
                                            'wear new outfits without buying.',
                                 'ipa': '/ˈren.təl ˈfæʃ.ən/',
                                 'meaning': 'thuê trang phục',
                                 'word': 'rental fashion'},
                             {   'example': 'Fashion archives preserve iconic '
                                            'looks for future generations.',
                                 'ipa': '/ˈfæʃ.ən ˈɑː.kaɪv/',
                                 'meaning': 'kho lưu trữ thời trang',
                                 'word': 'fashion archive'},
                             {   'example': 'Burberry and Chanel are iconic '
                                            'heritage brands.',
                                 'ipa': '/ˈher.ɪ.tɪdʒ brænd/',
                                 'meaning': 'thương hiệu lâu đời',
                                 'word': 'heritage brand'},
                             {   'example': 'Logomania returned as a major '
                                            'trend with visible brand logos on '
                                            'clothing.',
                                 'ipa': '/ˌləʊ.ɡəʊˈmeɪ.ni.ə/',
                                 'meaning': 'trào lưu khoe logo thương hiệu',
                                 'word': 'logomania'},
                             {   'example': 'The athleisure trend grew '
                                            'significantly during the '
                                            'work-from-home era.',
                                 'ipa': '/ˈæθ.liːʒ.ər trend/',
                                 'meaning': 'xu hướng trang phục thể '
                                            'thao-thường nhật',
                                 'word': 'athleisure trend'},
                             {   'example': 'Fashion tech includes virtual '
                                            'fitting rooms and AI-powered '
                                            'recommendations.',
                                 'ipa': '/ˈfæʃ.ən tek/',
                                 'meaning': 'công nghệ ứng dụng trong thời '
                                            'trang',
                                 'word': 'fashion tech'}]},
    'finance': {   'A1': [   {   'example': 'She saves money every month for '
                                            'her vacation.',
                                 'ipa': '/ˈmʌn.i/',
                                 'meaning': 'tiền',
                                 'word': 'money'},
                             {   'example': 'I want to buy a new phone next '
                                            'month.',
                                 'ipa': '/baɪ/',
                                 'meaning': 'mua',
                                 'word': 'buy'},
                             {   'example': 'He decided to sell his car to pay '
                                            'for his studies.',
                                 'ipa': '/sel/',
                                 'meaning': 'bán',
                                 'word': 'sell'},
                             {   'example': 'Can I pay by credit card?',
                                 'ipa': '/peɪ/',
                                 'meaning': 'thanh toán, trả tiền',
                                 'word': 'pay'},
                             {   'example': 'How much does this product cost?',
                                 'ipa': '/kɒst/',
                                 'meaning': 'giá cả',
                                 'word': 'cost'},
                             {   'example': 'The price of this jacket is too '
                                            'high for me.',
                                 'ipa': '/praɪs/',
                                 'meaning': 'giá',
                                 'word': 'price'},
                             {   'example': 'I try to save at least 20% of my '
                                            'income every month.',
                                 'ipa': '/seɪv/',
                                 'meaning': 'tiết kiệm',
                                 'word': 'save'},
                             {   'example': 'She opened a savings account at '
                                            'the bank.',
                                 'ipa': '/bæŋk/',
                                 'meaning': 'ngân hàng',
                                 'word': 'bank'},
                             {   'example': 'Do you have enough cash to pay '
                                            'for the meal?',
                                 'ipa': '/kæʃ/',
                                 'meaning': 'tiền mặt',
                                 'word': 'cash'},
                             {   'example': 'She paid for the groceries with '
                                            'her debit card.',
                                 'ipa': '/kɑːd/',
                                 'meaning': 'thẻ ngân hàng',
                                 'word': 'card'},
                             {   'example': 'I try not to spend too much on '
                                            'clothes.',
                                 'ipa': '/spend/',
                                 'meaning': 'chi tiêu',
                                 'word': 'spend'},
                             {   'example': 'This supermarket is cheap '
                                            'compared to others.',
                                 'ipa': '/tʃiːp/',
                                 'meaning': 'rẻ',
                                 'word': 'cheap'},
                             {   'example': 'The restaurant is too expensive '
                                            'for us to eat there every week.',
                                 'ipa': '/ɪkˈspen.sɪv/',
                                 'meaning': 'đắt tiền',
                                 'word': 'expensive'},
                             {   'example': 'The museum is free to enter on '
                                            'Sundays.',
                                 'ipa': '/friː/',
                                 'meaning': 'miễn phí',
                                 'word': 'free'},
                             {   'example': 'The store is offering a 20% '
                                            'discount on all shoes.',
                                 'ipa': '/ˈdɪs.kaʊnt/',
                                 'meaning': 'giảm giá',
                                 'word': 'discount'},
                             {   'example': 'I bought a coat in the winter '
                                            'sale.',
                                 'ipa': '/seɪl/',
                                 'meaning': 'đợt giảm giá',
                                 'word': 'sale'},
                             {   'example': 'Keep the receipt in case you want '
                                            'to return the item.',
                                 'ipa': '/rɪˈsiːt/',
                                 'meaning': 'hóa đơn',
                                 'word': 'receipt'},
                             {   'example': 'Here is your change — $5 back '
                                            'from $20.',
                                 'ipa': '/tʃeɪndʒ/',
                                 'meaning': 'tiền thối lại',
                                 'word': 'change'},
                             {   'example': 'He lost his wallet with all his '
                                            'cards inside.',
                                 'ipa': '/ˈwɒl.ɪt/',
                                 'meaning': 'ví tiền',
                                 'word': 'wallet'},
                             {   'example': 'She found a few coins in her coat '
                                            'pocket.',
                                 'ipa': '/kɔɪn/',
                                 'meaning': 'đồng xu',
                                 'word': 'coin'},
                             {   'example': 'She paid the electricity bill '
                                            'online this month.',
                                 'ipa': '/bɪl/',
                                 'meaning': 'tờ tiền; hóa đơn',
                                 'word': 'bill'},
                             {   'example': 'I have a savings account and a '
                                            'checking account.',
                                 'ipa': '/əˈkaʊnt/',
                                 'meaning': 'tài khoản ngân hàng',
                                 'word': 'account'},
                             {   'example': 'He took out a loan to buy his '
                                            'first car.',
                                 'ipa': '/ləʊn/',
                                 'meaning': 'khoản vay',
                                 'word': 'loan'},
                             {   'example': 'Can I borrow 50 dollars until '
                                            'next week?',
                                 'ipa': '/ˈbɒr.əʊ/',
                                 'meaning': 'vay mượn',
                                 'word': 'borrow'},
                             {   'example': 'She pays 500 dollars in rent '
                                            'every month.',
                                 'ipa': '/rent/',
                                 'meaning': 'tiền thuê nhà/xe',
                                 'word': 'rent'},
                             {   'example': 'His monthly income is enough to '
                                            'cover all expenses.',
                                 'ipa': '/ˈɪŋ.kʌm/',
                                 'meaning': 'thu nhập',
                                 'word': 'income'},
                             {   'example': 'Everyone must pay income tax '
                                            'every year.',
                                 'ipa': '/tæks/',
                                 'meaning': 'thuế',
                                 'word': 'tax'},
                             {   'example': 'Her salary increased after her '
                                            'promotion.',
                                 'ipa': '/ˈsæl.ər.i/',
                                 'meaning': 'lương tháng',
                                 'word': 'salary'},
                             {   'example': 'He earns minimum wage at his '
                                            'part-time job.',
                                 'ipa': '/weɪdʒ/',
                                 'meaning': 'tiền công (theo giờ/ngày)',
                                 'word': 'wage'},
                             {   'example': 'She decided to invest in stocks '
                                            'for the long term.',
                                 'ipa': '/ɪnˈvest/',
                                 'meaning': 'đầu tư',
                                 'word': 'invest'},
                             {   'example': 'The shop made a good profit last '
                                            'year.',
                                 'ipa': '/ˈprɒf.ɪt/',
                                 'meaning': 'lợi nhuận',
                                 'word': 'profit'},
                             {   'example': 'The business suffered a loss '
                                            'during the pandemic.',
                                 'ipa': '/lɒs/',
                                 'meaning': 'lỗ, thua lỗ',
                                 'word': 'loss'},
                             {   'example': 'It took him five years to pay off '
                                            'his debt.',
                                 'ipa': '/det/',
                                 'meaning': 'nợ',
                                 'word': 'debt'},
                             {   'example': 'I will transfer the money to your '
                                            'account tonight.',
                                 'ipa': '/ˈtræns.fɜːr/',
                                 'meaning': 'chuyển khoản',
                                 'word': 'transfer'},
                             {   'example': 'She withdrew $200 from the ATM.',
                                 'ipa': '/wɪðˈdrɔː/',
                                 'meaning': 'rút tiền',
                                 'word': 'withdraw'},
                             {   'example': 'He deposited his salary into his '
                                            'savings account.',
                                 'ipa': '/dɪˈpɒz.ɪt/',
                                 'meaning': 'gửi tiền vào tài khoản',
                                 'word': 'deposit'},
                             {   'example': 'She used the ATM to get some '
                                            'cash.',
                                 'ipa': '/ˌeɪ.tiːˈem/',
                                 'meaning': 'máy rút tiền tự động',
                                 'word': 'ATM'},
                             {   'example': 'The bank pays 3% interest on '
                                            'savings accounts.',
                                 'ipa': '/ˈɪn.trəst/',
                                 'meaning': 'lãi suất; tiền lãi',
                                 'word': 'interest'},
                             {   'example': 'We need to stay within our '
                                            'monthly budget.',
                                 'ipa': '/ˈbʌdʒ.ɪt/',
                                 'meaning': 'ngân sách',
                                 'word': 'budget'},
                             {   'example': 'Check the exchange rate before '
                                            'converting your money.',
                                 'ipa': '/ɪksˈtʃeɪndʒ reɪt/',
                                 'meaning': 'tỷ giá hối đoái',
                                 'word': 'exchange rate'},
                             {   'example': "The US dollar is the world's most "
                                            'traded currency.',
                                 'ipa': '/ˈkʌr.ən.si/',
                                 'meaning': 'tiền tệ',
                                 'word': 'currency'},
                             {   'example': 'Please go to the checkout to pay '
                                            'for your items.',
                                 'ipa': '/ˈtʃek.aʊt/',
                                 'meaning': 'thanh toán (tại quầy)',
                                 'word': 'checkout'},
                             {   'example': 'The bank recorded every '
                                            'transaction in its system.',
                                 'ipa': '/trænˈzækʃən/',
                                 'meaning': 'Giao dịch tài chính',
                                 'word': 'transaction'},
                             {   'example': 'There is a small fee for using '
                                            'the ATM abroad.',
                                 'ipa': '/fiː/',
                                 'meaning': 'phí dịch vụ',
                                 'word': 'fee'},
                             {   'example': 'She has a good credit score, so '
                                            'she got a loan easily.',
                                 'ipa': '/ˈkred.ɪt/',
                                 'meaning': 'tín dụng',
                                 'word': 'credit'},
                             {   'example': 'The payment was debited directly '
                                            'from her bank account.',
                                 'ipa': '/ˈdeb.ɪt/',
                                 'meaning': 'ghi nợ (trừ tiền từ tài khoản)',
                                 'word': 'debit'},
                             {   'example': 'She is worried about her '
                                            'financial situation.',
                                 'ipa': '/faɪˈnæn.ʃəl/',
                                 'meaning': 'tài chính (tính từ)',
                                 'word': 'financial'},
                             {   'example': 'He became rich after starting a '
                                            'successful business.',
                                 'ipa': '/rɪtʃ/',
                                 'meaning': 'giàu có',
                                 'word': 'rich'},
                             {   'example': 'Growing up poor motivated him to '
                                            'work hard and succeed.',
                                 'ipa': '/pɔːr/',
                                 'meaning': 'nghèo',
                                 'word': 'poor'},
                             {   'example': 'I cannot afford to buy a new car '
                                            'right now.',
                                 'ipa': '/əˈfɔːd/',
                                 'meaning': 'đủ khả năng mua',
                                 'word': 'afford'}],
                   'B1': [   {   'example': 'Smart asset allocation balances '
                                            'risk across stocks, bonds, and '
                                            'real estate.',
                                 'ipa': '/ˈæs.et ˌæl.əˈkeɪ.ʃən/',
                                 'meaning': 'phân bổ tài sản đầu tư',
                                 'word': 'asset allocation'},
                             {   'example': 'Diversification reduces risk by '
                                            'spreading investments across '
                                            'different sectors.',
                                 'ipa': '/daɪˌvɜː.sɪ.fɪˈkeɪ.ʃən/',
                                 'meaning': 'đa dạng hóa danh mục đầu tư',
                                 'word': 'diversification'},
                             {   'example': 'Cash is the most liquid asset you '
                                            'can hold.',
                                 'ipa': '/lɪˈkwɪd.ɪ.ti/',
                                 'meaning': 'tính thanh khoản',
                                 'word': 'liquidity'},
                             {   'example': 'A mutual fund pools money from '
                                            'many investors to buy a '
                                            'diversified portfolio.',
                                 'ipa': '/ˈmjuː.tʃu.əl fʌnd/',
                                 'meaning': 'quỹ tương hỗ',
                                 'word': 'mutual fund'},
                             {   'example': 'An index fund tracks a market '
                                            'index like the S&P 500.',
                                 'ipa': '/ˈɪn.deks fʌnd/',
                                 'meaning': 'quỹ chỉ số',
                                 'word': 'index fund'},
                             {   'example': 'ETFs combine the benefits of '
                                            'mutual funds and individual '
                                            'stocks.',
                                 'ipa': '/ˌiː.tiːˈef/',
                                 'meaning': 'quỹ giao dịch trên sàn',
                                 'word': 'ETF (Exchange-Traded Fund)'},
                             {   'example': 'Stock prices rose sharply during '
                                            'the bull market.',
                                 'ipa': '/bʊl ˈmɑː.kɪt/',
                                 'meaning': 'thị trường tăng giá',
                                 'word': 'bull market'},
                             {   'example': 'Many investors sold their stocks '
                                            'during the bear market.',
                                 'ipa': '/beər ˈmɑː.kɪt/',
                                 'meaning': 'thị trường giảm giá',
                                 'word': 'bear market'},
                             {   'example': 'A 10% drop in stock prices is '
                                            'considered a market correction.',
                                 'ipa': '/ˈmɑː.kɪt kəˈrek.ʃən/',
                                 'meaning': 'điều chỉnh thị trường',
                                 'word': 'market correction'},
                             {   'example': 'Dollar-cost averaging reduces the '
                                            'impact of market volatility on '
                                            'investments.',
                                 'ipa': '/ˈdɒl.ər kɒst ˈæv.ər.ɪ.dʒɪŋ/',
                                 'meaning': 'mua định kỳ trung bình giá',
                                 'word': 'dollar-cost averaging'},
                             {   'example': 'Annual rebalancing keeps your '
                                            'portfolio aligned with your '
                                            'target allocation.',
                                 'ipa': '/ˌriːˈbæl.əns.ɪŋ/',
                                 'meaning': 'tái cân bằng danh mục',
                                 'word': 'rebalancing'},
                             {   'example': 'Capital gains tax applies when '
                                            'you sell an asset for more than '
                                            'you paid.',
                                 'ipa': '/ˈkæp.ɪ.təl ɡeɪnz tæks/',
                                 'meaning': 'thuế lãi vốn',
                                 'word': 'capital gains tax'},
                             {   'example': 'A 401(k) is a tax-advantaged '
                                            'account for retirement savings.',
                                 'ipa': '/tæks ədˈvɑːn.tɪdʒd əˈkaʊnt/',
                                 'meaning': 'tài khoản ưu đãi thuế',
                                 'word': 'tax-advantaged account'},
                             {   'example': 'The net asset value of the fund '
                                            'increased by 12% this year.',
                                 'ipa': '/net ˈæs.et ˈvæl.juː/',
                                 'meaning': 'giá trị tài sản ròng',
                                 'word': 'net asset value'},
                             {   'example': 'Choose funds with a low expense '
                                            'ratio to maximize returns.',
                                 'ipa': '/ɪkˈspens ˈreɪ.ʃi.əʊ/',
                                 'meaning': 'tỷ lệ chi phí quản lý quỹ',
                                 'word': 'expense ratio'},
                             {   'example': 'You need a brokerage account to '
                                            'buy and sell stocks.',
                                 'ipa': '/ˈbrəʊ.kər.ɪdʒ əˈkaʊnt/',
                                 'meaning': 'tài khoản môi giới chứng khoán',
                                 'word': 'brokerage account'},
                             {   'example': 'She bought shares listed on the '
                                            'New York Stock Exchange.',
                                 'ipa': '/stɒk ɪksˈtʃeɪndʒ/',
                                 'meaning': 'sàn giao dịch chứng khoán',
                                 'word': 'stock exchange'},
                             {   'example': 'Large-cap companies have a market '
                                            'capitalization over $10 billion.',
                                 'ipa': '/ˈmɑː.kɪt ˌkæp.ɪ.t.əl.aɪˈzeɪ.ʃən/',
                                 'meaning': 'vốn hóa thị trường',
                                 'word': 'market capitalization'},
                             {   'example': 'A low P/E ratio may indicate an '
                                            'undervalued stock.',
                                 'ipa': '/piː tuː ˈɜː.nɪŋz ˈreɪ.ʃi.əʊ/',
                                 'meaning': 'tỷ lệ giá/lợi nhuận',
                                 'word': 'P/E ratio'},
                             {   'example': 'Rising earnings per share signal '
                                            'a healthy and growing company.',
                                 'ipa': '/ˈɜː.nɪŋz pər ʃeər/',
                                 'meaning': 'lợi nhuận trên mỗi cổ phần',
                                 'word': 'earnings per share'},
                             {   'example': 'Fundamental analysis evaluates a '
                                            "company's financials to determine "
                                            'its intrinsic value.',
                                 'ipa': '/ˌfʌn.dəˈmen.təl əˈnæl.ɪ.sɪs/',
                                 'meaning': 'phân tích cơ bản',
                                 'word': 'fundamental analysis'},
                             {   'example': 'Technical analysis uses price '
                                            'charts and patterns to predict '
                                            'future movements.',
                                 'ipa': '/ˈtek.nɪ.kəl əˈnæl.ɪ.sɪs/',
                                 'meaning': 'phân tích kỹ thuật',
                                 'word': 'technical analysis'},
                             {   'example': 'Short selling profits when a '
                                            "stock's price falls.",
                                 'ipa': '/ʃɔːt ˈsel.ɪŋ/',
                                 'meaning': 'bán khống',
                                 'word': 'short selling'},
                             {   'example': 'Margin trading amplifies returns '
                                            'but also increases risk of loss.',
                                 'ipa': '/ˈmɑː.dʒɪn ˈtreɪ.dɪŋ/',
                                 'meaning': 'giao dịch ký quỹ',
                                 'word': 'margin trading'},
                             {   'example': 'Options trading allows investors '
                                            'to hedge against market '
                                            'movements.',
                                 'ipa': '/ˈɒp.ʃənz ˈtreɪ.dɪŋ/',
                                 'meaning': 'giao dịch quyền chọn',
                                 'word': 'options trading'},
                             {   'example': 'Farmers use futures contracts to '
                                            'lock in crop prices in advance.',
                                 'ipa': '/ˈfjuː.tʃərz ˈkɒn.trækt/',
                                 'meaning': 'hợp đồng tương lai',
                                 'word': 'futures contract'},
                             {   'example': 'Gold and oil are popular '
                                            'commodity investments.',
                                 'ipa': '/kəˈmɒd.ɪ.ti/',
                                 'meaning': 'hàng hóa (đầu tư)',
                                 'word': 'commodity'},
                             {   'example': 'Real estate investment provides '
                                            'both income and capital '
                                            'appreciation.',
                                 'ipa': '/rɪəl ɪˈsteɪt ɪnˈvest.mənt/',
                                 'meaning': 'đầu tư bất động sản',
                                 'word': 'real estate investment'},
                             {   'example': "Bitcoin is the world's most "
                                            'well-known cryptocurrency.',
                                 'ipa': '/ˈkrɪp.təʊˌkʌr.ən.si/',
                                 'meaning': 'tiền điện tử',
                                 'word': 'cryptocurrency'},
                             {   'example': 'Blockchain technology underpins '
                                            'most cryptocurrencies.',
                                 'ipa': '/ˈblɒk.tʃeɪn/',
                                 'meaning': 'chuỗi khối (công nghệ)',
                                 'word': 'blockchain'},
                             {   'example': 'Fintech companies are disrupting '
                                            'traditional banking with '
                                            'innovative solutions.',
                                 'ipa': '/ˈfɪn.tek/',
                                 'meaning': 'công nghệ tài chính',
                                 'word': 'fintech'},
                             {   'example': 'A robo-advisor automatically '
                                            'manages your investments based on '
                                            'your goals.',
                                 'ipa': '/ˌrəʊ.bəʊ ədˈvaɪ.zər/',
                                 'meaning': 'cố vấn đầu tư tự động',
                                 'word': 'robo-advisor'},
                             {   'example': 'Financial planning helps you '
                                            'achieve your short and long-term '
                                            'money goals.',
                                 'ipa': '/faɪˈnæn.ʃəl ˈplæn.ɪŋ/',
                                 'meaning': 'lập kế hoạch tài chính',
                                 'word': 'financial planning'},
                             {   'example': 'Estate planning involves creating '
                                            'a will and designating '
                                            'beneficiaries.',
                                 'ipa': '/ɪˈsteɪt ˈplæn.ɪŋ/',
                                 'meaning': 'lập kế hoạch di sản',
                                 'word': 'estate planning'},
                             {   'example': 'She updated her will to include '
                                            'her new grandchildren.',
                                 'ipa': '/wɪl (ˈligəl)/',
                                 'meaning': 'di chúc',
                                 'word': 'will (legal)'},
                             {   'example': 'The parents set up a trust fund '
                                            "for their children's education.",
                                 'ipa': '/trʌst fʌnd/',
                                 'meaning': 'quỹ tín thác',
                                 'word': 'trust fund'},
                             {   'example': 'The company filed for bankruptcy '
                                            'after years of losses.',
                                 'ipa': '/ˈbæŋk.rʌp.si/',
                                 'meaning': 'phá sản',
                                 'word': 'bankruptcy'},
                             {   'example': 'Insolvency means a company cannot '
                                            'meet its financial obligations.',
                                 'ipa': '/ɪnˈsɒl.vən.si/',
                                 'meaning': 'mất khả năng thanh toán',
                                 'word': 'insolvency'},
                             {   'example': 'A healthy cash reserve protects '
                                            'businesses during economic '
                                            'downturns.',
                                 'ipa': '/kæʃ rɪˈzɜːv/',
                                 'meaning': 'dự trữ tiền mặt',
                                 'word': 'cash reserve'},
                             {   'example': 'Efficient working capital '
                                            'management ensures smooth daily '
                                            'operations.',
                                 'ipa': '/ˈwɜː.kɪŋ ˈkæp.ɪ.təl ˈmæn.ɪdʒ.mənt/',
                                 'meaning': 'quản lý vốn lưu động',
                                 'word': 'working capital management'},
                             {   'example': 'Accelerating accounts receivable '
                                            'collection improves cash flow.',
                                 'ipa': '/əˈkaʊnts rɪˈsiː.və.bəl/',
                                 'meaning': 'khoản phải thu',
                                 'word': 'accounts receivable'},
                             {   'example': 'Managing accounts payable '
                                            'efficiently maintains supplier '
                                            'relationships.',
                                 'ipa': '/əˈkaʊnts ˈpeɪ.ə.bəl/',
                                 'meaning': 'khoản phải trả',
                                 'word': 'accounts payable'},
                             {   'example': 'The finance team processes '
                                            'payroll at the end of each month.',
                                 'ipa': '/ˈpeɪ.rəʊl/',
                                 'meaning': 'bảng lương nhân viên',
                                 'word': 'payroll'},
                             {   'example': "The company's fiscal year runs "
                                            'from April to March.',
                                 'ipa': '/ˈfɪs.kəl jɪər/',
                                 'meaning': 'năm tài chính',
                                 'word': 'fiscal year'},
                             {   'example': 'Investors pay close attention to '
                                            'quarterly earnings reports.',
                                 'ipa': '/ˈkwɔː.tər.li ˈɜː.nɪŋz/',
                                 'meaning': 'lợi nhuận hàng quý',
                                 'word': 'quarterly earnings'},
                             {   'example': 'Revenue recognition rules '
                                            'determine when income is '
                                            'officially recorded.',
                                 'ipa': '/ˈrev.ən.juː ˌrek.əɡˈnɪʃ.ən/',
                                 'meaning': 'ghi nhận doanh thu',
                                 'word': 'revenue recognition'},
                             {   'example': 'The cash flow statement shows how '
                                            'money moves in and out of the '
                                            'business.',
                                 'ipa': '/kæʃ fləʊ ˈsteɪt.mənt/',
                                 'meaning': 'báo cáo lưu chuyển tiền tệ',
                                 'word': 'cash flow statement'},
                             {   'example': "A balance sheet shows a company's "
                                            'assets, liabilities, and equity.',
                                 'ipa': '/ˈbæl.əns ʃiːt/',
                                 'meaning': 'bảng cân đối kế toán',
                                 'word': 'balance sheet'},
                             {   'example': 'The income statement shows '
                                            'revenues and expenses over a '
                                            'period.',
                                 'ipa': '/ˈɪŋ.kʌm ˈsteɪt.mənt/',
                                 'meaning': 'báo cáo kết quả kinh doanh',
                                 'word': 'income statement'},
                             {   'example': 'Accrual accounting records income '
                                            'when earned, not when cash is '
                                            'received.',
                                 'ipa': '/əˈkruː.əl əˈkaʊn.tɪŋ/',
                                 'meaning': 'kế toán dồn tích',
                                 'word': 'accrual accounting'},
                             {   'example': 'Depreciation allocates the cost '
                                            'of assets over their useful life.',
                                 'ipa': '/dɪˌpriː.ʃiˈeɪ.ʃən/',
                                 'meaning': 'khấu hao tài sản',
                                 'word': 'depreciation'}]},
    'health': {   'B1': [   {   'example': 'Cardiovascular exercise '
                                           'strengthens the heart and improves '
                                           'circulation.',
                                'ipa': '/ˌkɑː.di.əʊˈvæs.kjʊ.lər/',
                                'meaning': 'tim mạch',
                                'word': 'cardiovascular'},
                            {   'example': 'Regular exercise boosts your '
                                           'metabolism and helps burn more '
                                           'calories.',
                                'ipa': '/məˈtæb.ə.lɪ.zəm/',
                                'meaning': 'trao đổi chất',
                                'word': 'metabolism'},
                            {   'example': 'Diabetes and hypertension are '
                                           'common chronic diseases.',
                                'ipa': '/ˈkrɒn.ɪk dɪˈziːz/',
                                'meaning': 'bệnh mãn tính',
                                'word': 'chronic disease'},
                            {   'example': 'An early diagnosis increases the '
                                           'chances of successful treatment.',
                                'ipa': '/ˌdaɪ.əɡˈnəʊ.sɪs/',
                                'meaning': 'chẩn đoán',
                                'word': 'diagnosis'},
                            {   'example': 'Preventive care like regular '
                                           'checkups helps catch diseases '
                                           'early.',
                                'ipa': '/prɪˈven.tɪv keər/',
                                'meaning': 'chăm sóc phòng ngừa',
                                'word': 'preventive care'},
                            {   'example': 'The doctor gave a positive '
                                           "prognosis for the patient's "
                                           'recovery.',
                                'ipa': '/prɒɡˈnəʊ.sɪs/',
                                'meaning': 'tiên lượng bệnh',
                                'word': 'prognosis'},
                            {   'example': 'He underwent six months of '
                                           'rehabilitation after the stroke.',
                                'ipa': '/ˌriː.ə.bɪl.ɪˈteɪ.ʃən/',
                                'meaning': 'phục hồi chức năng',
                                'word': 'rehabilitation'},
                            {   'example': 'Chronic pain can significantly '
                                           "impact a person's quality of life.",
                                'ipa': '/ˈkrɒn.ɪk peɪn/',
                                'meaning': 'đau mãn tính',
                                'word': 'chronic pain'},
                            {   'example': "The body's inflammatory response "
                                           'helps fight infection.',
                                'ipa': '/ɪnˈflæm.ə.tɔːr.i rɪˈspɒns/',
                                'meaning': 'phản ứng viêm',
                                'word': 'inflammatory response'},
                            {   'example': 'Rheumatoid arthritis is an '
                                           'autoimmune disease that affects '
                                           'the joints.',
                                'ipa': '/ˌɔː.tə.ɪˈmjuːn dɪˈziːz/',
                                'meaning': 'bệnh tự miễn',
                                'word': 'autoimmune disease'},
                            {   'example': 'Hormones control many functions in '
                                           'the body, including growth and '
                                           'mood.',
                                'ipa': '/ˈhɔː.məʊn/',
                                'meaning': 'hooc-môn',
                                'word': 'hormone'},
                            {   'example': 'High cholesterol increases the '
                                           'risk of heart disease.',
                                'ipa': '/kəˈles.tər.ɒl/',
                                'meaning': 'cholesterol',
                                'word': 'cholesterol'},
                            {   'example': 'Obesity management involves diet, '
                                           'exercise, and behavioral changes.',
                                'ipa': '/əʊˈbiː.sɪ.ti ˈmæn.ɪdʒ.mənt/',
                                'meaning': 'quản lý béo phì',
                                'word': 'obesity management'},
                            {   'example': 'Mental wellness includes '
                                           'emotional, psychological, and '
                                           'social well-being.',
                                'ipa': '/ˈmen.təl ˈwel.nəs/',
                                'meaning': 'sức khỏe tinh thần tổng thể',
                                'word': 'mental wellness'},
                            {   'example': 'Practicing mindfulness meditation '
                                           'reduces stress and anxiety.',
                                'ipa': '/ˈmaɪnd.fəl.nəs/',
                                'meaning': 'chánh niệm',
                                'word': 'mindfulness'},
                            {   'example': 'She suffered from insomnia and was '
                                           'unable to sleep for more than 4 '
                                           'hours.',
                                'ipa': '/ɪnˈsɒm.ni.ə/',
                                'meaning': 'chứng mất ngủ',
                                'word': 'insomnia'},
                            {   'example': 'The new drug is currently '
                                           'undergoing clinical trials.',
                                'ipa': '/ˈklɪn.ɪ.kəl ˈtraɪ.əl/',
                                'meaning': 'thử nghiệm lâm sàng',
                                'word': 'clinical trial'},
                            {   'example': 'In the clinical trial, one group '
                                           'received the drug and the other '
                                           'received a placebo.',
                                'ipa': '/pləˈsiː.bəʊ/',
                                'meaning': 'thuốc giả (đối chứng)',
                                'word': 'placebo'},
                            {   'example': 'The doctor ordered a blood test to '
                                           'check for diabetes.',
                                'ipa': '/blʌd test/',
                                'meaning': 'xét nghiệm máu',
                                'word': 'blood test'},
                            {   'example': 'A biopsy was taken to check if the '
                                           'tumor was malignant.',
                                'ipa': '/ˈbaɪ.ɒp.si/',
                                'meaning': 'sinh thiết',
                                'word': 'biopsy'},
                            {   'example': 'She is seeing an oncologist for '
                                           'her breast cancer treatment.',
                                'ipa': '/ɒŋˈkɒl.ə.dʒi/',
                                'meaning': 'ung thư học',
                                'word': 'oncology'},
                            {   'example': 'She underwent several rounds of '
                                           'chemotherapy to fight the cancer.',
                                'ipa': '/ˌkiː.məʊˈθer.ə.pi/',
                                'meaning': 'hóa trị',
                                'word': 'chemotherapy'},
                            {   'example': 'Radiation therapy targets cancer '
                                           'cells to destroy them.',
                                'ipa': '/ˌreɪ.diˈeɪ.ʃən ˈθer.ə.pi/',
                                'meaning': 'xạ trị',
                                'word': 'radiation therapy'},
                            {   'example': "Immunotherapy uses the body's "
                                           'immune system to fight cancer.',
                                'ipa': '/ˌɪm.jʊ.nəʊˈθer.ə.pi/',
                                'meaning': 'liệu pháp miễn dịch',
                                'word': 'immunotherapy'},
                            {   'example': 'Epidemiology studies the patterns '
                                           'and causes of disease in '
                                           'populations.',
                                'ipa': '/ˌep.ɪ.diː.miˈɒl.ə.dʒi/',
                                'meaning': 'dịch tễ học',
                                'word': 'epidemiology'},
                            {   'example': 'The COVID-19 pandemic affected '
                                           'every country in the world.',
                                'ipa': '/pænˈdem.ɪk/',
                                'meaning': 'đại dịch',
                                'word': 'pandemic'},
                            {   'example': 'Malaria is endemic in many '
                                           'tropical regions.',
                                'ipa': '/enˈdem.ɪk/',
                                'meaning': 'bệnh đặc hữu (địa phương)',
                                'word': 'endemic'},
                            {   'example': 'Herd immunity protects vulnerable '
                                           'people who cannot be vaccinated.',
                                'ipa': '/hɜːd ɪˈmjuː.nɪ.ti/',
                                'meaning': 'miễn dịch cộng đồng',
                                'word': 'herd immunity'},
                            {   'example': 'Public health campaigns educate '
                                           'communities about disease '
                                           'prevention.',
                                'ipa': '/ˈpʌb.lɪk helθ/',
                                'meaning': 'y tế công cộng',
                                'word': 'public health'},
                            {   'example': 'A strong healthcare system is '
                                           'essential for national '
                                           'development.',
                                'ipa': '/ˈhelθ.keər ˈsɪs.təm/',
                                'meaning': 'hệ thống y tế',
                                'word': 'healthcare system'},
                            {   'example': 'Primary care doctors are the first '
                                           'point of contact for health '
                                           'concerns.',
                                'ipa': '/ˈpraɪ.mər.i keər/',
                                'meaning': 'chăm sóc y tế ban đầu',
                                'word': 'primary care'},
                            {   'example': 'He was referred to a cardiologist, '
                                           'a specialist in heart conditions.',
                                'ipa': '/ˈspeʃ.ə.lɪst/',
                                'meaning': 'bác sĩ chuyên khoa',
                                'word': 'specialist'},
                            {   'example': 'She had the procedure done as an '
                                           'outpatient and went home the same '
                                           'day.',
                                'ipa': '/ˈaʊt.peɪ.ʃənt/',
                                'meaning': 'bệnh nhân ngoại trú',
                                'word': 'outpatient'},
                            {   'example': 'He was admitted as an inpatient '
                                           'for observation after the '
                                           'accident.',
                                'ipa': '/ˈɪn.peɪ.ʃənt/',
                                'meaning': 'bệnh nhân nội trú',
                                'word': 'inpatient'},
                            {   'example': 'Telemedicine allows patients to '
                                           'consult doctors via video call.',
                                'ipa': '/ˈtel.ɪˌmed.ɪ.sɪn/',
                                'meaning': 'y tế từ xa',
                                'word': 'telemedicine'},
                            {   'example': 'Health insurance covers the cost '
                                           'of most medical treatments.',
                                'ipa': '/helθ ɪnˈʃʊər.əns/',
                                'meaning': 'bảo hiểm y tế',
                                'word': 'health insurance'},
                            {   'example': 'Palliative care focuses on '
                                           'relieving pain and improving '
                                           'quality of life.',
                                'ipa': '/ˈpæl.i.ə.tɪv keər/',
                                'meaning': 'chăm sóc giảm nhẹ',
                                'word': 'palliative care'},
                            {   'example': 'Organ donation can save the lives '
                                           'of many people on transplant '
                                           'waiting lists.',
                                'ipa': '/ˈɔː.ɡən dəʊˈneɪ.ʃən/',
                                'meaning': 'hiến tạng',
                                'word': 'organ donation'},
                            {   'example': 'She received a kidney transplant '
                                           'after years of dialysis.',
                                'ipa': '/ˈtræns.plɑːnt/',
                                'meaning': 'cấy ghép nội tạng',
                                'word': 'transplant'},
                            {   'example': 'Dialysis cleans the blood of '
                                           'patients with kidney failure.',
                                'ipa': '/daɪˈæl.ɪ.sɪs/',
                                'meaning': 'lọc máu nhân tạo',
                                'word': 'dialysis'},
                            {   'example': 'She spent her final weeks in a '
                                           'hospice surrounded by family.',
                                'ipa': '/ˈhɒs.pɪs/',
                                'meaning': 'cơ sở chăm sóc người hấp hối',
                                'word': 'hospice'},
                            {   'example': 'Genetic testing can reveal '
                                           'predispositions to certain '
                                           'diseases.',
                                'ipa': '/dʒɪˈnet.ɪk ˈtes.tɪŋ/',
                                'meaning': 'xét nghiệm di truyền',
                                'word': 'genetic testing'},
                            {   'example': 'Elevated biomarkers in the blood '
                                           'can indicate heart damage.',
                                'ipa': '/ˈbaɪ.əʊˌmɑː.kər/',
                                'meaning': 'dấu ấn sinh học',
                                'word': 'biomarker'},
                            {   'example': 'The national vaccination program '
                                           'aims to eliminate measles.',
                                'ipa': '/ˌvæk.sɪˈneɪ.ʃən ˈprəʊ.ɡræm/',
                                'meaning': 'chương trình tiêm chủng',
                                'word': 'vaccination program'},
                            {   'example': 'Cancer screening programs detect '
                                           'disease in its early stages.',
                                'ipa': '/ˈskriː.nɪŋ ˈprəʊ.ɡræm/',
                                'meaning': 'chương trình sàng lọc bệnh',
                                'word': 'screening program'},
                            {   'example': 'Smoking is a major risk factor for '
                                           'lung cancer.',
                                'ipa': '/rɪsk ˈfæk.tər/',
                                'meaning': 'yếu tố nguy cơ',
                                'word': 'risk factor'},
                            {   'example': 'Uncontrolled diabetes can lead to '
                                           'serious complications.',
                                'ipa': '/ˌkɒm.plɪˈkeɪ.ʃən/',
                                'meaning': 'biến chứng',
                                'word': 'complication'},
                            {   'example': 'After treatment, the cancer went '
                                           'into full remission.',
                                'ipa': '/rɪˈmɪʃ.ən/',
                                'meaning': 'giai đoạn lui bệnh',
                                'word': 'remission'},
                            {   'example': 'She suffered a relapse of '
                                           'depression after stopping '
                                           'medication.',
                                'ipa': '/rɪˈlæps/',
                                'meaning': 'tái phát bệnh',
                                'word': 'relapse'},
                            {   'example': 'Nausea is a common side effect of '
                                           'this medication.',
                                'ipa': '/saɪd ɪˈfekt/',
                                'meaning': 'tác dụng phụ',
                                'word': 'side effect'}]},
    'interview': {   'A1': [   {   'example': 'Please tell me your name and '
                                              'where you are from.',
                                   'ipa': '/neɪm/',
                                   'meaning': 'tên',
                                   'word': 'name'},
                               {   'example': 'I am looking for a job as a '
                                              'teacher.',
                                   'ipa': '/ʤɑb/',
                                   'meaning': 'công việc',
                                   'word': 'job'},
                               {   'example': 'She works at a hospital as a '
                                              'nurse.',
                                   'ipa': '/wɜːk/',
                                   'meaning': 'làm việc',
                                   'word': 'work'},
                               {   'example': 'Hello! My name is Minh and I am '
                                              'applying for this position.',
                                   'ipa': '/həˈləʊ/',
                                   'meaning': 'xin chào',
                                   'word': 'hello'},
                               {   'example': 'Please sit down and make '
                                              'yourself comfortable.',
                                   'ipa': '/pliːz/',
                                   'meaning': 'làm ơn',
                                   'word': 'please'},
                               {   'example': 'Thank you for giving me this '
                                              'opportunity to interview.',
                                   'ipa': '/ˈθæŋk juː/',
                                   'meaning': 'cảm ơn',
                                   'word': 'thank you'},
                               {   'example': 'Yes, I have experience working '
                                              'in customer service.',
                                   'ipa': '/jes/',
                                   'meaning': 'có, vâng',
                                   'word': 'yes'},
                               {   'example': 'No, I have not worked in this '
                                              'field before, but I am eager to '
                                              'learn.',
                                   'ipa': '/nəʊ/',
                                   'meaning': 'không',
                                   'word': 'no'},
                               {   'example': 'I graduated from school three '
                                              'years ago.',
                                   'ipa': '/skuːl/',
                                   'meaning': 'trường học',
                                   'word': 'school'},
                               {   'example': 'I study English every day to '
                                              'improve my skills.',
                                   'ipa': '/ˈstʌd.i/',
                                   'meaning': 'học',
                                   'word': 'study'},
                               {   'example': 'I am eager to learn new things '
                                              'in this position.',
                                   'ipa': '/lɜːn/',
                                   'meaning': 'học hỏi',
                                   'word': 'learn'},
                               {   'example': 'I can speak English and '
                                              'Vietnamese fluently.',
                                   'ipa': '/spiːk/',
                                   'meaning': 'nói',
                                   'word': 'speak'},
                               {   'example': 'I read a lot to improve my '
                                              'professional knowledge.',
                                   'ipa': '/riːd/',
                                   'meaning': 'đọc',
                                   'word': 'read'},
                               {   'example': 'I can write clear reports and '
                                              'emails in English.',
                                   'ipa': '/raɪt/',
                                   'meaning': 'viết',
                                   'word': 'write'},
                               {   'example': 'I enjoy helping customers solve '
                                              'their problems.',
                                   'ipa': '/help/',
                                   'meaning': 'giúp đỡ',
                                   'word': 'help'},
                               {   'example': 'I like working with people and '
                                              'solving problems.',
                                   'ipa': '/laɪk/',
                                   'meaning': 'thích',
                                   'word': 'like'},
                               {   'example': 'I enjoy working as part of a '
                                              'team.',
                                   'ipa': '/tiːm/',
                                   'meaning': 'đội nhóm',
                                   'word': 'team'},
                               {   'example': 'I have experience working in an '
                                              'office environment.',
                                   'ipa': '/ˈɒf.ɪs/',
                                   'meaning': 'văn phòng',
                                   'word': 'office'},
                               {   'example': 'I use a computer every day for '
                                              'my work.',
                                   'ipa': '/kəmˈpjuː.tər/',
                                   'meaning': 'máy tính',
                                   'word': 'computer'},
                               {   'example': 'I am comfortable communicating '
                                              'by phone with customers.',
                                   'ipa': '/fəʊn/',
                                   'meaning': 'điện thoại',
                                   'word': 'phone'},
                               {   'example': 'I respond to emails quickly and '
                                              'professionally.',
                                   'ipa': '/ˈiː.meɪl/',
                                   'meaning': 'email',
                                   'word': 'email'},
                               {   'example': 'I attend team meetings every '
                                              'Monday morning.',
                                   'ipa': '/ˈmiː.tɪŋ/',
                                   'meaning': 'cuộc họp',
                                   'word': 'meeting'},
                               {   'example': 'Do you have any questions for '
                                              'me?',
                                   'ipa': '/ˈkwes.tʃən/',
                                   'meaning': 'câu hỏi',
                                   'word': 'question'},
                               {   'example': 'I will try to answer your '
                                              'questions honestly.',
                                   'ipa': '/ˈɑːn.sər/',
                                   'meaning': 'câu trả lời',
                                   'word': 'answer'},
                               {   'example': 'My expected salary is around 15 '
                                              'million VND per month.',
                                   'ipa': '/ˈsæl.ər.i/',
                                   'meaning': 'lương',
                                   'word': 'salary'},
                               {   'example': 'I am available to work '
                                              'full-time, 40 hours a week.',
                                   'ipa': '/aʊər/',
                                   'meaning': 'giờ làm việc',
                                   'word': 'hour'},
                               {   'example': 'I have two years of experience '
                                              'in customer service.',
                                   'ipa': '/ɪkˈspɪər.i.əns/',
                                   'meaning': 'kinh nghiệm',
                                   'word': 'experience'},
                               {   'example': 'I have strong communication and '
                                              'teamwork skills.',
                                   'ipa': '/skɪl/',
                                   'meaning': 'kỹ năng',
                                   'word': 'skill'},
                               {   'example': 'My strongest skill is my '
                                              'ability to work under pressure.',
                                   'ipa': '/strɒŋ/',
                                   'meaning': 'mạnh mẽ; nổi bật',
                                   'word': 'strong'},
                               {   'example': 'I can start the job as soon as '
                                              'next week.',
                                   'ipa': '/stɑːt/',
                                   'meaning': 'bắt đầu',
                                   'word': 'start'},
                               {   'example': 'I always finish my work before '
                                              'the deadline.',
                                   'ipa': '/ˈfɪn.ɪʃ/',
                                   'meaning': 'kết thúc; hoàn thành',
                                   'word': 'finish'},
                               {   'example': 'I am good at organizing tasks '
                                              'and managing my time.',
                                   'ipa': '/ɡʊd/',
                                   'meaning': 'tốt, giỏi',
                                   'word': 'good'},
                               {   'example': 'I enjoy finding creative '
                                              'solutions to difficult '
                                              'problems.',
                                   'ipa': '/ˈprɒb.ləm/',
                                   'meaning': 'vấn đề',
                                   'word': 'problem'},
                               {   'example': 'I get along well with friends '
                                              'and coworkers.',
                                   'ipa': '/frend/',
                                   'meaning': 'đồng nghiệp; bạn bè',
                                   'word': 'friend'},
                               {   'example': 'I am happy to take on new '
                                              'responsibilities.',
                                   'ipa': '/ˈhæp.i/',
                                   'meaning': 'vui vẻ; hài lòng',
                                   'word': 'happy'},
                               {   'example': 'My goal is to grow '
                                              'professionally within this '
                                              'company.',
                                   'ipa': '/ɡəʊl/',
                                   'meaning': 'mục tiêu',
                                   'word': 'goal'},
                               {   'example': 'In the future, I hope to become '
                                              'a team leader.',
                                   'ipa': '/ˈfjuː.tʃər/',
                                   'meaning': 'tương lai',
                                   'word': 'future'},
                               {   'example': 'I manage my time well and '
                                              'always meet deadlines.',
                                   'ipa': '/taɪm/',
                                   'meaning': 'thời gian',
                                   'word': 'time'},
                               {   'example': 'I work five days a week from '
                                              'Monday to Friday.',
                                   'ipa': '/deɪ/',
                                   'meaning': 'ngày (làm việc)',
                                   'word': 'day'},
                               {   'example': 'I am willing to relocate to '
                                              'another city for the right '
                                              'opportunity.',
                                   'ipa': '/ˈsɪt.i/',
                                   'meaning': 'thành phố',
                                   'word': 'city'},
                               {   'example': 'I love to travel to new '
                                              'countries.',
                                   'ipa': '/ˈtræv.əl/',
                                   'meaning': 'Đi du lịch, di chuyển',
                                   'word': 'travel'},
                               {   'example': 'I speak English and Vietnamese '
                                              'as working languages.',
                                   'ipa': '/ˈlæŋ.ɡwɪdʒ/',
                                   'meaning': 'ngôn ngữ',
                                   'word': 'language'},
                               {   'example': 'I graduated from the National '
                                              'University last year.',
                                   'ipa': '/ˌjuː.nɪˈvɜː.sɪ.ti/',
                                   'meaning': 'trường đại học',
                                   'word': 'university'},
                               {   'example': "I have a bachelor's degree in "
                                              'Business Administration.',
                                   'ipa': '/dɪˈɡriː/',
                                   'meaning': 'bằng cấp',
                                   'word': 'degree'},
                               {   'example': 'This is my first interview for '
                                              'a full-time position.',
                                   'ipa': '/ˈɪn.tə.vjuː/',
                                   'meaning': 'phỏng vấn',
                                   'word': 'interview'},
                               {   'example': 'I researched your company '
                                              'before attending this '
                                              'interview.',
                                   'ipa': '/ˈkʌm.pə.ni/',
                                   'meaning': 'công ty',
                                   'word': 'company'},
                               {   'example': 'I am applying for the marketing '
                                              'assistant position.',
                                   'ipa': '/pəˈzɪʃ.ən/',
                                   'meaning': 'vị trí công việc',
                                   'word': 'position'},
                               {   'example': 'I applied for this job because '
                                              "I believe in your company's "
                                              'mission.',
                                   'ipa': '/əˈplaɪ/',
                                   'meaning': 'ứng tuyển',
                                   'word': 'apply'},
                               {   'example': 'I brought a printed copy of my '
                                              'resume to the interview.',
                                   'ipa': '/ˈrez.jʊ.meɪ/',
                                   'meaning': 'CV, sơ yếu lý lịch',
                                   'word': 'resume'},
                               {   'example': 'Please allow me to introduce '
                                              'myself to the panel.',
                                   'ipa': '/ˌɪn.trəˈdjuːs/',
                                   'meaning': 'giới thiệu bản thân',
                                   'word': 'introduce'}],
                     'B1': [   {   'example': 'The interviewer assessed my '
                                              'competency in data analysis.',
                                   'ipa': '/ˈkɒm.pɪ.tən.si/',
                                   'meaning': 'năng lực cốt lõi',
                                   'word': 'competency'},
                               {   'example': 'A behavioral interview asks you '
                                              'to describe past experiences.',
                                   'ipa': '/bɪˈheɪ.vjər.əl ˈɪn.tə.vjuː/',
                                   'meaning': 'phỏng vấn hành vi',
                                   'word': 'behavioral interview'},
                               {   'example': 'Use the STAR method to '
                                              'structure your answers: '
                                              'Situation, Task, Action, '
                                              'Result.',
                                   'ipa': '/stɑːr ˈmeθ.əd/',
                                   'meaning': 'phương pháp STAR trả lời phỏng '
                                              'vấn',
                                   'word': 'STAR method'},
                               {   'example': 'My transferable skills from '
                                              'retail include customer service '
                                              'and time management.',
                                   'ipa': '/trænsˈfɜː.rə.bəl skɪlz/',
                                   'meaning': 'kỹ năng chuyển đổi được',
                                   'word': 'transferable skills'},
                               {   'example': 'Be clear about your value '
                                              "proposition when answering 'Why "
                                              "should we hire you?'",
                                   'ipa': '/ˈvæl.juː ˌprɒp.əˈzɪʃ.ən/',
                                   'meaning': 'giá trị bản thân mang lại',
                                   'word': 'value proposition'},
                               {   'example': 'Prepare a 60-second elevator '
                                              'pitch about yourself for the '
                                              'interview.',
                                   'ipa': '/ˈel.ɪ.veɪ.tər pɪtʃ/',
                                   'meaning': 'bài giới thiệu bản thân ngắn '
                                              'gọn',
                                   'word': 'elevator pitch'},
                               {   'example': 'The interviewer asked about my '
                                              'career trajectory over the next '
                                              'five years.',
                                   'ipa': '/kəˈrɪər trəˈdʒek.tər.i/',
                                   'meaning': 'lộ trình sự nghiệp',
                                   'word': 'career trajectory'},
                               {   'example': 'I used my gap year to volunteer '
                                              'abroad and develop new skills.',
                                   'ipa': '/ɡæp jɪər/',
                                   'meaning': 'năm nghỉ giữa công việc/học tập',
                                   'word': 'gap year'},
                               {   'example': 'A well-written cover letter '
                                              'sets you apart from other '
                                              'candidates.',
                                   'ipa': '/ˈkʌv.ər ˌlet.ər/',
                                   'meaning': 'thư xin việc',
                                   'word': 'cover letter'},
                               {   'example': 'I matched my skills carefully '
                                              'to the job description before '
                                              'applying.',
                                   'ipa': '/dʒɒb dɪˈskrɪp.ʃən/',
                                   'meaning': 'mô tả công việc',
                                   'word': 'job description'},
                               {   'example': 'I exceeded my key performance '
                                              'indicators by 15% last quarter.',
                                   'ipa': '/kiː pəˈfɔː.məns ˈɪn.dɪ.keɪ.tərz/',
                                   'meaning': 'chỉ số hiệu suất chính',
                                   'word': 'key performance indicators'},
                               {   'example': 'Employers value soft skills '
                                              'like communication and '
                                              'emotional intelligence.',
                                   'ipa': '/sɒft skɪlz/',
                                   'meaning': 'kỹ năng mềm',
                                   'word': 'soft skills'},
                               {   'example': 'My hard skills include Python '
                                              'programming and data analysis.',
                                   'ipa': '/hɑːd skɪlz/',
                                   'meaning': 'kỹ năng cứng',
                                   'word': 'hard skills'},
                               {   'example': 'Networking helped me find out '
                                              'about this job opening.',
                                   'ipa': '/ˈnet.wɜː.kɪŋ/',
                                   'meaning': 'xây dựng mạng lưới quan hệ',
                                   'word': 'networking'},
                               {   'example': 'A headhunter contacted me about '
                                              'an exciting opportunity.',
                                   'ipa': '/ˈhed.hʌn.tər/',
                                   'meaning': 'chuyên viên tuyển dụng đầu '
                                              'ngành',
                                   'word': 'headhunter'},
                               {   'example': 'The recruiter explained the '
                                              'role and salary range in '
                                              'detail.',
                                   'ipa': '/rɪˈkruː.tər/',
                                   'meaning': 'người tuyển dụng',
                                   'word': 'recruiter'},
                               {   'example': 'A panel interview involves '
                                              'multiple interviewers asking '
                                              'questions simultaneously.',
                                   'ipa': '/ˈpæn.əl ˈɪn.tə.vjuː/',
                                   'meaning': 'phỏng vấn hội đồng',
                                   'word': 'panel interview'},
                               {   'example': 'Send a follow-up email within '
                                              '24 hours of the interview.',
                                   'ipa': '/ˈfɒl.əʊ.ʌp ˈiː.meɪl/',
                                   'meaning': 'email theo dõi sau phỏng vấn',
                                   'word': 'follow-up email'},
                               {   'example': 'A rejection is an opportunity '
                                              'to learn and improve for the '
                                              'next interview.',
                                   'ipa': '/rɪˈdʒek.ʃən/',
                                   'meaning': 'bị từ chối (tuyển dụng)',
                                   'word': 'rejection'},
                               {   'example': 'She received an offer letter '
                                              'with a competitive salary '
                                              'package.',
                                   'ipa': '/ˈɒf.ər ˌlet.ər/',
                                   'meaning': 'thư mời nhận việc',
                                   'word': 'offer letter'},
                               {   'example': 'The probation period lasts '
                                              'three months before you become '
                                              'a permanent employee.',
                                   'ipa': '/prəˈbeɪ.ʃən ˌpɪər.i.əd/',
                                   'meaning': 'thời gian thử việc',
                                   'word': 'probation period'},
                               {   'example': 'The onboarding process includes '
                                              'orientation, training, and team '
                                              'introductions.',
                                   'ipa': '/ˈɒn.bɔː.dɪŋ/',
                                   'meaning': 'quy trình tiếp nhận nhân viên '
                                              'mới',
                                   'word': 'onboarding'},
                               {   'example': "Don't be afraid to engage in "
                                              'salary negotiation when you '
                                              'receive an offer.',
                                   'ipa': '/ˈsæl.ər.i nɪˌɡəʊ.ʃiˈeɪ.ʃən/',
                                   'meaning': 'đàm phán lương',
                                   'word': 'salary negotiation'},
                               {   'example': 'My current notice period is one '
                                              'month.',
                                   'ipa': '/ˈnəʊ.tɪs ˌpɪər.i.əd/',
                                   'meaning': 'thời gian báo trước khi nghỉ '
                                              'việc',
                                   'word': 'notice period'},
                               {   'example': 'Good body language includes eye '
                                              'contact, a firm handshake, and '
                                              'upright posture.',
                                   'ipa': '/ˈbɒd.i ˌlæŋ.ɡwɪdʒ/',
                                   'meaning': 'ngôn ngữ cơ thể',
                                   'word': 'body language'},
                               {   'example': 'Maintaining eye contact shows '
                                              'confidence and engagement.',
                                   'ipa': '/aɪ ˈkɒn.tækt/',
                                   'meaning': 'giao tiếp bằng mắt',
                                   'word': 'eye contact'},
                               {   'example': 'Active listening involves '
                                              'nodding, paraphrasing, and '
                                              'asking clarifying questions.',
                                   'ipa': '/ˈæk.tɪv ˈlɪs.ən.ɪŋ/',
                                   'meaning': 'lắng nghe chủ động',
                                   'word': 'active listening'},
                               {   'example': 'A structured interview uses the '
                                              'same set of questions for all '
                                              'candidates.',
                                   'ipa': '/ˈstrʌk.tʃərd ˈɪn.tə.vjuː/',
                                   'meaning': 'phỏng vấn có cấu trúc',
                                   'word': 'structured interview'},
                               {   'example': 'An unstructured interview is '
                                              'more like a natural '
                                              'conversation.',
                                   'ipa': '/ˈʌnˌstrʌk.tʃərd ˈɪn.tə.vjuː/',
                                   'meaning': 'phỏng vấn không có cấu trúc',
                                   'word': 'unstructured interview'},
                               {   'example': 'Management consulting firms '
                                              'often use case interviews to '
                                              'assess analytical skills.',
                                   'ipa': '/keɪs ˈɪn.tə.vjuː/',
                                   'meaning': 'phỏng vấn tình huống',
                                   'word': 'case interview'},
                               {   'example': 'I practiced coding problems to '
                                              'prepare for the technical '
                                              'interview.',
                                   'ipa': '/ˈtek.nɪ.kəl ˈɪn.tə.vjuː/',
                                   'meaning': 'phỏng vấn kỹ thuật',
                                   'word': 'technical interview'},
                               {   'example': 'The aptitude test measured my '
                                              'verbal and numerical reasoning '
                                              'skills.',
                                   'ipa': '/ˈæp.tɪ.tjuːd test/',
                                   'meaning': 'bài kiểm tra năng khiếu',
                                   'word': 'aptitude test'},
                               {   'example': 'Many employers use psychometric '
                                              'tests to assess personality and '
                                              'cognitive ability.',
                                   'ipa': '/ˌsaɪ.kəˈmet.rɪk test/',
                                   'meaning': 'bài kiểm tra tâm lý',
                                   'word': 'psychometric test'},
                               {   'example': 'The group discussion assessed '
                                              'our teamwork and leadership '
                                              'skills.',
                                   'ipa': '/ɡruːp dɪˈskʌʃ.ən/',
                                   'meaning': 'thảo luận nhóm',
                                   'word': 'group discussion'},
                               {   'example': 'The assessment center involved '
                                              'exercises, role plays, and '
                                              'group activities.',
                                   'ipa': '/əˈses.mənt ˈsen.tər/',
                                   'meaning': 'trung tâm đánh giá ứng viên',
                                   'word': 'assessment center'},
                               {   'example': 'The role play exercise tested '
                                              'how I handle difficult customer '
                                              'situations.',
                                   'ipa': '/rəʊl pleɪ/',
                                   'meaning': 'đóng vai tình huống',
                                   'word': 'role play'},
                               {   'example': 'Strong presentation skills are '
                                              'essential for client-facing '
                                              'roles.',
                                   'ipa': '/ˌprez.ənˈteɪ.ʃən skɪlz/',
                                   'meaning': 'kỹ năng thuyết trình',
                                   'word': 'presentation skills'},
                               {   'example': 'Critical thinking is highly '
                                              'valued in problem-solving '
                                              'roles.',
                                   'ipa': '/ˈkrɪt.ɪ.kəl ˈθɪŋk.ɪŋ/',
                                   'meaning': 'tư duy phản biện',
                                   'word': 'critical thinking'},
                               {   'example': 'I use time management '
                                              'techniques to prioritize my '
                                              'daily tasks.',
                                   'ipa': '/taɪm ˈmæn.ɪdʒ.mənt/',
                                   'meaning': 'quản lý thời gian',
                                   'word': 'time management'},
                               {   'example': 'I resolved a conflict between '
                                              'two colleagues through open '
                                              'communication.',
                                   'ipa': '/ˈkɒn.flɪkt ˌrez.əˈluː.ʃən/',
                                   'meaning': 'giải quyết xung đột',
                                   'word': 'conflict resolution'},
                               {   'example': 'Emotional intelligence helps '
                                              'you manage relationships at '
                                              'work effectively.',
                                   'ipa': '/ɪˌməʊ.ʃən.əl ɪnˈtel.ɪ.dʒəns/',
                                   'meaning': 'trí tuệ cảm xúc',
                                   'word': 'emotional intelligence'},
                               {   'example': 'Interviewers assess cultural '
                                              'fit to ensure long-term '
                                              'employee satisfaction.',
                                   'ipa': '/ˈkʌl.tʃər.əl fɪt/',
                                   'meaning': 'phù hợp văn hóa công ty',
                                   'word': 'cultural fit'},
                               {   'example': 'I have a strong work ethic and '
                                              'always give my best effort.',
                                   'ipa': '/wɜːk ˈeθ.ɪk/',
                                   'meaning': 'đạo đức làm việc',
                                   'word': 'work ethic'},
                               {   'example': 'Resilience is key to bouncing '
                                              'back from setbacks and '
                                              'challenges.',
                                   'ipa': '/rɪˈzɪl.i.əns/',
                                   'meaning': 'sức bền tinh thần',
                                   'word': 'resilience'},
                               {   'example': 'I have a growth mindset and '
                                              'always look for opportunities '
                                              'to improve.',
                                   'ipa': '/ɡrəʊθ ˈmaɪnd.set/',
                                   'meaning': 'tư duy phát triển',
                                   'word': 'growth mindset'},
                               {   'example': 'Self-awareness helps me '
                                              'identify my weaknesses and work '
                                              'on them.',
                                   'ipa': '/ˌself əˈweər.nəs/',
                                   'meaning': 'tự nhận thức bản thân',
                                   'word': 'self-awareness'},
                               {   'example': 'I benefited greatly from '
                                              'mentoring by an experienced '
                                              'senior colleague.',
                                   'ipa': '/ˈmen.tər.ɪŋ/',
                                   'meaning': 'cố vấn, hướng dẫn',
                                   'word': 'mentoring'},
                               {   'example': 'I invested in upskilling by '
                                              'completing online '
                                              'certifications.',
                                   'ipa': '/ˌʌpˈskɪl.ɪŋ/',
                                   'meaning': 'nâng cao kỹ năng',
                                   'word': 'upskilling'},
                               {   'example': 'My long-term vision is to lead '
                                              'a product team in a technology '
                                              'company.',
                                   'ipa': '/lɒŋ tɜːm ˈvɪʒ.ən/',
                                   'meaning': 'tầm nhìn dài hạn',
                                   'word': 'long-term vision'},
                               {   'example': 'I researched the company values '
                                              'and they align with my own '
                                              'principles.',
                                   'ipa': '/ˈkʌm.pə.ni ˈvæl.juːz/',
                                   'meaning': 'giá trị cốt lõi công ty',
                                   'word': 'company values'}]},
    'job': {   'A1': [   {   'example': 'I work from nine to five every day.',
                             'ipa': '/wɜːk/',
                             'meaning': 'làm việc; công việc',
                             'word': 'work'},
                         {   'example': 'She got a new job at a hospital.',
                             'ipa': '/ʤɑb/',
                             'meaning': 'việc làm',
                             'word': 'job'},
                         {   'example': 'My boss is very kind and helpful.',
                             'ipa': '/bɒs/',
                             'meaning': 'sếp, ông chủ',
                             'word': 'boss'},
                         {   'example': 'He goes to the office every morning.',
                             'ipa': '/ˈɒf.ɪs/',
                             'meaning': 'văn phòng',
                             'word': 'office'},
                         {   'example': 'Our team has five members.',
                             'ipa': '/tiːm/',
                             'meaning': 'đội, nhóm',
                             'word': 'team'},
                         {   'example': "We have a meeting at ten o'clock.",
                             'ipa': '/ˈmiː.tɪŋ/',
                             'meaning': 'cuộc họp',
                             'word': 'meeting'},
                         {   'example': 'She earns good money from her job.',
                             'ipa': '/ˈmʌn.i/',
                             'meaning': 'tiền',
                             'word': 'money'},
                         {   'example': "Let's take a break and have some "
                                        'coffee.',
                             'ipa': '/breɪk/',
                             'meaning': 'giờ nghỉ',
                             'word': 'break'},
                         {   'example': 'I work from nine to five every day.',
                             'ipa': '/ˈleɪbər/',
                             'meaning': 'làm việc; công việc',
                             'word': 'labor'},
                         {   'example': 'She got a new job at a hospital.',
                             'ipa': '/ˌɑkjəˈpeɪʃən/',
                             'meaning': 'việc làm',
                             'word': 'occupation'},
                         {   'example': 'My boss is very kind and helpful.',
                             'ipa': '/ˈmænɪʤər/',
                             'meaning': 'sếp, ông chủ',
                             'word': 'manager'},
                         {   'example': 'He goes to the office every morning.',
                             'ipa': '/ˈwərkˌpleɪs/',
                             'meaning': 'văn phòng',
                             'word': 'workplace'},
                         {   'example': 'Our team has five members.',
                             'ipa': '/skwɑd/',
                             'meaning': 'đội, nhóm',
                             'word': 'squad'},
                         {   'example': "We have a meeting at ten o'clock.",
                             'ipa': '/ˈgæðərɪŋ/',
                             'meaning': 'cuộc họp',
                             'word': 'gathering'},
                         {   'example': 'She earns good money from her job.',
                             'ipa': '/kæʃ/',
                             'meaning': 'tiền',
                             'word': 'cash'},
                         {   'example': "Let's take a break and have some "
                                        'coffee.',
                             'ipa': '/pɔz/',
                             'meaning': 'giờ nghỉ',
                             'word': 'pause'},
                         {   'example': 'My colleague helped me today.',
                             'ipa': '/ˈkɒl.iːɡ/',
                             'meaning': 'đồng nghiệp cùng công ty',
                             'word': 'colleague'},
                         {   'example': 'My salary is paid monthly.',
                             'ipa': '/ˈsæl.ər.i/',
                             'meaning': 'mức lương hàng tháng',
                             'word': 'salary'},
                         {   'example': 'I have a job interview tomorrow.',
                             'ipa': '/ˈɪn.tə.vjuː/',
                             'meaning': 'buổi phỏng vấn xin việc',
                             'word': 'interview'},
                         {   'example': 'Send your resume by email.',
                             'ipa': '/ˈrɛz.jʊ.meɪ/',
                             'meaning': 'hồ sơ xin việc',
                             'word': 'resume'},
                         {   'example': 'The company will hire ten people.',
                             'ipa': '/ˈhaɪər/',
                             'meaning': 'tuyển dụng nhân viên',
                             'word': 'hire'},
                         {   'example': 'Apply for the job online.',
                             'ipa': '/əˈplaɪ/',
                             'meaning': 'nộp đơn xin việc',
                             'word': 'apply'},
                         {   'example': 'Write a report for the boss.',
                             'ipa': '/rɪˈpɔːrt/',
                             'meaning': 'báo cáo công việc',
                             'word': 'report'},
                         {   'example': 'Our project ends next week.',
                             'ipa': '/ˈprɒdʒ.ɛkt/',
                             'meaning': 'dự án đang thực hiện',
                             'word': 'project'},
                         {   'example': 'The deadline is Friday.',
                             'ipa': '/ˈdɛd.laɪn/',
                             'meaning': 'hạn chót hoàn thành',
                             'word': 'deadline'},
                         {   'example': 'Learn new skills every year.',
                             'ipa': '/skɪlz/',
                             'meaning': 'kỹ năng chuyên môn',
                             'word': 'skills'},
                         {   'example': 'I have five years of experience.',
                             'ipa': '/ɪkˈspɪər.i.əns/',
                             'meaning': 'kinh nghiệm làm việc',
                             'word': 'experience'},
                         {   'example': 'I work for a tech company.',
                             'ipa': '/ˈkʌm.pə.ni/',
                             'meaning': 'công ty đang làm việc',
                             'word': 'company'},
                         {   'example': 'She works in the marketing '
                                        'department.',
                             'ipa': '/dɪˈpɑːrt.mənt/',
                             'meaning': 'phòng ban trong công ty',
                             'word': 'department'},
                         {   'example': 'What is your current position?',
                             'ipa': '/pəˈzɪʃ.ən/',
                             'meaning': 'chức vụ công việc',
                             'word': 'position'},
                         {   'example': 'I work full-time at the bank.',
                             'ipa': '/ˌfʊlˈtaɪm/',
                             'meaning': 'toàn thời gian làm việc',
                             'word': 'full-time'},
                         {   'example': 'She works part-time at a cafe.',
                             'ipa': '/ˌpɑːrtˈtaɪm/',
                             'meaning': 'bán thời gian làm việc',
                             'word': 'part-time'},
                         {   'example': 'Sign the contract before starting.',
                             'ipa': '/ˈkɒn.trækt/',
                             'meaning': 'hợp đồng lao động',
                             'word': 'contract'},
                         {   'example': 'The job has great benefits.',
                             'ipa': '/ˈbɛn.ɪ.fɪts/',
                             'meaning': 'phúc lợi lao động',
                             'word': 'benefits'},
                         {   'example': 'I have two weeks of vacation.',
                             'ipa': '/veɪˈkeɪ.ʃən/',
                             'meaning': 'kỳ nghỉ phép năm',
                             'word': 'vacation'},
                         {   'example': 'You can take sick leave when ill.',
                             'ipa': '/sɪk liːv/',
                             'meaning': 'nghỉ ốm có phép',
                             'word': 'sick leave'},
                         {   'example': 'I work the morning shift.',
                             'ipa': '/ʃɪft/',
                             'meaning': 'ca làm việc',
                             'word': 'shift'},
                         {   'example': 'We meet online every Monday.',
                             'ipa': '/ˌɒnˈlaɪn/',
                             'meaning': 'trực tuyến trên mạng',
                             'word': 'online'},
                         {   'example': 'I eat lunch during the lunch break.',
                             'ipa': '/lʌntʃ breɪk/',
                             'meaning': 'giờ nghỉ trưa',
                             'word': 'lunch break'},
                         {   'example': 'All staff wear a uniform.',
                             'ipa': '/ˈjuː.nɪ.fɔːm/',
                             'meaning': 'đồng phục công ty',
                             'word': 'uniform'},
                         {   'example': 'Wear your badge in the office.',
                             'ipa': '/bædʒ/',
                             'meaning': 'thẻ nhân viên đeo ngực',
                             'word': 'badge'},
                         {   'example': 'Clean your desk every day.',
                             'ipa': '/dɛsk/',
                             'meaning': 'bàn làm việc văn phòng',
                             'word': 'desk'},
                         {   'example': 'My office chair is very comfortable.',
                             'ipa': '/tʃɛər/',
                             'meaning': 'ghế văn phòng ngồi làm việc',
                             'word': 'chair'},
                         {   'example': 'Check your salary slip each month.',
                             'ipa': '/ˈsæl.ər.i slɪp/',
                             'meaning': 'phiếu lương hàng tháng',
                             'word': 'salary slip'},
                         {   'example': 'Good attendance is important.',
                             'ipa': '/əˈtɛn.dəns/',
                             'meaning': 'chuyên cần đi làm đúng giờ',
                             'word': 'attendance'},
                         {   'example': 'Always be punctual at work.',
                             'ipa': '/ˈpʌŋk.tʃʊ.əl/',
                             'meaning': 'đúng giờ đúng hẹn',
                             'word': 'punctual'},
                         {   'example': 'Follow the workplace rules.',
                             'ipa': '/ˈwɜːrk.pleɪs ruːlz/',
                             'meaning': 'nội quy công ty cần tuân thủ',
                             'word': 'workplace rules'},
                         {   'example': 'The lunch hour is from 12 to 1.',
                             'ipa': '/lʌntʃ aʊər/',
                             'meaning': 'tiếng đồng hồ nghỉ trưa',
                             'word': 'lunch hour'},
                         {   'example': 'Pay day is the last Friday.',
                             'ipa': '/peɪ deɪ/',
                             'meaning': 'ngày phát lương hàng tháng',
                             'word': 'pay day'},
                         {   'example': 'Write a professional resignation '
                                        'letter.',
                             'ipa': '/ˌrɛz.ɪɡˈneɪ.ʃən ˈlɛt.ər/',
                             'meaning': 'thư xin nghỉ việc chính thức',
                             'word': 'resignation letter'}],
               'A2': [   {   'example': 'Your employer must sign the form.',
                             'ipa': '/ɪmˈplɔɪ.ər/',
                             'meaning': 'chủ sử dụng lao động',
                             'word': 'employer'},
                         {   'example': 'Every employee gets health insurance.',
                             'ipa': '/ˌɪm.plɔɪˈiː/',
                             'meaning': 'nhân viên lao động',
                             'word': 'employee'},
                         {   'example': 'The company has a large workforce.',
                             'ipa': '/ˈwɜːrk.fɔːrs/',
                             'meaning': 'lực lượng lao động',
                             'word': 'workforce'},
                         {   'example': 'Recruitment starts next month.',
                             'ipa': '/rɪˈkruːt.mənt/',
                             'meaning': 'tuyển dụng nhân sự mới',
                             'word': 'recruitment'},
                         {   'example': 'The probation period is three months.',
                             'ipa': '/prəˈbeɪ.ʃən/',
                             'meaning': 'thời gian thử việc',
                             'word': 'probation'},
                         {   'example': 'Submit your resignation letter.',
                             'ipa': '/ˌrɛz.ɪɡˈneɪ.ʃən/',
                             'meaning': 'đơn xin nghỉ việc',
                             'word': 'resignation'},
                         {   'example': 'Many workers faced layoffs.',
                             'ipa': '/ˈleɪ.ɒf/',
                             'meaning': 'sa thải do cắt giảm nhân sự',
                             'word': 'layoff'},
                         {   'example': 'She received redundancy pay.',
                             'ipa': '/rɪˈdʌn.dən.si/',
                             'meaning': 'dư thừa nhân sự bị cắt giảm',
                             'word': 'redundancy'},
                         {   'example': 'He plans retirement at 65.',
                             'ipa': '/rɪˈtaɪər.mənt/',
                             'meaning': 'về hưu sau tuổi làm việc',
                             'word': 'retirement'},
                         {   'example': 'Save for a pension early.',
                             'ipa': '/ˈpɛn.ʃən/',
                             'meaning': 'lương hưu sau nghỉ việc',
                             'word': 'pension'},
                         {   'example': 'We received a year-end bonus.',
                             'ipa': '/ˈboʊ.nəs/',
                             'meaning': 'thưởng cuối năm',
                             'word': 'bonus'},
                         {   'example': 'She asked for a raise.',
                             'ipa': '/reɪz/',
                             'meaning': 'tăng lương theo hiệu suất',
                             'word': 'raise'},
                         {   'example': 'The paycheck arrives on Friday.',
                             'ipa': '/ˈpeɪ.tʃɛk/',
                             'meaning': 'phiếu lương hàng tháng',
                             'word': 'paycheck'},
                         {   'example': 'The minimum wage increased.',
                             'ipa': '/weɪdʒ/',
                             'meaning': 'tiền công theo giờ',
                             'word': 'wage'},
                         {   'example': 'Pay income tax every year.',
                             'ipa': '/tæks/',
                             'meaning': 'thuế thu nhập cá nhân',
                             'word': 'tax'},
                         {   'example': 'Plan your career path carefully.',
                             'ipa': '/kəˈrɪər pæθ/',
                             'meaning': 'con đường sự nghiệp',
                             'word': 'career path'},
                         {   'example': 'Annual performance reviews set goals.',
                             'ipa': '/pərˈfɔːr.məns rɪˈvjuː/',
                             'meaning': 'đánh giá hiệu suất công việc',
                             'word': 'performance review'},
                         {   'example': 'Goal setting improves motivation.',
                             'ipa': '/ɡoʊl ˈsɛt.ɪŋ/',
                             'meaning': 'thiết lập mục tiêu công việc',
                             'word': 'goal setting'},
                         {   'example': 'A mentorship program helps newcomers.',
                             'ipa': '/ˈmɛn.tər.ʃɪp/',
                             'meaning': 'hướng dẫn từ người có kinh nghiệm',
                             'word': 'mentorship'},
                         {   'example': 'She did an internship at a bank.',
                             'ipa': '/ˈɪn.tɜːrn.ʃɪp/',
                             'meaning': 'thực tập tại công ty',
                             'word': 'internship'},
                         {   'example': 'Volunteer work builds experience.',
                             'ipa': '/ˌvɒl.ənˈtɪər/',
                             'meaning': 'tình nguyện viên không lương',
                             'word': 'volunteer'},
                         {   'example': 'He became self-employed last year.',
                             'ipa': '/ˌsɛlf.ɪmˈplɔɪd/',
                             'meaning': 'tự kinh doanh làm chủ',
                             'word': 'self-employed'},
                         {   'example': 'Hire a consultant for advice.',
                             'ipa': '/kənˈsʌl.tənt/',
                             'meaning': 'chuyên gia tư vấn độc lập',
                             'word': 'consultant'},
                         {   'example': 'Hybrid work offers flexibility.',
                             'ipa': '/ˈhaɪ.brɪd wɜːrk/',
                             'meaning': 'làm việc kết hợp văn phòng và nhà',
                             'word': 'hybrid work'},
                         {   'example': 'She works in the corporate sector.',
                             'ipa': '/ˈkɔːr.pər.ɪt/',
                             'meaning': 'thuộc về doanh nghiệp lớn',
                             'word': 'corporate'},
                         {   'example': 'Invest in professional development.',
                             'ipa': '/prəˈfɛʃ.ən.əl dɪˈvɛl.əp.mənt/',
                             'meaning': 'phát triển năng lực chuyên nghiệp',
                             'word': 'professional development'},
                         {   'example': 'Teamwork achieves better results.',
                             'ipa': '/ˈtiːm.wɜːrk/',
                             'meaning': 'làm việc nhóm phối hợp nhau',
                             'word': 'teamwork'},
                         {   'example': 'Leadership motivates the whole team.',
                             'ipa': '/ˈliː.dər.ʃɪp/',
                             'meaning': 'kỹ năng lãnh đạo nhóm',
                             'word': 'leadership'},
                         {   'example': 'Problem solving is a key skill.',
                             'ipa': '/ˈprɒb.ləm ˌsɒlv.ɪŋ/',
                             'meaning': 'giải quyết vấn đề sáng tạo',
                             'word': 'problem solving'},
                         {   'example': 'Good communication is essential.',
                             'ipa': '/kəˌmjuː.nɪˈkeɪ.ʃən/',
                             'meaning': 'kỹ năng giao tiếp hiệu quả',
                             'word': 'communication'},
                         {   'example': 'Adaptability is key in tech jobs.',
                             'ipa': '/əˌdæp.təˈbɪl.ɪ.ti/',
                             'meaning': 'khả năng thích nghi linh hoạt',
                             'word': 'adaptability'},
                         {   'example': 'Show initiative to stand out.',
                             'ipa': '/ɪˈnɪʃ.ə.tɪv/',
                             'meaning': 'chủ động tiên phong hành động',
                             'word': 'initiative'},
                         {   'example': 'Creativity drives innovation.',
                             'ipa': '/ˌkriː.eɪˈtɪv.ɪ.ti/',
                             'meaning': 'sáng tạo giải pháp mới mẻ',
                             'word': 'creativity'},
                         {   'example': 'Attention to detail prevents errors.',
                             'ipa': '/əˈtɛn.ʃən tʊ ˈdiː.teɪl/',
                             'meaning': 'chú ý đến từng chi tiết nhỏ',
                             'word': 'attention to detail'},
                         {   'example': 'Multitasking is needed in busy roles.',
                             'ipa': '/ˈmʌl.ti.tɑːs.kɪŋ/',
                             'meaning': 'xử lý nhiều việc cùng lúc',
                             'word': 'multitasking'},
                         {   'example': 'Attend a job fair to find work.',
                             'ipa': '/dʒɒb fɛər/',
                             'meaning': 'hội chợ việc làm tuyển dụng',
                             'word': 'job fair'},
                         {   'example': 'You made the shortlist.',
                             'ipa': '/ˈʃɔːrt.lɪst/',
                             'meaning': 'danh sách ứng viên chọn lọc',
                             'word': 'shortlist'},
                         {   'example': 'Prepare a handover document.',
                             'ipa': '/ˈhænd.oʊ.vər/',
                             'meaning': 'bàn giao công việc khi nghỉ',
                             'word': 'handover'},
                         {   'example': 'Annual appraisals set new targets.',
                             'ipa': '/əˈpreɪ.zəl/',
                             'meaning': 'đánh giá hiệu suất nhân viên',
                             'word': 'appraisal'},
                         {   'example': 'There are promotion opportunities '
                                        'here.',
                             'ipa': '/prəˈmoʊ.ʃən ˌɒp.əˈtjuː.nɪ.ti/',
                             'meaning': 'cơ hội thăng tiến sự nghiệp',
                             'word': 'promotion opportunity'},
                         {   'example': 'Work experience is highly valued.',
                             'ipa': '/wɜːrk ɪkˈspɪər.i.əns/',
                             'meaning': 'kinh nghiệm làm việc thực tế',
                             'word': 'work experience'},
                         {   'example': 'A career change needs preparation.',
                             'ipa': '/kəˈrɪər tʃeɪndʒ/',
                             'meaning': 'chuyển đổi nghề nghiệp sang lĩnh vực '
                                        'mới',
                             'word': 'career change'},
                         {   'example': 'Job security is important to many.',
                             'ipa': '/dʒɒb sɪˈkjʊər.ɪ.ti/',
                             'meaning': 'sự ổn định việc làm dài hạn',
                             'word': 'job security'},
                         {   'example': 'Work-life balance prevents burnout.',
                             'ipa': '/ˈwɜːrk laɪf ˈbæl.əns/',
                             'meaning': 'cân bằng giữa công việc và cuộc sống',
                             'word': 'work-life balance'},
                         {   'example': 'Read the employee handbook carefully.',
                             'ipa': '/ɪmˈplɔɪ.iː ˈhænd.bʊk/',
                             'meaning': 'sổ tay nhân viên nội quy công ty',
                             'word': 'employee handbook'},
                         {   'example': 'Meet your quarterly performance '
                                        'targets.',
                             'ipa': '/pərˈfɔːr.məns ˈtɑːr.ɡɪt/',
                             'meaning': 'mục tiêu hiệu suất cần đạt được',
                             'word': 'performance target'},
                         {   'example': 'You have 20 days of annual leave.',
                             'ipa': '/ˈæn.jʊ.əl liːv/',
                             'meaning': 'nghỉ phép năm được hưởng',
                             'word': 'annual leave'},
                         {   'example': 'I am on a fixed-term contract.',
                             'ipa': '/ˌfɪkst tɜːrm ˈkɒn.trækt/',
                             'meaning': 'hợp đồng có thời hạn cố định',
                             'word': 'fixed-term contract'},
                         {   'example': 'She got a permanent position.',
                             'ipa': '/ˈpɜːr.mə.nənt pəˈzɪʃ.ən/',
                             'meaning': 'vị trí làm việc lâu dài ổn định',
                             'word': 'permanent position'},
                         {   'example': 'Earn a performance bonus this '
                                        'quarter.',
                             'ipa': '/pərˈfɔːr.məns ˈboʊ.nəs/',
                             'meaning': 'thưởng dựa trên hiệu suất công việc',
                             'word': 'performance bonus'}],
               'B1': [   {   'example': 'She has built a successful career in '
                                        'finance.',
                             'ipa': '/kəˈrɪər/',
                             'meaning': 'sự nghiệp',
                             'word': 'career'},
                         {   'example': 'He received a promotion after three '
                                        'years of hard work.',
                             'ipa': '/prəˈməʊ.ʃən/',
                             'meaning': 'thăng chức',
                             'word': 'promotion'},
                         {   'example': 'As a freelancer, she can choose her '
                                        'own working hours.',
                             'ipa': '/ˈfriː.lɑːn.sər/',
                             'meaning': 'người làm tự do',
                             'word': 'freelancer'},
                         {   'example': 'Remote work has become more common '
                                        'since the pandemic.',
                             'ipa': '/rɪˌməʊt ˈwɜːk/',
                             'meaning': 'làm việc từ xa',
                             'word': 'remote work'},
                         {   'example': 'Networking events are great '
                                        'opportunities to meet industry '
                                        'professionals.',
                             'ipa': '/ˈnet.wɜː.kɪŋ/',
                             'meaning': 'xây dựng quan hệ nghề nghiệp',
                             'word': 'networking'},
                         {   'example': 'The job requires a diverse skill set '
                                        'including communication and analysis.',
                             'ipa': '/ˈskɪl set/',
                             'meaning': 'bộ kỹ năng',
                             'word': 'skill set'},
                         {   'example': 'Please provide two professional '
                                        'references with your application.',
                             'ipa': '/ˈref.ər.əns/',
                             'meaning': 'người giới thiệu, tham chiếu',
                             'word': 'reference'},
                         {   'example': 'A positive workplace environment '
                                        'improves employee satisfaction.',
                             'ipa': '/ˈwɜːk.pleɪs/',
                             'meaning': 'nơi làm việc',
                             'word': 'workplace'},
                         {   'example': 'She has built a successful career in '
                                        'finance.',
                             'ipa': '/prəˈfɛʃən/',
                             'meaning': 'sự nghiệp',
                             'word': 'profession'},
                         {   'example': 'He received a promotion after three '
                                        'years of hard work.',
                             'ipa': '/ˈmɑrkətɪŋ/',
                             'meaning': 'thăng chức',
                             'word': 'marketing'},
                         {   'example': 'As a freelancer, she can choose her '
                                        'own working hours.',
                             'ipa': '/ˌɪndɪˈpɛndənt ˈkɑnˌtræktər/',
                             'meaning': 'người làm tự do',
                             'word': 'independent contractor'},
                         {   'example': 'Remote work has become more common '
                                        'since the pandemic.',
                             'ipa': '/tɛləkəmˈjutɪŋ/',
                             'meaning': 'làm việc từ xa',
                             'word': 'telecommuting'},
                         {   'example': 'Networking events are great '
                                        'opportunities to meet industry '
                                        'professionals.',
                             'ipa': '/kəˈnɛktɪŋ/',
                             'meaning': 'xây dựng quan hệ nghề nghiệp',
                             'word': 'connecting'},
                         {   'example': 'The job requires a diverse skill set '
                                        'including communication and analysis.',
                             'ipa': '/ˌɛkspərˈtiz/',
                             'meaning': 'bộ kỹ năng',
                             'word': 'expertise'},
                         {   'example': 'Please provide two professional '
                                        'references with your application.',
                             'ipa': '/ˌrɛkəmənˈdeɪʃən/',
                             'meaning': 'người giới thiệu, tham chiếu',
                             'word': 'recommendation'},
                         {   'example': 'A positive workplace environment '
                                        'improves employee satisfaction.',
                             'ipa': '/ˈwɜːk.pleɪs/',
                             'meaning': 'nơi làm việc',
                             'word': 'workspace'},
                         {   'example': 'Read the job posting carefully.',
                             'ipa': '/dʒɒb ˈpoʊ.stɪŋ/',
                             'meaning': 'tin tuyển dụng đăng trên mạng',
                             'word': 'job posting'},
                         {   'example': 'Executive search finds top talent.',
                             'ipa': '/ɪɡˈzɛk.jʊ.tɪv sɜːrtʃ/',
                             'meaning': 'tìm kiếm lãnh đạo cấp cao',
                             'word': 'executive search'},
                         {   'example': 'Offboarding ensures knowledge '
                                        'transfer.',
                             'ipa': '/ˈɒf.bɔːr.dɪŋ/',
                             'meaning': 'quy trình tiễn nhân viên nghỉ việc',
                             'word': 'offboarding'},
                         {   'example': 'Build a talent pool for future roles.',
                             'ipa': '/ˈtæl.ənt puːl/',
                             'meaning': 'kho nhân tài dự trữ tuyển dụng',
                             'word': 'talent pool'},
                         {   'example': 'Workforce planning aligns people with '
                                        'strategy.',
                             'ipa': '/ˈwɜːrk.fɔːrs ˈplæn.ɪŋ/',
                             'meaning': 'lập kế hoạch lực lượng lao động',
                             'word': 'workforce planning'},
                         {   'example': 'Job rotation broadens experience.',
                             'ipa': '/dʒɒb roʊˈteɪ.ʃən/',
                             'meaning': 'luân chuyển công việc phát triển kỹ '
                                        'năng',
                             'word': 'job rotation'},
                         {   'example': 'A lateral move builds new skills.',
                             'ipa': '/ˈlæt.ər.əl muːv/',
                             'meaning': 'di chuyển ngang sang vị trí cùng cấp',
                             'word': 'lateral move'},
                         {   'example': 'Obtain a professional qualification.',
                             'ipa': '/prəˈfɛʃ.ən.əl ˌkwɒl.ɪ.fɪˈkeɪ.ʃən/',
                             'meaning': 'bằng cấp chứng chỉ chuyên môn',
                             'word': 'professional qualification'},
                         {   'example': 'CPD keeps skills current.',
                             'ipa': '/kənˈtɪn.jʊ.əs prəˈfɛʃ.ən.əl '
                                    'dɪˈvɛl.əp.mənt/',
                             'meaning': 'phát triển chuyên nghiệp liên tục '
                                        'không ngừng',
                             'word': 'continuous professional development'},
                         {   'example': 'Knowledge transfer prevents skill '
                                        'gaps.',
                             'ipa': '/ˈnɒl.ɪdʒ ˈtræns.fɜːr/',
                             'meaning': 'truyền đạt kiến thức cho đồng nghiệp',
                             'word': 'knowledge transfer'},
                         {   'example': 'Remote onboarding needs extra effort.',
                             'ipa': '/rɪˈmoʊt ˈɒn.bɔːr.dɪŋ/',
                             'meaning': 'hội nhập nhân viên mới từ xa online',
                             'word': 'remote onboarding'},
                         {   'example': 'Hot desking saves office space.',
                             'ipa': '/hɒt ˈdɛs.kɪŋ/',
                             'meaning': 'sắp xếp bàn làm việc chung linh hoạt',
                             'word': 'hot desking'},
                         {   'example': 'Measure productivity with clear '
                                        'metrics.',
                             'ipa': '/ˌprɒd.ʌkˈtɪv.ɪ.ti/',
                             'meaning': 'năng suất làm việc hiệu quả',
                             'word': 'productivity'},
                         {   'example': 'Improve efficiency through '
                                        'automation.',
                             'ipa': '/ɪˈfɪʃ.ən.si/',
                             'meaning': 'hiệu quả sử dụng nguồn lực',
                             'word': 'efficiency'},
                         {   'example': 'Manage your workload effectively.',
                             'ipa': '/ˈwɜːrk.loʊd/',
                             'meaning': 'khối lượng công việc cần xử lý',
                             'word': 'workload'},
                         {   'example': 'Good prioritization reduces stress.',
                             'ipa': '/praɪˌɒr.ɪ.taɪˈzeɪ.ʃən/',
                             'meaning': 'sắp xếp thứ tự ưu tiên công việc',
                             'word': 'prioritization'},
                         {   'example': 'Manage a remote team effectively.',
                             'ipa': '/rɪˈmoʊt tiːm/',
                             'meaning': 'nhóm làm việc từ xa phân tán',
                             'word': 'remote team'},
                         {   'example': 'Asynchronous work suits global teams.',
                             'ipa': '/eɪˈsɪŋ.krə.nəs wɜːrk/',
                             'meaning': 'làm việc không đồng bộ không cùng giờ',
                             'word': 'asynchronous work'},
                         {   'example': 'Meeting fatigue reduces productivity.',
                             'ipa': '/ˈmiː.tɪŋ fəˈtiːɡ/',
                             'meaning': 'mệt mỏi do họp hành quá nhiều',
                             'word': 'meeting fatigue'},
                         {   'example': 'Daily standup meetings keep teams '
                                        'aligned.',
                             'ipa': '/ˈstænd.ʌp ˈmiː.tɪŋ/',
                             'meaning': 'cuộc họp đứng nhanh hàng ngày',
                             'word': 'standup meeting'},
                         {   'example': 'Run a sprint retrospective each week.',
                             'ipa': '/ˌrɛt.rəˈspɛk.tɪv/',
                             'meaning': 'cuộc họp tổng kết rút kinh nghiệm',
                             'word': 'retrospective'},
                         {   'example': 'Schedule weekly one-on-ones.',
                             'ipa': '/wʌn ɒn wʌn/',
                             'meaning': 'cuộc họp riêng giữa quản lý và nhân '
                                        'viên',
                             'word': 'one-on-one'},
                         {   'example': 'Skip-level meetings surface hidden '
                                        'issues.',
                             'ipa': '/skɪp ˈlɛv.əl ˈmiː.tɪŋ/',
                             'meaning': 'cuộc họp bỏ qua một cấp quản lý',
                             'word': 'skip-level meeting'},
                         {   'example': 'Set stretch goals to motivate teams.',
                             'ipa': '/strɛtʃ ɡoʊl/',
                             'meaning': 'mục tiêu thách thức vươn xa hơn',
                             'word': 'stretch goal'},
                         {   'example': 'Use SMART goals for performance '
                                        'reviews.',
                             'ipa': '/smɑːrt ɡoʊl/',
                             'meaning': 'mục tiêu cụ thể đo lường được thực tế',
                             'word': 'SMART goal'},
                         {   'example': 'Define key results for each '
                                        'objective.',
                             'ipa': '/kiː rɪˈzʌlt/',
                             'meaning': 'kết quả then chốt chứng minh đạt mục '
                                        'tiêu',
                             'word': 'key result'},
                         {   'example': 'Celebrate reaching each milestone.',
                             'ipa': '/ˈmaɪl.stoʊn/',
                             'meaning': 'mốc quan trọng trong tiến độ dự án',
                             'word': 'milestone'},
                         {   'example': 'List all project deliverables '
                                        'clearly.',
                             'ipa': '/dɪˈlɪv.ər.ə.bəl/',
                             'meaning': 'sản phẩm đầu ra cần giao cho khách',
                             'word': 'deliverable'},
                         {   'example': 'Sprint planning sets goals for the '
                                        'week.',
                             'ipa': '/sprɪnt ˈplæn.ɪŋ/',
                             'meaning': 'lập kế hoạch sprint đầu chu kỳ',
                             'word': 'sprint planning'},
                         {   'example': 'Good task management boosts '
                                        'productivity.',
                             'ipa': '/tæsk ˈmæn.ɪdʒ.mənt/',
                             'meaning': 'quản lý nhiệm vụ công việc hàng ngày',
                             'word': 'task management'},
                         {   'example': 'Meet every project deadline.',
                             'ipa': '/ˈprɒdʒ.ɛkt ˈdɛd.laɪn/',
                             'meaning': 'hạn chót hoàn thành dự án',
                             'word': 'project deadline'},
                         {   'example': 'Cross-departmental projects need '
                                        'coordination.',
                             'ipa': '/ˌkrɒs dɪˈpɑːrt.mɛn.təl/',
                             'meaning': 'liên phòng ban hợp tác cùng nhau',
                             'word': 'cross-departmental'},
                         {   'example': 'Job satisfaction increases retention.',
                             'ipa': '/dʒɒb ˌsæt.ɪsˈfæk.ʃən/',
                             'meaning': 'sự hài lòng với công việc',
                             'word': 'job satisfaction'},
                         {   'example': 'Employee retention reduces hiring '
                                        'costs.',
                             'ipa': '/ɪmˈplɔɪ.iː rɪˈtɛn.ʃən/',
                             'meaning': 'giữ chân nhân viên tài năng',
                             'word': 'employee retention'}],
               'B2': [   {   'example': 'The competency framework guides '
                                        'hiring.',
                             'ipa': '/kəmˈpɛt.ən.si ˈfreɪm.wɜːrk/',
                             'meaning': 'khung năng lực đánh giá nhân sự',
                             'word': 'competency framework'},
                         {   'example': 'Succession planning prepares future '
                                        'leaders.',
                             'ipa': '/səkˈsɛʃ.ən ˈplæn.ɪŋ/',
                             'meaning': 'lập kế hoạch kế thừa nhân sự',
                             'word': 'succession planning'},
                         {   'example': 'Talent acquisition is strategic.',
                             'ipa': '/ˈtæl.ənt ˌæk.wɪˈzɪʃ.ən/',
                             'meaning': 'thu hút và tuyển dụng nhân tài',
                             'word': 'talent acquisition'},
                         {   'example': 'Employer branding attracts top '
                                        'talent.',
                             'ipa': '/ɪmˈplɔɪ.ər ˈbrænd.ɪŋ/',
                             'meaning': 'xây dựng thương hiệu nhà tuyển dụng',
                             'word': 'employer branding'},
                         {   'example': 'The EVP makes the company attractive.',
                             'ipa': '/ɪmˈplɔɪ.iː ˈvæl.juː ˌprɒp.əˈzɪʃ.ən/',
                             'meaning': 'đề xuất giá trị cho nhân viên',
                             'word': 'employee value proposition'},
                         {   'example': 'Culture drives employee engagement.',
                             'ipa': '/ˌɔːr.ɡən.aɪˈzeɪ.ʃən.əl ˈkʌl.tʃər/',
                             'meaning': 'văn hóa tổ chức doanh nghiệp',
                             'word': 'organizational culture'},
                         {   'example': 'D&I programs improve team '
                                        'performance.',
                             'ipa': '/daɪˈvɜːr.sɪ.ti ænd ɪnˈkluː.ʒən/',
                             'meaning': 'đa dạng và hòa nhập trong tổ chức',
                             'word': 'diversity and inclusion'},
                         {   'example': 'Equity ensures fair treatment.',
                             'ipa': '/ˈɛk.wɪ.ti/',
                             'meaning': 'công bằng trong đãi ngộ và cơ hội',
                             'word': 'equity'},
                         {   'example': 'Psychological safety boosts '
                                        'innovation.',
                             'ipa': '/ˌsaɪ.kəˈlɒdʒ.ɪ.kəl ˈseɪf.ti/',
                             'meaning': 'an toàn tâm lý để nói thẳng',
                             'word': 'psychological safety'},
                         {   'example': 'Intrinsic motivation drives sustained '
                                        'performance.',
                             'ipa': '/ɪnˈtrɪn.sɪk ˌmoʊ.tɪˈveɪ.ʃən/',
                             'meaning': 'động lực nội tại từ bên trong',
                             'word': 'intrinsic motivation'},
                         {   'example': 'Bonuses are a form of extrinsic '
                                        'motivation.',
                             'ipa': '/ɛkˈstrɪn.sɪk ˌmoʊ.tɪˈveɪ.ʃən/',
                             'meaning': 'động lực ngoại tại từ phần thưởng bên '
                                        'ngoài',
                             'word': 'extrinsic motivation'},
                         {   'example': 'Talent management retains top '
                                        'performers.',
                             'ipa': '/ˈtæl.ənt ˈmæn.ɪdʒ.mənt/',
                             'meaning': 'quản lý nhân tài trong tổ chức',
                             'word': 'talent management'},
                         {   'example': 'Performance management aligns goals.',
                             'ipa': '/pərˈfɔːr.məns ˈmæn.ɪdʒ.mənt/',
                             'meaning': 'quản lý hiệu suất nhân viên hệ thống',
                             'word': 'performance management'},
                         {   'example': 'OKRs align team and company goals.',
                             'ipa': '/ˌoʊ.keɪˈɑːr/',
                             'meaning': 'mục tiêu và kết quả then chốt',
                             'word': 'OKR'},
                         {   'example': '360-degree feedback gives complete '
                                        'insight.',
                             'ipa': '/ˌθriː.sɪks.ti dɪˈɡriː ˈfiːd.bæk/',
                             'meaning': 'phản hồi toàn diện từ mọi phía',
                             'word': '360-degree feedback'},
                         {   'example': 'Reskilling prepares workers for '
                                        'automation.',
                             'ipa': '/ˌriːˈskɪl.ɪŋ/',
                             'meaning': 'đào tạo lại kỹ năng hoàn toàn mới',
                             'word': 'reskilling'},
                         {   'example': 'Invest in L&D for better retention.',
                             'ipa': '/ˈlɜːr.nɪŋ ænd dɪˈvɛl.əp.mənt/',
                             'meaning': 'học tập và phát triển nghề nghiệp',
                             'word': 'learning and development'},
                         {   'example': 'High engagement reduces turnover.',
                             'ipa': '/ɪmˈplɔɪ.iː ɪnˈɡeɪdʒ.mənt/',
                             'meaning': 'sự gắn kết nhiệt tình của nhân viên',
                             'word': 'employee engagement'},
                         {   'example': 'High attrition costs the company.',
                             'ipa': '/əˈtrɪʃ.ən reɪt/',
                             'meaning': 'tỷ lệ nghỉ việc tự nhiên của nhân '
                                        'viên',
                             'word': 'attrition rate'},
                         {   'example': 'The headcount will grow by 20%.',
                             'ipa': '/ˈhɛd.kaʊnt/',
                             'meaning': 'số lượng nhân sự trong tổ chức',
                             'word': 'headcount'},
                         {   'example': 'The C-suite approved the strategy.',
                             'ipa': '/ˈsiː.swiːt/',
                             'meaning': 'nhóm lãnh đạo cấp cao nhất',
                             'word': 'C-suite'},
                         {   'example': 'Cross-functional teams solve complex '
                                        'problems.',
                             'ipa': '/ˌkrɒs ˈfʌŋk.ʃən.əl/',
                             'meaning': 'liên phòng ban phối hợp cùng nhau',
                             'word': 'cross-functional'},
                         {   'example': 'Matrix organizations share resources.',
                             'ipa': '/ˈmeɪ.trɪks ˌɔːr.ɡən.aɪˈzeɪ.ʃən/',
                             'meaning': 'tổ chức ma trận hai tuyến báo cáo',
                             'word': 'matrix organization'},
                         {   'example': 'Flat hierarchies speed up decisions.',
                             'ipa': '/flæt ˈhaɪ.ər.ɑːr.ki/',
                             'meaning': 'cấu trúc phẳng ít tầng quản lý',
                             'word': 'flat hierarchy'},
                         {   'example': 'Effective delegation multiplies '
                                        'output.',
                             'ipa': '/ˌdɛl.ɪˈɡeɪ.ʃən/',
                             'meaning': 'ủy quyền nhiệm vụ cho cấp dưới',
                             'word': 'delegation'},
                         {   'example': 'Accountability drives better '
                                        'performance.',
                             'ipa': '/əˌkaʊn.tə.ˈbɪl.ɪ.ti/',
                             'meaning': 'trách nhiệm giải trình kết quả công '
                                        'việc',
                             'word': 'accountability'},
                         {   'example': 'Autonomy increases job satisfaction.',
                             'ipa': '/ɔːˈtɒn.ə.mi/',
                             'meaning': 'quyền tự chủ trong công việc',
                             'word': 'autonomy'},
                         {   'example': 'Empowerment increases employee '
                                        'confidence.',
                             'ipa': '/ɪmˈpaʊər.mənt/',
                             'meaning': 'trao quyền hạn cho nhân viên',
                             'word': 'empowerment'},
                         {   'example': 'Executive coaching improves '
                                        'leadership.',
                             'ipa': '/ɪɡˈzɛk.jʊ.tɪv ˈkoʊ.tʃɪŋ/',
                             'meaning': 'huấn luyện cá nhân dành cho lãnh đạo',
                             'word': 'executive coaching'},
                         {   'example': 'Change management reduces resistance.',
                             'ipa': '/tʃeɪndʒ ˈmæn.ɪdʒ.mənt/',
                             'meaning': 'quản lý sự thay đổi tổ chức',
                             'word': 'change management'},
                         {   'example': 'Organizational design supports '
                                        'strategy.',
                             'ipa': '/ˌɔːr.ɡən.aɪˈzeɪ.ʃən.əl dɪˈzaɪn/',
                             'meaning': 'thiết kế cấu trúc tổ chức hiệu quả',
                             'word': 'organizational design'},
                         {   'example': 'Organizational behavior improves team '
                                        'dynamics.',
                             'ipa': '/ˌɔːr.ɡən.aɪˈzeɪ.ʃən.əl bɪˈheɪ.vjər/',
                             'meaning': 'hành vi tổ chức nghiên cứu con người '
                                        'công ty',
                             'word': 'organizational behavior'},
                         {   'example': 'Workforce analytics predicts '
                                        'attrition.',
                             'ipa': '/ˈwɜːrk.fɔːrs ˌæn.əˈlɪt.ɪks/',
                             'meaning': 'phân tích dữ liệu nhân sự tối ưu hóa',
                             'word': 'workforce analytics'},
                         {   'example': 'People analytics supports '
                                        'evidence-based HR.',
                             'ipa': '/ˈpiː.pəl ˌæn.əˈlɪt.ɪks/',
                             'meaning': 'phân tích con người đưa ra quyết định '
                                        'nhân sự',
                             'word': 'people analytics'},
                         {   'example': 'Become an employer of choice.',
                             'ipa': '/ɪmˈplɔɪ.ər əv tʃɔɪs/',
                             'meaning': 'nhà tuyển dụng được lựa chọn nhiều '
                                        'nhất',
                             'word': 'employer of choice'},
                         {   'example': 'Total compensation includes salary '
                                        'and benefits.',
                             'ipa': '/ˈtoʊ.təl ˌkɒm.pɛnˈseɪ.ʃən/',
                             'meaning': 'tổng đãi ngộ bao gồm lương và phúc '
                                        'lợi',
                             'word': 'total compensation'},
                         {   'example': 'Variable pay incentivizes '
                                        'performance.',
                             'ipa': '/ˈveər.i.ə.bəl peɪ/',
                             'meaning': 'lương biến đổi theo hiệu suất đạt '
                                        'được',
                             'word': 'variable pay'},
                         {   'example': 'Deferred compensation retains senior '
                                        'talent.',
                             'ipa': '/dɪˈfɜːrd ˌkɒm.pɛnˈseɪ.ʃən/',
                             'meaning': 'đãi ngộ hoãn trả theo thời gian điều '
                                        'kiện',
                             'word': 'deferred compensation'},
                         {   'example': 'Sign a non-compete clause before '
                                        'joining.',
                             'ipa': '/nɒn kəmˈpiːt klɔːz/',
                             'meaning': 'điều khoản không cạnh tranh sau nghỉ '
                                        'việc',
                             'word': 'non-compete clause'},
                         {   'example': 'Sign the NDA before starting work.',
                             'ipa': '/ˌɛn.diːˈeɪ/',
                             'meaning': 'thỏa thuận không tiết lộ thông tin '
                                        'bảo mật',
                             'word': 'NDA'},
                         {   'example': 'Your work IP belongs to the company.',
                             'ipa': '/ˌɪn.tɪˈlɛk.tʃʊ.əl ˈprɒp.ər.ti/',
                             'meaning': 'sở hữu trí tuệ kết quả công việc',
                             'word': 'intellectual property'},
                         {   'example': 'Whistleblowing protects the public '
                                        'interest.',
                             'ipa': '/ˈwɪs.əl.bloʊ.ɪŋ/',
                             'meaning': 'tố cáo hành vi sai trái trong tổ chức',
                             'word': 'whistleblowing'},
                         {   'example': 'Understand employment law before '
                                        'hiring.',
                             'ipa': '/ɪmˈplɔɪ.mənt lɔː/',
                             'meaning': 'luật lao động bảo vệ quyền nhân viên',
                             'word': 'employment law'},
                         {   'example': 'Follow the grievance procedure '
                                        'formally.',
                             'ipa': '/ˈɡriː.vəns prəˈsiː.dʒər/',
                             'meaning': 'quy trình khiếu nại giải quyết tranh '
                                        'chấp',
                             'word': 'grievance procedure'},
                         {   'example': 'Disciplinary action follows a fair '
                                        'process.',
                             'ipa': '/ˈdɪs.ɪ.plɪ.nər.i ˈæk.ʃən/',
                             'meaning': 'kỷ luật xử lý vi phạm nội quy',
                             'word': 'disciplinary action'},
                         {   'example': 'A PIP gives employees a chance to '
                                        'improve.',
                             'ipa': '/pərˈfɔːr.məns ɪmˈpruːv.mənt plæn/',
                             'meaning': 'kế hoạch cải thiện hiệu suất nhân '
                                        'viên yếu',
                             'word': 'performance improvement plan'},
                         {   'example': 'Exit interviews reveal retention '
                                        'issues.',
                             'ipa': '/ˈɛk.sɪt ˈɪn.tə.vjuː/',
                             'meaning': 'phỏng vấn nhân viên khi nghỉ việc',
                             'word': 'exit interview'},
                         {   'example': 'Stay interviews prevent talent loss.',
                             'ipa': '/steɪ ˈɪn.tə.vjuː/',
                             'meaning': 'phỏng vấn giữ chân nhân viên hiện tại',
                             'word': 'stay interview'},
                         {   'example': 'Boomerang employees bring external '
                                        'insights.',
                             'ipa': '/ˈbuː.mər.æŋ ɪmˈplɔɪ.iː/',
                             'meaning': 'nhân viên quay lại làm việc sau khi '
                                        'nghỉ',
                             'word': 'boomerang employee'},
                         {   'example': 'Break the glass ceiling for women.',
                             'ipa': '/ɡlɑːs ˈsiː.lɪŋ/',
                             'meaning': 'trần kính rào cản thăng tiến vô hình',
                             'word': 'glass ceiling'}],
               'C1': [   {   'example': 'Labor market dynamics shift with '
                                        'technology.',
                             'ipa': '/ˈleɪ.bər ˈmɑːr.kɪt daɪˈnæm.ɪks/',
                             'meaning': 'động lực thị trường lao động biến đổi',
                             'word': 'labor market dynamics'},
                         {   'example': 'The gig economy offers flexibility.',
                             'ipa': '/ɡɪɡ ɪˈkɒn.ə.mi/',
                             'meaning': 'nền kinh tế hợp đồng ngắn hạn tự do',
                             'word': 'gig economy'},
                         {   'example': 'Uber operates in the platform '
                                        'economy.',
                             'ipa': '/ˈplæt.fɔːrm ɪˈkɒn.ə.mi/',
                             'meaning': 'nền kinh tế nền tảng kỹ thuật số',
                             'word': 'platform economy'},
                         {   'example': 'Precarious work lacks social '
                                        'protection.',
                             'ipa': '/prɪˈkeər.i.əs wɜːrk/',
                             'meaning': 'công việc bấp bênh không ổn định',
                             'word': 'precarious work'},
                         {   'example': 'Good labor relations prevent strikes.',
                             'ipa': '/ˈleɪ.bər rɪˈleɪ.ʃənz/',
                             'meaning': 'quan hệ lao động giữa công ty và nhân '
                                        'viên',
                             'word': 'labor relations'},
                         {   'example': 'Collective bargaining protects worker '
                                        'rights.',
                             'ipa': '/kəˈlɛk.tɪv ˈbɑːr.ɡɪ.nɪŋ/',
                             'meaning': 'thương lượng tập thể của công đoàn',
                             'word': 'collective bargaining'},
                         {   'example': 'Industrial action can halt '
                                        'production.',
                             'ipa': '/ɪnˈdʌs.tri.əl ˈæk.ʃən/',
                             'meaning': 'hành động công nghiệp đình công phản '
                                        'đối',
                             'word': 'industrial action'},
                         {   'example': "Human capital is a firm's greatest "
                                        'asset.',
                             'ipa': '/ˈhjuː.mən ˈkæp.ɪ.təl/',
                             'meaning': 'vốn nhân lực năng lực con người',
                             'word': 'human capital'},
                         {   'example': 'Intellectual capital drives '
                                        'competitive advantage.',
                             'ipa': '/ˌɪn.tɪˈlɛk.tʃʊ.əl ˈkæp.ɪ.təl/',
                             'meaning': 'vốn trí tuệ kiến thức sáng tạo',
                             'word': 'intellectual capital'},
                         {   'example': 'Organizational resilience is built '
                                        'through diversity.',
                             'ipa': '/ˌɔːr.ɡən.aɪˈzeɪ.ʃən.əl rɪˈzɪl.i.əns/',
                             'meaning': 'khả năng phục hồi của tổ chức sau '
                                        'khủng hoảng',
                             'word': 'organizational resilience'},
                         {   'example': 'AI shapes the future of work.',
                             'ipa': '/ˈfjuː.tʃər əv wɜːrk/',
                             'meaning': 'tương lai công việc trong kỷ nguyên '
                                        'AI',
                             'word': 'future of work'},
                         {   'example': 'Automation displacement requires '
                                        'reskilling.',
                             'ipa': '/ˌɔː.tə.ˈmeɪ.ʃən dɪsˈpleɪs.mənt/',
                             'meaning': 'mất việc làm do tự động hóa thay thế',
                             'word': 'automation displacement'},
                         {   'example': 'An augmented workforce uses AI tools.',
                             'ipa': '/ɔːɡˈmɛn.tɪd ˈwɜːrk.fɔːrs/',
                             'meaning': 'lực lượng lao động tăng cường bởi AI',
                             'word': 'augmented workforce'},
                         {   'example': 'Strategic workforce planning predicts '
                                        'talent needs.',
                             'ipa': '/strəˈtiː.dʒɪk ˈwɜːrk.fɔːrs ˈplæn.ɪŋ/',
                             'meaning': 'lập kế hoạch nhân sự chiến lược dài '
                                        'hạn',
                             'word': 'strategic workforce planning'},
                         {   'example': 'Total rewards include pay, benefits, '
                                        'and culture.',
                             'ipa': '/ˈtoʊ.təl rɪˈwɔːrdz ˈstræt.ɪ.dʒi/',
                             'meaning': 'chiến lược tổng đãi ngộ toàn diện',
                             'word': 'total rewards strategy'},
                         {   'example': 'Pay equity analysis closes the gender '
                                        'pay gap.',
                             'ipa': '/peɪ ˈɛk.wɪ.ti əˈnæl.ɪ.sɪs/',
                             'meaning': 'phân tích công bằng tiền lương giới '
                                        'tính',
                             'word': 'pay equity analysis'},
                         {   'example': 'Competency-based interviews reveal '
                                        'true behavior.',
                             'ipa': '/kəmˈpɛt.ən.si beɪst ˈɪn.tə.vjuː/',
                             'meaning': 'phỏng vấn dựa trên năng lực hành vi',
                             'word': 'competency-based interview'},
                         {   'example': 'Identify high-potential employees '
                                        'early.',
                             'ipa': '/haɪ pəˈtɛn.ʃəl/',
                             'meaning': 'nhân tài tiềm năng cao trong tổ chức',
                             'word': 'high-potential'},
                         {   'example': 'A leadership pipeline ensures '
                                        'continuity.',
                             'ipa': '/ˈliː.dər.ʃɪp ˈpaɪp.laɪn/',
                             'meaning': 'chuỗi lãnh đạo kế cận được chuẩn bị',
                             'word': 'leadership pipeline'},
                         {   'example': 'Breaking the psychological contract '
                                        'causes turnover.',
                             'ipa': '/ˌsaɪ.kəˈlɒdʒ.ɪ.kəl ˈkɒn.trækt/',
                             'meaning': 'hợp đồng tâm lý kỳ vọng ngầm định',
                             'word': 'psychological contract'},
                         {   'example': 'OCB goes beyond formal job '
                                        'requirements.',
                             'ipa': '/ˌɔːr.ɡən.aɪˈzeɪ.ʃən.əl ˈsɪt.ɪ.zən.ʃɪp '
                                    'bɪˈheɪ.vjər/',
                             'meaning': 'hành vi công dân tổ chức tự nguyện',
                             'word': 'organizational citizenship behavior'},
                         {   'example': 'Job crafting improves meaning and '
                                        'engagement.',
                             'ipa': '/dʒɒb ˈkrɑːf.tɪŋ/',
                             'meaning': 'tái thiết kế công việc phù hợp bản '
                                        'thân',
                             'word': 'job crafting'},
                         {   'example': 'Burnout prevention requires systemic '
                                        'change.',
                             'ipa': '/ˈbɜːrn.aʊt prɪˈvɛn.ʃən/',
                             'meaning': 'phòng ngừa kiệt sức chuyên nghiệp',
                             'word': 'burnout prevention'},
                         {   'example': 'A wellbeing strategy reduces '
                                        'absenteeism.',
                             'ipa': '/ˈwɛl.biː.ɪŋ ˈstræt.ɪ.dʒi/',
                             'meaning': 'chiến lược phúc lợi sức khỏe nhân '
                                        'viên',
                             'word': 'wellbeing strategy'},
                         {   'example': 'Inclusive leadership values every '
                                        'voice.',
                             'ipa': '/ɪnˈkluː.sɪv ˈliː.dər.ʃɪp/',
                             'meaning': 'lãnh đạo hòa nhập tôn trọng đa dạng',
                             'word': 'inclusive leadership'},
                         {   'example': 'Servant leadership puts the team '
                                        'first.',
                             'ipa': '/ˈsɜːr.vənt ˈliː.dər.ʃɪp/',
                             'meaning': 'lãnh đạo phụng sự phục vụ nhóm trước',
                             'word': 'servant leadership'},
                         {   'example': 'Transformational leadership inspires '
                                        'change.',
                             'ipa': '/trænsˈfɔːr.mə.ʃən.əl ˈliː.dər.ʃɪp/',
                             'meaning': 'lãnh đạo chuyển hóa truyền cảm hứng',
                             'word': 'transformational leadership'},
                         {   'example': 'Transactional leadership uses rewards '
                                        'and punishments.',
                             'ipa': '/trænˈzæk.ʃən.əl ˈliː.dər.ʃɪp/',
                             'meaning': 'lãnh đạo giao dịch dùng thưởng phạt',
                             'word': 'transactional leadership'},
                         {   'example': 'Situational leadership adapts to team '
                                        'needs.',
                             'ipa': '/ˌsɪtʃ.ʊˈeɪ.ʃən.əl ˈliː.dər.ʃɪp/',
                             'meaning': 'lãnh đạo tình huống linh hoạt thích '
                                        'ứng',
                             'word': 'situational leadership'},
                         {   'example': 'Cognitive diversity improves decision '
                                        'quality.',
                             'ipa': '/ˈkɒɡ.nɪ.tɪv daɪˈvɜːr.sɪ.ti/',
                             'meaning': 'đa dạng nhận thức cách tư duy khác '
                                        'nhau',
                             'word': 'cognitive diversity'},
                         {   'example': 'Knowledge management prevents brain '
                                        'drain.',
                             'ipa': '/ˈnɒl.ɪdʒ ˈmæn.ɪdʒ.mənt/',
                             'meaning': 'quản lý tri thức tổ chức chia sẻ',
                             'word': 'knowledge management'},
                         {   'example': 'A learning organization adapts '
                                        'quickly.',
                             'ipa': '/ˈlɜːr.nɪŋ ˌɔːr.ɡən.aɪˈzeɪ.ʃən/',
                             'meaning': 'tổ chức học hỏi liên tục thích nghi',
                             'word': 'learning organization'},
                         {   'example': 'A meritocracy rewards hard work.',
                             'ipa': '/ˌmɛr.ɪˈtɒk.rə.si/',
                             'meaning': 'chế độ trọng dụng nhân tài theo thực '
                                        'lực',
                             'word': 'meritocracy'},
                         {   'example': 'Nepotism undermines fairness.',
                             'ipa': '/ˈnɛp.ə.tɪ.zəm/',
                             'meaning': 'chủ nghĩa thân tộc thiên vị người '
                                        'quen',
                             'word': 'nepotism'},
                         {   'example': 'Many leaders experience imposter '
                                        'syndrome.',
                             'ipa': '/ɪmˈpɒs.tər ˈsɪn.droʊm/',
                             'meaning': 'hội chứng kẻ mạo danh tự ti năng lực',
                             'word': 'imposter syndrome'},
                         {   'example': 'Build career capital before choosing '
                                        'a path.',
                             'ipa': '/kəˈrɪər ˈkæp.ɪ.təl/',
                             'meaning': 'vốn sự nghiệp kỹ năng và mối quan hệ',
                             'word': 'career capital'},
                         {   'example': 'A strong professional network opens '
                                        'doors.',
                             'ipa': '/prəˈfɛʃ.ən.əl ˈnɛt.wɜːrk/',
                             'meaning': 'mạng lưới chuyên nghiệp hỗ trợ sự '
                                        'nghiệp',
                             'word': 'professional network'},
                         {   'example': 'Executive presence commands respect.',
                             'ipa': '/ɪɡˈzɛk.jʊ.tɪv ˈprɛz.əns/',
                             'meaning': 'phong thái lãnh đạo tạo ảnh hưởng',
                             'word': 'executive presence'},
                         {   'example': 'Strategic thinking separates leaders '
                                        'from managers.',
                             'ipa': '/strəˈtiː.dʒɪk ˈθɪŋ.kɪŋ/',
                             'meaning': 'tư duy chiến lược dài hạn toàn diện',
                             'word': 'strategic thinking'},
                         {   'example': 'Systems thinking reveals root causes.',
                             'ipa': '/ˈsɪs.təmz ˈθɪŋ.kɪŋ/',
                             'meaning': 'tư duy hệ thống toàn diện kết nối',
                             'word': 'systems thinking'},
                         {   'example': 'Double-loop learning challenges '
                                        'assumptions.',
                             'ipa': '/ˈdʌb.əl luːp ˈlɜːr.nɪŋ/',
                             'meaning': 'học vòng đôi thay đổi tư duy giả định',
                             'word': 'double-loop learning'},
                         {   'example': 'After-action reviews improve team '
                                        'learning.',
                             'ipa': '/ˈɑːf.tər ˈæk.ʃən rɪˈvjuː/',
                             'meaning': 'đánh giá sau hành động rút kinh '
                                        'nghiệm',
                             'word': 'after-action review'},
                         {   'example': 'Appreciative inquiry builds on '
                                        'strengths.',
                             'ipa': '/əˈpriː.ʃi.ə.tɪv ɪnˈkwaɪər.i/',
                             'meaning': 'truy vấn trân trọng tập trung điểm '
                                        'mạnh',
                             'word': 'appreciative inquiry'},
                         {   'example': 'POS focuses on human flourishing at '
                                        'work.',
                             'ipa': '/ˈpɒz.ɪ.tɪv ˌɔːr.ɡən.aɪˈzeɪ.ʃən.əl '
                                    'ˈskɒl.ər.ʃɪp/',
                             'meaning': 'học thuật tổ chức tích cực phát huy '
                                        'tiềm năng',
                             'word': 'positive organizational scholarship'},
                         {   'example': 'TQM improves processes continuously.',
                             'ipa': '/ˈtoʊ.təl ˈkwɒl.ɪ.ti ˈmæn.ɪdʒ.mənt/',
                             'meaning': 'quản lý chất lượng toàn diện TQM',
                             'word': 'total quality management'},
                         {   'example': 'Lean management eliminates waste.',
                             'ipa': '/liːn ˈmæn.ɪdʒ.mənt/',
                             'meaning': 'quản lý tinh gọn loại bỏ lãng phí',
                             'word': 'lean management'},
                         {   'example': 'Six Sigma reduces process defects.',
                             'ipa': '/sɪks ˈsɪɡ.mə/',
                             'meaning': 'phương pháp cải tiến chất lượng 6 '
                                        'sigma',
                             'word': 'six sigma'},
                         {   'example': 'Kaizen means continuous small '
                                        'improvements.',
                             'ipa': '/ˈkaɪ.zɛn/',
                             'meaning': 'triết lý cải tiến liên tục mỗi ngày',
                             'word': 'kaizen'},
                         {   'example': 'Organizational ambidexterity balances '
                                        'exploitation and exploration.',
                             'ipa': '/ˌɔːr.ɡən.aɪˈzeɪ.ʃən.əl '
                                    'ˌæm.bɪˈdɛks.tər.ɪ.ti/',
                             'meaning': 'khả năng vừa khai thác vừa khám phá '
                                        'của tổ chức',
                             'word': 'organizational ambidexterity'},
                         {   'example': 'Embracing neurodiversity unlocks '
                                        'unique talents.',
                             'ipa': '/ˈwɜːrk.pleɪs ˌnjʊər.oʊ.daɪˈvɜːr.sɪ.ti/',
                             'meaning': 'đa dạng thần kinh nhận thức tại nơi '
                                        'làm việc',
                             'word': 'workplace neurodiversity'}]},
    'marketing': {   'A1': [   {   'example': 'We sell products online.',
                                   'ipa': '/sɛl/',
                                   'meaning': 'bán hàng hóa',
                                   'word': 'sell'},
                               {   'example': 'I saw an ad on YouTube.',
                                   'ipa': '/æd/',
                                   'meaning': 'mẫu quảng cáo ngắn',
                                   'word': 'ad'},
                               {   'example': 'The logo is red and white.',
                                   'ipa': '/ˈloʊ.ɡoʊ/',
                                   'meaning': 'biểu trưng thương hiệu',
                                   'word': 'logo'},
                               {   'example': 'Apple is a famous brand.',
                                   'ipa': '/brænd/',
                                   'meaning': 'nhãn hiệu thương hiệu',
                                   'word': 'brand'},
                               {   'example': 'The price is too high.',
                                   'ipa': '/praɪs/',
                                   'meaning': 'giá bán sản phẩm',
                                   'word': 'price'},
                               {   'example': 'The cost is reasonable.',
                                   'ipa': '/kɒst/',
                                   'meaning': 'chi phí mua sản phẩm',
                                   'word': 'cost'},
                               {   'example': 'The sale ends today.',
                                   'ipa': '/seɪl/',
                                   'meaning': 'đợt giảm giá hàng',
                                   'word': 'sale'},
                               {   'example': 'Get one item free.',
                                   'ipa': '/friː/',
                                   'meaning': 'miễn phí không tốn tiền',
                                   'word': 'free'},
                               {   'example': 'Every customer gets a gift.',
                                   'ipa': '/ɡɪft/',
                                   'meaning': 'quà tặng cho khách',
                                   'word': 'gift'},
                               {   'example': 'Swipe your card to pay.',
                                   'ipa': '/kɑːrd/',
                                   'meaning': 'thẻ ngân hàng thanh toán',
                                   'word': 'card'},
                               {   'example': 'This is a great deal.',
                                   'ipa': '/diːl/',
                                   'meaning': 'giao dịch thỏa thuận tốt',
                                   'word': 'deal'},
                               {   'example': 'The customer is always right.',
                                   'ipa': '/ˈkʌs.tə.mər/',
                                   'meaning': 'người mua hàng hóa',
                                   'word': 'customer'},
                               {   'example': 'Our product has a warranty.',
                                   'ipa': '/ˈprɒd.ʌkt/',
                                   'meaning': 'sản phẩm hàng hóa',
                                   'word': 'product'},
                               {   'example': 'The service is excellent.',
                                   'ipa': '/ˈsɜːr.vɪs/',
                                   'meaning': 'dịch vụ đi kèm sản phẩm',
                                   'word': 'service'},
                               {   'example': 'We have a limited offer.',
                                   'ipa': '/ˈɒf.ər/',
                                   'meaning': 'đề nghị ưu đãi mua hàng',
                                   'word': 'offer'},
                               {   'example': 'Get a 20% discount today.',
                                   'ipa': '/ˈdɪs.kaʊnt/',
                                   'meaning': 'giảm giá phần trăm',
                                   'word': 'discount'},
                               {   'example': 'Use a coupon at checkout.',
                                   'ipa': '/ˈkuː.pɒn/',
                                   'meaning': 'phiếu giảm giá',
                                   'word': 'coupon'},
                               {   'example': 'Earn rewards with every '
                                              'purchase.',
                                   'ipa': '/rɪˈwɔːrd/',
                                   'meaning': 'điểm thưởng tích lũy',
                                   'word': 'reward'},
                               {   'example': 'Open the package carefully.',
                                   'ipa': '/ˈpæk.ɪdʒ/',
                                   'meaning': 'gói sản phẩm đóng gói',
                                   'word': 'package'},
                               {   'example': 'Read customer reviews first.',
                                   'ipa': '/rɪˈvjuː/',
                                   'meaning': 'đánh giá sản phẩm',
                                   'word': 'review'},
                               {   'example': 'The product has a 5-star '
                                              'rating.',
                                   'ipa': '/ˈreɪ.tɪŋ/',
                                   'meaning': 'xếp hạng sao sản phẩm',
                                   'word': 'rating'},
                               {   'example': 'Visit our online store.',
                                   'ipa': '/stɔːr/',
                                   'meaning': 'cửa hàng bán lẻ',
                                   'word': 'store'},
                               {   'example': 'Place your order online.',
                                   'ipa': '/ˈɔːr.dər/',
                                   'meaning': 'đặt hàng mua sản phẩm',
                                   'word': 'order'},
                               {   'example': 'You can return the item.',
                                   'ipa': '/rɪˈtɜːrn/',
                                   'meaning': 'trả lại hàng mua',
                                   'word': 'return'},
                               {   'example': 'The item is out of stock.',
                                   'ipa': '/stɒk/',
                                   'meaning': 'hàng tồn kho',
                                   'word': 'stock'},
                               {   'example': 'Supply meets demand now.',
                                   'ipa': '/səˈplaɪ/',
                                   'meaning': 'nguồn cung hàng hóa',
                                   'word': 'supply'},
                               {   'example': 'Demand for this is high.',
                                   'ipa': '/dɪˈmænd/',
                                   'meaning': 'nhu cầu thị trường',
                                   'word': 'demand'},
                               {   'example': 'This is our most popular item.',
                                   'ipa': '/ˈpɒp.jʊ.lər/',
                                   'meaning': 'phổ biến được ưa chuộng',
                                   'word': 'popular'},
                               {   'example': 'Build trust with your '
                                              'customers.',
                                   'ipa': '/trʌst/',
                                   'meaning': 'niềm tin khách hàng',
                                   'word': 'trust'},
                               {   'example': 'Quality is our top priority.',
                                   'ipa': '/ˈkwɒl.ɪ.ti/',
                                   'meaning': 'chất lượng sản phẩm tốt',
                                   'word': 'quality'},
                               {   'example': 'This product offers great '
                                              'value.',
                                   'ipa': '/ˈvæl.juː/',
                                   'meaning': 'giá trị sản phẩm nhận được',
                                   'word': 'value'},
                               {   'example': 'Know your target audience.',
                                   'ipa': '/ˈɔː.di.əns/',
                                   'meaning': 'đối tượng khách hàng mục tiêu',
                                   'word': 'audience'},
                               {   'example': 'Target young adults online.',
                                   'ipa': '/ˈtɑːr.ɡɪt/',
                                   'meaning': 'mục tiêu tiếp thị',
                                   'word': 'target'},
                               {   'example': 'Our ad reaches many people.',
                                   'ipa': '/riːtʃ/',
                                   'meaning': 'tiếp cận người xem quảng cáo',
                                   'word': 'reach'},
                               {   'example': 'Use social media as a channel.',
                                   'ipa': '/ˈtʃæn.əl/',
                                   'meaning': 'kênh phân phối truyền thông',
                                   'word': 'channel'},
                               {   'example': 'Create engaging content daily.',
                                   'ipa': '/ˈkɒn.tɛnt/',
                                   'meaning': 'nội dung truyền thông sáng tạo',
                                   'word': 'content'},
                               {   'example': 'Hand out flyers near the shop.',
                                   'ipa': '/ˈflaɪ.ər/',
                                   'meaning': 'tờ rơi quảng cáo in ấn',
                                   'word': 'flyer'},
                               {   'example': 'Put up a poster in the window.',
                                   'ipa': '/ˈpoʊ.stər/',
                                   'meaning': 'áp phích quảng cáo dán tường',
                                   'word': 'poster'},
                               {   'example': 'Give customers a brand sticker.',
                                   'ipa': '/ˈstɪk.ər/',
                                   'meaning': 'nhãn dán quảng cáo thương hiệu',
                                   'word': 'sticker'},
                               {   'example': 'Give free samples to customers.',
                                   'ipa': '/ˈsæm.pəl/',
                                   'meaning': 'mẫu thử miễn phí sản phẩm',
                                   'word': 'sample'},
                               {   'example': 'Watch the product demo.',
                                   'ipa': '/ˈdɛm.oʊ/',
                                   'meaning': 'bản trình diễn sản phẩm',
                                   'word': 'demo'},
                               {   'example': 'Host a brand event.',
                                   'ipa': '/ɪˈvɛnt/',
                                   'meaning': 'sự kiện quảng bá thương hiệu',
                                   'word': 'event'},
                               {   'example': 'Launch the product next month.',
                                   'ipa': '/lɔːntʃ/',
                                   'meaning': 'ra mắt sản phẩm mới',
                                   'word': 'launch'},
                               {   'example': 'Grow your subscriber count.',
                                   'ipa': '/səbˈskraɪ.bər/',
                                   'meaning': 'người đăng ký theo dõi',
                                   'word': 'subscriber'},
                               {   'example': 'Use a trending hashtag.',
                                   'ipa': '/ˈhæʃ.tæɡ/',
                                   'meaning': 'thẻ bắt đầu bằng dấu thăng',
                                   'word': 'hashtag'},
                               {   'example': 'Follow the latest market trend.',
                                   'ipa': '/trɛnd/',
                                   'meaning': 'xu hướng thị trường hot',
                                   'word': 'trend'},
                               {   'example': 'Place an advertisement in the '
                                              'paper.',
                                   'ipa': '/ədˈvɜːr.tɪs.mənt/',
                                   'meaning': 'mẫu quảng cáo chính thức',
                                   'word': 'advertisement'},
                               {   'example': 'Build a positive brand image.',
                                   'ipa': '/brænd ˈɪm.ɪdʒ/',
                                   'meaning': 'hình ảnh thương hiệu trong tâm '
                                              'trí',
                                   'word': 'brand image'},
                               {   'example': 'Prepare a strong sales pitch.',
                                   'ipa': '/seɪlz pɪtʃ/',
                                   'meaning': 'bài thuyết phục bán hàng',
                                   'word': 'sales pitch'},
                               {   'example': 'Word-of-mouth is very '
                                              'effective.',
                                   'ipa': '/wɜːrd əv maʊθ/',
                                   'meaning': 'truyền miệng quảng cáo tự nhiên',
                                   'word': 'word-of-mouth'},
                               {   'example': 'I want to buy a new phone.',
                                   'ipa': '/baɪ/',
                                   'meaning': 'mua hàng hóa',
                                   'word': 'buy'},
                               {   'example': "Let's go to the shop.",
                                   'ipa': '/ʃɒp/',
                                   'meaning': 'cửa hàng bán lẻ',
                                   'word': 'shop'},
                               {   'example': 'You can pay by card.',
                                   'ipa': '/peɪ/',
                                   'meaning': 'thanh toán tiền mua',
                                   'word': 'pay'},
                               {   'example': 'Request a full refund.',
                                   'ipa': '/ˈriː.fʌnd/',
                                   'meaning': 'hoàn tiền cho khách',
                                   'word': 'refund'}],
                     'A2': [   {   'example': 'Digital advertising is '
                                              'cost-effective.',
                                   'ipa': '/ˈæd.vər.taɪ.zɪŋ/',
                                   'meaning': 'hoạt động quảng cáo thương mại',
                                   'word': 'advertising'},
                               {   'example': 'We need a new marketing '
                                              'strategy.',
                                   'ipa': '/ˈmɑːr.kɪ.tɪŋ ˈstræt.ɪ.dʒi/',
                                   'meaning': 'chiến lược tiếp thị tổng thể',
                                   'word': 'marketing strategy'},
                               {   'example': 'Identify your target market '
                                              'first.',
                                   'ipa': '/ˈtɑːr.ɡɪt ˈmɑːr.kɪt/',
                                   'meaning': 'thị trường mục tiêu hướng đến',
                                   'word': 'target market'},
                               {   'example': 'Conduct a customer satisfaction '
                                              'survey.',
                                   'ipa': '/ˈsɜːr.veɪ/',
                                   'meaning': 'khảo sát ý kiến khách hàng',
                                   'word': 'survey'},
                               {   'example': 'Use customer feedback to '
                                              'improve.',
                                   'ipa': '/ˈfiːd.bæk/',
                                   'meaning': 'phản hồi từ khách hàng',
                                   'word': 'feedback'},
                               {   'example': 'Customer satisfaction is our '
                                              'goal.',
                                   'ipa': '/ˌsæt.ɪsˈfæk.ʃən/',
                                   'meaning': 'sự hài lòng của khách hàng',
                                   'word': 'satisfaction'},
                               {   'example': 'Build customer loyalty with '
                                              'rewards.',
                                   'ipa': '/ˈlɔɪ.əl.ti/',
                                   'meaning': 'lòng trung thành của khách hàng',
                                   'word': 'loyalty'},
                               {   'example': 'Analyze your key competitors.',
                                   'ipa': '/kəmˈpɛt.ɪ.tər/',
                                   'meaning': 'đối thủ cạnh tranh trên thị '
                                              'trường',
                                   'word': 'competitor'},
                               {   'example': 'Competition drives innovation.',
                                   'ipa': '/ˌkɒm.pɪˈtɪʃ.ən/',
                                   'meaning': 'sự cạnh tranh trên thị trường',
                                   'word': 'competition'},
                               {   'example': 'What is your unique selling '
                                              'point?',
                                   'ipa': '/juːˈniːk ˈsɛl.ɪŋ pɔɪnt/',
                                   'meaning': 'điểm bán hàng độc đáo khác biệt',
                                   'word': 'unique selling point'},
                               {   'example': 'Brand positioning sets you '
                                              'apart.',
                                   'ipa': '/pəˈzɪʃ.ən.ɪŋ/',
                                   'meaning': 'định vị thương hiệu trong tâm '
                                              'trí khách',
                                   'word': 'positioning'},
                               {   'example': 'Segmentation targets specific '
                                              'customer groups.',
                                   'ipa': '/ˌsɛɡ.mɛnˈteɪ.ʃən/',
                                   'meaning': 'phân khúc thị trường theo nhóm',
                                   'word': 'segmentation'},
                               {   'example': 'Understand the demographics of '
                                              'your audience.',
                                   'ipa': '/ˌdɛm.əˈɡræf.ɪk/',
                                   'meaning': 'đặc điểm nhân khẩu học nhóm '
                                              'khách',
                                   'word': 'demographic'},
                               {   'example': 'The video went viral overnight.',
                                   'ipa': '/ˈvaɪər.əl/',
                                   'meaning': 'lan truyền nhanh chóng trên '
                                              'mạng',
                                   'word': 'viral'},
                               {   'example': 'The ad received one million '
                                              'impressions.',
                                   'ipa': '/ɪmˈprɛʃ.ən/',
                                   'meaning': 'lượt hiển thị quảng cáo cho '
                                              'người xem',
                                   'word': 'impression'},
                               {   'example': 'Improve the click-through rate.',
                                   'ipa': '/klɪk θruː reɪt/',
                                   'meaning': 'tỷ lệ nhấp chuột vào quảng cáo',
                                   'word': 'click-through rate'},
                               {   'example': 'Generate more sales leads.',
                                   'ipa': '/liːd/',
                                   'meaning': 'khách hàng tiềm năng chưa mua',
                                   'word': 'lead'},
                               {   'example': 'The sales funnel needs '
                                              'optimization.',
                                   'ipa': '/ˈfʌn.əl/',
                                   'meaning': 'phễu bán hàng từ nhận biết đến '
                                              'mua',
                                   'word': 'funnel'},
                               {   'example': 'Add a clear call to action.',
                                   'ipa': '/kɔːl tuː ˈæk.ʃən/',
                                   'meaning': 'lời kêu gọi hành động mua ngay',
                                   'word': 'call to action'},
                               {   'example': 'Optimize the landing page for '
                                              'conversions.',
                                   'ipa': '/ˈlæn.dɪŋ peɪdʒ/',
                                   'meaning': 'trang đích nhận lưu lượng quảng '
                                              'cáo',
                                   'word': 'landing page'},
                               {   'example': 'Email marketing has a high ROI.',
                                   'ipa': '/ˈiː.meɪl ˈmɑːr.kɪ.tɪŋ/',
                                   'meaning': 'tiếp thị qua thư điện tử',
                                   'word': 'email marketing'},
                               {   'example': 'Send a monthly newsletter.',
                                   'ipa': '/ˈnjuːz.lɛt.ər/',
                                   'meaning': 'bản tin định kỳ cho khách đăng '
                                              'ký',
                                   'word': 'newsletter'},
                               {   'example': 'Get a sponsorship from a big '
                                              'brand.',
                                   'ipa': '/ˈspɒn.sər.ʃɪp/',
                                   'meaning': 'tài trợ sự kiện hoặc nội dung',
                                   'word': 'sponsorship'},
                               {   'example': 'Join our affiliate program.',
                                   'ipa': '/əˈfɪl.i.ɪt/',
                                   'meaning': 'đối tác liên kết kiếm hoa hồng',
                                   'word': 'affiliate'},
                               {   'example': 'Affiliates earn a 10% '
                                              'commission.',
                                   'ipa': '/kəˈmɪʃ.ən/',
                                   'meaning': 'hoa hồng cho đối tác bán hàng',
                                   'word': 'commission'},
                               {   'example': 'Use testimonials to build '
                                              'trust.',
                                   'ipa': '/ˌtɛs.tɪˈmoʊ.ni.əl/',
                                   'meaning': 'lời chứng thực từ khách hàng cũ',
                                   'word': 'testimonial'},
                               {   'example': 'Share a case study with '
                                              'prospects.',
                                   'ipa': '/keɪs ˈstʌd.i/',
                                   'meaning': 'nghiên cứu tình huống thành '
                                              'công',
                                   'word': 'case study'},
                               {   'example': 'Issue a press release for the '
                                              'launch.',
                                   'ipa': '/prɛs rɪˈliːs/',
                                   'meaning': 'thông cáo báo chí chính thức',
                                   'word': 'press release'},
                               {   'example': 'Exhibit at the annual trade '
                                              'show.',
                                   'ipa': '/treɪd ʃoʊ/',
                                   'meaning': 'hội chợ thương mại ngành nghề',
                                   'word': 'trade show'},
                               {   'example': 'Event marketing creates brand '
                                              'experiences.',
                                   'ipa': '/ɪˈvɛnt ˈmɑːr.kɪ.tɪŋ/',
                                   'meaning': 'tiếp thị thông qua tổ chức sự '
                                              'kiện',
                                   'word': 'event marketing'},
                               {   'example': 'Direct mail still works for '
                                              'some audiences.',
                                   'ipa': '/daɪˈrɛkt meɪl/',
                                   'meaning': 'gửi thư trực tiếp đến khách '
                                              'hàng',
                                   'word': 'direct mail'},
                               {   'example': 'Place a print ad in the '
                                              'newspaper.',
                                   'ipa': '/prɪnt æd/',
                                   'meaning': 'quảng cáo in ấn trên báo chí',
                                   'word': 'print ad'},
                               {   'example': 'Put a billboard near the '
                                              'highway.',
                                   'ipa': '/ˈbɪl.bɔːrd/',
                                   'meaning': 'biển quảng cáo ngoài trời lớn',
                                   'word': 'billboard'},
                               {   'example': 'Word of mouth is the best '
                                              'marketing.',
                                   'ipa': '/wɜːrd əv maʊθ/',
                                   'meaning': 'truyền miệng từ khách hàng hài '
                                              'lòng',
                                   'word': 'word of mouth'},
                               {   'example': 'Referrals bring high-quality '
                                              'leads.',
                                   'ipa': '/rɪˈfɜːr.əl/',
                                   'meaning': 'giới thiệu khách hàng mới từ cũ',
                                   'word': 'referral'},
                               {   'example': 'Build a strong brand identity.',
                                   'ipa': '/brænd aɪˈdɛn.tɪ.ti/',
                                   'meaning': 'bản sắc thương hiệu tổng thể',
                                   'word': 'brand identity'},
                               {   'example': 'Create a memorable tagline.',
                                   'ipa': '/ˈtæɡ.laɪn/',
                                   'meaning': 'khẩu hiệu thương hiệu ngắn gọn',
                                   'word': 'tagline'},
                               {   'example': "Nike's slogan is Just Do It.",
                                   'ipa': '/ˈsloʊ.ɡən/',
                                   'meaning': 'khẩu hiệu quảng cáo ghi nhớ',
                                   'word': 'slogan'},
                               {   'example': 'Good copywriting drives sales.',
                                   'ipa': '/ˈkɒp.i.raɪ.tɪŋ/',
                                   'meaning': 'viết nội dung thuyết phục để '
                                              'bán hàng',
                                   'word': 'copywriting'},
                               {   'example': 'Write a compelling headline.',
                                   'ipa': '/ˈhɛd.laɪn/',
                                   'meaning': 'tiêu đề thu hút chú ý quảng cáo',
                                   'word': 'headline'},
                               {   'example': 'Choose a consistent color '
                                              'scheme.',
                                   'ipa': '/ˈkʌl.ər skiːm/',
                                   'meaning': 'bảng màu thương hiệu nhất quán',
                                   'word': 'color scheme'},
                               {   'example': 'The mascot makes the brand '
                                              'memorable.',
                                   'ipa': '/ˈmæs.kɒt/',
                                   'meaning': 'linh vật đại diện thương hiệu',
                                   'word': 'mascot'},
                               {   'example': 'The jingle gets stuck in your '
                                              'head.',
                                   'ipa': '/ˈdʒɪŋ.ɡəl/',
                                   'meaning': 'điệu nhạc quảng cáo dễ nhớ',
                                   'word': 'jingle'},
                               {   'example': 'Packaging design influences '
                                              'buying decisions.',
                                   'ipa': '/ˈpæk.ɪ.dʒɪŋ dɪˈzaɪn/',
                                   'meaning': 'thiết kế bao bì thu hút mắt '
                                              'khách',
                                   'word': 'packaging design'},
                               {   'example': 'Create detailed buyer personas.',
                                   'ipa': '/ˈbaɪ.ər pərˈsoʊ.nə/',
                                   'meaning': 'chân dung người mua hàng mục '
                                              'tiêu',
                                   'word': 'buyer persona'},
                               {   'example': 'Address customer pain points.',
                                   'ipa': '/peɪn pɔɪnt/',
                                   'meaning': 'điểm đau nỗi lo của khách hàng',
                                   'word': 'pain point'},
                               {   'example': 'Find a market gap to fill.',
                                   'ipa': '/ˈmɑːr.kɪt ɡæp/',
                                   'meaning': 'khoảng trống thị trường chưa '
                                              'được phục vụ',
                                   'word': 'market gap'},
                               {   'example': 'Follow the latest market '
                                              'trends.',
                                   'ipa': '/ˈmɑːr.kɪt trɛnd/',
                                   'meaning': 'xu hướng thị trường hiện tại',
                                   'word': 'market trend'},
                               {   'example': 'Study consumer behavior for '
                                              'insights.',
                                   'ipa': '/kənˈsjuː.mər bɪˈheɪ.vjər/',
                                   'meaning': 'hành vi tiêu dùng của khách '
                                              'hàng',
                                   'word': 'consumer behavior'},
                               {   'example': 'Clear product positioning '
                                              'drives sales.',
                                   'ipa': '/ˈprɒd.ʌkt pəˈzɪʃ.ən.ɪŋ/',
                                   'meaning': 'định vị sản phẩm trong tâm trí',
                                   'word': 'product positioning'}],
                     'B1': [   {   'example': 'The target audience for this '
                                              'product is young professionals.',
                                   'ipa': '/ˌtɑː.ɡɪt ˈɔː.di.əns/',
                                   'meaning': 'đối tượng mục tiêu',
                                   'word': 'target audience'},
                               {   'example': 'The marketing campaign '
                                              'increased sales by 30 percent.',
                                   'ipa': '/kæmˈpeɪn/',
                                   'meaning': 'chiến dịch',
                                   'word': 'campaign'},
                               {   'example': 'Good branding helps customers '
                                              'remember your company.',
                                   'ipa': '/ˈbræn.dɪŋ/',
                                   'meaning': 'xây dựng thương hiệu',
                                   'word': 'branding'},
                               {   'example': 'We use analytics to track how '
                                              'visitors use our website.',
                                   'ipa': '/ˌæn.əˈlɪt.ɪks/',
                                   'meaning': 'phân tích dữ liệu',
                                   'word': 'analytics'},
                               {   'example': 'The conversion rate improved '
                                              'after we redesigned the landing '
                                              'page.',
                                   'ipa': '/kənˈvɜː.ʃən/',
                                   'meaning': 'chuyển đổi (khách thành người '
                                              'mua)',
                                   'word': 'conversion'},
                               {   'example': 'Social media engagement is '
                                              'higher when we post videos.',
                                   'ipa': '/ɪnˈɡeɪdʒ.mənt/',
                                   'meaning': 'mức độ tương tác',
                                   'word': 'engagement'},
                               {   'example': 'The brand partnered with an '
                                              'influencer to promote its new '
                                              'collection.',
                                   'ipa': '/ˈɪn.flu.ən.sər/',
                                   'meaning': 'người có ảnh hưởng',
                                   'word': 'influencer'},
                               {   'example': 'Content marketing focuses on '
                                              'creating valuable articles and '
                                              'videos for customers.',
                                   'ipa': '/ˌkɒn.tent ˈmɑː.kɪ.tɪŋ/',
                                   'meaning': 'tiếp thị nội dung',
                                   'word': 'content marketing'},
                               {   'example': 'We should focus our ads on '
                                              'potential customers in their '
                                              'twenties.',
                                   'ipa': '/pəˈten.ʃəl ˈkʌs.tə.mər/',
                                   'meaning': 'khách hàng tiềm năng',
                                   'word': 'potential customer'},
                               {   'example': 'The government launched a drive '
                                              'to encourage recycling.',
                                   'ipa': '/draɪv/',
                                   'meaning': 'chiến dịch lớn, cuộc vận động',
                                   'word': 'drive'},
                               {   'example': 'A strong corporate identity '
                                              'builds trust with clients.',
                                   'ipa': '/aɪˈden.tə.ti/',
                                   'meaning': 'nhận diện, danh tính thương '
                                              'hiệu',
                                   'word': 'identity'},
                               {   'example': 'Official statistics show a rise '
                                              'in local tourism.',
                                   'ipa': '/stəˈtɪs.tɪks/',
                                   'meaning': 'số liệu thống kê',
                                   'word': 'statistics'},
                               {   'example': 'The acquisition of new clients '
                                              'is crucial for business growth.',
                                   'ipa': '/ˌæk.wɪˈzɪʃ.ən/',
                                   'meaning': 'sự thu hút, thu nhận khách hàng',
                                   'word': 'acquisition'},
                               {   'example': 'The classroom activities '
                                              'encourage interaction among '
                                              'students.',
                                   'ipa': '/ˌɪn.təˈræk.ʃən/',
                                   'meaning': 'sự tương tác qua lại',
                                   'word': 'interaction'},
                               {   'example': 'The movie star became an '
                                              'international celebrity.',
                                   'ipa': '/səˈleb.rə.ti/',
                                   'meaning': 'người nổi tiếng',
                                   'word': 'celebrity'},
                               {   'example': 'Direct marketing involves '
                                              'sending emails or flyers '
                                              'straight to customers.',
                                   'ipa': '/daɪˈrekt ˈmɑː.kɪ.tɪŋ/',
                                   'meaning': 'tiếp thị trực tiếp',
                                   'word': 'direct marketing'},
                               {   'example': 'Apple has enormous brand '
                                              'equity.',
                                   'ipa': '/brænd ˈɛk.wɪ.ti/',
                                   'meaning': 'giá trị thương hiệu xây dựng '
                                              'theo thời gian',
                                   'word': 'brand equity'},
                               {   'example': 'Good SEO increases organic '
                                              'traffic.',
                                   'ipa': '/ˌɛs.iːˈoʊ/',
                                   'meaning': 'tối ưu hóa công cụ tìm kiếm',
                                   'word': 'SEO'},
                               {   'example': 'SEM includes paid search '
                                              'advertising.',
                                   'ipa': '/ˌɛs.iːˈɛm/',
                                   'meaning': 'tiếp thị trên công cụ tìm kiếm '
                                              'trả tiền',
                                   'word': 'SEM'},
                               {   'example': 'PPC campaigns drive immediate '
                                              'traffic.',
                                   'ipa': '/ˌpiː.piːˈsiː/',
                                   'meaning': 'trả tiền mỗi lần nhấp chuột '
                                              'quảng cáo',
                                   'word': 'PPC'},
                               {   'example': 'Calculate the ROI of each '
                                              'campaign.',
                                   'ipa': '/ˌɑːr.oʊˈaɪ/',
                                   'meaning': 'tỷ suất hoàn vốn đầu tư '
                                              'marketing',
                                   'word': 'ROI'},
                               {   'example': 'Set clear KPIs for each '
                                              'campaign.',
                                   'ipa': '/ˌkeɪ.piːˈaɪ/',
                                   'meaning': 'chỉ số hiệu suất chính cần theo '
                                              'dõi',
                                   'word': 'KPI'},
                               {   'example': 'Attribution shows which channel '
                                              'converts.',
                                   'ipa': '/ˌæt.rɪˈbjuː.ʃən/',
                                   'meaning': 'quy kết nguồn gốc chuyển đổi '
                                              'khách hàng',
                                   'word': 'attribution'},
                               {   'example': 'An omnichannel approach ensures '
                                              'consistency.',
                                   'ipa': '/ˌɒm.niˈtʃæn.əl/',
                                   'meaning': 'tiếp thị đa kênh liền mạch',
                                   'word': 'omnichannel'},
                               {   'example': 'Run A/B tests on your landing '
                                              'pages.',
                                   'ipa': '/ˌeɪ.biː ˈtɛs.tɪŋ/',
                                   'meaning': 'thử nghiệm so sánh hai phiên '
                                              'bản',
                                   'word': 'A/B testing'},
                               {   'example': 'Create a buyer persona for each '
                                              'segment.',
                                   'ipa': '/pərˈsoʊ.nə/',
                                   'meaning': 'chân dung khách hàng mục tiêu',
                                   'word': 'persona'},
                               {   'example': 'Map the customer journey from '
                                              'awareness to purchase.',
                                   'ipa': '/ˈkʌs.tə.mər ˈdʒɜːr.ni/',
                                   'meaning': 'hành trình trải nghiệm của '
                                              'khách hàng',
                                   'word': 'customer journey'},
                               {   'example': 'Every touchpoint shapes brand '
                                              'perception.',
                                   'ipa': '/ˈtʌtʃ.pɔɪnt/',
                                   'meaning': 'điểm tiếp xúc giữa thương hiệu '
                                              'và khách',
                                   'word': 'touchpoint'},
                               {   'example': 'High churn rate hurts revenue.',
                                   'ipa': '/tʃɜːrn reɪt/',
                                   'meaning': 'tỷ lệ khách hàng ngừng sử dụng '
                                              'dịch vụ',
                                   'word': 'churn rate'},
                               {   'example': 'CLV determines how much to '
                                              'spend on acquisition.',
                                   'ipa': '/ˈkʌs.tə.mər ˈlaɪf.taɪm ˈvæl.juː/',
                                   'meaning': 'giá trị vòng đời của một khách '
                                              'hàng',
                                   'word': 'customer lifetime value'},
                               {   'example': 'Reduce cost per acquisition '
                                              'with better targeting.',
                                   'ipa': '/kɒst pɜːr ˌæk.wɪˈzɪʃ.ən/',
                                   'meaning': 'chi phí để có một khách hàng '
                                              'mới',
                                   'word': 'cost per acquisition'},
                               {   'example': 'The celebrity became our brand '
                                              'ambassador.',
                                   'ipa': '/brænd æmˈbæs.ə.dər/',
                                   'meaning': 'đại sứ thương hiệu đại diện '
                                              'truyền thông',
                                   'word': 'brand ambassador'},
                               {   'example': 'User-generated content builds '
                                              'authenticity.',
                                   'ipa': '/ˈjuː.zər ˈdʒɛn.ər.eɪ.tɪd '
                                          'ˈkɒn.tɛnt/',
                                   'meaning': 'nội dung do người dùng tự tạo',
                                   'word': 'user-generated content'},
                               {   'example': 'Growth hacking tests '
                                              'unconventional tactics.',
                                   'ipa': '/ɡroʊθ ˈhæk.ɪŋ/',
                                   'meaning': 'tăng trưởng nhanh qua thử '
                                              'nghiệm sáng tạo',
                                   'word': 'growth hacking'},
                               {   'example': 'Define your go-to-market '
                                              'strategy.',
                                   'ipa': '/ˌɡoʊ.tʊˈmɑːr.kɪt ˈstræt.ɪ.dʒi/',
                                   'meaning': 'chiến lược đưa sản phẩm ra thị '
                                              'trường',
                                   'word': 'go-to-market strategy'},
                               {   'example': 'A freemium pricing strategy '
                                              'attracts users.',
                                   'ipa': '/ˈpraɪ.sɪŋ ˈstræt.ɪ.dʒi/',
                                   'meaning': 'chiến lược định giá sản phẩm',
                                   'word': 'pricing strategy'},
                               {   'example': 'Cross-selling increases order '
                                              'value.',
                                   'ipa': '/ˈkrɒs ˌsɛl.ɪŋ/',
                                   'meaning': 'bán chéo sản phẩm bổ sung cho '
                                              'nhau',
                                   'word': 'cross-selling'},
                               {   'example': 'Upselling moves customers to '
                                              'premium tiers.',
                                   'ipa': '/ˈʌp.sɛl.ɪŋ/',
                                   'meaning': 'nâng cấp lên sản phẩm cao cấp '
                                              'hơn',
                                   'word': 'upselling'},
                               {   'example': 'Spotify uses a freemium '
                                              'business model.',
                                   'ipa': '/ˈfriː.mi.əm/',
                                   'meaning': 'mô hình miễn phí cơ bản tính '
                                              'phí cao cấp',
                                   'word': 'freemium'},
                               {   'example': 'The subscription model ensures '
                                              'recurring revenue.',
                                   'ipa': '/səbˈskrɪp.ʃən ˈmɒd.əl/',
                                   'meaning': 'mô hình kinh doanh thu phí theo '
                                              'kỳ',
                                   'word': 'subscription model'},
                               {   'example': 'Pay-per-click ads appear in '
                                              'search results.',
                                   'ipa': '/peɪ pɜːr klɪk/',
                                   'meaning': 'trả tiền theo số lần nhấp quảng '
                                              'cáo',
                                   'word': 'pay-per-click'},
                               {   'example': 'High brand recall drives '
                                              'organic searches.',
                                   'ipa': '/brænd rɪˈkɔːl/',
                                   'meaning': 'khả năng nhớ lại thương hiệu tự '
                                              'phát',
                                   'word': 'brand recall'},
                               {   'example': 'Increase share of wallet with '
                                              'loyalty programs.',
                                   'ipa': '/ʃɛər əv ˈwɒl.ɪt/',
                                   'meaning': 'tỷ lệ chi tiêu của khách dành '
                                              'cho thương hiệu',
                                   'word': 'share of wallet'},
                               {   'example': 'Customer advocacy is earned '
                                              'through experience.',
                                   'ipa': '/ˈkʌs.tə.mər ˈæd.və.kə.si/',
                                   'meaning': 'vận động bởi khách hàng trung '
                                              'thành',
                                   'word': 'customer advocacy'},
                               {   'example': 'Plan a Christmas seasonal '
                                              'campaign.',
                                   'ipa': '/ˈsiː.zən.əl kæmˈpeɪn/',
                                   'meaning': 'chiến dịch theo mùa vụ',
                                   'word': 'seasonal campaign'},
                               {   'example': 'Balance reach and frequency in '
                                              'media buying.',
                                   'ipa': '/riːtʃ ænd ˈfriː.kwən.si/',
                                   'meaning': 'tầm với và tần suất tiếp cận '
                                              'quảng cáo',
                                   'word': 'reach and frequency'},
                               {   'example': 'Media planning maximizes ad '
                                              'effectiveness.',
                                   'ipa': '/ˈmiː.di.ə ˈplæn.ɪŋ/',
                                   'meaning': 'lập kế hoạch truyền thông phân '
                                              'bổ ngân sách',
                                   'word': 'media planning'},
                               {   'example': 'Follow brand guidelines for all '
                                              'materials.',
                                   'ipa': '/brænd ˈɡaɪd.laɪn/',
                                   'meaning': 'hướng dẫn thương hiệu về hình '
                                              'ảnh nhất quán',
                                   'word': 'brand guideline'},
                               {   'example': 'Use a content calendar to plan '
                                              'posts.',
                                   'ipa': '/ˈkɒn.tɛnt ˈkæl.ɪn.dər/',
                                   'meaning': 'lịch đăng nội dung theo kế '
                                              'hoạch',
                                   'word': 'content calendar'},
                               {   'example': 'Launch a brand loyalty program.',
                                   'ipa': '/brænd ˈlɔɪ.əl.ti ˈproʊ.ɡræm/',
                                   'meaning': 'chương trình khách hàng trung '
                                              'thành',
                                   'word': 'brand loyalty program'}],
                     'B2': [   {   'example': 'IMC ensures a consistent brand '
                                              'message.',
                                   'ipa': '/ˈɪn.tɪ.ɡreɪ.tɪd ˈmɑːr.kɪ.tɪŋ '
                                          'kəˌmjuː.nɪˈkeɪ.ʃənz/',
                                   'meaning': 'truyền thông tiếp thị tích hợp '
                                              'đồng nhất',
                                   'word': 'integrated marketing '
                                           'communications'},
                               {   'example': 'Programmatic advertising '
                                              'automates ad buying.',
                                   'ipa': '/ˌproʊ.ɡrəˈmæt.ɪk ˈæd.vər.taɪ.zɪŋ/',
                                   'meaning': 'quảng cáo tự động hóa theo '
                                              'thuật toán',
                                   'word': 'programmatic advertising'},
                               {   'example': 'A DSP manages programmatic ad '
                                              'buying.',
                                   'ipa': '/dɪˈmænd saɪd ˈplæt.fɔːrm/',
                                   'meaning': 'nền tảng phía cầu quản lý quảng '
                                              'cáo tự động',
                                   'word': 'demand-side platform'},
                               {   'example': 'Publishers use an SSP to sell '
                                              'ad space.',
                                   'ipa': '/səˈplaɪ saɪd ˈplæt.fɔːrm/',
                                   'meaning': 'nền tảng phía cung bán không '
                                              'gian quảng cáo',
                                   'word': 'supply-side platform'},
                               {   'example': 'Data-driven marketing improves '
                                              'targeting.',
                                   'ipa': '/ˈdeɪ.tə ˈdrɪv.ən ˈmɑːr.kɪ.tɪŋ/',
                                   'meaning': 'tiếp thị dựa trên phân tích dữ '
                                              'liệu',
                                   'word': 'data-driven marketing'},
                               {   'example': 'Predictive analytics forecasts '
                                              'customer behavior.',
                                   'ipa': '/prɪˈdɪk.tɪv ˌæn.əˈlɪt.ɪks/',
                                   'meaning': 'phân tích dự đoán hành vi khách '
                                              'hàng',
                                   'word': 'predictive analytics'},
                               {   'example': 'A CDP unifies all customer data '
                                              'sources.',
                                   'ipa': '/ˈkʌs.tə.mər ˈdeɪ.tə ˈplæt.fɔːrm/',
                                   'meaning': 'nền tảng dữ liệu khách hàng tập '
                                              'trung',
                                   'word': 'customer data platform'},
                               {   'example': 'Use CRM to track customer '
                                              'interactions.',
                                   'ipa': '/ˌsiː.ɑːrˈɛm/',
                                   'meaning': 'quản lý quan hệ khách hàng',
                                   'word': 'CRM'},
                               {   'example': 'Marketing automation nurtures '
                                              'leads.',
                                   'ipa': '/ˈmɑːr.kɪ.tɪŋ ˌɔː.tə.ˈmeɪ.ʃən/',
                                   'meaning': 'tự động hóa quy trình tiếp thị',
                                   'word': 'marketing automation'},
                               {   'example': 'Lead nurturing moves prospects '
                                              'to purchase.',
                                   'ipa': '/liːd ˈnɜːr.tʃər.ɪŋ/',
                                   'meaning': 'chăm sóc khách tiềm năng theo '
                                              'thời gian',
                                   'word': 'lead nurturing'},
                               {   'example': 'Psychographic segmentation '
                                              'targets values.',
                                   'ipa': '/ˌsaɪ.kəˈɡræf.ɪk/',
                                   'meaning': 'phân khúc theo tâm lý và lối '
                                              'sống',
                                   'word': 'psychographic'},
                               {   'example': 'Track NPS to measure customer '
                                              'loyalty.',
                                   'ipa': '/nɛt prəˈmoʊ.tər skɔːr/',
                                   'meaning': 'điểm số khuyến nghị thương hiệu '
                                              'từ khách',
                                   'word': 'net promoter score'},
                               {   'example': 'Monitor brand perception '
                                              'regularly.',
                                   'ipa': '/brænd pərˈsɛp.ʃən/',
                                   'meaning': 'nhận thức của công chúng về '
                                              'thương hiệu',
                                   'word': 'brand perception'},
                               {   'example': 'Sentiment monitoring alerts you '
                                              'to crises.',
                                   'ipa': '/ˈsɛn.tɪ.mənt ˈmɒn.ɪ.tər.ɪŋ/',
                                   'meaning': 'theo dõi cảm xúc công chúng về '
                                              'thương hiệu',
                                   'word': 'sentiment monitoring'},
                               {   'example': 'Increase share of voice in the '
                                              'market.',
                                   'ipa': '/ʃɛər əv vɔɪs/',
                                   'meaning': 'thị phần tiếng nói trong ngành '
                                              'so với đối thủ',
                                   'word': 'share of voice'},
                               {   'example': 'Media mix modeling optimizes '
                                              'budget.',
                                   'ipa': '/ˈmiː.di.ə mɪks ˈmɒd.əl.ɪŋ/',
                                   'meaning': 'mô hình hóa tổ hợp kênh truyền '
                                              'thông',
                                   'word': 'media mix modeling'},
                               {   'example': 'Multivariate testing tests '
                                              'multiple elements.',
                                   'ipa': '/ˌmʌl.tɪˈvɛər.i.ɪt ˈtɛs.tɪŋ/',
                                   'meaning': 'thử nghiệm đa biến tối ưu hóa '
                                              'trang',
                                   'word': 'multivariate testing'},
                               {   'example': 'Cohort analysis tracks user '
                                              'retention.',
                                   'ipa': '/ˈkoʊ.hɔːrt əˈnæl.ɪ.sɪs/',
                                   'meaning': 'phân tích nhóm người dùng theo '
                                              'thời gian',
                                   'word': 'cohort analysis'},
                               {   'example': 'Attribution modeling credits '
                                              'the right channels.',
                                   'ipa': '/ˌæt.rɪˈbjuː.ʃən ˈmɒd.əl.ɪŋ/',
                                   'meaning': 'mô hình hóa quy kết giá trị '
                                              'chuyển đổi',
                                   'word': 'attribution modeling'},
                               {   'example': 'Inbound marketing draws '
                                              'customers in.',
                                   'ipa': '/ˈɪn.baʊnd ˈmɑːr.kɪ.tɪŋ/',
                                   'meaning': 'tiếp thị thu hút khách tự nhiên '
                                              'vào',
                                   'word': 'inbound marketing'},
                               {   'example': 'Outbound marketing includes '
                                              'cold calling.',
                                   'ipa': '/ˈaʊt.baʊnd ˈmɑːr.kɪ.tɪŋ/',
                                   'meaning': 'tiếp thị chủ động tiếp cận '
                                              'khách hàng',
                                   'word': 'outbound marketing'},
                               {   'example': 'ABM targets high-value accounts '
                                              'directly.',
                                   'ipa': '/əˈkaʊnt beɪst ˈmɑːr.kɪ.tɪŋ/',
                                   'meaning': 'tiếp thị tập trung vào khách '
                                              'hàng lớn',
                                   'word': 'account-based marketing'},
                               {   'example': 'Gather competitive intelligence '
                                              'regularly.',
                                   'ipa': '/kəmˈpɛt.ɪ.tɪv ɪnˈtɛl.ɪ.dʒəns/',
                                   'meaning': 'tình báo cạnh tranh phân tích '
                                              'đối thủ',
                                   'word': 'competitive intelligence'},
                               {   'example': 'Conduct a SWOT analysis before '
                                              'planning.',
                                   'ipa': '/swɒt əˈnæl.ɪ.sɪs/',
                                   'meaning': 'phân tích điểm mạnh yếu cơ hội '
                                              'thách thức',
                                   'word': 'SWOT analysis'},
                               {   'example': 'Brand extension leverages '
                                              'existing equity.',
                                   'ipa': '/brænd ɪkˈstɛn.ʃən/',
                                   'meaning': 'mở rộng thương hiệu sang danh '
                                              'mục mới',
                                   'word': 'brand extension'},
                               {   'example': 'Co-marketing expands audience '
                                              'reach.',
                                   'ipa': '/ˌkoʊˈmɑːr.kɪ.tɪŋ/',
                                   'meaning': 'hợp tác tiếp thị cùng thương '
                                              'hiệu khác',
                                   'word': 'co-marketing'},
                               {   'example': 'Cause marketing aligns brands '
                                              'with values.',
                                   'ipa': '/kɔːz ˈmɑːr.kɪ.tɪŋ/',
                                   'meaning': 'tiếp thị gắn liền với mục tiêu '
                                              'xã hội',
                                   'word': 'cause marketing'},
                               {   'example': 'Neuromarketing uses brain '
                                              'science in ads.',
                                   'ipa': '/ˌnjʊər.oʊˈmɑːr.kɪ.tɪŋ/',
                                   'meaning': 'tiếp thị dựa trên khoa học thần '
                                              'kinh',
                                   'word': 'neuromarketing'},
                               {   'example': 'Understand price elasticity '
                                              'before discounting.',
                                   'ipa': '/praɪs ˌɪ.læsˈtɪs.ɪ.ti/',
                                   'meaning': 'độ co giãn giá cầu của sản phẩm',
                                   'word': 'price elasticity'},
                               {   'example': 'Achieve product-market fit '
                                              'before scaling.',
                                   'ipa': '/ˈprɒd.ʌkt ˈmɑːr.kɪt fɪt/',
                                   'meaning': 'sự phù hợp giữa sản phẩm và thị '
                                              'trường',
                                   'word': 'product-market fit'},
                               {   'example': 'Launch an MVP before full '
                                              'development.',
                                   'ipa': '/ˈmɪn.ɪ.məm ˈvaɪ.ə.bəl ˈprɒd.ʌkt/',
                                   'meaning': 'sản phẩm khả dụng tối thiểu để '
                                              'test',
                                   'word': 'minimum viable product'},
                               {   'example': 'The startup pivoted to a new '
                                              'market.',
                                   'ipa': '/ˈpɪv.ɪt/',
                                   'meaning': 'thay đổi hướng chiến lược kinh '
                                              'doanh',
                                   'word': 'pivot'},
                               {   'example': 'Airlines use dynamic pricing '
                                              'models.',
                                   'ipa': '/daɪˈnæm.ɪk ˈpraɪ.sɪŋ/',
                                   'meaning': 'định giá động thay đổi theo cầu',
                                   'word': 'dynamic pricing'},
                               {   'example': 'Hotels use yield management for '
                                              'pricing.',
                                   'ipa': '/jiːld ˈmæn.ɪdʒ.mənt/',
                                   'meaning': 'quản lý doanh thu theo thời '
                                              'điểm',
                                   'word': 'yield management'},
                               {   'example': 'Over-licensing causes brand '
                                              'dilution.',
                                   'ipa': '/brænd daɪˈluː.ʃən/',
                                   'meaning': 'pha loãng thương hiệu khi mở '
                                              'rộng quá mức',
                                   'word': 'brand dilution'},
                               {   'example': 'Market skimming targets early '
                                              'adopters.',
                                   'ipa': '/ˈmɑːr.kɪt ˈskɪm.ɪŋ/',
                                   'meaning': 'định giá hớt váng thị trường '
                                              'cao ban đầu',
                                   'word': 'market skimming'},
                               {   'example': 'Penetration pricing builds '
                                              'market share fast.',
                                   'ipa': '/ˌpɛn.ɪˈtreɪ.ʃən ˈpraɪ.sɪŋ/',
                                   'meaning': 'định giá thâm nhập thấp thu hút '
                                              'khách',
                                   'word': 'penetration pricing'},
                               {   'example': 'Anchor pricing uses a high '
                                              'reference price.',
                                   'ipa': '/ˈæŋ.kər ˈpraɪ.sɪŋ/',
                                   'meaning': 'định giá mỏ neo tâm lý so sánh',
                                   'word': 'anchor pricing'},
                               {   'example': 'The decoy effect nudges buyers '
                                              'to premium.',
                                   'ipa': '/ˈdiː.kɔɪ ɪˈfɛkt/',
                                   'meaning': 'hiệu ứng mồi nhử lựa chọn tâm '
                                              'lý',
                                   'word': 'decoy effect'},
                               {   'example': 'Scarcity marketing creates '
                                              'urgency.',
                                   'ipa': '/ˈskeər.sɪ.ti ˈmɑːr.kɪ.tɪŋ/',
                                   'meaning': 'tiếp thị khan hiếm tạo cảm giác '
                                              'cấp bách',
                                   'word': 'scarcity marketing'},
                               {   'example': 'Loss aversion drives insurance '
                                              'purchases.',
                                   'ipa': '/lɒs əˈvɜːr.ʒən/',
                                   'meaning': 'tâm lý né tránh thua lỗ hơn '
                                              'kiếm lời',
                                   'word': 'loss aversion'},
                               {   'example': 'Reciprocity principle drives '
                                              'free samples.',
                                   'ipa': '/ˌrɛs.ɪˈprɒs.ɪ.ti ˈprɪn.sɪ.pəl/',
                                   'meaning': 'nguyên tắc có đi có lại trong '
                                              'tiếp thị',
                                   'word': 'reciprocity principle'},
                               {   'example': 'Build social capital through '
                                              'community.',
                                   'ipa': '/ˈsoʊ.ʃəl ˈkæp.ɪ.təl/',
                                   'meaning': 'vốn xã hội mạng lưới quan hệ '
                                              'thương hiệu',
                                   'word': 'social capital'},
                               {   'example': 'Omnichannel attribution is '
                                              'complex.',
                                   'ipa': '/ˌɒm.niˈtʃæn.əl ˌæt.rɪˈbjuː.ʃən/',
                                   'meaning': 'quy kết đa kênh xác định điểm '
                                              'chuyển đổi',
                                   'word': 'omnichannel attribution'},
                               {   'example': 'Brand salience drives '
                                              'top-of-mind awareness.',
                                   'ipa': '/brænd ˈseɪ.li.əns/',
                                   'meaning': 'tính nổi bật thương hiệu trong '
                                              'tâm trí',
                                   'word': 'brand salience'},
                               {   'example': 'Mental availability drives '
                                              'purchase frequency.',
                                   'ipa': '/ˈmɛn.təl əˌveɪ.lə.ˈbɪl.ɪ.ti/',
                                   'meaning': 'khả năng xuất hiện trong tâm '
                                              'trí mua hàng',
                                   'word': 'mental availability'},
                               {   'example': 'Physical availability ensures '
                                              'shelf presence.',
                                   'ipa': '/ˈfɪz.ɪ.kəl əˌveɪ.lə.ˈbɪl.ɪ.ti/',
                                   'meaning': 'khả năng tiếp cận sản phẩm tại '
                                              'điểm bán',
                                   'word': 'physical availability'},
                               {   'example': 'Logos are distinctive brand '
                                              'assets.',
                                   'ipa': '/dɪˈstɪŋk.tɪv ˈæs.ɛts/',
                                   'meaning': 'tài sản đặc trưng nhận diện '
                                              'thương hiệu',
                                   'word': 'distinctive assets'},
                               {   'example': 'Identify category entry points '
                                              'for campaigns.',
                                   'ipa': '/ˈkæt.ɪ.ɡər.i ˈɛn.tri pɔɪnt/',
                                   'meaning': 'điểm vào danh mục khi khách bắt '
                                              'đầu mua',
                                   'word': 'category entry point'},
                               {   'example': 'Measure advertising '
                                              'effectiveness with sales lift.',
                                   'ipa': '/ˈæd.vər.taɪ.zɪŋ ɪˈfɛk.tɪv.nɪs/',
                                   'meaning': 'hiệu quả của hoạt động quảng '
                                              'cáo',
                                   'word': 'advertising effectiveness'}],
                     'C1': [   {   'example': 'Brand architecture organizes a '
                                              'portfolio of brands.',
                                   'ipa': '/brænd ˈɑːr.kɪ.tɛk.tʃər/',
                                   'meaning': 'kiến trúc danh mục thương hiệu '
                                              'tổng thể',
                                   'word': 'brand architecture'},
                               {   'example': 'A clear positioning strategy '
                                              'differentiates the brand.',
                                   'ipa': '/pəˈzɪʃ.ən.ɪŋ ˈstræt.ɪ.dʒi/',
                                   'meaning': 'chiến lược định vị thương hiệu '
                                              'cạnh tranh',
                                   'word': 'positioning strategy'},
                               {   'example': 'A strong brand is a competitive '
                                              'moat.',
                                   'ipa': '/kəmˈpɛt.ɪ.tɪv moʊt/',
                                   'meaning': 'hào cạnh tranh bảo vệ lợi thế '
                                              'bền vững',
                                   'word': 'competitive moat'},
                               {   'example': 'Market saturation forces '
                                              'innovation.',
                                   'ipa': '/ˈmɑːr.kɪt ˌsætʃ.ʊˈreɪ.ʃən/',
                                   'meaning': 'thị trường bão hòa khó tăng '
                                              'trưởng thêm',
                                   'word': 'market saturation'},
                               {   'example': 'Blue ocean strategy creates '
                                              'uncontested markets.',
                                   'ipa': '/bluː ˈoʊ.ʃən ˈstræt.ɪ.dʒi/',
                                   'meaning': 'chiến lược đại dương xanh tạo '
                                              'thị trường mới',
                                   'word': 'blue ocean strategy'},
                               {   'example': 'Disruptive marketing challenges '
                                              'the status quo.',
                                   'ipa': '/dɪsˈrʌp.tɪv ˈmɑːr.kɪ.tɪŋ/',
                                   'meaning': 'tiếp thị đột phá thay đổi quy '
                                              'tắc ngành',
                                   'word': 'disruptive marketing'},
                               {   'example': 'Hyper-personalization uses AI '
                                              'for individual targeting.',
                                   'ipa': '/ˌhaɪ.pər.ˌpɜːr.sən.ə.laɪˈzeɪ.ʃən/',
                                   'meaning': 'cá nhân hóa siêu chi tiết theo '
                                              'từng người',
                                   'word': 'hyper-personalization'},
                               {   'example': 'Dark social includes WhatsApp '
                                              'shares.',
                                   'ipa': '/dɑːrk ˈsoʊ.ʃəl/',
                                   'meaning': 'chia sẻ riêng tư không theo dõi '
                                              'được',
                                   'word': 'dark social'},
                               {   'example': 'First-party data is more '
                                              'valuable after cookies end.',
                                   'ipa': '/fɜːrst ˈpɑːr.ti ˈdeɪ.tə/',
                                   'meaning': 'dữ liệu bên thứ nhất từ khách '
                                              'hàng trực tiếp',
                                   'word': 'first-party data'},
                               {   'example': 'Zero-party data comes from '
                                              'preference centers.',
                                   'ipa': '/ˈzɪər.oʊ ˈpɑːr.ti ˈdeɪ.tə/',
                                   'meaning': 'dữ liệu chủ động chia sẻ bởi '
                                              'khách hàng',
                                   'word': 'zero-party data'},
                               {   'example': 'Prepare for a cookieless future '
                                              'now.',
                                   'ipa': '/ˈkʊk.i.lɪs ˈfjuː.tʃər/',
                                   'meaning': 'tương lai tiếp thị không dùng '
                                              'cookie',
                                   'word': 'cookieless future'},
                               {   'example': 'Intent data identifies '
                                              'in-market buyers.',
                                   'ipa': '/ɪnˈtɛnt ˈdeɪ.tə/',
                                   'meaning': 'dữ liệu ý định mua hàng sắp tới',
                                   'word': 'intent data'},
                               {   'example': 'Privacy-first marketing builds '
                                              'trust.',
                                   'ipa': '/ˈprɪv.ə.si fɜːrst ˈmɑːr.kɪ.tɪŋ/',
                                   'meaning': 'tiếp thị ưu tiên bảo vệ quyền '
                                              'riêng tư',
                                   'word': 'privacy-first marketing'},
                               {   'example': 'Contextual advertising replaces '
                                              'behavioral tracking.',
                                   'ipa': '/kənˈtɛks.tʃʊ.əl ˈæd.vər.taɪ.zɪŋ/',
                                   'meaning': 'quảng cáo theo bối cảnh nội '
                                              'dung trang',
                                   'word': 'contextual advertising'},
                               {   'example': 'Emotional branding creates deep '
                                              'loyalty.',
                                   'ipa': '/ɪˈmoʊ.ʃən.əl ˈbrænd.ɪŋ/',
                                   'meaning': 'xây dựng thương hiệu kết nối '
                                              'cảm xúc',
                                   'word': 'emotional branding'},
                               {   'example': 'Brand storytelling connects on '
                                              'a human level.',
                                   'ipa': '/brænd ˈstɔːr.i.tɛl.ɪŋ/',
                                   'meaning': 'kể chuyện thương hiệu hấp dẫn '
                                              'nhân văn',
                                   'word': 'brand storytelling'},
                               {   'example': 'Transmedia marketing spans '
                                              'multiple platforms.',
                                   'ipa': '/trænsˈmiː.di.ə ˈmɑːr.kɪ.tɪŋ/',
                                   'meaning': 'tiếp thị đa phương tiện kể '
                                              'chuyện liên kết',
                                   'word': 'transmedia marketing'},
                               {   'example': 'Conversational marketing uses '
                                              'chatbots for engagement.',
                                   'ipa': '/ˌkɒn.vəˈseɪ.ʃən.əl ˈmɑːr.kɪ.tɪŋ/',
                                   'meaning': 'tiếp thị đối thoại tương tác '
                                              'thời gian thực',
                                   'word': 'conversational marketing'},
                               {   'example': 'A purpose-driven brand attracts '
                                              'loyal customers.',
                                   'ipa': '/ˈpɜːr.pəs ˈdrɪv.ən brænd/',
                                   'meaning': 'thương hiệu có mục đích sứ mệnh '
                                              'xã hội',
                                   'word': 'purpose-driven brand'},
                               {   'example': 'Brand activism requires '
                                              'authenticity.',
                                   'ipa': '/brænd ˈæk.tɪ.vɪzm/',
                                   'meaning': 'thương hiệu dũng cảm lên tiếng '
                                              'vấn đề xã hội',
                                   'word': 'brand activism'},
                               {   'example': 'Performance marketing pays for '
                                              'results only.',
                                   'ipa': '/pərˈfɔːr.məns ˈmɑːr.kɪ.tɪŋ/',
                                   'meaning': 'tiếp thị dựa trên kết quả đo '
                                              'lường được',
                                   'word': 'performance marketing'},
                               {   'example': 'Growth marketing optimizes the '
                                              'full funnel.',
                                   'ipa': '/ɡroʊθ ˈmɑːr.kɪ.tɪŋ/',
                                   'meaning': 'tiếp thị tăng trưởng tập trung '
                                              'số liệu',
                                   'word': 'growth marketing'},
                               {   'example': 'Ecosystem marketing leverages '
                                              'partner networks.',
                                   'ipa': '/ˈiː.kəʊ.sɪs.təm ˈmɑːr.kɪ.tɪŋ/',
                                   'meaning': 'tiếp thị hệ sinh thái đối tác '
                                              'liên kết',
                                   'word': 'ecosystem marketing'},
                               {   'example': 'Community-led growth turns '
                                              'users into advocates.',
                                   'ipa': '/kəˈmjuː.nɪ.ti lɛd ɡroʊθ/',
                                   'meaning': 'tăng trưởng dẫn dắt bởi cộng '
                                              'đồng người dùng',
                                   'word': 'community-led growth'},
                               {   'example': 'Slack achieved product-led '
                                              'growth.',
                                   'ipa': '/ˈprɒd.ʌkt lɛd ɡroʊθ/',
                                   'meaning': 'tăng trưởng dẫn dắt bởi chính '
                                              'sản phẩm',
                                   'word': 'product-led growth'},
                               {   'example': 'Optimize for voice search as AI '
                                              'assistants grow.',
                                   'ipa': '/vɔɪs sɜːrtʃ ˌɒp.tɪ.maɪˈzeɪ.ʃən/',
                                   'meaning': 'tối ưu hóa tìm kiếm bằng giọng '
                                              'nói',
                                   'word': 'voice search optimization'},
                               {   'example': 'AR marketing lets customers try '
                                              'products virtually.',
                                   'ipa': '/ˌɔːɡ.mɛn.tɪd rɪˈæl.ɪ.ti '
                                          'ˈmɑːr.kɪ.tɪŋ/',
                                   'meaning': 'tiếp thị qua công nghệ thực tế '
                                              'tăng cường',
                                   'word': 'augmented reality marketing'},
                               {   'example': 'Brands experiment with '
                                              'metaverse marketing.',
                                   'ipa': '/ˈmɛt.ə.vɜːrs ˈmɑːr.kɪ.tɪŋ/',
                                   'meaning': 'tiếp thị trong thế giới ảo '
                                              'metaverse',
                                   'word': 'metaverse marketing'},
                               {   'example': 'DCO personalizes ads at scale.',
                                   'ipa': '/daɪˈnæm.ɪk kriːˈeɪ.tɪv '
                                          'ˌɒp.tɪ.maɪˈzeɪ.ʃən/',
                                   'meaning': 'tối ưu hóa sáng tạo quảng cáo '
                                              'tự động',
                                   'word': 'dynamic creative optimization'},
                               {   'example': 'Google and Meta are walled '
                                              'gardens.',
                                   'ipa': '/wɔːld ˈɡɑːr.dən/',
                                   'meaning': 'hệ sinh thái đóng kiểm soát dữ '
                                              'liệu',
                                   'word': 'walled garden'},
                               {   'example': 'Incrementality testing measures '
                                              'true ad impact.',
                                   'ipa': '/ˌɪŋ.krɪˈmɛnt.əl.ɪ.ti ˈtɛs.tɪŋ/',
                                   'meaning': 'kiểm tra tác động gia tăng thực '
                                              'sự của quảng cáo',
                                   'word': 'incrementality testing'},
                               {   'example': 'Unified measurement solves '
                                              'multi-touch attribution.',
                                   'ipa': '/ˈjuː.nɪ.faɪd ˈmɛʒ.ər.mənt/',
                                   'meaning': 'đo lường thống nhất hiệu quả đa '
                                              'kênh',
                                   'word': 'unified measurement'},
                               {   'example': 'Semiotics informs brand symbol '
                                              'choices.',
                                   'ipa': '/ˌsiː.miˈɒt.ɪks/',
                                   'meaning': 'ký hiệu học nghiên cứu biểu '
                                              'tượng văn hóa',
                                   'word': 'semiotics'},
                               {   'example': 'Mythology marketing builds '
                                              'iconic brands.',
                                   'ipa': '/mɪˈθɒl.ə.dʒi ˈmɑːr.kɪ.tɪŋ/',
                                   'meaning': 'tiếp thị huyền thoại tạo câu '
                                              'chuyện thương hiệu',
                                   'word': 'mythology marketing'},
                               {   'example': 'Postmodern branding embraces '
                                              'contradictions.',
                                   'ipa': '/ˌpoʊst.ˈmɒd.ən ˈbrænd.ɪŋ/',
                                   'meaning': 'thương hiệu hậu hiện đại đón '
                                              'nhận phức tạp',
                                   'word': 'postmodern branding'},
                               {   'example': 'Cultural branding connects with '
                                              'movements.',
                                   'ipa': '/ˈkʌl.tʃər.əl ˈbrænd.ɪŋ/',
                                   'meaning': 'xây dựng thương hiệu dựa trên '
                                              'văn hóa xã hội',
                                   'word': 'cultural branding'},
                               {   'example': 'Brand co-creation builds deep '
                                              'loyalty.',
                                   'ipa': '/brænd ˌkoʊ.kriˈeɪ.ʃən/',
                                   'meaning': 'đồng sáng tạo thương hiệu cùng '
                                              'người dùng',
                                   'word': 'brand co-creation'},
                               {   'example': 'Market orientation puts '
                                              'customers first.',
                                   'ipa': '/ˈmɑːr.kɪt ˌɔːr.i.ɛnˈteɪ.ʃən/',
                                   'meaning': 'định hướng thị trường trong '
                                              'toàn tổ chức',
                                   'word': 'market orientation'},
                               {   'example': 'Service dominant logic rethinks '
                                              'value creation.',
                                   'ipa': '/ˈsɜːr.vɪs ˈdɒm.ɪ.nənt ˈlɒdʒ.ɪk/',
                                   'meaning': 'logic ưu thế dịch vụ quan điểm '
                                              'giá trị mới',
                                   'word': 'service dominant logic'},
                               {   'example': 'Value cocreation involves '
                                              'customers in design.',
                                   'ipa': '/ˈvæl.juː ˌkoʊ.kriˈeɪ.ʃən/',
                                   'meaning': 'cùng tạo ra giá trị với khách '
                                              'hàng',
                                   'word': 'value cocreation'},
                               {   'example': 'Relationship marketing drives '
                                              'retention.',
                                   'ipa': '/rɪˈleɪ.ʃən.ʃɪp ˈmɑːr.kɪ.tɪŋ/',
                                   'meaning': 'tiếp thị quan hệ xây dựng dài '
                                              'hạn',
                                   'word': 'relationship marketing'},
                               {   'example': 'Experiential marketing creates '
                                              'lasting memories.',
                                   'ipa': '/ɪkˌspɪər.i.ˈɛn.ʃəl ˈmɑːr.kɪ.tɪŋ/',
                                   'meaning': 'tiếp thị trải nghiệm tạo ký ức '
                                              'cảm xúc',
                                   'word': 'experiential marketing'},
                               {   'example': 'Sensory marketing uses scent '
                                              'and sound.',
                                   'ipa': '/ˈsɛn.sər.i ˈmɑːr.kɪ.tɪŋ/',
                                   'meaning': 'tiếp thị giác quan kích thích '
                                              'các giác quan',
                                   'word': 'sensory marketing'},
                               {   'example': 'Ambient marketing places ads in '
                                              'unexpected places.',
                                   'ipa': '/ˈæm.bi.ənt ˈmɑːr.kɪ.tɪŋ/',
                                   'meaning': 'tiếp thị xung quanh môi trường '
                                              'hàng ngày',
                                   'word': 'ambient marketing'},
                               {   'example': 'DOOH combines outdoor with '
                                              'digital targeting.',
                                   'ipa': '/ˈdɪdʒ.ɪ.təl ˈaʊt əv hoʊm/',
                                   'meaning': 'quảng cáo kỹ thuật số ngoài '
                                              'trời màn hình lớn',
                                   'word': 'digital out-of-home'},
                               {   'example': 'CTV advertising targets '
                                              'streaming audiences.',
                                   'ipa': '/kəˈnɛk.tɪd tiː.viː '
                                          'ˈæd.vər.taɪ.zɪŋ/',
                                   'meaning': 'quảng cáo TV kết nối internet',
                                   'word': 'connected TV advertising'},
                               {   'example': 'Audit influencers to detect '
                                              'influencer fraud.',
                                   'ipa': '/ˈɪn.flu.ən.sər frɔːd/',
                                   'meaning': 'gian lận người ảnh hưởng dùng '
                                              'follower ảo',
                                   'word': 'influencer fraud'},
                               {   'example': 'Avoid dark patterns in UX '
                                              'design.',
                                   'ipa': '/dɑːrk ˈpæt.ənz/',
                                   'meaning': 'thiết kế gian lận đánh lừa '
                                              'người dùng',
                                   'word': 'dark patterns'},
                               {   'example': 'Ethical consumption drives '
                                              'demand for sustainability.',
                                   'ipa': '/ˈɛθ.ɪ.kəl kənˈsʌmp.ʃən/',
                                   'meaning': 'tiêu dùng có đạo đức bền vững',
                                   'word': 'ethical consumption'},
                               {   'example': 'Green marketing appeals to '
                                              'eco-conscious buyers.',
                                   'ipa': '/ɡriːn ˈmɑːr.kɪ.tɪŋ/',
                                   'meaning': 'tiếp thị xanh thân thiện môi '
                                              'trường',
                                   'word': 'green marketing'}]},
    'music': {   'B1': [   {   'example': "Beethoven's Fifth Symphony is one "
                                          'of the most famous compositions in '
                                          'history.',
                               'ipa': '/ˈsɪm.fə.ni/',
                               'meaning': 'bản giao hưởng',
                               'word': 'symphony'},
                           {   'example': 'The young composer presented his '
                                          'first major composition at the '
                                          'music hall.',
                               'ipa': '/ˌkɒm.pəˈzɪʃ.ən/',
                               'meaning': 'tác phẩm âm nhạc',
                               'word': 'composition'},
                           {   'example': 'The singers harmonized beautifully '
                                          'throughout the entire performance.',
                               'ipa': '/ˈhɑː.mə.naɪz/',
                               'meaning': 'hòa âm',
                               'word': 'harmonize'},
                           {   'example': 'Jazz musicians often improvise '
                                          'solos based on the chord '
                                          'progression.',
                               'ipa': '/ˈɪm.prə.vaɪz/',
                               'meaning': 'ứng tấu, ngẫu hứng',
                               'word': 'improvise'},
                           {   'example': 'Many popular songs share the same '
                                          'four-chord progression.',
                               'ipa': '/kɔːd prəˈɡreʃ.ən/',
                               'meaning': 'tiến trình hợp âm',
                               'word': 'chord progression'},
                           {   'example': 'The conductor emphasized the '
                                          'dynamics, going from soft to '
                                          'powerful.',
                               'ipa': '/daɪˈnæm.ɪks/',
                               'meaning': 'sắc thái to nhỏ trong âm nhạc',
                               'word': 'dynamics'},
                           {   'example': 'Students practice scales daily to '
                                          'improve their technical skills.',
                               'ipa': '/skeɪl/',
                               'meaning': 'gam nhạc',
                               'word': 'scale'},
                           {   'example': 'Songs in a major key tend to sound '
                                          'happy and bright.',
                               'ipa': '/ˈmeɪ.dʒər kiː/',
                               'meaning': 'giọng trưởng',
                               'word': 'major key'},
                           {   'example': 'Pieces in a minor key often convey '
                                          'sadness or tension.',
                               'ipa': '/ˈmaɪ.nər kiː/',
                               'meaning': 'giọng thứ',
                               'word': 'minor key'},
                           {   'example': 'The string arrangement added depth '
                                          'and emotion to the song.',
                               'ipa': '/əˈreɪndʒ.mənt/',
                               'meaning': 'phần phối khí',
                               'word': 'arrangement'},
                           {   'example': 'Learning music notation allows '
                                          'musicians to read and write music.',
                               'ipa': '/ˈmjuː.zɪk nəʊˈteɪ.ʃən/',
                               'meaning': 'ký hiệu âm nhạc',
                               'word': 'music notation'},
                           {   'example': 'The countermelody played by the '
                                          'flute complemented the main theme.',
                               'ipa': '/ˌkaʊn.tərˈmel.ə.di/',
                               'meaning': 'giai điệu phụ đối',
                               'word': 'countermelody'},
                           {   'example': 'The use of syncopation gives the '
                                          'rhythm a surprising, off-beat feel.',
                               'ipa': '/ˌsɪŋ.kəˈpeɪ.ʃən/',
                               'meaning': 'đảo phách',
                               'word': 'syncopation'},
                           {   'example': 'The unexpected modulation to a new '
                                          'key created an exciting moment.',
                               'ipa': '/ˌmɒd.jʊˈleɪ.ʃən/',
                               'meaning': 'chuyển giọng',
                               'word': 'modulation'},
                           {   'example': 'The symphony ends with a dramatic '
                                          'coda that builds to a climax.',
                               'ipa': '/ˈkəʊ.də/',
                               'meaning': 'đoạn kết bài nhạc',
                               'word': 'coda'},
                           {   'example': 'She practiced singing intervals to '
                                          'improve her pitch accuracy.',
                               'ipa': '/ˈɪn.tə.vəl/',
                               'meaning': 'quãng (âm nhạc)',
                               'word': 'interval'},
                           {   'example': 'The pianist played the opening '
                                          'phrase in sharp, staccato notes.',
                               'ipa': '/stəˈkɑː.təʊ/',
                               'meaning': 'kỹ thuật ngắt âm trong âm nhạc',
                               'word': 'staccato'},
                           {   'example': 'Play those notes legato to create a '
                                          'smooth, flowing sound.',
                               'ipa': '/lɪˈɡɑː.təʊ/',
                               'meaning': 'liền mạch, trơn tru (âm nhạc)',
                               'word': 'legato'},
                           {   'example': 'Her vibrato gave the high notes a '
                                          'rich, warm quality.',
                               'ipa': '/vɪˈbrɑː.təʊ/',
                               'meaning': 'kỹ thuật rung âm',
                               'word': 'vibrato'},
                           {   'example': 'Sight-reading is an important skill '
                                          'for professional musicians.',
                               'ipa': '/saɪt ˈriː.dɪŋ/',
                               'meaning': 'đọc nhạc không qua luyện tập trước',
                               'word': 'sight-reading'},
                           {   'example': 'A solid understanding of music '
                                          'theory helps with composing and '
                                          'arranging.',
                               'ipa': '/ˈmjuː.zɪk ˈθɪər.i/',
                               'meaning': 'lý thuyết âm nhạc',
                               'word': 'music theory'},
                           {   'example': 'Call and response is a common '
                                          'technique in gospel and blues '
                                          'music.',
                               'ipa': '/kɔːl ənd rɪˈspɒns/',
                               'meaning': 'kỹ thuật hỏi-đáp trong âm nhạc',
                               'word': 'call and response'},
                           {   'example': 'The bass ostinato creates a '
                                          'hypnotic effect throughout the '
                                          'piece.',
                               'ipa': '/ˌɒs.tɪˈnɑː.təʊ/',
                               'meaning': 'mô-típ âm nhạc lặp đi lặp lại',
                               'word': 'ostinato'},
                           {   'example': 'She played the romantic ballad with '
                                          'expressive rubato.',
                               'ipa': '/ruːˈbɑː.təʊ/',
                               'meaning': 'kỹ thuật linh hoạt tempo',
                               'word': 'rubato'},
                           {   'example': 'A 3/4 time signature gives the '
                                          'music a waltz-like feel.',
                               'ipa': '/taɪm ˈsɪɡ.nɪ.tʃər/',
                               'meaning': 'nhịp (ký hiệu thời gian)',
                               'word': 'time signature'},
                           {   'example': 'The conductor held the fermata for '
                                          'several beats before releasing it.',
                               'ipa': '/fɜːˈmɑː.tə/',
                               'meaning': 'dấu giữ nốt',
                               'word': 'fermata'},
                           {   'example': 'A key signature with four sharps '
                                          'indicates E major.',
                               'ipa': '/kiː ˈsɪɡ.nɪ.tʃər/',
                               'meaning': 'giọng điệu (ký hiệu)',
                               'word': 'key signature'},
                           {   'example': 'Transposition allows a piece to be '
                                          'sung in a different key.',
                               'ipa': '/ˌtræn.spəˈzɪʃ.ən/',
                               'meaning': 'chuyển giọng/điều chỉnh khóa',
                               'word': 'transposition'},
                           {   'example': 'The pentatonic scale is widely used '
                                          'in folk and blues music.',
                               'ipa': '/ˌpen.təˈtɒn.ɪk skeɪl/',
                               'meaning': 'gam ngũ âm',
                               'word': 'pentatonic scale'},
                           {   'example': 'Most Western classical music is '
                                          'based on the diatonic scale.',
                               'ipa': '/ˌdaɪ.əˈtɒn.ɪk skeɪl/',
                               'meaning': 'gam diatonic (7 âm)',
                               'word': 'diatonic scale'},
                           {   'example': 'Music production involves '
                                          'recording, mixing, and mastering '
                                          'tracks.',
                               'ipa': '/ˈmjuː.zɪk prəˈdʌk.ʃən/',
                               'meaning': 'sản xuất âm nhạc',
                               'word': 'music production'},
                           {   'example': 'The crowd went wild when the beat '
                                          'drop hit.',
                               'ipa': '/biːt drɒp/',
                               'meaning': 'đoạn nhạc bùng nổ (trong EDM)',
                               'word': 'beat drop'},
                           {   'example': 'He uses looping pedals to layer '
                                          'sounds during live performances.',
                               'ipa': '/ˈluː.pɪŋ/',
                               'meaning': 'lặp vòng âm thanh',
                               'word': 'looping'},
                           {   'example': 'Layering instruments creates a '
                                          'richer, more complex sound.',
                               'ipa': '/ˈleɪ.ər.ɪŋ/',
                               'meaning': 'chồng lớp âm thanh',
                               'word': 'layering'},
                           {   'example': 'The recording session lasted 12 '
                                          'hours to capture the perfect sound.',
                               'ipa': '/rɪˈkɔː.dɪŋ ˈseʃ.ən/',
                               'meaning': 'phiên thu âm',
                               'word': 'recording session'},
                           {   'example': 'Acoustic treatment panels reduce '
                                          'unwanted sound reflections in a '
                                          'studio.',
                               'ipa': '/əˈkuː.stɪk ˈtriːt.mənt/',
                               'meaning': 'xử lý âm học phòng thu',
                               'word': 'acoustic treatment'},
                           {   'example': 'The sound engineer adjusted the '
                                          'levels on the mixing board.',
                               'ipa': '/ˈmɪk.sɪŋ bɔːd/',
                               'meaning': 'bàn trộn âm thanh',
                               'word': 'mixing board'},
                           {   'example': 'She sang over a backing track '
                                          'during the live performance.',
                               'ipa': '/ˈbæk.ɪŋ træk/',
                               'meaning': 'bản nhạc nền',
                               'word': 'backing track'},
                           {   'example': 'Adding reverb to the vocals gives '
                                          'them a richer, fuller sound.',
                               'ipa': '/ˈriː.vɜːb/',
                               'meaning': 'hiệu ứng vang tiếng',
                               'word': 'reverb'},
                           {   'example': 'The sound engineer used EQ to '
                                          'balance the frequencies in the mix.',
                               'ipa': '/ˌiː.kwəlaɪˈzeɪ.ʃən/',
                               'meaning': 'điều chỉnh tần số âm thanh',
                               'word': 'EQ (equalization)'},
                           {   'example': 'Mastering is the final step before '
                                          'a song is released.',
                               'ipa': '/ˈmɑː.stər.ɪŋ/',
                               'meaning': 'xử lý cuối bản nhạc',
                               'word': 'mastering'},
                           {   'example': 'Overdubbing allows musicians to add '
                                          'new parts on top of existing '
                                          'recordings.',
                               'ipa': '/ˌəʊ.vəˈdʌb.ɪŋ/',
                               'meaning': 'thu chèn thêm âm',
                               'word': 'overdubbing'},
                           {   'example': 'Music licensing allows companies to '
                                          'legally use copyrighted songs in '
                                          'advertisements.',
                               'ipa': '/ˈmjuː.zɪk ˈlaɪ.sən.sɪŋ/',
                               'meaning': 'cấp phép nhạc',
                               'word': 'music licensing'},
                           {   'example': 'Songwriters earn royalties every '
                                          'time their song is played on the '
                                          'radio.',
                               'ipa': '/ˈrɔɪ.əl.tiz/',
                               'meaning': 'tiền bản quyền âm nhạc',
                               'word': 'royalties'},
                           {   'example': 'Copyright law protects musicians '
                                          'from having their work copied '
                                          'without permission.',
                               'ipa': '/ˈkɒp.i.raɪt/',
                               'meaning': 'bản quyền',
                               'word': 'copyright'},
                           {   'example': 'Music streaming has changed how '
                                          'people discover and consume music.',
                               'ipa': '/ˈmjuː.zɪk ˈstriː.mɪŋ/',
                               'meaning': 'phát nhạc trực tuyến',
                               'word': 'music streaming'},
                           {   'example': 'Her song climbed to number one on '
                                          'the music charts.',
                               'ipa': '/ˈmjuː.zɪk tʃɑːts/',
                               'meaning': 'bảng xếp hạng âm nhạc',
                               'word': 'music charts'},
                           {   'example': 'Genre blending creates exciting new '
                                          'musical styles.',
                               'ipa': '/ˈʒɒn.rə ˈblen.dɪŋ/',
                               'meaning': 'pha trộn thể loại nhạc',
                               'word': 'genre blending'},
                           {   'example': 'The choir performed an impressive a '
                                          'cappella arrangement.',
                               'ipa': '/ˌæ kəˈpel.ə/',
                               'meaning': 'hát không nhạc đệm',
                               'word': 'a cappella'},
                           {   'example': 'A music educator inspires students '
                                          'to develop a lifelong love of '
                                          'music.',
                               'ipa': '/ˈmjuː.zɪk ˈed.jʊ.keɪ.tər/',
                               'meaning': 'giáo viên âm nhạc',
                               'word': 'music educator'}]},
    'social_media': {   'B1': [   {   'example': 'Social media marketing is '
                                                 'now essential for every '
                                                 'brand.',
                                      'ipa': '/ˈsəʊ.ʃəl ˈmiː.di.ə ˈmɑː.kɪ.tɪŋ/',
                                      'meaning': 'tiếp thị qua mạng xã hội',
                                      'word': 'social media marketing'},
                                  {   'example': 'A strong content strategy '
                                                 'drives consistent audience '
                                                 'growth.',
                                      'ipa': '/ˈkɒn.tent ˈstræt.ɪ.dʒi/',
                                      'meaning': 'chiến lược nội dung',
                                      'word': 'content strategy'},
                                  {   'example': "Wendy's Twitter brand voice "
                                                 'is playful and witty.',
                                      'ipa': '/brænd vɔɪs/',
                                      'meaning': 'giọng điệu thương hiệu',
                                      'word': 'brand voice'},
                                  {   'example': 'Social listening monitors '
                                                 'what people say about your '
                                                 'brand online.',
                                      'ipa': '/ˈsəʊ.ʃəl ˈlɪs.ən.ɪŋ/',
                                      'meaning': 'lắng nghe mạng xã hội',
                                      'word': 'social listening'},
                                  {   'example': 'Sentiment analysis reveals '
                                                 'whether brand mentions are '
                                                 'positive or negative.',
                                      'ipa': '/ˈsen.tɪ.mənt əˈnæl.ɪ.sɪs/',
                                      'meaning': 'phân tích cảm xúc người dùng',
                                      'word': 'sentiment analysis'},
                                  {   'example': 'Community management '
                                                 'involves responding to '
                                                 'comments and fostering '
                                                 'engagement.',
                                      'ipa': '/kəˈmjuː.nɪ.ti ˈmæn.ɪdʒ.mənt/',
                                      'meaning': 'quản lý cộng đồng trực tuyến',
                                      'word': 'community management'},
                                  {   'example': 'Reputation management '
                                                 "protects a brand's image "
                                                 'during crises.',
                                      'ipa': '/ˌrep.jʊˈteɪ.ʃən ˈmæn.ɪdʒ.mənt/',
                                      'meaning': 'quản lý danh tiếng trực '
                                                 'tuyến',
                                      'word': 'reputation management'},
                                  {   'example': 'Effective crisis '
                                                 'communication can save a '
                                                 "brand's reputation.",
                                      'ipa': '/ˈkraɪ.sɪs kəˌmjuː.nɪˈkeɪ.ʃən/',
                                      'meaning': 'truyền thông khủng hoảng',
                                      'word': 'crisis communication'},
                                  {   'example': 'Paid media includes promoted '
                                                 'posts and sponsored ads on '
                                                 'social platforms.',
                                      'ipa': '/peɪd ˈmiː.di.ə/',
                                      'meaning': 'quảng cáo trả phí',
                                      'word': 'paid media'},
                                  {   'example': 'Organic reach has declined '
                                                 'as platforms prioritize paid '
                                                 'content.',
                                      'ipa': '/ɔːˈɡæn.ɪk riːtʃ/',
                                      'meaning': 'tiếp cận tự nhiên (không trả '
                                                 'phí)',
                                      'word': 'organic reach'},
                                  {   'example': 'Brands increase their '
                                                 'visibility through paid '
                                                 'reach on social media.',
                                      'ipa': '/peɪd riːtʃ/',
                                      'meaning': 'tiếp cận trả phí',
                                      'word': 'paid reach'},
                                  {   'example': 'She boosted her post to '
                                                 'reach a wider audience.',
                                      'ipa': '/ˈbuːst.ɪd pəʊst/',
                                      'meaning': 'bài viết được quảng bá',
                                      'word': 'boosted post'},
                                  {   'example': 'Demographic targeting '
                                                 'delivers ads to the right '
                                                 'age and gender groups.',
                                      'ipa': '/ˌdem.əˈɡræf.ɪk ˈtɑː.ɡɪ.tɪŋ/',
                                      'meaning': 'nhắm mục tiêu theo nhân khẩu '
                                                 'học',
                                      'word': 'demographic targeting'},
                                  {   'example': 'Behavioral targeting shows '
                                                 'ads based on user browsing '
                                                 'and purchase history.',
                                      'ipa': '/bɪˈheɪ.vjər.əl ˈtɑː.ɡɪ.tɪŋ/',
                                      'meaning': 'nhắm mục tiêu theo hành vi',
                                      'word': 'behavioral targeting'},
                                  {   'example': 'Retargeting shows ads to '
                                                 'users who have previously '
                                                 'visited your website.',
                                      'ipa': '/ˌriːˈtɑː.ɡɪ.tɪŋ/',
                                      'meaning': 'tiếp thị lại',
                                      'word': 'retargeting'},
                                  {   'example': "Facebook's lookalike "
                                                 'audience feature finds users '
                                                 'similar to your existing '
                                                 'customers.',
                                      'ipa': '/ˈlʊk.ə.laɪk ˈɔː.di.əns/',
                                      'meaning': 'đối tượng tương tự',
                                      'word': 'lookalike audience'},
                                  {   'example': 'A/B testing compares two '
                                                 'versions of a post to see '
                                                 'which performs better.',
                                      'ipa': '/ˌeɪˈbiː ˈtes.tɪŋ/',
                                      'meaning': 'thử nghiệm A/B nội dung',
                                      'word': 'A/B testing (social media)'},
                                  {   'example': 'Calculate the ROI of your '
                                                 'social media campaigns to '
                                                 'prove their value.',
                                      'ipa': '/rɔɪ (rɪˈtərn ɔn ˌɪnˈvɛstmənt)/',
                                      'meaning': 'lợi nhuận trên đầu tư',
                                      'word': 'ROI (return on investment)'},
                                  {   'example': 'Customer reviews and '
                                                 'follower counts act as '
                                                 'social proof for brands.',
                                      'ipa': '/ˈsəʊ.ʃəl pruːf/',
                                      'meaning': 'bằng chứng xã hội',
                                      'word': 'social proof'},
                                  {   'example': 'Social media amplifies FOMO '
                                                 'among users who compare '
                                                 'their lives to others.',
                                      'ipa': '/ˈfəʊ.məʊ/',
                                      'meaning': 'tâm lý sợ bị bỏ lỡ',
                                      'word': 'FOMO (fear of missing out)'},
                                  {   'example': 'Doomscrolling through bad '
                                                 'news can worsen anxiety and '
                                                 'mental health.',
                                      'ipa': '/ˈduːm.skrəʊ.lɪŋ/',
                                      'meaning': 'cuộn mạng liên tục xem tin '
                                                 'xấu',
                                      'word': 'doomscrolling'},
                                  {   'example': 'Digital wellness involves '
                                                 'managing screen time and '
                                                 'online habits mindfully.',
                                      'ipa': '/ˈdɪdʒ.ɪ.təl ˈwel.nəs/',
                                      'meaning': 'sức khỏe số',
                                      'word': 'digital wellness'},
                                  {   'example': 'She reduced her daily screen '
                                                 'time to improve her sleep '
                                                 'quality.',
                                      'ipa': '/skriːn taɪm/',
                                      'meaning': 'thời gian sử dụng màn hình',
                                      'word': 'screen time'},
                                  {   'example': 'She went on a two-week '
                                                 'social media detox and felt '
                                                 'much calmer.',
                                      'ipa': '/ˈsəʊ.ʃəl ˈmiː.di.ə ˈdiː.tɒks/',
                                      'meaning': 'cai nghiện mạng xã hội tạm '
                                                 'thời',
                                      'word': 'social media detox'},
                                  {   'example': 'The attention economy treats '
                                                 'human attention as a scarce '
                                                 'commodity.',
                                      'ipa': '/əˈten.ʃən ɪˈkɒn.ə.mi/',
                                      'meaning': 'nền kinh tế thu hút sự chú ý',
                                      'word': 'attention economy'},
                                  {   'example': 'Social media algorithms '
                                                 'create echo chambers that '
                                                 'reinforce existing beliefs.',
                                      'ipa': '/ˈek.əʊ ˌtʃeɪm.bər/',
                                      'meaning': 'buồng vọng (bong bóng thông '
                                                 'tin)',
                                      'word': 'echo chamber'},
                                  {   'example': 'A filter bubble limits your '
                                                 'exposure to diverse '
                                                 'viewpoints online.',
                                      'ipa': '/ˈfɪl.tər ˌbʌb.əl/',
                                      'meaning': 'bong bóng lọc thông tin',
                                      'word': 'filter bubble'},
                                  {   'example': 'Viral marketing encourages '
                                                 'users to share content '
                                                 'organically.',
                                      'ipa': '/ˈvaɪ.rəl ˈmɑː.kɪ.tɪŋ/',
                                      'meaning': 'tiếp thị lan truyền',
                                      'word': 'viral marketing'},
                                  {   'example': 'The ice bucket challenge was '
                                                 'a guerrilla marketing '
                                                 'success.',
                                      'ipa': '/ɡəˈrɪl.ə ˈmɑː.kɪ.tɪŋ/',
                                      'meaning': 'tiếp thị du kích',
                                      'word': 'guerrilla marketing'},
                                  {   'example': 'TikTok Shop is a leading '
                                                 'example of social commerce.',
                                      'ipa': '/ˈsəʊ.ʃəl ˈkɒm.ɜːs/',
                                      'meaning': 'mua sắm qua mạng xã hội',
                                      'word': 'social commerce'},
                                  {   'example': "Instagram's shoppable posts "
                                                 'let users buy products '
                                                 'directly from the app.',
                                      'ipa': '/ˈʃɒp.ə.bəl ˈkɒn.tent/',
                                      'meaning': 'nội dung có thể mua hàng '
                                                 'trực tiếp',
                                      'word': 'shoppable content'},
                                  {   'example': 'Influencer marketing can be '
                                                 'more effective than '
                                                 'traditional advertising.',
                                      'ipa': '/ˈɪn.fluː.ən.sər ˈmɑː.kɪ.tɪŋ/',
                                      'meaning': 'tiếp thị người ảnh hưởng',
                                      'word': 'influencer marketing'},
                                  {   'example': 'She earns commission through '
                                                 'affiliate marketing links in '
                                                 'her videos.',
                                      'ipa': '/əˈfɪl.i.ɪt ˈmɑː.kɪ.tɪŋ/',
                                      'meaning': 'tiếp thị liên kết',
                                      'word': 'affiliate marketing'},
                                  {   'example': 'YouTube offers several '
                                                 'monetization options for '
                                                 'creators.',
                                      'ipa': '/ˌmɒn.ɪ.taɪˈzeɪ.ʃən/',
                                      'meaning': 'kiếm tiền từ nội dung',
                                      'word': 'monetization'},
                                  {   'example': 'The creator economy has '
                                                 'empowered millions to earn '
                                                 'income from content.',
                                      'ipa': '/kriˈeɪ.tər ɪˈkɒn.ə.mi/',
                                      'meaning': 'nền kinh tế người sáng tạo',
                                      'word': 'creator economy'},
                                  {   'example': 'She negotiated a brand deal '
                                                 'worth $10,000 for a single '
                                                 'post.',
                                      'ipa': '/brænd diːl/',
                                      'meaning': 'thỏa thuận hợp tác thương '
                                                 'hiệu',
                                      'word': 'brand deal'},
                                  {   'example': 'Content moderation removes '
                                                 'harmful posts from social '
                                                 'platforms.',
                                      'ipa': '/ˈkɒn.tent ˌmɒd.əˈreɪ.ʃən/',
                                      'meaning': 'kiểm duyệt nội dung',
                                      'word': 'content moderation'},
                                  {   'example': 'Every algorithm update '
                                                 "affects creators' reach and "
                                                 'strategy.',
                                      'ipa': '/ˈæl.ɡə.rɪð.əm ˈʌp.deɪt/',
                                      'meaning': 'cập nhật thuật toán',
                                      'word': 'algorithm update'},
                                  {   'example': 'Platform dependency is risky '
                                                 '— one algorithm change can '
                                                 'destroy a business.',
                                      'ipa': '/ˈplæt.fɔːm dɪˈpen.dən.si/',
                                      'meaning': 'sự phụ thuộc vào nền tảng',
                                      'word': 'platform dependency'},
                                  {   'example': 'A multi-platform strategy '
                                                 'reduces dependence on any '
                                                 'single social network.',
                                      'ipa': '/ˈmʌl.ti ˈplæt.fɔːm '
                                             'ˈstræt.ɪ.dʒi/',
                                      'meaning': 'chiến lược đa nền tảng',
                                      'word': 'multi-platform strategy'},
                                  {   'example': 'Her content pillars are '
                                                 'travel, food, and '
                                                 'sustainable living.',
                                      'ipa': '/ˈkɒn.tent ˈpɪl.ərz/',
                                      'meaning': 'chủ đề cốt lõi của nội dung',
                                      'word': 'content pillars'},
                                  {   'example': 'Evergreen content stays '
                                                 'relevant and drives traffic '
                                                 'long after posting.',
                                      'ipa': '/ˈev.ə.ɡriːn ˈkɒn.tent/',
                                      'meaning': 'nội dung không lỗi thời',
                                      'word': 'evergreen content'},
                                  {   'example': 'She creates content around '
                                                 'trending topics to boost '
                                                 'discoverability.',
                                      'ipa': '/ˈtren.dɪŋ ˈtɒp.ɪk/',
                                      'meaning': 'chủ đề đang hot',
                                      'word': 'trending topic'},
                                  {   'example': 'Social SEO uses keywords in '
                                                 'captions and hashtags to '
                                                 'improve visibility.',
                                      'ipa': '/ˈsioʊ (ˈsoʊʃəl)/',
                                      'meaning': 'tối ưu hóa tìm kiếm trên '
                                                 'mạng xã hội',
                                      'word': 'SEO (social)'},
                                  {   'example': 'Keyword optimization helps '
                                                 'your content appear in more '
                                                 'searches.',
                                      'ipa': '/ˈkiː.wɜːd ˌɒp.tɪ.maɪˈzeɪ.ʃən/',
                                      'meaning': 'tối ưu hóa từ khóa',
                                      'word': 'keyword optimization'},
                                  {   'example': 'They created a collaboration '
                                                 'post to grow both of their '
                                                 'audiences.',
                                      'ipa': '/kəˌlæb.əˈreɪ.ʃən pəʊst/',
                                      'meaning': 'bài đăng hợp tác',
                                      'word': 'collaboration post'},
                                  {   'example': 'She pinned her most '
                                                 'important post to the top of '
                                                 'her profile.',
                                      'ipa': '/pɪnd pəʊst/',
                                      'meaning': 'bài viết được ghim',
                                      'word': 'pinned post'},
                                  {   'example': 'Online advertising is a '
                                                 'highly effective way to '
                                                 'reach target consumers.',
                                      'ipa': '/ˈɒn.laɪn ˈæd.və.taɪ.zɪŋ/',
                                      'meaning': 'quảng cáo trực tuyến',
                                      'word': 'online advertising'}]},
    'software': {   'B1': [   {   'example': 'The search algorithm ranks '
                                             'results based on relevance.',
                                  'ipa': '/ˈæl.ɡə.rɪð.əm/',
                                  'meaning': 'thuật toán',
                                  'word': 'algorithm'},
                              {   'example': 'The developer used an API to '
                                             'connect the app to the payment '
                                             'gateway.',
                                  'ipa': '/ˌeɪ.piːˈaɪ/',
                                  'meaning': 'giao diện lập trình ứng dụng',
                                  'word': 'API'},
                              {   'example': 'The backend processes data and '
                                             'handles business logic.',
                                  'ipa': '/ˈbæk.end/',
                                  'meaning': 'phía máy chủ (backend)',
                                  'word': 'backend'},
                              {   'example': 'The frontend developer focuses '
                                             'on the visual design and user '
                                             'experience.',
                                  'ipa': '/ˈfrʌnt.end/',
                                  'meaning': 'phía giao diện người dùng '
                                             '(frontend)',
                                  'word': 'frontend'},
                              {   'example': 'They used React as their '
                                             'JavaScript framework for the '
                                             'project.',
                                  'ipa': '/ˈfreɪm.wɜːk/',
                                  'meaning': 'khung phần mềm',
                                  'word': 'framework'},
                              {   'example': 'The developer imported a library '
                                             'to handle date formatting.',
                                  'ipa': '/ˈlaɪ.brər.i/',
                                  'meaning': 'thư viện lập trình',
                                  'word': 'library'},
                              {   'example': 'The team uses GitHub as their '
                                             'code repository.',
                                  'ipa': '/rɪˈpɒz.ɪ.tər.i/',
                                  'meaning': 'kho lưu trữ mã nguồn',
                                  'word': 'repository'},
                              {   'example': 'Version control allows teams to '
                                             'track changes to the codebase.',
                                  'ipa': '/ˈvɜː.ʃən kənˈtrəʊl/',
                                  'meaning': 'quản lý phiên bản mã nguồn',
                                  'word': 'version control'},
                              {   'example': 'The deployment of the new '
                                             'version went smoothly without '
                                             'any downtime.',
                                  'ipa': '/dɪˈplɔɪ.mənt/',
                                  'meaning': 'triển khai phần mềm',
                                  'word': 'deployment'},
                              {   'example': 'The team completes one sprint '
                                             'every two weeks.',
                                  'ipa': '/sprɪnt/',
                                  'meaning': 'chu kỳ làm việc ngắn (Agile)',
                                  'word': 'sprint'},
                              {   'example': 'Agile methodology allows teams '
                                             'to adapt quickly to changing '
                                             'requirements.',
                                  'ipa': '/ˈædʒ.aɪl meˌθɒd.ɒl.ə.dʒi/',
                                  'meaning': 'phương pháp Agile',
                                  'word': 'agile methodology'},
                              {   'example': 'The team holds a daily scrum '
                                             'meeting to review progress.',
                                  'ipa': '/skrʌm/',
                                  'meaning': 'khung Scrum (quản lý dự án)',
                                  'word': 'scrum'},
                              {   'example': 'Each user story describes a '
                                             "feature from the user's "
                                             'perspective.',
                                  'ipa': '/ˈjuː.zər ˈstɔː.ri/',
                                  'meaning': 'câu chuyện người dùng (Agile)',
                                  'word': 'user story'},
                              {   'example': 'The product manager prioritizes '
                                             'items in the backlog each '
                                             'sprint.',
                                  'ipa': '/ˈbæk.lɒɡ/',
                                  'meaning': 'danh sách công việc tồn đọng',
                                  'word': 'backlog'},
                              {   'example': 'She submitted a pull request to '
                                             'merge her changes into the main '
                                             'branch.',
                                  'ipa': '/pʊl rɪˈkwest/',
                                  'meaning': 'yêu cầu gộp mã (Git)',
                                  'word': 'pull request'},
                              {   'example': 'Merge the feature branch into '
                                             'the main branch after testing.',
                                  'ipa': '/mərʤ/',
                                  'meaning': 'gộp mã nguồn',
                                  'word': 'merge'},
                              {   'example': 'Create a new branch before '
                                             'making changes to the code.',
                                  'ipa': '/brɑːntʃ/',
                                  'meaning': 'nhánh mã nguồn',
                                  'word': 'branch'},
                              {   'example': 'Commit your changes with a clear '
                                             'and descriptive message.',
                                  'ipa': '/kəˈmɪt/',
                                  'meaning': 'lưu thay đổi vào kho mã',
                                  'word': 'commit'},
                              {   'example': 'Unit testing verifies that '
                                             'individual pieces of code work '
                                             'correctly.',
                                  'ipa': '/ˈjuː.nɪt ˈtes.tɪŋ/',
                                  'meaning': 'kiểm thử đơn vị',
                                  'word': 'unit testing'},
                              {   'example': 'Integration testing checks how '
                                             'different modules work together.',
                                  'ipa': '/ˌɪn.tɪˈɡreɪ.ʃən ˈtes.tɪŋ/',
                                  'meaning': 'kiểm thử tích hợp',
                                  'word': 'integration testing'},
                              {   'example': 'Code review helps identify bugs '
                                             'and improve code quality.',
                                  'ipa': '/kəʊd rɪˈvjuː/',
                                  'meaning': 'xem xét mã nguồn',
                                  'word': 'code review'},
                              {   'example': 'Refactoring improves code '
                                             'readability without changing its '
                                             'behavior.',
                                  'ipa': '/ˌriːˈfæk.tər.ɪŋ/',
                                  'meaning': 'tái cấu trúc mã nguồn',
                                  'word': 'refactoring'},
                              {   'example': 'The application is designed for '
                                             'scalability to handle millions '
                                             'of users.',
                                  'ipa': '/ˌskeɪ.ləˈbɪl.ɪ.ti/',
                                  'meaning': 'khả năng mở rộng',
                                  'word': 'scalability'},
                              {   'example': 'Performance optimization reduced '
                                             'the page load time by 50%.',
                                  'ipa': '/pəˈfɔː.məns ˌɒp.tɪ.maɪˈzeɪ.ʃən/',
                                  'meaning': 'tối ưu hiệu suất',
                                  'word': 'performance optimization'},
                              {   'example': 'The application was rebuilt '
                                             'using a microservices '
                                             'architecture.',
                                  'ipa': '/ˈmaɪ.krəʊˌsɜː.vɪsɪz/',
                                  'meaning': 'kiến trúc vi dịch vụ',
                                  'word': 'microservices'},
                              {   'example': 'They migrated from a monolith to '
                                             'microservices for better '
                                             'scalability.',
                                  'ipa': '/ˈmɒn.ə.lɪθ/',
                                  'meaning': 'ứng dụng nguyên khối',
                                  'word': 'monolith'},
                              {   'example': 'Containerization using Docker '
                                             'makes deployment consistent '
                                             'across environments.',
                                  'ipa': '/kənˌteɪ.nər.aɪˈzeɪ.ʃən/',
                                  'meaning': 'đóng gói ứng dụng vào container',
                                  'word': 'containerization'},
                              {   'example': 'The CI/CD pipeline automatically '
                                             'tests and deploys code changes.',
                                  'ipa': '/ˌsiː.aɪ ˌsiːˈdiː ˈpaɪp.laɪn/',
                                  'meaning': 'quy trình tích hợp/triển khai '
                                             'liên tục',
                                  'word': 'CI/CD pipeline'},
                              {   'example': 'A load balancer distributes '
                                             'traffic across multiple servers.',
                                  'ipa': '/ləʊd ˈbæl.əns.ər/',
                                  'meaning': 'bộ cân bằng tải',
                                  'word': 'load balancer'},
                              {   'example': 'A CDN delivers content faster by '
                                             'caching it on servers close to '
                                             'the user.',
                                  'ipa': '/ˌsiː.diːˈen/',
                                  'meaning': 'mạng phân phối nội dung',
                                  'word': 'CDN (Content Delivery Network)'},
                              {   'example': 'The mobile app communicates with '
                                             'the server using a REST API.',
                                  'ipa': '/rest ˌeɪ.piːˈaɪ/',
                                  'meaning': 'API kiểu REST',
                                  'word': 'REST API'},
                              {   'example': 'The API returns data in JSON '
                                             'format.',
                                  'ipa': '/ˈdʒeɪ.sɒn/',
                                  'meaning': 'định dạng dữ liệu JSON',
                                  'word': 'JSON'},
                              {   'example': 'The system uses JWT tokens for '
                                             'user authentication.',
                                  'ipa': '/ɔːˌθen.tɪˈkeɪ.ʃən/',
                                  'meaning': 'xác thực người dùng',
                                  'word': 'authentication'},
                              {   'example': 'Authorization determines what '
                                             'each user is allowed to do.',
                                  'ipa': '/ˌɔː.θər.aɪˈzeɪ.ʃən/',
                                  'meaning': 'phân quyền truy cập',
                                  'word': 'authorization'},
                              {   'example': 'She wrote an SQL query to '
                                             'retrieve data from the database.',
                                  'ipa': '/ˌes.kjuːˈel/',
                                  'meaning': 'ngôn ngữ truy vấn SQL',
                                  'word': 'SQL'},
                              {   'example': 'MongoDB is a popular NoSQL '
                                             'database for storing '
                                             'unstructured data.',
                                  'ipa': '/ˌnəʊ.ˈes.kjuːˈel/',
                                  'meaning': 'cơ sở dữ liệu phi quan hệ',
                                  'word': 'NoSQL'},
                              {   'example': 'The DevOps team manages both '
                                             'development and system '
                                             'operations.',
                                  'ipa': '/ˈdev.ɒps/',
                                  'meaning': 'DevOps (kết hợp phát triển và '
                                             'vận hành)',
                                  'word': 'DevOps'},
                              {   'example': 'She used browser debugging tools '
                                             'to identify the JavaScript '
                                             'error.',
                                  'ipa': '/diːˈbʌɡ.ɪŋ tuːlz/',
                                  'meaning': 'công cụ gỡ lỗi',
                                  'word': 'debugging tools'},
                              {   'example': 'Responsive design ensures the '
                                             'website looks good on all screen '
                                             'sizes.',
                                  'ipa': '/rɪˈspɒn.sɪv dɪˈzaɪn/',
                                  'meaning': 'thiết kế giao diện thích ứng',
                                  'word': 'responsive design'},
                              {   'example': 'Good UX design makes software '
                                             'intuitive and easy to use.',
                                  'ipa': '/ˌjuːˈeks dɪˈzaɪn/',
                                  'meaning': 'thiết kế trải nghiệm người dùng',
                                  'word': 'UX design'},
                              {   'example': 'UI design focuses on the visual '
                                             'elements of the interface.',
                                  'ipa': '/ˌjuːˈaɪ dɪˈzaɪn/',
                                  'meaning': 'thiết kế giao diện người dùng',
                                  'word': 'UI design'},
                              {   'example': 'The designer created wireframes '
                                             'before building the actual '
                                             'interface.',
                                  'ipa': '/ˈwaɪər.freɪm/',
                                  'meaning': 'khung giao diện sơ bộ',
                                  'word': 'wireframe'},
                              {   'example': 'They built a prototype to test '
                                             'the concept with users.',
                                  'ipa': '/ˈprəʊ.tə.taɪp/',
                                  'meaning': 'nguyên mẫu phần mềm',
                                  'word': 'prototype'},
                              {   'example': 'User acceptance testing ensures '
                                             'the software meets user '
                                             'requirements.',
                                  'ipa': '/ˈjuː.zər əkˈsep.təns ˈtes.tɪŋ/',
                                  'meaning': 'kiểm thử chấp nhận người dùng',
                                  'word': 'user acceptance testing'},
                              {   'example': 'Regression testing ensures that '
                                             "new changes haven't broken "
                                             'existing features.',
                                  'ipa': '/rɪˈɡreʃ.ən ˈtes.tɪŋ/',
                                  'meaning': 'kiểm thử hồi quy',
                                  'word': 'regression testing'},
                              {   'example': 'Linux is the most widely used '
                                             'open source operating system.',
                                  'ipa': '/ˌəʊ.pən ˈsɔːs/',
                                  'meaning': 'mã nguồn mở',
                                  'word': 'open source'},
                              {   'example': 'Good documentation makes it '
                                             'easier for new developers to '
                                             'understand the code.',
                                  'ipa': '/ˌdɒk.jʊ.menˈteɪ.ʃən/',
                                  'meaning': 'tài liệu kỹ thuật',
                                  'word': 'documentation'},
                              {   'example': 'Accumulating tech debt makes '
                                             'future development slower and '
                                             'more expensive.',
                                  'ipa': '/tek det/',
                                  'meaning': 'nợ kỹ thuật (code tệ tích tụ)',
                                  'word': 'tech debt'},
                              {   'example': 'The team tested the release '
                                             'candidate before the final '
                                             'launch.',
                                  'ipa': '/rɪˈliːs ˈkæn.dɪ.dɪt/',
                                  'meaning': 'phiên bản ứng viên phát hành',
                                  'word': 'release candidate'},
                              {   'example': 'Many companies now prefer SaaS '
                                             'solutions over traditional '
                                             'installed software.',
                                  'ipa': '/sæs/',
                                  'meaning': 'phần mềm dưới dạng dịch vụ',
                                  'word': 'SaaS (Software as a Service)'}]},
    'sports': {   'B1': [   {   'example': 'Marathon runners need exceptional '
                                           'endurance to complete the 42km '
                                           'race.',
                                'ipa': '/ɪnˈdjʊər.əns/',
                                'meaning': 'sức bền',
                                'word': 'endurance'},
                            {   'example': 'Building stamina takes months of '
                                           'consistent training.',
                                'ipa': '/ˈstæm.ɪ.nə/',
                                'meaning': 'thể lực bền bỉ',
                                'word': 'stamina'},
                            {   'example': 'He congratulated his opponent, '
                                           'showing great sportsmanship.',
                                'ipa': '/ˈspɔːts.mən.ʃɪp/',
                                'meaning': 'tinh thần thể thao',
                                'word': 'sportsmanship'},
                            {   'example': 'The relay race requires smooth '
                                           'baton exchanges between teammates.',
                                'ipa': '/ˈriː.leɪ reɪs/',
                                'meaning': 'đua tiếp sức',
                                'word': 'relay race'},
                            {   'example': 'The boxer won by knockout in the '
                                           'third round.',
                                'ipa': '/ˈnɒk.aʊt/',
                                'meaning': 'đấm knock-out; hạ gục đối thủ',
                                'word': 'knockout'},
                            {   'example': 'She easily passed the qualifying '
                                           'round and reached the semifinals.',
                                'ipa': '/ˈkwɒl.ɪ.faɪ.ɪŋ raʊnd/',
                                'meaning': 'vòng loại',
                                'word': 'qualifying round'},
                            {   'example': 'He worked three hours of overtime '
                                           'yesterday.',
                                'ipa': '/ˈəʊ.və.taɪm/',
                                'meaning': 'Làm thêm giờ, thời gian làm thêm',
                                'word': 'overtime'},
                            {   'example': 'The underdog team surprised '
                                           'everyone by beating the champions.',
                                'ipa': '/ˈʌn.də.dɒɡ/',
                                'meaning': 'đội/người yếu thế',
                                'word': 'underdog'},
                            {   'example': 'The aggregate score over both legs '
                                           'was 4-3.',
                                'ipa': '/ˈæɡ.rɪ.ɡɪt skɔːr/',
                                'meaning': 'tổng tỉ số hai lượt',
                                'word': 'aggregate score'},
                            {   'example': 'The team avoided relegation by '
                                           'winning their last three matches.',
                                'ipa': '/ˌrel.ɪˈɡeɪ.ʃən/',
                                'meaning': 'xuống hạng',
                                'word': 'relegation'},
                            {   'example': 'Winning the second division earned '
                                           'them promotion to the top league.',
                                'ipa': '/prəˈməʊ.ʃən/',
                                'meaning': 'thăng hạng',
                                'word': 'promotion'},
                            {   'example': 'The national squad was announced '
                                           'ahead of the World Cup.',
                                'ipa': '/skwɒd/',
                                'meaning': 'đội hình cầu thủ',
                                'word': 'squad'},
                            {   'example': 'The fixture list for the new '
                                           'season has been released.',
                                'ipa': '/ˈfɪks.tʃər/',
                                'meaning': 'lịch thi đấu',
                                'word': 'fixture'},
                            {   'example': 'The goalkeeper kept a clean sheet '
                                           'throughout the tournament.',
                                'ipa': '/kliːn ʃiːt/',
                                'meaning': 'không để thủng lưới',
                                'word': 'clean sheet'},
                            {   'example': 'He scored a hat-trick in just 20 '
                                           'minutes.',
                                'ipa': '/ˈhæt.trɪk/',
                                'meaning': 'ghi ba bàn thắng trong một trận',
                                'word': 'hat-trick'},
                            {   'example': 'The defenders set an offsides trap '
                                           'to catch the striker.',
                                'ipa': '/ˈɒf.saɪdz træp/',
                                'meaning': 'bẫy việt vị',
                                'word': 'offsides trap'},
                            {   'example': 'The home team had 65% ball '
                                           'possession during the match.',
                                'ipa': '/pəˈzeʃ.ən/',
                                'meaning': 'sự kiểm soát bóng',
                                'word': 'possession'},
                            {   'example': 'They scored on a quick '
                                           'counterattack after winning the '
                                           'ball back.',
                                'ipa': '/ˌkaʊn.tərəˈtæk/',
                                'meaning': 'phản công',
                                'word': 'counterattack'},
                            {   'example': 'Their coach has developed '
                                           'effective set piece routines.',
                                'ipa': '/set piːs/',
                                'meaning': 'tình huống cố định (phạt góc, phạt '
                                           'trực tiếp)',
                                'word': 'set piece'},
                            {   'example': 'The winning goal was scored in '
                                           'injury time.',
                                'ipa': '/ˈɪn.dʒər.i taɪm/',
                                'meaning': 'giờ bù giờ',
                                'word': 'injury time'},
                            {   'example': 'She made her international debut '
                                           'at the age of 17.',
                                'ipa': '/ˈdeɪ.bjuː/',
                                'meaning': 'lần ra sân/thi đấu đầu tiên',
                                'word': 'debut'},
                            {   'example': 'The veteran midfielder brought '
                                           'experience and leadership to the '
                                           'team.',
                                'ipa': '/ˈvet.ər.ən/',
                                'meaning': 'cầu thủ kỳ cựu',
                                'word': 'veteran'},
                            {   'example': 'She ran a personal best in the '
                                           '1500m race.',
                                'ipa': '/ˈpɜː.sən.əl best/',
                                'meaning': 'thành tích cá nhân tốt nhất',
                                'word': 'personal best'},
                            {   'example': 'Proper sports nutrition helps '
                                           'athletes recover faster after '
                                           'training.',
                                'ipa': '/spɔːts njuːˈtrɪʃ.ən/',
                                'meaning': 'dinh dưỡng thể thao',
                                'word': 'sports nutrition'},
                            {   'example': 'He needed physiotherapy to recover '
                                           'from his hamstring injury.',
                                'ipa': '/ˌfɪz.i.əʊˈθer.ə.pi/',
                                'meaning': 'vật lý trị liệu',
                                'word': 'physiotherapy'},
                            {   'example': "The club's scouting network "
                                           'identified young talent from '
                                           'across the country.',
                                'ipa': '/ˈskaʊ.tɪŋ/',
                                'meaning': 'tìm kiếm tài năng',
                                'word': 'scouting'},
                            {   'example': 'The transfer fee for the striker '
                                           'was a record $100 million.',
                                'ipa': '/ˈtræns.fər fiː/',
                                'meaning': 'phí chuyển nhượng',
                                'word': 'transfer fee'},
                            {   'example': 'The club offered the captain a '
                                           'contract extension for two more '
                                           'years.',
                                'ipa': '/ˈkɒn.trækt ɪkˈsten.ʃən/',
                                'meaning': 'gia hạn hợp đồng',
                                'word': 'contract extension'},
                            {   'example': 'The team conceded three goals in '
                                           'the second half.',
                                'ipa': '/kənˈsiːd/',
                                'meaning': 'thủng lưới; để thua',
                                'word': 'concede'},
                            {   'example': 'The attacking midfielder created '
                                           "most of the team's scoring "
                                           'opportunities.',
                                'ipa': '/əˈtæk.ɪŋ ˈmɪd.fiːl.dər/',
                                'meaning': 'tiền vệ tấn công',
                                'word': 'attacking midfielder'},
                            {   'example': 'Their defensive line was solid '
                                           'throughout the tournament.',
                                'ipa': '/dɪˈfen.sɪv laɪn/',
                                'meaning': 'hàng phòng thủ',
                                'word': 'defensive line'},
                            {   'example': 'He curled the free kick into the '
                                           'top corner.',
                                'ipa': '/ˈfriː kɪk/',
                                'meaning': 'đá phạt trực tiếp',
                                'word': 'free kick'},
                            {   'example': 'She swung in a dangerous corner '
                                           'kick that led to a goal.',
                                'ipa': '/ˈkɔː.nər kɪk/',
                                'meaning': 'phạt góc',
                                'word': 'corner kick'},
                            {   'example': 'The goal was ruled out due to an '
                                           'offside decision.',
                                'ipa': '/ˌɒfˈsaɪd/',
                                'meaning': 'việt vị',
                                'word': 'offside'},
                            {   'example': 'The player received a yellow card '
                                           'for a reckless tackle.',
                                'ipa': '/ˈjel.əʊ kɑːd/',
                                'meaning': 'thẻ vàng',
                                'word': 'yellow card'},
                            {   'example': 'He was shown a red card and sent '
                                           'off in the 70th minute.',
                                'ipa': '/red kɑːd/',
                                'meaning': 'thẻ đỏ',
                                'word': 'red card'},
                            {   'example': 'The match went into extra time '
                                           'after 90 minutes.',
                                'ipa': '/ˈek.strə taɪm/',
                                'meaning': 'hiệp phụ',
                                'word': 'extra time'},
                            {   'example': 'England were eliminated in a '
                                           'penalty shootout.',
                                'ipa': '/ˈpen.əl.ti ˈʃuː.taʊt/',
                                'meaning': 'loạt sút phạt đền',
                                'word': 'penalty shootout'},
                            {   'example': 'The coach switched to a 4-3-3 '
                                           'formation for the second half.',
                                'ipa': '/fɔːˈmeɪ.ʃən/',
                                'meaning': 'đội hình chiến thuật',
                                'word': 'formation'},
                            {   'example': 'High pressing forces opponents to '
                                           'make mistakes in their own half.',
                                'ipa': '/ˈpres.ɪŋ/',
                                'meaning': 'chiến thuật pressing',
                                'word': 'pressing'},
                            {   'example': "Barcelona's tiki-taka style "
                                           'dominated world football for a '
                                           'decade.',
                                'ipa': '/ˌtɪk.iˈtɑː.kə/',
                                'meaning': 'phong cách chơi trao đổi bóng ngắn '
                                           'liên tục',
                                'word': 'tiki-taka'},
                            {   'example': 'The sweeper is positioned behind '
                                           'the defensive line to cover '
                                           'mistakes.',
                                'ipa': '/ˈswiː.pər/',
                                'meaning': 'hậu vệ quét (libero)',
                                'word': 'sweeper'},
                            {   'example': "The winger's pace and dribbling "
                                           'caused constant problems for '
                                           'defenders.',
                                'ipa': '/ˈwɪŋ.ər/',
                                'meaning': 'cầu thủ chạy cánh',
                                'word': 'winger'},
                            {   'example': 'The striker scored 30 goals this '
                                           'season.',
                                'ipa': '/ˈstraɪ.kər/',
                                'meaning': 'tiền đạo trung tâm',
                                'word': 'striker'},
                            {   'example': 'The coach employed man-to-man '
                                           'marking to neutralize the '
                                           "opposition's star player.",
                                'ipa': '/mæn tə mæn ˈmɑː.kɪŋ/',
                                'meaning': 'kèm người',
                                'word': 'man-to-man marking'},
                            {   'example': 'The throw-in was taken quickly to '
                                           "maintain the team's momentum.",
                                'ipa': '/ˈθrəʊ.ɪn/',
                                'meaning': 'ném biên',
                                'word': 'throw-in'},
                            {   'example': 'He scored with a powerful header '
                                           'from a corner kick.',
                                'ipa': '/ˈhed.ər/',
                                'meaning': 'cú đánh đầu',
                                'word': 'header'},
                            {   'example': "The winger's pace was too much for "
                                           'the defenders to handle.',
                                'ipa': '/peɪs/',
                                'meaning': 'tốc độ',
                                'word': 'pace'},
                            {   'example': 'Agility drills help footballers '
                                           'change direction quickly.',
                                'ipa': '/əˈdʒɪl.ɪ.ti/',
                                'meaning': 'sự linh hoạt, nhanh nhẹn',
                                'word': 'agility'},
                            {   'example': 'He had to leave the field due to a '
                                           'muscle cramp.',
                                'ipa': '/ˈmʌs.əl kræmp/',
                                'meaning': 'chuột rút',
                                'word': 'muscle cramp'},
                            {   'example': 'The national team held a training '
                                           'camp before the World Cup '
                                           'qualifiers.',
                                'ipa': '/ˈtreɪ.nɪŋ kæmp/',
                                'meaning': 'trại tập huấn',
                                'word': 'training camp'}]},
    'tech': {   'A1': [   {   'example': 'I use my phone to call my friends.',
                              'ipa': '/fəʊn/',
                              'meaning': 'điện thoại',
                              'word': 'phone'},
                          {   'example': 'The screen on this laptop is very '
                                         'bright.',
                              'ipa': '/skriːn/',
                              'meaning': 'màn hình',
                              'word': 'screen'},
                          {   'example': 'She took a photo with her camera.',
                              'ipa': '/ˈkæm.ər.ə/',
                              'meaning': 'máy ảnh, máy quay',
                              'word': 'camera'},
                          {   'example': 'He reads books on his tablet.',
                              'ipa': '/ˈtæb.lɪt/',
                              'meaning': 'máy tính bảng',
                              'word': 'tablet'},
                          {   'example': 'We watched a funny video online.',
                              'ipa': '/ˈvɪd.i.əʊ/',
                              'meaning': 'video, phim',
                              'word': 'video'},
                          {   'example': 'This game is very popular with '
                                         'children.',
                              'ipa': '/ɡeɪm/',
                              'meaning': 'trò chơi',
                              'word': 'game'},
                          {   'example': 'I need the internet to do my '
                                         'homework.',
                              'ipa': '/ˈɪn.tə.net/',
                              'meaning': 'mạng Internet',
                              'word': 'internet'},
                          {   'example': 'Please send me an email with the '
                                         'details.',
                              'ipa': '/ˈiː.meɪl/',
                              'meaning': 'thư điện tử',
                              'word': 'email'},
                          {   'example': 'He called me on the telephone to '
                                         'confirm the meeting.',
                              'ipa': '/ˈtɛlɪfoʊn/',
                              'meaning': 'Điện thoại (cố định)',
                              'word': 'telephone'},
                          {   'example': 'The new phone has a sharp, '
                                         'high-resolution display.',
                              'ipa': '/dɪˈspleɪ/',
                              'meaning': 'Màn hình hiển thị',
                              'word': 'display'},
                          {   'example': 'She bought a new wide-angle lens for '
                                         'her camera.',
                              'ipa': '/lɛnz/',
                              'meaning': 'Ống kính máy ảnh; thấu kính',
                              'word': 'lens'},
                          {   'example': 'She wrote a note on her notepad.',
                              'ipa': '/pæd/',
                              'meaning': 'Miếng lót, tập giấy ghi chú',
                              'word': 'pad'},
                          {   'example': 'She shared a funny clip on social '
                                         'media.',
                              'ipa': '/klɪp/',
                              'meaning': 'Đoạn video ngắn; kẹp giấy',
                              'word': 'clip'},
                          {   'example': 'The match between the two teams was '
                                         'exciting.',
                              'ipa': '/mæʧ/',
                              'meaning': 'Trận đấu; diêm quẹt',
                              'word': 'match'},
                          {   'example': 'The fisherman cast his net into the '
                                         'sea.',
                              'ipa': '/nɛt/',
                              'meaning': 'Lưới; mạng lưới',
                              'word': 'net'},
                          {   'example': 'Send me the report by electronic '
                                         'mail.',
                              'ipa': '/ɪˌlɛkˈtrɒnɪk meɪl/',
                              'meaning': 'Thư điện tử',
                              'word': 'electronic mail'},
                          {   'example': 'Type on the keyboard to enter text.',
                              'ipa': '/ˈkiː.bɔːrd/',
                              'meaning': 'bàn phím máy tính',
                              'word': 'keyboard'},
                          {   'example': 'Click the mouse to open the file.',
                              'ipa': '/maʊs/',
                              'meaning': 'chuột máy tính',
                              'word': 'mouse'},
                          {   'example': 'Print the document on the printer.',
                              'ipa': '/ˈprɪn.tər/',
                              'meaning': 'máy in tài liệu',
                              'word': 'printer'},
                          {   'example': 'The speaker makes very clear sound.',
                              'ipa': '/ˈspiː.kər/',
                              'meaning': 'loa âm thanh',
                              'word': 'speaker'},
                          {   'example': 'Use headphones to listen to music.',
                              'ipa': '/ˈhɛd.foʊnz/',
                              'meaning': 'tai nghe',
                              'word': 'headphones'},
                          {   'example': 'Connect using a USB cable.',
                              'ipa': '/ˈkeɪ.bəl/',
                              'meaning': 'dây cáp kết nối',
                              'word': 'cable'},
                          {   'example': 'Plug the device into the socket.',
                              'ipa': '/plʌɡ/',
                              'meaning': 'phích cắm điện',
                              'word': 'plug'},
                          {   'example': 'The device runs on battery power.',
                              'ipa': '/ˈpaʊ.ər/',
                              'meaning': 'nguồn điện',
                              'word': 'power'},
                          {   'example': 'Save the file before closing.',
                              'ipa': '/faɪl/',
                              'meaning': 'tập tin, file dữ liệu',
                              'word': 'file'},
                          {   'example': 'Put the file in the correct folder.',
                              'ipa': '/ˈfoʊl.dər/',
                              'meaning': 'thư mục chứa file',
                              'word': 'folder'},
                          {   'example': 'Click the icon to open the app.',
                              'ipa': '/ˈaɪ.kɒn/',
                              'meaning': 'biểu tượng ứng dụng',
                              'word': 'icon'},
                          {   'example': 'Select the option from the menu.',
                              'ipa': '/ˈmɛn.juː/',
                              'meaning': 'thanh menu điều hướng',
                              'word': 'menu'},
                          {   'example': 'Open a new page in the browser.',
                              'ipa': '/peɪdʒ/',
                              'meaning': 'trang web cụ thể',
                              'word': 'page'},
                          {   'example': 'Use a browser to access websites.',
                              'ipa': '/ˈbraʊ.zər/',
                              'meaning': 'trình duyệt web',
                              'word': 'browser'},
                          {   'example': 'Listen to music on your phone.',
                              'ipa': '/ˈmjuː.zɪk/',
                              'meaning': 'âm nhạc kỹ thuật số',
                              'word': 'music'},
                          {   'example': 'Share the photo with your friends.',
                              'ipa': '/ʃɛər/',
                              'meaning': 'chia sẻ nội dung',
                              'word': 'share'},
                          {   'example': 'Save the document before closing.',
                              'ipa': '/seɪv/',
                              'meaning': 'lưu dữ liệu',
                              'word': 'save'},
                          {   'example': 'Delete old files to free up space.',
                              'ipa': '/dɪˈliːt/',
                              'meaning': 'xóa dữ liệu',
                              'word': 'delete'},
                          {   'example': 'Start the computer by pressing '
                                         'power.',
                              'ipa': '/stɑːrt/',
                              'meaning': 'khởi động thiết bị',
                              'word': 'start'},
                          {   'example': 'Connect to the home wifi.',
                              'ipa': '/ˈwaɪ.faɪ/',
                              'meaning': 'mạng wifi không dây',
                              'word': 'wifi'},
                          {   'example': 'The signal is weak here.',
                              'ipa': '/ˈsɪɡ.nəl/',
                              'meaning': 'tín hiệu mạng',
                              'word': 'signal'},
                          {   'example': 'Install the program on your '
                                         'computer.',
                              'ipa': '/ɪnˈstɔːl/',
                              'meaning': 'cài đặt phần mềm',
                              'word': 'install'},
                          {   'example': 'Login to access your account.',
                              'ipa': '/ˈlɒɡ.ɪn/',
                              'meaning': 'đăng nhập tài khoản',
                              'word': 'login'},
                          {   'example': 'Create an account to use the '
                                         'service.',
                              'ipa': '/əˈkaʊnt/',
                              'meaning': 'tài khoản trực tuyến',
                              'word': 'account'},
                          {   'example': 'Turn off notifications at night.',
                              'ipa': '/ˌnoʊ.tɪ.fɪˈkeɪ.ʃən/',
                              'meaning': 'thông báo trên thiết bị',
                              'word': 'notification'},
                          {   'example': 'Change the settings in the app.',
                              'ipa': '/ˈsɛt.ɪŋz/',
                              'meaning': 'cài đặt hệ thống',
                              'word': 'settings'},
                          {   'example': 'Carry your laptop in a laptop bag.',
                              'ipa': '/ˈlæp.tɒp bæɡ/',
                              'meaning': 'túi đựng laptop bảo vệ',
                              'word': 'laptop bag'},
                          {   'example': 'Charge your phone with a power bank.',
                              'ipa': '/ˈpaʊ.ər bæŋk/',
                              'meaning': 'pin dự phòng sạc điện thoại',
                              'word': 'power bank'},
                          {   'example': 'Insert the SIM card to make calls.',
                              'ipa': '/sɪm kɑːrd/',
                              'meaning': 'thẻ SIM điện thoại',
                              'word': 'SIM card'},
                          {   'example': 'Take a screenshot of the error.',
                              'ipa': '/ˈskriːn.ʃɒt/',
                              'meaning': 'chụp màn hình thiết bị',
                              'word': 'screenshot'},
                          {   'example': 'Swipe right to unlock the screen.',
                              'ipa': '/swaɪp/',
                              'meaning': 'vuốt màn hình cảm ứng',
                              'word': 'swipe'},
                          {   'example': 'Tap the icon to open the app.',
                              'ipa': '/tæp/',
                              'meaning': 'chạm nhẹ màn hình',
                              'word': 'tap'},
                          {   'example': 'Zoom in to see the details.',
                              'ipa': '/zuːm/',
                              'meaning': 'phóng to thu nhỏ hình ảnh',
                              'word': 'zoom'},
                          {   'example': 'Scan the QR code to visit the '
                                         'website.',
                              'ipa': '/ˌkjuː.ɑːr ˈkoʊd/',
                              'meaning': 'mã QR quét bằng điện thoại',
                              'word': 'QR code'},
                          {   'example': 'Take a photo with your phone.',
                              'ipa': '/ˈfoʊ.toʊ/',
                              'meaning': 'bức ảnh kỹ thuật số',
                              'word': 'photo'},
                          {   'example': 'Stop the download now.',
                              'ipa': '/stɒp/',
                              'meaning': 'dừng hoạt động',
                              'word': 'stop'}],
                'A2': [   {   'example': 'Most people have a smartphone these '
                                         'days.',
                              'ipa': '/ˈsmɑːt.fəʊn/',
                              'meaning': 'điện thoại thông minh',
                              'word': 'smartphone'},
                          {   'example': 'My battery is low, I need to charge '
                                         'my phone.',
                              'ipa': '/ˈbæt.ər.i/',
                              'meaning': 'pin',
                              'word': 'battery'},
                          {   'example': 'You can download the app for free.',
                              'ipa': '/ˌdaʊnˈləʊd/',
                              'meaning': 'tải xuống',
                              'word': 'download'},
                          {   'example': 'Visit our website for more '
                                         'information.',
                              'ipa': '/ˈweb.saɪt/',
                              'meaning': 'trang web',
                              'word': 'website'},
                          {   'example': "Don't share your password with "
                                         'anyone.',
                              'ipa': '/ˈpɑːs.wɜːd/',
                              'meaning': 'mật khẩu',
                              'word': 'password'},
                          {   'example': 'You should update your software '
                                         'regularly.',
                              'ipa': '/ʌpˈdeɪt/',
                              'meaning': 'cập nhật',
                              'word': 'update'},
                          {   'example': "I can't connect to the Wi-Fi "
                                         'network.',
                              'ipa': '/kəˈnekt/',
                              'meaning': 'kết nối',
                              'word': 'connect'},
                          {   'example': 'She sent me a message on social '
                                         'media.',
                              'ipa': '/ˈmes.ɪdʒ/',
                              'meaning': 'tin nhắn',
                              'word': 'message'},
                          {   'example': 'He kept his cellphone in his front '
                                         'pocket.',
                              'ipa': '/ˈsel.fəʊn/',
                              'meaning': 'điện thoại di động',
                              'word': 'cellphone'},
                          {   'example': 'I left my phone charger at the '
                                         'office.',
                              'ipa': '/ˈʧɑrʤər/',
                              'meaning': 'thiết bị sạc pin',
                              'word': 'charger'},
                          {   'example': 'It took ten minutes to upload the '
                                         'high-resolution photo.',
                              'ipa': '/ʌpˈləʊd/',
                              'meaning': 'tải lên dữ liệu',
                              'word': 'upload'},
                          {   'example': 'The homepage is the first webpage '
                                         'you see when visiting a site.',
                              'ipa': '/ˈweb.peɪdʒ/',
                              'meaning': 'trang web (một trang đơn lẻ)',
                              'word': 'webpage'},
                          {   'example': 'Enter your passcode to unlock the '
                                         'phone.',
                              'ipa': '/ˈpæsˌkoʊd/',
                              'meaning': 'Mã PIN, mật khẩu số',
                              'word': 'passcode'},
                          {   'example': "It's time to upgrade your computer's "
                                         'operating system.',
                              'ipa': '/ˈʌpˌɡreɪd/',
                              'meaning': 'Nâng cấp lên phiên bản mới hơn',
                              'word': 'upgrade'},
                          {   'example': 'Click the link to visit the website.',
                              'ipa': '/lɪŋk/',
                              'meaning': 'Liên kết, đường dẫn',
                              'word': 'link'},
                          {   'example': 'There is a notice on the wall about '
                                         'the power outage.',
                              'ipa': '/ˈnəʊ.tɪs/',
                              'meaning': 'thông báo, yết thị',
                              'word': 'notice'},
                          {   'example': 'Upgrade the hardware for better '
                                         'performance.',
                              'ipa': '/ˈhɑːrd.weər/',
                              'meaning': 'phần cứng máy tính',
                              'word': 'hardware'},
                          {   'example': 'Add more RAM for multitasking.',
                              'ipa': '/ræm/',
                              'meaning': 'bộ nhớ truy cập ngẫu nhiên',
                              'word': 'RAM'},
                          {   'example': 'An SSD makes the computer boot '
                                         'faster.',
                              'ipa': '/ˌɛs.ɛsˈdiː/',
                              'meaning': 'ổ cứng thể rắn nhanh',
                              'word': 'SSD'},
                          {   'example': 'A good graphics card is needed for '
                                         'gaming.',
                              'ipa': '/ˈɡræf.ɪks kɑːrd/',
                              'meaning': 'card đồ họa xử lý hình ảnh',
                              'word': 'graphics card'},
                          {   'example': 'A large monitor improves '
                                         'productivity.',
                              'ipa': '/ˈmɒn.ɪ.tər/',
                              'meaning': 'màn hình hiển thị máy tính',
                              'word': 'monitor'},
                          {   'example': 'I carry my laptop to work every day.',
                              'ipa': '/ˈlæp.tɒp/',
                              'meaning': 'máy tính xách tay',
                              'word': 'laptop'},
                          {   'example': 'A desktop is more powerful than a '
                                         'laptop.',
                              'ipa': '/ˈdɛsk.tɒp/',
                              'meaning': 'máy tính để bàn',
                              'word': 'desktop'},
                          {   'example': 'The router distributes internet to '
                                         'all devices.',
                              'ipa': '/ˈruː.tər/',
                              'meaning': 'bộ định tuyến mạng',
                              'word': 'router'},
                          {   'example': 'The modem connects you to the '
                                         'internet.',
                              'ipa': '/ˈmoʊ.dɛm/',
                              'meaning': 'thiết bị kết nối internet',
                              'word': 'modem'},
                          {   'example': 'Pair your phone via Bluetooth.',
                              'ipa': '/ˈbluː.tuːθ/',
                              'meaning': 'kết nối không dây Bluetooth',
                              'word': 'bluetooth'},
                          {   'example': 'The GPS shows your exact location.',
                              'ipa': '/ˌdʒiː.piːˈɛs/',
                              'meaning': 'hệ thống định vị toàn cầu',
                              'word': 'GPS'},
                          {   'example': 'Plug in the USB drive to transfer '
                                         'files.',
                              'ipa': '/ˌjuː.ɛsˈbiː/',
                              'meaning': 'cổng kết nối USB phổ biến',
                              'word': 'USB'},
                          {   'example': 'Always back up your important files.',
                              'ipa': '/ˈbæk.ʌp/',
                              'meaning': 'sao lưu dữ liệu an toàn',
                              'word': 'backup'},
                          {   'example': 'Install antivirus to protect your '
                                         'computer.',
                              'ipa': '/ˈvaɪ.rəs/',
                              'meaning': 'phần mềm độc hại virus',
                              'word': 'virus'},
                          {   'example': 'Run antivirus scans weekly.',
                              'ipa': '/ˌæn.tiˈvaɪ.rəs/',
                              'meaning': 'phần mềm diệt virus',
                              'word': 'antivirus'},
                          {   'example': 'A firewall blocks unauthorized '
                                         'access.',
                              'ipa': '/ˈfaɪər.wɔːl/',
                              'meaning': 'tường lửa bảo vệ mạng',
                              'word': 'firewall'},
                          {   'example': 'Encryption protects your personal '
                                         'data.',
                              'ipa': '/ɪnˈkrɪp.ʃən/',
                              'meaning': 'mã hóa dữ liệu bảo mật',
                              'word': 'encryption'},
                          {   'example': 'Install a browser extension for ad '
                                         'blocking.',
                              'ipa': '/ˈbraʊ.zər ɪkˈstɛn.ʃən/',
                              'meaning': 'tiện ích mở rộng trình duyệt',
                              'word': 'browser extension'},
                          {   'example': 'Windows is a popular operating '
                                         'system.',
                              'ipa': '/ˈɒp.ər.eɪ.tɪŋ ˈsɪs.təm/',
                              'meaning': 'hệ điều hành máy tính',
                              'word': 'operating system'},
                          {   'example': 'The user interface is clean and '
                                         'easy.',
                              'ipa': '/ˈjuː.zər ˈɪn.tər.feɪs/',
                              'meaning': 'giao diện người dùng',
                              'word': 'user interface'},
                          {   'example': 'Open the email attachment carefully.',
                              'ipa': '/əˈtætʃ.mənt/',
                              'meaning': 'tệp đính kèm email',
                              'word': 'attachment'},
                          {   'example': 'Delete spam emails immediately.',
                              'ipa': '/spæm/',
                              'meaning': 'email rác không mong muốn',
                              'word': 'spam'},
                          {   'example': 'Buy a monthly subscription for the '
                                         'app.',
                              'ipa': '/səbˈskrɪp.ʃən/',
                              'meaning': 'đăng ký dịch vụ trả phí',
                              'word': 'subscription'},
                          {   'example': 'Listen to a podcast while commuting.',
                              'ipa': '/ˈpɒd.kæst/',
                              'meaning': 'chương trình âm thanh trực tuyến',
                              'word': 'podcast'},
                          {   'example': 'Social media connects people '
                                         'worldwide.',
                              'ipa': '/ˈsoʊ.ʃəl ˈmiː.di.ə/',
                              'meaning': 'mạng xã hội trực tuyến',
                              'word': 'social media'},
                          {   'example': 'Post a photo of your lunch.',
                              'ipa': '/poʊst/',
                              'meaning': 'đăng bài lên mạng xã hội',
                              'word': 'post'},
                          {   'example': 'Leave a comment on the post.',
                              'ipa': '/ˈkɒm.ənt/',
                              'meaning': 'bình luận dưới bài đăng',
                              'word': 'comment'},
                          {   'example': 'Like the post if you enjoy it.',
                              'ipa': '/laɪk/',
                              'meaning': 'bấm thích bài đăng',
                              'word': 'like'},
                          {   'example': 'Follow the official account for '
                                         'updates.',
                              'ipa': '/ˈfɒl.oʊ/',
                              'meaning': 'theo dõi tài khoản người dùng',
                              'word': 'follow'},
                          {   'example': 'A smart device learns your '
                                         'preferences.',
                              'ipa': '/smɑːrt dɪˈvaɪs/',
                              'meaning': 'thiết bị thông minh kết nối',
                              'word': 'smart device'},
                          {   'example': 'IoT connects everyday objects '
                                         'online.',
                              'ipa': '/ˌaɪ.oʊˈtiː/',
                              'meaning': 'internet vạn vật kết nối',
                              'word': 'IoT'},
                          {   'example': 'Scan the document with a scanner.',
                              'ipa': '/ˈskæn.ər/',
                              'meaning': 'máy quét tài liệu',
                              'word': 'scanner'},
                          {   'example': 'Use a webcam for online meetings.',
                              'ipa': '/ˈwɛb.kæm/',
                              'meaning': 'camera web cho video call',
                              'word': 'webcam'},
                          {   'example': 'Speak clearly into the microphone.',
                              'ipa': '/ˈmaɪ.krə.foʊn/',
                              'meaning': 'micro thu âm',
                              'word': 'microphone'},
                          {   'example': 'The touchscreen responds to finger '
                                         'touch.',
                              'ipa': '/ˈtʌtʃ.skriːn/',
                              'meaning': 'màn hình cảm ứng',
                              'word': 'touchscreen'},
                          {   'example': 'Use fingerprint to unlock your '
                                         'phone.',
                              'ipa': '/ˈfɪŋ.ɡər.prɪnt/',
                              'meaning': 'vân tay mở khóa thiết bị',
                              'word': 'fingerprint'},
                          {   'example': 'Face ID unlocks the phone instantly.',
                              'ipa': '/feɪs aɪˈdiː/',
                              'meaning': 'nhận dạng khuôn mặt bảo mật',
                              'word': 'face ID'},
                          {   'example': 'A drone took aerial photos of the '
                                         'event.',
                              'ipa': '/droʊn/',
                              'meaning': 'máy bay không người lái',
                              'word': 'drone'},
                          {   'example': 'The 3D printer creates plastic '
                                         'models.',
                              'ipa': '/ˌθriː diː ˈprɪn.tər/',
                              'meaning': 'máy in 3 chiều',
                              'word': '3D printer'},
                          {   'example': 'Wear a VR headset to enter virtual '
                                         'worlds.',
                              'ipa': '/ˌviː.ɑːr ˈhɛd.sɛt/',
                              'meaning': 'kính thực tế ảo',
                              'word': 'VR headset'}],
                'B1': [   {   'example': 'Innovation drives the technology '
                                         'industry forward.',
                              'ipa': '/ˌɪn.əˈveɪ.ʃən/',
                              'meaning': 'sự đổi mới, sáng tạo',
                              'word': 'innovation'},
                          {   'example': 'We need more bandwidth to stream '
                                         'high-quality videos.',
                              'ipa': '/ˈbænd.wɪdθ/',
                              'meaning': 'băng thông',
                              'word': 'bandwidth'},
                          {   'example': 'Cybersecurity is essential for '
                                         'protecting personal data.',
                              'ipa': '/ˌsaɪ.bə.sɪˈkjʊə.rə.ti/',
                              'meaning': 'an ninh mạng',
                              'word': 'cybersecurity'},
                          {   'example': 'Many companies use cloud computing '
                                         'to store their data.',
                              'ipa': '/klaʊd kəmˈpjuː.tɪŋ/',
                              'meaning': 'điện toán đám mây',
                              'word': 'cloud computing'},
                          {   'example': 'Virtual reality games make you feel '
                                         'like you are inside the game.',
                              'ipa': '/ˌvɜː.tʃu.əl riˈæl.ə.ti/',
                              'meaning': 'thực tế ảo',
                              'word': 'virtual reality'},
                          {   'example': 'Smartwatches are the most common '
                                         'type of wearable technology.',
                              'ipa': '/ˈweə.rə.bəl/',
                              'meaning': 'thiết bị đeo được',
                              'word': 'wearable'},
                          {   'example': 'Music streaming services have '
                                         'changed how we listen to songs.',
                              'ipa': '/ˈstriː.mɪŋ/',
                              'meaning': 'phát trực tuyến',
                              'word': 'streaming'},
                          {   'example': 'He loves buying the latest gadgets '
                                         'from tech stores.',
                              'ipa': '/ˈgæʤət/',
                              'meaning': 'thiết bị điện tử nhỏ',
                              'word': 'gadget'},
                          {   'example': 'Innovation drives the technology '
                                         'industry forward.',
                              'ipa': '/ˌɪn.əˈveɪ.ʃən/',
                              'meaning': 'sự đổi mới, sáng tạo',
                              'word': 'invention'},
                          {   'example': 'The hard drive has a storage '
                                         'capacity of 1 terabyte.',
                              'ipa': '/kəˈpæsɪti/',
                              'meaning': 'Dung lượng; năng lực',
                              'word': 'capacity'},
                          {   'example': 'IT security teams protect company '
                                         'data from cyberattacks.',
                              'ipa': '/ˌaɪˈtiː sɪˈkjʊərɪti/',
                              'meaning': 'Bảo mật hệ thống công nghệ thông tin',
                              'word': 'IT security'},
                          {   'example': 'Many companies use cloud computing '
                                         'to store their data.',
                              'ipa': '/klaʊd kəmˈpjuː.tɪŋ/',
                              'meaning': 'điện toán đám mây',
                              'word': 'cloud tech'},
                          {   'example': 'Virtual reality games make you feel '
                                         'like you are inside the game.',
                              'ipa': '/ˌvɜː.tʃu.əl riˈæl.ə.ti/',
                              'meaning': 'thực tế ảo',
                              'word': 'VR'},
                          {   'example': 'Wearable smart tech can monitor your '
                                         'heart rate and steps.',
                              'ipa': '/smɑːrt tɛk/',
                              'meaning': 'Công nghệ thông minh',
                              'word': 'smart tech'},
                          {   'example': 'The live broadcasting of the match '
                                         'attracted millions of viewers.',
                              'ipa': '/ˈbrɔːdkɑːstɪŋ/',
                              'meaning': 'Phát sóng, truyền hình/phát thanh',
                              'word': 'broadcasting'},
                          {   'example': 'Every device in the smart home is '
                                         'connected to the internet.',
                              'ipa': '/dɪˈvaɪs/',
                              'meaning': 'Thiết bị điện tử',
                              'word': 'device'},
                          {   'example': 'Download the SDK to build your app.',
                              'ipa': '/ˌɛs.diːˈkeɪ/',
                              'meaning': 'bộ công cụ phát triển phần mềm',
                              'word': 'SDK'},
                          {   'example': 'Debugging takes a lot of patience.',
                              'ipa': '/diːˈbʌɡ.ɪŋ/',
                              'meaning': 'gỡ lỗi chương trình',
                              'word': 'debugging'},
                          {   'example': 'Agile teams work in short sprints.',
                              'ipa': '/ˈædʒ.aɪl/',
                              'meaning': 'phương pháp phát triển linh hoạt',
                              'word': 'agile'},
                          {   'example': 'Database management keeps data '
                                         'organized.',
                              'ipa': '/ˈdeɪ.tə.beɪs ˈmæn.ɪdʒ.mənt/',
                              'meaning': 'quản trị cơ sở dữ liệu',
                              'word': 'database management'},
                          {   'example': 'Caching reduces server load '
                                         'significantly.',
                              'ipa': '/ˈkæʃ.ɪŋ/',
                              'meaning': 'lưu tạm bộ nhớ đệm tăng tốc',
                              'word': 'caching'},
                          {   'example': 'Load balancing prevents server '
                                         'overload.',
                              'ipa': '/loʊd ˈbæl.ən.sɪŋ/',
                              'meaning': 'cân bằng tải giữa các server',
                              'word': 'load balancing'},
                          {   'example': 'The server achieved 99.9% uptime.',
                              'ipa': '/ˈʌp.taɪm/',
                              'meaning': 'thời gian hệ thống hoạt động ổn định',
                              'word': 'uptime'},
                          {   'example': 'SSL certificate encrypts website '
                                         'data.',
                              'ipa': '/ˌɛs.ɛsˈɛl ˈsɜːr.tɪ.fɪ.kɪt/',
                              'meaning': 'chứng chỉ bảo mật SSL cho web',
                              'word': 'SSL certificate'},
                          {   'example': 'HTTP is a common web protocol.',
                              'ipa': '/ˈproʊ.tə.kɒl/',
                              'meaning': 'giao thức truyền thông mạng',
                              'word': 'protocol'},
                          {   'example': 'A webhook triggers when an event '
                                         'occurs.',
                              'ipa': '/ˈwɛb.hʊk/',
                              'meaning': 'cơ chế gọi lại sự kiện tự động',
                              'word': 'webhook'},
                          {   'example': 'Middleware connects the frontend and '
                                         'backend.',
                              'ipa': '/ˈmɪd.əl.weər/',
                              'meaning': 'phần mềm trung gian kết nối',
                              'word': 'middleware'},
                          {   'example': 'Write unit tests for every function.',
                              'ipa': '/ˈjuː.nɪt tɛst/',
                              'meaning': 'kiểm thử đơn vị từng thành phần nhỏ',
                              'word': 'unit test'},
                          {   'example': 'Integration tests check module '
                                         'interaction.',
                              'ipa': '/ˌɪn.tɪˈɡreɪ.ʃən tɛst/',
                              'meaning': 'kiểm thử tích hợp nhiều module cùng '
                                         'nhau',
                              'word': 'integration test'},
                          {   'example': 'CI/CD automates the deployment '
                                         'pipeline.',
                              'ipa': '/ˌsiː.aɪ.ˌsiːˈdiː/',
                              'meaning': 'tích hợp và triển khai liên tục tự '
                                         'động',
                              'word': 'CI/CD'},
                          {   'example': 'The CI/CD pipeline runs tests '
                                         'automatically.',
                              'ipa': '/ˈpaɪp.laɪn/',
                              'meaning': 'luồng xử lý tự động tuần tự',
                              'word': 'pipeline'},
                          {   'example': 'Check the server log for errors.',
                              'ipa': '/lɒɡ/',
                              'meaning': 'nhật ký sự kiện hệ thống',
                              'word': 'log'},
                          {   'example': 'Monitoring tools alert you to '
                                         'issues.',
                              'ipa': '/ˈmɒn.ɪ.tər.ɪŋ/',
                              'meaning': 'theo dõi hệ thống liên tục',
                              'word': 'monitoring'},
                          {   'example': 'Set up alerting for downtime events.',
                              'ipa': '/əˈlɜːr.tɪŋ/',
                              'meaning': 'cảnh báo khi có sự cố hệ thống',
                              'word': 'alerting'},
                          {   'example': 'The incident was resolved in 30 '
                                         'minutes.',
                              'ipa': '/ˈɪn.sɪ.dənt/',
                              'meaning': 'sự cố kỹ thuật cần xử lý ngay',
                              'word': 'incident'},
                          {   'example': 'Perform a rollback if the update '
                                         'fails.',
                              'ipa': '/ˈroʊl.bæk/',
                              'meaning': 'quay lại phiên bản trước sau lỗi',
                              'word': 'rollback'},
                          {   'example': 'We released a hotfix for the '
                                         'critical bug.',
                              'ipa': '/ˈhɒt.fɪks/',
                              'meaning': 'bản vá lỗi khẩn cấp',
                              'word': 'hotfix'},
                          {   'example': 'Accumulated technical debt slows '
                                         'teams down.',
                              'ipa': '/ˈtɛk.nɪ.kəl dɛt/',
                              'meaning': 'nợ kỹ thuật do bỏ qua chất lượng',
                              'word': 'technical debt'},
                          {   'example': 'Software architecture decisions are '
                                         'hard to reverse.',
                              'ipa': '/ˈsɒft.weər ˈɑːr.kɪ.tɛk.tʃər/',
                              'meaning': 'kiến trúc phần mềm tổng thể hệ thống',
                              'word': 'software architecture'},
                          {   'example': 'Data modeling ensures a clean '
                                         'database design.',
                              'ipa': '/ˈdeɪ.tə ˈmɒd.əl.ɪŋ/',
                              'meaning': 'mô hình hóa dữ liệu thiết kế cơ sở '
                                         'dữ liệu',
                              'word': 'data modeling'},
                          {   'example': 'System design interviews test '
                                         'architecture skills.',
                              'ipa': '/ˈsɪs.təm dɪˈzaɪn/',
                              'meaning': 'thiết kế hệ thống phần mềm quy mô '
                                         'lớn',
                              'word': 'system design'},
                          {   'example': 'Java is an object-oriented language.',
                              'ipa': '/ˈɒb.dʒɪkt ˈɔːr.i.ɛn.tɪd/',
                              'meaning': 'lập trình hướng đối tượng OOP',
                              'word': 'object-oriented'},
                          {   'example': 'Abstraction hides implementation '
                                         'details.',
                              'ipa': '/æbˈstræk.ʃən/',
                              'meaning': 'trừu tượng hóa ẩn đi chi tiết phức '
                                         'tạp',
                              'word': 'abstraction'},
                          {   'example': 'Encapsulation protects internal '
                                         'state.',
                              'ipa': '/ɪnˌkæp.sjʊˈleɪ.ʃən/',
                              'meaning': 'đóng gói dữ liệu và phương thức cùng '
                                         'nhau',
                              'word': 'encapsulation'},
                          {   'example': 'Polymorphism enables flexible code '
                                         'reuse.',
                              'ipa': '/ˌpɒl.iˈmɔːr.fɪzm/',
                              'meaning': 'tính đa hình cho phép nhiều kiểu '
                                         'dùng chung',
                              'word': 'polymorphism'},
                          {   'example': 'Inheritance reduces code '
                                         'duplication.',
                              'ipa': '/ɪnˈhɛr.ɪ.təns/',
                              'meaning': 'kế thừa thuộc tính từ lớp cha',
                              'word': 'inheritance'},
                          {   'example': 'Dependency injection improves '
                                         'testability.',
                              'ipa': '/dɪˈpɛn.dən.si ɪnˈdʒɛk.ʃən/',
                              'meaning': 'tiêm phụ thuộc giúp code dễ kiểm thử',
                              'word': 'dependency injection'},
                          {   'example': 'Event sourcing creates an audit '
                                         'trail.',
                              'ipa': '/ɪˈvɛnt ˈsɔːr.sɪŋ/',
                              'meaning': 'lưu trữ sự kiện ghi lại mọi thay đổi',
                              'word': 'event sourcing'},
                          {   'example': 'CQRS separates reads and writes.',
                              'ipa': '/siː.kjuː.ɑːr.ɛs/',
                              'meaning': 'phân tách lệnh và truy vấn trong '
                                         'kiến trúc',
                              'word': 'CQRS'},
                          {   'example': 'Kafka is a popular message broker.',
                              'ipa': '/ˈmɛs.ɪdʒ ˈbroʊ.kər/',
                              'meaning': 'môi giới tin nhắn kết nối dịch vụ',
                              'word': 'message broker'}],
                'B2': [   {   'example': 'Distributed systems handle massive '
                                         'traffic.',
                              'ipa': '/dɪˈstrɪb.jʊ.tɪd ˈsɪs.təm/',
                              'meaning': 'hệ thống phân tán nhiều node',
                              'word': 'distributed system'},
                          {   'example': 'Raft is a consensus algorithm for '
                                         'clusters.',
                              'ipa': '/kənˈsɛn.səs ˈæl.ɡə.rɪ.ðəm/',
                              'meaning': 'thuật toán đồng thuận trong hệ phân '
                                         'tán',
                              'word': 'consensus algorithm'},
                          {   'example': 'Eventual consistency trades '
                                         'consistency for availability.',
                              'ipa': '/ɪˈvɛn.tʃʊ.əl kənˈsɪs.tən.si/',
                              'meaning': 'tính nhất quán cuối cùng trong phân '
                                         'tán',
                              'word': 'eventual consistency'},
                          {   'example': 'The CAP theorem limits distributed '
                                         'systems.',
                              'ipa': '/kæp ˈθɪər.əm/',
                              'meaning': 'định lý CAP về hệ thống phân tán',
                              'word': 'CAP theorem'},
                          {   'example': 'Database sharding improves read '
                                         'performance.',
                              'ipa': '/ˈʃɑːr.dɪŋ/',
                              'meaning': 'phân mảnh dữ liệu theo chiều ngang',
                              'word': 'sharding'},
                          {   'example': 'Data replication ensures high '
                                         'availability.',
                              'ipa': '/ˌrɛp.lɪˈkeɪ.ʃən/',
                              'meaning': 'sao chép dữ liệu sang nhiều node',
                              'word': 'replication'},
                          {   'example': 'Fault tolerance keeps services '
                                         'running.',
                              'ipa': '/fɔːlt ˈtɒl.ər.əns/',
                              'meaning': 'khả năng chịu lỗi của hệ thống',
                              'word': 'fault tolerance'},
                          {   'example': 'Observability includes logs, '
                                         'metrics, traces.',
                              'ipa': '/əbˌzɜːr.vəˈbɪl.ɪ.ti/',
                              'meaning': 'khả năng quan sát toàn diện hệ thống',
                              'word': 'observability'},
                          {   'example': 'Distributed tracing finds '
                                         'performance bottlenecks.',
                              'ipa': '/ˈtreɪ.sɪŋ/',
                              'meaning': 'theo dõi luồng yêu cầu qua hệ thống',
                              'word': 'tracing'},
                          {   'example': 'A service mesh manages microservice '
                                         'traffic.',
                              'ipa': '/ˈsɜːr.vɪs mɛʃ/',
                              'meaning': 'lưới dịch vụ quản lý giao tiếp '
                                         'microservice',
                              'word': 'service mesh'},
                          {   'example': 'Kubernetes orchestrates '
                                         'containerized workloads.',
                              'ipa': '/ˌkjuː.bərˈniː.tɪs/',
                              'meaning': 'nền tảng điều phối container phổ '
                                         'biến',
                              'word': 'Kubernetes'},
                          {   'example': 'Docker packages apps in containers.',
                              'ipa': '/ˈdɒk.ər/',
                              'meaning': 'công cụ container hóa ứng dụng',
                              'word': 'Docker'},
                          {   'example': 'Terraform enables infrastructure as '
                                         'code.',
                              'ipa': '/ˈɪn.frə.strʌk.tʃər æz koʊd/',
                              'meaning': 'quản lý hạ tầng bằng mã nguồn',
                              'word': 'infrastructure as code'},
                          {   'example': 'Serverless functions scale '
                                         'automatically.',
                              'ipa': '/ˈsɜːr.vər.lɪs/',
                              'meaning': 'điện toán không máy chủ trả theo '
                                         'dùng',
                              'word': 'serverless'},
                          {   'example': 'Edge computing reduces cloud '
                                         'latency.',
                              'ipa': '/ɛdʒ kəmˈpjuː.tɪŋ/',
                              'meaning': 'điện toán tại biên gần nguồn dữ liệu',
                              'word': 'edge computing'},
                          {   'example': 'A message queue decouples services.',
                              'ipa': '/ˈmɛs.ɪdʒ kjuː/',
                              'meaning': 'hàng đợi tin nhắn giữa các dịch vụ',
                              'word': 'message queue'},
                          {   'example': 'Event-driven systems react to state '
                                         'changes.',
                              'ipa': '/ɪˈvɛnt ˈdrɪv.ən/',
                              'meaning': 'kiến trúc hướng sự kiện phản ứng',
                              'word': 'event-driven'},
                          {   'example': 'A data pipeline moves data from '
                                         'source to warehouse.',
                              'ipa': '/ˈdeɪ.tə ˈpaɪp.laɪn/',
                              'meaning': 'luồng xử lý dữ liệu từ đầu đến cuối',
                              'word': 'data pipeline'},
                          {   'example': 'The data warehouse stores historical '
                                         'reports.',
                              'ipa': '/ˈdeɪ.tə ˈweər.haʊs/',
                              'meaning': 'kho dữ liệu lớn phục vụ phân tích',
                              'word': 'data warehouse'},
                          {   'example': 'ETL pipelines prepare raw data for '
                                         'analysis.',
                              'ipa': '/ˌiː.tiːˈɛl/',
                              'meaning': 'trích xuất chuyển đổi và tải dữ liệu',
                              'word': 'ETL'},
                          {   'example': 'Real-time processing powers live '
                                         'dashboards.',
                              'ipa': '/ˌriːl ˈtaɪm ˈprɒs.ɛs.ɪŋ/',
                              'meaning': 'xử lý dữ liệu theo thời gian thực',
                              'word': 'real-time processing'},
                          {   'example': 'Kafka enables stream processing at '
                                         'scale.',
                              'ipa': '/striːm ˈprɒs.ɛs.ɪŋ/',
                              'meaning': 'xử lý luồng dữ liệu liên tục',
                              'word': 'stream processing'},
                          {   'example': 'Cryptography underlies all internet '
                                         'security.',
                              'ipa': '/krɪpˈtɒɡ.rə.fi/',
                              'meaning': 'mật mã học bảo vệ dữ liệu',
                              'word': 'cryptography'},
                          {   'example': 'Zero-trust assumes no user is '
                                         'trusted.',
                              'ipa': '/ˈzɪər.oʊ trʌst/',
                              'meaning': 'mô hình bảo mật không tin tưởng mặc '
                                         'định',
                              'word': 'zero-trust'},
                          {   'example': 'Penetration testing finds security '
                                         'vulnerabilities.',
                              'ipa': '/ˌpɛn.ɪˈtreɪ.ʃən ˈtɛs.tɪŋ/',
                              'meaning': 'kiểm tra xâm nhập tìm lỗ hổng bảo '
                                         'mật',
                              'word': 'penetration testing'},
                          {   'example': 'Patch all known vulnerabilities '
                                         'quickly.',
                              'ipa': '/ˌvʌl.nər.əˈbɪl.ɪ.ti/',
                              'meaning': 'lỗ hổng bảo mật trong hệ thống',
                              'word': 'vulnerability'},
                          {   'example': 'Hackers use exploits to breach '
                                         'systems.',
                              'ipa': '/ˈɛk.splɔɪt/',
                              'meaning': 'khai thác lỗ hổng tấn công hệ thống',
                              'word': 'exploit'},
                          {   'example': 'Phishing emails steal login '
                                         'credentials.',
                              'ipa': '/ˈfɪʃ.ɪŋ/',
                              'meaning': 'tấn công giả mạo lừa đảo thông tin',
                              'word': 'phishing'},
                          {   'example': 'Ransomware encrypts files and '
                                         'demands payment.',
                              'ipa': '/ˈræn.səm.weər/',
                              'meaning': 'phần mềm mã độc đòi tiền chuộc',
                              'word': 'ransomware'},
                          {   'example': 'Zero-day exploits are especially '
                                         'dangerous.',
                              'ipa': '/ˈzɪər.oʊ deɪ/',
                              'meaning': 'lỗ hổng chưa được vá bởi nhà phát '
                                         'triển',
                              'word': 'zero-day'},
                          {   'example': 'Stolen data is sold on the dark web.',
                              'ipa': '/dɑːrk wɛb/',
                              'meaning': 'mạng internet ẩn truy cập qua Tor',
                              'word': 'dark web'},
                          {   'example': 'Smart contracts execute '
                                         'automatically on blockchain.',
                              'ipa': '/smɑːrt ˈkɒn.trækt/',
                              'meaning': 'hợp đồng thông minh tự động thực thi',
                              'word': 'smart contract'},
                          {   'example': 'Decentralized apps run on '
                                         'blockchain.',
                              'ipa': '/diːˈsɛn.trə.laɪzd/',
                              'meaning': 'phi tập trung không có cơ quan kiểm '
                                         'soát',
                              'word': 'decentralized'},
                          {   'example': 'A token economy rewards platform '
                                         'participants.',
                              'ipa': '/ˈtoʊ.kən ɪˈkɒn.ə.mi/',
                              'meaning': 'nền kinh tế token trong hệ sinh thái '
                                         'số',
                              'word': 'token economy'},
                          {   'example': 'WebAssembly runs near-native code in '
                                         'browsers.',
                              'ipa': '/ˌwɛb.əˈsɛm.bli/',
                              'meaning': 'ngôn ngữ trung gian web hiệu suất '
                                         'cao',
                              'word': 'WebAssembly'},
                          {   'example': 'A PWA works offline like a native '
                                         'app.',
                              'ipa': '/ˌpiː.dʌb.ljuːˈeɪ/',
                              'meaning': 'ứng dụng web tiến bộ chạy offline',
                              'word': 'PWA'},
                          {   'example': 'GraphQL lets clients request '
                                         'specific data.',
                              'ipa': '/ˈɡræf.kjuː.ɛl/',
                              'meaning': 'ngôn ngữ truy vấn API linh hoạt',
                              'word': 'GraphQL'},
                          {   'example': 'OAuth allows third-party login.',
                              'ipa': '/ˈoʊ.ɔːθ/',
                              'meaning': 'giao thức ủy quyền truy cập mở',
                              'word': 'OAuth'},
                          {   'example': 'JWT tokens verify user identity '
                                         'securely.',
                              'ipa': '/ˌdʒeɪ.dʌb.ljuːˈtiː/',
                              'meaning': 'token xác thực JSON phi trạng thái',
                              'word': 'JWT'},
                          {   'example': 'TDD requires writing tests before '
                                         'code.',
                              'ipa': '/ˌtiː.diːˈdiː/',
                              'meaning': 'phát triển hướng kiểm thử trước khi '
                                         'code',
                              'word': 'TDD'},
                          {   'example': 'BDD describes features in plain '
                                         'language.',
                              'ipa': '/ˌbiː.diːˈdiː/',
                              'meaning': 'phát triển hướng hành vi người dùng',
                              'word': 'BDD'},
                          {   'example': 'The singleton is a common design '
                                         'pattern.',
                              'ipa': '/dɪˈzaɪn ˈpæt.ərn/',
                              'meaning': 'mẫu thiết kế giải quyết vấn đề phổ '
                                         'biến',
                              'word': 'design pattern'},
                          {   'example': 'SOLID principles guide clean code '
                                         'design.',
                              'ipa': '/ˈsɒl.ɪd ˈprɪn.sɪ.pəlz/',
                              'meaning': 'nguyên lý thiết kế phần mềm hướng '
                                         'đối tượng',
                              'word': 'SOLID principles'},
                          {   'example': 'Clean code is easy to read and '
                                         'maintain.',
                              'ipa': '/kliːn koʊd/',
                              'meaning': 'mã nguồn sạch dễ đọc và bảo trì',
                              'word': 'clean code'},
                          {   'example': 'A code smell suggests refactoring is '
                                         'needed.',
                              'ipa': '/koʊd smɛl/',
                              'meaning': 'dấu hiệu mã nguồn kém chất lượng',
                              'word': 'code smell'},
                          {   'example': 'Pair programming catches errors '
                                         'early.',
                              'ipa': '/pɛər ˈproʊ.ɡræm.ɪŋ/',
                              'meaning': 'lập trình đôi cùng một máy tính',
                              'word': 'pair programming'},
                          {   'example': 'Mob programming builds shared '
                                         'understanding.',
                              'ipa': '/mɒb ˈproʊ.ɡræm.ɪŋ/',
                              'meaning': 'lập trình nhóm toàn bộ trên cùng '
                                         'task',
                              'word': 'mob programming'},
                          {   'example': 'Write a technical specification '
                                         'before coding.',
                              'ipa': '/ˈtɛk.nɪ.kəl ˌspɛs.ɪ.fɪˈkeɪ.ʃən/',
                              'meaning': 'bản đặc tả kỹ thuật chi tiết dự án',
                              'word': 'technical specification'},
                          {   'example': 'ADRs document why architecture '
                                         'choices were made.',
                              'ipa': '/ˈɑːr.kɪ.tɛk.tʃər dɪˈsɪʒ.ən ˈrɛk.ərd/',
                              'meaning': 'ghi lại quyết định kiến trúc quan '
                                         'trọng',
                              'word': 'architecture decision record'},
                          {   'example': 'Confidential computing protects data '
                                         'in use.',
                              'ipa': '/ˌkɒn.fɪˈdɛn.ʃəl kəmˈpjuː.tɪŋ/',
                              'meaning': 'điện toán bảo mật xử lý dữ liệu mã '
                                         'hóa',
                              'word': 'confidential computing'}],
                'C1': [   {   'example': 'Neuromorphic computing mimics brain '
                                         'structure.',
                              'ipa': '/ˌnjʊər.oʊˈmɔːr.fɪk kəmˈpjuː.tɪŋ/',
                              'meaning': 'điện toán mô phỏng kiến trúc não bộ',
                              'word': 'neuromorphic computing'},
                          {   'example': 'Quantum computing solves complex '
                                         'optimization problems.',
                              'ipa': '/ˈkwɒn.təm kəmˈpjuː.tɪŋ/',
                              'meaning': 'điện toán lượng tử dùng qubit',
                              'word': 'quantum computing'},
                          {   'example': 'A qubit can be 0 and 1 '
                                         'simultaneously.',
                              'ipa': '/ˈkjuː.bɪt/',
                              'meaning': 'bit lượng tử có thể ở trạng thái '
                                         'chồng chất',
                              'word': 'qubit'},
                          {   'example': 'Superposition enables parallel '
                                         'computation.',
                              'ipa': '/ˌsuː.pər.pəˈzɪʃ.ən/',
                              'meaning': 'trạng thái chồng chất lượng tử',
                              'word': 'superposition'},
                          {   'example': 'Quantum entanglement links qubits '
                                         'instantly.',
                              'ipa': '/ˈkwɒn.təm ɪnˈtæŋ.ɡəl.mənt/',
                              'meaning': 'vướng mắc lượng tử giữa các qubit',
                              'word': 'quantum entanglement'},
                          {   'example': 'Photonic chips process data at light '
                                         'speed.',
                              'ipa': '/fəˈtɒn.ɪk tʃɪp/',
                              'meaning': 'chip quang tử dùng ánh sáng thay '
                                         'điện',
                              'word': 'photonic chip'},
                          {   'example': 'Exascale computing enables climate '
                                         'simulations.',
                              'ipa': '/ˈɛk.sə.skeɪl kəmˈpjuː.tɪŋ/',
                              'meaning': 'điện toán exascale vượt 10^18 phép '
                                         'tính',
                              'word': 'exascale computing'},
                          {   'example': 'Formal verification proves program '
                                         'correctness.',
                              'ipa': '/ˈfɔːr.məl ˌvɛr.ɪ.fɪˈkeɪ.ʃən/',
                              'meaning': 'xác minh chính xác toán học của phần '
                                         'mềm',
                              'word': 'formal verification'},
                          {   'example': 'Type theory ensures program '
                                         'correctness.',
                              'ipa': '/taɪp ˈθɪər.i/',
                              'meaning': 'lý thuyết kiểu dữ liệu trong ngôn '
                                         'ngữ lập trình',
                              'word': 'type theory'},
                          {   'example': 'Dependent types encode invariants in '
                                         'code.',
                              'ipa': '/dɪˈpɛn.dənt taɪps/',
                              'meaning': 'kiểu phụ thuộc giá trị trong lập '
                                         'trình',
                              'word': 'dependent types'},
                          {   'example': 'Functional programming avoids '
                                         'mutable state.',
                              'ipa': '/ˈfʌŋk.ʃən.əl ˈproʊ.ɡræm.ɪŋ/',
                              'meaning': 'lập trình hàm thuần túy không trạng '
                                         'thái',
                              'word': 'functional programming'},
                          {   'example': 'Monads handle side effects in '
                                         'functional code.',
                              'ipa': '/ˈmɒn.æd/',
                              'meaning': 'cấu trúc đơn nguyên trong lập trình '
                                         'hàm',
                              'word': 'monad'},
                          {   'example': 'Lambda calculus forms the basis of '
                                         'functional languages.',
                              'ipa': '/ˈlæm.də ˈkæl.kjʊ.ləs/',
                              'meaning': 'phép tính lambda nền tảng lập trình '
                                         'hàm',
                              'word': 'lambda calculus'},
                          {   'example': 'Rust provides memory safety without '
                                         'garbage collection.',
                              'ipa': '/ˈmɛm.ər.i ˈseɪf.ti/',
                              'meaning': 'an toàn bộ nhớ ngăn lỗi buffer '
                                         'overflow',
                              'word': 'memory safety'},
                          {   'example': 'Garbage collection prevents memory '
                                         'leaks.',
                              'ipa': '/ˈɡɑːr.bɪdʒ kəˈlɛk.ʃən/',
                              'meaning': 'thu gom rác giải phóng bộ nhớ tự '
                                         'động',
                              'word': 'garbage collection'},
                          {   'example': 'Concurrency improves application '
                                         'responsiveness.',
                              'ipa': '/kənˈkɜːr.ən.si/',
                              'meaning': 'lập trình đồng thời xử lý nhiều tác '
                                         'vụ',
                              'word': 'concurrency'},
                          {   'example': 'Parallelism uses multiple CPU cores '
                                         'simultaneously.',
                              'ipa': '/ˈpær.ə.lɛl.ɪzm/',
                              'meaning': 'song song hóa thực sự trên nhiều '
                                         'nhân CPU',
                              'word': 'parallelism'},
                          {   'example': 'Async programming prevents blocking '
                                         'the main thread.',
                              'ipa': '/eɪˈsɪŋk ˈproʊ.ɡræm.ɪŋ/',
                              'meaning': 'lập trình bất đồng bộ không chặn '
                                         'luồng chính',
                              'word': 'async programming'},
                          {   'example': 'Node.js uses an event loop for '
                                         'non-blocking I/O.',
                              'ipa': '/ɪˈvɛnt luːp/',
                              'meaning': 'vòng lặp sự kiện xử lý I/O bất đồng '
                                         'bộ',
                              'word': 'event loop'},
                          {   'example': 'The actor model avoids shared memory '
                                         'issues.',
                              'ipa': '/ˈæk.tər ˈmɒd.əl/',
                              'meaning': 'mô hình diễn viên xử lý đồng thời '
                                         'qua tin nhắn',
                              'word': 'actor model'},
                          {   'example': 'CRDTs enable conflict-free '
                                         'distributed edits.',
                              'ipa': '/ˌsiː.ɑːr.diːˈtiː/',
                              'meaning': 'kiểu dữ liệu hội tụ phân tán nhất '
                                         'quán',
                              'word': 'CRDT'},
                          {   'example': 'Homomorphic encryption computes on '
                                         'encrypted data.',
                              'ipa': '/ˌhɒm.ə.ˈmɔːr.fɪk ɪnˈkrɪp.ʃən/',
                              'meaning': 'mã hóa đồng cấu tính toán trên dữ '
                                         'liệu mã hóa',
                              'word': 'homomorphic encryption'},
                          {   'example': 'Zero-knowledge proofs verify without '
                                         'revealing data.',
                              'ipa': '/ˈzɪər.oʊ ˈnɒl.ɪdʒ pruːf/',
                              'meaning': 'bằng chứng không tiết lộ thông tin '
                                         'bí mật',
                              'word': 'zero-knowledge proof'},
                          {   'example': 'Post-quantum cryptography resists '
                                         'quantum attacks.',
                              'ipa': '/ˌpoʊst ˈkwɒn.təm krɪpˈtɒɡ.rə.fi/',
                              'meaning': 'mật mã hậu lượng tử chống máy tính '
                                         'lượng tử',
                              'word': 'post-quantum cryptography'},
                          {   'example': 'Byzantine faults occur when nodes '
                                         'send conflicting messages.',
                              'ipa': '/ˈbɪz.ən.tiːn fɔːlt/',
                              'meaning': 'lỗi Byzantine khi node gửi thông tin '
                                         'sai',
                              'word': 'Byzantine fault'},
                          {   'example': 'Paxos solves consensus in '
                                         'distributed systems.',
                              'ipa': '/ˈpæk.sɒs/',
                              'meaning': 'giao thức đồng thuận phân tán cổ '
                                         'điển',
                              'word': 'Paxos'},
                          {   'example': 'Raft consensus is easier to '
                                         'implement than Paxos.',
                              'ipa': '/ræft kənˈsɛn.səs/',
                              'meaning': 'thuật toán đồng thuận dễ hiểu hơn '
                                         'Paxos',
                              'word': 'Raft consensus'},
                          {   'example': 'LSM trees optimize write-heavy '
                                         'workloads.',
                              'ipa': '/lɒɡ ˈstrʌk.tʃərd mɜːrdʒ/',
                              'meaning': 'cấu trúc lưu trữ LSM tối ưu ghi dữ '
                                         'liệu',
                              'word': 'log-structured merge'},
                          {   'example': 'Column stores accelerate analytical '
                                         'queries.',
                              'ipa': '/ˈkɒl.əm stɔːr/',
                              'meaning': 'cơ sở dữ liệu lưu theo cột tối ưu '
                                         'phân tích',
                              'word': 'column store'},
                          {   'example': 'Vector databases power semantic '
                                         'search.',
                              'ipa': '/ˈvɛk.tər ˈdeɪ.tə.beɪs/',
                              'meaning': 'cơ sở dữ liệu vector cho tìm kiếm '
                                         'tương đồng',
                              'word': 'vector database'},
                          {   'example': 'WASM enables high-performance web '
                                         'applications.',
                              'ipa': '/ˈwæz.əm/',
                              'meaning': 'WebAssembly định dạng nhị phân hiệu '
                                         'suất cao',
                              'word': 'WASM'},
                          {   'example': 'eBPF enables kernel-level '
                                         'observability.',
                              'ipa': '/ˌiː.biː.piːˈɛf/',
                              'meaning': 'lọc gói mở rộng Berkeley trong nhân '
                                         'Linux',
                              'word': 'eBPF'},
                          {   'example': 'RDMA enables low-latency network '
                                         'communication.',
                              'ipa': '/ˌɑːr.diː.ɛmˈeɪ/',
                              'meaning': 'truy cập bộ nhớ từ xa trực tiếp tốc '
                                         'độ cao',
                              'word': 'RDMA'},
                          {   'example': 'NUMA affects memory access patterns '
                                         'on servers.',
                              'ipa': '/ˈnjuː.mə ˈɑːr.kɪ.tɛk.tʃər/',
                              'meaning': 'kiến trúc bộ nhớ không đồng nhất đa '
                                         'nhân',
                              'word': 'NUMA architecture'},
                          {   'example': 'Kernel bypass reduces network '
                                         'latency.',
                              'ipa': '/ˈkɜːr.nəl ˈbaɪ.pæs/',
                              'meaning': 'bỏ qua nhân hệ điều hành để tăng tốc '
                                         'I/O',
                              'word': 'kernel bypass'},
                          {   'example': 'FinOps optimizes cloud spending.',
                              'ipa': '/ˈfɪn.ɒps/',
                              'meaning': 'quản lý tài chính điện toán đám mây '
                                         'hiệu quả',
                              'word': 'FinOps'},
                          {   'example': 'Platform engineering improves '
                                         'developer experience.',
                              'ipa': '/ˈplæt.fɔːrm ˌɛn.dʒɪˈnɪər.ɪŋ/',
                              'meaning': 'xây dựng nền tảng nội bộ tự phục vụ '
                                         'dev',
                              'word': 'platform engineering'},
                          {   'example': 'Chaos engineering tests system '
                                         'resilience.',
                              'ipa': '/ˈkeɪ.ɒs ˌɛn.dʒɪˈnɪər.ɪŋ/',
                              'meaning': 'kiểm tra hệ thống bằng cách cố tình '
                                         'gây lỗi',
                              'word': 'chaos engineering'},
                          {   'example': 'Supply chain attacks target software '
                                         'dependencies.',
                              'ipa': '/səˈplaɪ tʃeɪn əˈtæk/',
                              'meaning': 'tấn công vào chuỗi cung ứng phần mềm',
                              'word': 'supply chain attack'},
                          {   'example': 'An SBOM lists all software '
                                         'components used.',
                              'ipa': '/ˈsɒft.weər bɪl əv məˈtɪər.i.əlz/',
                              'meaning': 'danh sách thành phần phần mềm đầy đủ',
                              'word': 'software bill of materials'},
                          {   'example': 'Ephemeral environments improve '
                                         'developer speed.',
                              'ipa': '/ɪˈfɛm.ər.əl ɪnˈvaɪər.ən.mənt/',
                              'meaning': 'môi trường tạm thời tạo và xóa theo '
                                         'yêu cầu',
                              'word': 'ephemeral environment'},
                          {   'example': 'GitOps uses Git as the source of '
                                         'truth.',
                              'ipa': '/ˈɡɪt.ɒps/',
                              'meaning': 'triển khai hạ tầng dùng Git làm '
                                         'nguồn sự thật',
                              'word': 'GitOps'},
                          {   'example': 'Policy as code enforces compliance '
                                         'automatically.',
                              'ipa': '/ˈpɒl.ɪ.si æz koʊd/',
                              'meaning': 'quản lý chính sách hệ thống bằng mã',
                              'word': 'policy as code'},
                          {   'example': 'A self-healing system restarts '
                                         'failed services.',
                              'ipa': '/sɛlf ˈhiː.lɪŋ ˈsɪs.təm/',
                              'meaning': 'hệ thống tự phục hồi sau sự cố tự '
                                         'động',
                              'word': 'self-healing system'},
                          {   'example': 'Semantic versioning communicates '
                                         'breaking changes.',
                              'ipa': '/sɪˈmæn.tɪk ˈvɜːr.ʒən.ɪŋ/',
                              'meaning': 'đánh số phiên bản ngữ nghĩa '
                                         'MAJOR.MINOR.PATCH',
                              'word': 'semantic versioning'},
                          {   'example': 'Idempotency ensures safe API '
                                         'retries.',
                              'ipa': '/ˌaɪ.dɛmˈpoʊ.tən.si/',
                              'meaning': 'tính lũy đẳng: thực hiện nhiều lần '
                                         'ra cùng kết quả',
                              'word': 'idempotency'},
                          {   'example': 'The eventual consistency model suits '
                                         'NoSQL stores.',
                              'ipa': '/ɪˈvɛn.tʃʊ.əl kənˈsɪs.tən.si ˈmɒd.əl/',
                              'meaning': 'mô hình nhất quán cuối cùng trong hệ '
                                         'phân tán',
                              'word': 'eventual consistency model'},
                          {   'example': 'Monitor p99 latency for tail latency '
                                         'issues.',
                              'ipa': '/ˈleɪ.tən.si pərˈsɛn.taɪl/',
                              'meaning': 'phân vị độ trễ đo lường hiệu suất '
                                         'thực sự',
                              'word': 'latency percentile'},
                          {   'example': 'An SLO defines the reliability '
                                         'target.',
                              'ipa': '/ˌɛs.ɛlˈoʊ/',
                              'meaning': 'mục tiêu mức độ dịch vụ cần đạt được',
                              'word': 'SLO'},
                          {   'example': 'The SLA guarantees 99.9% uptime.',
                              'ipa': '/ˌɛs.ɛlˈeɪ/',
                              'meaning': 'thỏa thuận mức độ dịch vụ với khách '
                                         'hàng',
                              'word': 'SLA'}]},
    'travel': {   'A1': [   {   'example': 'Please show your ticket at the '
                                           'gate.',
                                'ipa': '/ˈtɪkɪt/',
                                'meaning': 'Vé xe/tàu/máy bay',
                                'word': 'Ticket'},
                            {   'example': 'We booked a room at the central '
                                           'hotel.',
                                'ipa': '/həʊˈtel/',
                                'meaning': 'Khách sạn',
                                'word': 'Hotel'},
                            {   'example': 'I go to school by bus every day.',
                                'ipa': '/bʌs/',
                                'meaning': 'Xe buýt',
                                'word': 'Bus'},
                            {   'example': 'We need a map to find our way.',
                                'ipa': '/mæp/',
                                'meaning': 'Bản đồ',
                                'word': 'Map'},
                            {   'example': "Don't forget to pack your "
                                           'passport.',
                                'ipa': '/ˈpɑːspɔːt/',
                                'meaning': 'Hộ chiếu',
                                'word': 'Passport'},
                            {   'example': 'I will fly to Paris tomorrow.',
                                'ipa': '/flaɪ/',
                                'meaning': 'Bay, đi máy bay',
                                'word': 'Fly'},
                            {   'example': 'We played soccer on the beach.',
                                'ipa': '/biːtʃ/',
                                'meaning': 'Bãi biển',
                                'word': 'Beach'},
                            {   'example': 'Put your camera in the bag.',
                                'ipa': '/bæɡ/',
                                'meaning': 'Túi xách, ba lô',
                                'word': 'Bag'},
                            {   'example': 'You must show your security pass '
                                           'to enter.',
                                'ipa': '/pɑːs/',
                                'meaning': 'Thẻ thông hành, thẻ ra vào',
                                'word': 'Pass'},
                            {   'example': 'We spent the night at a cozy inn '
                                           'near the forest.',
                                'ipa': '/ɪn/',
                                'meaning': 'Quán trọ, nhà nghỉ nhỏ',
                                'word': 'Inn'},
                            {   'example': 'She hired a personal coach to '
                                           'improve her tennis skills.',
                                'ipa': '/kəʊtʃ/',
                                'meaning': 'Huấn luyện viên',
                                'word': 'Coach'},
                            {   'example': 'We need an atlas to find our way.',
                                'ipa': '/ˈæt.ləs/',
                                'meaning': 'Bản đồ, tập bản đồ',
                                'word': 'Atlas'},
                            {   'example': 'You need a valid visa to enter the '
                                           'United States.',
                                'ipa': '/ˈviːzə/',
                                'meaning': 'Thị thực nhập cảnh',
                                'word': 'Visa'},
                            {   'example': 'I love to travel to new countries.',
                                'ipa': '/ˈtræv.əl/',
                                'meaning': 'Đi du lịch, di chuyển',
                                'word': 'Travel'},
                            {   'example': 'We played soccer on the coast.',
                                'ipa': '/kəʊst/',
                                'meaning': 'Bờ biển',
                                'word': 'Coast'},
                            {   'example': 'They helped me carry my luggage.',
                                'ipa': '/ˈləgɪʤ/',
                                'meaning': 'Hành lý',
                                'word': 'Luggage'},
                            {   'example': 'The plane flies very high.',
                                'ipa': '/pleɪn/',
                                'meaning': 'máy bay',
                                'word': 'plane'},
                            {   'example': 'We rented a small car.',
                                'ipa': '/kɑːr/',
                                'meaning': 'xe ô tô',
                                'word': 'car'},
                            {   'example': 'The road is very long.',
                                'ipa': '/rəʊd/',
                                'meaning': 'con đường',
                                'word': 'road'},
                            {   'example': 'My room is on the second floor.',
                                'ipa': '/ruːm/',
                                'meaning': 'căn phòng, phòng nghỉ',
                                'word': 'room'},
                            {   'example': 'They saw land after weeks at sea.',
                                'ipa': '/lænd/',
                                'meaning': 'đất liền, vùng đất',
                                'word': 'land'},
                            {   'example': 'We walked around the lake.',
                                'ipa': '/leɪk/',
                                'meaning': 'hồ nước',
                                'word': 'lake'},
                            {   'example': 'The park is full of flowers.',
                                'ipa': '/pɑːk/',
                                'meaning': 'công viên',
                                'word': 'park'},
                            {   'example': 'This street is very quiet.',
                                'ipa': '/striːt/',
                                'meaning': 'đường phố',
                                'word': 'street'},
                            {   'example': 'What time does the tour start?',
                                'ipa': '/taɪm/',
                                'meaning': 'thời gian, giờ giấc',
                                'word': 'time'},
                            {   'example': 'They took a small boat to the '
                                           'island.',
                                'ipa': '/bəʊt/',
                                'meaning': 'thuyền, tàu nhỏ',
                                'word': 'boat'},
                            {   'example': 'The ship docked at the port.',
                                'ipa': '/pɔːt/',
                                'meaning': 'cảng, hải cảng',
                                'word': 'port'},
                            {   'example': 'It is a sunny day for travel.',
                                'ipa': '/deɪ/',
                                'meaning': 'ngày, ban ngày',
                                'word': 'day'},
                            {   'example': 'We stayed at the hotel for one '
                                           'night.',
                                'ipa': '/naɪt/',
                                'meaning': 'đêm, ban đêm',
                                'word': 'night'},
                            {   'example': 'They travel abroad once a year.',
                                'ipa': '/jɪər/',
                                'meaning': 'năm',
                                'word': 'year'},
                            {   'example': 'We are on holiday this week.',
                                'ipa': '/ˈhɒl.ə.deɪ/',
                                'meaning': 'ngày nghỉ, kỳ nghỉ',
                                'word': 'holiday'},
                            {   'example': 'This is a great place to visit.',
                                'ipa': '/pleɪs/',
                                'meaning': 'địa điểm, nơi chốn',
                                'word': 'place'},
                            {   'example': 'I want to travel the world.',
                                'ipa': '/wɜːld/',
                                'meaning': 'thế giới',
                                'word': 'world'},
                            {   'example': 'Japan is a safe country to visit.',
                                'ipa': '/ˈkʌn.tri/',
                                'meaning': 'đất nước, quốc gia',
                                'word': 'country'},
                            {   'example': 'The town is very old and small.',
                                'ipa': '/taʊn/',
                                'meaning': 'thị trấn',
                                'word': 'town'},
                            {   'example': 'The sea is warm today.',
                                'ipa': '/siː/',
                                'meaning': 'biển, đại dương',
                                'word': 'sea'},
                            {   'example': 'They climbed to the top of the '
                                           'hill.',
                                'ipa': '/hɪl/',
                                'meaning': 'đồi, ngọn đồi',
                                'word': 'hill'},
                            {   'example': 'Here is the key to your room.',
                                'ipa': '/kiː/',
                                'meaning': 'chìa khóa',
                                'word': 'key'},
                            {   'example': 'Please lock the door behind you.',
                                'ipa': '/dɔːr/',
                                'meaning': 'cửa, cánh cửa',
                                'word': 'door'},
                            {   'example': 'Meet me at the train station.',
                                'ipa': '/ˈsteɪ.ʃən/',
                                'meaning': 'nhà ga, trạm',
                                'word': 'station'},
                            {   'example': 'The guide showed us the museum.',
                                'ipa': '/ɡaɪd/',
                                'meaning': 'hướng dẫn viên; sách chỉ dẫn',
                                'word': 'guide'},
                            {   'example': 'Hostels are great for budget '
                                           'travelers.',
                                'ipa': '/ˈhɒs.təl/',
                                'meaning': 'nhà nghỉ giá rẻ',
                                'word': 'hostel'},
                            {   'example': 'A large ship is sailing across the '
                                           'blue ocean.',
                                'ipa': '/ʃɪp/',
                                'meaning': 'tàu thủy, tàu lớn',
                                'word': 'ship'},
                            {   'example': 'It is easy to explore the small '
                                           'island by bike.',
                                'ipa': '/baɪk/',
                                'meaning': 'xe đạp',
                                'word': 'bike'},
                            {   'example': 'We are planning a weekend trip to '
                                           'the countryside.',
                                'ipa': '/trɪp/',
                                'meaning': 'chuyến đi',
                                'word': 'trip'},
                            {   'example': 'I want to visit the famous museum '
                                           'tomorrow.',
                                'ipa': '/ˈvɪz.ɪt/',
                                'meaning': 'ghé thăm, tham quan',
                                'word': 'visit'},
                            {   'example': 'The children love to swim in the '
                                           'warm sea water.',
                                'ipa': '/swɪm/',
                                'meaning': 'bơi lội',
                                'word': 'swim'},
                            {   'example': "Let's walk along the beautiful "
                                           'beach in the evening.',
                                'ipa': '/wɔːk/',
                                'meaning': 'đi bộ',
                                'word': 'walk'},
                            {   'example': 'I like to run in the park near the '
                                           'hotel.',
                                'ipa': '/rʌn/',
                                'meaning': 'chạy bộ, chạy',
                                'word': 'run'},
                            {   'example': 'Always carry a bottle of fresh '
                                           'water during your hike.',
                                'ipa': '/ˈwɔː.tər/',
                                'meaning': 'nước',
                                'word': 'water'},
                            {   'example': 'The sun is hot, so remember to '
                                           'wear a sun hat.',
                                'ipa': '/sʌn/',
                                'meaning': 'mặt trời',
                                'word': 'sun'},
                            {   'example': 'Tokyo is a very large and modern '
                                           'city.',
                                'ipa': '/ˈsɪt.i/',
                                'meaning': 'thành phố',
                                'word': 'city'},
                            {   'example': 'I need a gold coin to buy coffee '
                                           'from the machine.',
                                'ipa': '/kɔɪn/',
                                'meaning': 'tiền xu',
                                'word': 'coin'},
                            {   'example': 'Trying local food is my favorite '
                                           'part of any trip.',
                                'ipa': '/fuːd/',
                                'meaning': 'thức ăn, đồ ăn',
                                'word': 'food'},
                            {   'example': 'We sat down to enjoy a cold drink '
                                           'after a long walk.',
                                'ipa': '/drɪnk/',
                                'meaning': 'đồ uống, thức uống',
                                'word': 'drink'},
                            {   'example': 'We met in a small cafe near the '
                                           'river bank.',
                                'ipa': '/ˈkæf.eɪ/',
                                'meaning': 'quán cà phê',
                                'word': 'cafe'},
                            {   'example': 'Our flight departs from gate '
                                           'number twelve.',
                                'ipa': '/ɡeɪt/',
                                'meaning': 'cổng',
                                'word': 'gate'},
                            {   'example': 'Is this window seat free, or is '
                                           'someone sitting here?',
                                'ipa': '/siːt/',
                                'meaning': 'chỗ ngồi',
                                'word': 'seat'},
                            {   'example': 'The taxi driver was polite and '
                                           'drove very safely.',
                                'ipa': '/ˈdraɪ.vər/',
                                'meaning': 'tài xế, người lái xe',
                                'word': 'driver'},
                            {   'example': 'A group of young tourists is '
                                           'waiting near the entrance.',
                                'ipa': '/ɡruːp/',
                                'meaning': 'nhóm',
                                'word': 'group'},
                            {   'example': 'We visited the local castle in the '
                                           'afternoon.',
                                'ipa': '/ˌɑːf.təˈnuːn/',
                                'meaning': 'buổi chiều',
                                'word': 'afternoon'},
                            {   'example': "Let's have a nice dinner together "
                                           'this evening.',
                                'ipa': '/ˈiːv.nɪŋ/',
                                'meaning': 'buổi tối',
                                'word': 'evening'},
                            {   'example': 'I hope the weather remains warm '
                                           'and sunny tomorrow.',
                                'ipa': '/ˈweð.ər/',
                                'meaning': 'thời tiết',
                                'word': 'weather'},
                            {   'example': 'We enjoyed spending time in nature '
                                           'during our trip.',
                                'ipa': '/ˈneɪ.tʃər/',
                                'meaning': 'tự nhiên, thiên nhiên',
                                'word': 'nature'}],
                  'A2': [   {   'example': 'Our flight to Paris was delayed by '
                                           'two hours.',
                                'ipa': '/flaɪt/',
                                'meaning': 'chuyến bay',
                                'word': 'flight'},
                            {   'example': 'We spent the entire morning '
                                           'visiting the art museum.',
                                'ipa': '/mjuːˈziː.əm/',
                                'meaning': 'bảo tàng',
                                'word': 'museum'},
                            {   'example': 'She packed her clothes carefully '
                                           'in a large suitcase.',
                                'ipa': '/ˈsuːt.keɪs/',
                                'meaning': 'va li',
                                'word': 'suitcase'},
                            {   'example': 'We took a small ferry to reach the '
                                           'tropical island.',
                                'ipa': '/ˈaɪ.lənd/',
                                'meaning': 'hòn đảo',
                                'word': 'island'},
                            {   'example': 'The mountain tops were completely '
                                           'covered in snow.',
                                'ipa': '/ˈmaʊn.tɪn/',
                                'meaning': 'ngọn núi',
                                'word': 'mountain'},
                            {   'example': 'We walked along a narrow trail '
                                           'through the forest.',
                                'ipa': '/ˈfɒr.ɪst/',
                                'meaning': 'khu rừng',
                                'word': 'forest'},
                            {   'example': 'The beautiful river flows through '
                                           'the heart of the city.',
                                'ipa': '/ˈrɪv.ər/',
                                'meaning': 'sông, dòng sông',
                                'word': 'river'},
                            {   'example': 'We crossed the ancient stone '
                                           'bridge over the river.',
                                'ipa': '/brɪdʒ/',
                                'meaning': 'cây cầu',
                                'word': 'bridge'},
                            {   'example': 'The palace is famous for its '
                                           'botanical garden.',
                                'ipa': '/ˈɡɑː.dən/',
                                'meaning': 'khu vườn',
                                'word': 'garden'},
                            {   'example': 'That tall building offers an '
                                           'incredible view of the skyline.',
                                'ipa': '/ˈbɪl.dɪŋ/',
                                'meaning': 'tòa nhà',
                                'word': 'building'},
                            {   'example': 'The medieval castle stands proudly '
                                           'on top of the hill.',
                                'ipa': '/ˈkɑː.səl/',
                                'meaning': 'lâu đài',
                                'word': 'castle'},
                            {   'example': 'Visitors must dress quietly and '
                                           'politely in the temple.',
                                'ipa': '/ˈtem.pəl/',
                                'meaning': 'đền chùa',
                                'word': 'temple'},
                            {   'example': 'I bought some fresh local fruits '
                                           'at the outdoor market.',
                                'ipa': '/ˈmɑː.kɪt/',
                                'meaning': 'chợ, thị trường',
                                'word': 'market'},
                            {   'example': 'We booked a comfortable double '
                                           'room with a queen bed.',
                                'ipa': '/ˈdʌb.əl ruːm/',
                                'meaning': 'phòng đôi (khách sạn)',
                                'word': 'double room'},
                            {   'example': 'I requested a single room since I '
                                           'was traveling alone.',
                                'ipa': '/ˈsɪŋ.ɡəl ruːm/',
                                'meaning': 'phòng đơn (khách sạn)',
                                'word': 'single room'},
                            {   'example': 'Please leave your room keys at the '
                                           'reception desk.',
                                'ipa': '/rɪˈsep.ʃən/',
                                'meaning': 'quầy lễ tân',
                                'word': 'reception'},
                            {   'example': 'The hotel manager welcomed every '
                                           'guest warmly.',
                                'ipa': '/ɡest/',
                                'meaning': 'khách du lịch, khách trọ',
                                'word': 'guest'},
                            {   'example': 'We asked the waiter for the '
                                           'restaurant bill.',
                                'ipa': '/bɪl/',
                                'meaning': 'hóa đơn',
                                'word': 'bill'},
                            {   'example': 'The historic town is popular with '
                                           'many international tourists.',
                                'ipa': '/ˈtʊə.rɪst/',
                                'meaning': 'khách du lịch',
                                'word': 'tourist'},
                            {   'example': 'The airline lost my baggage on my '
                                           'way back.',
                                'ipa': '/ˈbæɡ.ɪdʒ/',
                                'meaning': 'hành lý',
                                'word': 'baggage'},
                            {   'example': 'The heavy rain caused a major '
                                           'delay at the station.',
                                'ipa': '/dɪˈleɪ/',
                                'meaning': 'sự trì hoãn, chậm trễ',
                                'word': 'delay'},
                            {   'example': 'I need to pack my swimsuit for the '
                                           'beach trip.',
                                'ipa': '/pæk/',
                                'meaning': 'đóng gói hành lý',
                                'word': 'pack'},
                            {   'example': 'We will unpack our bags once we '
                                           'reach the room.',
                                'ipa': '/ʌnˈpæk/',
                                'meaning': 'mở hành lý',
                                'word': 'unpack'},
                            {   'example': 'Our rental car broke down on our '
                                           'way to the mountains.',
                                'ipa': '/ˈren.təl/',
                                'meaning': 'thuê xe, sự thuê mướn',
                                'word': 'rental'},
                            {   'example': 'Can you give me directions to the '
                                           'nearest subway?',
                                'ipa': '/daɪˈrek.ʃənz/',
                                'meaning': 'chỉ đường, phương hướng',
                                'word': 'directions'},
                            {   'example': 'The guesthouse has an excellent '
                                           'location close to town.',
                                'ipa': '/ləʊˈkeɪ.ʃən/',
                                'meaning': 'vị trí, địa điểm',
                                'word': 'location'},
                            {   'example': 'This area is known for its '
                                           'beautiful lakes.',
                                'ipa': '/ˈeə.ri.ə/',
                                'meaning': 'khu vực, vùng',
                                'word': 'area'},
                            {   'example': 'Follow the stone path down to the '
                                           'lake.',
                                'ipa': '/pɑːθ/',
                                'meaning': 'lối đi, đường mòn',
                                'word': 'path'},
                            {   'example': 'You should exchange some cash into '
                                           'the local currency.',
                                'ipa': '/ˈkʌr.ən.si/',
                                'meaning': 'tiền tệ',
                                'word': 'currency'},
                            {   'example': 'The hotel check-in begins at two '
                                           'in the afternoon.',
                                'ipa': '/ˈtʃek.ɪn/',
                                'meaning': 'thủ tục nhận phòng/lên máy bay',
                                'word': 'check-in'},
                            {   'example': 'We did our check-out and left for '
                                           'the airport.',
                                'ipa': '/ˈtʃek.aʊt/',
                                'meaning': 'thủ tục trả phòng',
                                'word': 'check-out'},
                            {   'example': 'Ask the information desk for a '
                                           'free bus map.',
                                'ipa': '/ˌɪn.fəˈmeɪ.ʃən/',
                                'meaning': 'thông tin',
                                'word': 'information'},
                            {   'example': 'I took a travel brochure about '
                                           'city museum tours.',
                                'ipa': '/ˈbrəʊ.ʃər/',
                                'meaning': 'tờ rơi quảng cáo du lịch',
                                'word': 'brochure'},
                            {   'example': 'This guidebook lists the best '
                                           'local restaurants in town.',
                                'ipa': '/ˈɡaɪd.bʊk/',
                                'meaning': 'sách hướng dẫn du lịch',
                                'word': 'guidebook'},
                            {   'example': 'I bought a postcard to send to my '
                                           'best friend.',
                                'ipa': '/ˈpəʊst.kɑːd/',
                                'meaning': 'bưu thiếp',
                                'word': 'postcard'},
                            {   'example': 'She bought a small magnet as a '
                                           'souvenir from Rome.',
                                'ipa': '/ˌsuː.vəˈnɪər/',
                                'meaning': 'quà lưu niệm',
                                'word': 'souvenir'},
                            {   'example': 'It is a local custom to bow when '
                                           'greeting elders.',
                                'ipa': '/ˈkʌs.təm/',
                                'meaning': 'phong tục địa phương',
                                'word': 'custom'},
                            {   'example': 'The flight attendant helped us '
                                           'place our bags.',
                                'ipa': '/flaɪt əˈten.dənt/',
                                'meaning': 'tiếp viên hàng không',
                                'word': 'flight attendant'},
                            {   'example': 'The pilot announced that the '
                                           'flight would land shortly.',
                                'ipa': '/ˈpaɪ.lət/',
                                'meaning': 'phi công',
                                'word': 'pilot'},
                            {   'example': 'The train for Edinburgh is waiting '
                                           'at platform four.',
                                'ipa': '/ˈplæt.fɔːm/',
                                'meaning': 'sân ga, thềm ga',
                                'word': 'platform'},
                            {   'example': 'The railway line runs along the '
                                           'beautiful sea coast.',
                                'ipa': '/ˈreɪl.weɪ/',
                                'meaning': 'đường sắt',
                                'word': 'railway'},
                            {   'example': 'You can buy your underground '
                                           'tickets at the ticket office.',
                                'ipa': '/ˈtɪk.ɪt ˌɒf.ɪs/',
                                'meaning': 'phòng bán vé',
                                'word': 'ticket office'},
                            {   'example': "Let's check the timetable to see "
                                           'when the next bus leaves.',
                                'ipa': '/ˈtaɪm.teɪ.bəl/',
                                'meaning': 'lịch trình chạy xe, thời khóa biểu',
                                'word': 'timetable'},
                            {   'example': 'The heavy morning traffic delayed '
                                           'our journey slightly.',
                                'ipa': '/ˈtræf.ɪk/',
                                'meaning': 'giao thông, xe cộ',
                                'word': 'traffic'},
                            {   'example': 'The London underground is very '
                                           'fast and easy to use.',
                                'ipa': '/ˌʌn.dəˈɡraʊnd/',
                                'meaning': 'tàu điện ngầm',
                                'word': 'underground'},
                            {   'example': 'No private vehicles are allowed '
                                           'inside the park area.',
                                'ipa': '/ˈviː.ə.kəl/',
                                'meaning': 'phương tiện giao thông',
                                'word': 'vehicle'},
                            {   'example': 'The sailors prepared for their '
                                           'long voyage across the sea.',
                                'ipa': '/ˈvɔɪ.ɪdʒ/',
                                'meaning': 'hành trình bằng đường biển',
                                'word': 'voyage'},
                            {   'example': 'A cold wind blew across the beach '
                                           'in the evening.',
                                'ipa': '/wɪnd/',
                                'meaning': 'gió',
                                'word': 'wind'},
                            {   'example': 'We packed sturdy boots for our '
                                           'hiking holiday.',
                                'ipa': '/ˈhaɪ.kɪŋ/',
                                'meaning': 'đi bộ đường dài, dã ngoại',
                                'word': 'hiking'},
                            {   'example': 'They bought a new tent for their '
                                           'weekend camping trip.',
                                'ipa': '/ˈkæm.pɪŋ/',
                                'meaning': 'cắm trại',
                                'word': 'camping'},
                            {   'example': 'The airport is far from the city.',
                                'ipa': '/ˈeə.pɔːt/',
                                'meaning': 'sân bay',
                                'word': 'airport'},
                            {   'example': 'We weighed our bags on the scale.',
                                'ipa': '/ˈlʌɡ.ɪdʒ skeɪl/',
                                'meaning': 'cân hành lý',
                                'word': 'luggage scale'},
                            {   'example': 'Proceed to boarding gate seven.',
                                'ipa': '/ˈbɔː.dɪŋ ɡeɪt/',
                                'meaning': 'cổng lên máy bay',
                                'word': 'boarding gate'},
                            {   'example': 'The passenger train runs hourly.',
                                'ipa': '/ˈpæs.ən.dʒər treɪn/',
                                'meaning': 'tàu chở khách',
                                'word': 'passenger train'},
                            {   'example': 'We hailed a taxi outside the '
                                           'station.',
                                'ipa': '/ˈtæk.si/',
                                'meaning': 'xe taxi',
                                'word': 'taxi'},
                            {   'example': 'The subway is fast and cheap.',
                                'ipa': '/ˈsʌb.weɪ/',
                                'meaning': 'tàu điện ngầm',
                                'word': 'subway'},
                            {   'example': 'Cars sped down the highway.',
                                'ipa': '/ˈhaɪ.weɪ/',
                                'meaning': 'đường cao tốc',
                                'word': 'highway'},
                            {   'example': 'The journey time is three hours.',
                                'ipa': '/ˈdʒɜː.ni taɪm/',
                                'meaning': 'thời gian di chuyển',
                                'word': 'journey time'},
                            {   'example': 'Ask at the reservation desk.',
                                'ipa': '/ˌrez.əˈveɪ.ʃən dɛsk/',
                                'meaning': 'quầy đặt chỗ trước',
                                'word': 'reservation desk'},
                            {   'example': 'The boat crossed the calm river.',
                                'ipa': '/ˈpæs.ən.dʒər bəʊt/',
                                'meaning': 'tàu chở khách đường thủy',
                                'word': 'passenger boat'},
                            {   'example': 'Yachts docked in the peaceful '
                                           'harbor.',
                                'ipa': '/ˈhɑː.bər/',
                                'meaning': 'bến cảng, vũng tàu',
                                'word': 'harbor'},
                            {   'example': 'They took a cruise in the '
                                           'Caribbean.',
                                'ipa': '/kruːz/',
                                'meaning': 'chuyến du thuyền',
                                'word': 'cruise'},
                            {   'example': 'Our cabin was very comfortable.',
                                'ipa': '/ˈkæb.ɪn/',
                                'meaning': 'cabin, buồng ngủ trên tàu',
                                'word': 'cabin'},
                            {   'example': 'The backpacker carried a large '
                                           'tent.',
                                'ipa': '/ˈbæk.pæk.ər/',
                                'meaning': 'khách du lịch ba lô',
                                'word': 'backpacker'},
                            {   'example': 'We took an open-top sightseeing '
                                           'bus.',
                                'ipa': '/ˈsaɪtˌsiː.ɪŋ bʌs/',
                                'meaning': 'xe buýt ngắm cảnh',
                                'word': 'sightseeing bus'},
                            {   'example': 'He loves visiting foreign '
                                           'countries.',
                                'ipa': '/ˈfɒr.ən ˈkʌn.tri/',
                                'meaning': 'nước ngoài',
                                'word': 'foreign country'},
                            {   'example': 'The tour guide explained the '
                                           'history.',
                                'ipa': '/tʊər ɡaɪd/',
                                'meaning': 'hướng dẫn viên du lịch',
                                'word': 'tour guide'},
                            {   'example': 'We tried some delicious local '
                                           'food.',
                                'ipa': '/ˈləʊ.kəl fuːd/',
                                'meaning': 'món ăn địa phương',
                                'word': 'local food'},
                            {   'example': 'She bought fresh fruit from a '
                                           'market stall.',
                                'ipa': '/ˈmɑː.kɪt stɔːl/',
                                'meaning': 'quầy hàng ở chợ',
                                'word': 'market stall'},
                            {   'example': 'They camped in the national park.',
                                'ipa': '/ˈnæʃ.ən.əl pɑːk/',
                                'meaning': 'vườn quốc gia',
                                'word': 'national park'},
                            {   'example': 'Follow the marked hiking trail.',
                                'ipa': '/ˈhaɪ.kɪŋ treɪl/',
                                'meaning': 'đường mòn đi bộ dã ngoại',
                                'word': 'hiking trail'},
                            {   'example': 'The waterfall is high and '
                                           'beautiful.',
                                'ipa': '/ˈwɔː.tə.fɔːl/',
                                'meaning': 'thác nước',
                                'word': 'waterfall'},
                            {   'example': 'Snow covered the mountain peak.',
                                'ipa': '/ˈmaʊn.tɪn piːk/',
                                'meaning': 'đỉnh núi',
                                'word': 'mountain peak'},
                            {   'example': 'They hiked down into the deep '
                                           'canyon.',
                                'ipa': '/ˈkæn.jən/',
                                'meaning': 'hẻm núi lớn',
                                'word': 'canyon'},
                            {   'example': 'Cacti grow in the hot desert.',
                                'ipa': '/ˈdez.ət/',
                                'meaning': 'sa mạc',
                                'word': 'desert'},
                            {   'example': 'We booked a room at a beach '
                                           'resort.',
                                'ipa': '/biːtʃ rɪˈzɔːt/',
                                'meaning': 'khu nghỉ dưỡng bãi biển',
                                'word': 'beach resort'},
                            {   'example': 'The hotel has an outdoor swimming '
                                           'pool.',
                                'ipa': '/ˈswɪm.ɪŋ puːl/',
                                'meaning': 'bể bơi',
                                'word': 'swimming pool'},
                            {   'example': 'They serve fresh seafood by the '
                                           'harbor.',
                                'ipa': '/ˈsiː.fuːd/',
                                'meaning': 'hải sản',
                                'word': 'seafood'},
                            {   'example': 'Take an umbrella in case it rains.',
                                'ipa': '/ʌmˈbrel.ə/',
                                'meaning': 'cái ô, cái dù',
                                'word': 'umbrella'},
                            {   'example': 'Apply sunscreen before going to '
                                           'the beach.',
                                'ipa': '/ˈsʌn.skriːn/',
                                'meaning': 'kem chống nắng',
                                'word': 'sunscreen'},
                            {   'example': 'She wore dark sunglasses in the '
                                           'sun.',
                                'ipa': '/ˈsʌn.ɡlɑː.sɪz/',
                                'meaning': 'kính râm, kính mát',
                                'word': 'sunglasses'},
                            {   'example': 'Clean your camera lens regularly.',
                                'ipa': '/ˈkæm.ər.ə lenz/',
                                'meaning': 'ống kính máy ảnh',
                                'word': 'camera lens'},
                            {   'example': 'She put the holiday photos in an '
                                           'album.',
                                'ipa': '/ˈfəʊ.təʊ ˈæl.bəm/',
                                'meaning': 'cuốn album ảnh',
                                'word': 'photo album'},
                            {   'example': 'Write your name on the luggage '
                                           'tag.',
                                'ipa': '/ˈlʌɡ.ɪdʒ tæɡ/',
                                'meaning': 'thẻ ghi thông tin hành lý',
                                'word': 'luggage tag'},
                            {   'example': 'He packed his clothes into a '
                                           'backpack.',
                                'ipa': '/ˈbæk.pæk/',
                                'meaning': 'ba lô',
                                'word': 'backpack'},
                            {   'example': 'It got cold in the sleeping bag.',
                                'ipa': '/ˈsliː.pɪŋ bæɡ/',
                                'meaning': 'túi ngủ dã ngoại',
                                'word': 'sleeping bag'},
                            {   'example': 'We set up our tent under the '
                                           'trees.',
                                'ipa': '/tent/',
                                'meaning': 'cái lều dã ngoại',
                                'word': 'tent'},
                            {   'example': 'The camping site has hot showers.',
                                'ipa': '/ˈkæm.pɪŋ saɪt/',
                                'meaning': 'bãi cắm trại',
                                'word': 'camping site'},
                            {   'example': 'The map guide shows historical '
                                           'sites.',
                                'ipa': '/mæp ɡaɪd/',
                                'meaning': 'bản đồ chỉ dẫn',
                                'word': 'map guide'},
                            {   'example': 'Ask for a free map at the '
                                           'information desk.',
                                'ipa': '/ˌɪn.fəˈmeɪ.ʃən dɛsk/',
                                'meaning': 'quầy thông tin',
                                'word': 'information desk'},
                            {   'example': 'I need to find a cash machine.',
                                'ipa': '/kæʃ məˈʃiːn/',
                                'meaning': 'máy rút tiền tự động ATM',
                                'word': 'cash machine'},
                            {   'example': 'Can I pay by credit card?',
                                'ipa': '/ˈkred.ɪt kɑːd/',
                                'meaning': 'thẻ tín dụng',
                                'word': 'credit card'}],
                  'B1': [   {   'example': 'What is your final travel '
                                           'destination?',
                                'ipa': '/ˌdestɪˈneɪʃn/',
                                'meaning': 'Điểm đến',
                                'word': 'Destination'},
                            {   'example': 'We planned our itinerary in '
                                           'detail.',
                                'ipa': '/aɪˈtɪnərəri/',
                                'meaning': 'Lịch trình chuyến đi',
                                'word': 'Itinerary'},
                            {   'example': 'The hostel offers cheap '
                                           'accommodation.',
                                'ipa': '/əˌkɒməˈdeɪʃn/',
                                'meaning': 'Chỗ ở, nơi lưu trú',
                                'word': 'Accommodation'},
                            {   'example': 'We spent the afternoon exploring '
                                           'the ancient temple.',
                                'ipa': '/ɪkˈsplɔː(r)/',
                                'meaning': 'Khám phá, thám hiểm',
                                'word': 'Explore'},
                            {   'example': 'I made a hotel reservation online.',
                                'ipa': '/ˌrezəˈveɪʃn/',
                                'meaning': 'Sự đặt trước',
                                'word': 'Reservation'},
                            {   'example': 'He wrote a book about his desert '
                                           'adventure.',
                                'ipa': '/ədˈventʃə(r)/',
                                'meaning': 'Cuộc phiêu lưu',
                                'word': 'Adventure'},
                            {   'example': 'We went on a day excursion to the '
                                           'island.',
                                'ipa': '/ɪkˈskɜːʃn/',
                                'meaning': 'Chuyến tham quan ngắn',
                                'word': 'Excursion'},
                            {   'example': 'All passengers must fasten their '
                                           'seatbelts.',
                                'ipa': '/ˈpæsɪndʒə(r)/',
                                'meaning': 'Hành khách',
                                'word': 'Passenger'},
                            {   'example': "The Eiffel Tower is Paris's most "
                                           'famous tourist attraction.',
                                'ipa': '/əˈtrækʃən/',
                                'meaning': 'Điểm tham quan, địa điểm hấp dẫn',
                                'word': 'Attraction'},
                            {   'example': 'I need to check my work schedule.',
                                'ipa': '/ˈskɛʤʊl/',
                                'meaning': 'Lịch trình, thời khóa biểu',
                                'word': 'Schedule'},
                            {   'example': 'The hotel provides comfortable '
                                           'lodging for tourists.',
                                'ipa': '/ˈlɒdʒɪŋ/',
                                'meaning': 'Chỗ trọ, nơi ở tạm',
                                'word': 'Lodging'},
                            {   'example': 'Explorers discovered new lands in '
                                           'the 15th century.',
                                'ipa': '/dɪˈskʌvər/',
                                'meaning': 'Phát hiện ra, tìm thấy điều mới',
                                'word': 'Discover'},
                            {   'example': 'Please confirm your booking at '
                                           'least 24 hours in advance.',
                                'ipa': '/ˈbʊkɪŋ/',
                                'meaning': 'Đặt chỗ, đặt phòng trước',
                                'word': 'Booking'},
                            {   'example': 'The journey from Hanoi to Ho Chi '
                                           'Minh City takes about two hours by '
                                           'plane.',
                                'ipa': '/ˈdʒɜːni/',
                                'meaning': 'Hành trình dài, chuyến đi',
                                'word': 'Journey'},
                            {   'example': 'The whole family went on an outing '
                                           'to the countryside.',
                                'ipa': '/ˈaʊtɪŋ/',
                                'meaning': 'Chuyến dã ngoại, đi chơi ngoài',
                                'word': 'Outing'},
                            {   'example': 'The traveler packed light for the '
                                           'long trip.',
                                'ipa': '/ˈtræv.əl.ər/',
                                'meaning': 'Người đi du lịch, lữ khách',
                                'word': 'Traveler'},
                            {   'example': 'We plan to do some sightseeing in '
                                           'Rome tomorrow morning.',
                                'ipa': '/ˈsaɪtˌʃiː.ɪŋ/',
                                'meaning': 'ngắm cảnh, tham quan',
                                'word': 'sightseeing'},
                            {   'example': 'We booked a guided walking tour of '
                                           'the historic city.',
                                'ipa': '/tʊər/',
                                'meaning': 'chuyến đi tham quan, tour du lịch',
                                'word': 'tour'},
                            {   'example': 'Please show your boarding pass and '
                                           'passport at the gate.',
                                'ipa': '/ˈbɔː.dɪŋ ˌpɑːs/',
                                'meaning': 'thẻ lên máy bay',
                                'word': 'boarding pass'},
                            {   'example': 'The departure board showed that '
                                           'our flight was on time.',
                                'ipa': '/dɪˈpɑː.tʃər/',
                                'meaning': 'sự khởi hành',
                                'word': 'departure'},
                            {   'example': 'We waited for their arrival at the '
                                           'hotel lobby.',
                                'ipa': '/əˈraɪ.vəl/',
                                'meaning': 'sự đến nơi',
                                'word': 'arrival'},
                            {   'example': 'We had to go through customs after '
                                           'landing at the airport.',
                                'ipa': '/ˈkʌs.təmz/',
                                'meaning': 'hải quan, thuế quan',
                                'word': 'customs'},
                            {   'example': 'The flight to New York departs '
                                           'from terminal three.',
                                'ipa': '/ˈtɜː.mɪ.nəl/',
                                'meaning': 'nhà ga (sân bay, bến xe)',
                                'word': 'terminal'},
                            {   'example': 'Public transport in this city is '
                                           'very cheap and reliable.',
                                'ipa': '/trænsˈpɔːt/',
                                'meaning': 'vận tải, giao thông công cộng',
                                'word': 'transport'},
                            {   'example': 'The hotel provides a free airport '
                                           'transfer service.',
                                'ipa': '/trænsˈfɜːr/',
                                'meaning': 'sự trung chuyển, chuyển khách',
                                'word': 'transfer'},
                            {   'example': 'I received an email confirmation '
                                           'for my flight reservation.',
                                'ipa': '/ˌkɒn.fəˈmeɪ.ʃən/',
                                'meaning': 'thư xác nhận, sự xác nhận',
                                'word': 'confirmation'},
                            {   'example': 'We had to cancel our trip due to '
                                           'sudden health issues.',
                                'ipa': '/ˈkæn.səl/',
                                'meaning': 'hủy bỏ',
                                'word': 'cancel'},
                            {   'example': 'We decided to rent a bicycle to '
                                           'explore the quiet countryside.',
                                'ipa': '/rent/',
                                'meaning': 'thuê (xe, nhà)',
                                'word': 'rent'},
                            {   'example': 'We loved to wander through the '
                                           'narrow streets of the old quarter.',
                                'ipa': '/ˈwɒn.dər/',
                                'meaning': 'đi lang thang, dạo chơi',
                                'word': 'wander'},
                            {   'example': 'The scenic route offers '
                                           'spectacular views of the valleys.',
                                'ipa': '/ruːt/',
                                'meaning': 'tuyến đường, lộ trình',
                                'word': 'route'},
                            {   'example': 'They booked a package tour that '
                                           'included flights and meals.',
                                'ipa': '/ˈpæk.ɪdʒ tʊər/',
                                'meaning': 'du lịch trọn gói',
                                'word': 'package tour'},
                            {   'example': 'The train passed through beautiful '
                                           'mountain scenery.',
                                'ipa': '/ˈsiː.nər.i/',
                                'meaning': 'phong cảnh, cảnh vật',
                                'word': 'scenery'},
                            {   'example': 'This is a popular picnic spot for '
                                           'local families.',
                                'ipa': '/spɒt/',
                                'meaning': 'nơi, điểm, địa điểm',
                                'word': 'spot'},
                            {   'example': 'We visited several historical '
                                           'buildings during our tour.',
                                'ipa': '/hɪˈstɒr.ɪ.kəl/',
                                'meaning': 'thuộc lịch sử, mang tính lịch sử',
                                'word': 'historical'},
                            {   'example': 'Traveling is the best way to '
                                           'experience a different culture.',
                                'ipa': '/ˈkʌl.tʃər/',
                                'meaning': 'văn hóa',
                                'word': 'culture'},
                            {   'example': 'He had a long chat with the native '
                                           'inhabitants of the village.',
                                'ipa': '/ˈneɪ.tɪv/',
                                'meaning': 'bản địa, bản xứ',
                                'word': 'native'},
                            {   'example': 'This was the first time she had '
                                           'traveled abroad alone.',
                                'ipa': '/əˈbrɔːd/',
                                'meaning': 'ở nước ngoài',
                                'word': 'abroad'},
                            {   'example': 'The hotel attracts thousands of '
                                           'overseas visitors every summer.',
                                'ipa': '/ˌəʊ.vəˈsiːz/',
                                'meaning': 'hải ngoại, nước ngoài',
                                'word': 'overseas'},
                            {   'example': 'We had to show our visas at the '
                                           'border crossing.',
                                'ipa': '/ˈbɔː.dər/',
                                'meaning': 'biên giới',
                                'word': 'border'},
                            {   'example': 'The Eiffel Tower is a world-famous '
                                           'landmark.',
                                'ipa': '/ˈlænd.mɑːk/',
                                'meaning': 'cột mốc, điểm mốc nổi tiếng',
                                'word': 'landmark'},
                            {   'example': 'There is a beautiful historical '
                                           'monument in the square.',
                                'ipa': '/ˈmɒn.jə.mənt/',
                                'meaning': 'đài tưởng niệm, di tích',
                                'word': 'monument'},
                            {   'example': 'The royal family lives in the '
                                           'grand palace in the city.',
                                'ipa': '/ˈpæl.ɪs/',
                                'meaning': 'cung điện',
                                'word': 'palace'},
                            {   'example': 'The gothic cathedral dominates the '
                                           "town's skyline.",
                                'ipa': '/kəˈθiː.drəl/',
                                'meaning': 'nhà thờ lớn, thánh đường',
                                'word': 'cathedral'},
                            {   'example': 'We stayed at a luxury beach resort '
                                           'in Thailand.',
                                'ipa': '/rɪˈzɔːt/',
                                'meaning': 'khu nghỉ dưỡng',
                                'word': 'resort'},
                            {   'example': 'The family-run guesthouse was '
                                           'extremely cozy and clean.',
                                'ipa': '/ˈɡest.haʊs/',
                                'meaning': 'nhà khách, nhà trọ',
                                'word': 'guesthouse'},
                            {   'example': 'We parked our car outside the '
                                           'motel and went inside to sleep.',
                                'ipa': '/məʊˈtel/',
                                'meaning': 'nhà nghỉ bên đường',
                                'word': 'motel'},
                            {   'example': 'Please reconfirm your flight '
                                           'ticket 24 hours in advance.',
                                'ipa': '/ˌriː.kənˈfɜːm/',
                                'meaning': 'xác nhận lại',
                                'word': 'reconfirm'},
                            {   'example': 'We headed to baggage reclaim to '
                                           'collect our heavy suitcases.',
                                'ipa': '/ˈbæɡ.ɪdʒ rɪˈkleɪm/',
                                'meaning': 'khu vực trả hành lý',
                                'word': 'baggage reclaim'},
                            {   'example': 'I bought some perfume at the '
                                           'airport duty-free shop.',
                                'ipa': '/ˌdʒuː.tiˈfriː/',
                                'meaning': 'miễn thuế',
                                'word': 'duty-free'},
                            {   'example': 'We had a brief stopover in '
                                           'Singapore before flying to London.',
                                'ipa': '/ˈstɒp.əʊ.vər/',
                                'meaning': 'điểm dừng chân (trong hành trình '
                                           'dài)',
                                'word': 'stopover'},
                            {   'example': 'We sat on the upper deck to watch '
                                           'the harbor fade away.',
                                'ipa': '/dek/',
                                'meaning': 'boong tàu',
                                'word': 'deck'},
                            {   'example': 'I always suffer from bad jet lag '
                                           'when traveling east.',
                                'ipa': '/ˈdʒet ˌlæɡ/',
                                'meaning': 'cảm giác mệt mỏi sau bay dài, lệch '
                                           'múi giờ',
                                'word': 'jet lag'},
                            {   'example': 'It is essential to buy medical '
                                           'insurance before traveling.',
                                'ipa': '/ɪnˈʃɔː.rəns/',
                                'meaning': 'bảo hiểm',
                                'word': 'insurance'},
                            {   'example': 'You need a special permit to camp '
                                           'in the national park.',
                                'ipa': '/ˈpɜː.mɪt/',
                                'meaning': 'giấy phép',
                                'word': 'permit'},
                            {   'example': 'Keep all your travel documents '
                                           'safe in your hand bag.',
                                'ipa': '/ˈdɒk.jə.mənt/',
                                'meaning': 'tài liệu, giấy tờ',
                                'word': 'document'},
                            {   'example': 'A friendly local showed us the way '
                                           'to the market.',
                                'ipa': '/ˈləʊ.kəl/',
                                'meaning': 'người địa phương, dân bản xứ',
                                'word': 'local'},
                            {   'example': 'They decided to postpone their '
                                           'trip due to bad weather.',
                                'ipa': '/pəʊstˈpəʊn/',
                                'meaning': 'hoãn lại, trì hoãn',
                                'word': 'postpone'},
                            {   'example': 'Booking a direct flight is much '
                                           'more convenient.',
                                'ipa': '/daɪˈrekt flaɪt/',
                                'meaning': 'chuyến bay thẳng',
                                'word': 'direct flight'},
                            {   'example': 'We spent six hours in transit at '
                                           'the airport.',
                                'ipa': '/ˈtræn.zɪt/',
                                'meaning': 'quá cảnh',
                                'word': 'transit'},
                            {   'example': 'The airline has a strict 20kg '
                                           'luggage allowance policy.',
                                'ipa': '/ˈlʌɡ.ɪdʒ əˈlaʊ.əns/',
                                'meaning': 'tiêu chuẩn hành lý cho phép',
                                'word': 'luggage allowance'},
                            {   'example': 'There was a long queue at the '
                                           'airline check-in desk.',
                                'ipa': '/ˈtʃek.ɪn desk/',
                                'meaning': 'quầy làm thủ tục',
                                'word': 'check-in desk'}],
                  'B2': [   {   'example': 'His intense wanderlust led him to '
                                           'explore remote islands.',
                                'ipa': '/ˈwɒn.də.lʌst/',
                                'meaning': 'sự đam mê dịch chuyển, cuồng đi',
                                'word': 'wanderlust'},
                            {   'example': 'The local community benefits '
                                           'greatly from sustainable '
                                           'ecotourism.',
                                'ipa': '/ˈiː.kəʊˌtʊə.rɪ.zəm/',
                                'meaning': 'du lịch sinh thái',
                                'word': 'ecotourism'},
                            {   'example': 'She spent six months backpacking '
                                           'through Southeast Asia.',
                                'ipa': '/ˈbæk.pæk.ɪŋ/',
                                'meaning': 'du lịch ba lô, phượt',
                                'word': 'backpacking'},
                            {   'example': 'He organized a scientific '
                                           'expedition to the Antarctic '
                                           'region.',
                                'ipa': '/ˌek.spəˈdɪʃ.ən/',
                                'meaning': 'cuộc thám hiểm, hành trình',
                                'word': 'expedition'},
                            {   'example': 'Every year, thousands of believers '
                                           'make a sacred pilgrimage.',
                                'ipa': '/ˈpɪl.ɡrɪ.mɪdʒ/',
                                'meaning': 'cuộc hành hương',
                                'word': 'pilgrimage'},
                            {   'example': 'My daily commute to the office '
                                           'takes forty minutes by train.',
                                'ipa': '/kəˈmjuːt/',
                                'meaning': 'quãng đường đi lại hàng ngày',
                                'word': 'commute'},
                            {   'example': 'We were deeply touched by the warm '
                                           'hospitality of the villagers.',
                                'ipa': '/ˌhɒs.pɪˈtæl.ə.ti/',
                                'meaning': 'lòng hiếu khách, sự mến khách',
                                'word': 'hospitality'},
                            {   'example': 'New York is an extremely '
                                           'cosmopolitan and diverse city.',
                                'ipa': '/ˌkɒz.məˈpɒl.ɪ.tən/',
                                'meaning': 'mang tính quốc tế, đa sắc tộc',
                                'word': 'cosmopolitan'},
                            {   'example': 'The ancient city is filled with '
                                           'rich architectural heritage.',
                                'ipa': '/ˈher.ɪ.tɪdʒ/',
                                'meaning': 'di sản',
                                'word': 'heritage'},
                            {   'example': 'The view from the top of the '
                                           'volcanic peak was spectacular.',
                                'ipa': '/spekˈtæk.jə.lər/',
                                'meaning': 'ngoạn mục, hùng vĩ',
                                'word': 'spectacular'},
                            {   'example': 'We stayed in a picturesque fishing '
                                           'village along the coast.',
                                'ipa': '/ˌpɪk.tʃərˈesk/',
                                'meaning': 'đẹp như tranh vẽ',
                                'word': 'picturesque'},
                            {   'example': 'She took some stunning photos of '
                                           'the sunset over the bay.',
                                'ipa': '/ˈstʌn.ɪŋ/',
                                'meaning': 'lộng lẫy, làm sững sờ',
                                'word': 'stunning'},
                            {   'example': 'The scenery in the national park '
                                           'was absolutely breathtaking.',
                                'ipa': '/ˈbreθˌteɪ.kɪŋ/',
                                'meaning': 'hấp dẫn đến ngạt thở, ngoạn mục',
                                'word': 'breathtaking'},
                            {   'example': 'The research station is in a '
                                           'highly remote area of the jungle.',
                                'ipa': '/rɪˈməʊt/',
                                'meaning': 'xa xôi, hẻo lánh',
                                'word': 'remote'},
                            {   'example': 'The small cabin is isolated from '
                                           'the rest of the town.',
                                'ipa': '/ˈaɪ.sə.leɪ.tɪd/',
                                'meaning': 'cô lập, tách biệt',
                                'word': 'isolated'},
                            {   'example': 'I love discovering exotic spices '
                                           'and foods when traveling.',
                                'ipa': '/ɪɡˈzɒt.ɪk/',
                                'meaning': 'ngoại lai, độc đáo, kỳ lạ',
                                'word': 'exotic'},
                            {   'example': 'The airport recently expanded its '
                                           'domestic terminal.',
                                'ipa': '/dəˈmes.tɪk/',
                                'meaning': 'nội địa, trong nước',
                                'word': 'domestic'},
                            {   'example': 'The passengers began to embark on '
                                           'the cruise ship.',
                                'ipa': '/ɪmˈbɑːk/',
                                'meaning': 'lên tàu, máy bay',
                                'word': 'embark'},
                            {   'example': 'Please have your luggage ready '
                                           'before you disembark.',
                                'ipa': '/ˌdɪs.ɪmˈbɑːk/',
                                'meaning': 'xuống tàu, máy bay',
                                'word': 'disembark'},
                            {   'example': 'We had to run across the airport '
                                           'to catch our connecting flight.',
                                'ipa': '/kəˈnek.tɪŋ flaɪt/',
                                'meaning': 'chuyến bay chuyển tiếp',
                                'word': 'connecting flight'},
                            {   'example': 'We had a long five-hour layover in '
                                           'Tokyo before our flight.',
                                'ipa': '/ˈleɪˌəʊ.vər/',
                                'meaning': 'thời gian chờ chuyển tiếp',
                                'word': 'layover'},
                            {   'example': 'The company organized a charter '
                                           'flight for the executives.',
                                'ipa': '/ˈtʃɑː.tər flaɪt/',
                                'meaning': 'chuyến bay thuê trọn gói riêng',
                                'word': 'charter flight'},
                            {   'example': 'Since the airline overbooked the '
                                           'flight, they offered vouchers.',
                                'ipa': '/ˌəʊ.vəˈbʊk/',
                                'meaning': 'đặt trước quá tải',
                                'word': 'overbook'},
                            {   'example': 'He received financial compensation '
                                           'for the flight cancellation.',
                                'ipa': '/ˌkɒm.penˈseɪ.ʃən/',
                                'meaning': 'khoản bồi thường',
                                'word': 'compensation'},
                            {   'example': 'Low-cost carriers have made '
                                           'international travel much cheaper.',
                                'ipa': '/ləʊ ˌkɒst ˈkær.i.ər/',
                                'meaning': 'hãng hàng không giá rẻ',
                                'word': 'low-cost carrier'},
                            {   'example': 'Hotel rooms are very hard to find '
                                           'during the high season.',
                                'ipa': '/haɪ ˈsiː.zən/',
                                'meaning': 'mùa cao điểm',
                                'word': 'high season'},
                            {   'example': 'Traveling during off-peak times '
                                           'helps you avoid crowds.',
                                'ipa': '/ˌɒfˈpiːk/',
                                'meaning': 'ngoài giờ cao điểm',
                                'word': 'off-peak'},
                            {   'example': 'We asked the travel agency to plan '
                                           'our entire itinerary.',
                                'ipa': '/ˈtræv.əl ˌeɪ.dʒən.si/',
                                'meaning': 'đại lý du lịch',
                                'word': 'travel agency'},
                            {   'example': 'The tour operator resolved our '
                                           'transport issue quickly.',
                                'ipa': '/tʊər ˈɒp.ər.eɪ.tər/',
                                'meaning': 'nhà điều hành tour du lịch',
                                'word': 'tour operator'},
                            {   'example': 'This beautiful beach is a famous '
                                           'hotspot for surfers.',
                                'ipa': '/ˈhɒt.spɒt/',
                                'meaning': 'điểm nóng du lịch, điểm thu hút',
                                'word': 'hotspot'},
                            {   'example': 'They spent a week hiking through '
                                           'the mountain wilderness.',
                                'ipa': '/ˈwɪl.də.nəs/',
                                'meaning': 'vùng hoang dã',
                                'word': 'wilderness'},
                            {   'example': 'The tropical island is a natural '
                                           'sanctuary for birds.',
                                'ipa': '/ˈsæŋk.tʃʊə.ri/',
                                'meaning': 'khu bảo tồn thiên nhiên',
                                'word': 'sanctuary'},
                            {   'example': 'We must protect and preserve our '
                                           'cultural monuments.',
                                'ipa': '/prɪˈzɜːv/',
                                'meaning': 'khu bảo tồn, bảo tồn',
                                'word': 'preserve'},
                            {   'example': 'The national park is highly '
                                           'dedicated to wildlife '
                                           'conservation.',
                                'ipa': '/ˌkɒn.səˈveɪ.ʃən/',
                                'meaning': 'sự bảo tồn thiên nhiên',
                                'word': 'conservation'},
                            {   'example': 'The island is famous for its '
                                           'pristine sandy beaches.',
                                'ipa': '/ˈprɪs.tiːn/',
                                'meaning': 'nguyên sơ, tinh khôi',
                                'word': 'pristine'},
                            {   'example': 'The mountain valley remains '
                                           'completely natural and unspoilt.',
                                'ipa': '/uʌnˈspɔɪlt/',
                                'meaning': 'chưa bị hoang hóa, tự nhiên',
                                'word': 'unspoilt'},
                            {   'example': 'We rented a self-catering '
                                           'apartment near the beach.',
                                'ipa': '/ˌselfˈkeɪ.tər.ɪŋ/',
                                'meaning': 'tự phục vụ ăn uống (căn hộ)',
                                'word': 'self-catering'},
                            {   'example': 'Our hotel booking includes full '
                                           'board options.',
                                'ipa': '/ˌfʊl ˈbɔːd/',
                                'meaning': 'bao gồm tất cả bữa ăn (trọn gói)',
                                'word': 'full board'},
                            {   'example': 'We chose half board so we could '
                                           'eat lunch outdoors.',
                                'ipa': '/ˌhɑːf ˈbɔːd/',
                                'meaning': 'bao gồm bữa sáng và tối',
                                'word': 'half board'},
                            {   'example': 'They enjoyed an all-inclusive stay '
                                           'at the resort.',
                                'ipa': '/ˌɔːl.ɪnˈkluː.sɪv/',
                                'meaning': 'trọn gói dịch vụ',
                                'word': 'all-inclusive'},
                            {   'example': 'You must present the travel '
                                           'voucher to board the bus.',
                                'ipa': '/ˈvaʊ.tʃər/',
                                'meaning': 'phiếu mua hàng, phiếu dịch vụ',
                                'word': 'voucher'},
                            {   'example': 'Please read your travel insurance '
                                           'policy thoroughly.',
                                'ipa': '/ɪnˈʃɔː.rəns ˈpɒl.ə.si/',
                                'meaning': 'hợp đồng bảo hiểm',
                                'word': 'insurance policy'},
                            {   'example': 'Check the visa requirement of your '
                                           'destination country.',
                                'ipa': '/ˈviː.zə rɪˈkwaɪə.mənt/',
                                'meaning': 'yêu cầu thị thực',
                                'word': 'visa requirement'},
                            {   'example': 'The exchange rate for the dollar '
                                           'has improved recently.',
                                'ipa': '/ɪksˈtʃeɪndʒ ˌreɪt/',
                                'meaning': 'tỷ giá hối đoái',
                                'word': 'exchange rate'},
                            {   'example': 'I need to visit a bureau de change '
                                           'before my flight.',
                                'ipa': '/ˌbjʊə.rəʊ de ˈʃɒ̃ʒ/',
                                'meaning': 'quầy đổi ngoại tệ',
                                'word': 'bureau de change'},
                            {   'example': "Traveler's checks are rarely "
                                           'accepted in local shops.',
                                'ipa': '/ˈtræv.əl.əz tʃek/',
                                'meaning': 'séc du lịch',
                                'word': "traveler's check"},
                            {   'example': 'Do you have any items to declare '
                                           'to customs today?',
                                'ipa': '/dɪˈkleər/',
                                'meaning': 'khai báo thuế/hải quan',
                                'word': 'declare'},
                            {   'example': 'Airport security will confiscate '
                                           'any large liquid bottles.',
                                'ipa': '/ˈkɒn.fɪ.skeɪt/',
                                'meaning': 'tịch thu',
                                'word': 'confiscate'},
                            {   'example': 'He was deported for entering the '
                                           'nation illegally.',
                                'ipa': '/dɪˈpɔːt/',
                                'meaning': 'trục xuất',
                                'word': 'deport'},
                            {   'example': 'The friendly old inn offered '
                                           'shelter to weary wayfarers.',
                                'ipa': '/ˈweɪˌfeə.rər/',
                                'meaning': 'người lữ hành, khách đi bộ',
                                'word': 'wayfarer'}],
                  'C1': [   {   'example': 'As an experienced globetrotter, '
                                           'she travels with very light bags.',
                                'ipa': '/ˈɡləʊbˌtrɒt.ər/',
                                'meaning': 'người đi du lịch khắp thế giới',
                                'word': 'globetrotter'},
                            {   'example': 'A microadventure is a cheap way to '
                                           'explore your own province.',
                                'ipa': '/ˈmaɪ.krəʊ.ədˈven.tʃər/',
                                'meaning': 'chuyến dã ngoại ngắn ngày, vi mô',
                                'word': 'microadventure'},
                            {   'example': 'Voluntourism lets travelers build '
                                           'schools for local children.',
                                'ipa': '/ˌvɒl.ənˈtʊə.rɪ.zəm/',
                                'meaning': 'du lịch kết hợp tình nguyện',
                                'word': 'voluntourism'},
                            {   'example': 'Overtourism is threatening the '
                                           'local heritage of Venice.',
                                'ipa': '/ˌəʊ.vəˈtʊə.rɪ.zəm/',
                                'meaning': 'tình trạng quá tải khách du lịch',
                                'word': 'overtourism'},
                            {   'example': 'They opted for a staycation rather '
                                           'than booking flights abroad.',
                                'ipa': '/ˌsteɪˈkeɪ.ʃən/',
                                'meaning': 'kỳ nghỉ tại nhà hoặc vùng lân cận',
                                'word': 'staycation'},
                            {   'example': 'Glamping combines outdoor nature '
                                           'experiences with hotel luxury.',
                                'ipa': '/ˈɡlæm.pɪŋ/',
                                'meaning': 'cắm trại kiểu sang trọng, cao cấp',
                                'word': 'glamping'},
                            {   'example': 'Slow travel emphasizes authentic '
                                           'connections with local history.',
                                'ipa': '/sləʊ ˈtræv.əl/',
                                'meaning': 'du lịch chậm, trải nghiệm chiều '
                                           'sâu',
                                'word': 'slow travel'},
                            {   'example': 'Dark tourism includes visits to '
                                           'old battlefields and prisons.',
                                'ipa': '/dɑːk ˈtʊə.rɪ.zəm/',
                                'meaning': 'du lịch đen, tham quan nơi thảm '
                                           'họa',
                                'word': 'dark tourism'},
                            {   'example': 'Culinary tourism is growing among '
                                           'food lovers worldwide.',
                                'ipa': '/ˈkʌl.ɪ.nər.i ˈtʊə.rɪ.zəm/',
                                'meaning': 'du lịch ẩm thực',
                                'word': 'culinary tourism'},
                            {   'example': 'Working as a digital nomad '
                                           'requires only a laptop and Wi-Fi.',
                                'ipa': '/ˌdɪdʒ.ɪ.təl ˈnəʊ.mæd/',
                                'meaning': 'người du mục kỹ thuật số',
                                'word': 'digital nomad'},
                            {   'example': 'We loved finding quiet spots that '
                                           'were off the beaten track.',
                                'ipa': '/ɒf ðə ˈbiː.tən træk/',
                                'meaning': 'nơi hẻo lánh, ít ai biết tới',
                                'word': 'off the beaten track'},
                            {   'example': 'The airport botanical garden '
                                           'served as a peaceful transit '
                                           'oasis.',
                                'ipa': '/ˈtræn.zɪt əʊˈeɪ.sɪs/',
                                'meaning': 'không gian thư giãn khi quá cảnh',
                                'word': 'transit oasis'},
                            {   'example': 'A fly-drive package is ideal for '
                                           'exploring huge national parks.',
                                'ipa': '/ˌflaɪ ˈdraɪv/',
                                'meaning': 'gói bay kết hợp thuê ô tô tự lái',
                                'word': 'fly-drive'},
                            {   'example': 'The red-eye flight was cheap but '
                                           'made me extremely tired.',
                                'ipa': '/ˌred.aɪ ˈflaɪt/',
                                'meaning': 'chuyến bay đêm muộn, bay mắt đỏ',
                                'word': 'red-eye flight'},
                            {   'example': 'Outbound travel has risen '
                                           'dramatically due to rising '
                                           'incomes.',
                                'ipa': '/ˌaʊt.baʊnd ˈtræv.əl/',
                                'meaning': 'du lịch ra nước ngoài',
                                'word': 'outbound travel'},
                            {   'example': 'The state has launched a campaign '
                                           'to boost inbound travel.',
                                'ipa': '/ˌɪn.baʊnd ˈtræv.əl/',
                                'meaning': 'du lịch đón khách quốc tế vào',
                                'word': 'inbound travel'},
                            {   'example': 'The resort was accused of '
                                           'greenwashing its carbon output '
                                           'claim.',
                                'ipa': '/ˈɡriːnˌwɒʃ.ɪŋ/',
                                'meaning': 'tẩy xanh (quảng cáo sinh thái giả '
                                           'tạo)',
                                'word': 'greenwashing'},
                            {   'example': 'Wearing sacred tribal dress as a '
                                           'costume is cultural appropriation.',
                                'ipa': '/ˈkʌl.tʃər.əl əˌprəʊ.priˈeɪ.ʃən/',
                                'meaning': 'chiếm đoạt văn hóa, chiếm dụng văn '
                                           'hóa',
                                'word': 'cultural appropriation'},
                            {   'example': 'You can calculate your carbon '
                                           'footprint before booking a flight.',
                                'ipa': '/ˌkɑː.bən ˈfʊt.prɪnt/',
                                'meaning': 'dấu chân carbon, khí thải cá nhân',
                                'word': 'carbon footprint'},
                            {   'example': 'Many airlines now offer carbon '
                                           'offsetting programs to passengers.',
                                'ipa': '/ˌkɑː.bən ˈɒf.set.ɪŋ/',
                                'meaning': 'bù đắp lượng phát thải carbon',
                                'word': 'carbon offsetting'},
                            {   'example': 'The historic sanctuary has '
                                           'exceeded its daily carrying '
                                           'capacity.',
                                'ipa': '/ˈkær.i.ɪŋ kəˈpæs.ə.ti/',
                                'meaning': 'sức chứa, giới hạn khách tối đa',
                                'word': 'carrying capacity'},
                            {   'example': 'Sustainable tourism seeks to '
                                           'preserve nature for future '
                                           'generations.',
                                'ipa': '/səˈsteɪ.nə.bəl ˈtʊə.rɪ.zəm/',
                                'meaning': 'du lịch bền vũg',
                                'word': 'sustainable tourism'},
                            {   'example': 'Regenerative travel encourages '
                                           'tourists to plant native trees.',
                                'ipa': '/rɪˈdʒen.ər.ə.tɪv ˈtræv.əl/',
                                'meaning': 'du lịch tái tạo, phục hồi môi '
                                           'trường',
                                'word': 'regenerative travel'},
                            {   'example': 'Indigenous tourism supports tribal '
                                           'art preservation projects.',
                                'ipa': '/ɪnˈdɪdʒ.ɪ.nəs ˈtʊə.rɪ.zəm/',
                                'meaning': 'du lịch tìm hiểu cộng đồng bản địa',
                                'word': 'indigenous tourism'},
                            {   'example': 'Living with a local family '
                                           'provides deep cultural immersion.',
                                'ipa': '/ˈkʌl.tʃər.əl ɪˈmɜː.ʃən/',
                                'meaning': 'sự hòa nhập văn hóa sâu sắc',
                                'word': 'cultural immersion'},
                            {   'example': 'The coastal town relies heavily on '
                                           'its transient summer visitors.',
                                'ipa': '/ˈtræn.zi.ənt/',
                                'meaning': 'mang tính nhất thời, lưu trú ngắn '
                                           'ngày',
                                'word': 'transient'},
                            {   'example': 'The lonely wanderer walked through '
                                           'the misty mountain valleys.',
                                'ipa': '/ˈwɒn.dər.ər/',
                                'meaning': 'kẻ lãng du, người đi đó đi đây',
                                'word': 'wanderer'},
                            {   'example': 'Her brief sojourn in Rome inspired '
                                           'her to paint historic ruins.',
                                'ipa': '/ˈsɒdʒ.ɜːn/',
                                'meaning': 'sự ở lại tạm thời, lưu trú tạm',
                                'word': 'sojourn'},
                            {   'example': 'He leads a highly peripatetic life '
                                           'as a global travel writer.',
                                'ipa': '/ˌper.i.pəˈtet.ɪk/',
                                'meaning': 'lưu động, đi đây đi đó liên tục',
                                'word': 'peripatetic'},
                            {   'example': 'The nomadic shepherds move their '
                                           'tents with the changing seasons.',
                                'ipa': '/nəʊˈmæd.ɪk/',
                                'meaning': 'thuộc du mục, nay đây mai đó',
                                'word': 'nomadic'},
                            {   'example': 'There is a massive expatriate '
                                           'community living in this coastal '
                                           'city.',
                                'ipa': '/ekˈspæt.ri.ət/',
                                'meaning': 'kiều dân, người sống ở nước ngoài',
                                'word': 'expatriate'},
                            {   'example': 'The government worked hard to '
                                           'repatriate tourists during the '
                                           'storm.',
                                'ipa': '/ˌriːˈpæt.ri.eɪt/',
                                'meaning': 'hồi hương, đưa về nước',
                                'word': 'repatriate'},
                            {   'example': 'European citizens are visa-exempt '
                                           'for short tourist stays.',
                                'ipa': '/ˈviː.zə ɪɡˈzempt/',
                                'meaning': 'được miễn thị thực',
                                'word': 'visa-exempt'},
                            {   'example': 'You can queue to receive your visa '
                                           'on arrival at the gate.',
                                'ipa': '/ˈviː.zə ɒn əˈraɪ.vəl/',
                                'meaning': 'thị thực tại cửa khẩu, visa tại '
                                           'sân bay',
                                'word': 'visa on arrival'},
                            {   'example': 'The biometric passport stores the '
                                           "traveler's facial details.",
                                'ipa': '/ˌbaɪ.əʊˈmet.rɪk ˈpɑːs.pɔːt/',
                                'meaning': 'hộ chiếu sinh trắc học',
                                'word': 'biometric passport'},
                            {   'example': 'We stopped for lunch at a historic '
                                           'town en route to Paris.',
                                'ipa': '/ˌɒ̃ ˈruːt/',
                                'meaning': 'trên đường đi, đang trên đường',
                                'word': 'en route'},
                            {   'example': 'Please proceed to the embarkation '
                                           'gate immediately.',
                                'ipa': '/ˌem.bɑːˈkeɪ.ʃən/',
                                'meaning': 'sự lên tàu, sự lên máy bay',
                                'word': 'embarkation'},
                            {   'example': 'All passengers must show health '
                                           'declarations upon disembarkation.',
                                'ipa': '/ˌdɪs.em.bɑːˈkeɪ.ʃən/',
                                'meaning': 'sự xuống tàu, sự xuống máy bay',
                                'word': 'disembarkation'},
                            {   'example': 'We marked several gorgeous '
                                           'waypoints along our highway route.',
                                'ipa': '/ˈweɪ.pɔɪnt/',
                                'meaning': 'điểm trung chuyển, tọa độ hành '
                                           'trình',
                                'word': 'waypoint'},
                            {   'example': 'The tourist group decided to '
                                           'charter a yacht for the afternoon.',
                                'ipa': '/ˈtʃɑː.tər/',
                                'meaning': 'thuê trọn chuyến tàu/xe/máy bay',
                                'word': 'charter'},
                            {   'example': 'The hotel concierge booked premium '
                                           'tickets for our opera show.',
                                'ipa': '/ˌkɒ̃.siˈeəʒ/',
                                'meaning': 'nhân viên hỗ trợ khách hàng khách '
                                           'sạn',
                                'word': 'concierge'},
                            {   'example': 'The pandemic caused massive job '
                                           'losses in the hospitality '
                                           'industry.',
                                'ipa': '/ˌhɒs.pɪˈtæl.ə.ti ˈɪn.də.stri/',
                                'meaning': 'ngành công nghiệp dịch vụ khách '
                                           'sạn',
                                'word': 'hospitality industry'},
                            {   'example': 'High-end tourism brings '
                                           'substantial revenue to coastal '
                                           'cities.',
                                'ipa': '/haɪ end ˈtʊə.rɪ.zəm/',
                                'meaning': 'du lịch phân khúc cao cấp',
                                'word': 'high-end tourism'},
                            {   'example': 'Sailing vacations serve as a '
                                           'profitable niche market for travel '
                                           'agencies.',
                                'ipa': '/niːʃ ˈmɑː.kɪt/',
                                'meaning': 'thị trường ngách',
                                'word': 'niche market'},
                            {   'example': 'She wrote an inspiring travelogue '
                                           'detailing her walks in Asia.',
                                'ipa': '/ˈtræv.əl.ɒɡ/',
                                'meaning': 'ký sự du lịch, phim tài liệu du '
                                           'lịch',
                                'word': 'travelogue'},
                            {   'example': 'They sailed away into completely '
                                           'unmapped areas of the ocean.',
                                'ipa': '/ʌnˈmæpt/',
                                'meaning': 'chưa được thám hiểm, chưa vẽ bản '
                                           'đồ',
                                'word': 'unmapped'},
                            {   'example': 'He spent two years photographing '
                                           'the pristine wilderness of Alaska.',
                                'ipa': '/ˈprɪs.tiːn ˈwɪl.də.nəs/',
                                'meaning': 'vùng hoang dã nguyên sơ',
                                'word': 'pristine wilderness'},
                            {   'example': 'Major airlines aim to achieve '
                                           'total carbon neutrality by 2050.',
                                'ipa': '/ˌkɑː.bən njuːˈtræl.ə.ti/',
                                'meaning': 'trung hòa carbon, giảm khí thải '
                                           'ròng',
                                'word': 'carbon neutrality'},
                            {   'example': 'The ancient citadel was declared a '
                                           'UNESCO world heritage site.',
                                'ipa': '/ˈher.ɪ.tɪdʒ saɪt/',
                                'meaning': 'di sản văn hóa/thiên nhiên thế '
                                           'giới',
                                'word': 'heritage site'},
                            {   'example': 'They joined a culinary tour to '
                                           'discover local street foods.',
                                'ipa': '/ˈkʌl.ɪ.nər.i tʊər/',
                                'meaning': 'tour du lịch ẩm thực trải nghiệm',
                                'word': 'culinary tour'}]}}




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
    
    # Nếu DB chỉ chứa ít hơn dữ liệu chuẩn (thiếu hụt), tự động xóa sạch để sinh lại 100% chuẩn xác
    if vocab_items and len(vocab_items) < expected_count:
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
