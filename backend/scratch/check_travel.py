import json

with open('backend/scratch/travel_vocab.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

from collections import Counter
levels = Counter(d['level'] for d in data)
print("=== TRAVEL VOCAB COUNT ===")
for lv in ['A1','A2','B1','B2','C1']:
    print(f"  {lv}: {levels.get(lv, 0)} words")

with open('backend/scratch/existing_words.json', 'r', encoding='utf-8') as f:
    existing = json.load(f)

print(f"\nExisting words in DB: {len(existing)}")
