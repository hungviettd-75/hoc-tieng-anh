from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.services.ai_service import gemini_service
from app.services.memory_service import memory_service
from app.services.ai_router import ai_router
from app.services.conversation_memory import conversation_memory
from app.services.vietnamese_tutor_engine import vietnamese_tutor
from app.db.session import SessionLocal
from app.models.models import Conversation, Message as DBMessage, PronunciationSession, PronunciationScore, ActivityLog, User
from app.api import deps
from sqlalchemy.orm import Session
from pydantic import BaseModel
import json
import asyncio
import time

class RoleplaySessionCreate(BaseModel):
    duration_minutes: int
    sentence_count: int
    pronunciation_errors_count: int
    grammar_errors_count: int
    pronunciation_score: float
    fluency_score: float
    confidence_score: float
    topic: str
    level: str

router = APIRouter()

@router.post("/roleplay/session")
def save_roleplay_session(
    session_data: RoleplaySessionCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    # 1. Tạo PronunciationSession
    overall = (session_data.pronunciation_score + session_data.fluency_score + session_data.confidence_score) / 3.0
    db_session = PronunciationSession(
        user_id=current_user.id,
        target_text=f"Roleplay topic: {session_data.topic}",
        transcribed_text=f"Completed {session_data.level} roleplay on topic '{session_data.topic}'",
        overall_score=overall
    )
    db.add(db_session)
    db.flush() # Để lấy db_session.id
    
    # 2. Tạo PronunciationScores
    metrics = [
        ("pronunciation", session_data.pronunciation_score, "Phát âm trong buổi nhập vai."),
        ("fluency", session_data.fluency_score, "Độ lưu loát khi nhập vai."),
        ("confidence", session_data.confidence_score, "Độ tự tin khi luyện nói.")
    ]
    for metric, score, feedback in metrics:
        db_score = PronunciationScore(
            session_id=db_session.id,
            metric=metric,
            score=score,
            feedback=feedback
        )
        db.add(db_score)
        
    # 3. Tạo ActivityLog
    # Tính toán XP thực tế dựa trên đóng góp & nỗ lực thực tế của học viên:
    # - Mỗi câu nói (sentence_count) hoàn chỉnh: +6 XP (học viên phải động não và phát âm)
    # - Mỗi phút học (duration_minutes): +5 XP
    # - Phạt nhẹ dựa trên lỗi sai nhưng đảm bảo vẫn khuyến khích: -1 XP cho mỗi lỗi ngữ pháp/phát âm
    # - Thưởng điểm chất lượng nếu điểm trung bình phát âm/lưu loát/tự tin > 80: +20 XP
    # - Giới hạn: Tối thiểu 15 XP (nếu có tham gia), Tối đa 150 XP.
    base_xp = 10
    sentence_xp = session_data.sentence_count * 6
    duration_xp = session_data.duration_minutes * 5
    penalty_xp = (session_data.pronunciation_errors_count + session_data.grammar_errors_count) * 1
    
    quality_bonus = 0
    if overall > 80.0:
        quality_bonus = 20
        
    xp_calculated = base_xp + sentence_xp + duration_xp - penalty_xp + quality_bonus
    xp_earned = max(15, min(150, xp_calculated))
    
    db_activity = ActivityLog(
        user_id=current_user.id,
        activity_type="roleplay",
        duration_minutes=session_data.duration_minutes,
        xp_earned=xp_earned
    )
    db.add(db_activity)
    
    # 4. Cộng XP cho User
    from app.services.gamification_service import gamification_service
    user_xp, leveled_up = gamification_service.add_xp(db, current_user.id, xp_earned)
    
    # 5. Cập nhật UserSkillLevel của User dựa trên buổi học thực tế
    skill_level = db.query(UserSkillLevel).filter(UserSkillLevel.user_id == current_user.id).first()
    if not skill_level:
        skill_level = UserSkillLevel(
            user_id=current_user.id,
            vocabulary=30.0,
            grammar=30.0,
            pronunciation=30.0,
            listening=30.0,
            fluency=30.0
        )
        db.add(skill_level)
        db.flush()
    
    # Cập nhật theo moving average (70% cũ, 30% mới) để phản ánh đúng thực tế
    def update_score(old, new):
        return round((old * 0.7) + (new * 0.3), 1)
        
    skill_level.pronunciation = update_score(skill_level.pronunciation, session_data.pronunciation_score)
    skill_level.fluency = update_score(skill_level.fluency, session_data.fluency_score)
    # Ngữ pháp (grammar): có thể ước lượng tăng nhẹ hoặc giảm nhẹ tùy lỗi sai
    # Nếu grammar_errors_count ít thì nâng grammar skill lên
    if session_data.sentence_count > 0:
        grammar_performance = (100.0 - (session_data.grammar_errors_count * 10.0 / session_data.sentence_count * 10.0)).clamp(50.0, 100.0) if hasattr(float, 'clamp') else max(50.0, min(100.0, 100.0 - (session_data.grammar_errors_count / session_data.sentence_count) * 100.0))
        skill_level.grammar = update_score(skill_level.grammar, grammar_performance)
        # Nâng nhẹ từ vựng
        skill_level.vocabulary = min(100.0, skill_level.vocabulary + 0.3)
        # Nâng nhẹ kĩ năng nghe do nghe AI nói
        skill_level.listening = min(100.0, skill_level.listening + 0.2)
        
    db.commit()
    
    return {
        "message": "Saved roleplay session successfully",
        "session_id": db_session.id,
        "xp_earned": xp_earned,
        "total_xp": user_xp.total_xp,
        "level": user_xp.level,
        "leveled_up": leveled_up
    }



class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_json(self, data: dict, websocket: WebSocket):
        async with self._lock:
            try:
                await websocket.send_json(data)
            except Exception as e:
                print(f"DEBUG: Error sending JSON: {e}")
                self.disconnect(websocket)

manager = ConnectionManager()

VOCAB_LISTS = {
    "A1": ["Beginner", "Practice", "Vocabulary", "Improve", "Welcome", "Language", "Simple", "Friend", "Happy", "Learn", "Family", "Morning", "School", "Summer", "Active"],
    "A2": ["Journey", "Confident", "Habit", "Encourage", "Positive", "Healthy", "Creative", "Success", "Goal", "Experience", "Patient", "Support", "Believe", "Method", "Imagine"],
    "B1": ["Persistent", "Collaborate", "Effective", "Challenge", "Achieve", "Determine", "Essential", "Progress", "Valuable", "Optimize", "Dynamic", "Strategy", "Productive", "Opportunity", "Flexibly"],
    "B2": ["Substantial", "Fluency", "Analyze", "Evaluate", "Alternative", "Consequence", "Significant", "Distinguish", "Innovative", "Perspective", "Professional", "Sustainable", "Coherent", "Efficient", "Implement"],
    "C1": ["Pragmatic", "Eloquent", "Cognitive", "Sophisticated", "Ambiguous", "Comprehensive", "Ephemeral", "Inevitable", "Paradigm", "Resilient", "Ubiquitous", "Volatile", "Aesthetic", "Paradox", "Synthesis"],
}

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    user_id: int,
    mode: str = None,
    level: str = None,
    topic: str = None,
    words: str = None
):
    # Ensure query parameters are parsed robustly from websocket.query_params
    query_params = websocket.query_params
    if not mode or mode == "null" or mode == "None":
        mode = query_params.get("mode")
    if not level or level == "null" or level == "None":
        level = query_params.get("level")
    if not topic or topic == "null" or topic == "None":
        topic = query_params.get("topic")
    if not words or words == "null" or words == "None":
        words = query_params.get("words")

    if mode == "null" or mode == "None": mode = None
    if level == "null" or level == "None": level = None
    if topic == "null" or topic == "None": topic = None
    if words == "null" or words == "None": words = None

    print(f"DEBUG: New WebSocket connection for user_id: {user_id}, mode: {mode}, level: {level}, topic: {topic}, words: {words}")
    try:
        with open("connection_log.txt", "a", encoding="utf-8") as f:
            f.write(f"New TEXT WebSocket: mode={mode}, level={level}, topic={topic}, words={words}\n")
    except Exception as log_e:
        print(f"DEBUG log error: {log_e}")
    await manager.connect(websocket)
    
    # Bắt buộc dọn dẹp bộ nhớ hội thoại cũ của user để đảm bảo mỗi lần mở lại phòng là một session mới tươi nguyên, 100% hiện giới thiệu tiếng Việt dẫn dắt!
    conversation_memory.clear(user_id)
    
    # Khởi tạo history hội thoại cho session này
    history = []
    
    # Cấu hình custom System Instruction tùy theo chế độ
    custom_instruction = None
    welcome_prompt = None

    if mode == "vocabulary_practice" and level:
        if words:
            vocab_words = [w.strip() for w in words.split(",") if w.strip()]
        else:
            vocab_words = VOCAB_LISTS.get(level.upper(), VOCAB_LISTS["B1"])
        words_str = ", ".join([f"'{w}'" for w in vocab_words])
        numbered_words = "\n".join([f"   Từ {i+1}: {w}" for i, w in enumerate(vocab_words)])
        custom_instruction = (
            "Bạn là AI English Coach chuyên hỗ trợ học viên Luyện tập Từ vựng Thông minh.\n"
            f"DANH SÁCH TỪ VỰNG BẮT BUỘC (trình độ {level}) - CHỈ DẠY CÁC TỪ NÀY, TUYỆT ĐỐI KHÔNG DẠY TỪ NÀO KHÁC:\n"
            f"{numbered_words}\n"
            f"\nTổng cộng: {len(vocab_words)} từ vựng.\n"
            "\nQUY TẮC DẪN DẮT NGHIÊM NGẶT:\n"
            "1. CHỈ DẠY CÁC TỪ TRONG DANH SÁCH TRÊN. TUYỆT ĐỐI CẤM giới thiệu, dạy, hoặc yêu cầu học viên đọc bất kỳ từ nào KHÔNG có trong danh sách trên. Đây là quy tắc quan trọng nhất.\n"
            "2. HỌC TỪNG TỪ MỘT THEO ĐÚNG THỨ TỰ: Bắt đầu từ Từ 1, rồi Từ 2, Từ 3... Tuyệt đối không nhảy cóc hay thay đổi thứ tự.\n"
            "3. ĐỐI VỚI MỖI TỪ:\n"
            "   - Bước 1: Giới thiệu từ vựng, phiên âm IPA, nghĩa tiếng Việt và đặt 1 câu ví dụ siêu ngắn.\n"
            "   - Bước 2: Yêu cầu học viên phát âm từ vựng đó.\n"
            "   - Bước 3: Nhận xét ngắn gọn về phát âm của học viên, giải thích nhanh cách sử dụng thực tế (nếu cần), rồi giới thiệu từ tiếp theo trong danh sách.\n"
            "4. LUÔN GIAO TIẾP BẰNG TIẾNG VIỆT thân thiện, ngắn gọn (tối đa 2-3 câu mỗi lượt).\n"
            f"5. KẾT THÚC BUỔI HỌC: Khi đã dạy HẾT tất cả {len(vocab_words)} từ trong danh sách (sau khi học viên phát âm xong từ cuối cùng), "
            "bạn PHẢI tổng kết buổi học bằng cách: khen ngợi học viên, tóm tắt ngắn gọn các từ đã học, và nói 'Buổi học hôm nay hoàn thành! 🎉'. "
            "TUYỆT ĐỐI KHÔNG quay lại dạy từ đã dạy rồi.\n"
            "6. KHÔNG BAO GIỜ yêu cầu học viên phát âm lại một từ đã dạy xong ở bước trước. Mỗi từ chỉ được dạy MỘT LẦN DUY NHẤT."
        )
        welcome_prompt = (
            f"Hãy chào đón học viên bằng Tiếng Việt thân thiện, nói hôm nay sẽ học {len(vocab_words)} từ vựng trình độ {level}. "
            f"Sau đó, giới thiệu ngay TỪ ĐẦU TIÊN là '{vocab_words[0]}' (kèm phiên âm IPA, nghĩa tiếng Việt, 1 câu ví dụ ngắn) và yêu cầu học viên đọc to từ '{vocab_words[0]}' để bắt đầu. "
            f"CHÚ Ý: Từ đầu tiên BẮT BUỘC phải là '{vocab_words[0]}', KHÔNG ĐƯỢC dạy từ nào khác."
        )
    elif mode == "roleplay" and topic:
        # Dynamic Scenario Generator: AI tự sáng tạo bối cảnh đa dạng mỗi lần học
        level_tag = f" (trình độ {level})" if level else ""
        custom_instruction = (
            f"Bạn là AI chuyên gia nhập vai tiếng Anh{level_tag} trong chủ đề: '{topic}'.\n"
            "QUY TẮC SÁNG TẠO BỐI CẢNH ĐỘNG:\n"
            "1. MỖI LẦN HỌC, bạn PHẢI TỰ SÁNG TẠO một bối cảnh nhập vai HOÀN TOÀN MỚI và KHÁC BIỆT liên quan đến chủ đề.\n"
            "   - TUYỆT ĐỐI KHÔNG lặp lại kịch bản cũ hay dùng template cố định.\n"
            "   - Hãy sáng tạo các tình huống thực tế, bất ngờ, thú vị (ví dụ: cùng chủ đề Du lịch nhưng lần này có thể là check-in khách sạn, lần khác là mua vé tàu, lần khác là hỏi đường tại Tokyo...).\n"
            "2. Bạn tự chọn vai trò phù hợp cho mình VÀ cho học viên dựa trên bối cảnh đã sáng tạo.\n"
            "3. GIAO TIẾP CHỦ YẾU BẰNG TIẾNG ANH (ngắn gọn, 1-2 câu mỗi lượt) để kéo học viên vào vai diễn.\n"
            "4. Hỗ trợ sư phạm: Nếu học viên nói sai ngữ pháp hoặc phát âm, bạn có thể kèm giải thích/gợi ý ngắn gọn bằng Tiếng Việt ở cuối câu thoại.\n"
            "5. Hãy dẫn dắt tình huống tự nhiên, đặt câu hỏi hoặc đưa ra gợi mở để thúc đẩy cuộc hội thoại.\n"
            f"6. QUY TẮC BÁM SÁT CHỦ ĐỀ (TUYỆT ĐỐI TUÂN THỦ):\n"
            f"   - TOÀN BỘ buổi học phải xoay quanh CHỦ ĐỀ DUY NHẤT: '{topic}'.\n"
            f"   - TUYỆT ĐỐI KHÔNG được tự ý chuyển sang chủ đề khác dù học viên nói gì.\n"
            f"   - Nếu học viên đi lạc đề, hãy nhẹ nhàng kéo họ quay lại chủ đề '{topic}' bằng một câu hỏi mới liên quan.\n"
            f"   - Hãy khai thác sâu nhiều khía cạnh khác nhau TRONG chủ đề '{topic}' (ví dụ: đặt phòng, hỏi giá, yêu cầu dịch vụ, than phiền, thanh toán...) thay vì nhảy sang chủ đề ngoài.\n"
            "7. QUY TẮC CHỦ ĐỘNG TƯƠNG TÁC (BẮT BUỘC):\n"
            "   - SAU MỖI CÂU TRẢ LỜI CỦA HỌC VIÊN, bạn BẮT BUỘC phải phản hồi VÀ đặt thêm 1 câu hỏi tiếp theo hoặc đưa ra tình huống mới trong cùng chủ đề để cuộc hội thoại KHÔNG BAO GIỜ bị ngắt quãng.\n"
            "   - TUYỆT ĐỐI KHÔNG chỉ trả lời rồi im lặng. Luôn kết thúc lượt thoại bằng 1 câu hỏi hoặc 1 gợi mở mới.\n"
            "   - HỖ TRỢ KHI BẾ TẮC: Nếu học viên nói 'I don't know', im lặng hoặc bế tắc, bạn BẮT BUỘC phải nói 1 câu Tiếng Việt động viên nồng ấm, gợi ý 1-2 câu trả lời mẫu Tiếng Anh đơn giản kèm dịch Tiếng Việt, hoặc chuyển sang 1 tình huống mới dễ hơn TRONG CÙNG CHỦ ĐỀ."
        )
        welcome_prompt = (
            f"Học viên vừa chọn chủ đề nhập vai: '{topic}'{level_tag}.\n"
            "BẮT BUỘC THỰC HIỆN THEO ĐÚNG THỨ TỰ SAU (KHÔNG ĐƯỢC BỎ QUA BƯỚC NÀO):\n"
            "BƯỚC 1 - CHÀO HỌC VIÊN: Nói 1 câu tiếng Việt chào mừng nồng ấm, xác nhận chủ đề hôm nay.\n"
            "   Ví dụ: 'Chào bạn! Hôm nay chúng ta sẽ cùng luyện chủ đề Du lịch nhé! 🌍✈️'\n"
            "BƯỚC 2 - GIỚI THIỆU MỤC TIÊU: Nói bằng tiếng Việt 1-2 câu ngắn về mục tiêu buổi học.\n"
            "   Ví dụ: 'Mục tiêu hôm nay: Luyện giao tiếp tự nhiên khi check-in khách sạn, hỏi giá phòng và yêu cầu dịch vụ.'\n"
            "BƯỚC 3 - TẠO BỐI CẢNH MỚI: Sáng tạo 1 bối cảnh nhập vai CỤ THỂ, SINH ĐỘNG, KHÔNG LẶP LẠI.\n"
            "   - Mô tả ngắn gọn bối cảnh bằng tiếng Việt (địa điểm, thời gian, hoàn cảnh cụ thể).\n"
            "   - Nêu rõ VAI TRÒ của AI (ví dụ: lễ tân khách sạn 5 sao, đầu bếp Ý, hướng dẫn viên du lịch...).\n"
            "   - Nêu rõ VAI TRÒ của học viên (ví dụ: khách du lịch, khách hàng VIP, ứng viên xin việc...).\n"
            "BƯỚC 4 - CÂU MỞ ĐẦU SONG NGỮ (BẮT BUỘC VỪA TIẾNG VIỆT VỪA TIẾNG ANH):\n"
            "   a) Nói 1 câu Tiếng Việt động viên thân thiện để học viên tự tin, ví dụ: 'Bạn cứ thoải mái nhé, mình sẽ bắt đầu trước! 😊'\n"
            "   b) Đưa ra câu thoại Tiếng Anh đầu tiên (1 câu ngắn gọn) của vai diễn AI.\n"
            "   c) Kèm ngay bản dịch Tiếng Việt trong ngoặc đơn dạng '(Dịch: ...)' để học viên hiểu ý nghĩa.\n"
            "   d) Gợi ý 1-2 câu trả lời mẫu siêu đơn giản bằng Tiếng Anh kèm dịch Tiếng Việt để học viên có thể bắt chước nói theo ngay.\n"
            "   Ví dụ chuẩn: 'Bạn cứ thoải mái nhé, mình bắt đầu trước! 😊 Good evening! Welcome to our hotel. Do you have a reservation? (Dịch: Chào buổi tối! Chào mừng đến khách sạn. Bạn đã đặt phòng chưa?) 💡 Bạn có thể trả lời: \"Yes, I have a reservation.\" (Dịch: \"Vâng, tôi đã đặt phòng.\")'\n"
            "TUYỆT ĐỐI KHÔNG viết thêm gợi ý dài dòng hay giải thích luật chơi. Chỉ thực hiện đúng 4 bước trên."
        )
    elif mode == "free_talk":
        custom_instruction = (
            "Bạn là AI English Coach đàm thoại tự do bằng Tiếng Anh.\n"
            "QUY TẮC:\n"
            "1. LUÔN đặt câu hỏi gợi mở ngắn gọn (1-2 câu tiếng Anh) để giữ lửa cuộc đàm thoại.\n"
            "2. Giải thích sư phạm: Bất cứ khi nào học viên nói sai ngữ pháp hoặc từ vựng, hãy chủ động sửa lỗi và giải thích chi tiết bằng Tiếng Việt ở cuối lượt thoại.\n"
            "3. Khuyến khích học viên bày tỏ quan điểm của mình."
        )
        welcome_prompt = (
            "Học viên vừa bắt đầu phòng luyện nói tự do. Hãy gửi lời chào bằng Tiếng Việt nồng ấm, "
            "giới thiệu bản thân là người bạn đồng hành luyện nói tiếng Anh và đưa ra 1 chủ đề giao tiếp gợi mở thú vị bằng Tiếng Anh."
        )

    try:
        # Nếu có welcome prompt (ở bất kỳ chế độ học động nào), chủ động gửi lời chào đầu tiên!
        if welcome_prompt:
            full_welcome = ""
            async for chunk in gemini_service.get_streaming_response(
                history=history, user_message=welcome_prompt, custom_instruction=custom_instruction
            ):
                full_welcome += chunk
                await websocket.send_json({
                    "type": "delta",
                    "role": "assistant",
                    "content": chunk
                })
            
            await websocket.send_json({
                "type": "completion",
                "role": "assistant",
                "content": full_welcome,
                "grammar_notes": ""
            })
            
            history.append({"role": "assistant", "content": full_welcome})

        while True:
            data = await websocket.receive_text()
            print(f"DEBUG: Received message from user {user_id}: {data}")
            
            message_data = json.loads(data)
            user_message = message_data.get("content", "")
            
            # Retrieve relevant memories
            print(f"DEBUG: Retrieving memories for user {user_id}...")
            memories = await memory_service.retrieve_relevant_memories(user_id=user_id, query=user_message)
            memory_context = "\n".join([f"- {m['text']}" for m in memories])
            
            context_prompt = user_message
            if memory_context:
                print(f"DEBUG: Memory context found: {len(memories)} items")
                context_prompt = f"Background info you remember about the user:\n{memory_context}\n\nUser: {user_message}"

            # === Step 1: Grammar check (runs in background) ===
            import asyncio
            async def get_grammar_corrections():
                try:
                    ai_corrections = await gemini_service.get_structured_correction(user_message)
                    if ai_corrections:
                        notes = []
                        for c in ai_corrections:
                            original = c.get("original", "")
                            correction = c.get("correction", "")
                            exp = c.get("explanation_vi", "")
                            notes.append(f"'{original}' -> '{correction}' ({exp})")
                        return "; ".join(notes)
                except Exception as e:
                    print(f"ERROR getting grammar corrections in ws: {e}")
                return ""
            
            correction_task = asyncio.create_task(get_grammar_corrections())

            # Streaming response from Gemini
            print(f"DEBUG: Starting Gemini streaming response...")
            full_response = ""
            async for chunk in gemini_service.get_streaming_response(
                history=history, user_message=context_prompt, custom_instruction=custom_instruction
            ):
                full_response += chunk
                await websocket.send_json({
                    "type": "delta",
                    "role": "assistant",
                    "content": chunk
                })
            
            print(f"DEBUG: Streaming finished. Full response length: {len(full_response)}")
            
            # Lưu vào history để duy trì ngữ cảnh
            history.append({"role": "user", "content": user_message})
            history.append({"role": "assistant", "content": full_response})
            
            # Giới hạn history (ví dụ 10 lượt gần nhất)
            if len(history) > 20:
                history = history[-20:]
            
            grammar_notes = await correction_task
            await websocket.send_json({
                "type": "completion",
                "role": "assistant",
                "content": full_response,
                "grammar_notes": grammar_notes
            })

            print(f"DEBUG: Completion sent to user {user_id}")
            
            # Lưu ký ức vào bộ nhớ dài hạn (Pinecone)
            if user_message.strip():
                print(f"DEBUG: Storing interaction in long-term memory for user {user_id}...")
                memory_text = f"User said: {user_message}. AI responded: {full_response}"
                asyncio.create_task(memory_service.store_memory(
                    user_id=user_id, 
                    text=memory_text, 
                    metadata={"type": "chat_interaction", "timestamp": time.time()}
                ))

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass
        manager.disconnect(websocket)

