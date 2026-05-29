from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Float, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    avatar_url = Column(String)
    level = Column(String, default="A1")
    is_active = Column(Boolean(), default=True)
    is_verified = Column(Boolean(), default=False)
    is_admin = Column(Boolean(), default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    streak = relationship("Streak", back_populates="user", uselist=False)
    xp = relationship("UserXP", back_populates="user", uselist=False)
    daily_goals = relationship("DailyGoal", back_populates="user", cascade="all, delete-orphan")
    activities = relationship("ActivityLog", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")
    memories = relationship("AIMemory", back_populates="user")
    pronunciation_sessions = relationship("PronunciationSession", back_populates="user", cascade="all, delete-orphan")
    skill_level = relationship("UserSkillLevel", back_populates="user", uselist=False, cascade="all, delete-orphan")
    weak_points = relationship("WeakPoint", back_populates="user", cascade="all, delete-orphan")
    learning_preference = relationship("LearningPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")
    recommendations = relationship("RecommendationHistory", back_populates="user", cascade="all, delete-orphan")
    achievements = relationship("UserAchievement", back_populates="user", cascade="all, delete-orphan")
    missions = relationship("UserMission", back_populates="user", cascade="all, delete-orphan")
    rewards = relationship("Reward", back_populates="user", cascade="all, delete-orphan")
    subscription = relationship("UserSubscription", back_populates="user", uselist=False)
    vocabulary_games = relationship("VocabularyGame", back_populates="user", cascade="all, delete-orphan")
    
class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    role = Column(String) # user or assistant
    content = Column(String)
    audio_url = Column(String)
    grammar_corrections = Column(JSON) # Store list of corrections
    pronunciation_score = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    conversation = relationship("Conversation", back_populates="messages")

class Streak(Base):
    __tablename__ = "streaks"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_activity_date = Column(DateTime(timezone=True))
    
    user = relationship("User", back_populates="streak")

class AIMemory(Base):
    __tablename__ = "ai_memories"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    key = Column(String, index=True)
    value = Column(String)
    importance = Column(Float, default=1.0)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", back_populates="memories")

class UserXP(Base):
    __tablename__ = "user_xp"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    total_xp = Column(Integer, default=0)
    level = Column(Integer, default=1)
    
    user = relationship("User", back_populates="xp")

class DailyGoal(Base):
    __tablename__ = "daily_goals"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    goal_type = Column(String) # speaking, vocabulary, listening
    target_value = Column(Integer) # e.g., 30 minutes, 20 words
    current_value = Column(Integer, default=0)
    date = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="daily_goals")

class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    activity_type = Column(String)
    xp_earned = Column(Integer)
    duration_minutes = Column(Integer, default=0)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="activities")

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_revoked = Column(Boolean(), default=False)
    
    user = relationship("User", back_populates="refresh_tokens")

class PronunciationSession(Base):
    __tablename__ = "pronunciation_sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    target_text = Column(String, nullable=False)
    transcribed_text = Column(String)
    audio_path = Column(String)
    overall_score = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="pronunciation_sessions")
    scores = relationship("PronunciationScore", back_populates="session", cascade="all, delete-orphan")

class PronunciationScore(Base):
    __tablename__ = "pronunciation_scores"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("pronunciation_sessions.id"))
    metric = Column(String, nullable=False)  # fluency, pronunciation, confidence, intonation
    score = Column(Float, default=0.0)
    feedback = Column(String)
    
    session = relationship("PronunciationSession", back_populates="scores")

# --- AI Learning Engine Models ---

class UserSkillLevel(Base):
    __tablename__ = "user_skill_levels"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    vocabulary = Column(Float, default=0.0) # Scale 0.0 - 100.0 or IELTS equivalent
    grammar = Column(Float, default=0.0)
    pronunciation = Column(Float, default=0.0)
    listening = Column(Float, default=0.0)
    fluency = Column(Float, default=0.0)
    last_evaluated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    user = relationship("User", back_populates="skill_level")

class WeakPoint(Base):
    __tablename__ = "weak_points"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    category = Column(String, nullable=False) # e.g. "grammar", "pronunciation"
    description = Column(String, nullable=False) # e.g. "Present Perfect Tense", "th sound"
    frequency = Column(Integer, default=1) # How many times they made this mistake
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", back_populates="weak_points")

class LearningPreference(Base):
    __tablename__ = "learning_preferences"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    daily_time_goal_minutes = Column(Integer, default=15)
    target_level = Column(String, default="B2") # CEFR levels: A1, A2, B1, B2, C1, C2
    focus_areas = Column(JSON) # List of strings e.g. ["speaking", "business english"]
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    user = relationship("User", back_populates="learning_preference")

