from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


# --- Overview Metrics ---
class OverviewMetrics(BaseModel):
    total_users: int
    active_users_today: int
    total_conversations: int
    total_messages: int
    total_speaking_sessions: int
    avg_pronunciation_score: float
    total_xp_earned: int
    active_subscriptions: int


# --- User Management ---
class AdminUserItem(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    level: Optional[str] = "A1"
    is_active: bool
    is_verified: bool
    is_admin: bool
    created_at: Optional[datetime] = None
    total_xp: int = 0
    current_streak: int = 0
    total_conversations: int = 0
    total_speaking_sessions: int = 0
    subscription_plan: Optional[str] = "free"

    class Config:
        from_attributes = True


class AdminUserListResponse(BaseModel):
    users: List[AdminUserItem]
    total: int
    page: int
    page_size: int


class UserDetailResponse(AdminUserItem):
    avg_pronunciation_score: float = 0.0
    total_messages: int = 0
    total_activities: int = 0
    skill_levels: Optional[Dict[str, float]] = None
    weak_points_count: int = 0
    achievements_count: int = 0
    last_activity: Optional[datetime] = None


class UserStatusUpdate(BaseModel):
    is_active: bool


# --- Analytics Charts ---
class TimeSeriesPoint(BaseModel):
    date: str
    value: float


class UserGrowthResponse(BaseModel):
    daily_signups: List[TimeSeriesPoint]
    cumulative_users: List[TimeSeriesPoint]
    total_users: int
    growth_rate: float  # percentage


class ActivityTrendResponse(BaseModel):
    daily_activities: List[TimeSeriesPoint]
    activity_by_type: Dict[str, int]
    avg_daily_activities: float
    peak_hour: int


class SpeakingStatsResponse(BaseModel):
    total_sessions: int
    avg_overall_score: float
    avg_fluency: float
    avg_pronunciation: float
    avg_confidence: float
    avg_intonation: float
    score_distribution: Dict[str, int]  # e.g., {"0-20": 5, "20-40": 10, ...}
    daily_sessions: List[TimeSeriesPoint]
    top_performers: List[Dict[str, Any]]


class AIUsageResponse(BaseModel):
    total_conversations: int
    total_messages: int
    avg_messages_per_conversation: float
    total_ai_memories: int
    daily_conversations: List[TimeSeriesPoint]
    daily_messages: List[TimeSeriesPoint]
    popular_topics: List[Dict[str, Any]]


class RetentionResponse(BaseModel):
    dau: int  # Daily Active Users
    wau: int  # Weekly Active Users
    mau: int  # Monthly Active Users
    dau_mau_ratio: float
    daily_retention: List[TimeSeriesPoint]
    churn_rate: float
    avg_session_duration_minutes: float
    returning_users_rate: float


class SubscriptionStatsResponse(BaseModel):
    total_subscriptions: int
    active_subscriptions: int
    cancelled_subscriptions: int
    expired_subscriptions: int
    revenue_monthly: float
    revenue_yearly: float
    plan_distribution: Dict[str, int]  # e.g., {"free": 100, "basic": 30, ...}
    daily_new_subscriptions: List[TimeSeriesPoint]
    churn_rate: float
    mrr: float  # Monthly Recurring Revenue


# --- Subscription Plan ---
class SubscriptionPlanSchema(BaseModel):
    id: int
    name: str
    price_monthly: float
    price_yearly: float
    max_conversations_per_day: int
    max_speaking_sessions_per_day: int
    has_ai_memory: bool
    has_advanced_analytics: bool

    class Config:
        from_attributes = True


# --- Admin Seed ---
class SeedResponse(BaseModel):
    message: str
    admin_email: str
