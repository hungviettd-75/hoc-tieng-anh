import sqlite3

conn = sqlite3.connect('e:/Project/Hoc/hoc-tieng-anh/backend/app/ai_coach.db')
c = conn.cursor()

# Check Coast
c.execute("SELECT id, word, ipa, meaning FROM vocabularies WHERE word='Coast' COLLATE NOCASE")
print("Before:", c.fetchall())

# Update Coast
c.execute("UPDATE vocabularies SET ipa='/kəʊst/', meaning='bờ biển' WHERE word='Coast' COLLATE NOCASE")
conn.commit()

c.execute("SELECT id, word, ipa, meaning FROM vocabularies WHERE word='Coast' COLLATE NOCASE")
print("After:", c.fetchall())

conn.close()
