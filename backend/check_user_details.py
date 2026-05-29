import sqlite3
db_path = 'e:/Project/Hoc/hoc-tieng-anh/backend/app/ai_coach.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(users)")
print("Columns:", cursor.fetchall())
cursor.execute("SELECT id, email, hashed_password, is_admin, is_active FROM users")
for row in cursor.fetchall():
    print(f"ID: {row[0]}, Email: {row[1]}, Hash: {row[2]}, Is Admin: {row[3]}, Is Active: {row[4]}")
conn.close()
