import sys
import os
import json

# Them thu muc hien tai (backend) vao path de import duoc app
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from app.db.session import SessionLocal
from app.models.models import Vocabulary

try:
    db = SessionLocal()
    # Tim tat ca tu vung
    all_vocabs = db.query(Vocabulary).all()
    print(f"Tong so tu vung trong DB: {len(all_vocabs)}")
    
    vocab_with_2 = []
    all_words = set(v.word.lower().strip() for v in all_vocabs)
    
    for v in all_vocabs:
        word_str = v.word.strip()
        # Kiem tra ket thuc bang '2' hoac ' 2'
        if word_str.endswith('2') or word_str.endswith(' 2'):
            vocab_with_2.append({
                "id": v.id,
                "word": v.word,
                "ipa": v.ipa,
                "meaning": v.meaning,
                "level": v.level,
                "example": v.example,
                "topic": v.topic
            })
            
    print(f"Tim thay {len(vocab_with_2)} tu ket thuc bang 2")
    
    # Ghi vao file json
    output_path = os.path.join(os.path.dirname(__file__), "vocab_with_2.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(vocab_with_2, f, ensure_ascii=False, indent=4)
        
    print(f"Da ghi ket qua vao {output_path}")
        
    db.close()
except Exception as e:
    print("Error querying database:", e)
