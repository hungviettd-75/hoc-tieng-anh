from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.services.ai_service import gemini_service
from app.services.memory_service import memory_service
from app.services.ai_router import ai_router
from app.services.conversation_memory import conversation_memory
from app.services.vietnamese_tutor_engine import vietnamese_tutor
from app.db.session import SessionLocal
from app.models.models import Conversation, Message as DBMessage
import json
import asyncio
import time

router = APIRouter()

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
    "A1": ["Beginner", "Practice", "Vocabulary", "Improve"],
    "A2": ["Journey", "Confident", "Habit", "Encourage"],
    "B1": ["Persistent", "Collaborate", "Effective", "Challenge"],
    "B2": ["Substantial", "Fluency", "Analyze", "Evaluate"],
    "C1": ["Pragmatic", "Eloquent", "Cognitive", "Sophisticated"],
}

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    user_id: int,
    mode: str = None,
    level: str = None,
    topic: str = None
):
    print(f"DEBUG: New WebSocket connection for user_id: {user_id}, mode: {mode}, level: {level}, topic: {topic}")
    await manager.connect(websocket)
    
    # Bắt buộc dọn dẹp bộ nhớ hội thoại cũ của user để đảm bảo mỗi lần mở lại phòng là một session mới tươi nguyên, 100% hiện giới thiệu tiếng Việt dẫn dắt!
    conversation_memory.clear(user_id)
    
    # Khởi tạo history hội thoại cho session này
    history = []
    
    # Cấu hình custom System Instruction tùy theo chế độ
    custom_instruction = None
    welcome_prompt = None

    if mode == "vocabulary_practice" and level:
        vocab_words = VOCAB_LISTS.get(level.upper(), VOCAB_LISTS["B1"])
        words_str = ", ".join([f"'{w}'" for w in vocab_words])
        custom_instruction = (
            "Bạn là AI English Coach chuyên hỗ trợ học viên Luyện tập Từ vựng Thông minh.\n"
            f"Nhiệm vụ của bạn là bắt buộc học viên thực hành các từ khóa trình độ {level}: {words_str}.\n"
            "QUY TẮC:\n"
            "1. LUÔN GIAO TIẾP BẰNG TIẾNG VIỆT thân thiện, ngắn gọn (max 2-3 câu mỗi lượt).\n"
            "2. KIỂM TRA TỪ KHÓA: Trong mỗi câu trả lời của học viên, hãy kiểm tra xem họ có sử dụng bất kỳ từ khóa nào ở trên không.\n"
            "   - Nếu có: Hãy lập tức khen ngợi nồng nhiệt kèm dấu tick xanh lá (ví dụ: 'Tuyệt vời! Bạn đã sử dụng từ khóa B1 thành công ✅').\n"
            "   - Nếu không: Hãy khéo léo nhắc nhở hoặc gợi ý họ áp dụng từ khóa vào câu tiếp theo.\n"
            "3. Hướng dẫn học viên cách dùng chuẩn bằng các ví dụ tiếng Anh ngắn gọn."
        )
        welcome_prompt = (
            f"Học viên vừa tham gia lớp học từ vựng trình độ {level}. "
            f"Hãy gửi lời chào đón bằng Tiếng Việt nồng ấm, giới thiệu nhiệm vụ hôm nay là thực hành các từ khóa: {words_str}. "
            "Đưa ra 1 câu hỏi gợi mở ngắn bằng Tiếng Anh để bắt đầu cuộc hội thoại."
        )
    elif mode == "roleplay" and topic:
        custom_instruction = (
            f"Bạn là AI chuyên gia nhập vai tiếng Anh trong tình huống giao tiếp thực tế: '{topic}'.\n"
            "QUY TẮC:\n"
            "1. Bạn PHẢI đóng đúng vai trò hội thoại phù hợp với tình huống này.\n"
            "   - Nếu tình huống là nhà hàng, bạn là nhân viên phục vụ (Waiter/Waitress), học viên là khách hàng.\n"
            "   - Nếu tình huống là sân bay, bạn là nhân viên check-in, học viên là hành khách.\n"
            "   - Đối với bất kỳ tình huống nào khác, hãy đóng vai trò đối thoại tự nhiên tương ứng.\n"
            "2. GIAO TIẾP CHỦ YẾU BẰNG TIẾNG ANH (ngắn gọn, 1-2 câu mỗi lượt) để kéo học viên vào vai diễn.\n"
            "3. Hỗ trợ sư phạm: Nếu học viên nói sai ngữ pháp hoặc phát âm, bạn có thể kèm giải thích/gợi ý ngắn gọn bằng Tiếng Việt ở cuối câu thoại.\n"
            "4. Hãy dẫn dắt tình huống tự nhiên, đặt câu hỏi hoặc đưa ra gợi mở để thúc đẩy cuộc hội thoại."
        )
        welcome_prompt = (
            f"Học viên vừa tham gia tình huống nhập vai thực tế: '{topic}'. "
            "Hãy gửi lời chào chào mừng bằng Tiếng Việt nồng ấm, giới thiệu rõ vai diễn của bạn và vai diễn của học viên trong tình huống này. "
            "Sau đó đưa ra câu thoại tiếng Anh đầu tiên để dẫn dắt học viên bắt đầu nhập vai."
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
            
            await websocket.send_json({
                "type": "completion",
                "role": "assistant",
                "content": full_response,
                "grammar_notes": ""
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
    topic: str = None
):
    """
    WebSocket endpoint chuyên biệt cho trải nghiệm Voice Realtime.
    Smart Hybrid AI Pipeline:
    User Text → Local NLP → AI Router → (LLM nếu cần) → Vietnamese Tutor → Response
    """
    if not mode or mode == "null":
        mode = "free_talk"
    print(f"DEBUG: New Realtime WebSocket connection for user_id: {user_id}, mode: {mode}, level: {level}, topic: {topic}")
    await manager.connect(websocket)
    
    # Bắt buộc dọn dẹp bộ nhớ hội thoại cũ của user để đảm bảo mỗi lần mở lại phòng là một session mới tươi nguyên, 100% hiện giới thiệu tiếng Việt dẫn dắt!
    conversation_memory.clear(user_id)

    # Cấu hình custom System Instruction tùy theo chế độ
    custom_instruction = None
    welcome_prompt = None

    if mode == "vocabulary_practice" and level:
        vocab_words = VOCAB_LISTS.get(level.upper(), VOCAB_LISTS["B1"])
        words_str = ", ".join([f"'{w}'" for w in vocab_words])
        custom_instruction = (
            "Bạn là AI English Coach chuyên hỗ trợ học viên Luyện tập Từ vựng Thông minh.\n"
            f"Nhiệm vụ của bạn là bắt buộc học viên thực hành các từ khóa trình độ {level}: {words_str}.\n"
            "QUY TẮC:\n"
            "1. LUÔN GIAO TIẾP BẰNG TIẾNG VIỆT thân thiện, ngắn gọn (max 2-3 câu mỗi lượt).\n"
            "2. KIỂM TRA TỪ KHÓA: Trong mỗi câu trả lời của học viên, hãy kiểm tra xem họ có sử dụng bất kỳ từ khóa nào ở trên không.\n"
            "   - Nếu có: Hãy lập tức khen ngợi nồng nhiệt kèm dấu tick xanh lá (ví dụ: 'Tuyệt vời! Bạn đã sử dụng từ khóa B1 thành công ✅').\n"
            "   - Nếu không: Hãy khéo léo nhắc nhở hoặc gợi ý họ áp dụng từ khóa vào câu tiếp theo.\n"
            "3. Hướng dẫn học viên cách dùng chuẩn bằng các ví dụ tiếng Anh ngắn gọn."
        )
        welcome_prompt = (
            f"Chào mừng học viên bằng Tiếng Việt siêu ngắn gọn (tối đa 1-2 câu ngắn), "
            f"giới thiệu chủ đề từ vựng {level} hôm nay cần thực hành: {words_str}. "
            "Sau đó, đưa ra ngay 1 câu hỏi tiếng Anh gợi mở siêu ngắn gọn để học viên bắt đầu."
        )
    elif mode == "roleplay" and topic:
        custom_instruction = (
            f"Bạn là AI chuyên gia nhập vai tiếng Anh trong tình huống giao tiếp thực tế: '{topic}'.\n"
            "QUY TẮC:\n"
            "1. Bạn PHẢI đóng đúng vai trò hội thoại phù hợp với tình huống này.\n"
            "   - Nếu tình huống là nhà hàng, bạn là nhân viên phục vụ (Waiter/Waitress), học viên là khách hàng.\n"
            "   - Nếu tình huống là sân bay, bạn là nhân viên check-in, học viên là hành khách.\n"
            "   - Đối với bất kỳ tình huống nào khác, hãy đóng vai trò đối thoại tự nhiên tương ứng.\n"
            "2. GIAO TIẾP CHỦ YẾU BẰNG TIẾNG ANH (ngắn gọn, 1-2 câu mỗi lượt) để kéo học viên vào vai diễn.\n"
            "3. TUYỆT ĐỐI KHÔNG chèn bất kỳ phần giải thích ngữ pháp, sửa lỗi hay nhắc nhở lỗi sai nào trong câu thoại này. Việc phân tích lỗi đã có một hệ thống chuyên biệt khác tự động xử lý và hiển thị ở Thẻ Vàng AI Correction. Bạn chỉ tập trung 100% vào việc đưa ra câu thoại nhập vai tự nhiên nhất.\n"
            "4. Hãy dẫn dắt tình huống tự nhiên, đặt câu hỏi hoặc đưa ra gợi mở để thúc đẩy cuộc hội thoại.\n"
            "5. HỖ TRỢ KHI BẾ TẮC: Nếu học viên nói 'I don't know', 'I don't understand' hoặc im lặng/bế tắc, bạn BẮT BUỘC phải nói 1 câu Tiếng Việt động viên ngắn gọn, sau đó gợi ý cho họ 2 câu thoại Tiếng Anh mẫu siêu đơn giản phù hợp tình huống (ví dụ: 'Yes, please' hoặc 'Here you go') để họ tự tin bắt chước nói theo."
        )
        welcome_prompt = (
            f"Hãy gửi lời chào bằng Tiếng Việt siêu ngắn gọn (tối đa 1-2 câu ngắn) giới thiệu vai diễn của bạn và của học viên "
            f"trong tình huống '{topic}'. Sau đó, đưa ra ngay câu thoại tiếng Anh đầu tiên "
            "của bạn (tối đa 1 câu ngắn) để dẫn dắt học viên nhập vai ngay lập tức. TUYỆT ĐỐI không viết gợi ý hay hướng dẫn dài dòng."
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
                print(f"DEBUG: Client is ready. Initiating welcome greeting...")
                if welcome_prompt:
                    await manager.send_json({"type": "status", "status": "thinking"}, websocket)
                    await manager.send_json({"type": "status", "status": "speaking"}, websocket)
                    
                    # Thiết lập custom_instruction chuyên dụng cho lượt chào mừng đầu tiên để ép Gemini nói Tiếng Việt dẫn dắt
                    current_instruction = custom_instruction
                    if mode == "roleplay":
                        current_instruction = (
                            f"Bạn là AI chuyên gia nhập vai trong tình huống giao tiếp thực tế: '{topic}'.\n"
                            "QUY TẮC BẮT BUỘC CHO LƯỢT CHÀO ĐẦU TIÊN:\n"
                            "1. Bạn BẮT BUỘC phải nói bằng Tiếng Việt trước (tối đa 1-2 câu ngắn gọn) để chào mừng nồng nhiệt và giới thiệu rõ tình huống cũng như vai diễn của cả hai.\n"
                            "2. Ngay sau đó, đưa ra câu thoại Tiếng Anh đầu tiên của vai diễn (tối đa 1 câu ngắn) để dẫn dắt học viên bắt đầu nhập vai.\n"
                            "3. Tuyệt đối không viết thêm các lời dặn dò hay gợi ý thực hành dài dòng khác."
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
                            full_welcome = f"Chào mừng bạn đến với tình huống nhập vai '{topic}'! Mình đã sẵn sàng rồi. Hãy bắt đầu cuộc hội thoại nhé! 🚀"
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
                
                # === STEP 1: Professional LLM Correction Analysis with Fallback ===
                async def get_and_send_corrections():
                    from app.services.lightweight_nlp_engine import CorrectionItem, lightweight_nlp
                    corrections_obj = []
                    used_route = "llm_professional"
                    try:
                        ai_corrections = await gemini_service.get_structured_correction(user_message)
                        for c in ai_corrections:
                            corrections_obj.append(CorrectionItem(
                                error_type=c.get("error_type", "grammar"),
                                severity=c.get("severity", "medium"),
                                original=c.get("original", ""),
                                correction=c.get("correction", ""),
                                explanation_vi=c.get("explanation_vi", ""),
                                category="llm_professional"
                            ))
                        
                        # FALLBACK: Nếu Gemini trả về mảng rỗng (do lỗi 429, timeout hoặc không tìm thấy lỗi)
                        if not corrections_obj:
                            local_errors = lightweight_nlp.detect_all_errors(target_text, user_message)
                            if local_errors:
                                print("DEBUG: Gemini returned empty. Activated Local NLP Fallback.")
                                corrections_obj = local_errors
                                used_route = "local_fallback"
                        
                        if corrections_obj:
                            correction_text = vietnamese_tutor.format_correction_response(corrections_obj)
                            correction_data = [{
                                "error_type": c.error_type, "severity": c.severity,
                                "original": c.original, "correction": c.correction,
                                "ipa": getattr(c, 'ipa', ''), "explanation_vi": c.explanation_vi,
                            } for c in corrections_obj]
                            
                            await manager.send_json({
                                "type": "realtime_correction",
                                "corrections": correction_data,
                                "formatted_text": correction_text,
                                "route": used_route,
                            }, websocket)
                        return corrections_obj, used_route
                    except Exception as e:
                        print(f"ERROR in get_and_send_corrections: {e}")
                        return corrections_obj, used_route

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
                    
                    # Bộ sinh phản hồi dự phòng ngẫu nhiên và linh hoạt dựa trên chế độ học để tránh prompt cứng nhắc
                    if mode == "roleplay":
                        roleplay_fallbacks = [
                            f"Mình đã nghe câu thoại của bạn. Để tiếp tục tình huống nhập vai '{topic}', bạn có thể thử nói các câu mẫu sau nhé:\n"
                            "1. \"Can you help me with this?\" (Dịch: Bạn có thể giúp tôi việc này không?)\n"
                            "2. \"Yes, that sounds perfect!\" (Dịch: Vâng, nghe tuyệt đấy!)\n"
                            "Hãy thử chọn một câu để tiếp tục nhập vai nhé! ✨",
                            
                            f"Tình huống '{topic}' đang rất thú vị! Bạn có thể thử phản hồi bằng các mẫu câu đơn giản này nhé:\n"
                            "1. \"Excuse me, could you tell me more?\" (Dịch: Xin lỗi, bạn có thể nói rõ hơn không?)\n"
                            "2. \"Okay, I agree with you.\" (Dịch: Được rồi, tôi đồng ý với bạn.)\n"
                            "Hãy bấm giữ Mic và nói thử xem nào! 🌟",
                            
                            f"Đừng lo lắng nhé! Đối với tình huống '{topic}', bạn có thể thử nói các câu đơn giản sau để tiếp tục diễn:\n"
                            "1. \"How much does it cost?\" (Dịch: Cái này giá bao nhiêu vậy?)\n"
                            "2. \"Thank you so much for your help.\" (Dịch: Cảm ơn bạn rất nhiều vì đã giúp đỡ.)\n"
                            "Cố lên, bạn nói rất tốt mà! 🚀"
                        ]
                        full_response = random.choice(roleplay_fallbacks)
                    else:  # free_talk hoặc vocabulary_practice
                        if level in ["A1", "A2"]:
                            a1_a2_fallbacks = [
                                "Không sao cả, hãy cứ tự nhiên nhé! Bạn có thể thử trả lời bằng các câu mẫu siêu đơn giản này:\n"
                                "1. \"I love eating pizza and burgers.\" (Dịch: Mình thích ăn pizza và humberger.)\n"
                                "2. \"The weather today is very nice.\" (Dịch: Thời tiết hôm nay rất đẹp.)\n"
                                "Hãy chọn một câu bạn thích và nói vào Mic nhé! 🍕🌞",
                                
                                "Đừng ngại ngùng nhé! Để tiếp tục câu chuyện, bạn có thể nói về sở thích của mình:\n"
                                "1. \"I like watching English movies.\" (Dịch: Mình thích xem phim tiếng Anh.)\n"
                                "2. \"I usually go to bed at 10 PM.\" (Dịch: Mình thường đi ngủ lúc 10 giờ tối.)\n"
                                "Hãy thử bấm Mic nói một câu nhé! 🎬🛌",
                                
                                "Hãy cứ thoải mái luyện tập nhé! Bạn có thể thử bắt đầu lại câu chuyện bằng các câu mẫu sau:\n"
                                "1. \"I have a beautiful small pet dog.\" (Dịch: Mình có một chú chó cưng nhỏ rất đẹp.)\n"
                                "2. \"I want to learn English to travel.\" (Dịch: Mình muốn học tiếng Anh để đi du lịch.)\n"
                                "Bấm Mic và thử nói xem sao nhé! 🐶✈️"
                            ]
                            full_response = random.choice(a1_a2_fallbacks)
                        else:  # B1/B2/C1/C2
                            b1_c2_fallbacks = [
                                "That's an interesting point! To expand our conversation, you could say:\n"
                                "1. \"In my opinion, learning languages opens new doors.\" (Dịch: Theo tôi, học ngôn ngữ mở ra những cánh cửa mới.)\n"
                                "2. \"I enjoy spending time outdoors on weekends.\" (Dịch: Tôi thích dành thời gian ngoài trời vào cuối tuần.)\n"
                                "Give it a try! You are doing great! 🚀",
                                
                                "Keep going! Here are some sample ideas you can use to express yourself:\n"
                                "1. \"I usually manage my time by creating a daily to-do list.\" (Dịch: Tôi thường quản lý thời gian bằng cách lập danh sách việc cần làm.)\n"
                                "2. \"Travelling helps me learn about different cultures.\" (Dịch: Du lịch giúp tôi tìm hiểu về các nền văn hóa khác nhau.)\n"
                                "Choose one and speak to the mic! 🌟",
                                
                                "You're doing fantastic! Feel free to talk about your daily routines:\n"
                                "1. \"I try to read at least ten pages of a book every day.\" (Dịch: Tôi cố gắng đọc ít nhất mười trang sách mỗi ngày.)\n"
                                "2. \"Working in a team is both challenging and rewarding.\" (Dịch: Làm việc nhóm vừa thử thách vừa bổ ích.)\n"
                                "Let's speak! 🚀"
                            ]
                            full_response = random.choice(b1_c2_fallbacks)
                    await manager.send_json({"type": "delta", "content": full_response}, websocket)

                # Đảm bảo task sửa lỗi đã xong hẳn
                final_corrections_tuple = await correction_task
                final_corrections = final_corrections_tuple[0]
                route_used = final_corrections_tuple[1]

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

