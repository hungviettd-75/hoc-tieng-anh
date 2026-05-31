"""
Script import tổng hợp: đổ toàn bộ dữ liệu vào DB
Tránh trùng lặp 100% với từ đã có
"""
import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app', 'ai_coach.db')

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Lấy tất cả từ đã có
c.execute("SELECT LOWER(word) FROM vocabularies")
existing_words = set(r[0] for r in c.fetchall())
print(f"Existing words: {len(existing_words)}")

def insert_words(words_list, topic, level):
    """Insert (word, ipa, meaning, example) tuples or dicts"""
    inserted = 0
    skipped = 0
    for item in words_list:
        if isinstance(item, dict):
            word = item['word']
            ipa = item.get('ipa', '')
            meaning = item.get('meaning', '')
            example = item.get('example', '')
        else:
            word, ipa, meaning, example = item[0], item[1], item[2], item[3]
        
        word_lower = word.lower().strip()
        if word_lower in existing_words:
            skipped += 1
            continue
        
        c.execute("""
            INSERT INTO vocabularies (word, ipa, meaning, example, topic, level, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, datetime('now'))
        """, (word, ipa, meaning, example, topic, level))
        existing_words.add(word_lower)
        inserted += 1
    return inserted, skipped

# ============ IMPORT AI ============
print("\n=== AI ===")
from vocab_data_ai import AI_A1, AI_A2, AI_B1, AI_B2, AI_C1

for level, data in [('A1', AI_A1), ('A2', AI_A2), ('B1', AI_B1), ('B2', AI_B2), ('C1', AI_C1)]:
    ins, skip = insert_words(data, 'ai', level)
    print(f"  AI {level}: +{ins} inserted, {skip} skipped")

# ============ IMPORT TECH ============
print("\n=== TECH ===")
from vocab_data_tech import TECH_A1, TECH_A2, TECH_B1, TECH_B2, TECH_C1

for level, data in [('A1', TECH_A1), ('A2', TECH_A2), ('B1', TECH_B1), ('B2', TECH_B2), ('C1', TECH_C1)]:
    ins, skip = insert_words(data, 'tech', level)
    print(f"  Tech {level}: +{ins} inserted, {skip} skipped")

# ============ IMPORT MARKETING ============
print("\n=== MARKETING ===")
from vocab_data_rest import (
    MARKETING_A1, MARKETING_A2, MARKETING_B1, MARKETING_B2, MARKETING_C1,
    JOB_A1, JOB_A2, JOB_B2, JOB_C1,
    BUSINESS_A1, BUSINESS_A2, BUSINESS_B2, BUSINESS_C1
)

for level, data in [('A1', MARKETING_A1), ('A2', MARKETING_A2), ('B1', MARKETING_B1), ('B2', MARKETING_B2), ('C1', MARKETING_C1)]:
    ins, skip = insert_words(data, 'marketing', level)
    print(f"  Marketing {level}: +{ins} inserted, {skip} skipped")

# ============ IMPORT JOB ============
print("\n=== JOB ===")
for level, data in [('A1', JOB_A1), ('A2', JOB_A2), ('B2', JOB_B2), ('C1', JOB_C1)]:
    ins, skip = insert_words(data, 'job', level)
    print(f"  Job {level}: +{ins} inserted, {skip} skipped")

# ============ IMPORT BUSINESS ============
print("\n=== BUSINESS ===")
for level, data in [('A1', BUSINESS_A1), ('A2', BUSINESS_A2), ('B2', BUSINESS_B2), ('C1', BUSINESS_C1)]:
    ins, skip = insert_words(data, 'business', level)
    print(f"  Business {level}: +{ins} inserted, {skip} skipped")

conn.commit()
conn.close()

print("\n=== DONE! ===")
