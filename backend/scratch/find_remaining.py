import re
import json

with open('e:/Project/Hoc/hoc-tieng-anh/backend/app/api/v1/endpoints/learn.py', 'r', encoding='utf-8') as f:
    content = f.read()

words = re.findall(r'"word":\s*"([^"]+) 2"', content)
print("FOUND:", len(words))
print(json.dumps(words, indent=2))
