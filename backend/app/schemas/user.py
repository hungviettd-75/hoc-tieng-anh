from typing import Optional
from pydantic import BaseModel

class UserBase(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    level: Optional[str] = "A1"

class UserCreate(UserBase):
    email: str
    password: str

class UserUpdate(UserBase):
    password: Optional[str] = None

class User(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    is_admin: bool = False

    class Config:
        from_attributes = True
