
import sqlite3
import os

db_path = 'e:/Project/Hoc/hoc-tieng-anh/backend/app/ai_coach.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM users")
    rows = cursor.fetchall()
    print(f"Users: {rows}")
    conn.close()
else:
    print("DB not found")
