import sqlite3, os
DB_PATH = os.path.join('backend', 'app', 'ai_coach.db')
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute("SELECT LOWER(word) FROM vocabularies")
existing = set(r[0] for r in c.fetchall())

def ins(words, topic, level):
    i = 0
    for w, ipa, mean, ex in words:
        if w.lower() in existing: continue
        c.execute("INSERT INTO vocabularies (word,ipa,meaning,example,topic,level,is_active,created_at) VALUES (?,?,?,?,?,?,1,datetime('now'))", (w,ipa,mean,ex,topic,level))
        existing.add(w.lower()); i += 1
    return i

# Business A1: +1
r = ins([("revenue stream", "/ˈrɛv.ɪ.njuː striːm/", "dòng doanh thu của doanh nghiệp", "Identify multiple revenue streams.")], 'business', 'A1')
print(f"Business A1: +{r}")

# Business A2: +3
r = ins([
    ("gross revenue", "/ɡroʊs ˈrɛv.ɪ.njuː/", "tổng doanh thu chưa trừ chi phí", "Report gross revenue to investors."),
    ("business objective", "/ˈbɪz.nɪs əbˈdʒɛk.tɪv/", "mục tiêu kinh doanh cụ thể", "Set clear business objectives."),
    ("operating profit", "/ˈɒp.ər.eɪ.tɪŋ ˈprɒf.ɪt/", "lợi nhuận từ hoạt động kinh doanh chính", "Operating profit excludes interest and tax."),
], 'business', 'A2')
print(f"Business A2: +{r}")

# Job B1: +1
r = ins([("sprint planning", "/sprɪnt ˈplæn.ɪŋ/", "lập kế hoạch sprint đầu chu kỳ", "Sprint planning sets goals for the week.")], 'job', 'B1')
print(f"Job B1: +{r}")

conn.commit()
conn.close()
print("Done!")
