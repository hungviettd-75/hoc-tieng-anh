"""
Script import lại tất cả các từ vựng còn thiếu cho các list bị xóa
"""
import sqlite3, os, sys
sys.path.insert(0, os.path.dirname(__file__))
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app', 'ai_coach.db')
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.execute("SELECT LOWER(word) FROM vocabularies")
existing = set(r[0] for r in c.fetchall())

def ins(words, topic, level):
    i = 0
    for w_info in words:
        if isinstance(w_info, dict):
            w = w_info['word']; ipa = w_info.get('ipa',''); mean = w_info.get('meaning',''); ex = w_info.get('example','')
        else:
            w = w_info[0]; ipa = w_info[1]; mean = w_info[2]; ex = w_info[3]
        if w.lower().strip() in existing: continue
        c.execute("INSERT INTO vocabularies (word,ipa,meaning,example,topic,level,is_active,created_at) VALUES (?,?,?,?,?,?,1,datetime('now'))", (w,ipa,mean,ex,topic,level))
        existing.add(w.lower().strip()); i += 1
    return i

total = 0
from vocab_data_rest import JOB_A1, JOB_A2, JOB_B2, JOB_C1
from vocab_data_extra import JOB_B1_EXTRA, JOB_A1_EXTRA, JOB_A2_EXTRA, JOB_B2_EXTRA, JOB_C1_EXTRA
total += ins(JOB_A1, 'job', 'A1'); total += ins(JOB_A1_EXTRA, 'job', 'A1')
total += ins(JOB_A2, 'job', 'A2'); total += ins(JOB_A2_EXTRA, 'job', 'A2')
total += ins(JOB_B1_EXTRA, 'job', 'B1')
total += ins(JOB_B2, 'job', 'B2'); total += ins(JOB_B2_EXTRA, 'job', 'B2')
total += ins(JOB_C1, 'job', 'C1'); total += ins(JOB_C1_EXTRA, 'job', 'C1')

# Travel full
try:
    from vocab_travel_full import VOCABULARY_DATA
    for lvl in ['A1','A2','B1','B2','C1']:
        if lvl in VOCABULARY_DATA['travel']:
            total += ins(VOCABULARY_DATA['travel'][lvl], 'travel', lvl)
except Exception as e:
    print("Error travel:", e)
    
# But wait, travel B1 was generated somewhere else if it's not in VOCABULARY_DATA.
# Let's import all the travel data from travel_vocab.json if it exists!
try:
    import json
    with open('backend/scratch/travel_vocab.json', 'r', encoding='utf-8') as f:
        travel_json = json.load(f)
        for lvl in travel_json:
            total += ins(travel_json[lvl], 'travel', lvl)
except Exception as e:
    pass

# Final gaps
try:
    total += ins([("sprint planning", "/sprɪnt ˈplæn.ɪŋ/", "lập kế hoạch sprint đầu chu kỳ", "Sprint planning sets goals for the week.")], 'job', 'B1')
except:
    pass

conn.commit()
conn.close()
print(f"Inserted {total} missing words!")
