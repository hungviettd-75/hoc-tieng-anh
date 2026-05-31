import sqlite3
from collections import defaultdict

conn = sqlite3.connect('e:/Project/Hoc/hoc-tieng-anh/backend/app/ai_coach.db')
c = conn.cursor()

c.execute("SELECT id, word, ipa, meaning FROM vocabularies")
rows = c.fetchall()

meaning_map = defaultdict(list)
for r in rows:
    # Normalize meaning to find exact duplicates (strip, lowercase, remove periods)
    m_norm = r[3].strip().lower().replace('.', '')
    meaning_map[m_norm].append(r)

duplicates = {k: v for k, v in meaning_map.items() if len(v) > 1}

print(f"Found {len(duplicates)} meanings that have duplicate words.")

# Print some duplicates
count = 0
for m, words in duplicates.items():
    if count >= 50:
        break
    # Only print if words are actually different
    word_strs = [w[1] for w in words]
    if len(set(word_strs)) > 1:
        print(f"Meaning: '{m}' -> Words: {word_strs}")
        count += 1

conn.close()
