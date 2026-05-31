import sqlite3
import re

# 1. Cập nhật trong database
conn = sqlite3.connect('e:/Project/Hoc/hoc-tieng-anh/backend/app/ai_coach.db')
c = conn.cursor()

c.execute("SELECT id, word, ipa, meaning, example FROM vocabularies WHERE word='Coach' COLLATE NOCASE")
rows = c.fetchall()
print("Before:", rows)

c.execute("""
    UPDATE vocabularies 
    SET meaning='Huấn luyện viên', ipa='/kəʊtʃ/', example='She hired a personal coach to improve her tennis skills.'
    WHERE word='Coach' COLLATE NOCASE
""")
print(f"Updated {c.rowcount} rows in DB.")

conn.commit()
conn.close()

# 2. Cập nhật trong learn.py
FILE_PATH = 'e:/Project/Hoc/hoc-tieng-anh/backend/app/api/v1/endpoints/learn.py'
with open(FILE_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# Tìm và thay thế meaning + example của Coach
pattern = r'("word":\s*"Coach",\s*"ipa":\s*")[^"]+(",\s*"meaning":\s*")[^"]+(",\s*"example":\s*")[^"]+(")'
replacement = r'\1/kəʊtʃ/\2Huấn luyện viên\3She hired a personal coach to improve her tennis skills.\4'

new_content, count = re.subn(pattern, replacement, content, flags=re.IGNORECASE)
print(f"Updated {count} occurrence(s) in learn.py.")

with open(FILE_PATH, 'w', encoding='utf-8') as f:
    f.write(new_content)
