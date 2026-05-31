import sqlite3

conn = sqlite3.connect('e:/Project/Hoc/hoc-tieng-anh/backend/app/ai_coach.db')
c = conn.cursor()

# Xóa các bản ghi trùng lặp tuyệt đối về word, giữ lại bản ghi có ID nhỏ nhất
c.execute("""
    DELETE FROM vocabularies 
    WHERE id NOT IN (
        SELECT MIN(id) 
        FROM vocabularies 
        GROUP BY LOWER(word)
    )
""")
print(f"Removed {c.rowcount} exact duplicate rows from database.")

conn.commit()
conn.close()
