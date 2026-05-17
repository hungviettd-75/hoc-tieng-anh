from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app import schemas, models
from app.api import deps
from app.services.analytics_service import AnalyticsService

router = APIRouter()


# ============================================================
# SEED ADMIN ACCOUNT
# ============================================================
@router.post("/seed", response_model=schemas.admin.SeedResponse)
def seed_admin(db: Session = Depends(deps.get_db)) -> Any:
    """Seed admin account và subscription plans (chỉ dùng cho dev)."""
    service = AnalyticsService(db)
    return service.seed_admin_and_plans(
        email="hunghvc@aicoach.com",
        password="hung123"
    )


# ============================================================
# OVERVIEW
# ============================================================
@router.get("/overview", response_model=schemas.admin.OverviewMetrics)
def get_overview(
    db: Session = Depends(deps.get_db),
    admin: models.models.User = Depends(deps.get_current_admin),
) -> Any:
    """Lấy metrics tổng quan cho admin dashboard."""
    service = AnalyticsService(db)
    return service.get_overview_metrics()


# ============================================================
# USER MANAGEMENT
# ============================================================
@router.get("/users", response_model=schemas.admin.AdminUserListResponse)
def get_users(
    db: Session = Depends(deps.get_db),
    admin: models.models.User = Depends(deps.get_current_admin),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
) -> Any:
    """Danh sách users với pagination, search, filter."""
    service = AnalyticsService(db)
    return service.get_users_list(
        page=page, page_size=page_size,
        search=search, status_filter=status
    )


@router.get("/users/{user_id}", response_model=schemas.admin.UserDetailResponse)
def get_user_detail(
    user_id: int,
    db: Session = Depends(deps.get_db),
    admin: models.models.User = Depends(deps.get_current_admin),
) -> Any:
    """Chi tiết user."""
    service = AnalyticsService(db)
    result = service.get_user_detail(user_id)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return result


@router.put("/users/{user_id}/status")
def update_user_status(
    user_id: int,
    status_update: schemas.admin.UserStatusUpdate,
    db: Session = Depends(deps.get_db),
    admin: models.models.User = Depends(deps.get_current_admin),
) -> Any:
    """Toggle user active/banned."""
    user = db.query(models.models.User).filter(models.models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = status_update.is_active
    db.commit()
    return {"message": f"User {'activated' if status_update.is_active else 'banned'}", "user_id": user_id}


# ============================================================
# ANALYTICS ENDPOINTS
# ============================================================
@router.get("/analytics/users", response_model=schemas.admin.UserGrowthResponse)
def get_user_analytics(
    db: Session = Depends(deps.get_db),
    admin: models.models.User = Depends(deps.get_current_admin),
    days: int = Query(30, ge=7, le=90),
) -> Any:
    """User growth analytics."""
    service = AnalyticsService(db)
    return service.get_user_growth(days=days)


@router.get("/analytics/activity", response_model=schemas.admin.ActivityTrendResponse)
def get_activity_analytics(
    db: Session = Depends(deps.get_db),
    admin: models.models.User = Depends(deps.get_current_admin),
    days: int = Query(30, ge=7, le=90),
) -> Any:
    """Activity trend analytics."""
    service = AnalyticsService(db)
    return service.get_activity_trends(days=days)


@router.get("/analytics/speaking", response_model=schemas.admin.SpeakingStatsResponse)
def get_speaking_analytics(
    db: Session = Depends(deps.get_db),
    admin: models.models.User = Depends(deps.get_current_admin),
    days: int = Query(30, ge=7, le=90),
) -> Any:
    """Speaking/pronunciation statistics."""
    service = AnalyticsService(db)
    return service.get_speaking_statistics(days=days)


@router.get("/analytics/ai-usage", response_model=schemas.admin.AIUsageResponse)
def get_ai_usage_analytics(
    db: Session = Depends(deps.get_db),
    admin: models.models.User = Depends(deps.get_current_admin),
    days: int = Query(30, ge=7, le=90),
) -> Any:
    """AI usage analytics (conversations, messages, memories)."""
    service = AnalyticsService(db)
    return service.get_ai_usage(days=days)


@router.get("/analytics/retention", response_model=schemas.admin.RetentionResponse)
def get_retention_analytics(
    db: Session = Depends(deps.get_db),
    admin: models.models.User = Depends(deps.get_current_admin),
    days: int = Query(30, ge=7, le=90),
) -> Any:
    """Retention metrics (DAU/WAU/MAU, churn)."""
    service = AnalyticsService(db)
    return service.get_retention_metrics(days=days)


@router.get("/analytics/subscriptions", response_model=schemas.admin.SubscriptionStatsResponse)
def get_subscription_analytics(
    db: Session = Depends(deps.get_db),
    admin: models.models.User = Depends(deps.get_current_admin),
    days: int = Query(30, ge=7, le=90),
) -> Any:
    """Subscription analytics."""
    service = AnalyticsService(db)
    return service.get_subscription_analytics(days=days)
