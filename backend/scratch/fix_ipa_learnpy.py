import sqlite3
import re
import eng_to_ipa as ipa_lib

# Helper: Levenshtein distance
def edit_dist(s1, s2):
    if len(s1) < len(s2):
        return edit_dist(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (c1 != c2)))
        prev = curr
    return prev[-1]

def normalize_ipa(s):
    if not s:
        return ""
    s = s.replace("/", "").replace("ˈ", "").replace("ˌ", "").replace(".", "").replace(" ", "")
    return s.lower()

# --- 1. Quét và sửa file learn.py ---
FILE_PATH = 'e:/Project/Hoc/hoc-tieng-anh/backend/app/api/v1/endpoints/learn.py'
with open(FILE_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# Tìm tất cả các entry từ vựng trong learn.py
pattern = r'"word":\s*"([^"]+)",\s*"ipa":\s*"([^"]+)"'
matches = list(re.finditer(pattern, content))

print(f"Found {len(matches)} word+ipa pairs in learn.py")

fixed_count = 0
# Duyệt ngược để giữ nguyên offset của các match trước
for m in reversed(matches):
    word = m.group(1)
    db_ipa = m.group(2)
    
    suggested = ipa_lib.convert(word)
    if not suggested or "*" in suggested:
        continue
    
    new_ipa = f"/{suggested}/"
    n_db = normalize_ipa(db_ipa)
    n_su = normalize_ipa(suggested)
    max_len = max(len(n_db), len(n_su), 1)
    dist = edit_dist(n_db, n_su)
    ratio = dist / max_len
    
    if ratio > 0.6:
        # Thay thế đúng đoạn ipa trong nội dung
        start = m.start(2)
        end = m.end(2)
        content = content[:start] + new_ipa + content[end:]
        fixed_count += 1

print(f"Fixed {fixed_count} IPAs in learn.py")

with open(FILE_PATH, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done. Syntax check...")
import py_compile
try:
    py_compile.compile(FILE_PATH, doraise=True)
    print("Syntax OK")
except py_compile.PyCompileError as e:
    print("Syntax ERROR:", e)
