import json
import sqlite3
import re
import os

# Danh sách từ vựng hiện tại (tránh trùng)
with open('e:/Project/Hoc/hoc-tieng-anh/backend/scratch/existing_words.json', 'r', encoding='utf-8') as f:
    existing_map = json.load(f)

# Phân loại theo chủ đề và level
existing_by_topic = {}
for w, info in existing_map.items():
    t = info['topic']
    lvl = info['level']
    existing_by_topic.setdefault(t, {}).setdefault(lvl, set()).add(w)

print("Pre-existing structures loaded.")
