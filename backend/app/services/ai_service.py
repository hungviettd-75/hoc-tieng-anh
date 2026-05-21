import google.generativeai as genai
import asyncio
from app.core.config import settings
from typing import List, Dict, AsyncGenerator
import json

class GeminiService:
    def __init__(self):
        # Kiểm tra API Key (chỉ in 5 ký tự đầu để bảo mật)
        key_preview = settings.GEMINI_API_KEY[:5] + "..." if settings.GEMINI_API_KEY else "None"
        print(f"DEBUG: Initializing GeminiService with API Key starting with: {key_preview}")
        
        genai.configure(api_key=settings.GEMINI_API_KEY, transport="rest")
        # Sử dụng gemini-2.5-flash làm mặc định ban đầu
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        self.system_instruction = (
            "Bạn là AI English Coach siêu tối ưu. Quy tắc cốt lõi: NGẮN GỌN & TRỌNG TÂM.\n"
            "1. GIAO TIẾP TIẾNG VIỆT: Trả lời đi thẳng vào vấn đề, tối đa 2-3 câu ngắn mỗi lượt.\n"
            "2. TIẾT KIỆM TOKEN: Không chào hỏi dài dòng. Chỉ đưa ra kiến thức cần thiết.\n"
            "3. HỌC TỪ VỰNG: Đưa ra từ vựng kèm nghĩa/phiên âm một cách súc tích. Ví dụ: 'Apple /ˈæpl/: Quả táo. I like apples.'\n"
            "4. PHẢN HỒI NHANH: Sửa lỗi ngắn gọn bằng nhãn [Sửa]. Yêu cầu học viên thực hành ngay.\n"
            "5. Đảm bảo mỗi token bỏ ra đều mang lại giá trị học tập cao nhất cho học viên."
        )

        # Vietnamese Tutor system instruction (dùng cho realtime voice)
        self.tutor_instruction = (
            "Bạn là AI English Coach chuyên hỗ trợ học viên Việt Nam luyện nói đàm thoại hai chiều.\n"
            "QUY TẮC ĐÀM THOẠI SONG NGỮ BẮT BUỘC:\n"
            "1. CẤU TRÚC PHẢN HỒI SONG NGỮ DUY NHẤT: Mỗi lượt phản hồi, bạn chỉ được viết đúng 1 đoạn văn ngắn gồm 2 phần liên tiếp:\n"
            "   - Phần 1 (Tiếng Anh): Gồm 1 câu phản hồi siêu ngắn + đúng 1 câu hỏi mở dễ thương ở cuối (phù hợp học sinh lớp 6, trình độ A1-A2).\n"
            "   - Elevate (Dịch tiếng Việt): Viết bản dịch tiếng Việt trọn vẹn của Phần 1 đặt trong dấu ngoặc đơn ngay sau đó.\n"
            "   - Tuyệt đối cấm viết thêm bất kỳ câu hỏi hay ký tự nào ngoài cấu trúc này để tránh lặp câu hỏi.\n"
            "   Ví dụ chuẩn: 'Hello! What is your favorite toy? (Dịch: Xin chào! Món đồ chơi yêu thích của bạn là gì?)'\n"
            "2. KHÔNG DÙNG CÂU MẪU CỨNG: Tuyệt đối không đưa ra các câu gợi ý dạng 1, 2, 3 và bắt học viên chọn đọc theo. Hãy đàm thoại linh hoạt.\n"
            "3. THÂN THIỆN & ĐỘNG VIÊN: Sử dụng emoji sinh động (🐶, 🍕, 🎨,...).\n"
            "4. KHÔNG SỬA LỖI NGỮ PHÁP TRỰC TIẾP TRONG LỜI NÓI: Tuyệt đối không nhận xét lỗi sai ngữ pháp hay phát âm bằng lời nói, vì giao diện UI của ứng dụng đã tự hiển thị Thẻ Vàng sửa lỗi rất rõ ràng rồi."
        )

    def _get_text_safely(self, response_or_chunk) -> str:
        """
        Lấy văn bản phản hồi từ Gemini một cách an toàn để tránh lỗi 'Invalid operation: response.text quick accessor...'
        """
        try:
            # 1. Kiểm tra nếu có thuộc tính candidates
            if hasattr(response_or_chunk, "candidates") and response_or_chunk.candidates:
                candidate = response_or_chunk.candidates[0]
                if hasattr(candidate, "content") and candidate.content.parts:
                    part = candidate.content.parts[0]
                    if hasattr(part, "text") and part.text:
                        return part.text
            
            # 2. Cố gắng lấy qua quick accessor với try-except
            if hasattr(response_or_chunk, "text") and response_or_chunk.text:
                return response_or_chunk.text
        except Exception:
            pass
        return ""

    async def get_streaming_response(
        self, history: List[Dict[str, str]], user_message: str, custom_instruction: str = None
    ) -> AsyncGenerator[str, None]:
        """
        Gửi tin nhắn tới Gemini và nhận phản hồi streaming. Hỗ trợ tùy biến system instruction.
        Tự động xoay vòng qua các model Flash khác nhau nếu gặp lỗi Quota (429).
        Nếu tất cả model lỗi, sử dụng luồng phản hồi cục bộ để giữ kết nối học viên.
        """
        # Chuyển đổi history sang định dạng Gemini
        gemini_history = []
        for h in history:
            role = "user" if h["role"] == "user" else "model"
            gemini_history.append({"role": role, "parts": [h["content"]]})
        
        # Danh sách model xoay vòng
        models_to_try = [
            self.model.model_name.replace("models/", ""),
            'gemini-2.5-flash',
            'gemini-2.5-flash-lite',
            'gemini-3.1-flash-lite',
            'gemini-3.5-flash',
            'gemini-2.0-flash-lite'
        ]
        seen = set()
        models_to_try = [m for m in models_to_try if not (m in seen or seen.add(m))]

        last_err = None
        success = False

        system_prompt = custom_instruction or self.system_instruction
        for model_name in models_to_try:
            try:
                print(f"DEBUG GeminiService: Trying model {model_name} for chat streaming...")
                current_model = genai.GenerativeModel(model_name, system_instruction=system_prompt)
                chat = current_model.start_chat(history=gemini_history)
                
                # Dùng sync API trong thread riêng để tương thích với transport='rest'
                def _collect_chunks():
                    chunks = []
                    resp = chat.send_message(user_message, stream=True)
                    for chunk in resp:
                        text = self._get_text_safely(chunk)
                        if text:
                            chunks.append(text)
                    return chunks
                
                collected = await asyncio.to_thread(_collect_chunks)
                for chunk_text in collected:
                    yield chunk_text
                
                success = True
                if model_name != self.model.model_name.replace("models/", ""):
                    print(f"DEBUG: Setting new default chat model to {model_name}")
                    self.model = current_model
                break
            except Exception as model_e:
                print(f"DEBUG: Model {model_name} failed in chat streaming: {model_e}")
                last_err = model_e
                err_str = str(model_e).lower()
                if any(x in err_str for x in ["api_key", "api key", "invalid", "credential", "auth", "key not found", "not found", "forbidden", "403", "401"]):
                    break

        if not success:
            print(f"DEBUG GeminiService: Activating local fallback for chat. Last error: {last_err}")
            # Phản hồi dự phòng cục bộ chất lượng cao tránh ngắt quãng học tập
            if "B1" in (custom_instruction or "") or "B1" in user_message:
                yield "Chào mừng bạn đến với phòng luyện tập từ vựng trình độ B1! HLV AI đang bận xử lý một chút, hệ thống đã chuyển sang chế độ tự động. Chúng ta sẽ cùng thực hành các từ khóa: 'Persistent', 'Collaborate', 'Effective', 'Challenge' nhé! Hãy dùng câu đầu tiên bằng Tiếng Anh để trả lời câu hỏi: How was your day today?"
            else:
                yield f"Chào bạn! Kết nối AI đang bận rộn một chút (Chi tiết lỗi: {last_err}). Hãy tiếp tục nói tiếng Anh nhé. How are you today? 😊"

    async def get_tutor_response(
        self, compact_context: str, user_message: str, custom_instruction: str = None
    ) -> AsyncGenerator[str, None]:
        """
        Streaming response với compressed context cho Vietnamese tutor.
        Tiết kiệm ~60% tokens so với get_streaming_response.
        Tự động xoay vòng qua các model Flash khác nhau nếu gặp lỗi Quota (429).
        """
        system_instruction = custom_instruction or self.tutor_instruction
        prompt = (
            f"{compact_context}\n\n"
            f"User: {user_message}\nCoach:"
        )

        models_to_try = [
            self.model.model_name.replace("models/", ""),
            'gemini-2.5-flash',
            'gemini-2.5-flash-lite',
            'gemini-3.1-flash-lite',
            'gemini-3.5-flash',
            'gemini-2.0-flash-lite'
        ]
        seen = set()
        models_to_try = [m for m in models_to_try if not (m in seen or seen.add(m))]

        last_err = None
        success = False

        for model_name in models_to_try:
            try:
                print(f"DEBUG GeminiService: Trying model {model_name} for tutor streaming...")
                current_model = genai.GenerativeModel(model_name, system_instruction=system_instruction)
                chat = current_model.start_chat(history=[])
                
                # Dùng sync API trong thread riêng để tương thích với transport='rest'
                def _collect_tutor_chunks():
                    chunks = []
                    resp = chat.send_message(prompt, stream=True)
                    for chunk in resp:
                        text = self._get_text_safely(chunk)
                        if text:
                            chunks.append(text)
                    return chunks
                
                collected = await asyncio.to_thread(_collect_tutor_chunks)
                for chunk_text in collected:
                    yield chunk_text
                success = True
                if model_name != self.model.model_name.replace("models/", ""):
                    print(f"DEBUG: Setting new default tutor model to {model_name}")
                    self.model = current_model
                break
            except Exception as model_e:
                print(f"DEBUG: Model {model_name} failed in tutor streaming: {model_e}")
                last_err = model_e
                err_str = str(model_e).lower()
                if any(x in err_str for x in ["api_key", "api key", "invalid", "credential", "auth", "key not found", "not found", "forbidden", "403", "401"]):
                    break

        if not success:
            print(f"DEBUG GeminiService: Activating local fallback for tutor response. Last error: {last_err}")
            # Cung cấp phản hồi song ngữ song hành đúng format sư phạm
            if "restaurant" in (custom_instruction or "").lower() or "restaurant" in user_message.lower():
                yield "Hello! Welcome to our restaurant. Are you ready to order? (Dịch: Xin chào! Chào mừng bạn đến với nhà hàng của chúng tôi. Bạn đã sẵn sàng gọi món chưa?)"
            else:
                yield f"That's very interesting! Can you tell me more about it? (Chi tiết lỗi: {last_err})"

    async def get_tutor_correction(self, user_text: str, errors_summary: str, user_level: str = "A2") -> str:
        """
        Nhờ LLM tạo correction chi tiết cho lỗi phức tạp.
        Tự động xoay vòng qua các model Flash khác nhau nếu gặp lỗi Quota (429).
        """
        vi_ratio = "90% Vietnamese" if user_level in ("A1", "A2") else "bilingual" if user_level == "B1" else "mostly English"
        prompt = (
            f"Sửa lỗi speaking cho học viên level {user_level} ({vi_ratio}).\n"
            f"User said: \"{user_text}\"\n"
            f"Errors: {errors_summary}\n"
            f"Respond in 2-3 sentences max. Include IPA if pronunciation error."
        )

        models_to_try = [
            self.model.model_name.replace("models/", ""),
            'gemini-2.5-flash',
            'gemini-2.5-flash-lite',
            'gemini-3.1-flash-lite',
            'gemini-3.5-flash',
            'gemini-2.0-flash-lite'
        ]
        seen = set()
        models_to_try = [m for m in models_to_try if not (m in seen or seen.add(m))]

        for model_name in models_to_try:
            try:
                print(f"DEBUG GeminiService: Trying model {model_name} for tutor correction...")
                current_model = genai.GenerativeModel(model_name)
                response = await current_model.generate_content_async(prompt)
                return self._get_text_safely(response).strip()
            except Exception as model_e:
                print(f"DEBUG: Model {model_name} failed in tutor correction: {model_e}")
                err_str = str(model_e).lower()
                if any(x in err_str for x in ["api_key", "api key", "invalid", "credential", "auth", "key not found", "not found", "forbidden", "403", "401"]):
                    break
        
        return f"Bạn đã nói: '{user_text}'. Hãy chú ý cấu trúc ngữ pháp và cách phát âm của các từ khóa nhé! 💪"

    async def get_structured_correction(self, user_message: str) -> List[Dict]:
        """
        Sử dụng LLM để phân tích lỗi chuyên sâu và trả về cấu trúc JSON chuẩn.
        Tự động xoay vòng qua các model Flash khác nhau nếu gặp lỗi Quota (429).
        """
        prompt = f"""You are an expert English Grammar and Pronunciation Coach.
Analyze the user's speech: "{user_message}"

If the sentence is perfectly natural and grammatically correct, return an empty JSON array: []
If there are errors or unnatural phrasing, return a JSON array containing the errors. 
Format ONLY as valid JSON (no markdown):
[
  {{
    "error_type": "grammar", // or "pronunciation", "natural_speaking"
    "severity": "medium", // "low", "medium", "high"
    "original": "<the incorrect word or phrase>",
    "correction": "<the correct word or phrase>",
    "explanation_vi": "<Friendly, encouraging explanation in Vietnamese, max 20 words>"
  }}
]"""

        models_to_try = [
            self.model.model_name.replace("models/", ""),
            'gemini-2.5-flash',
            'gemini-2.5-flash-lite',
            'gemini-3.1-flash-lite',
            'gemini-3.5-flash',
            'gemini-2.0-flash-lite'
        ]
        seen = set()
        models_to_try = [m for m in models_to_try if not (m in seen or seen.add(m))]

        import re

        for model_name in models_to_try:
            try:
                print(f"DEBUG GeminiService: Trying model {model_name} for structured correction...")
                current_model = genai.GenerativeModel(model_name)
                response = await current_model.generate_content_async(prompt)
                text = self._get_text_safely(response).strip()
                
                match = re.search(r'\[.*\]', text, re.DOTALL)
                if match:
                    text = match.group(0)
                else:
                    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.IGNORECASE)
                    text = re.sub(r'\s*```$', '', text)
                
                cleaned_text = text.strip()
                if not cleaned_text or cleaned_text == "[]":
                    return []
                    
                return json.loads(cleaned_text)
            except Exception as model_e:
                print(f"DEBUG: Model {model_name} failed in structured correction: {model_e}")
                err_str = str(model_e).lower()
                if any(x in err_str for x in ["api_key", "api key", "invalid", "credential", "auth", "key not found", "not found", "forbidden", "403", "401"]):
                    break

        # Trả về mảng rỗng làm fallback để hệ thống Local NLP tự xử lý phía sau
        return []

    async def get_embedding(self, text: str) -> List[float]:
        """
        Tạo vector embedding cho văn bản sử dụng Gemini.
        """
        try:
            result = await asyncio.to_thread(
                genai.embed_content,
                model="models/gemini-embedding-001",
                content=text,
                task_type="retrieval_document",
                title="Memory Embedding"
            )
            return result['embedding'][:768]
        except Exception as e:
            print(f"WARN: get_embedding failed: {e}")
            # Trả về dummy vector 768 số 0 để tránh lỗi định dạng
            return [0.0] * 768

# Initialize service singleton
gemini_service = GeminiService()
