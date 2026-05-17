from fastapi import APIRouter, UploadFile, File, Form, Query, Response
from fastapi.responses import StreamingResponse
from app.services.pronunciation_service import pronunciation_service, PRACTICE_SENTENCES
from app.db.session import SessionLocal
from app.models.models import PronunciationSession, PronunciationScore, UserSkillLevel
from app.schemas.pronunciation import (
    PronunciationAnalysisResponse,
    PronunciationHistoryResponse,
    PronunciationAnalyticsResponse,
    PronunciationSessionSchema,
    PronunciationMetricSchema,
    PracticeSentenceSchema,
)
from sqlalchemy import desc, func
from typing import Optional
import os
import edge_tts

router = APIRouter()

@router.get("/tts")
async def generate_azure_tts(
    text: str = Query(..., description="Text to synthesize (bilingual supported)"),
    voice: str = Query(default="en-US-AvaMultilingualNeural", description="Azure Neural Voice")
):
    import re
    
    try:
        # 1. Làm sạch sơ bộ
        text = re.sub(r'/[^/]+/', '', text) # Xóa IPA
        # Loại bỏ tất cả emoji (dải Unicode) để ngăn TTS đọc tên emoji như "đinh ghim tròn"
        text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
        # Loại bỏ các ký hiệu đặc biệt khác và thẻ cảnh báo
        text = re.sub(r'[❌✅💡📝🗣️😊👍🌟💪✨🎉👏📊📌📍⚠️•|*#\-]', '', text)
        
        # 2. Tách văn bản thành các câu đơn lẻ để phân đoạn ngôn ngữ chuẩn xác
        sentences = re.split(r'(?<=[.?!])\s+|\n+', text)
        raw_parts = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            last_idx = 0
            # Tìm các cụm từ tiếng Anh bọc trong nháy đơn, nháy kép hoặc ngoặc kép nổi bật
            for match in re.finditer(r"['\"“]([^'\"“”]+)['\"”]", sentence):
                before = sentence[last_idx:match.start()].strip()
                if before:
                    lang = "vi" if re.search(r'[À-ỹ]', before) else "en"
                    raw_parts.append({"text": before, "lang": lang})
                
                inside = match.group(1).strip()
                if inside:
                    raw_parts.append({"text": inside, "lang": "en"})
                
                last_idx = match.end()
                
            remaining = sentence[last_idx:].strip()
            if remaining:
                lang = "vi" if re.search(r'[À-ỹ]', remaining) else "en"
                raw_parts.append({"text": remaining, "lang": lang})

        if not raw_parts:
            raw_parts = [{"text": text, "lang": "vi"}]
 
        # 3. Gộp các phần cùng ngôn ngữ liên tiếp để giảm số lượng request tới server TTS
        parts = []
        if raw_parts:
            current_part = raw_parts[0]
            for next_part in raw_parts[1:]:
                if next_part["lang"] == current_part["lang"]:
                    current_part["text"] += " " + next_part["text"]
                else:
                    parts.append(current_part)
                    current_part = next_part
            parts.append(current_part)
 
        # 4. Tổng hợp âm thanh đa giọng đọc chuyên biệt
        raw_pcm_data = bytearray()
        
        for part in parts:
            p_text = part["text"]
            p_lang = part["lang"]
            
            # Bỏ qua nếu text chỉ chứa ký tự đặc biệt/trống
            if not re.search(r'[a-zA-ZÀ-ỹ0-9]', p_text):
                continue
 
            if p_lang == "vi":
                v_name = "vi-VN-HoaiMyNeural"
                p_rate = "+0%"
            else:
                # Sử dụng giọng đọc chuẩn Anh-Anh (British English) cực kỳ quý phái, rõ ràng, dễ nghe
                v_name = "en-GB-SoniaNeural"
                p_rate = "-5%" # Độ chậm vừa phải để học viên nghe rõ
            
            print(f"DEBUG Hybrid TTS (PCM): [{p_lang}] {p_text}")
            
            try:
                communicate = edge_tts.Communicate(p_text, v_name, rate=p_rate)
                audio_data = b""
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_data += chunk["data"]
                
                # Lọc bỏ ID3 tag để ghép nối MP3 mượt mà
                if audio_data.startswith(b"ID3"):
                    size_bytes = audio_data[6:10]
                    tag_size = (size_bytes[0] << 21) | (size_bytes[1] << 14) | (size_bytes[2] << 7) | size_bytes[3]
                    total_id3_size = 10 + tag_size
                    audio_data = audio_data[total_id3_size:]
                    
                raw_pcm_data.extend(audio_data)
            except Exception as inner_e:
                print(f"WARN: edge_tts failed for part '{p_text}': {inner_e}")
                continue

        if not raw_pcm_data:
            return Response(content=b"", status_code=204)

        return Response(content=bytes(raw_pcm_data), media_type="audio/mpeg")

        
    except Exception as e:
        print(f"TTS Error: {e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))


# Thư mục lưu audio uploads
AUDIO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "audio_uploads")
os.makedirs(AUDIO_DIR, exist_ok=True)


