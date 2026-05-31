import sqlite3
import re

conn = sqlite3.connect('e:/Project/Hoc/hoc-tieng-anh/backend/app/ai_coach.db')
c = conn.cursor()

# Kiểm tra hiện tại
c.execute("SELECT id, word, ipa, meaning, example FROM vocabularies WHERE word='pad' COLLATE NOCASE")
print("Before:", c.fetchall())

# Cập nhật thành nghĩa đúng: pad = miếng lót, tập giấy ghi chú
c.execute("""
    UPDATE vocabularies 
    SET ipa='/pæd/', meaning='Miếng lót, tập giấy ghi chú', example='She wrote a note on her notepad.'
    WHERE word='pad' COLLATE NOCASE
""")
print(f"Updated {c.rowcount} rows in DB.")
conn.commit()

c.execute("SELECT id, word, ipa, meaning, example FROM vocabularies WHERE word='pad' COLLATE NOCASE")
print("After:", c.fetchall())
conn.close()

# Cập nhật trong learn.py
FILE_PATH = 'e:/Project/Hoc/hoc-tieng-anh/backend/app/api/v1/endpoints/learn.py'
with open(FILE_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

pattern = r'("word":\s*"[Pp]ad",\s*"ipa":\s*")[^"]+(",\s*"meaning":\s*")[^"]+(",\s*"example":\s*")[^"]+(")'
replacement = r'\1/pæd/\2Miếng lót, tập giấy ghi chú\3She wrote a note on her notepad.\4'
new_content, count = re.subn(pattern, replacement, content)
print(f"Updated {count} occurrence(s) in learn.py.")

with open(FILE_PATH, 'w', encoding='utf-8') as f:
    f.write(new_content)
