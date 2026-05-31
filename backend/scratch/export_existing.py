import sqlite3
import json

conn = sqlite3.connect('backend/app/ai_coach.db')
c = conn.cursor()
c.execute("SELECT word, topic, level FROM vocabularies")
rows = c.fetchall()

# Xuất danh sách từ đã có theo topic
by_topic = {}
for word, topic, level in rows:
    key = f"{topic}_{level}"
    by_topic.setdefault(key, []).append(word.lower())

# Tất cả từ đã có (global)
all_words = set(r[0].lower() for r in rows)

print("=== WORDS PER TOPIC/LEVEL ===")
topics = ('ai','tech','marketing','job','business')
for t in topics:
    for lv in ['A1','A2','B1','B2','C1']:
        key = f"{t}_{lv}"
        words = by_topic.get(key, [])
        print(f"{t:12} {lv}: {len(words)} words -> {', '.join(sorted(words)[:5])}...")

print(f"\nTotal global words: {len(all_words)}")

# Lưu all_words ra file JSON để script khác dùng
with open('backend/scratch/all_existing_words.json', 'w', encoding='utf-8') as f:
    json.dump(sorted(list(all_words)), f, ensure_ascii=False, indent=2)
print("Saved to all_existing_words.json")
conn.close()
