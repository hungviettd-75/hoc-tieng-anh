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


# ============================================================
# VOCABULARY MANAGEMENT
# ============================================================
@router.get("/vocabulary", response_model=schemas.admin.AdminVocabularyListResponse)
def get_vocabulary(
    db: Session = Depends(deps.get_db),
    admin: models.models.User = Depends(deps.get_current_admin),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
) -> Any:
    """Danh sách từ vựng với pagination, search, filter theo level."""
    query = db.query(models.models.Vocabulary)
    if search:
        query = query.filter(
            (models.models.Vocabulary.word.ilike(f"%{search}%")) |
            (models.models.Vocabulary.meaning.ilike(f"%{search}%"))
        )
    if level:
        query = query.filter(models.models.Vocabulary.level == level)
    
    total = query.count()
    items = query.order_by(models.models.Vocabulary.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.post("/vocabulary", response_model=schemas.admin.VocabularyResponse)
def create_vocabulary(
    vocab_in: schemas.admin.VocabularyCreate,
    db: Session = Depends(deps.get_db),
    admin: models.models.User = Depends(deps.get_current_admin),
) -> Any:
    """Thêm từ vựng mới."""
    vocab = models.models.Vocabulary(**vocab_in.dict())
    db.add(vocab)
    db.commit()
    db.refresh(vocab)
    return vocab


@router.put("/vocabulary/{vocab_id}", response_model=schemas.admin.VocabularyResponse)
def update_vocabulary(
    vocab_id: int,
    vocab_in: schemas.admin.VocabularyUpdate,
    db: Session = Depends(deps.get_db),
    admin: models.models.User = Depends(deps.get_current_admin),
) -> Any:
    """Sửa từ vựng."""
    vocab = db.query(models.models.Vocabulary).filter(models.models.Vocabulary.id == vocab_id).first()
    if not vocab:
        raise HTTPException(status_code=404, detail="Vocabulary not found")
    
    update_data = vocab_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(vocab, field, value)
        
    db.commit()
    db.refresh(vocab)
    return vocab


@router.delete("/vocabulary/{vocab_id}")
def delete_vocabulary(
    vocab_id: int,
    db: Session = Depends(deps.get_db),
    admin: models.models.User = Depends(deps.get_current_admin),
) -> Any:
    """Xóa từ vựng."""
    vocab = db.query(models.models.Vocabulary).filter(models.models.Vocabulary.id == vocab_id).first()
    if not vocab:
        raise HTTPException(status_code=404, detail="Vocabulary not found")
    
    db.delete(vocab)
    db.commit()
    return {"message": "Vocabulary deleted successfully", "id": vocab_id}


@router.post("/vocabulary/seed")
def seed_vocabulary_data(
    db: Session = Depends(deps.get_db),
    admin: models.models.User = Depends(deps.get_current_admin),
) -> Any:
    """Seed data từ hardcode trong learn.py vào DB nếu DB trống."""
    # Import base_vocab từ learn.py
    from app.api.v1.endpoints.learn import base_vocab
    
    # Kiểm tra xem đã có từ vựng nào chưa
    existing_count = db.query(models.models.Vocabulary).count()
    if existing_count > 0:
        return {"message": f"Database already has {existing_count} vocabularies. Skipping seed."}
        
    count = 0
    for level, words in base_vocab.items():
        for item in words:
            vocab = models.models.Vocabulary(
                word=item["word"],
                ipa=item["ipa"],
                meaning=item["meaning"],
                level=level,
                example=item.get("example"),
                topic="General",
                is_active=True
            )
            db.add(vocab)
            count += 1
            
    db.commit()
    return {"message": f"Successfully seeded {count} vocabularies into database."}


# ============================================================
# LESSON MANAGEMENT
# ============================================================
@router.get("/lessons", response_model=schemas.admin.AdminLessonListResponse)
def get_lessons(
    db: Session = Depends(deps.get_db),
    admin: models.models.User = Depends(deps.get_current_admin),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    content_type: Optional[str] = Query(None),
) -> Any:
    """Danh sách bài học với pagination, search, filter."""
    query = db.query(models.models.Lesson)
    if search:
        query = query.filter(
            (models.models.Lesson.title.ilike(f"%{search}%")) |
            (models.models.Lesson.description.ilike(f"%{search}%"))
        )
    if level:
        query = query.filter(models.models.Lesson.level == level)
    if content_type:
        query = query.filter(models.models.Lesson.content_type == content_type)
        
    total = query.count()
    items = query.order_by(models.models.Lesson.order_index.asc(), models.models.Lesson.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.post("/lessons", response_model=schemas.admin.LessonResponse)
def create_lesson(
    lesson_in: schemas.admin.LessonCreate,
    db: Session = Depends(deps.get_db),
    admin: models.models.User = Depends(deps.get_current_admin),
) -> Any:
    """Thêm bài học mới."""
    lesson = models.models.Lesson(**lesson_in.dict())
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


@router.put("/lessons/{lesson_id}", response_model=schemas.admin.LessonResponse)
def update_lesson(
    lesson_id: int,
    lesson_in: schemas.admin.LessonUpdate,
    db: Session = Depends(deps.get_db),
    admin: models.models.User = Depends(deps.get_current_admin),
) -> Any:
    """Sửa bài học."""
    lesson = db.query(models.models.Lesson).filter(models.models.Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
        
    update_data = lesson_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lesson, field, value)
        
    db.commit()
    db.refresh(lesson)
    return lesson


@router.delete("/lessons/{lesson_id}")
def delete_lesson(
    lesson_id: int,
    db: Session = Depends(deps.get_db),
    admin: models.models.User = Depends(deps.get_current_admin),
) -> Any:
    """Xóa bài học."""
    lesson = db.query(models.models.Lesson).filter(models.models.Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
        
    db.delete(lesson)
    db.commit()
    return {"message": "Lesson deleted successfully", "id": lesson_id}
