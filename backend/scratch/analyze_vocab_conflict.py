import sys
import os
import json

# Them thu muc hien tai (backend) vao path de import duoc app
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from app.db.session import SessionLocal
from app.models.models import Vocabulary

try:
    db = SessionLocal()
    all_vocabs = db.query(Vocabulary).all()
    
    all_words_lower = set(v.word.lower().strip() for v in all_vocabs)
    
    vocab_with_2 = []
    for v in all_vocabs:
        word_str = v.word.strip()
        if word_str.endswith('2') or word_str.endswith(' 2'):
            vocab_with_2.append(v)
            
    print(f"Tong so tu ket thuc bang 2: {len(vocab_with_2)}")
    
    no_conflict_clean = []
    conflict_clean = []
    
    for v in vocab_with_2:
        # Lay tu goc bang cach loai bo '2' o cuoi
        word_str = v.word.strip()
        if word_str.endswith(' 2'):
            clean_word = word_str[:-2].strip()
        else:
            clean_word = word_str[:-1].strip()
            
        if clean_word.lower() not in all_words_lower:
            no_conflict_clean.append((v, clean_word))
        else:
            conflict_clean.append((v, clean_word))
            
    print(f"So tu khong bi xung dot khi bo 2: {len(no_conflict_clean)}")
    print(f"So tu bi xung dot (da ton tai tu goc khong co 2): {len(conflict_clean)}")
    
    if conflict_clean:
        print("Cac tu bi xung dot:")
        for v, clean in conflict_clean:
            print(f"- '{v.word}' -> '{clean}' (Da ton tai trong DB)")
            
    db.close()
except Exception as e:
    print("Error:", e)
