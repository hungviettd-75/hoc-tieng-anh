import json
import sqlite3

# 1. Đọc từ file learn.py
learn_words = []
try:
    with open('e:/Project/Hoc/hoc-tieng-anh/backend/app/api/v1/endpoints/learn.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Tìm các dictionary từ vựng dạng {"word": "...", "ipa": "...", "meaning": "..."}
    import re
    matches = re.findall(r'\{\"word\":\s*\"([^\"]+)\",\s*\"ipa\":\s*\"([^\"]+)\",\s*\"meaning\":\s*\"([^\"]+)\"', content)
    for m in matches:
        learn_words.append({
            "source": "learn.py",
            "word": m[0],
            "ipa": m[1],
            "meaning": m[2]
        })
except Exception as e:
    print("Error reading learn.py:", e)

# 2. Đọc từ database
db_words = []
try:
    conn = sqlite3.connect('e:/Project/Hoc/hoc-tieng-anh/backend/app/ai_coach.db')
    c = conn.cursor()
    c.execute("SELECT word, ipa, meaning FROM vocabularies")
    for r in c.fetchall():
        db_words.append({
            "source": "db",
            "word": r[0],
            "ipa": r[1],
            "meaning": r[2]
        })
    conn.close()
except Exception as e:
    print("Error reading DB:", e)

all_words = learn_words + db_words
# Deduplicate by word (keep first)
unique_words = {}
for w in all_words:
    word_lower = w["word"].lower()
    if word_lower not in unique_words:
        unique_words[word_lower] = {
            "word": w["word"],
            "ipa": w["ipa"],
            "meaning": w["meaning"]
        }

with open('e:/Project/Hoc/hoc-tieng-anh/backend/scratch/all_vocab_dump.json', 'w', encoding='utf-8') as f:
    json.dump(list(unique_words.values()), f, ensure_ascii=False, indent=2)

print(f"Dumped {len(unique_words)} unique words to scratch.")
