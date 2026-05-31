import sqlite3
import re

# 1. Dọn dẹp trong cơ sở dữ liệu ai_coach.db
conn = sqlite3.connect('e:/Project/Hoc/hoc-tieng-anh/backend/app/ai_coach.db')
c = conn.cursor()

# Tìm tất cả các từ trong DB có đuôi số (ví dụ 'Robot 3', 'deadline 4', v.v.)
c.execute("SELECT word FROM vocabularies")
all_db_words = [r[0] for r in c.fetchall()]
numbered_words = [w for w in all_db_words if re.search(r'\s\d+$', w)]

print(f"Found {len(numbered_words)} numbered words in database.")

deleted_vocab = 0
deleted_wrong = 0
deleted_mastered = 0
deleted_memory = 0

for w in numbered_words:
    # Xóa trong vocabularies
    c.execute("DELETE FROM vocabularies WHERE word=?", (w,))
    deleted_vocab += c.rowcount
    
    # Xóa trong các bảng liên quan để tránh dữ liệu rác
    c.execute("DELETE FROM vocabulary_wrong_answers WHERE word=?", (w,))
    deleted_wrong += c.rowcount
    
    c.execute("DELETE FROM vocabulary_mastered_words WHERE word=?", (w,))
    deleted_mastered += c.rowcount
    
    c.execute("DELETE FROM vocabulary_memory WHERE word=?", (w,))
    deleted_memory += c.rowcount

conn.commit()
conn.close()

print("Database Cleanup Summary:")
print(f"- Deleted {deleted_vocab} words from vocabularies table.")
print(f"- Deleted {deleted_wrong} words from vocabulary_wrong_answers.")
print(f"- Deleted {deleted_mastered} words from vocabulary_mastered_words.")
print(f"- Deleted {deleted_memory} words from vocabulary_memory.")


# 2. Dọn dẹp trong file learn.py
FILE_PATH = 'e:/Project/Hoc/hoc-tieng-anh/backend/app/api/v1/endpoints/learn.py'
with open(FILE_PATH, 'r', encoding='utf-8') as f:
    learn_content = f.read()

# learn.py chứa base_vocab với dạng: {"word": "Robot 3", "ipa": "...", ...},
# Chúng ta sẽ phân tích cú pháp hoặc dùng regex để loại bỏ các dict từ vựng có chứa số ở đuôi của trường "word"
# Một dòng từ vựng chuẩn trong learn.py:
#             {"word": "Robot 3", "ipa": "...", "meaning": "...", ...},
# Chúng ta có thể tìm và xóa các dòng này.
lines = learn_content.split('\n')
new_lines = []
removed_lines_count = 0

for line in lines:
    # Nếu dòng chứa "word": "từ_nào_đó số_ở_cuối"
    if re.search(r'"word":\s*"[^"]+ \d+"', line):
        removed_lines_count += 1
        continue  # Bỏ qua dòng này (xóa nó)
    new_lines.append(line)

new_content = '\n'.join(new_lines)

# Ghi lại file learn.py
with open(FILE_PATH, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"Source Code Cleanup Summary:")
print(f"- Removed {removed_lines_count} numbered vocabulary lines from learn.py.")
