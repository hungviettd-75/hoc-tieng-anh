import sqlite3
import json

conn = sqlite3.connect('e:/Project/Hoc/hoc-tieng-anh/backend/app/ai_coach.db')
c = conn.cursor()
c.execute("SELECT word, ipa, meaning FROM vocabularies ORDER BY word")
rows = c.fetchall()
conn.close()

# Xuất danh sách từ vựng ra file JSON để kiểm tra thủ công
data = [{"word": r[0], "ipa": r[1], "meaning": r[2]} for r in rows]
with open('e:/Project/Hoc/hoc-tieng-anh/backend/scratch/vocab_export.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Exported {len(data)} words to vocab_export.json")