class RecommendationHistory(Base):
    __tablename__ = "recommendation_histories"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    recommended_content_id = Column(String) # UUID or identifier generated by AI
    topic = Column(String)
    content_type = Column(String) # "vocabulary", "grammar", "roleplay"
    difficulty_level = Column(String)
    status = Column(String, default="pending") # "pending", "started", "completed", "skipped"
    score = Column(Float, nullable=True) # How well they did
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="recommendations")

# --- Gamification Models ---

class Achievement(Base):
    __tablename__ = "achievements"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    icon_url = Column(String)
    required_xp = Column(Integer, default=0)
    condition_type = Column(String) # e.g., 'reach_level', 'login_streak', 'complete_conversations'
    condition_value = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user_achievements = relationship("UserAchievement", back_populates="achievement", cascade="all, delete-orphan")

class UserAchievement(Base):
    __tablename__ = "user_achievements"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    achievement_id = Column(Integer, ForeignKey("achievements.id"))
    unlocked_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="achievements")
    achievement = relationship("Achievement", back_populates="user_achievements")

class Mission(Base):
    __tablename__ = "missions"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String)
    reward_xp = Column(Integer, default=10)
    mission_type = Column(String) # e.g., 'daily', 'weekly'
    target_action = Column(String) # e.g., 'speak_duration', 'complete_lesson'
    target_value = Column(Integer) # e.g., 15 (minutes)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user_missions = relationship("UserMission", back_populates="mission", cascade="all, delete-orphan")

class UserMission(Base):
    __tablename__ = "user_missions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    mission_id = Column(Integer, ForeignKey("missions.id"))
    progress = Column(Integer, default=0)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="missions")
    mission = relationship("Mission", back_populates="user_missions")

class Reward(Base):
    __tablename__ = "rewards"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    reward_type = Column(String) # e.g., 'xp', 'badge', 'premium_days'
    amount = Column(Integer)
    claimed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="rewards")

# --- Subscription Models ---

class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # e.g., 'free', 'basic', 'premium', 'enterprise'
    price_monthly = Column(Float, default=0.0)
    price_yearly = Column(Float, default=0.0)
    max_conversations_per_day = Column(Integer, default=5)
    max_speaking_sessions_per_day = Column(Integer, default=3)
    has_ai_memory = Column(Boolean, default=False)
    has_advanced_analytics = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    subscriptions = relationship("UserSubscription", back_populates="plan")

class UserSubscription(Base):
    __tablename__ = "user_subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"))
    status = Column(String, default="active")  # active, cancelled, expired
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="subscription")
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")

# --- Analytics Models ---

class AnalyticsSnapshot(Base):
    __tablename__ = "analytics_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime(timezone=True), index=True)
    metric_type = Column(String, index=True)
    metric_value = Column(Float)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# --- V2 Models ---

class SpeakingSessionV2(Base):
    """Enhanced speaking session with realtime data."""
    __tablename__ = "speaking_sessions_v2"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_type = Column(String, default="free_talk")  # "free_talk", "practice", "roleplay"
    total_corrections = Column(Integer, default=0)
    local_corrections = Column(Integer, default=0)  # Corrections handled locally
    llm_corrections = Column(Integer, default=0)    # Corrections needing LLM
    tokens_used = Column(Integer, default=0)
    duration_seconds = Column(Integer, default=0)
    compressed_summary = Column(String)  # Compact session summary
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class PronunciationMistakeLog(Base):
    """Track specific pronunciation mistakes for pattern learning."""
    __tablename__ = "pronunciation_mistake_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    mistake_type = Column(String)  # "th_sound", "ending_s", "vowel_confusion"
    original_word = Column(String)
    correct_word = Column(String)
    ipa_target = Column(String)
    frequency = Column(Integer, default=1)
    last_occurred = Column(DateTime(timezone=True), server_default=func.now())
    is_mastered = Column(Boolean, default=False)

