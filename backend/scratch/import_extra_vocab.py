"""
Script import dữ liệu bổ sung vào DB
"""
import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app', 'ai_coach.db')

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.execute("SELECT LOWER(word) FROM vocabularies")
existing_words = set(r[0] for r in c.fetchall())
print(f"Existing words: {len(existing_words)}")

def insert_words(words_list, topic, level):
    inserted = 0
    skipped = 0
    for item in words_list:
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

from vocab_data_extra import (
    AI_B1_EXTRA, AI_B2_EXTRA,
    BUSINESS_A1_EXTRA, BUSINESS_A2_EXTRA, BUSINESS_B2_EXTRA, BUSINESS_C1_EXTRA,
    JOB_A1_EXTRA, JOB_A2_EXTRA, JOB_B1_EXTRA, JOB_B2_EXTRA, JOB_C1_EXTRA,
    MARKETING_A1_EXTRA, MARKETING_A2_EXTRA, MARKETING_B1_EXTRA, MARKETING_B2_EXTRA, MARKETING_C1_EXTRA,
    TECH_A1_EXTRA, TECH_B1_EXTRA, TECH_B2_EXTRA,
)

print("\n=== AI EXTRA ===")
for level, data in [('B1', AI_B1_EXTRA), ('B2', AI_B2_EXTRA)]:
    ins, skip = insert_words(data, 'ai', level)
    print(f"  AI {level}: +{ins} inserted, {skip} skipped")

print("\n=== BUSINESS EXTRA ===")
for level, data in [('A1', BUSINESS_A1_EXTRA), ('A2', BUSINESS_A2_EXTRA), ('B2', BUSINESS_B2_EXTRA), ('C1', BUSINESS_C1_EXTRA)]:
    ins, skip = insert_words(data, 'business', level)
    print(f"  Business {level}: +{ins} inserted, {skip} skipped")

print("\n=== JOB EXTRA ===")
for level, data in [('A1', JOB_A1_EXTRA), ('A2', JOB_A2_EXTRA), ('B1', JOB_B1_EXTRA), ('B2', JOB_B2_EXTRA), ('C1', JOB_C1_EXTRA)]:
    ins, skip = insert_words(data, 'job', level)
    print(f"  Job {level}: +{ins} inserted, {skip} skipped")

print("\n=== MARKETING EXTRA ===")
for level, data in [('A1', MARKETING_A1_EXTRA), ('A2', MARKETING_A2_EXTRA), ('B1', MARKETING_B1_EXTRA), ('B2', MARKETING_B2_EXTRA), ('C1', MARKETING_C1_EXTRA)]:
    ins, skip = insert_words(data, 'marketing', level)
    print(f"  Marketing {level}: +{ins} inserted, {skip} skipped")

print("\n=== TECH EXTRA ===")
for level, data in [('A1', TECH_A1_EXTRA), ('B1', TECH_B1_EXTRA), ('B2', TECH_B2_EXTRA)]:
    ins, skip = insert_words(data, 'tech', level)
    print(f"  Tech {level}: +{ins} inserted, {skip} skipped")

conn.commit()
conn.close()
print("\n=== DONE ===")
