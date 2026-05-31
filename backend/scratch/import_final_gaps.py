"""
Import các từ còn thiếu cuối cùng để đạt đúng 50/level
"""
import sqlite3, sys, os
sys.path.insert(0, os.path.dirname(__file__))
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app', 'ai_coach.db')
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute("SELECT LOWER(word) FROM vocabularies")
existing = set(r[0] for r in c.fetchall())
print(f"Current: {len(existing)} words in DB")

def ins(words, topic, level):
    i, s = 0, 0
    for w, ipa, mean, ex in words:
        if w.lower() in existing:
            s += 1; continue
        c.execute("INSERT INTO vocabularies (word,ipa,meaning,example,topic,level,is_active,created_at) VALUES (?,?,?,?,?,?,1,datetime('now'))",
                  (w, ipa, mean, ex, topic, level))
        existing.add(w.lower()); i += 1
    return i, s

# === BUSINESS A1: cần 11 từ ===
biz_a1 = [
    ("brand name", "/brænd neɪm/", "tên thương hiệu sản phẩm", "Build a strong brand name."),
    ("business card", "/ˈbɪz.nɪs kɑːrd/", "danh thiếp kinh doanh", "Give your business card to clients."),
    ("cash register", "/kæʃ ˈrɛdʒ.ɪs.tər/", "máy tính tiền thu ngân", "Use a cash register at checkout."),
    ("price list", "/praɪs lɪst/", "bảng giá sản phẩm", "Check the price list before ordering."),
    ("trade", "/treɪd/", "buôn bán giao thương", "Trade is the backbone of business.") if "trade" not in existing else None,
    ("profit sharing", "/ˈprɒf.ɪt ˈʃɛər.ɪŋ/", "chia sẻ lợi nhuận với nhân viên", "Profit sharing motivates staff."),
    ("working hours", "/ˈwɜːr.kɪŋ aʊərz/", "giờ làm việc hành chính", "Working hours are nine to five."),
    ("business license", "/ˈbɪz.nɪs ˈlaɪ.səns/", "giấy phép kinh doanh", "Apply for a business license first."),
    ("opening hours", "/ˈoʊ.pən.ɪŋ aʊərz/", "giờ mở cửa kinh doanh", "The opening hours are posted on the door."),
    ("sales target", "/seɪlz ˈtɑːr.ɡɪt/", "mục tiêu doanh số bán hàng", "Reach your monthly sales target."),
    ("net income", "/nɛt ˈɪn.kʌm/", "thu nhập ròng sau thuế", "Calculate your net income monthly."),
]
biz_a1 = [x for x in biz_a1 if x is not None]
i, s = ins(biz_a1, 'business', 'A1')
print(f"Business A1: +{i} inserted, {s} skipped")

# === BUSINESS A2: cần 8 từ ===
biz_a2 = [
    ("operating budget", "/ˈɒp.ər.eɪ.tɪŋ ˈbʌdʒ.ɪt/", "ngân sách hoạt động hàng năm", "Set the operating budget carefully."),
    ("market analysis", "/ˈmɑːr.kɪt əˈnæl.ɪ.sɪs/", "phân tích thị trường chi tiết", "Conduct a market analysis first."),
    ("cost reduction", "/kɒst rɪˈdʌk.ʃən/", "cắt giảm chi phí vận hành", "Cost reduction improves profit margins."),
    ("business development", "/ˈbɪz.nɪs dɪˈvɛl.əp.mənt/", "phát triển kinh doanh mở rộng", "Business development finds new opportunities."),
    ("market expansion", "/ˈmɑːr.kɪt ɪkˈspæn.ʃən/", "mở rộng thị trường mới", "Plan a market expansion strategy."),
    ("profit forecast", "/ˈprɒf.ɪt ˈfɔːr.kæst/", "dự báo lợi nhuận tương lai", "The profit forecast looks optimistic."),
    ("financial report", "/faɪˈnæn.ʃəl rɪˈpɔːrt/", "báo cáo tài chính doanh nghiệp", "Review the financial report quarterly."),
    ("risk assessment", "/rɪsk əˈsɛs.mənt/", "đánh giá rủi ro kinh doanh", "Conduct a risk assessment before investing."),
]
i, s = ins(biz_a2, 'business', 'A2')
print(f"Business A2: +{i} inserted, {s} skipped")

# === JOB A1: cần 1 từ ===
job_a1 = [
    ("resignation letter", "/ˌrɛz.ɪɡˈneɪ.ʃən ˈlɛt.ər/", "thư xin nghỉ việc chính thức", "Write a professional resignation letter."),
]
i, s = ins(job_a1, 'job', 'A1')
print(f"Job A1: +{i} inserted, {s} skipped")

