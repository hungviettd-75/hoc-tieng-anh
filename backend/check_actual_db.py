import sys
import os

# Thêm thư mục hiện tại (backend) vào path để import được app
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.models import User

print("DATABASE URI:", settings.SQLALCHEMY_DATABASE_URI)

try:
    db = SessionLocal()
    users = db.query(User).all()
    print("Users in DB:")
    for user in users:
        print(f"- ID: {user.id}, Email: {user.email}, Is Admin: {user.is_admin}")
    if not users:
        print("No users found in database.")
    db.close()
except Exception as e:
    print("Error querying database:", e)
