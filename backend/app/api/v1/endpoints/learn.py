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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lấy danh sách câu hỏi game trắc nghiệm từ vựng, ưu tiên từ cần ôn tập (Spaced Repetition) 
    và các từ hay sai (Weak Words) để tăng tần suất lặp lại.
    """
    from app.models.models import Vocabulary, VocabularyMemory, VocabularyWrongAnswer
    from datetime import datetime
    
    db_vocab = db.query(Vocabulary).filter(Vocabulary.level == level, Vocabulary.is_active == True).all()
    vocab_pool_dict = {}
    
    # Prioritize vocabulary items from database
    for v in db_vocab:
        vocab_pool_dict[v.word.lower()] = {
            "word": v.word,
            "ipa": v.ipa,
            "meaning": v.meaning,
            "example": v.example,
            "level": v.level
        }
        
    # Merge with base_vocab to ensure rich distractor options and prevent insufficient word crashes
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

    # Phân loại độ ưu tiên dựa trên AI Personalization
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

    # Chọn 10 từ (ưu tiên từ priority_items trước)
    selected_items = (priority_items + normal_items)[:10]

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
    "travel": {
        "A1": [
            {"word": "Ticket", "ipa": "/ˈtɪkɪt/", "meaning": "Vé xe/tàu/máy bay", "example": "Please show your ticket at the gate."},
            {"word": "Hotel", "ipa": "/həʊˈtel/", "meaning": "Khách sạn", "example": "We booked a room at the central hotel."},
            {"word": "Bus", "ipa": "/bʌs/", "meaning": "Xe buýt", "example": "I go to school by bus every day."},
            {"word": "Map", "ipa": "/mæp/", "meaning": "Bản đồ", "example": "We need a map to find our way."},
            {"word": "Passport", "ipa": "/ˈpɑːspɔːt/", "meaning": "Hộ chiếu", "example": "Don't forget to pack your passport."},
            {"word": "Fly", "ipa": "/flaɪ/", "meaning": "Bay, đi máy bay", "example": "I will fly to Paris tomorrow."},
            {"word": "Beach", "ipa": "/biːtʃ/", "meaning": "Bãi biển", "example": "We played soccer on the beach."},
            {"word": "Bag", "ipa": "/bæɡ/", "meaning": "Túi xách, ba lô", "example": "Put your camera in the bag."}
        ],
        "A2": [
            {"word": "Airport", "ipa": "/ˈeəpɔːt/", "meaning": "Sân bay", "example": "We arrived at the airport two hours early."},
            {"word": "Luggage", "ipa": "/ˈlʌɡɪdʒ/", "meaning": "Hành lý", "example": "They lost my luggage on the flight."},
            {"word": "Journey", "ipa": "/ˈdʒɜːni/", "meaning": "Hành trình, chuyến đi", "example": "Learning English is a journey."},
            {"word": "Tourist", "ipa": "/ˈtʊərɪst/", "meaning": "Khách du lịch", "example": "The city is full of tourists in summer."},
            {"word": "Flight", "ipa": "/flaɪt/", "meaning": "Chuyến bay", "example": "Our flight was delayed for three hours."},
            {"word": "Station", "ipa": "/ˈsteɪʃn/", "meaning": "Nhà ga, trạm", "example": "Let's meet at the train station."},
            {"word": "Guide", "ipa": "/ɡaɪd/", "meaning": "Hướng dẫn viên, sách hướng dẫn", "example": "Our tour guide was very knowledgeable."},
            {"word": "Souvenir", "ipa": "/ˌsuːvəˈnɪə(r)/", "meaning": "Quà lưu niệm", "example": "She bought a small souvenir from Rome."}
        ],
        "B1": [
            {"word": "Destination", "ipa": "/ˌdestɪˈneɪʃn/", "meaning": "Điểm đến", "example": "What is your final travel destination?"},
            {"word": "Itinerary", "ipa": "/aɪˈtɪnərəri/", "meaning": "Lịch trình chuyến đi", "example": "We planned our itinerary in detail."},
            {"word": "Accommodation", "ipa": "/əˌkɒməˈdeɪʃn/", "meaning": "Chỗ ở, nơi lưu trú", "example": "The hostel offers cheap accommodation."},
            {"word": "Explore", "ipa": "/ɪkˈsplɔː(r)/", "meaning": "Khám phá, thám hiểm", "example": "We spent the afternoon exploring the ancient temple."},
            {"word": "Reservation", "ipa": "/ˌrezəˈveɪʃn/", "meaning": "Sự đặt trước", "example": "I made a hotel reservation online."},
            {"word": "Adventure", "ipa": "/ədˈventʃə(r)/", "meaning": "Cuộc phiêu lưu", "example": "He wrote a book about his desert adventure."},
            {"word": "Excursion", "ipa": "/ɪkˈskɜːʃn/", "meaning": "Chuyến tham quan ngắn", "example": "We went on a day excursion to the island."},
            {"word": "Passenger", "ipa": "/ˈpæsɪndʒə(r)/", "meaning": "Hành khách", "example": "All passengers must fasten their seatbelts."}
        ],
        "B2": [
            {"word": "Expedition", "ipa": "/ˌekspəˈdɪʃn/", "meaning": "Cuộc thám hiểm", "example": "They organized an expedition to Antarctica."},
            {"word": "Picturesque", "ipa": "/ˌpɪktʃəˈresk/", "meaning": "Đẹp như tranh vẽ", "example": "We visited a picturesque seaside village."},
            {"word": "Breathtaking", "ipa": "/ˈbreθteɪkɪŋ/", "meaning": "Đẹp đến ngạt thở", "example": "The view from the top of the mountain was breathtaking."},
            {"word": "Hospitable", "ipa": "/hɒˈspɪtəbl/", "meaning": "Hiếu khách, mến khách", "example": "The local people were exceptionally hospitable."},
            {"word": "Spectacular", "ipa": "/spekˈtækjələ(r)/", "meaning": "Ngoạn mục, hùng vĩ", "example": "The fireworks display was truly spectacular."},
            {"word": "Wilderness", "ipa": "/ˈwɪldənəs/", "meaning": "Vùng hoang dã", "example": "They love camping in the deep wilderness."},
            {"word": "Sightseeing", "ipa": "/ˈsaɪtsiːɪŋ/", "meaning": "Sự tham quan ngắm cảnh", "example": "We did a lot of sightseeing in Paris."},
            {"word": "Transcontinental", "ipa": "/ˌtrænzˌkɒntɪˈnentl/", "meaning": "Xuyên lục địa", "example": "They took a transcontinental train trip."}
        ],
        "C1": [
            {"word": "Sojourn", "ipa": "/ˈsɒdʒɜːn/", "meaning": "Sự lưu trú tạm thời", "example": "Our brief sojourn in Rome was delightful."},
            {"word": "Uncharted", "ipa": "/ˌʌnˈtʃɑːtɪd/", "meaning": "Chưa được thám hiểm, xa lạ", "example": "They sailed into uncharted waters."},
            {"word": "Peregrination", "ipa": "/ˌperəɡrɪˈneɪʃn/", "meaning": "Hành trình dài ngày, sự ngao du", "example": "His artistic style evolved during his long peregrinations."},
            {"word": "Globetrotter", "ipa": "/ˈɡləʊbtrɒtə(r)/", "meaning": "Người đi du lịch khắp thế giới", "example": "She has been a globetrotter since graduating from university."},
            {"word": "Bespoke", "ipa": "/bɪˈspəʊk/", "meaning": "Được thiết kế riêng, độc bản", "example": "The agency designs bespoke travel experiences."},
            {"word": "Wanderlust", "ipa": "/ˈwɒndəlʌst/", "meaning": "Sự cuồng đi, đam mê du lịch", "example": "Her wanderlust led her to visit fifty countries."},
            {"word": "Unspoiled", "ipa": "/ˌʌnˈspɔɪld/", "meaning": "Hoang sơ, chưa bị đô thị hóa", "example": "We found a quiet, unspoiled island in Greece."},
            {"word": "Vagabond", "ipa": "/ˈvæɡəbɒnd/", "meaning": "Kẻ ngao du, người đi đây đi đó", "example": "He lived a vagabond lifestyle, moving from town to town."}
        ]
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
            {"word": "Fast", "ipa": "/fɑːst/", "meaning": "Nhanh", "example": "This computer is extremely fast."}
        ],
        "A2": [
            {"word": "Computer", "ipa": "/kəmˈpjuːtə(r)/", "meaning": "Máy tính", "example": "I use my computer for coding."},
            {"word": "System", "ipa": "/ˈsɪstəm/", "meaning": "Hệ thống", "example": "The computer system needs an update."},
            {"word": "Network", "ipa": "/ˈnetwɜːk/", "meaning": "Mạng lưới, mạng kết nối", "example": "The social network connects millions of people."},
            {"word": "Program", "ipa": "/ˈprəʊɡræm/", "meaning": "Chương trình máy tính", "example": "This program helps detect grammar errors."},
            {"word": "Digital", "ipa": "/ˈdɪdʒɪtl/", "meaning": "Kỹ thuật số", "example": "We are living in a digital age."},
            {"word": "Device", "ipa": "/dɪˈvaɪs/", "meaning": "Thiết bị", "example": "Smartphones are essential mobile devices."},
            {"word": "Storage", "ipa": "/ˈstɔːrɪdʒ/", "meaning": "Bộ nhớ lưu trữ", "example": "This cloud storage is highly secure."},
            {"word": "Process", "ipa": "/ˈprəʊses/", "meaning": "Xử lý, quy trình", "example": "The CPU processes information quickly."}
        ],
        "B1": [
            {"word": "Automation", "ipa": "/ˌɔːtəˈmeɪʃn/", "meaning": "Tự động hóa", "example": "Automation will change the future of work."},
            {"word": "Database", "ipa": "/ˈdeɪtəbeɪs/", "meaning": "Cơ sở dữ liệu", "example": "The customer records are in the database."},
            {"word": "Software", "ipa": "/ˈsɒftweə(r)/", "meaning": "Phần mềm", "example": "They design software for language learning."},
            {"word": "Interface", "ipa": "/ˈɪntəfeɪs/", "meaning": "Giao diện", "example": "The user interface is very clean."},
            {"word": "Assistant", "ipa": "/əˈsɪstənt/", "meaning": "Trợ lý", "example": "Siri is a virtual assistant on iOS."},
            {"word": "Analyze", "ipa": "/ˈænəlaɪz/", "meaning": "Phân tích", "example": "We use AI to analyze pronunciation."},
            {"word": "Prediction", "ipa": "/prɪˈdɪkʃn/", "meaning": "Sự dự đoán", "example": "AI makes a prediction based on trends."},
            {"word": "Algorithm", "ipa": "/ˈælɡərɪðəm/", "meaning": "Thuật toán", "example": "The search engine uses a complex algorithm."}
        ],
        "B2": [
            {"word": "Neural network", "ipa": "/ˈnjʊərəl ˈnetwɜːk/", "meaning": "Mạng nơ-ron", "example": "AI is built on neural networks."},
            {"word": "Machine learning", "ipa": "/məˈʃiːn ˈlɜːnɪŋ/", "meaning": "Học máy", "example": "Machine learning is a subset of AI."},
            {"word": "Dataset", "ipa": "/ˈdeɪtəset/", "meaning": "Tập dữ liệu", "example": "The model was trained on a massive dataset."},
            {"word": "Optimization", "ipa": "/ˌɒptɪmaɪˈzeɪʃn/", "meaning": "Sự tối ưu hóa", "example": "We perform optimization on the search logic."},
            {"word": "Classification", "ipa": "/ˌklæsɪfɪˈkeɪʃn/", "meaning": "Sự phân loại", "example": "The algorithm handles image classification."},
            {"word": "Framework", "ipa": "/ˈfreɪmwɜːk/", "meaning": "Khung làm việc, thư viện mẫu", "example": "TensorFlow is a popular framework for deep learning."},
            {"word": "Generative", "ipa": "/ˈdʒenərətɪv/", "meaning": "Tạo sinh", "example": "ChatGPT is a popular generative AI application."},
            {"word": "Autonomous", "ipa": "/ɔːˈtɒnəməs/", "meaning": "Tự trị, tự lái", "example": "Autonomous vehicles are being tested on public roads."}
        ],
        "C1": [
            {"word": "Cognitive computing", "ipa": "/ˈkɒɡnətɪv kəmˈpjuːtɪŋ/", "meaning": "Điện toán nhận thức", "example": "Cognitive computing mimics human thought."},
            {"word": "Deep learning", "ipa": "/diːp ˈlɜːnɪŋ/", "meaning": "Học sâu", "example": "Deep learning achieves state of the art results."},
            {"word": "Reinforcement", "ipa": "/ˌriːɪnˈfɔːsmənt/", "meaning": "Sự tăng cường", "example": "AlphaGo uses reinforcement learning."},
            {"word": "Transformers", "ipa": "/trænsˈfɔːməs/", "meaning": "Mô hình Transformer", "example": "Modern LLMs are built on the Transformer architecture."},
            {"word": "Supervised", "ipa": "/ˈsuːpəvaɪzd/", "meaning": "Có giám sát", "example": "Supervised learning requires labeled training data."},
            {"word": "Natural Language", "ipa": "/ˈnætʃrəl ˈlæŋɡwɪdʒ/", "meaning": "Ngôn ngữ tự nhiên", "example": "Natural Language Processing makes chatbots smarter."},
            {"word": "Hyperparameters", "ipa": "/ˌhaɪpəpəˈræmɪtəz/", "meaning": "Siêu tham số", "example": "Tuning hyperparameters is essential for model training."},
            {"word": "Backpropagation", "ipa": "/ˌbækprɒpəˈɡeɪʃn/", "meaning": "Lan truyền ngược", "example": "Backpropagation is used to train deep neural networks."}
        ]
    }
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
