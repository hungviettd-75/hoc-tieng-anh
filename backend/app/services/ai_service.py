import google.generativeai as genai
from app.core.config import settings
from typing import List, Dict, AsyncGenerator
import json

class GeminiService:
    def __init__(self):
        # Kiểm tra API Key (chỉ in 5 ký tự đầu để bảo mật)
        key_preview = settings.GEMINI_API_KEY[:5] + "..." if settings.GEMINI_API_KEY else "None"
        print(f"DEBUG: Initializing GeminiService with API Key starting with: {key_preview}")
        
        genai.configure(api_key=settings.GEMINI_API_KEY)
        # Sử dụng gemini-2.5-flash (phiên bản tiên tiến hơn theo yêu cầu)
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
            "Bạn là AI English Coach chuyên hỗ trợ học viên Việt Nam luyện nói.\n"
            "QUY TẮC:\n"
            "- TRẢ LỜI BẰNG TIẾNG VIỆT để học viên dễ tiếp cận.\n"
            "- Chỉ dùng tiếng Anh khi đưa ra các mẫu câu luyện tập hoặc các đoạn hội thoại thực hành.\n"
            "- Thân thiện, dùng emoji phù hợp, câu trả lời ngắn gọn (max 2-3 câu).\n"
            "- Luôn khen ngợi và động viên khi học viên cố gắng nói tiếng Anh.\n"
            "- TUYỆT ĐỐI KHÔNG sửa lỗi trong lúc đang trò chuyện (hệ thống UI sẽ tự hiển thị thẻ sửa lỗi)."
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
        """
        # Chuyển đổi history sang định dạng Gemini
        gemini_history = []
        for h in history:
            role = "user" if h["role"] == "user" else "model"
            gemini_history.append({"role": role, "parts": [h["content"]]})
        
        try:
            chat = self.model.start_chat(history=gemini_history)
            system_prompt = custom_instruction or self.system_instruction
            prompt = f"{system_prompt}\n\nUser: {user_message}\nCoach:"
            response = await chat.send_message_async(prompt, stream=True)
            
            async for chunk in response:
                chunk_text = self._get_text_safely(chunk)
                if chunk_text:
                    yield chunk_text
        except Exception as e:
            print(f"ERROR in Gemini streaming: {str(e)}")
            raise e

    async def get_tutor_response(
        self, compact_context: str, user_message: str, custom_instruction: str = None
    ) -> AsyncGenerator[str, None]:
        """
        Streaming response với compressed context cho Vietnamese tutor.
        Tiết kiệm ~60% tokens so với get_streaming_response.
        """
        system_instruction = custom_instruction or self.tutor_instruction
        prompt = (
            f"{system_instruction}\n\n"
            f"{compact_context}\n\n"
            f"User: {user_message}\nCoach:"
        )
        try:
            response = await self.model.generate_content_async(prompt, stream=True)
            async for chunk in response:
                chunk_text = self._get_text_safely(chunk)
                if chunk_text:
                    yield chunk_text
        except Exception as e:
            print(f"ERROR in tutor streaming: {str(e)}")
            raise e

    async def get_tutor_correction(self, user_text: str, errors_summary: str, user_level: str = "A2") -> str:
        """
        Nhờ LLM tạo correction chi tiết cho lỗi phức tạp.
        Compressed prompt (~200 tokens input).
        """
        vi_ratio = "90% Vietnamese" if user_level in ("A1", "A2") else "bilingual" if user_level == "B1" else "mostly English"
        prompt = (
            f"Sửa lỗi speaking cho học viên level {user_level} ({vi_ratio}).\n"
            f"User said: \"{user_text}\"\n"
            f"Errors: {errors_summary}\n"
            f"Respond in 2-3 sentences max. Include IPA if pronunciation error."
        )
        try:
            response = await self.model.generate_content_async(prompt)
            return self._get_text_safely(response).strip()
        except Exception as e:
            print(f"ERROR in tutor correction: {str(e)}")
            return ""

    async def get_structured_correction(self, user_message: str) -> List[Dict]:
        """
        Sử dụng LLM để phân tích lỗi chuyên sâu và trả về cấu trúc JSON chuẩn.
        Bỏ qua Local NLP và thay thế hoàn toàn bằng AI chuyên nghiệp.
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
        try:
            response = await self.model.generate_content_async(prompt)
            text = self._get_text_safely(response).strip()
            if text.startswith("```"):
                import re
                text = re.sub(r'^```(?:json)?\s*', '', text)
                text = re.sub(r'\s*```$', '', text)
            return json.loads(text)
        except Exception as e:
            print(f"ERROR parsing structured correction: {e}")
            return []

    async def get_embedding(self, text: str) -> List[float]:
        """
        Tạo vector embedding cho văn bản sử dụng Gemini.
        """
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=text,
            task_type="retrieval_document",
            title="Memory Embedding"
        )
        
        # Kỹ thuật Matryoshka: Cắt lấy 768 phần tử đầu tiên để khớp với Pinecone Index
        # Điều này đảm bảo tính ổn định bất kể model trả về 768 hay 3072.
        return result['embedding'][:768]

# Initialize service singleton
gemini_service = GeminiService()
