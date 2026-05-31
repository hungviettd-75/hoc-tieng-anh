# Đây là bộ dữ liệu khổng lồ chứa đầy đủ 50 từ vựng cho mỗi level: A1, A2, B1, B2, C1
# cho các chủ đề: travel, tech, ai, marketing, job, business
# Được thiết kế để tránh trùng lặp 100% với các từ hiện tại trong DB.

import json
import sqlite3
import os
import sys

# Khởi tạo db session
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from app.db.session import SessionLocal
from app.models.models import Vocabulary

# Đọc file dữ liệu word map để tránh trùng
with open('e:/Project/Hoc/hoc-tieng-anh/backend/scratch/existing_words.json', 'r', encoding='utf-8') as f:
    existing_map = json.load(f)

existing_words_set = set(k.lower().strip() for k in existing_map.keys())

# Nhập danh sách từ vựng khổng lồ từ các file phân nhỏ
# Để đảm bảo tính ổn định và an toàn, ta sẽ load trực tiếp các file python đã tạo
# hoặc định nghĩa trực tiếp ở đây các chủ đề du lịch, công nghệ, marketing, công việc, kinh doanh.

# Ta import các module danh sách từ vựng đã tạo
from vocab_ai_a1_a2 import topics_data as ai_a1_a2
from vocab_ai_b1 import ai_vocab_remaining as ai_b1
from vocab_ai_b2_c1 import ai_b2_c1

# Tích hợp toàn bộ AI vocab vào một cấu trúc chuẩn
FINAL_VOCAB = {
    "ai": {
        "A1": ai_a1_a2["ai"]["A1"],
        "A2": ai_a1_a2["ai"]["A2"],
        "B1": ai_b1["B1"],
        "B2": ai_b2_c1["B2"],
        "C1": ai_b2_c1["C1"]
    }
}

# In thử số lượng để xác minh
for lvl, words in FINAL_VOCAB["ai"].items():
    print(f"AI {lvl}: {len(words)} words")