class Vocabulary(Base):
    __tablename__ = "vocabularies"
    id = Column(Integer, primary_key=True, index=True)
    word = Column(String, nullable=False, index=True)
    ipa = Column(String)
    meaning = Column(String, nullable=False)
    level = Column(String, nullable=False, index=True)  # A1, A2, B1, B2, C1, C2
    example = Column(String)
    topic = Column(String, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Lesson(Base):
    __tablename__ = "lessons"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String)
    level = Column(String, nullable=False, index=True)  # A1, A2, B1, B2, C1, C2
    content_type = Column(String, nullable=False)  # vocabulary, grammar, listening, roleplay
    content_data = Column(JSON)
    is_active = Column(Boolean, default=True)
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class VocabularyGame(Base):
    __tablename__ = "vocabulary_games"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    level = Column(String, nullable=False)
    score = Column(Integer, default=0)
    xp_earned = Column(Integer, default=0)
    duration_seconds = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="vocabulary_games")
    attempts = relationship("VocabularyAttempt", back_populates="game", cascade="all, delete-orphan")

class VocabularyAttempt(Base):
    __tablename__ = "vocabulary_attempts"
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("vocabulary_games.id"))
    word = Column(String, nullable=False)
    user_answer = Column(String)
    is_correct = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    game = relationship("VocabularyGame", back_populates="attempts")

class VocabularyWrongAnswer(Base):
    __tablename__ = "vocabulary_wrong_answers"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    word = Column(String, nullable=False, index=True)
    error_count = Column(Integer, default=1)
    last_attempt_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class VocabularyMasteredWord(Base):
    __tablename__ = "vocabulary_mastered_words"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    word = Column(String, nullable=False, index=True)
    correct_streak = Column(Integer, default=1)
    mastered_at = Column(DateTime(timezone=True), server_default=func.now())

class VocabularyMemory(Base):
    __tablename__ = "vocabulary_memory"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    word = Column(String, nullable=False, index=True)
    ease_factor = Column(Float, default=2.5)  # SM-2 ease factor
    interval_days = Column(Integer, default=0)
    repetitions = Column(Integer, default=0)
    last_reviewed_at = Column(DateTime(timezone=True), server_default=func.now())
    next_review_at = Column(DateTime(timezone=True), server_default=func.now())

class VocabularyReviewSchedule(Base):
    __tablename__ = "vocabulary_review_schedules"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    word = Column(String, nullable=False, index=True)
    scheduled_for = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, default="pending")  # pending, completed
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class VocabularyTopic(Base):
    __tablename__ = "vocabulary_topics"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    code = Column(String, nullable=False, unique=True, index=True)
    icon = Column(String)
    description = Column(String)

class VocabularyTopicProgress(Base):
    __tablename__ = "vocabulary_topic_progress"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    topic_code = Column(String, nullable=False, index=True)
    level = Column(String, nullable=False)
    mastered_count = Column(Integer, default=0)
    total_count = Column(Integer, default=0)
    last_studied_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class VocabularyXP(Base):
    __tablename__ = "vocabulary_xp"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    xp = Column(Integer, default=0)
    level = Column(Integer, default=1)
    weekly_xp = Column(Integer, default=0)
    last_earned_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class VocabularyAchievement(Base):
    __tablename__ = "vocabulary_achievements"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    achievement_code = Column(String, nullable=False, index=True) # e.g. "first_perfect", "streak_10", "vocab_master"
    title = Column(String, nullable=False)
    description = Column(String)
    unlocked_at = Column(DateTime(timezone=True), server_default=func.now())

class DailyChallenge(Base):
    __tablename__ = "daily_challenges"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String)
    target_value = Column(Integer, default=1) # e.g. 3 games, 100 points
    xp_reward = Column(Integer, default=50)
    challenge_type = Column(String, nullable=False) # e.g. "play_games", "score_points", "perfect_game"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class VocabularyReport(Base):
    __tablename__ = "vocabulary_reports"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    game_id = Column(Integer, ForeignKey("vocabulary_games.id"))
    words_learned_count = Column(Integer, default=0)
    correct_answers_count = Column(Integer, default=0)
    accuracy = Column(Float, default=0.0)
    max_combo = Column(Integer, default=0)
    xp_earned = Column(Integer, default=0)
    ai_insights_json = Column(JSON) # e.g. {"words_to_review": [], "weak_points": [], "suggested_topics": []}
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DailyVocabularyProgress(Base):
    __tablename__ = "daily_vocabulary_progress"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime(timezone=True), server_default=func.now())
    words_studied = Column(Integer, default=0)
    minutes_spent = Column(Integer, default=0)
    xp_earned = Column(Integer, default=0)

class VocabularyLearningStatistics(Base):
    __tablename__ = "vocabulary_learning_statistics"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    total_words_studied = Column(Integer, default=0)
    total_games_played = Column(Integer, default=0)
    overall_accuracy = Column(Float, default=100.0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())