@router.websocket("/ws/realtime/{user_id}")
async def realtime_voice_endpoint(
    websocket: WebSocket, 
    user_id: int,
    mode: str = None,
    level: str = None,
    topic: str = None,
    words: str = None
):
    """
    WebSocket endpoint chuyên biệt cho trải nghiệm Voice Realtime.
    Smart Hybrid AI Pipeline:
    User Text → Local NLP → AI Router → (LLM nếu cần) → Vietnamese Tutor → Response
    """
    # Ensure query parameters are parsed robustly from websocket.query_params
    query_params = websocket.query_params
    if not mode or mode == "null" or mode == "None":
        mode = query_params.get("mode")
    if not level or level == "null" or level == "None":
        level = query_params.get("level")
    if not topic or topic == "null" or topic == "None":
        topic = query_params.get("topic")
    if not words or words == "null" or words == "None":
        words = query_params.get("words")

    if mode == "null" or mode == "None": mode = None
    if level == "null" or level == "None": level = None
    if topic == "null" or topic == "None": topic = None
    if words == "null" or words == "None": words = None

    if not mode:
        mode = "free_talk"
    print(f"DEBUG: New Realtime WebSocket connection for user_id: {user_id}, mode: {mode}, level: {level}, topic: {topic}, words: {words}")
    try:
        with open("connection_log.txt", "a", encoding="utf-8") as f:
            f.write(f"New REALTIME WebSocket: mode={mode}, level={level}, topic={topic}, words={words}\n")
    except Exception as log_e:
        print(f"DEBUG log error: {log_e}")
    await manager.connect(websocket)
    
    # Bắt buộc dọn dẹp bộ nhớ hội thoại cũ của user để đảm bảo mỗi lần mở lại phòng là một session mới tươi nguyên, 100% hiện giới thiệu tiếng Việt dẫn dắt!
    conversation_memory.clear(user_id)

    # Cấu hình custom System Instruction tùy theo chế độ
    custom_instruction = None
    welcome_prompt = None

    if mode == "vocabulary_practice" and level:
        if words:
            vocab_words = [w.strip() for w in words.split(",") if w.strip()]
        else:
            vocab_words = VOCAB_LISTS.get(level.upper(), VOCAB_LISTS["B1"])
        words_str = ", ".join([f"'{w}'" for w in vocab_words])
        numbered_words = "\n".join([f"   Từ {i+1}: {w}" for i, w in enumerate(vocab_words)])
        custom_instruction = (
            "Bạn là AI English Coach chuyên hỗ trợ học viên Luyện tập Từ vựng Thông minh.\n"
            f"DANH SÁCH TỪ VỰNG BẮT BUỘC (trình độ {level}) - CHỈ DẠY CÁC TỪ NÀY, TUYỆT ĐỐI KHÔNG DẠY TỪ NÀO KHÁC:\n"
            f"{numbered_words}\n"
            f"\nTổng cộng: {len(vocab_words)} từ vựng.\n"
            "\nQUY TẮC DẪN DẮT NGHIÊM NGẶT:\n"
            "1. CHỈ DẠY CÁC TỪ TRONG DANH SÁCH TRÊN. TUYỆT ĐỐI CẤM giới thiệu, dạy, hoặc yêu cầu học viên đọc bất kỳ từ nào KHÔNG có trong danh sách trên. Đây là quy tắc quan trọng nhất.\n"
            "2. HỌC TỪNG TỪ MỘT THEO ĐÚNG THỨ TỰ: Bắt đầu từ Từ 1, rồi Từ 2, Từ 3... Tuyệt đối không nhảy cóc hay thay đổi thứ tự.\n"
            "3. ĐỐI VỚI MỖI TỪ:\n"
            "   - Bước 1: Giới thiệu từ vựng, phiên âm IPA, nghĩa tiếng Việt và câu ví dụ cực ngắn.\n"
            "   - Bước 2: Yêu cầu học viên đọc to (phát âm) từ đó.\n"
            "   - Bước 3: Nhận xét ngắn gọn về phát âm của học viên, sau đó giới thiệu từ tiếp theo TRONG DANH SÁCH.\n"
            "4. LUÔN GIAO TIẾP BẰNG TIẾNG VIỆT ngắn gọn (tối đa 2 câu mỗi lượt để phù hợp với giao tiếp Voice).\n"
            f"5. KẾT THÚC BUỔI HỌC: Khi đã dạy HẾT tất cả {len(vocab_words)} từ trong danh sách (sau khi học viên phát âm xong từ cuối cùng), "
            "bạn PHẢI tổng kết buổi học bằng cách: khen ngợi học viên, tóm tắt ngắn gọn các từ đã học, và nói 'Buổi học hôm nay hoàn thành! 🎉'. "
            "TUYỆT ĐỐI KHÔNG quay lại dạy từ đã dạy rồi.\n"
            "6. KHÔNG BAO GIỜ yêu cầu học viên phát âm lại một từ đã dạy xong ở bước trước. Mỗi từ chỉ được dạy MỘT LẦN DUY NHẤT."
        )
        welcome_prompt = (
            f"Hãy gửi lời chào bằng Tiếng Việt siêu ngắn gọn (tối đa 1-2 câu), nói hôm nay sẽ học {len(vocab_words)} từ vựng trình độ {level}. "
            f"Sau đó giới thiệu TỪ ĐẦU TIÊN là '{vocab_words[0]}' (phiên âm IPA, nghĩa tiếng Việt, 1 câu ví dụ ngắn) và yêu cầu học viên phát âm từ '{vocab_words[0]}'. "
            f"CHÚ Ý: Từ đầu tiên BẮT BUỘC phải là '{vocab_words[0]}', KHÔNG ĐƯỢC dạy từ nào khác."
        )
    elif mode == "roleplay" and topic:
        # Dynamic Scenario Generator: AI tự sáng tạo bối cảnh đa dạng mỗi lần học
        level_tag = f" (trình độ {level})" if level else ""
        custom_instruction = (
            f"Bạn là AI chuyên gia nhập vai tiếng Anh{level_tag} trong chủ đề: '{topic}'.\n"
            "QUY TẮC SÁNG TẠO BỐI CẢNH ĐỘNG:\n"
            "1. MỖI LẦN HỌC, bạn PHẢI TỰ SÁNG TẠO một bối cảnh nhập vai HOÀN TOÀN MỚI và KHÁC BIỆT liên quan đến chủ đề.\n"
            "   - TUYỆT ĐỐI KHÔNG lặp lại kịch bản cũ hay dùng template cố định.\n"
            "   - Hãy sáng tạo các tình huống thực tế, bất ngờ, thú vị.\n"
            "2. Bạn tự chọn vai trò phù hợp cho mình VÀ cho học viên dựa trên bối cảnh đã sáng tạo.\n"
            "3. GIAO TIẾP CHỦ YẾU BẰNG TIẾNG ANH (ngắn gọn, 1-2 câu mỗi lượt) để kéo học viên vào vai diễn.\n"
            "4. TUYỆT ĐỐI KHÔNG chèn bất kỳ phần giải thích ngữ pháp, sửa lỗi hay nhắc nhở lỗi sai nào trong câu thoại. Việc phân tích lỗi đã có hệ thống chuyên biệt khác xử lý ở Thẻ Vàng AI Correction.\n"
            "5. Hãy dẫn dắt tình huống tự nhiên, đặt câu hỏi hoặc đưa ra gợi mở để thúc đẩy cuộc hội thoại.\n"
            "6. HỖ TRỢ KHI BẾ TẮC: Nếu học viên nói 'I don't know', 'I don't understand' hoặc im lặng/bế tắc, bạn BẮT BUỘC phải nói 1 câu Tiếng Việt động viên ngắn gọn, sau đó gợi ý cho họ 2 câu thoại Tiếng Anh mẫu siêu đơn giản phù hợp tình huống để họ tự tin bắt chước nói theo."
        )
        welcome_prompt = (
            f"Học viên vừa chọn chủ đề nhập vai: '{topic}'{level_tag}.\n"
            "BẮT BUỘC THỰC HIỆN THEO ĐÚNG THỨ TỰ SAU (KHÔNG ĐƯỢC BỎ QUA BƯỚC NÀO):\n"
            "BƯỚC 1 - CHÀO HỌC VIÊN: Nói 1 câu tiếng Việt ngắn gọn chào mừng, xác nhận chủ đề hôm nay.\n"
            "BƯỚC 2 - MỤC TIÊU: Nói bằng tiếng Việt 1 câu ngắn về mục tiêu buổi học hôm nay.\n"
            "BƯỚC 3 - TẠO BỐI CẢNH: Sáng tạo 1 bối cảnh nhập vai CỤ THỂ, SINH ĐỘNG, KHÔNG LẶP LẠI.\n"
            "   - Mô tả ngắn gọn bối cảnh bằng tiếng Việt (1 câu).\n"
            "   - Nêu rõ vai trò AI và vai trò học viên (1 câu).\n"
            "BƯỚC 4 - CÂU MỞ ĐẦU SONG NGỮ (BẮT BUỘC VỪA TIẾNG VIỆT VỪA TIẾNG ANH):\n"
            "   a) Nói 1 câu Tiếng Việt động viên thân thiện, ví dụ: 'Bạn cứ thoải mái nhé! 😊'\n"
            "   b) Đưa ra câu thoại Tiếng Anh đầu tiên (1 câu ngắn) của vai diễn AI.\n"
            "   c) Kèm bản dịch Tiếng Việt trong ngoặc đơn '(Dịch: ...)'.\n"
            "   d) Gợi ý 1 câu trả lời mẫu Tiếng Anh kèm dịch để học viên bắt chước nói theo ngay.\n"
            "GIỮ TOÀN BỘ NỘI DUNG NGẮN GỌN (tối đa 6-7 câu tổng cộng). TUYỆT ĐỐI KHÔNG viết dài dòng."
        )
    elif mode == "free_talk":
        # Điều chỉnh chỉ thị hệ thống dựa trên trình độ học viên lựa chọn
        level_instruction = ""
        if level in ["A1", "A2"]:
            level_instruction = (
                "BẮT BUỘC SỬ DỤNG TIẾNG ANH SIÊU ĐƠN GIẢN (Phù hợp với học sinh Lớp 6 tại Việt Nam):\n"
                "1. Bạn PHẢI nói cực kỳ chậm rãi, sử dụng các từ vựng căn bản và câu thoại siêu ngắn gọn (chỉ 1 câu ngắn mỗi lượt).\n"
                "2. Ở cuối mỗi câu thoại tiếng Anh, bạn BẮT BUỘC phải kèm theo bản dịch Tiếng Việt trong ngoặc đơn dạng '(Dịch: ...)' để học viên dễ hiểu và theo kịp.\n"
                "3. Đặt câu hỏi cực kỳ dễ trả lời và quen thuộc với học sinh phổ thông như 'How are you?', 'What is your name?', 'Do you like school?', 'What is your favorite color?'. TUYỆT ĐỐI KHÔNG dùng các cấu trúc bản xứ phức tạp như 'How are you doing today?' hay 'What's up?'."
            )
        elif level in ["B1", "B2"]:
            level_instruction = (
                "SỬ DỤNG TIẾNG ANH TRUNG CẤP (Trình độ B1-B2):\n"
                "1. Nói tốc độ vừa phải, dùng từ vựng giao tiếp thông dụng hàng ngày.\n"
                "2. Câu thoại ngắn gọn, rõ ràng (1-2 câu).\n"
                "3. Không cần dịch tiếng Việt trừ khi giải thích lỗi ngữ pháp."
            )
        else:  # Nâng cao C1/C2
            level_instruction = (
                "SỬ DỤNG TIẾNG ANH NÂNG CAO (Trình độ C1-C2):\n"
                "1. Nói tốc độ tự nhiên của người bản xứ, dùng từ vựng học thuật, thành ngữ (idioms) phong phú.\n"
                "2. Đặt các câu hỏi mở mang tính tư duy phản biện cao."
            )

        custom_instruction = (
            "Bạn là AI English Coach đàm thoại tự do bằng Tiếng Anh.\n"
            f"{level_instruction}\n"
            "QUY TẮC CHUNG:\n"
            "1. LUÔN đặt câu hỏi gợi mở ngắn gọn để giữ lửa cuộc đàm thoại.\n"
            "2. TUYỆT ĐỐI KHÔNG chèn bất kỳ phần giải thích ngữ pháp, sửa lỗi hay phân tích lỗi nào vào câu thoại chính. Việc sửa lỗi đã có hệ thống độc lập xử lý và hiển thị riêng ở Thẻ Vàng AI Correction. Bạn chỉ tập trung 100% vào việc đưa ra câu thoại đàm thoại tự nhiên.\n"
            "3. Khuyến khích học viên bày tỏ quan điểm.\n"
            "4. HỖ TRỢ KHI BẾ TẮC: Nếu học viên nói 'I don't know', 'I don't understand' hoặc im lặng/bế tắc, bạn BẮT BUỘC phải nói 1 câu Tiếng Việt động viên nồng ấm, gợi ý cho họ 2-3 câu trả lời mẫu Tiếng Anh siêu đơn giản (ví dụ: 'I like music' hoặc 'I want to sleep') hoặc chuyển hướng cuộc trò chuyện sang 1 câu hỏi mới cực kỳ dễ để học viên tự tin bắt đầu lại."
        )

        if level in ["A1", "A2"]:
            welcome_prompt = (
                "Hãy gửi lời chào bằng Tiếng Việt siêu ngắn gọn (tối đa 1 câu ngắn), "
                "giới thiệu bạn là AI English Coach và hôm nay sẽ cùng luyện nói mức độ Cơ bản dễ dàng. "
                "Sau đó, đưa ra ngay 1 câu hỏi tiếng Anh siêu ngắn và dễ kèm bản dịch Tiếng Việt trong ngoặc đơn."
            )
        else:
            welcome_prompt = (
                "Hãy gửi lời chào bằng Tiếng Việt siêu ngắn gọn (tối đa 1 câu ngắn), "
                "giới thiệu bạn là AI English Coach. Sau đó, đưa ra ngay 1 câu hỏi gợi mở tiếng Anh siêu ngắn gọn (1 câu) "
                "về một chủ đề thú vị để bắt đầu cuộc trò chuyện tự do."
            )

    try:
        while True:
            data = await websocket.receive_text()
            print(f"DEBUG: Realtime voice endpoint received: {data}")
            message_data = json.loads(data)
            
            if message_data.get("type") == "client_ready":
                if message_data.get("skip_welcome") is True:
                    print("DEBUG: Client is ready but requested to skip welcome greeting.")
                    await manager.send_json({"type": "status", "status": "idle"}, websocket)
                    continue
                
                print(f"DEBUG: Client is ready. Initiating welcome greeting...")
                if welcome_prompt:
                    await manager.send_json({"type": "status", "status": "thinking"}, websocket)
                    await manager.send_json({"type": "status", "status": "speaking"}, websocket)
                    
                    # Thiết lập custom_instruction chuyên dụng cho lượt chào mừng đầu tiên để ép Gemini nói Tiếng Việt dẫn dắt
                    current_instruction = custom_instruction
                    if mode == "roleplay":
                        current_instruction = (
                            f"Bạn là AI chuyên gia nhập vai{level_tag} trong chủ đề: '{topic}'.\n"
                            "QUY TẮC CỰC KỲ NGHIÊM NGẶT CHO LƯỢT CHÀO ĐẦU TIÊN (Giới thiệu Siêu ngắn gọn & Đi thẳng vào trọng tâm):\n"
                            "1. TỰ SÁNG TẠO một bối cảnh nhập vai cụ thể liên quan đến chủ đề.\n"
                            "2. BẮT BUỘC chỉ được nói tối đa 4 câu ngắn gọn theo cấu trúc sau:\n"
                            "   - Câu 1 (Tiếng Việt): Chào học viên ngắn gọn, giới thiệu bối cảnh và vai diễn (AI vai gì, học viên vai gì).\n"
                            "   - Câu 2 (Tiếng Việt): Một câu động viên siêu ngắn (Ví dụ: 'Bạn cứ tự nhiên nhé! 😊').\n"
                            "   - Câu 3 (Tiếng Anh): Đi thẳng vào câu thoại Tiếng Anh đầu tiên của vai diễn AI kèm bản dịch Tiếng Việt trong ngoặc '(Dịch: ...)'.\n"
                            "   - Câu 4 (Tiếng Anh/Tiếng Việt): Đưa ra 1 gợi ý câu trả lời mẫu Tiếng Anh kèm dịch (Ví dụ: '💡 Bạn có thể nói: \"Yes, I am ready.\"').\n"
                            "3. TUYỆT ĐỐI KHÔNG giải thích dông dài, không nêu mục tiêu rườm rà. Phải đi thẳng vào tình huống đàm thoại.\n"
                            f"4. LƯU Ý QUAN TRỌNG: Toàn bộ buổi học sau đó phải BÁM SÁT chủ đề '{topic}'. TUYỆT ĐỐI KHÔNG tự ý chuyển sang chủ đề khác."
                        )
                    
                    full_welcome = ""
                    try:
                        async for chunk in gemini_service.get_tutor_response(
                            compact_context="Học viên vừa tham gia bài học.",
                            user_message=welcome_prompt,
                            custom_instruction=current_instruction
                        ):
                            full_welcome += chunk
                            await manager.send_json({"type": "delta", "content": chunk}, websocket)
                    except Exception as e:
                        print(f"WARN: Realtime welcome response failed: {e}")
                        if mode == "roleplay":
                            import random
                            # Dynamic fallback: Rút gọn siêu ngắn gọn, đi thẳng vào trọng tâm
                            fallback_scenarios = [
                                (
                                    f"Chào bạn! Chúng ta sẽ nhập vai chủ đề '{topic}' nhé. Mình đóng vai người bán hàng, còn bạn là khách hàng. Bạn cứ tự nhiên nhé! 😊\n"
                                    "Hello! Let's get started. How can I help you today? (Dịch: Xin chào! Chúng ta bắt đầu nhé. Mình có thể giúp gì cho bạn hôm nay?)\n"
                                    "💡 Bạn có thể nói: 'I want to practice speaking English.'"
                                ),
                                (
                                    f"Xin chào! Hôm nay chúng ta sẽ nhập vai chủ đề '{topic}' nhé. Mình sẽ đồng hành trò chuyện cùng bạn. Hãy tự tin lên nhé! 😊\n"
                                    "Hi there! Are you ready to begin our conversation? (Dịch: Chào bạn! Bạn đã sẵn sàng bắt đầu cuộc trò chuyện chưa?)\n"
                                    "💡 Bạn có thể nói: 'Yes, I am ready!'"
                                ),
                                (
                                    f"Chào mừng bạn! Chúng ta sẽ nhập vai chủ đề '{topic}' nhé. Mình đóng vai bồi bàn, còn bạn là thực khách. Bạn cứ tự nhiên nhé! 😊\n"
                                    "Good day! Welcome! What would you like to talk about first? (Dịch: Ngày tốt lành! Chào mừng bạn! Bạn muốn nói về điều gì đầu tiên?)\n"
                                    "💡 Bạn có thể nói: 'Let's start the roleplay!'"
                                ),
                            ]
                            full_welcome = random.choice(fallback_scenarios)
                        else:
                            if level in ["A1", "A2"]:
                                full_welcome = "Xin chào! Mình là AI English Coach của bạn. Hôm nay chúng ta sẽ cùng đàm thoại tự do để tăng phản xạ nhé! How are you? (Dịch: Bạn khỏe không?) 😊"
                            else:
                                full_welcome = "Xin chào! Mình là AI English Coach của bạn. Hôm nay chúng ta sẽ cùng đàm thoại tự do để tăng phản xạ nhé! How are you doing today? 😊"
                        
                        await manager.send_json({"type": "delta", "content": full_welcome}, websocket)
                    
                    # Lưu chào mừng vào lịch sử hội thoại của memory
                    conversation_memory.add_turn(user_id, "[System welcome initiation]", full_welcome)
                    
                    await manager.send_json({
                        "type": "done",
                        "full_content": full_welcome,
                        "grammar_notes": "",
                        "route_used": "llm_welcome_initiate"
                    }, websocket)
                    await manager.send_json({"type": "status", "status": "idle"}, websocket)
                continue

            if message_data.get("type") == "voice_start":
                continue

            if message_data.get("type") == "message":
                user_message = message_data.get("content", "")
                target_text = message_data.get("target_text", user_message)
                current_time = time.time()
                
                # === XỬ LÝ TÍN HIỆU NUDGE: Học viên im lặng quá lâu ===
                if user_message == "[SILENCE_NUDGE]":
                    print("DEBUG: Received SILENCE_NUDGE - Student has been silent. AI will proactively re-engage.")
                    await manager.send_json({"type": "status", "status": "thinking"}, websocket)
                    await manager.send_json({"type": "status", "status": "speaking"}, websocket)
                    
                    nudge_instruction = custom_instruction + (
                        "\n\nTÌNH HUỐNG ĐẶC BIỆT: Học viên đang im lặng/chưa phản hồi. "
                        "Bạn BẮT BUỘC phải CHỦ ĐỘNG lên tiếng bằng 1 trong các cách sau:\n"
                        "a) Nhắc nhở thân thiện bằng Tiếng Việt (1 câu ngắn), sau đó lặp lại hoặc đặt lại câu hỏi Tiếng Anh đơn giản hơn kèm dịch Tiếng Việt.\n"
                        "b) Gợi ý 1-2 câu trả lời mẫu Tiếng Anh siêu đơn giản kèm dịch để học viên bắt chước nói theo.\n"
                        "Ví dụ: 'Bạn ơi, đến lượt bạn rồi! 😊 Let me ask again: Do you have a reservation? (Dịch: Bạn đã đặt phòng chưa?) "
                        "💡 Bạn có thể nói: \"Yes, I do.\" hoặc \"No, I don't.\"'\n"
                        "GIỮ NGẮN GỌN (tối đa 3-4 câu). TUYỆT ĐỐI KHÔNG nói dài dòng."
                    )
                    
                    nudge_full = ""
                    compact_ctx = conversation_memory.get_compact_context(user_id)
                    try:
                        async for chunk in gemini_service.get_tutor_response(
                            compact_context=compact_ctx,
                            user_message="Học viên đang im lặng, chưa phản hồi. Hãy chủ động nhắc nhở và hỏi lại.",
                            custom_instruction=nudge_instruction
                        ):
                            nudge_full += chunk
                            await manager.send_json({"type": "delta", "content": chunk}, websocket)
                    except Exception as e:
                        print(f"WARN: Nudge response failed: {e}")
                        nudge_full = "Bạn ơi, đến lượt bạn rồi! 😊 Don't worry, take your time! (Dịch: Đừng lo, cứ từ từ nhé!)"
                        await manager.send_json({"type": "delta", "content": nudge_full}, websocket)
                    
                    conversation_memory.add_turn(user_id, "[Học viên im lặng]", nudge_full)
                    await manager.send_json({
                        "type": "done",
                        "full_content": nudge_full,
                        "grammar_notes": "",
                        "route_used": "nudge_proactive"
                    }, websocket)
                    await manager.send_json({"type": "status", "status": "idle"}, websocket)
                    continue
                
                # === STEP 1: Professional LLM Correction Analysis with Fallback ===
                async def get_and_send_corrections():
                    # ĐÃ LOẠI BỎ TÍNH NĂNG AI CORRECTION THEO YÊU CẦU NGƯỜI DÙNG
                    # Điều này giúp tăng gấp đôi tốc độ phản hồi và tiết kiệm 100% tài nguyên API
                    return [], "disabled"

                correction_task = asyncio.create_task(get_and_send_corrections())

                # === STEP 2: AI Response Generation ===
                await manager.send_json({"type": "status", "status": "thinking"}, websocket)
                await manager.send_json({"type": "status", "status": "speaking"}, websocket)
                
                # Hiển thị lại nội dung học viên vừa nói (có dấu nháy kép) để người dùng xác nhận
                await manager.send_json({
                    "type": "delta", 
                    "content": f"\"{user_message}\"\n\n",
                    "silent": True 
                }, websocket)
                
                full_response = ""
                tokens_used = 500
                compact_ctx = conversation_memory.get_compact_context(user_id)
                
                try:
                    async for chunk in gemini_service.get_tutor_response(
                        compact_context=compact_ctx, user_message=user_message, custom_instruction=custom_instruction
                    ):
                        full_response += chunk
                        await manager.send_json({"type": "delta", "content": chunk}, websocket)
                except Exception as e:
                    import random
                    print(f"WARN: Gemini response failed: {e}")
                    
                    # Bộ sinh phản hồi dự phòng ngẫu nhiên và linh hoạt dựa trên chế độ học để tránh prompt cứng nhắc, chuyển sang hội thoại tương tác 2 chiều thực thụ
                    if mode == "roleplay":
                        roleplay_fallbacks = [
                            f"Mình nghe rất rõ câu thoại của bạn rồi nhé! Để tiếp tục tình huống nhập vai '{topic}' của chúng mình, hãy cho mình biết bạn muốn nói câu tiếp theo như thế nào nhé? Mình đang rất mong chờ đấy! ✨🚀",
                            f"Tình huống nhập vai '{topic}' đang diễn ra cực kỳ thú vị! Hãy cứ tự tin nhập vai và tiếp tục câu thoại tiếp theo của nhân vật của bạn nhé! Mình đã sẵn sàng lắng nghe rồi đây! 🌟",
                            f"Bạn nhập vai rất xuất sắc! Hãy tiếp tục câu chuyện '{topic}' theo cách tự nhiên nhất của bạn nhé. Đừng lo lắng về việc đúng sai, cứ thoải mái lên nè! 🎭"
                        ]
                        full_response = random.choice(roleplay_fallbacks)
                    else:  # free_talk hoặc vocabulary_practice
                        if level in ["A1", "A2"]:
                            a1_a2_fallbacks = [
                                "Chào bạn! Mình rất vui được luyện nói tiếng Anh cùng bạn. Hãy nói cho mình biết nhé: What is your favorite food? (Dịch: Món ăn yêu thích của bạn là gì?) Bạn có thích ăn pizza hay hamburger không? 🍕🍔",
                                "Ồ, giọng của bạn nghe rất dễ thương và ấm áp! Hãy chia sẻ một chút nhé: Do you like animals? (Dịch: Bạn có thích động vật không?) Bạn có nuôi chú chó hay chú mèo đáng yêu nào ở nhà không? 🐶🐱",
                                "Tuyệt vời lắm! Chúng mình hãy cùng tiếp tục câu chuyện nhé: What do you like to do in your free time? (Dịch: Bạn thích làm gì vào thời gian rảnh?) Bạn thích xem phim hoạt hình hay chơi trò chơi nè? 🎬🎮"
                            ]
                            full_response = random.choice(a1_a2_fallbacks)
                        else:  # B1/B2/C1/C2
                            b1_c2_fallbacks = [
                                "That's wonderful! I really enjoy chatting with you. Tell me, what do you usually like to do to relax after a busy day? (Dịch: Bạn thường làm gì để thư giãn sau một ngày bận rộn?) 🎧📚",
                                "Great response! Let's talk about our daily lives. How do you usually spend your weekends? Do you prefer staying indoors or going out with friends? 🚴‍♂️☕",
                                "Awesome! I'd love to hear your thoughts: Do you think learning English is important for your future career? Why or why not? 🚀🌟"
                            ]
                            full_response = random.choice(b1_c2_fallbacks)
                    await manager.send_json({"type": "delta", "content": full_response}, websocket)

                # Đảm bảo task sửa lỗi đã xong hẳn
                final_corrections_tuple = await correction_task
                final_corrections = final_corrections_tuple[0]
                route_used = final_corrections_tuple[1]

                # Tự động đồng bộ và lưu các lỗi sai thành WeakPoint vào Database để cá nhân hóa lộ trình xuyên suốt
                if final_corrections:
                    from app.models.models import WeakPoint
                    db = SessionLocal()
                    try:
                        for c in final_corrections:
                            # Thu gọn description của điểm yếu cho cô đọng
                            desc = c.explanation_vi if len(c.explanation_vi) < 180 else c.explanation_vi[:177] + "..."
                            weak_desc = f"'{c.original}' -> '{c.correction}' ({desc})"
                            if len(weak_desc) > 255:
                                weak_desc = weak_desc[:252] + "..."
                            
                            # Tìm xem lỗi tương tự đã có chưa
                            existing_wp = db.query(WeakPoint).filter(
                                WeakPoint.user_id == user_id,
                                WeakPoint.category == c.error_type,
                                WeakPoint.is_resolved == False,
                                WeakPoint.description.like(f"%{c.original}%")
                            ).first()
                            
                            if existing_wp:
                                existing_wp.frequency += 1
                            else:
                                new_wp = WeakPoint(
                                    user_id=user_id,
                                    category=c.error_type,
                                    description=weak_desc,
                                    frequency=1,
                                    is_resolved=False
                                )
                                db.add(new_wp)
                        db.commit()
                        print(f"DEBUG: Successfully synced {len(final_corrections)} WeakPoints to DB for User {user_id}")
                    except Exception as db_err:
                        print(f"WARN: Failed to save WeakPoints to DB: {db_err}")
                        db.rollback()
                    finally:
                        db.close()

                conversation_memory.add_turn(user_id, user_message, full_response)
                grammar_notes = "; ".join([c.explanation_vi for c in final_corrections if c.error_type == "grammar"])
                
                await manager.send_json({
                    "type": "done",
                    "full_content": full_response,
                    "grammar_notes": grammar_notes,
                    "route_used": route_used,
                    "tokens_used": tokens_used,
                }, websocket)
                await manager.send_json({"type": "status", "status": "idle"}, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass
        manager.disconnect(websocket)

