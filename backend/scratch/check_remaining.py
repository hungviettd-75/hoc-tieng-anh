import sys
import os

sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.models import Vocabulary, Lesson, VocabularyGame, VocabularyAttempt, VocabularyWrongAnswer, VocabularyMasteredWord, VocabularyMemory

print("DATABASE URI:", settings.SQLALCHEMY_DATABASE_URI)

try:
    db = SessionLocal()
    
    # 1. Kiem tra bang Vocabulary
    vocabs = db.query(Vocabulary).all()
    v_count = 0
    for v in vocabs:
        if v.word.strip().endswith('2'):
            print(f"[Vocabulary] ID: {v.id}, Word: '{v.word}'")
            v_count += 1
            
    # 2. Kiem tra bang Lesson (co the co content_data co chua tu ket thuc bang 2)
    lessons = db.query(Lesson).all()
    l_count = 0
    for l in lessons:
        # content_data la JSON
        data_str = str(l.content_data)
        if " 2" in data_str or "2'" in data_str or "2\"" in data_str:
            print(f"[Lesson] ID: {l.id}, Title: '{l.title}' co chua '2' trong content_data")
            l_count += 1
            
    # 3. Kiem tra bang VocabularyWrongAnswer
    wrong_answers = db.query(VocabularyWrongAnswer).all()
    wa_count = 0
    for wa in wrong_answers:
        if wa.word.strip().endswith('2'):
            print(f"[VocabularyWrongAnswer] ID: {wa.id}, Word: '{wa.word}'")
            wa_count += 1
            
    # 4. Kiem tra bang VocabularyMasteredWord
    mastered = db.query(VocabularyMasteredWord).all()
    m_count = 0
    for m in mastered:
        if m.word.strip().endswith('2'):
            print(f"[VocabularyMasteredWord] ID: {m.id}, Word: '{m.word}'")
            m_count += 1
            
    # 5. Kiem tra bang VocabularyMemory
    memories = db.query(VocabularyMemory).all()
    mem_count = 0
    for mem in memories:
        if mem.word.strip().endswith('2'):
            print(f"[VocabularyMemory] ID: {mem.id}, Word: '{mem.word}'")
            mem_count += 1

    print(f"\nKET QUA CON LAI:")
    print(f"- Vocabulary: {v_count}")
    print(f"- Lesson content: {l_count}")
    print(f"- VocabularyWrongAnswer: {wa_count}")
    print(f"- VocabularyMasteredWord: {m_count}")
    print(f"- VocabularyMemory: {mem_count}")
    
    db.close()
except Exception as e:
    print("Error:", e)