@router.post("/analyze", response_model=PronunciationAnalysisResponse)
async def analyze_pronunciation(
    audio: UploadFile = File(...),
    target_text: str = Form(...),
    user_id: int = Form(default=1),
):
    """
    Upload audio + target_text → Gemini phân tích pronunciation → trả về scores.
    """
    # Đọc audio bytes
    audio_bytes = await audio.read()

    # Lưu audio file
    audio_filename = f"user_{user_id}_{audio.filename}"
    audio_path = os.path.join(AUDIO_DIR, audio_filename)
    with open(audio_path, "wb") as f:
        f.write(audio_bytes)

    # Gọi pronunciation service (Gemini-powered)
    result = await pronunciation_service.analyze_pronunciation(
        audio_bytes=audio_bytes,
        target_text=target_text,
        audio_filename=audio.filename or "audio.webm",
    )

    # Lưu vào database
    db = SessionLocal()
    try:
        session = PronunciationSession(
            user_id=user_id,
            target_text=target_text,
            transcribed_text=result["transcribed_text"],
            audio_path=audio_path,
            overall_score=result["overall_score"],
        )
        db.add(session)
        db.flush()

        # Lưu từng metric score
        for metric_data in result["metrics"]:
            score = PronunciationScore(
                session_id=session.id,
                metric=metric_data["metric"],
                score=metric_data["score"],
                feedback=metric_data["feedback"],
            )
            db.add(score)

        db.commit()
        db.refresh(session)

        # Cập nhật UserSkillLevel dựa trên kết quả mới
        skill_level = db.query(UserSkillLevel).filter(UserSkillLevel.user_id == user_id).first()
        if skill_level:
            # Thuật toán đơn giản: Moving average (70% cũ, 30% mới)
            def update_score(old, new):
                return round((old * 0.7) + (new * 0.3), 1)

            for m in result["metrics"]:
                if m["metric"] == "pronunciation":
                    skill_level.pronunciation = update_score(skill_level.pronunciation, m["score"])
                elif m["metric"] == "fluency":
                    skill_level.fluency = update_score(skill_level.fluency, m["score"])
                elif m["metric"] == "intonation":
                    skill_level.intonation = update_score(skill_level.intonation, m["score"])
            
            # Cập nhật vocabulary ngẫu nhiên nhẹ dựa trên độ khó của text
            if len(target_text.split()) > 10:
                skill_level.vocabulary = min(100.0, skill_level.vocabulary + 0.5)
            
            db.commit()

        print(f"DEBUG: Returning analysis result for session {session.id}: {result['overall_score']}")
        
        response_data = PronunciationAnalysisResponse(
            session_id=session.id,
            overall_score=result["overall_score"],
            target_text=target_text,
            transcribed_text=result["transcribed_text"],
            metrics=[PronunciationMetricSchema(**m) for m in result["metrics"]],
            word_scores=result["word_scores"],
            feedback=result["feedback"],
        )
        return response_data
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


