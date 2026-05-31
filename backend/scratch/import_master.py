"""
Script master để import toàn bộ dữ liệu từ vựng vào DB.
Chỉ thêm từ chưa có, không trùng lặp.
"""
import sqlite3
import json
import os

DB_PATH = 'backend/app/ai_coach.db'
TRAVEL_JSON = 'backend/scratch/travel_vocab.json'

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Lấy tất cả từ đã có trong DB (word + topic + level)
c.execute("SELECT word, topic, level FROM vocabularies")
existing_rows = set((r[0].lower().strip(), r[1], r[2]) for r in c.fetchall())
existing_words_global = set(r[0].lower().strip() for r in existing_rows)

print(f"Current DB has {len(existing_rows)} words total")
print(f"Unique words: {len(existing_words_global)}")

def insert_vocab(words_list, topic, level):
    """Insert list of vocab dicts into DB, skipping duplicates."""
    inserted = 0
    skipped = 0
    for item in words_list:
        word = item['word'].lower().strip()
        key = (word, topic, level)
        if key in existing_rows or word in existing_words_global:
            skipped += 1
            continue
        c.execute("""
            INSERT INTO vocabularies (word, ipa, meaning, example, topic, level, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, datetime('now'))
        """, (item['word'], item.get('ipa',''), item.get('meaning',''), item.get('example',''), topic, level))
        existing_rows.add(key)
        existing_words_global.add(word)
        inserted += 1
    return inserted, skipped

# ============================================================
# 1. Import TRAVEL from JSON
# ============================================================
print("\n=== IMPORTING TRAVEL ===")
with open(TRAVEL_JSON, 'r', encoding='utf-8') as f:
    travel_data = json.load(f)

travel_by_level = {}
for item in travel_data:
    lv = item['level']
    travel_by_level.setdefault(lv, []).append(item)

for level, words in sorted(travel_by_level.items()):
    ins, skip = insert_vocab(words, 'travel', level)
    print(f"  Travel {level}: +{ins} inserted, {skip} skipped")

conn.commit()

# ============================================================
# 2. Kiểm tra trạng thái hiện tại
# ============================================================
print("\n=== FINAL STATUS ===")
c.execute("SELECT topic, level, COUNT(*) FROM vocabularies GROUP BY topic, level ORDER BY topic, level")
rows = c.fetchall()
targets = ('travel','tech','ai','marketing','job','business')
for r in rows:
    if r[0] in targets:
        status = "✓" if r[2] >= 50 else f"✗ (need {50-r[2]} more)"
        print(f"  {r[0]:12} | {r[1]} | {r[2]:3d} {status}")

conn.close()
print("\nDone!")
