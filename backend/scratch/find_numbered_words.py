import re

with open('e:/Project/Hoc/hoc-tieng-anh/backend/app/api/v1/endpoints/learn.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find words with trailing number like "Ticket 3", "Hotel 4"
matches = re.findall(r'"word":\s*"([^"]+ \d+)"', content)
print("Found words with number suffixes:", len(matches))
print(set(matches))
