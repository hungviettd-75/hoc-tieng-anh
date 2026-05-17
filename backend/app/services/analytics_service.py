from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, and_, cast, Date
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from app.models.models import (
    User, Conversation, Message, Streak, UserXP, DailyGoal,
    ActivityLog, PronunciationSession, PronunciationScore,
    UserSkillLevel, WeakPoint, AIMemory, UserAchievement,
    UserSubscription, SubscriptionPlan, AnalyticsSnapshot
)


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    # ============================================================
    # OVERVIEW METRICS
    # ============================================================
    def get_overview_metrics(self) -> Dict[str, Any]:
        total_users = self.db.query(func.count(User.id)).scalar() or 0

        # Active users today (có activity_log hôm nay)
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())
        active_today = self.db.query(func.count(distinct(ActivityLog.user_id))).filter(
            ActivityLog.timestamp >= today_start
        ).scalar() or 0

        total_conversations = self.db.query(func.count(Conversation.id)).scalar() or 0
        total_messages = self.db.query(func.count(Message.id)).scalar() or 0
        total_speaking = self.db.query(func.count(PronunciationSession.id)).scalar() or 0

        avg_score = self.db.query(func.avg(PronunciationSession.overall_score)).scalar() or 0.0

        total_xp = self.db.query(func.sum(UserXP.total_xp)).scalar() or 0

        active_subs = self.db.query(func.count(UserSubscription.id)).filter(
            UserSubscription.status == "active"
        ).scalar() or 0

        return {
            "total_users": total_users,
            "active_users_today": active_today,
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "total_speaking_sessions": total_speaking,
            "avg_pronunciation_score": round(float(avg_score), 1),
            "total_xp_earned": total_xp,
            "active_subscriptions": active_subs,
        }

    # ============================================================
    # USER MANAGEMENT
    # ============================================================
    def get_users_list(self, page: int = 1, page_size: int = 20,
                       search: Optional[str] = None, status_filter: Optional[str] = None):
        query = self.db.query(User)

        if search:
            query = query.filter(
                (User.email.ilike(f"%{search}%")) |
                (User.full_name.ilike(f"%{search}%"))
            )

        if status_filter == "active":
            query = query.filter(User.is_active == True)
        elif status_filter == "banned":
            query = query.filter(User.is_active == False)

        total = query.count()
        users = query.order_by(User.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size).all()

        result = []
        for user in users:
            xp = self.db.query(UserXP).filter(UserXP.user_id == user.id).first()
            streak = self.db.query(Streak).filter(Streak.user_id == user.id).first()
            conv_count = self.db.query(func.count(Conversation.id)).filter(
                Conversation.user_id == user.id
            ).scalar() or 0
            speak_count = self.db.query(func.count(PronunciationSession.id)).filter(
                PronunciationSession.user_id == user.id
            ).scalar() or 0
            sub = self.db.query(UserSubscription).filter(
                UserSubscription.user_id == user.id,
                UserSubscription.status == "active"
            ).first()
            plan_name = "free"
            if sub:
                plan = self.db.query(SubscriptionPlan).filter(SubscriptionPlan.id == sub.plan_id).first()
                plan_name = plan.name if plan else "free"

            result.append({
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "level": user.level,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "is_admin": user.is_admin,
                "created_at": user.created_at,
                "total_xp": xp.total_xp if xp else 0,
                "current_streak": streak.current_streak if streak else 0,
                "total_conversations": conv_count,
                "total_speaking_sessions": speak_count,
                "subscription_plan": plan_name,
            })

        return {"users": result, "total": total, "page": page, "page_size": page_size}

    def get_user_detail(self, user_id: int) -> Optional[Dict[str, Any]]:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None

        xp = self.db.query(UserXP).filter(UserXP.user_id == user.id).first()
        streak = self.db.query(Streak).filter(Streak.user_id == user.id).first()
        conv_count = self.db.query(func.count(Conversation.id)).filter(
            Conversation.user_id == user.id
        ).scalar() or 0
        msg_count = self.db.query(func.count(Message.id)).join(Conversation).filter(
            Conversation.user_id == user.id
        ).scalar() or 0
        speak_count = self.db.query(func.count(PronunciationSession.id)).filter(
            PronunciationSession.user_id == user.id
        ).scalar() or 0
        avg_score = self.db.query(func.avg(PronunciationSession.overall_score)).filter(
            PronunciationSession.user_id == user.id
        ).scalar() or 0.0
        activity_count = self.db.query(func.count(ActivityLog.id)).filter(
            ActivityLog.user_id == user.id
        ).scalar() or 0
        skill = self.db.query(UserSkillLevel).filter(UserSkillLevel.user_id == user.id).first()
        weak_count = self.db.query(func.count(WeakPoint.id)).filter(
            WeakPoint.user_id == user.id, WeakPoint.is_resolved == False
        ).scalar() or 0
        achieve_count = self.db.query(func.count(UserAchievement.id)).filter(
            UserAchievement.user_id == user.id
        ).scalar() or 0
        last_act = self.db.query(func.max(ActivityLog.timestamp)).filter(
            ActivityLog.user_id == user.id
        ).scalar()

        sub = self.db.query(UserSubscription).filter(
            UserSubscription.user_id == user.id,
            UserSubscription.status == "active"
        ).first()
        plan_name = "free"
        if sub:
            plan = self.db.query(SubscriptionPlan).filter(SubscriptionPlan.id == sub.plan_id).first()
            plan_name = plan.name if plan else "free"

        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "level": user.level,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "is_admin": user.is_admin,
            "created_at": user.created_at,
            "total_xp": xp.total_xp if xp else 0,
            "current_streak": streak.current_streak if streak else 0,
            "total_conversations": conv_count,
            "total_speaking_sessions": speak_count,
            "subscription_plan": plan_name,
            "avg_pronunciation_score": round(float(avg_score), 1),
            "total_messages": msg_count,
            "total_activities": activity_count,
            "skill_levels": {
                "vocabulary": skill.vocabulary if skill else 0,
                "grammar": skill.grammar if skill else 0,
                "pronunciation": skill.pronunciation if skill else 0,
                "listening": skill.listening if skill else 0,
                "fluency": skill.fluency if skill else 0,
            } if skill else None,
            "weak_points_count": weak_count,
            "achievements_count": achieve_count,
            "last_activity": last_act,
        }

    # ============================================================
    # USER GROWTH ANALYTICS
    # ============================================================
    def get_user_growth(self, days: int = 30) -> Dict[str, Any]:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # Daily signups
        daily_signups = []
        cumulative_users = []
        cumulative = 0

        for i in range(days):
            day = start_date + timedelta(days=i)
            day_start = datetime.combine(day.date(), datetime.min.time())
            day_end = day_start + timedelta(days=1)

            count = self.db.query(func.count(User.id)).filter(
                and_(User.created_at >= day_start, User.created_at < day_end)
            ).scalar() or 0

            cumulative += count
            daily_signups.append({"date": day.strftime("%Y-%m-%d"), "value": count})
            cumulative_users.append({"date": day.strftime("%Y-%m-%d"), "value": cumulative})

        total_users = self.db.query(func.count(User.id)).scalar() or 0

        # Growth rate (compare last 7 days vs previous 7 days)
        recent_7 = self.db.query(func.count(User.id)).filter(
            User.created_at >= end_date - timedelta(days=7)
        ).scalar() or 0
        prev_7 = self.db.query(func.count(User.id)).filter(
            and_(
                User.created_at >= end_date - timedelta(days=14),
                User.created_at < end_date - timedelta(days=7)
            )
        ).scalar() or 0
        growth_rate = ((recent_7 - prev_7) / max(prev_7, 1)) * 100

        return {
            "daily_signups": daily_signups,
            "cumulative_users": cumulative_users,
            "total_users": total_users,
            "growth_rate": round(growth_rate, 1),
        }

    # ============================================================
    # ACTIVITY TRENDS
    # ============================================================
    def get_activity_trends(self, days: int = 30) -> Dict[str, Any]:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        daily_activities = []
        for i in range(days):
            day = start_date + timedelta(days=i)
            day_start = datetime.combine(day.date(), datetime.min.time())
            day_end = day_start + timedelta(days=1)

            count = self.db.query(func.count(ActivityLog.id)).filter(
                and_(ActivityLog.timestamp >= day_start, ActivityLog.timestamp < day_end)
            ).scalar() or 0
            daily_activities.append({"date": day.strftime("%Y-%m-%d"), "value": count})

        # Activity by type
        type_counts = self.db.query(
            ActivityLog.activity_type,
            func.count(ActivityLog.id)
        ).filter(
            ActivityLog.timestamp >= start_date
        ).group_by(ActivityLog.activity_type).all()

        activity_by_type = {t: c for t, c in type_counts} if type_counts else {}

        total_acts = sum(d["value"] for d in daily_activities)
        avg_daily = total_acts / max(days, 1)

        # Peak hour (simplified - just return most common hour)
        peak_hour = 14  # Default

        return {
            "daily_activities": daily_activities,
            "activity_by_type": activity_by_type,
            "avg_daily_activities": round(avg_daily, 1),
            "peak_hour": peak_hour,
        }

    # ============================================================
    # SPEAKING STATISTICS
    # ============================================================
    def get_speaking_statistics(self, days: int = 30) -> Dict[str, Any]:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        total_sessions = self.db.query(func.count(PronunciationSession.id)).scalar() or 0
        avg_overall = self.db.query(func.avg(PronunciationSession.overall_score)).scalar() or 0.0

        # Average by metric
        metrics = {}
        for metric_name in ["fluency", "pronunciation", "confidence", "intonation"]:
            avg_val = self.db.query(func.avg(PronunciationScore.score)).filter(
                PronunciationScore.metric == metric_name
            ).scalar() or 0.0
            metrics[metric_name] = round(float(avg_val), 1)

        # Score distribution
        distribution = {"0-20": 0, "20-40": 0, "40-60": 0, "60-80": 0, "80-100": 0}
        sessions = self.db.query(PronunciationSession.overall_score).all()
        for (score,) in sessions:
            if score is None:
                continue
            if score < 20:
                distribution["0-20"] += 1
            elif score < 40:
                distribution["20-40"] += 1
            elif score < 60:
                distribution["40-60"] += 1
            elif score < 80:
                distribution["60-80"] += 1
            else:
                distribution["80-100"] += 1

        # Daily sessions
        daily_sessions = []
        for i in range(days):
            day = start_date + timedelta(days=i)
            day_start = datetime.combine(day.date(), datetime.min.time())
            day_end = day_start + timedelta(days=1)
            count = self.db.query(func.count(PronunciationSession.id)).filter(
                and_(PronunciationSession.created_at >= day_start,
                     PronunciationSession.created_at < day_end)
            ).scalar() or 0
            daily_sessions.append({"date": day.strftime("%Y-%m-%d"), "value": count})

        # Top performers
        top = self.db.query(
            User.id, User.full_name, User.email,
            func.avg(PronunciationSession.overall_score).label("avg_score"),
            func.count(PronunciationSession.id).label("session_count")
        ).join(PronunciationSession, PronunciationSession.user_id == User.id
        ).group_by(User.id, User.full_name, User.email
        ).order_by(func.avg(PronunciationSession.overall_score).desc()
        ).limit(5).all()

        top_performers = [
            {"user_id": t[0], "name": t[1] or t[2], "avg_score": round(float(t[3]), 1),
             "sessions": t[4]}
            for t in top
        ]

        return {
            "total_sessions": total_sessions,
            "avg_overall_score": round(float(avg_overall), 1),
            "avg_fluency": metrics.get("fluency", 0),
            "avg_pronunciation": metrics.get("pronunciation", 0),
            "avg_confidence": metrics.get("confidence", 0),
            "avg_intonation": metrics.get("intonation", 0),
            "score_distribution": distribution,
            "daily_sessions": daily_sessions,
            "top_performers": top_performers,
        }

    # ============================================================
    # AI USAGE ANALYTICS
    # ============================================================
    def get_ai_usage(self, days: int = 30) -> Dict[str, Any]:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        total_conversations = self.db.query(func.count(Conversation.id)).scalar() or 0
        total_messages = self.db.query(func.count(Message.id)).scalar() or 0
        avg_msgs = total_messages / max(total_conversations, 1)
        total_memories = self.db.query(func.count(AIMemory.id)).scalar() or 0

        # Daily conversations
        daily_conversations = []
        daily_messages = []
        for i in range(days):
            day = start_date + timedelta(days=i)
            day_start = datetime.combine(day.date(), datetime.min.time())
            day_end = day_start + timedelta(days=1)

            conv_count = self.db.query(func.count(Conversation.id)).filter(
                and_(Conversation.created_at >= day_start, Conversation.created_at < day_end)
            ).scalar() or 0
            msg_count = self.db.query(func.count(Message.id)).filter(
                and_(Message.created_at >= day_start, Message.created_at < day_end)
            ).scalar() or 0

            daily_conversations.append({"date": day.strftime("%Y-%m-%d"), "value": conv_count})
            daily_messages.append({"date": day.strftime("%Y-%m-%d"), "value": msg_count})

        # Popular topics (from conversation titles)
        topics = self.db.query(
            Conversation.title, func.count(Conversation.id)
        ).filter(
            Conversation.title.isnot(None)
        ).group_by(Conversation.title
        ).order_by(func.count(Conversation.id).desc()
        ).limit(10).all()

        popular_topics = [{"topic": t[0], "count": t[1]} for t in topics]

        return {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "avg_messages_per_conversation": round(avg_msgs, 1),
            "total_ai_memories": total_memories,
            "daily_conversations": daily_conversations,
            "daily_messages": daily_messages,
            "popular_topics": popular_topics,
        }

    # ============================================================
    # RETENTION METRICS
    # ============================================================
    def get_retention_metrics(self, days: int = 30) -> Dict[str, Any]:
        now = datetime.utcnow()
        today = now.date()

        # DAU - users with activity today
        today_start = datetime.combine(today, datetime.min.time())
        dau = self.db.query(func.count(distinct(ActivityLog.user_id))).filter(
            ActivityLog.timestamp >= today_start
        ).scalar() or 0

        # WAU - users with activity in last 7 days
        week_start = now - timedelta(days=7)
        wau = self.db.query(func.count(distinct(ActivityLog.user_id))).filter(
            ActivityLog.timestamp >= week_start
        ).scalar() or 0

        # MAU - users with activity in last 30 days
        month_start = now - timedelta(days=30)
        mau = self.db.query(func.count(distinct(ActivityLog.user_id))).filter(
            ActivityLog.timestamp >= month_start
        ).scalar() or 0

        dau_mau_ratio = (dau / max(mau, 1)) * 100

        # Daily retention trend
        daily_retention = []
        for i in range(days):
            day = (now - timedelta(days=days - i - 1)).date()
            day_start = datetime.combine(day, datetime.min.time())
            day_end = day_start + timedelta(days=1)
            active = self.db.query(func.count(distinct(ActivityLog.user_id))).filter(
                and_(ActivityLog.timestamp >= day_start, ActivityLog.timestamp < day_end)
            ).scalar() or 0
            daily_retention.append({"date": day.strftime("%Y-%m-%d"), "value": active})

        # Churn rate (users who were active last month but not this month)
        prev_month_start = now - timedelta(days=60)
        prev_month_end = now - timedelta(days=30)
        prev_active = self.db.query(func.count(distinct(ActivityLog.user_id))).filter(
            and_(ActivityLog.timestamp >= prev_month_start, ActivityLog.timestamp < prev_month_end)
        ).scalar() or 0
        churned = max(prev_active - mau, 0)
        churn_rate = (churned / max(prev_active, 1)) * 100

        # Avg session duration
        avg_duration = self.db.query(func.avg(ActivityLog.duration_minutes)).filter(
            ActivityLog.duration_minutes > 0
        ).scalar() or 0.0

        # Returning users rate
        total_users = self.db.query(func.count(User.id)).scalar() or 1
        returning_rate = (mau / total_users) * 100

        return {
            "dau": dau,
            "wau": wau,
            "mau": mau,
            "dau_mau_ratio": round(dau_mau_ratio, 1),
            "daily_retention": daily_retention,
            "churn_rate": round(churn_rate, 1),
            "avg_session_duration_minutes": round(float(avg_duration), 1),
            "returning_users_rate": round(returning_rate, 1),
        }

    # ============================================================
    # SUBSCRIPTION ANALYTICS
    # ============================================================
    def get_subscription_analytics(self, days: int = 30) -> Dict[str, Any]:
        total_subs = self.db.query(func.count(UserSubscription.id)).scalar() or 0
        active_subs = self.db.query(func.count(UserSubscription.id)).filter(
            UserSubscription.status == "active"
        ).scalar() or 0
        cancelled_subs = self.db.query(func.count(UserSubscription.id)).filter(
            UserSubscription.status == "cancelled"
        ).scalar() or 0
        expired_subs = self.db.query(func.count(UserSubscription.id)).filter(
            UserSubscription.status == "expired"
        ).scalar() or 0

        # Revenue calculation
        revenue_monthly = 0.0
        revenue_yearly = 0.0
        active_plans = self.db.query(
            SubscriptionPlan.price_monthly,
            SubscriptionPlan.price_yearly,
            func.count(UserSubscription.id)
        ).join(UserSubscription, UserSubscription.plan_id == SubscriptionPlan.id
        ).filter(UserSubscription.status == "active"
        ).group_by(SubscriptionPlan.price_monthly, SubscriptionPlan.price_yearly).all()

        for monthly, yearly, count in active_plans:
            revenue_monthly += (monthly or 0) * count
            revenue_yearly += (yearly or 0) * count

        # Plan distribution
        plan_dist = self.db.query(
            SubscriptionPlan.name,
            func.count(UserSubscription.id)
        ).join(UserSubscription, UserSubscription.plan_id == SubscriptionPlan.id
        ).group_by(SubscriptionPlan.name).all()

        plan_distribution = {name: count for name, count in plan_dist}

        # Count free users (no subscription)
        users_with_sub = self.db.query(func.count(distinct(UserSubscription.user_id))).scalar() or 0
        total_users = self.db.query(func.count(User.id)).scalar() or 0
        free_users = total_users - users_with_sub
        plan_distribution["free"] = plan_distribution.get("free", 0) + free_users

        # Daily new subscriptions
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        daily_new = []
        for i in range(days):
            day = start_date + timedelta(days=i)
            day_start = datetime.combine(day.date(), datetime.min.time())
            day_end = day_start + timedelta(days=1)
            count = self.db.query(func.count(UserSubscription.id)).filter(
                and_(UserSubscription.started_at >= day_start,
                     UserSubscription.started_at < day_end)
            ).scalar() or 0
            daily_new.append({"date": day.strftime("%Y-%m-%d"), "value": count})

        churn_rate = (cancelled_subs / max(total_subs, 1)) * 100
        mrr = revenue_monthly

        return {
            "total_subscriptions": total_subs,
            "active_subscriptions": active_subs,
            "cancelled_subscriptions": cancelled_subs,
            "expired_subscriptions": expired_subs,
            "revenue_monthly": round(revenue_monthly, 2),
            "revenue_yearly": round(revenue_yearly, 2),
            "plan_distribution": plan_distribution,
            "daily_new_subscriptions": daily_new,
            "churn_rate": round(churn_rate, 1),
            "mrr": round(mrr, 2),
        }

    # ============================================================
    # SEED ADMIN & SUBSCRIPTION PLANS
    # ============================================================
    def seed_admin_and_plans(self, email: str, password: str) -> Dict[str, str]:
        from app.core.security import get_password_hash

        # Check if admin already exists
        existing = self.db.query(User).filter(User.email == email).first()
        if existing:
            existing.is_admin = True
            self.db.commit()
            return {"message": "Admin privileges granted to existing user", "admin_email": email}

        # Create admin user
        admin_user = User(
            email=email,
            hashed_password=get_password_hash(password),
            full_name="Admin",
            level="C2",
            is_active=True,
            is_verified=True,
            is_admin=True,
        )
        self.db.add(admin_user)

        # Seed subscription plans if not exist
        existing_plans = self.db.query(func.count(SubscriptionPlan.id)).scalar() or 0
        if existing_plans == 0:
            plans = [
                SubscriptionPlan(
                    name="basic",
                    price_monthly=4.99,
                    price_yearly=49.99,
                    max_conversations_per_day=15,
                    max_speaking_sessions_per_day=10,
                    has_ai_memory=False,
                    has_advanced_analytics=False,
                ),
                SubscriptionPlan(
                    name="premium",
                    price_monthly=9.99,
                    price_yearly=99.99,
                    max_conversations_per_day=50,
                    max_speaking_sessions_per_day=30,
                    has_ai_memory=True,
                    has_advanced_analytics=True,
                ),
                SubscriptionPlan(
                    name="enterprise",
                    price_monthly=24.99,
                    price_yearly=249.99,
                    max_conversations_per_day=999,
                    max_speaking_sessions_per_day=999,
                    has_ai_memory=True,
                    has_advanced_analytics=True,
                ),
            ]
            for plan in plans:
                self.db.add(plan)

        self.db.commit()
        return {"message": "Admin account and subscription plans created", "admin_email": email}
