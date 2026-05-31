import json
import sqlite3
import re
import eng_to_ipa as ipa

# Load suspicious IPAs
with open('e:/Project/Hoc/hoc-tieng-anh/backend/scratch/suspicious_ipas.json', 'r', encoding='utf-8') as f:
    bad_ipas = json.load(f)

print(f"Loaded {len(bad_ipas)} bad IPAs to fix.")

# Connect to database
conn = sqlite3.connect('e:/Project/Hoc/hoc-tieng-anh/backend/app/ai_coach.db')
c = conn.cursor()

# Read learn.py content
FILE_PATH = 'e:/Project/Hoc/hoc-tieng-anh/backend/app/api/v1/endpoints/learn.py'
with open(FILE_PATH, 'r', encoding='utf-8') as f:
    learn_content = f.read()

fixed_count_db = 0
fixed_count_file = 0

for item in bad_ipas:
    word = item["word"]
    # Get standard suggested IPA (ensure it's clean and wrapped in slashes)
    suggested = item["suggested_ipa"] # e.g. /braɪt/
    
    # 1. Update in SQLite DB
    c.execute("UPDATE vocabularies SET ipa=? WHERE word=? COLLATE NOCASE", (suggested, word))
    if c.rowcount > 0:
        fixed_count_db += c.rowcount
        
    # 2. Update in learn.py file content
    # Find {"word": "Word", "ipa": "wrong_ipa"} or similar patterns
    # We will use regex substitution
    # Standard format in learn.py: {"word": "Bright", "ipa": "/smɑːt/", ...}
    # We want to replace it to {"word": "Bright", "ipa": "/braɪt/", ...}
    # We can search for '"word": "word_here", "ipa": "anything"'
    pattern = rf'(\"word\":\s*\"{re.escape(word)}\",\s*\"ipa\":\s*\")[^\"]+(\")'
    replacement = rf'\1{suggested}\2'
    
    # Check if pattern matches in learn_content
    if re.search(pattern, learn_content, re.IGNORECASE):
        learn_content = re.sub(pattern, replacement, learn_content, flags=re.IGNORECASE)
        fixed_count_file += 1

# Commit DB changes
conn.commit()
conn.close()

# Write updated learn.py
with open(FILE_PATH, 'w', encoding='utf-8') as f:
    f.write(learn_content)

print(f"Successfully fixed {fixed_count_db} rows in DB.")
print(f"Successfully fixed {fixed_count_file} definitions in learn.py.")
