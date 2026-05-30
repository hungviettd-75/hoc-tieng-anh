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
        other_meanings = [v["meaning"] for v in vocab_pool if v["word"] != item["word"]]
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
        ],
        "B1": [
            {"word": "innovation", "ipa": "/ˌɪn.əˈveɪ.ʃən/", "meaning": "sự đổi mới, sáng tạo", "example": "Innovation drives the technology industry forward."},
            {"word": "bandwidth", "ipa": "/ˈbænd.wɪdθ/", "meaning": "băng thông", "example": "We need more bandwidth to stream high-quality videos."},
            {"word": "cybersecurity", "ipa": "/ˌsaɪ.bə.sɪˈkjʊə.rə.ti/", "meaning": "an ninh mạng", "example": "Cybersecurity is essential for protecting personal data."},
            {"word": "cloud computing", "ipa": "/klaʊd kəmˈpjuː.tɪŋ/", "meaning": "điện toán đám mây", "example": "Many companies use cloud computing to store their data."},
            {"word": "virtual reality", "ipa": "/ˌvɜː.tʃu.əl riˈæl.ə.ti/", "meaning": "thực tế ảo", "example": "Virtual reality games make you feel like you are inside the game."},
            {"word": "wearable", "ipa": "/ˈweə.rə.bəl/", "meaning": "thiết bị đeo được", "example": "Smartwatches are the most common type of wearable technology."},
            {"word": "streaming", "ipa": "/ˈstriː.mɪŋ/", "meaning": "phát trực tuyến", "example": "Music streaming services have changed how we listen to songs."},
            {"word": "gadget", "ipa": "/ˈɡædʒ.ɪt/", "meaning": "thiết bị điện tử nhỏ", "example": "He loves buying the latest gadgets from tech stores."},
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
        ],
        "B2": [
            {"word": "segmentation", "ipa": "/ˌseɡ.menˈteɪ.ʃən/", "meaning": "phân khúc thị trường", "example": "Market segmentation allows companies to tailor products to specific groups."},
            {"word": "market penetration", "ipa": "/ˌmɑː.kɪt ˌpen.ɪˈtreɪ.ʃən/", "meaning": "thâm nhập thị trường", "example": "The company achieved rapid market penetration through aggressive pricing."},
            {"word": "brand equity", "ipa": "/brænd ˈek.wɪ.ti/", "meaning": "giá trị thương hiệu", "example": "Apple has built strong brand equity over the past decades."},
            {"word": "omnichannel", "ipa": "/ˌɒm.niˈtʃæn.əl/", "meaning": "đa kênh tích hợp", "example": "An omnichannel strategy ensures a seamless customer experience across all platforms."},
            {"word": "lead generation", "ipa": "/liːd ˌdʒen.əˈreɪ.ʃən/", "meaning": "tạo khách hàng tiềm năng", "example": "Lead generation is the first step in building a strong sales pipeline."},
            {"word": "A/B testing", "ipa": "/ˌeɪ biː ˈtes.tɪŋ/", "meaning": "thử nghiệm A/B", "example": "A/B testing showed that the red button got more clicks than the blue one."},
            {"word": "ROI", "ipa": "/ˌɑːr.əʊˈaɪ/", "meaning": "lợi tức đầu tư", "example": "We need to calculate the ROI before launching the new campaign."},
            {"word": "viral marketing", "ipa": "/ˌvaɪə.rəl ˈmɑː.kɪ.tɪŋ/", "meaning": "tiếp thị lan truyền", "example": "The video went viral, making it a perfect example of viral marketing."},
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
        ],
    },
    "job": {
        "A1": [
            {"word": "work", "ipa": "/wɜːk/", "meaning": "làm việc; công việc", "example": "I work from nine to five every day."},
            {"word": "job", "ipa": "/dʒɒb/", "meaning": "việc làm", "example": "She got a new job at a hospital."},
            {"word": "boss", "ipa": "/bɒs/", "meaning": "sếp, ông chủ", "example": "My boss is very kind and helpful."},
            {"word": "office", "ipa": "/ˈɒf.ɪs/", "meaning": "văn phòng", "example": "He goes to the office every morning."},
            {"word": "team", "ipa": "/tiːm/", "meaning": "đội, nhóm", "example": "Our team has five members."},
            {"word": "meeting", "ipa": "/ˈmiː.tɪŋ/", "meaning": "cuộc họp", "example": "We have a meeting at ten o'clock."},
            {"word": "money", "ipa": "/ˈmʌn.i/", "meaning": "tiền", "example": "She earns good money from her job."},
            {"word": "break", "ipa": "/breɪk/", "meaning": "giờ nghỉ", "example": "Let's take a break and have some coffee."},
        ],
        "A2": [
            {"word": "salary", "ipa": "/ˈsæl.ər.i/", "meaning": "lương tháng", "example": "His salary is paid at the end of each month."},
            {"word": "colleague", "ipa": "/ˈkɒl.iːɡ/", "meaning": "đồng nghiệp", "example": "I have lunch with my colleagues every day."},
            {"word": "schedule", "ipa": "/ˈʃedʒ.uːl/", "meaning": "lịch trình", "example": "My schedule is very busy this week."},
            {"word": "deadline", "ipa": "/ˈded.laɪn/", "meaning": "hạn chót", "example": "We must finish the report before the deadline."},
            {"word": "overtime", "ipa": "/ˈəʊ.və.taɪm/", "meaning": "làm thêm giờ", "example": "He often works overtime to complete his projects."},
            {"word": "resume", "ipa": "/ˈrez.juː.meɪ/", "meaning": "sơ yếu lý lịch", "example": "Please send your resume to our HR department."},
            {"word": "apply", "ipa": "/əˈplaɪ/", "meaning": "nộp đơn, ứng tuyển", "example": "She decided to apply for the manager position."},
            {"word": "hire", "ipa": "/haɪər/", "meaning": "thuê, tuyển dụng", "example": "The company plans to hire ten new employees."},
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
        ],
        "B1": [
            {"word": "entrepreneur", "ipa": "/ˌɒn.trə.prəˈnɜːr/", "meaning": "doanh nhân, nhà khởi nghiệp", "example": "The young entrepreneur founded her first company at the age of 22."},
            {"word": "startup", "ipa": "/ˈstɑːt.ʌp/", "meaning": "công ty khởi nghiệp", "example": "The startup received funding from several investors."},
            {"word": "strategy", "ipa": "/ˈstræt.ə.dʒi/", "meaning": "chiến lược", "example": "A clear business strategy is essential for long-term growth."},
            {"word": "revenue", "ipa": "/ˈrev.ən.juː/", "meaning": "doanh thu", "example": "The company's annual revenue exceeded ten million pounds."},
            {"word": "stakeholder", "ipa": "/ˈsteɪk.həʊl.dər/", "meaning": "bên liên quan", "example": "All stakeholders were invited to the annual general meeting."},
            {"word": "venture capital", "ipa": "/ˌven.tʃər ˈkæp.ɪ.təl/", "meaning": "vốn đầu tư mạo hiểm", "example": "The tech startup secured venture capital to expand its operations."},
            {"word": "merger", "ipa": "/ˈmɜː.dʒər/", "meaning": "sáp nhập", "example": "The merger of the two banks created the largest financial institution in the region."},
            {"word": "franchise", "ipa": "/ˈfræn.tʃaɪz/", "meaning": "nhượng quyền thương mại", "example": "He opened a fast-food franchise in the city centre."},
        ],
        "B2": [
            {"word": "acquisition", "ipa": "/ˌæk.wɪˈzɪʃ.ən/", "meaning": "sự mua lại", "example": "The acquisition of the rival firm strengthened the company's market position."},
            {"word": "scalable", "ipa": "/ˈskeɪ.lə.bəl/", "meaning": "có khả năng mở rộng", "example": "Investors prefer scalable business models that can grow rapidly."},
            {"word": "due diligence", "ipa": "/ˌdjuː ˈdɪl.ɪ.dʒəns/", "meaning": "thẩm định, rà soát kỹ lưỡng", "example": "The investors conducted due diligence before finalizing the deal."},
            {"word": "leveraged buyout", "ipa": "/ˌlev.ər.ɪdʒd ˈbaɪ.aʊt/", "meaning": "mua lại bằng vốn vay", "example": "The private equity firm completed a leveraged buyout of the retail chain."},
            {"word": "equity", "ipa": "/ˈek.wɪ.ti/", "meaning": "vốn chủ sở hữu, cổ phần", "example": "She holds a 20 percent equity stake in the company."},
            {"word": "liability", "ipa": "/ˌlaɪ.əˈbɪl.ə.ti/", "meaning": "nợ phải trả, trách nhiệm pháp lý", "example": "The company's total liabilities exceeded its assets last quarter."},
            {"word": "diversification", "ipa": "/daɪˌvɜː.sɪ.fɪˈkeɪ.ʃən/", "meaning": "đa dạng hóa", "example": "Diversification reduces the risk of depending on a single revenue source."},
            {"word": "portfolio", "ipa": "/pɔːtˈfəʊ.li.əʊ/", "meaning": "danh mục đầu tư", "example": "A well-balanced portfolio includes stocks, bonds, and real estate."},
        ],
        "C1": [
            {"word": "conglomerate", "ipa": "/kənˈɡlɒm.ər.ət/", "meaning": "tập đoàn đa ngành", "example": "The conglomerate operates in industries ranging from electronics to hospitality."},
            {"word": "arbitrage", "ipa": "/ˈɑː.bɪ.trɑːʒ/", "meaning": "kinh doanh chênh lệch giá", "example": "Arbitrage opportunities arise when the same asset is priced differently in two markets."},
            {"word": "fiduciary", "ipa": "/fɪˈdjuː.ʃi.ər.i/", "meaning": "người được ủy thác; liên quan đến ủy thác", "example": "Financial advisers have a fiduciary duty to act in their clients' best interests."},
            {"word": "amortization", "ipa": "/əˌmɔː.taɪˈzeɪ.ʃən/", "meaning": "khấu hao, trả dần", "example": "The amortization of the loan is spread over a period of thirty years."},
            {"word": "capitalization", "ipa": "/ˌkæp.ɪ.təl.aɪˈzeɪ.ʃən/", "meaning": "vốn hóa", "example": "The company's market capitalization reached fifty billion dollars."},
            {"word": "hostile takeover", "ipa": "/ˌhɒs.taɪl ˈteɪk.əʊ.vər/", "meaning": "thâu tóm thù địch", "example": "The board rejected the hostile takeover bid from the competing corporation."},
            {"word": "vertical integration", "ipa": "/ˌvɜː.tɪ.kəl ˌɪn.tɪˈɡreɪ.ʃən/", "meaning": "hội nhập dọc", "example": "Vertical integration allows the company to control its entire supply chain."},
            {"word": "oligopoly", "ipa": "/ˌɒl.ɪˈɡɒp.əl.i/", "meaning": "thị trường độc quyền nhóm", "example": "The airline industry is often described as an oligopoly dominated by a few major carriers."},
        ],
    },
    "sports": {
        "A1": [
            {"word": "ball", "ipa": "/bɔːl/", "meaning": "quả bóng", "example": "He kicked the ball into the net."},
            {"word": "run", "ipa": "/rʌn/", "meaning": "chạy", "example": "She likes to run in the park every morning."},
            {"word": "swim", "ipa": "/swɪm/", "meaning": "bơi", "example": "I swim in the pool every weekend."},
            {"word": "team", "ipa": "/tiːm/", "meaning": "đội, nhóm", "example": "Our team won the game yesterday."},
            {"word": "win", "ipa": "/wɪn/", "meaning": "thắng, chiến thắng", "example": "We want to win the match tonight."},
            {"word": "play", "ipa": "/pleɪ/", "meaning": "chơi", "example": "The children play football after school."},
            {"word": "goal", "ipa": "/ɡəʊl/", "meaning": "bàn thắng, mục tiêu", "example": "He scored a goal in the last minute."},
            {"word": "race", "ipa": "/reɪs/", "meaning": "cuộc đua", "example": "She finished first in the race."},
        ],
        "A2": [
            {"word": "coach", "ipa": "/kəʊtʃ/", "meaning": "huấn luyện viên", "example": "The coach trained the team every day."},
            {"word": "player", "ipa": "/ˈpleɪ.ər/", "meaning": "cầu thủ, người chơi", "example": "He is the best player on the team."},
            {"word": "score", "ipa": "/skɔːr/", "meaning": "tỉ số, ghi bàn", "example": "The final score was 3–1."},
            {"word": "match", "ipa": "/mætʃ/", "meaning": "trận đấu", "example": "The match starts at seven o'clock."},
            {"word": "champion", "ipa": "/ˈtʃæm.pi.ən/", "meaning": "nhà vô địch", "example": "She became the world champion last year."},
            {"word": "exercise", "ipa": "/ˈek.sə.saɪz/", "meaning": "tập thể dục, bài tập", "example": "Regular exercise is good for your health."},
            {"word": "athlete", "ipa": "/ˈæθ.liːt/", "meaning": "vận động viên", "example": "The athlete trained hard for the Olympics."},
            {"word": "stadium", "ipa": "/ˈsteɪ.di.əm/", "meaning": "sân vận động", "example": "The stadium was full of excited fans."},
        ],
        "B1": [
            {"word": "tournament", "ipa": "/ˈtʊə.nə.mənt/", "meaning": "giải đấu", "example": "Eight teams competed in the tournament."},
            {"word": "referee", "ipa": "/ˌref.əˈriː/", "meaning": "trọng tài", "example": "The referee gave a yellow card to the player."},
            {"word": "endurance", "ipa": "/ɪnˈdjʊə.rəns/", "meaning": "sức chịu đựng, sức bền", "example": "Marathon runners need great endurance."},
            {"word": "relay", "ipa": "/ˈriː.leɪ/", "meaning": "chạy tiếp sức", "example": "Our team won the 4x100 metres relay."},
            {"word": "sportsmanship", "ipa": "/ˈspɔːts.mən.ʃɪp/", "meaning": "tinh thần thể thao", "example": "He showed great sportsmanship by helping his opponent up."},
            {"word": "opponent", "ipa": "/əˈpəʊ.nənt/", "meaning": "đối thủ", "example": "She shook hands with her opponent after the match."},
            {"word": "medal", "ipa": "/ˈmed.əl/", "meaning": "huy chương", "example": "He won a gold medal at the Olympics."},
            {"word": "knockout", "ipa": "/ˈnɒk.aʊt/", "meaning": "knock-out, hạ gục", "example": "The boxer won by a knockout in the third round."},
        ],
        "B2": [
            {"word": "doping", "ipa": "/ˈdəʊ.pɪŋ/", "meaning": "sử dụng chất kích thích (trong thể thao)", "example": "The athlete was banned for doping violations."},
            {"word": "stamina", "ipa": "/ˈstæm.ɪ.nə/", "meaning": "thể lực, sức chịu đựng", "example": "Swimming long distances requires a lot of stamina."},
            {"word": "decathlon", "ipa": "/dɪˈkæθ.lɒn/", "meaning": "môn mười môn phối hợp", "example": "He competed in the decathlon at the national championships."},
            {"word": "underdog", "ipa": "/ˈʌn.də.dɒɡ/", "meaning": "đội cửa dưới, người không được đánh giá cao", "example": "The underdog surprised everyone by winning the final."},
            {"word": "aggregate", "ipa": "/ˈæɡ.rɪ.ɡət/", "meaning": "tổng tỉ số (qua nhiều trận)", "example": "They won 5–3 on aggregate over two legs."},
            {"word": "qualifier", "ipa": "/ˈkwɒl.ɪ.faɪ.ər/", "meaning": "vòng loại, trận vòng loại", "example": "The team must win this qualifier to reach the World Cup."},
            {"word": "overtime", "ipa": "/ˈəʊ.və.taɪm/", "meaning": "hiệp phụ, thời gian bù giờ", "example": "The game went into overtime after a 2–2 draw."},
            {"word": "relegation", "ipa": "/ˌrel.ɪˈɡeɪ.ʃən/", "meaning": "xuống hạng", "example": "The club is facing relegation to the lower division."},
        ],
        "C1": [
            {"word": "biomechanics", "ipa": "/ˌbaɪ.əʊ.mɪˈkæn.ɪks/", "meaning": "cơ sinh học", "example": "Biomechanics helps athletes improve their technique and prevent injuries."},
            {"word": "periodization", "ipa": "/ˌpɪə.ri.ə.daɪˈzeɪ.ʃən/", "meaning": "phân kỳ huấn luyện", "example": "Periodization divides the training year into phases for peak performance."},
            {"word": "proprioception", "ipa": "/ˌprəʊ.pri.əˈsep.ʃən/", "meaning": "cảm giác bản thể (khả năng cảm nhận vị trí cơ thể)", "example": "Good proprioception helps gymnasts maintain balance on the beam."},
            {"word": "plyometrics", "ipa": "/ˌplaɪ.əˈmet.rɪks/", "meaning": "bài tập nhảy bật (tăng sức mạnh bùng nổ)", "example": "Plyometrics training improves explosive power in sprinters."},
            {"word": "anaerobic threshold", "ipa": "/ˌæn.eəˈrəʊ.bɪk ˈθreʃ.həʊld/", "meaning": "ngưỡng yếm khí", "example": "Training above the anaerobic threshold builds speed and lactate tolerance."},
            {"word": "calisthenics", "ipa": "/ˌkæl.ɪsˈθen.ɪks/", "meaning": "thể dục dụng cụ (dùng trọng lượng cơ thể)", "example": "Calisthenics uses body weight for exercises like push-ups and pull-ups."},
            {"word": "kinaesthesia", "ipa": "/ˌkɪn.ɪsˈθiː.zi.ə/", "meaning": "cảm giác vận động", "example": "Kinaesthesia allows dancers to control their movements without looking."},
            {"word": "ergogenic", "ipa": "/ˌɜː.ɡəˈdʒen.ɪk/", "meaning": "tăng cường hiệu suất thể thao", "example": "Caffeine is a widely used ergogenic aid among endurance athletes."},
        ],
    },
    "music": {
        "A1": [
            {"word": "song", "ipa": "/sɒŋ/", "meaning": "bài hát", "example": "This is my favourite song."},
            {"word": "sing", "ipa": "/sɪŋ/", "meaning": "hát", "example": "She loves to sing in the shower."},
            {"word": "drum", "ipa": "/drʌm/", "meaning": "trống", "example": "He plays the drum in a band."},
            {"word": "piano", "ipa": "/piˈæn.əʊ/", "meaning": "đàn piano", "example": "My sister is learning to play the piano."},
            {"word": "guitar", "ipa": "/ɡɪˈtɑːr/", "meaning": "đàn guitar", "example": "He bought a new guitar last week."},
            {"word": "band", "ipa": "/bænd/", "meaning": "ban nhạc", "example": "The band played at the school festival."},
            {"word": "dance", "ipa": "/dɑːns/", "meaning": "nhảy, khiêu vũ", "example": "They like to dance to pop music."},
            {"word": "loud", "ipa": "/laʊd/", "meaning": "to, ồn ào", "example": "The music is too loud; please turn it down."},
        ],
        "A2": [
            {"word": "melody", "ipa": "/ˈmel.ə.di/", "meaning": "giai điệu", "example": "The melody of this song is very beautiful."},
            {"word": "rhythm", "ipa": "/ˈrɪð.əm/", "meaning": "nhịp điệu", "example": "She clapped her hands to the rhythm of the music."},
            {"word": "concert", "ipa": "/ˈkɒn.sət/", "meaning": "buổi hòa nhạc", "example": "We went to a concert in the park last night."},
            {"word": "lyrics", "ipa": "/ˈlɪr.ɪks/", "meaning": "lời bài hát", "example": "The lyrics of this song tell a sad story."},
            {"word": "microphone", "ipa": "/ˈmaɪ.krə.fəʊn/", "meaning": "micrô", "example": "The singer held the microphone and started singing."},
            {"word": "instrument", "ipa": "/ˈɪn.strə.mənt/", "meaning": "nhạc cụ", "example": "The violin is a beautiful instrument."},
            {"word": "chorus", "ipa": "/ˈkɔː.rəs/", "meaning": "điệp khúc, dàn hợp xướng", "example": "Everyone joined in singing the chorus."},
            {"word": "volume", "ipa": "/ˈvɒl.juːm/", "meaning": "âm lượng", "example": "Can you turn up the volume a little?"},
        ],
        "B1": [
            {"word": "symphony", "ipa": "/ˈsɪm.fə.ni/", "meaning": "bản giao hưởng", "example": "Beethoven's Fifth Symphony is one of the most famous works in classical music."},
            {"word": "composition", "ipa": "/ˌkɒm.pəˈzɪʃ.ən/", "meaning": "tác phẩm âm nhạc, sáng tác", "example": "This composition was written by Mozart when he was just twelve."},
            {"word": "orchestra", "ipa": "/ˈɔː.kɪ.strə/", "meaning": "dàn nhạc giao hưởng", "example": "The orchestra performed beautifully at the Royal Albert Hall."},
            {"word": "harmonize", "ipa": "/ˈhɑː.mə.naɪz/", "meaning": "hòa âm, phối hòa âm", "example": "The two singers harmonize perfectly together."},
            {"word": "genre", "ipa": "/ˈʒɒn.rə/", "meaning": "thể loại (nhạc)", "example": "Jazz is a genre that originated in the United States."},
            {"word": "rehearsal", "ipa": "/rɪˈhɜː.səl/", "meaning": "buổi tập, buổi diễn tập", "example": "The band had a rehearsal before the big show."},
            {"word": "acoustic", "ipa": "/əˈkuː.stɪk/", "meaning": "mộc, không dùng điện (nhạc cụ)", "example": "She prefers acoustic guitar to electric guitar."},
            {"word": "tempo", "ipa": "/ˈtem.pəʊ/", "meaning": "nhịp độ", "example": "The tempo of this waltz is slow and graceful."},
        ],
        "B2": [
            {"word": "virtuoso", "ipa": "/ˌvɜː.tʃuˈəʊ.zəʊ/", "meaning": "nghệ sĩ bậc thầy, danh cầm", "example": "The virtuoso played the violin with incredible skill."},
            {"word": "dissonance", "ipa": "/ˈdɪs.ən.əns/", "meaning": "sự bất hòa âm, nghịch âm", "example": "The composer used dissonance to create tension in the piece."},
            {"word": "crescendo", "ipa": "/krɪˈʃen.dəʊ/", "meaning": "đoạn tăng dần âm lượng", "example": "The music built to a dramatic crescendo at the end."},
            {"word": "counterpoint", "ipa": "/ˈkaʊn.tə.pɔɪnt/", "meaning": "đối âm, phức điệu", "example": "Bach was a master of counterpoint in his fugues."},
            {"word": "improvisation", "ipa": "/ɪmˌprɒv.aɪˈzeɪ.ʃən/", "meaning": "sự ứng tấu, ngẫu hứng", "example": "Jazz musicians are known for their improvisation skills."},
            {"word": "syncopation", "ipa": "/ˌsɪŋ.kəˈpeɪ.ʃən/", "meaning": "nhịp lệch, nhấn trái phách", "example": "Syncopation gives reggae music its distinctive rhythmic feel."},
            {"word": "modulation", "ipa": "/ˌmɒdʒ.ʊˈleɪ.ʃən/", "meaning": "chuyển điệu, chuyển giọng", "example": "The modulation from minor to major key lifted the mood of the piece."},
            {"word": "timbre", "ipa": "/ˈtæm.bər/", "meaning": "âm sắc", "example": "The timbre of a cello is warm and rich compared to a violin."},
        ],
        "C1": [
            {"word": "polyphony", "ipa": "/pəˈlɪf.ən.i/", "meaning": "đa âm, phức điệu nhiều bè", "example": "Renaissance choral music is characterized by rich polyphony."},
            {"word": "atonality", "ipa": "/ˌeɪ.tɒnˈæl.ɪ.ti/", "meaning": "thể vô điệu tính", "example": "Schoenberg's embrace of atonality revolutionized 20th-century music."},
            {"word": "chromaticism", "ipa": "/krəˈmæt.ɪ.sɪ.zəm/", "meaning": "bán âm, sắc thái bán cung", "example": "Wagner's operas are famous for their extensive use of chromaticism."},
            {"word": "leitmotif", "ipa": "/ˈlaɪt.məʊ.tiːf/", "meaning": "nhạc đề chủ đạo (gắn với nhân vật/ý tưởng)", "example": "Each character in the opera is associated with a distinct leitmotif."},
            {"word": "cadenza", "ipa": "/kəˈden.zə/", "meaning": "đoạn độc tấu ngẫu hứng (trong concerto)", "example": "The pianist played a brilliant cadenza before the final movement."},
            {"word": "rubato", "ipa": "/ruːˈbɑː.təʊ/", "meaning": "nhịp co giãn tự do", "example": "Chopin's nocturnes are often played with expressive rubato."},
            {"word": "tessitura", "ipa": "/ˌtes.ɪˈtjʊə.rə/", "meaning": "âm vực chính (của giọng hát/bè nhạc)", "example": "The role requires a soprano with a high tessitura."},
            {"word": "dodecaphony", "ipa": "/ˌdəʊ.dɪˈkæf.ən.i/", "meaning": "nhạc 12 âm (kỹ thuật sáng tác)", "example": "Dodecaphony uses all twelve notes of the chromatic scale in a fixed order."},
        ],
    },
    "health": {
        "A1": [
            {"word": "doctor", "ipa": "/ˈdɒk.tər/", "meaning": "bác sĩ", "example": "I need to see a doctor because I feel sick."},
            {"word": "sick", "ipa": "/sɪk/", "meaning": "ốm, bệnh", "example": "She is sick and cannot go to school today."},
            {"word": "pain", "ipa": "/peɪn/", "meaning": "cơn đau, sự đau đớn", "example": "I have a pain in my back."},
            {"word": "pill", "ipa": "/pɪl/", "meaning": "viên thuốc", "example": "Take one pill after breakfast."},
            {"word": "body", "ipa": "/ˈbɒd.i/", "meaning": "cơ thể", "example": "Exercise is good for your body."},
            {"word": "sleep", "ipa": "/sliːp/", "meaning": "ngủ, giấc ngủ", "example": "You need eight hours of sleep every night."},
            {"word": "water", "ipa": "/ˈwɔː.tər/", "meaning": "nước", "example": "Drink plenty of water every day."},
            {"word": "food", "ipa": "/fuːd/", "meaning": "thức ăn, thực phẩm", "example": "Healthy food gives you energy."},
        ],
        "A2": [
            {"word": "medicine", "ipa": "/ˈmed.ɪ.sən/", "meaning": "thuốc, y học", "example": "The doctor gave me some medicine for my cough."},
            {"word": "symptom", "ipa": "/ˈsɪmp.təm/", "meaning": "triệu chứng", "example": "A high temperature is a common symptom of the flu."},
            {"word": "headache", "ipa": "/ˈhed.eɪk/", "meaning": "đau đầu", "example": "I have a terrible headache today."},
            {"word": "vitamin", "ipa": "/ˈvɪt.ə.mɪn/", "meaning": "vitamin", "example": "Oranges are a good source of vitamin C."},
            {"word": "diet", "ipa": "/ˈdaɪ.ət/", "meaning": "chế độ ăn uống", "example": "A balanced diet includes fruit, vegetables, and protein."},
            {"word": "hospital", "ipa": "/ˈhɒs.pɪ.təl/", "meaning": "bệnh viện", "example": "She was taken to the hospital after the accident."},
            {"word": "checkup", "ipa": "/ˈtʃek.ʌp/", "meaning": "khám sức khỏe định kỳ", "example": "I go for a health checkup once a year."},
            {"word": "fever", "ipa": "/ˈfiː.vər/", "meaning": "sốt", "example": "The child has a fever and needs to rest."},
        ],
        "B1": [
            {"word": "nutrition", "ipa": "/njuːˈtrɪʃ.ən/", "meaning": "dinh dưỡng", "example": "Good nutrition is essential for growing children."},
            {"word": "immune system", "ipa": "/ɪˈmjuːn ˈsɪs.təm/", "meaning": "hệ miễn dịch", "example": "A healthy lifestyle strengthens your immune system."},
            {"word": "prescription", "ipa": "/prɪˈskrɪp.ʃən/", "meaning": "đơn thuốc", "example": "You need a prescription from the doctor to buy this medicine."},
            {"word": "diagnosis", "ipa": "/ˌdaɪ.əɡˈnəʊ.sɪs/", "meaning": "chẩn đoán", "example": "The diagnosis confirmed that she had diabetes."},
            {"word": "therapy", "ipa": "/ˈθer.ə.pi/", "meaning": "liệu pháp, trị liệu", "example": "Physical therapy helped him recover from the injury."},
            {"word": "chronic", "ipa": "/ˈkrɒn.ɪk/", "meaning": "mãn tính", "example": "She suffers from chronic back pain."},
            {"word": "allergy", "ipa": "/ˈæl.ə.dʒi/", "meaning": "dị ứng", "example": "He has an allergy to peanuts."},
            {"word": "mental health", "ipa": "/ˈmen.təl helθ/", "meaning": "sức khỏe tâm thần", "example": "Taking breaks from work is important for your mental health."},
        ],
        "B2": [
            {"word": "metabolism", "ipa": "/məˈtæb.əl.ɪ.zəm/", "meaning": "sự trao đổi chất", "example": "Regular exercise can boost your metabolism."},
            {"word": "holistic", "ipa": "/həʊˈlɪs.tɪk/", "meaning": "toàn diện (xét cả thể chất lẫn tinh thần)", "example": "She takes a holistic approach to health, considering both mind and body."},
            {"word": "rehabilitation", "ipa": "/ˌriː.hə.bɪl.ɪˈteɪ.ʃən/", "meaning": "phục hồi chức năng", "example": "He underwent months of rehabilitation after knee surgery."},
            {"word": "cardiovascular", "ipa": "/ˌkɑː.di.əʊˈvæs.kjʊ.lər/", "meaning": "thuộc tim mạch", "example": "Running is an excellent form of cardiovascular exercise."},
            {"word": "inflammation", "ipa": "/ˌɪn.fləˈmeɪ.ʃən/", "meaning": "viêm, sự viêm nhiễm", "example": "Chronic inflammation can lead to serious health problems."},
            {"word": "epidemiology", "ipa": "/ˌep.ɪ.diː.miˈɒl.ə.dʒi/", "meaning": "dịch tễ học", "example": "Epidemiology studies how diseases spread across populations."},
            {"word": "biomarker", "ipa": "/ˈbaɪ.əʊˌmɑː.kər/", "meaning": "chỉ dấu sinh học", "example": "Blood sugar level is an important biomarker for diabetes."},
            {"word": "prognosis", "ipa": "/prɒɡˈnəʊ.sɪs/", "meaning": "tiên lượng (dự đoán diễn biến bệnh)", "example": "The doctor said the prognosis for a full recovery is very good."},
        ],
        "C1": [
            {"word": "psychosomatic", "ipa": "/ˌsaɪ.kəʊ.səˈmæt.ɪk/", "meaning": "tâm thể (bệnh do tâm lý gây ra triệu chứng thể chất)", "example": "Stress can cause psychosomatic symptoms such as stomachaches."},
            {"word": "pathogenesis", "ipa": "/ˌpæθ.əˈdʒen.ə.sɪs/", "meaning": "cơ chế sinh bệnh", "example": "Researchers are studying the pathogenesis of Alzheimer's disease."},
            {"word": "immunodeficiency", "ipa": "/ˌɪm.jʊ.nəʊ.dɪˈfɪʃ.ən.si/", "meaning": "suy giảm miễn dịch", "example": "Immunodeficiency makes patients vulnerable to opportunistic infections."},
            {"word": "neurodegenerative", "ipa": "/ˌnjʊə.rəʊ.dɪˈdʒen.ər.ə.tɪv/", "meaning": "thoái hóa thần kinh", "example": "Parkinson's is a neurodegenerative disease that affects movement."},
            {"word": "pharmacokinetics", "ipa": "/ˌfɑː.mə.kəʊ.kɪˈnet.ɪks/", "meaning": "dược động học", "example": "Pharmacokinetics determines how quickly a drug is absorbed and eliminated."},
            {"word": "comorbidity", "ipa": "/ˌkəʊ.mɔːˈbɪd.ɪ.ti/", "meaning": "bệnh đi kèm, đồng mắc", "example": "Obesity is a common comorbidity in patients with type 2 diabetes."},
            {"word": "epigenetics", "ipa": "/ˌep.ɪ.dʒɪˈnet.ɪks/", "meaning": "biểu sinh học (thay đổi gen không do đột biến ADN)", "example": "Epigenetics explains how lifestyle choices can affect gene expression."},
            {"word": "microbiome", "ipa": "/ˈmaɪ.krəʊ.baɪ.əʊm/", "meaning": "hệ vi sinh vật", "example": "A diverse gut microbiome is linked to better overall health."},
        ],
    },
    "cooking": {
        "A1": [
            {"word": "cook", "ipa": "/kʊk/", "meaning": "nấu ăn, đầu bếp", "example": "My mother cooks dinner every evening."},
            {"word": "eat", "ipa": "/iːt/", "meaning": "ăn", "example": "We eat lunch at twelve o'clock."},
            {"word": "rice", "ipa": "/raɪs/", "meaning": "gạo, cơm", "example": "Rice is the main food in many Asian countries."},
            {"word": "egg", "ipa": "/eɡ/", "meaning": "trứng", "example": "I had a boiled egg for breakfast."},
            {"word": "meat", "ipa": "/miːt/", "meaning": "thịt", "example": "She bought some meat at the market."},
            {"word": "salt", "ipa": "/sɒlt/", "meaning": "muối", "example": "Add a little salt to the soup."},
            {"word": "hot", "ipa": "/hɒt/", "meaning": "nóng, cay", "example": "Be careful, the pan is very hot."},
            {"word": "knife", "ipa": "/naɪf/", "meaning": "dao", "example": "Use a sharp knife to cut the vegetables."},
        ],
        "A2": [
            {"word": "recipe", "ipa": "/ˈres.ɪ.pi/", "meaning": "công thức nấu ăn", "example": "I found a great recipe for chocolate cake online."},
            {"word": "fry", "ipa": "/fraɪ/", "meaning": "chiên, rán", "example": "Fry the onions until they are golden brown."},
            {"word": "boil", "ipa": "/bɔɪl/", "meaning": "luộc, đun sôi", "example": "Boil the potatoes for about twenty minutes."},
            {"word": "spice", "ipa": "/spaɪs/", "meaning": "gia vị", "example": "Indian food uses a lot of spice."},
            {"word": "oven", "ipa": "/ˈʌv.ən/", "meaning": "lò nướng", "example": "Preheat the oven to 180 degrees."},
            {"word": "sauce", "ipa": "/sɔːs/", "meaning": "nước sốt", "example": "This pasta tastes better with tomato sauce."},
            {"word": "ingredient", "ipa": "/ɪnˈɡriː.di.ənt/", "meaning": "nguyên liệu", "example": "You need fresh ingredients to make a good salad."},
            {"word": "dessert", "ipa": "/dɪˈzɜːt/", "meaning": "món tráng miệng", "example": "We had ice cream for dessert."},
        ],
        "B1": [
            {"word": "marinate", "ipa": "/ˈmær.ɪ.neɪt/", "meaning": "ướp (thịt, cá)", "example": "Marinate the chicken in soy sauce for at least two hours."},
            {"word": "sauté", "ipa": "/ˈsəʊ.teɪ/", "meaning": "xào nhanh (với ít dầu, lửa lớn)", "example": "Sauté the garlic and mushrooms in olive oil."},
            {"word": "broth", "ipa": "/brɒθ/", "meaning": "nước dùng, nước hầm", "example": "The chef prepared a rich chicken broth as the base for the soup."},
            {"word": "seasoning", "ipa": "/ˈsiː.zən.ɪŋ/", "meaning": "gia vị nêm nếm", "example": "The steak needs more seasoning to bring out the flavour."},
            {"word": "garnish", "ipa": "/ˈɡɑː.nɪʃ/", "meaning": "trang trí món ăn", "example": "Garnish the dish with fresh parsley before serving."},
            {"word": "portion", "ipa": "/ˈpɔː.ʃən/", "meaning": "khẩu phần, suất ăn", "example": "The restaurant serves generous portions of food."},
            {"word": "cuisine", "ipa": "/kwɪˈziːn/", "meaning": "ẩm thực, phong cách nấu ăn", "example": "Vietnamese cuisine is known for its fresh herbs and balanced flavours."},
            {"word": "appetizer", "ipa": "/ˈæp.ɪ.taɪ.zər/", "meaning": "món khai vị", "example": "We ordered spring rolls as an appetizer."},
        ],
        "B2": [
            {"word": "emulsify", "ipa": "/ɪˈmʌl.sɪ.faɪ/", "meaning": "nhũ hóa (trộn đều dầu và nước)", "example": "Whisk vigorously to emulsify the oil and vinegar into a smooth dressing."},
            {"word": "caramelize", "ipa": "/ˈkær.ə.mə.laɪz/", "meaning": "caramen hóa (nấu đường đến khi vàng nâu)", "example": "Caramelize the onions slowly over low heat for a sweet flavour."},
            {"word": "julienne", "ipa": "/ˌdʒuː.liˈen/", "meaning": "thái sợi (cắt rau thành sợi nhỏ dài)", "example": "Julienne the carrots and peppers for the stir-fry."},
            {"word": "reduction", "ipa": "/rɪˈdʌk.ʃən/", "meaning": "nước sốt cô đặc", "example": "Simmer the sauce until you get a thick balsamic reduction."},
            {"word": "infusion", "ipa": "/ɪnˈfjuː.ʒən/", "meaning": "sự ngâm chiết, hãm (trà, thảo mộc)", "example": "The chef made a rosemary infusion to flavour the cream."},
            {"word": "sous vide", "ipa": "/ˌsuː ˈviːd/", "meaning": "nấu chân không (ở nhiệt độ thấp)", "example": "Cooking steak sous vide produces perfectly even results."},
            {"word": "umami", "ipa": "/uːˈmɑː.mi/", "meaning": "vị umami (vị ngọt thịt, vị ngon)", "example": "Soy sauce and mushrooms are rich sources of umami flavour."},
            {"word": "blanch", "ipa": "/blɑːntʃ/", "meaning": "chần (nhúng nhanh vào nước sôi rồi làm lạnh)", "example": "Blanch the broccoli for two minutes, then plunge it into ice water."},
        ],
        "C1": [
            {"word": "gastronomy", "ipa": "/ɡæsˈtrɒn.ə.mi/", "meaning": "ẩm thực học, nghệ thuật ẩm thực", "example": "French gastronomy has been recognised by UNESCO as cultural heritage."},
            {"word": "molecular cuisine", "ipa": "/məˈlek.jʊ.lər kwɪˈziːn/", "meaning": "ẩm thực phân tử", "example": "Molecular cuisine uses scientific techniques to create innovative dishes."},
            {"word": "terroir", "ipa": "/teˈrwɑːr/", "meaning": "phong thổ (đặc trưng đất đai ảnh hưởng đến hương vị)", "example": "The terroir of this region gives the wine its unique character."},
            {"word": "deglaze", "ipa": "/diːˈɡleɪz/", "meaning": "tráng chảo (bằng chất lỏng để lấy phần cặn ngon)", "example": "Deglaze the pan with white wine to make a rich sauce."},
            {"word": "confit", "ipa": "/ˈkɒn.fiː/", "meaning": "thịt ướp muối nấu chậm trong mỡ", "example": "Duck confit is a classic dish of southwestern French cooking."},
            {"word": "béchamel", "ipa": "/ˈbeɪ.ʃə.mel/", "meaning": "sốt béchamel (sốt trắng từ bơ, bột mì, sữa)", "example": "Béchamel sauce is the base for many creamy pasta dishes."},
            {"word": "mise en place", "ipa": "/ˌmiːz ɒn ˈplɑːs/", "meaning": "chuẩn bị nguyên liệu sẵn trước khi nấu", "example": "Professional chefs always do their mise en place before service begins."},
            {"word": "charcuterie", "ipa": "/ʃɑːˈkuː.tər.i/", "meaning": "thịt nguội chế biến sẵn (xúc xích, giăm bông...)", "example": "The charcuterie board included prosciutto, salami, and pâté."},
        ],
    },
    "software": {
        "A1": [
            {"word": "file", "ipa": "/faɪl/", "meaning": "tệp tin", "example": "Please save the file before closing the program."},
            {"word": "save", "ipa": "/seɪv/", "meaning": "lưu lại", "example": "Remember to save your work every few minutes."},
            {"word": "open", "ipa": "/ˈəʊpən/", "meaning": "mở", "example": "Double-click the icon to open the application."},
            {"word": "click", "ipa": "/klɪk/", "meaning": "nhấp chuột", "example": "Click the button to start the download."},
            {"word": "type", "ipa": "/taɪp/", "meaning": "gõ, nhập liệu", "example": "Type your password in the text box."},
            {"word": "print", "ipa": "/prɪnt/", "meaning": "in", "example": "You can print the document from the File menu."},
            {"word": "copy", "ipa": "/ˈkɒpi/", "meaning": "sao chép", "example": "Copy the text and paste it into a new document."},
            {"word": "delete", "ipa": "/dɪˈliːt/", "meaning": "xóa", "example": "Delete the old files to free up space."},
        ],
        "A2": [
            {"word": "install", "ipa": "/ɪnˈstɔːl/", "meaning": "cài đặt", "example": "You need to install the latest version of the software."},
            {"word": "folder", "ipa": "/ˈfəʊldə/", "meaning": "thư mục", "example": "Create a new folder to organize your documents."},
            {"word": "browser", "ipa": "/ˈbraʊzə/", "meaning": "trình duyệt", "example": "Open your browser and go to the website."},
            {"word": "search", "ipa": "/sɜːtʃ/", "meaning": "tìm kiếm", "example": "Use the search bar to find the file you need."},
            {"word": "upload", "ipa": "/ʌpˈləʊd/", "meaning": "tải lên", "example": "Upload your photo to the cloud storage."},
            {"word": "backup", "ipa": "/ˈbækʌp/", "meaning": "sao lưu", "example": "Always keep a backup of your important data."},
            {"word": "virus", "ipa": "/ˈvaɪrəs/", "meaning": "vi-rút máy tính", "example": "The antivirus software detected a virus on your computer."},
            {"word": "error", "ipa": "/ˈerə/", "meaning": "lỗi", "example": "An error message appeared when I tried to run the program."},
        ],
        "B1": [
            {"word": "debug", "ipa": "/diːˈbʌɡ/", "meaning": "gỡ lỗi", "example": "The developer spent hours trying to debug the code."},
            {"word": "compiler", "ipa": "/kəmˈpaɪlə/", "meaning": "trình biên dịch", "example": "The compiler converts source code into machine language."},
            {"word": "repository", "ipa": "/rɪˈpɒzɪtəri/", "meaning": "kho lưu trữ mã nguồn", "example": "Push your changes to the remote repository on GitHub."},
            {"word": "framework", "ipa": "/ˈfreɪmwɜːk/", "meaning": "khung phần mềm", "example": "React is a popular JavaScript framework for building user interfaces."},
            {"word": "API", "ipa": "/ˌeɪ piː ˈaɪ/", "meaning": "giao diện lập trình ứng dụng", "example": "The API allows different applications to communicate with each other."},
            {"word": "deploy", "ipa": "/dɪˈplɔɪ/", "meaning": "triển khai", "example": "We will deploy the new version to the production server tonight."},
            {"word": "module", "ipa": "/ˈmɒdjuːl/", "meaning": "mô-đun, phân hệ", "example": "Each module handles a specific function of the application."},
            {"word": "version control", "ipa": "/ˈvɜːʃən kənˈtrəʊl/", "meaning": "quản lý phiên bản", "example": "Version control helps teams track changes to their codebase."},
        ],
        "B2": [
            {"word": "refactoring", "ipa": "/riːˈfæktərɪŋ/", "meaning": "tái cấu trúc mã nguồn", "example": "Refactoring the legacy code improved its readability and performance."},
            {"word": "microservices", "ipa": "/ˈmaɪkrəʊˌsɜːvɪsɪz/", "meaning": "vi dịch vụ", "example": "The company migrated from a monolithic system to microservices."},
            {"word": "containerization", "ipa": "/kənˌteɪnəraɪˈzeɪʃən/", "meaning": "đóng gói ứng dụng trong container", "example": "Containerization with Docker simplifies application deployment."},
            {"word": "CI/CD", "ipa": "/ˌsiː aɪ siː ˈdiː/", "meaning": "tích hợp/triển khai liên tục", "example": "Our CI/CD pipeline automatically tests and deploys every code change."},
            {"word": "middleware", "ipa": "/ˈmɪdəlweə/", "meaning": "phần mềm trung gian", "example": "The middleware handles authentication before requests reach the server."},
            {"word": "concurrency", "ipa": "/kənˈkʌrənsi/", "meaning": "xử lý đồng thời", "example": "Concurrency issues can cause unexpected bugs in multi-threaded applications."},
            {"word": "dependency injection", "ipa": "/dɪˈpendənsi ɪnˈdʒekʃən/", "meaning": "tiêm phụ thuộc", "example": "Dependency injection makes the code more testable and loosely coupled."},
            {"word": "polymorphism", "ipa": "/ˌpɒliˈmɔːfɪzəm/", "meaning": "tính đa hình", "example": "Polymorphism allows objects of different classes to be treated uniformly."},
        ],
        "C1": [
            {"word": "idempotent", "ipa": "/ˌaɪdəmˈpəʊtənt/", "meaning": "bất biến khi lặp lại", "example": "A PUT request should be idempotent, producing the same result regardless of repetition."},
            {"word": "monolithic architecture", "ipa": "/ˌmɒnəˈlɪθɪk ˈɑːkɪtektʃə/", "meaning": "kiến trúc nguyên khối", "example": "Monolithic architecture can become difficult to scale as the application grows."},
            {"word": "eventual consistency", "ipa": "/ɪˈventʃuəl kənˈsɪstənsi/", "meaning": "nhất quán cuối cùng", "example": "Distributed databases often rely on eventual consistency rather than immediate consistency."},
            {"word": "race condition", "ipa": "/reɪs kənˈdɪʃən/", "meaning": "điều kiện tranh chấp", "example": "A race condition occurred because two threads accessed the same resource simultaneously."},
            {"word": "garbage collection", "ipa": "/ˈɡɑːbɪdʒ kəˈlekʃən/", "meaning": "thu gom rác bộ nhớ", "example": "Java uses automatic garbage collection to manage memory allocation."},
            {"word": "bytecode", "ipa": "/ˈbaɪtkəʊd/", "meaning": "mã byte trung gian", "example": "The Java compiler translates source code into bytecode that runs on the JVM."},
            {"word": "sharding", "ipa": "/ˈʃɑːdɪŋ/", "meaning": "phân mảnh dữ liệu", "example": "Database sharding distributes data across multiple servers to improve performance."},
            {"word": "orthogonality", "ipa": "/ˌɔːθɒɡəˈnæləti/", "meaning": "tính trực giao, độc lập giữa các thành phần", "example": "Good software design emphasizes orthogonality so that changing one component does not affect others."},
        ],
    },
    "interview": {
        "A1": [
            {"word": "name", "ipa": "/neɪm/", "meaning": "tên", "example": "My name is Anna, nice to meet you."},
            {"word": "hello", "ipa": "/həˈləʊ/", "meaning": "xin chào", "example": "Hello, thank you for inviting me to this interview."},
            {"word": "nice", "ipa": "/naɪs/", "meaning": "vui, dễ chịu", "example": "It is nice to meet you in person."},
            {"word": "tell", "ipa": "/tel/", "meaning": "kể, nói", "example": "Please tell me about yourself."},
            {"word": "ask", "ipa": "/ɑːsk/", "meaning": "hỏi", "example": "Can I ask you a question about the role?"},
            {"word": "answer", "ipa": "/ˈɑːnsə/", "meaning": "trả lời", "example": "Take your time to answer each question carefully."},
            {"word": "thank", "ipa": "/θæŋk/", "meaning": "cảm ơn", "example": "Thank you for your time today."},
            {"word": "please", "ipa": "/pliːz/", "meaning": "xin vui lòng, làm ơn", "example": "Please have a seat and make yourself comfortable."},
        ],
        "A2": [
            {"word": "experience", "ipa": "/ɪkˈspɪəriəns/", "meaning": "kinh nghiệm", "example": "I have three years of experience in marketing."},
            {"word": "strength", "ipa": "/streŋθ/", "meaning": "điểm mạnh", "example": "My greatest strength is my ability to work under pressure."},
            {"word": "weakness", "ipa": "/ˈwiːknəs/", "meaning": "điểm yếu", "example": "I consider my weakness to be a lack of patience sometimes."},
            {"word": "question", "ipa": "/ˈkwestʃən/", "meaning": "câu hỏi", "example": "Do you have any question about the job description?"},
            {"word": "confident", "ipa": "/ˈkɒnfɪdənt/", "meaning": "tự tin", "example": "She appeared confident during the entire interview."},
            {"word": "polite", "ipa": "/pəˈlaɪt/", "meaning": "lịch sự", "example": "Always be polite when greeting the interviewer."},
            {"word": "prepare", "ipa": "/prɪˈpeə/", "meaning": "chuẩn bị", "example": "You should prepare your answers before the interview."},
            {"word": "introduce", "ipa": "/ˌɪntrəˈdjuːs/", "meaning": "giới thiệu", "example": "Let me introduce myself briefly before we begin."},
        ],
        "B1": [
            {"word": "behavioral question", "ipa": "/bɪˈheɪvjərəl ˈkwestʃən/", "meaning": "câu hỏi hành vi", "example": "A behavioral question asks you to describe how you handled a past situation."},
            {"word": "situational", "ipa": "/ˌsɪtʃuˈeɪʃənəl/", "meaning": "tình huống", "example": "Situational interview questions test how you would react to hypothetical scenarios."},
            {"word": "follow-up", "ipa": "/ˈfɒləʊ ʌp/", "meaning": "theo dõi, tiếp nối", "example": "Send a follow-up email to thank the interviewer after the meeting."},
            {"word": "body language", "ipa": "/ˈbɒdi ˈlæŋɡwɪdʒ/", "meaning": "ngôn ngữ cơ thể", "example": "Good body language can make a positive impression during an interview."},
            {"word": "elevator pitch", "ipa": "/ˈelɪveɪtə pɪtʃ/", "meaning": "bài giới thiệu ngắn gọn", "example": "Prepare a 30-second elevator pitch to summarize your career highlights."},
            {"word": "competency", "ipa": "/ˈkɒmpɪtənsi/", "meaning": "năng lực", "example": "The interviewer assessed each candidate's core competency for the role."},
            {"word": "panel interview", "ipa": "/ˈpænəl ˈɪntəvjuː/", "meaning": "phỏng vấn hội đồng", "example": "In a panel interview, you will face questions from several interviewers at once."},
            {"word": "shortlist", "ipa": "/ˈʃɔːtlɪst/", "meaning": "danh sách ứng viên chọn lọc", "example": "Only five candidates were placed on the shortlist for the final round."},
        ],
        "B2": [
            {"word": "negotiation", "ipa": "/nɪˌɡəʊʃiˈeɪʃən/", "meaning": "đàm phán", "example": "Salary negotiation is an important part of the hiring process."},
            {"word": "counteroffer", "ipa": "/ˈkaʊntərˌɒfə/", "meaning": "đề nghị đối lại", "example": "She received a counteroffer from her current employer after resigning."},
            {"word": "value proposition", "ipa": "/ˈvæljuː ˌprɒpəˈzɪʃən/", "meaning": "đề xuất giá trị", "example": "Articulate your value proposition to show what unique skills you bring to the team."},
            {"word": "cultural fit", "ipa": "/ˈkʌltʃərəl fɪt/", "meaning": "phù hợp văn hóa công ty", "example": "Employers look for cultural fit as well as technical skills."},
            {"word": "psychometric test", "ipa": "/ˌsaɪkəˈmetrɪk test/", "meaning": "bài kiểm tra tâm lý đo lường", "example": "Candidates must complete a psychometric test to assess cognitive abilities."},
            {"word": "assessment center", "ipa": "/əˈsesmənt ˈsentə/", "meaning": "trung tâm đánh giá ứng viên", "example": "The assessment center includes group exercises, presentations, and interviews."},
            {"word": "executive presence", "ipa": "/ɪɡˈzekjʊtɪv ˈprezəns/", "meaning": "phong thái lãnh đạo", "example": "Executive presence helps leaders inspire confidence in their teams."},
            {"word": "succession planning", "ipa": "/səkˈseʃən ˈplænɪŋ/", "meaning": "kế hoạch kế nhiệm", "example": "Succession planning ensures that key positions are always filled with qualified leaders."},
        ],
        "C1": [
            {"word": "impostor syndrome", "ipa": "/ɪmˈpɒstə ˈsɪndrəʊm/", "meaning": "hội chứng kẻ mạo danh", "example": "Many high achievers experience impostor syndrome despite their obvious success."},
            {"word": "cognitive bias", "ipa": "/ˈkɒɡnɪtɪv ˈbaɪəs/", "meaning": "thiên kiến nhận thức", "example": "Interviewers must be aware of cognitive bias to ensure fair evaluation."},
            {"word": "halo effect", "ipa": "/ˈheɪləʊ ɪˈfekt/", "meaning": "hiệu ứng hào quang", "example": "The halo effect can cause an interviewer to overlook a candidate's weaknesses."},
            {"word": "anchoring technique", "ipa": "/ˈæŋkərɪŋ tekˈniːk/", "meaning": "kỹ thuật neo (đàm phán)", "example": "Using an anchoring technique, she stated a high salary expectation to set the negotiation range."},
            {"word": "stress interview", "ipa": "/stres ˈɪntəvjuː/", "meaning": "phỏng vấn gây áp lực", "example": "A stress interview deliberately puts candidates under pressure to test their resilience."},
            {"word": "topgrading", "ipa": "/ˈtɒpɡreɪdɪŋ/", "meaning": "phương pháp tuyển dụng chuyên sâu", "example": "Topgrading involves chronological interviews to identify consistently high-performing candidates."},
            {"word": "structured interview", "ipa": "/ˈstrʌktʃəd ˈɪntəvjuː/", "meaning": "phỏng vấn có cấu trúc", "example": "A structured interview uses the same set of questions for every candidate to ensure fairness."},
            {"word": "competency framework", "ipa": "/ˈkɒmpɪtənsi ˈfreɪmwɜːk/", "meaning": "khung năng lực", "example": "The company designed a competency framework to standardize performance expectations across departments."},
        ],
    },
    "finance": {
        "A1": [
            {"word": "money", "ipa": "/ˈmʌni/", "meaning": "tiền", "example": "She saved enough money to buy a new phone."},
            {"word": "pay", "ipa": "/peɪ/", "meaning": "trả tiền", "example": "You can pay by cash or card at the checkout."},
            {"word": "save", "ipa": "/seɪv/", "meaning": "tiết kiệm", "example": "I try to save a little money every month."},
            {"word": "rich", "ipa": "/rɪtʃ/", "meaning": "giàu có", "example": "He became rich after starting his own business."},
            {"word": "poor", "ipa": "/pɔː/", "meaning": "nghèo", "example": "Many poor families struggle to afford basic necessities."},
            {"word": "coin", "ipa": "/kɔɪn/", "meaning": "đồng xu", "example": "I found a coin on the ground near the bus stop."},
            {"word": "bill", "ipa": "/bɪl/", "meaning": "tờ tiền, hóa đơn", "example": "He paid the restaurant bill with a fifty-pound bill."},
            {"word": "cash", "ipa": "/kæʃ/", "meaning": "tiền mặt", "example": "Do you have enough cash or should we find an ATM?"},
        ],
        "A2": [
            {"word": "account", "ipa": "/əˈkaʊnt/", "meaning": "tài khoản", "example": "I opened a savings account at the bank."},
            {"word": "credit", "ipa": "/ˈkredɪt/", "meaning": "tín dụng", "example": "She used her credit card to buy groceries online."},
            {"word": "debit", "ipa": "/ˈdebɪt/", "meaning": "ghi nợ", "example": "The payment was taken directly from my debit card."},
            {"word": "interest", "ipa": "/ˈɪntrəst/", "meaning": "lãi suất", "example": "The savings account earns three percent interest per year."},
            {"word": "loan", "ipa": "/ləʊn/", "meaning": "khoản vay", "example": "They took out a loan to buy their first house."},
            {"word": "insurance", "ipa": "/ɪnˈʃʊərəns/", "meaning": "bảo hiểm", "example": "Health insurance covers the cost of medical treatment."},
            {"word": "exchange", "ipa": "/ɪksˈtʃeɪndʒ/", "meaning": "trao đổi, đổi tiền", "example": "You can exchange your currency at the airport counter."},
            {"word": "receipt", "ipa": "/rɪˈsiːt/", "meaning": "biên lai", "example": "Keep the receipt in case you need to return the item."},
        ],
        "B1": [
            {"word": "investment", "ipa": "/ɪnˈvestmənt/", "meaning": "đầu tư", "example": "Real estate can be a profitable long-term investment."},
            {"word": "dividend", "ipa": "/ˈdɪvɪdend/", "meaning": "cổ tức", "example": "Shareholders receive a dividend payment every quarter."},
            {"word": "inflation", "ipa": "/ɪnˈfleɪʃən/", "meaning": "lạm phát", "example": "Inflation reduces the purchasing power of money over time."},
            {"word": "mortgage", "ipa": "/ˈmɔːɡɪdʒ/", "meaning": "thế chấp", "example": "They applied for a mortgage to finance their new home."},
            {"word": "stock market", "ipa": "/stɒk ˈmɑːkɪt/", "meaning": "thị trường chứng khoán", "example": "The stock market experienced a sharp decline last week."},
            {"word": "bond", "ipa": "/bɒnd/", "meaning": "trái phiếu", "example": "Government bonds are considered a low-risk investment."},
            {"word": "asset", "ipa": "/ˈæset/", "meaning": "tài sản", "example": "The company listed all its assets in the annual report."},
            {"word": "portfolio", "ipa": "/pɔːtˈfəʊliəʊ/", "meaning": "danh mục đầu tư", "example": "A diversified portfolio helps reduce overall financial risk."},
        ],
        "B2": [
            {"word": "derivatives", "ipa": "/dɪˈrɪvətɪvz/", "meaning": "phái sinh (tài chính)", "example": "Derivatives are financial instruments whose value depends on an underlying asset."},
            {"word": "hedge fund", "ipa": "/hedʒ fʌnd/", "meaning": "quỹ phòng hộ", "example": "The hedge fund uses complex strategies to generate high returns."},
            {"word": "liquidity", "ipa": "/lɪˈkwɪdəti/", "meaning": "tính thanh khoản", "example": "Stocks generally offer higher liquidity than real estate investments."},
            {"word": "depreciation", "ipa": "/dɪˌpriːʃiˈeɪʃən/", "meaning": "khấu hao", "example": "The depreciation of the equipment is recorded over a five-year period."},
            {"word": "fiscal policy", "ipa": "/ˈfɪskəl ˈpɒləsi/", "meaning": "chính sách tài khóa", "example": "The government adjusted its fiscal policy to stimulate economic growth."},
            {"word": "yield curve", "ipa": "/jiːld kɜːv/", "meaning": "đường cong lợi suất", "example": "An inverted yield curve is often seen as a predictor of recession."},
            {"word": "commodities", "ipa": "/kəˈmɒdətiz/", "meaning": "hàng hóa (nguyên liệu)", "example": "Gold and oil are among the most traded commodities in the world."},
            {"word": "securitization", "ipa": "/sɪˌkjʊərɪtaɪˈzeɪʃən/", "meaning": "chứng khoán hóa", "example": "Securitization allows banks to convert loans into tradeable securities."},
        ],
        "C1": [
            {"word": "quantitative easing", "ipa": "/ˈkwɒntɪtətɪv ˈiːzɪŋ/", "meaning": "nới lỏng định lượng", "example": "The central bank implemented quantitative easing to increase money supply during the crisis."},
            {"word": "credit default swap", "ipa": "/ˈkredɪt dɪˈfɔːlt swɒp/", "meaning": "hợp đồng hoán đổi rủi ro tín dụng", "example": "Credit default swaps played a significant role in the 2008 financial crisis."},
            {"word": "collateralized debt obligation", "ipa": "/kəˌlætərəlaɪzd det ˌɒblɪˈɡeɪʃən/", "meaning": "nghĩa vụ nợ có thế chấp", "example": "A collateralized debt obligation bundles various loans into a single investment product."},
            {"word": "algorithmic trading", "ipa": "/ˌælɡəˈrɪðmɪk ˈtreɪdɪŋ/", "meaning": "giao dịch thuật toán", "example": "Algorithmic trading uses computer programs to execute trades at high speed."},
            {"word": "macroprudential", "ipa": "/ˌmækrəʊpruːˈdenʃəl/", "meaning": "an toàn vĩ mô", "example": "Macroprudential regulations aim to prevent systemic risks in the financial system."},
            {"word": "Basel accords", "ipa": "/ˈbɑːzəl əˈkɔːdz/", "meaning": "hiệp ước Basel", "example": "The Basel accords set international standards for bank capital requirements."},
            {"word": "deleveraging", "ipa": "/diːˈlevərɪdʒɪŋ/", "meaning": "giảm đòn bẩy tài chính", "example": "After the crisis, many companies began deleveraging by paying down their debts."},
            {"word": "stagflation", "ipa": "/stæɡˈfleɪʃən/", "meaning": "đình lạm (đình trệ + lạm phát)", "example": "Stagflation combines stagnant economic growth with high inflation and unemployment."},
        ],
    },
    "fashion": {
        "A1": [
            {"word": "shirt", "ipa": "/ʃɜːt/", "meaning": "áo sơ mi", "example": "He wore a white shirt to the office today."},
            {"word": "dress", "ipa": "/dres/", "meaning": "váy đầm", "example": "She bought a beautiful red dress for the party."},
            {"word": "shoe", "ipa": "/ʃuː/", "meaning": "giày", "example": "I need a new pair of shoes for the wedding."},
            {"word": "hat", "ipa": "/hæt/", "meaning": "mũ, nón", "example": "Wear a hat to protect yourself from the sun."},
            {"word": "color", "ipa": "/ˈkʌlə/", "meaning": "màu sắc", "example": "What color do you prefer, blue or green?"},
            {"word": "wear", "ipa": "/weə/", "meaning": "mặc, mang", "example": "You should wear something warm because it is cold outside."},
            {"word": "big", "ipa": "/bɪɡ/", "meaning": "lớn, rộng", "example": "This jacket is too big for me; I need a smaller one."},
            {"word": "small", "ipa": "/smɔːl/", "meaning": "nhỏ, chật", "example": "The shoes are too small, so my feet hurt."},
        ],
        "A2": [
            {"word": "fashion", "ipa": "/ˈfæʃən/", "meaning": "thời trang", "example": "Paris is considered the capital of fashion in the world."},
            {"word": "style", "ipa": "/staɪl/", "meaning": "phong cách", "example": "Her style is a mix of classic and modern elements."},
            {"word": "jeans", "ipa": "/dʒiːnz/", "meaning": "quần bò", "example": "He always wears jeans and a T-shirt on weekends."},
            {"word": "jacket", "ipa": "/ˈdʒækɪt/", "meaning": "áo khoác", "example": "Bring a jacket because it might rain this evening."},
            {"word": "accessory", "ipa": "/əkˈsesəri/", "meaning": "phụ kiện", "example": "A simple accessory like a scarf can transform your outfit."},
            {"word": "trendy", "ipa": "/ˈtrendi/", "meaning": "hợp thời trang", "example": "That new store sells trendy clothes at affordable prices."},
            {"word": "fabric", "ipa": "/ˈfæbrɪk/", "meaning": "vải", "example": "Cotton is a natural fabric that feels comfortable in hot weather."},
            {"word": "size", "ipa": "/saɪz/", "meaning": "kích cỡ", "example": "What size do you wear — small, medium, or large?"},
        ],
        "B1": [
            {"word": "haute couture", "ipa": "/ˌəʊt kuːˈtjʊə/", "meaning": "thời trang cao cấp", "example": "Haute couture garments are handmade and extremely expensive."},
            {"word": "runway", "ipa": "/ˈrʌnweɪ/", "meaning": "sàn diễn thời trang", "example": "The models walked down the runway showcasing the new collection."},
            {"word": "collection", "ipa": "/kəˈlekʃən/", "meaning": "bộ sưu tập", "example": "The designer unveiled her spring collection at Milan Fashion Week."},
            {"word": "textile", "ipa": "/ˈtekstaɪl/", "meaning": "dệt may, vải dệt", "example": "The textile industry plays a major role in the country's economy."},
            {"word": "sustainable fashion", "ipa": "/səˈsteɪnəbəl ˈfæʃən/", "meaning": "thời trang bền vững", "example": "Sustainable fashion encourages using eco-friendly materials and ethical labor practices."},
            {"word": "silhouette", "ipa": "/ˌsɪluˈet/", "meaning": "dáng trang phục", "example": "The A-line silhouette is flattering on most body types."},
            {"word": "vintage", "ipa": "/ˈvɪntɪdʒ/", "meaning": "đồ cổ điển, phong cách retro", "example": "She loves shopping at vintage stores for unique clothing pieces."},
            {"word": "wardrobe", "ipa": "/ˈwɔːdrəʊb/", "meaning": "tủ quần áo, bộ sưu tập trang phục cá nhân", "example": "She organized her wardrobe by season and color."},
        ],
        "B2": [
            {"word": "avant-garde", "ipa": "/ˌævɒ̃ˈɡɑːd/", "meaning": "tiên phong, phá cách", "example": "The avant-garde designer challenged traditional fashion norms with her bold creations."},
            {"word": "minimalism", "ipa": "/ˈmɪnɪməlɪzəm/", "meaning": "chủ nghĩa tối giản", "example": "Minimalism in fashion focuses on clean lines and neutral colors."},
            {"word": "fast fashion", "ipa": "/fɑːst ˈfæʃən/", "meaning": "thời trang nhanh", "example": "Fast fashion produces cheap clothing quickly, but it harms the environment."},
            {"word": "capsule wardrobe", "ipa": "/ˈkæpsjuːl ˈwɔːdrəʊb/", "meaning": "tủ đồ tối giản", "example": "A capsule wardrobe consists of versatile pieces that can be mixed and matched."},
            {"word": "bespoke tailoring", "ipa": "/bɪˈspəʊk ˈteɪlərɪŋ/", "meaning": "may đo riêng", "example": "Savile Row in London is famous for its bespoke tailoring tradition."},
            {"word": "athleisure", "ipa": "/æθˈleʒə/", "meaning": "thời trang thể thao kết hợp thường ngày", "example": "Athleisure allows people to wear sportswear as everyday casual clothing."},
            {"word": "upcycling", "ipa": "/ˈʌpˌsaɪklɪŋ/", "meaning": "tái chế nâng cấp", "example": "Upcycling old garments into new designs reduces textile waste significantly."},
            {"word": "draping", "ipa": "/ˈdreɪpɪŋ/", "meaning": "kỹ thuật xếp nếp vải", "example": "Draping is a technique where fabric is arranged on a mannequin to create a design."},
        ],
        "C1": [
            {"word": "sartorial", "ipa": "/sɑːˈtɔːriəl/", "meaning": "thuộc về may mặc, trang phục", "example": "His sartorial choices always reflected impeccable taste and attention to detail."},
            {"word": "haute couture atelier", "ipa": "/ˌəʊt kuːˈtjʊə ˌætəlˈjeɪ/", "meaning": "xưởng may thời trang cao cấp", "example": "Each haute couture atelier in Paris employs dozens of skilled artisans."},
            {"word": "fashion semiotics", "ipa": "/ˈfæʃən ˌsemiˈɒtɪks/", "meaning": "ký hiệu học thời trang", "example": "Fashion semiotics studies how clothing communicates social meaning and identity."},
            {"word": "deconstructionism", "ipa": "/ˌdiːkənˈstrʌkʃənɪzəm/", "meaning": "phong cách giải cấu trúc", "example": "Deconstructionism in fashion deliberately exposes seams and unfinished edges."},
            {"word": "prêt-à-porter", "ipa": "/ˌpretɑːpɔːˈteɪ/", "meaning": "thời trang may sẵn cao cấp", "example": "Prêt-à-porter bridges the gap between haute couture and mass-market clothing."},
            {"word": "bias cut", "ipa": "/ˈbaɪəs kʌt/", "meaning": "cắt chéo vải", "example": "The bias cut allows the fabric to drape elegantly over the body."},
            {"word": "toile", "ipa": "/twɑːl/", "meaning": "mẫu thử bằng vải thô", "example": "The designer made a toile first to test the garment's shape and fit."},
            {"word": "fashion diaspora", "ipa": "/ˈfæʃən daɪˈæspərə/", "meaning": "sự phân tán văn hóa thời trang toàn cầu", "example": "The fashion diaspora has brought diverse cultural influences into mainstream design."},
        ],
    },
    "social_media": {
        "A1": [
            {"word": "like", "ipa": "/laɪk/", "meaning": "thích, nút thích", "example": "She got over a hundred likes on her new profile picture."},
            {"word": "share", "ipa": "/ʃeə/", "meaning": "chia sẻ", "example": "Share this post with your friends if you find it useful."},
            {"word": "post", "ipa": "/pəʊst/", "meaning": "bài đăng", "example": "He wrote a post about his vacation on social media."},
            {"word": "photo", "ipa": "/ˈfəʊtəʊ/", "meaning": "ảnh", "example": "Upload a photo to your profile so people can recognize you."},
            {"word": "friend", "ipa": "/frend/", "meaning": "bạn bè, kết bạn", "example": "I added her as a friend on Facebook yesterday."},
            {"word": "chat", "ipa": "/tʃæt/", "meaning": "trò chuyện", "example": "We can chat online using the messaging app."},
            {"word": "follow", "ipa": "/ˈfɒləʊ/", "meaning": "theo dõi", "example": "Follow our page to get the latest news and updates."},
            {"word": "comment", "ipa": "/ˈkɒment/", "meaning": "bình luận", "example": "Please leave a comment below if you have any questions."},
        ],
        "A2": [
            {"word": "profile", "ipa": "/ˈprəʊfaɪl/", "meaning": "trang cá nhân", "example": "Update your profile with your latest contact information."},
            {"word": "hashtag", "ipa": "/ˈhæʃtæɡ/", "meaning": "thẻ dấu thăng", "example": "Use a relevant hashtag to make your post easier to find."},
            {"word": "notification", "ipa": "/ˌnəʊtɪfɪˈkeɪʃən/", "meaning": "thông báo", "example": "I received a notification that someone liked my photo."},
            {"word": "subscribe", "ipa": "/səbˈskraɪb/", "meaning": "đăng ký theo dõi", "example": "Subscribe to the channel to watch new videos every week."},
            {"word": "stream", "ipa": "/striːm/", "meaning": "phát trực tiếp", "example": "He decided to stream his gaming session live on Twitch."},
            {"word": "upload", "ipa": "/ʌpˈləʊd/", "meaning": "tải lên", "example": "You can upload videos up to ten minutes long on this platform."},
            {"word": "follower", "ipa": "/ˈfɒləʊə/", "meaning": "người theo dõi", "example": "She now has over ten thousand followers on Instagram."},
            {"word": "content", "ipa": "/ˈkɒntent/", "meaning": "nội dung", "example": "Creating good content is the key to growing your audience."},
        ],
        "B1": [
            {"word": "algorithm", "ipa": "/ˈælɡərɪðəm/", "meaning": "thuật toán", "example": "The algorithm decides which posts appear first in your feed."},
            {"word": "viral", "ipa": "/ˈvaɪrəl/", "meaning": "lan truyền rộng rãi", "example": "The funny video went viral and was viewed by millions of people."},
            {"word": "influencer", "ipa": "/ˈɪnfluənsə/", "meaning": "người có sức ảnh hưởng", "example": "Many brands pay influencers to promote their products on Instagram."},
            {"word": "engagement", "ipa": "/ɪnˈɡeɪdʒmənt/", "meaning": "mức tương tác", "example": "High engagement on your posts helps increase your visibility online."},
            {"word": "analytics", "ipa": "/ˌænəˈlɪtɪks/", "meaning": "phân tích dữ liệu", "example": "Use analytics tools to track how your content is performing."},
            {"word": "community", "ipa": "/kəˈmjuːnəti/", "meaning": "cộng đồng", "example": "Building a strong community around your brand takes time and effort."},
            {"word": "moderator", "ipa": "/ˈmɒdəreɪtə/", "meaning": "người kiểm duyệt", "example": "The moderator removed offensive comments from the forum."},
            {"word": "digital footprint", "ipa": "/ˈdɪdʒɪtəl ˈfʊtprɪnt/", "meaning": "dấu chân số", "example": "Everything you post online contributes to your digital footprint."},
        ],
        "B2": [
            {"word": "echo chamber", "ipa": "/ˈekəʊ ˈtʃeɪmbə/", "meaning": "buồng vang (thông tin một chiều)", "example": "Social media can create echo chambers where users only see opinions they agree with."},
            {"word": "misinformation", "ipa": "/ˌmɪsɪnfəˈmeɪʃən/", "meaning": "thông tin sai lệch", "example": "It is important to fact-check articles to avoid spreading misinformation."},
            {"word": "content curation", "ipa": "/ˈkɒntent kjʊəˈreɪʃən/", "meaning": "tuyển chọn nội dung", "example": "Content curation involves selecting and sharing the best resources on a topic."},
            {"word": "social listening", "ipa": "/ˈsəʊʃəl ˈlɪsənɪŋ/", "meaning": "lắng nghe mạng xã hội", "example": "Brands use social listening to monitor what customers are saying about them online."},
            {"word": "sentiment analysis", "ipa": "/ˈsentɪmənt əˈnæləsɪs/", "meaning": "phân tích cảm xúc", "example": "Sentiment analysis helps companies understand public opinion about their products."},
            {"word": "clickbait", "ipa": "/ˈklɪkbeɪt/", "meaning": "mồi nhấp chuột", "example": "The headline was pure clickbait designed to attract attention without substance."},
            {"word": "doomscrolling", "ipa": "/ˈduːmˌskrəʊlɪŋ/", "meaning": "cuộn xem tin tiêu cực liên tục", "example": "Doomscrolling through bad news at night can seriously affect your mental health."},
            {"word": "cancel culture", "ipa": "/ˈkænsəl ˈkʌltʃə/", "meaning": "văn hóa tẩy chay", "example": "Cancel culture has sparked debate about free speech and accountability online."},
        ],
        "C1": [
            {"word": "algorithmic amplification", "ipa": "/ˌælɡəˈrɪðmɪk ˌæmplɪfɪˈkeɪʃən/", "meaning": "khuếch đại bằng thuật toán", "example": "Algorithmic amplification can spread extreme content faster than factual news."},
            {"word": "digital detox", "ipa": "/ˈdɪdʒɪtəl ˈdiːtɒks/", "meaning": "cai nghiện công nghệ", "example": "She took a week-long digital detox to improve her mental well-being."},
            {"word": "parasocial relationship", "ipa": "/ˌpærəˈsəʊʃəl rɪˈleɪʃənʃɪp/", "meaning": "mối quan hệ ảo một chiều", "example": "Fans often develop parasocial relationships with celebrities they follow online."},
            {"word": "Dunbar's number", "ipa": "/ˈdʌnbɑːz ˈnʌmbə/", "meaning": "số Dunbar (giới hạn quan hệ xã hội)", "example": "Dunbar's number suggests humans can maintain about 150 meaningful relationships."},
            {"word": "filter bubble", "ipa": "/ˈfɪltə ˈbʌbəl/", "meaning": "bong bóng lọc thông tin", "example": "Filter bubbles limit users' exposure to diverse perspectives and viewpoints."},
            {"word": "astroturfing", "ipa": "/ˈæstrəʊˌtɜːfɪŋ/", "meaning": "tạo phong trào giả", "example": "Astroturfing creates the illusion of grassroots support for a product or political cause."},
            {"word": "deepfake", "ipa": "/ˈdiːpfeɪk/", "meaning": "video/ảnh giả tạo bằng AI", "example": "Deepfake technology can create convincing but entirely fabricated videos of public figures."},
            {"word": "platform capitalism", "ipa": "/ˈplætfɔːm ˈkæpɪtəlɪzəm/", "meaning": "chủ nghĩa tư bản nền tảng", "example": "Platform capitalism describes how tech companies monetize user data and digital interactions."},
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
        ],
        "A2": [
            {"word": "Airport", "ipa": "/ˈeəpɔːt/", "meaning": "Sân bay", "example": "We arrived at the airport two hours early."},
            {"word": "Luggage", "ipa": "/ˈlʌɡɪdʒ/", "meaning": "Hành lý", "example": "They lost my luggage on the flight."},
            {"word": "Journey", "ipa": "/ˈdʒɜːni/", "meaning": "Hành trình, chuyến đi", "example": "Learning English is a journey."},
            {"word": "Tourist", "ipa": "/ˈtʊərɪst/", "meaning": "Khách du lịch", "example": "The city is full of tourists in summer."},
            {"word": "Flight", "ipa": "/flaɪt/", "meaning": "Chuyến bay", "example": "Our flight was delayed for three hours."},
            {"word": "Station", "ipa": "/ˈsteɪʃn/", "meaning": "Nhà ga, trạm", "example": "Let's meet at the train station."},
            {"word": "Guide", "ipa": "/ɡaɪd/", "meaning": "Hướng dẫn viên, sách hướng dẫn", "example": "Our tour guide was very knowledgeable."},
            {"word": "Souvenir", "ipa": "/ˌsuːvəˈnɪə(r)/", "meaning": "Quà lưu niệm", "example": "She bought a small souvenir from Rome."},
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
        ],
        "C1": [
            {"word": "Sojourn", "ipa": "/ˈsɒdʒɜːn/", "meaning": "Sự lưu trú tạm thời", "example": "Our brief sojourn in Rome was delightful."},
            {"word": "Uncharted", "ipa": "/ˌʌnˈtʃɑːtɪd/", "meaning": "Chưa được thám hiểm, xa lạ", "example": "They sailed into uncharted waters."},
            {"word": "Peregrination", "ipa": "/ˌperəɡrɪˈneɪʃn/", "meaning": "Hành trình dài ngày, sự ngao du", "example": "His artistic style evolved during his long peregrinations."},
            {"word": "Globetrotter", "ipa": "/ˈɡləʊbtrɒtə(r)/", "meaning": "Người đi du lịch khắp thế giới", "example": "She has been a globetrotter since graduating from university."},
            {"word": "Bespoke", "ipa": "/bɪˈspəʊk/", "meaning": "Được thiết kế riêng, độc bản", "example": "The agency designs bespoke travel experiences."},
            {"word": "Wanderlust", "ipa": "/ˈwɒndəlʌst/", "meaning": "Sự cuồng đi, đam mê du lịch", "example": "Her wanderlust led her to visit fifty countries."},
            {"word": "Unspoiled", "ipa": "/ˌʌnˈspɔɪld/", "meaning": "Hoang sơ, chưa bị đô thị hóa", "example": "We found a quiet, unspoiled island in Greece."},
            {"word": "Vagabond", "ipa": "/ˈvæɡəbɒnd/", "meaning": "Kẻ ngao du, người đi đây đi đó", "example": "He lived a vagabond lifestyle, moving from town to town."},
        ],
    },
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
        ],
        "A2": [
            {"word": "Computer", "ipa": "/kəmˈpjuːtə(r)/", "meaning": "Máy tính", "example": "I use my computer for coding."},
            {"word": "System", "ipa": "/ˈsɪstəm/", "meaning": "Hệ thống", "example": "The computer system needs an update."},
            {"word": "Network", "ipa": "/ˈnetwɜːk/", "meaning": "Mạng lưới, mạng kết nối", "example": "The social network connects millions of people."},
            {"word": "Program", "ipa": "/ˈprəʊɡræm/", "meaning": "Chương trình máy tính", "example": "This program helps detect grammar errors."},
            {"word": "Digital", "ipa": "/ˈdɪdʒɪtl/", "meaning": "Kỹ thuật số", "example": "We are living in a digital age."},
            {"word": "Device", "ipa": "/dɪˈvaɪs/", "meaning": "Thiết bị", "example": "Smartphones are essential mobile devices."},
            {"word": "Storage", "ipa": "/ˈstɔːrɪdʒ/", "meaning": "Bộ nhớ lưu trữ", "example": "This cloud storage is highly secure."},
            {"word": "Process", "ipa": "/ˈprəʊses/", "meaning": "Xử lý, quy trình", "example": "The CPU processes information quickly."},
        ],
        "B1": [
            {"word": "Automation", "ipa": "/ˌɔːtəˈmeɪʃn/", "meaning": "Tự động hóa", "example": "Automation will change the future of work."},
            {"word": "Database", "ipa": "/ˈdeɪtəbeɪs/", "meaning": "Cơ sở dữ liệu", "example": "The customer records are in the database."},
            {"word": "Software", "ipa": "/ˈsɒftweə(r)/", "meaning": "Phần mềm", "example": "They design software for language learning."},
            {"word": "Interface", "ipa": "/ˈɪntəfeɪs/", "meaning": "Giao diện", "example": "The user interface is very clean."},
            {"word": "Assistant", "ipa": "/əˈsɪstənt/", "meaning": "Trợ lý", "example": "Siri is a virtual assistant on iOS."},
            {"word": "Analyze", "ipa": "/ˈænəlaɪz/", "meaning": "Phân tích", "example": "We use AI to analyze pronunciation."},
            {"word": "Prediction", "ipa": "/prɪˈdɪkʃn/", "meaning": "Sự dự đoán", "example": "AI makes a prediction based on trends."},
            {"word": "Algorithm", "ipa": "/ˈælɡərɪðəm/", "meaning": "Thuật toán", "example": "The search engine uses a complex algorithm."},
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

    # So sánh với dữ liệu fallback gốc để đảm bảo DB không thiếu hụt từ vựng
    fallback_topic = topic_vocab_db.get(topic_code, topic_vocab_db["travel"])
    fallback_level_items = fallback_topic.get(user_level, fallback_topic.get("B1", []))
    expected_count = len(fallback_level_items)
    
    # Nếu DB chỉ chứa ít hơn dữ liệu fallback gốc (dữ liệu cũ thiếu hụt), tự động dọn dẹp để sinh lại dữ liệu phong phú mới
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
