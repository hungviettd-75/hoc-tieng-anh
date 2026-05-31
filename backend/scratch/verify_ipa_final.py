import sqlite3
import eng_to_ipa as ipa_lib

def edit_dist(s1, s2):
    if len(s1) < len(s2):
        return edit_dist(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (c1 != c2)))
        prev = curr
    return prev[-1]

def normalize_ipa(s):
    if not s:
        return ""
    s = s.replace("/", "").replace("ˈ", "").replace("ˌ", "").replace(".", "").replace(" ", "")
    return s.lower()

conn = sqlite3.connect('e:/Project/Hoc/hoc-tieng-anh/backend/app/ai_coach.db')
c = conn.cursor()
c.execute("SELECT id, word, ipa FROM vocabularies")
rows = c.fetchall()

bad = []
for (db_id, word, db_ipa) in rows:
    suggested = ipa_lib.convert(word)
    if not suggested or "*" in suggested:
        continue
    n_db = normalize_ipa(db_ipa)
    n_su = normalize_ipa(suggested)
    max_len = max(len(n_db), len(n_su), 1)
    dist = edit_dist(n_db, n_su)
    ratio = dist / max_len
    if ratio > 0.6:
        bad.append((db_id, word, db_ipa, f"/{suggested}/"))

print(f"Remaining bad IPAs: {len(bad)}")
for item in bad:
    print(f"  word={item[1]} | current={item[2]} | correct={item[3]}")

if bad:
    for (db_id, word, old_ipa, new_ipa) in bad:
        c.execute("UPDATE vocabularies SET ipa=? WHERE id=?", (new_ipa, db_id))
    conn.commit()
    print(f"Fixed {len(bad)} more rows.")
else:
    print("All IPAs in database are correct!")

conn.close()
