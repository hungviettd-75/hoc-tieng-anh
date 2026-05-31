import sqlite3

conn = sqlite3.connect('backend/app/ai_coach.db')
c = conn.cursor()
c.execute("SELECT topic, level, COUNT(*) as cnt FROM vocabularies GROUP BY topic, level ORDER BY topic, level")
rows = c.fetchall()
topics = ('travel', 'tech', 'ai', 'marketing', 'job', 'business')
print("=== VOCAB STATUS ===")
for r in rows:
    if r[0] in topics:
        print(f"Topic: {r[0]:12} | Level: {r[1]} | Count: {r[2]}")
conn.close()
