import sqlite3

conn = sqlite3.connect('backend/app/ai_coach.db')
c = conn.cursor()
c.execute("SELECT topic, level, COUNT(*) FROM vocabularies GROUP BY topic, level ORDER BY topic, level")
rows = c.fetchall()
targets = ('travel','tech','ai','marketing','job','business')
print("=== FINAL STATUS ===")
for r in rows:
    if r[0] in targets:
        status = "OK" if r[2] >= 50 else f"NEED {50-r[2]} MORE"
        print(f"  {r[0]:12} | {r[1]} | {r[2]:3d} | {status}")
conn.close()
