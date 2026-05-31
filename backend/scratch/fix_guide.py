import sqlite3

conn = sqlite3.connect('e:/Project/Hoc/hoc-tieng-anh/backend/app/ai_coach.db')
c = conn.cursor()

# Find Guide records
c.execute("SELECT id, word, ipa, meaning, example FROM vocabularies WHERE word='Guide' COLLATE NOCASE")
records = c.fetchall()
print("Guides in DB:", records)

# If one of them has meaning containing 'bản đồ' or 'Bản đồ' or ipa '/mæp/', update it to 'Atlas'
for r in records:
    db_id, word, ipa_val, meaning, example = r
    if 'bản đồ' in meaning.lower() or ipa_val == '/mæp/' or 'map' in example.lower():
        print(f"Updating record {db_id} to Atlas")
        c.execute("""
            UPDATE vocabularies 
            SET word='Atlas', ipa='/ˈæt.ləs/', meaning='Bản đồ, tập bản đồ', example='We need an atlas to find our way.'
            WHERE id=?
        """, (db_id,))
        
conn.commit()

c.execute("SELECT id, word, ipa, meaning, example FROM vocabularies WHERE word IN ('Guide', 'Atlas') COLLATE NOCASE")
print("After update in DB:", c.fetchall())
conn.close()