# === JOB A2: cần 3 từ ===
job_a2 = [
    ("fixed-term contract", "/ˌfɪkst tɜːrm ˈkɒn.trækt/", "hợp đồng có thời hạn cố định", "I am on a fixed-term contract."),
    ("permanent position", "/ˈpɜːr.mə.nənt pəˈzɪʃ.ən/", "vị trí làm việc lâu dài ổn định", "She got a permanent position."),
    ("performance bonus", "/pərˈfɔːr.məns ˈboʊ.nəs/", "thưởng dựa trên hiệu suất công việc", "Earn a performance bonus this quarter."),
]
i, s = ins(job_a2, 'job', 'A2')
print(f"Job A2: +{i} inserted, {s} skipped")

# === JOB B1: cần 6 từ ===
job_b1 = [
    ("agile methodology", "/ˈædʒ.aɪl mɛθˈɒd.ə.lɒdʒ.i/", "phương pháp luận agile linh hoạt", "Use agile methodology for projects."),
    ("task management", "/tæsk ˈmæn.ɪdʒ.mənt/", "quản lý nhiệm vụ công việc hàng ngày", "Good task management boosts productivity."),
    ("project deadline", "/ˈprɒdʒ.ɛkt ˈdɛd.laɪn/", "hạn chót hoàn thành dự án", "Meet every project deadline."),
    ("cross-departmental", "/ˌkrɒs dɪˈpɑːrt.mɛn.təl/", "liên phòng ban hợp tác cùng nhau", "Cross-departmental projects need coordination."),
    ("job satisfaction", "/dʒɒb ˌsæt.ɪsˈfæk.ʃən/", "sự hài lòng với công việc", "Job satisfaction increases retention."),
    ("employee retention", "/ɪmˈplɔɪ.iː rɪˈtɛn.ʃən/", "giữ chân nhân viên tài năng", "Employee retention reduces hiring costs."),
]
i, s = ins(job_b1, 'job', 'B1')
print(f"Job B1: +{i} inserted, {s} skipped")

# === MARKETING A1: cần 4 từ ===
mkt_a1 = [
    ("advertisement", "/ədˈvɜːr.tɪs.mənt/", "mẫu quảng cáo chính thức", "Place an advertisement in the paper."),
    ("brand image", "/brænd ˈɪm.ɪdʒ/", "hình ảnh thương hiệu trong tâm trí", "Build a positive brand image."),
    ("sales pitch", "/seɪlz pɪtʃ/", "bài thuyết phục bán hàng", "Prepare a strong sales pitch."),
    ("word-of-mouth", "/wɜːrd əv maʊθ/", "truyền miệng quảng cáo tự nhiên", "Word-of-mouth is very effective."),
]
i, s = ins(mkt_a1, 'marketing', 'A1')
print(f"Marketing A1: +{i} inserted, {s} skipped")

# === MARKETING A2: cần 3 từ ===
mkt_a2 = [
    ("market trend", "/ˈmɑːr.kɪt trɛnd/", "xu hướng thị trường hiện tại", "Follow the latest market trends."),
    ("consumer behavior", "/kənˈsjuː.mər bɪˈheɪ.vjər/", "hành vi tiêu dùng của khách hàng", "Study consumer behavior for insights."),
    ("product positioning", "/ˈprɒd.ʌkt pəˈzɪʃ.ən.ɪŋ/", "định vị sản phẩm trong tâm trí", "Clear product positioning drives sales."),
]
i, s = ins(mkt_a2, 'marketing', 'A2')
print(f"Marketing A2: +{i} inserted, {s} skipped")

# === MARKETING B1: cần 1 từ ===
mkt_b1 = [
    ("brand loyalty program", "/brænd ˈlɔɪ.əl.ti ˈproʊ.ɡræm/", "chương trình khách hàng trung thành", "Launch a brand loyalty program."),
]
i, s = ins(mkt_b1, 'marketing', 'B1')
print(f"Marketing B1: +{i} inserted, {s} skipped")

# === TECH A1: cần 1 từ ===
tech_a1 = [
    ("QR code", "/ˌkjuː.ɑːr ˈkoʊd/", "mã QR quét bằng điện thoại", "Scan the QR code to visit the website."),
]
i, s = ins(tech_a1, 'tech', 'A1')
print(f"Tech A1: +{i} inserted, {s} skipped")

# === TECH B1: cần 1 từ ===
tech_b1 = [
    ("message broker", "/ˈmɛs.ɪdʒ ˈbroʊ.kər/", "môi giới tin nhắn kết nối dịch vụ", "Kafka is a popular message broker."),
]
i, s = ins(tech_b1, 'tech', 'B1')
print(f"Tech B1: +{i} inserted, {s} skipped")

conn.commit()
conn.close()
print("\nAll done!")
