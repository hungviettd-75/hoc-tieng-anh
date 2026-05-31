import sqlite3
import re

# Định nghĩa các từ cần cập nhật nghĩa tiếng Việt chính xác và ví dụ tương ứng
UPDATES = {
    # word: (new_meaning, new_example, ipa)
    "Attraction": ("Điểm thu hút khách du lịch", "The Eiffel Tower is a major tourist attraction.", "/əˈtræk.ʃən/"),
    "Schedule": ("Lịch trình, thời khóa biểu", "I need to check my work schedule.", "/ˈʃedʒ.uːl/"),
    "Lodging": ("Phòng trọ, nơi tạm trú", "The hotel provides free lodging and board.", "/ˈlɒdʒ.ɪŋ/"),
    "Discover": ("Phát hiện ra, khám phá ra", "They discovered a new star in the galaxy.", "/dɪˈskʌv.ər/"),
    "Booking": ("Việc đặt chỗ trước", "Can I make a booking for tonight?", "/ˈbʊk.ɪŋ/"),
    "Journey": ("Hành trình, chuyến đi", "It was a long and tiring journey.", "/ˈdʒɜː.ni/"),
    "Outing": ("Chuyến dã ngoại, đi chơi ngoài trời", "The company organized an outing for its staff.", "/ˈaʊ.tɪŋ/"),
    "Traveler": ("Khách du lịch, người du hành", "The traveler rested by the river.", "/ˈtræv.əl.ər/"),
    "Pass": ("Thẻ thông hành, thẻ ra vào", "You must show your security pass to enter.", "/pɑːs/"),
    "Inn": ("Nhà trọ, quán trọ cổ", "We stayed at a cozy country inn.", "/ɪn/"),
    "Coach": ("Xe khách đường dài", "We traveled from London to Paris by coach.", "/kəʊtʃ/"),
    "Visa": ("Thị thực nhập cảnh", "She applied for a student visa.", "/ˈviː.zə/"),
    "Travel": ("Đi du lịch, di chuyển", "I love to travel to new countries.", "/ˈtræv.əl/"),
    "Luggage": ("Hành lý", "They helped me carry my luggage.", "/ˈlʌɡ.ɪdʒ/"),
    "overtime": ("Làm thêm giờ, thời gian làm thêm", "He worked three hours of overtime yesterday.", "/ˈəʊ.və.taɪm/")
}

# 1. Cập nhật Database
conn = sqlite3.connect('e:/Project/Hoc/hoc-tieng-anh/backend/app/ai_coach.db')
c = conn.cursor()

# Xóa từ 'Algorithm' viết hoa vì đã có 'algorithm' viết thường
c.execute("DELETE FROM vocabularies WHERE word='Algorithm'")
print("Deleted uppercase Algorithm from DB:", c.rowcount)

for word, (meaning, example, ipa) in UPDATES.items():
    c.execute("""
        UPDATE vocabularies 
        SET meaning=?, example=?, ipa=? 
        WHERE word=? COLLATE NOCASE
    """, (meaning, example, ipa, word))
    if c.rowcount > 0:
        print(f"Updated {word} in DB.")

conn.commit()
conn.close()


# 2. Cập nhật file learn.py
FILE_PATH = 'e:/Project/Hoc/hoc-tieng-anh/backend/app/api/v1/endpoints/learn.py'
with open(FILE_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# Xóa từ 'Algorithm' viết hoa trong learn.py
# Tìm cả dòng {"word": "Algorithm", ...} và xóa nó đi
lines = content.split('\n')
new_lines = []
for line in lines:
    if '"word": "Algorithm"' in line:
        print("Removed Algorithm from learn.py")
        continue
    new_lines.append(line)

content = '\n'.join(new_lines)

# Cập nhật nghĩa, ví dụ, ipa cho các từ còn lại trong learn.py
for word, (meaning, example, ipa) in UPDATES.items():
    # regex tìm dòng chứa từ này
    # Ví dụ: {"word": "Attraction", "ipa": "...", "meaning": "...", "example": "..."}
    # Ta sẽ thay thế toàn bộ ipa, meaning, example của từ đó
    pattern = rf'({{\s*"word"\s*:\s*"{re.escape(word)}"\s*,\s*"ipa"\s*:\s*")[^"]+("\s*,\s*"meaning"\s*:\s*")[^"]+("\s*,\s*"example"\s*:\s*")[^"]+(")'
    replacement = rf'\1{ipa}\2{meaning}\3{example}\4'
    
    # Một số từ viết thường hoặc viết hoa chữ cái đầu, ta check ignore case
    content, count = re.subn(pattern, replacement, content, flags=re.IGNORECASE)
    if count > 0:
        print(f"Updated {word} {count} times in learn.py")

with open(FILE_PATH, 'w', encoding='utf-8') as f:
    f.write(content)
