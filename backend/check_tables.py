
import sqlite3
import os

db_path = 'e:/Project/Hoc/hoc-tieng-anh/backend/app/ai_coach.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    print(f"Tables: {cursor.fetchall()}")
    conn.close()
else:
    print("DB not found")
