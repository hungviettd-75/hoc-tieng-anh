import json
import sqlite3
import re
import eng_to_ipa as ipa

# 1. Đọc từ file learn.py và DB để lấy danh sách từ duy nhất
learn_words = []
try:
    with open('e:/Project/Hoc/hoc-tieng-anh/backend/app/api/v1/endpoints/learn.py', 'r', encoding='utf-8') as f:
        content = f.read()
    matches = re.findall(r'\{\"word\":\s*\"([^\"]+)\",\s*\"ipa\":\s*\"([^\"]+)\",\s*\"meaning\":\s*\"([^\"]+)\"', content)
    for m in matches:
        learn_words.append({"word": m[0], "ipa": m[1]})
except Exception as e:
    print("Error reading learn.py:", e)

db_words = []
try:
    conn = sqlite3.connect('e:/Project/Hoc/hoc-tieng-anh/backend/app/ai_coach.db')
    c = conn.cursor()
    c.execute("SELECT word, ipa FROM vocabularies")
    for r in c.fetchall():
        db_words.append({"word": r[0], "ipa": r[1]})
    conn.close()
except Exception as e:
    print("Error reading DB:", e)

all_words = learn_words + db_words
unique_words = {}
for w in all_words:
    word_lower = w["word"].lower()
    if word_lower not in unique_words:
        unique_words[word_lower] = {"word": w["word"], "ipa": w["ipa"]}

print(f"Loaded {len(unique_words)} words to check.")

def clean_ipa(s):
    if not s:
        return ""
    s = s.replace("/", "").replace("ˈ", "").replace("ˌ", "").replace(".", "").replace(" ", "").replace("ˈ", "")
    s = s.replace("g", "ɡ")
    return s.lower()

# Đếm khoảng cách Levenshtein
def edit_dist(s1, s2):
    if len(s1) < len(s2):
        return edit_dist(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

bad_ipas = []
for item in unique_words.values():
    word = item["word"]
    db_ipa = item["ipa"]
    
    suggested = ipa.convert(word)
    if "*" in suggested or not suggested:
        continue
        
    cleaned_db = clean_ipa(db_ipa)
    cleaned_sug = clean_ipa(suggested)
    
    dist = edit_dist(cleaned_db, cleaned_sug)
    max_len = max(len(cleaned_db), len(cleaned_sug), 1)
    ratio = dist / max_len
    
    if ratio > 0.6:
        # standard format e.g. /braɪt/
        bad_ipas.append({
            "word": word,
            "suggested_ipa": f"/{suggested}/"
        })

print(f"Found {len(bad_ipas)} bad IPAs to fix.")

# Tiến hành update vào DB và learn.py
conn = sqlite3.connect('e:/Project/Hoc/hoc-tieng-anh/backend/app/ai_coach.db')
c = conn.cursor()

FILE_PATH = 'e:/Project/Hoc/hoc-tieng-anh/backend/app/api/v1/endpoints/learn.py'
with open(FILE_PATH, 'r', encoding='utf-8') as f:
    learn_content = f.read()

fixed_count_db = 0
fixed_count_file = 0

for item in bad_ipas:
    word = item["word"]
    suggested = item["suggested_ipa"]
    
    c.execute("UPDATE vocabularies SET ipa=? WHERE word=? COLLATE NOCASE", (suggested, word))
    if c.rowcount > 0:
        fixed_count_db += c.rowcount
        
    pattern = rf'(\"word\":\s*\"{re.escape(word)}\",\s*\"ipa\":\s*\")[^\"]+(\")'
    replacement = rf'\1{suggested}\2'
    
    if re.search(pattern, learn_content, re.IGNORECASE):
        learn_content = re.sub(pattern, replacement, learn_content, flags=re.IGNORECASE)
        fixed_count_file += 1

conn.commit()
conn.close()

with open(FILE_PATH, 'w', encoding='utf-8') as f:
    f.write(learn_content)

print(f"Successfully fixed {fixed_count_db} rows in DB.")
print(f"Successfully fixed {fixed_count_file} definitions in learn.py.")
