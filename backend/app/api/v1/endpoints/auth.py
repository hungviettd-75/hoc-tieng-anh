from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app import schemas, models
from app.api import deps
from app.core import security
from app.core.config import settings

router = APIRouter()

@router.post("/register", response_model=schemas.user.User)
def register(
    *,
    db: Session = Depends(deps.get_db),
    user_in: schemas.user.UserCreate,
) -> Any:
    """
    Đăng ký người dùng mới.
    """
    user = db.query(models.models.User).filter(models.models.User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="Người dùng với email này đã tồn tại trong hệ thống.",
        )
    
    new_user = models.models.User(
        email=user_in.email,
        hashed_password=security.get_password_hash(user_in.password),
        full_name=user_in.full_name,
        level=user_in.level,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login", response_model=schemas.token.Token)
def login(
    db: Session = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """
    Đăng nhập lấy Access Token và Refresh Token.
    """
    user = db.query(models.models.User).filter(models.models.User.email == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Email hoặc mật khẩu không chính xác")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Tài khoản đã bị khóa")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(user.id, expires_delta=access_token_expires)
    refresh_token = security.create_refresh_token(user.id)
    
    # Lưu refresh token vào DB
    from datetime import datetime, timedelta as td
    db_refresh_token = models.models.RefreshToken(
        token=refresh_token,
        user_id=user.id,
        expires_at=datetime.utcnow() + td(days=30)
    )
    db.add(db_refresh_token)
    db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }

@router.post("/refresh", response_model=schemas.token.Token)
def refresh_token(
    *,
    db: Session = Depends(deps.get_db),
    refresh_token: str,
) -> Any:
    """
    Làm mới Access Token bằng Refresh Token (Token Rotation).
    """
    from jose import jwt
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[security.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Refresh token không hợp lệ")
    except Exception:
        raise HTTPException(status_code=401, detail="Refresh token không hợp lệ hoặc đã hết hạn")
    
    # Kiểm tra token trong DB
    db_token = db.query(models.models.RefreshToken).filter(
        models.models.RefreshToken.token == refresh_token,
        models.models.RefreshToken.is_revoked == False
    ).first()
    
    if not db_token:
        raise HTTPException(status_code=401, detail="Refresh token đã bị thu hồi hoặc không tồn tại")
    
    # Revoke old token
    db_token.is_revoked = True
    db.commit()
    
    # Create new tokens (Rotation)
    new_access_token = security.create_access_token(user_id)
    new_refresh_token = security.create_refresh_token(user_id)
    
    # Save new refresh token
    from datetime import datetime, timedelta as td
    new_db_token = models.models.RefreshToken(
        token=new_refresh_token,
        user_id=int(user_id),
        expires_at=datetime.utcnow() + td(days=30)
    )
    db.add(new_db_token)
    db.commit()
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }

@router.get("/me", response_model=schemas.user.User)
def read_user_me(
    current_user: models.models.User = Depends(deps.get_current_user),
) -> Any:
    """
    Lấy thông tin người dùng hiện tại.
    """
    return current_user
