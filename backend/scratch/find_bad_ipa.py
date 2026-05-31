import json
import sqlite3
import re
import eng_to_ipa as ipa

# Load all words from JSON dump
with open('e:/Project/Hoc/hoc-tieng-anh/backend/scratch/all_vocab_dump.json', 'r', encoding='utf-8') as f:
    vocab_list = json.load(f)

print(f"Loaded {len(vocab_list)} words.")

def clean_ipa(s):
    if not s:
        return ""
    # Remove slashes, stress marks, periods, and spaces
    s = s.replace("/", "").replace("ˈ", "").replace("ˌ", "").replace(".", "").replace(" ", "").replace("ˈ", "")
    # Normalize some common IPA characters for comparison
    s = s.replace("g", "ɡ")
    return s.lower()

bad_ipas = []

for item in vocab_list:
    word = item["word"]
    db_ipa = item["ipa"]
    
    # Get standard IPA from library
    # eng-to-ipa returns something like "ǽndrɔyd" or with asterisk if not found
    suggested = ipa.convert(word)
    if "*" in suggested or not suggested:
        continue # skip words not in dictionary
        
    cleaned_db = clean_ipa(db_ipa)
    cleaned_sug = clean_ipa(suggested)
    
    # If the suggested IPA and DB IPA are too different
    # We can check if they share characters, or check simple edit distance
    # Since a wrong IPA (like /bi:tʃ/ vs /kəust/) is completely different:
    # We can measure overlap of characters or length difference
    # Let's check if the edit distance is large or if there's very little common chars.
    
    # Simple check: if they don't share any of the same vowels or first characters
    # Or if length of clean IPAs differ significantly, or standard edit distance.
    def edit_dist(s1, s2):
        if len(s1) < len(s2):
            return edit_dist(s2, s1)
        if len(s2) == 0:
            return len(s1)
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]

    dist = edit_dist(cleaned_db, cleaned_sug)
    max_len = max(len(cleaned_db), len(cleaned_sug), 1)
    ratio = dist / max_len
    
    # If distance ratio > 0.6, it is highly likely a wrong IPA (e.g. completely different word)
    if ratio > 0.6:
        bad_ipas.append({
            "word": word,
            "db_ipa": db_ipa,
            "suggested_ipa": f"/{suggested}/",
            "ratio": ratio
        })

print(f"Found {len(bad_ipas)} suspicious IPAs.")
with open('e:/Project/Hoc/hoc-tieng-anh/backend/scratch/suspicious_ipas.json', 'w', encoding='utf-8') as f:
    json.dump(bad_ipas, f, ensure_ascii=False, indent=2)

# Print first 20 suspicious
for i, item in enumerate(bad_ipas[:30]):
    print(f"{i+1}. {item['word']}: DB={item['db_ipa']} | Suggested={item['suggested_ipa']} (diff: {item['ratio']:.2f})")
