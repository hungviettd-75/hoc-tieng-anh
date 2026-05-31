import re

with open('e:/Project/Hoc/hoc-tieng-anh/backend/app/api/v1/endpoints/learn.py', 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
for i, line in enumerate(lines):
    match = re.search(r'"word":\s*"([^"]+ \d+)"', line)
    if match:
        print(f"Line {i+1}: word={match.group(1)}")
        if i > 1200:
            break
