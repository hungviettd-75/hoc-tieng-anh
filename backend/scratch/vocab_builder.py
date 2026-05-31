import json
import sqlite3
import re
import os

# 1. Load các từ vựng hiện đang có để hoàn toàn tránh trùng lặp
with open('e:/Project/Hoc/hoc-tieng-anh/backend/scratch/existing_words.json', 'r', encoding='utf-8') as f:
    existing_map = json.load(f)

existing_words_set = set(existing_map.keys())

# Định nghĩa các bộ từ vựng 50 từ chất lượng cho mỗi chủ đề, mỗi level A1, A2, B1, B2, C1
# Chủ đề cần bổ sung đầy đủ:
# - ai (A1-C1)
# - travel (A1-C1)
# - tech (A1-C1)
# - marketing (A1-C1)
# - job (A1-C1)
# - business (A1-A2)

# Ta sẽ viết một script sinh ra cấu trúc dữ liệu khổng lồ này và ghi vào file để dễ import hoặc merge.
# Để tạo ra đúng 50 từ cho mỗi level x chủ đề, ta dùng danh sách phong phú nhất có thể.

# Hãy viết mã Python cấu trúc để tự động kiểm tra xem các danh sách được tạo ra có bất kỳ từ nào trùng lặp nhau hay trùng lặp với DB không.
# Nếu trùng, nó sẽ báo lỗi ngay lập tức để ta thay thế từ khác trước khi lưu.