@router.get("/history/{user_id}", response_model=PronunciationHistoryResponse)
async def get_pronunciation_history(user_id: int, limit: int = Query(default=20, le=100)):
    """
    Lấy lịch sử pronunciation sessions của user.
    """
    db = SessionLocal()
    try:
        sessions = (
            db.query(PronunciationSession)
            .filter(PronunciationSession.user_id == user_id)
            .order_by(desc(PronunciationSession.created_at))
            .limit(limit)
            .all()
        )

        session_schemas = []
        for s in sessions:
            scores = db.query(PronunciationScore).filter(PronunciationScore.session_id == s.id).all()
            session_schemas.append(PronunciationSessionSchema(
                id=s.id,
                target_text=s.target_text,
                transcribed_text=s.transcribed_text,
                overall_score=s.overall_score,
                created_at=s.created_at,
                metrics=[PronunciationMetricSchema(
                    metric=sc.metric,
                    score=sc.score,
                    feedback=sc.feedback or "",
                ) for sc in scores],
            ))

        total = db.query(PronunciationSession).filter(PronunciationSession.user_id == user_id).count()
        avg_score = db.query(func.avg(PronunciationSession.overall_score)).filter(
            PronunciationSession.user_id == user_id
        ).scalar() or 0.0

        return PronunciationHistoryResponse(
            sessions=session_schemas,
            total_sessions=total,
            average_score=round(float(avg_score), 1),
        )
    finally:
        db.close()


@router.get("/analytics/{user_id}", response_model=PronunciationAnalyticsResponse)
async def get_pronunciation_analytics(user_id: int):
    """
    Thống kê tổng hợp voice analytics.
    """
    db = SessionLocal()
    try:
        total = db.query(PronunciationSession).filter(PronunciationSession.user_id == user_id).count()

        if total == 0:
            return PronunciationAnalyticsResponse(
                total_sessions=0,
                average_overall=0.0,
                average_fluency=0.0,
                average_pronunciation=0.0,
                average_confidence=0.0,
                average_intonation=0.0,
                recent_trend="stable",
                best_score=0.0,
                practice_streak=0,
            )

        avg_overall = db.query(func.avg(PronunciationSession.overall_score)).filter(
            PronunciationSession.user_id == user_id
        ).scalar() or 0.0

        best_score = db.query(func.max(PronunciationSession.overall_score)).filter(
            PronunciationSession.user_id == user_id
        ).scalar() or 0.0

        # Tính average cho từng metric
        def get_avg_metric(metric_name: str) -> float:
            result = (
                db.query(func.avg(PronunciationScore.score))
                .join(PronunciationSession)
                .filter(
                    PronunciationSession.user_id == user_id,
                    PronunciationScore.metric == metric_name,
                )
                .scalar()
            )
            return round(float(result or 0.0), 1)

        # Xác định trend: so sánh 5 sessions gần nhất vs 5 trước đó
        recent = (
            db.query(PronunciationSession.overall_score)
            .filter(PronunciationSession.user_id == user_id)
            .order_by(desc(PronunciationSession.created_at))
            .limit(5)
            .all()
        )
        older = (
            db.query(PronunciationSession.overall_score)
            .filter(PronunciationSession.user_id == user_id)
            .order_by(desc(PronunciationSession.created_at))
            .offset(5)
            .limit(5)
            .all()
        )

        trend = "stable"
        if recent and older:
            recent_avg = sum(r[0] for r in recent) / len(recent)
            older_avg = sum(r[0] for r in older) / len(older)
            if recent_avg > older_avg + 5:
                trend = "improving"
            elif recent_avg < older_avg - 5:
                trend = "declining"

        return PronunciationAnalyticsResponse(
            total_sessions=total,
            average_overall=round(float(avg_overall), 1),
            average_fluency=get_avg_metric("fluency"),
            average_pronunciation=get_avg_metric("pronunciation"),
            average_confidence=get_avg_metric("confidence"),
            average_intonation=get_avg_metric("intonation"),
            recent_trend=trend,
            best_score=round(float(best_score), 1),
            practice_streak=total,  # Simplified: count total as streak
        )
    finally:
        db.close()


@router.get("/sentences", response_model=list[PracticeSentenceSchema])
async def get_practice_sentences(
    level: Optional[str] = Query(default=None, description="Filter by level: A1, A2, B1, B2"),
    category: Optional[str] = Query(default=None, description="Filter by category"),
):
    """
    Lấy danh sách câu luyện tập theo level/category.
    """
    sentences = PRACTICE_SENTENCES
    if level:
        sentences = [s for s in sentences if s["level"] == level.upper()]
    if category:
        sentences = [s for s in sentences if s["category"] == category.lower()]
    return [PracticeSentenceSchema(**s) for s in sentences]
