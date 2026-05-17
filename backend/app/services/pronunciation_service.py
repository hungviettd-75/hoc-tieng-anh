import google.generativeai as genai
from app.core.config import settings
from typing import Dict, List, Optional
import json
import os
import re
import tempfile
import difflib

# Cấu hình Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)


class PronunciationService:
    """
    Voice processing pipeline sử dụng 100% Gemini API.
    - Audio transcription (Gemini multimodal)
    - Pronunciation scoring (Gemini text analysis)
    - Word-level accuracy (local algorithm)
    """

    def __init__(self):
        # Kiểm tra API Key nạp vào service
        key_preview = settings.GEMINI_API_KEY[:5] + "..." if settings.GEMINI_API_KEY else "None"
        print(f"DEBUG: Initializing PronunciationService with API Key starting with: {key_preview}")
        
        # Tự động tìm model khả dụng để tránh lỗi 404
        available_models = []
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append(m.name)
            print(f"DEBUG: Available models on this API Key: {available_models}")
        except Exception as e:
            print(f"DEBUG: Could not list models: {e}")

        # Ưu tiên chọn model 'gemini-1.5-flash' cứng để được hưởng quota 1500 req/ngày của Free Tier, tránh 429
        target_model = 'models/gemini-1.5-flash'
        if 'models/gemini-1.5-flash' in available_models:
            target_model = 'models/gemini-1.5-flash'
        elif 'models/gemini-flash-latest' in available_models:
            target_model = 'models/gemini-flash-latest'
        elif 'models/gemini-2.0-flash' in available_models:
            target_model = 'models/gemini-2.0-flash'
        elif available_models:
            target_model = available_models[0]
            
        print(f"DEBUG: Selected model for Pronunciation: {target_model}")
        self.model = genai.GenerativeModel(target_model)

    async def analyze_pronunciation(
        self, audio_bytes: bytes, target_text: str, audio_filename: str = "audio.webm"
    ) -> Dict:
        """
        Pipeline tối ưu: Một lần gọi Gemini duy nhất để vừa Transcribe vừa Score.
        Giúp tiết kiệm 50% Quota API (Tránh lỗi 429 Free Tier).
        """
        try:
            suffix = os.path.splitext(audio_filename)[1] or ".webm"
            mime_type = self._detect_mime_type_from_bytes(audio_bytes, suffix)
            
            print(f"DEBUG PronunciationService: Single-call analysis ({len(audio_bytes)} bytes, detected MIME: {mime_type})")

            prompt = f"""You are an expert English pronunciation coach. 
1. Listen to the attached audio and transcribe it exactly.
2. Compare it with the TARGET TEXT: "{target_text}"
3. Score these metrics (0-100): fluency, pronunciation, confidence, intonation.
4. Provide brief feedback for each and an overall summary.

Return your response as a JSON object ONLY:
{{
    "transcribed_text": "<exact transcription>",
    "fluency": <number>,
    "fluency_feedback": "<tip>",
    "pronunciation": <number>,
    "pronunciation_feedback": "<tip>",
    "confidence": <number>,
    "confidence_feedback": "<tip>",
    "intonation": <number>,
    "intonation_feedback": "<tip>",
    "overall_feedback": "<summary>"
}}"""

            response = await self.model.generate_content_async([
                {"mime_type": mime_type, "data": audio_bytes},
                prompt
            ])

            response_text = response.text.strip()
            if response_text.startswith("```"):
                response_text = re.sub(r'^```(?:json)?\s*', '', response_text)
                response_text = re.sub(r'\s*```$', '', response_text)

            result = json.loads(response_text)
            transcribed_text = result.get("transcribed_text", "")

            # Tính word scores (local)
            word_scores = self.calculate_word_scores(target_text, transcribed_text)

            # Đảm bảo không lỗi null/NaN
            def safe_score(val):
                try: return float(val) if val is not None else 0.0
                except: return 0.0

            f_score = safe_score(result.get("fluency", 0))
            p_score = safe_score(result.get("pronunciation", 0))
            c_score = safe_score(result.get("confidence", 0))
            i_score = safe_score(result.get("intonation", 0))
            overall_score = (f_score + p_score + c_score + i_score) / 4.0

            return {
                "overall_score": round(overall_score, 1),
                "transcribed_text": transcribed_text,
                "metrics": [
                    {"metric": "fluency", "score": f_score, "feedback": result.get("fluency_feedback", "")},
                    {"metric": "pronunciation", "score": p_score, "feedback": result.get("pronunciation_feedback", "")},
                    {"metric": "confidence", "score": c_score, "feedback": result.get("confidence_feedback", "")},
                    {"metric": "intonation", "score": i_score, "feedback": result.get("intonation_feedback", "")},
                ],
                "word_scores": word_scores,
                "feedback": result.get("overall_feedback", ""),
            }

        except Exception as e:
            print(f"DEBUG PronunciationService: Analysis error: {str(e)}")
            try:
                # Ghi log lỗi chi tiết phục vụ chẩn đoán
                with open("E:/Project/Hoc/hoc-tieng-anh/backend/error_log.txt", "w", encoding="utf-8") as f:
                    import traceback
                    f.write(f"Exception in PronunciationService: {str(e)}\n")
                    f.write(f"Traceback:\n{traceback.format_exc()}\n")
            except Exception as log_err:
                print(f"DEBUG: Could not write error log: {log_err}")

            if "429" in str(e):
                return {
                    "overall_score": 0.0,
                    "transcribed_text": "Quota Exceeded",
                    "metrics": [],
                    "word_scores": [],
                    "feedback": "Hết quota Gemini (Free Tier). Vui lòng thử lại sau 1 phút.",
                }
            
            return {
                "overall_score": 0.0,
                "transcribed_text": "Error during analysis",
                "metrics": [],
                "word_scores": [],
                "feedback": f"Error: {str(e)}",
            }

    def calculate_word_scores(self, target_text: str, transcribed_text: str) -> List[Dict]:
        """
        So sánh word-level giữa target và transcribed text.
        Sử dụng difflib.SequenceMatcher cho accuracy.
        """
        target_words = self._normalize_text(target_text).split()
        transcribed_words = self._normalize_text(transcribed_text).split()

        if not target_words:
            return []

        # Dùng SequenceMatcher để align words
        matcher = difflib.SequenceMatcher(None, target_words, transcribed_words)
        word_scores = []

        matched_indices = set()
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                for idx in range(i1, i2):
                    word_scores.append({
                        "word": target_words[idx],
                        "is_correct": True,
                        "confidence": 1.0,
                    })
                    matched_indices.add(idx)
            elif tag == 'replace':
                for idx in range(i1, i2):
                    # Tính similarity cho từng word
                    t_word = target_words[idx]
                    if idx - i1 < j2 - j1:
                        s_word = transcribed_words[j1 + (idx - i1)]
                        similarity = difflib.SequenceMatcher(None, t_word, s_word).ratio()
                    else:
                        similarity = 0.0
                    word_scores.append({
                        "word": t_word,
                        "is_correct": similarity > 0.7,
                        "confidence": round(similarity, 2),
                    })
                    matched_indices.add(idx)
            elif tag == 'delete':
                for idx in range(i1, i2):
                    word_scores.append({
                        "word": target_words[idx],
                        "is_correct": False,
                        "confidence": 0.0,
                    })
                    matched_indices.add(idx)

        # Đảm bảo mọi target word đều có score
        for idx, word in enumerate(target_words):
            if idx not in matched_indices:
                word_scores.append({
                    "word": word,
                    "is_correct": False,
                    "confidence": 0.0,
                })

        return word_scores

    async def get_detailed_analysis(
        self, target_text: str, transcribed_text: str, word_scores: List[Dict]
    ) -> Dict:
        """
        Sử dụng Gemini để phân tích pronunciation chi tiết.
        Trả về scores cho 4 metrics + feedback.
        """
        correct_count = sum(1 for w in word_scores if w["is_correct"])
        total_count = len(word_scores) if word_scores else 1
        accuracy = correct_count / total_count

        prompt = f"""You are an expert English pronunciation coach. Analyze the following speaking attempt.

TARGET TEXT: "{target_text}"
TRANSCRIBED TEXT: "{transcribed_text}"
WORD ACCURACY: {correct_count}/{total_count} words correct ({accuracy:.0%})

Score the following metrics from 0 to 100:
1. FLUENCY - How smooth and natural the speech flow was
2. PRONUNCIATION - How accurately each word was pronounced  
3. CONFIDENCE - How confident the speaker sounded (based on word accuracy and completeness)
4. INTONATION - How natural the pitch and rhythm were

Return your response as a JSON object ONLY (no markdown, no code blocks):
{{
    "fluency": <number>,
    "fluency_feedback": "<brief tip to improve fluency>",
    "pronunciation": <number>,
    "pronunciation_feedback": "<brief tip about pronunciation>",
    "confidence": <number>,
    "confidence_feedback": "<brief tip about confidence>",
    "intonation": <number>,
    "intonation_feedback": "<brief tip about intonation>",
    "overall_feedback": "<1-2 sentence summary of performance and main area to improve>"
}}"""

        try:
            response = await self.model.generate_content_async(prompt)
            response_text = response.text.strip()

            # Loại bỏ markdown code block nếu có
            if response_text.startswith("```"):
                response_text = re.sub(r'^```(?:json)?\s*', '', response_text)
                response_text = re.sub(r'\s*```$', '', response_text)

            result = json.loads(response_text)

            # Đảm bảo scores trong range 0-100
            for key in ["fluency", "pronunciation", "confidence", "intonation"]:
                if key in result:
                    result[key] = max(0, min(100, float(result[key])))

            return result

        except Exception as e:
            print(f"PronunciationService: Analysis error: {e}")
            # Fallback: tính scores dựa trên accuracy
            base_score = accuracy * 100
            return {
                "fluency": round(base_score * 0.9, 1),
                "fluency_feedback": "Keep practicing for smoother speech.",
                "pronunciation": round(base_score, 1),
                "pronunciation_feedback": "Focus on clear word pronunciation.",
                "confidence": round(base_score * 0.85, 1),
                "confidence_feedback": "Speak with more confidence.",
                "intonation": round(base_score * 0.8, 1),
                "intonation_feedback": "Work on natural rhythm and pitch.",
                "overall_feedback": f"You got {correct_count}/{total_count} words correct. Keep practicing!",
            }

    def _normalize_text(self, text: str) -> str:
        """Chuẩn hóa text cho comparison."""
        text = text.lower().strip()
        text = re.sub(r'[^\w\s]', '', text)  # Bỏ punctuation
        text = re.sub(r'\s+', ' ', text)     # Chuẩn hóa spaces
        return text

    def _get_mime_type(self, suffix: str) -> str:
        """Trả về MIME type cho audio file."""
        mime_map = {
            ".webm": "audio/webm",
            ".wav": "audio/wav",
            ".mp3": "audio/mpeg",
            ".ogg": "audio/ogg",
            ".m4a": "audio/mp4",
            ".aac": "audio/aac",
            ".flac": "audio/flac",
        }
        return mime_map.get(suffix.lower(), "audio/webm")

    def _detect_mime_type_from_bytes(self, audio_bytes: bytes, fallback_suffix: str) -> str:
        """
        Tự động phát hiện MIME type chính xác của file âm thanh dựa trên Magic Bytes ở đầu file.
        Giúp triệt tiêu hoàn toàn lỗi lệch định dạng giữa Frontend và Backend.
        """
        if not audio_bytes or len(audio_bytes) < 12:
            return "audio/webm"
            
        # EBML Header (WebM / Matroska): 1A 45 DF A3
        if audio_bytes.startswith(b"\x1a\x45\xdf\xa3"):
            return "audio/webm"
            
        # RIFF WAVE Header: RIFF (bytes 0-4) and WAVE (bytes 8-12)
        if audio_bytes.startswith(b"RIFF") and b"WAVE" in audio_bytes[8:12]:
            return "audio/wav"
            
        # MP4/M4A Header: ftyp (bytes 4-8)
        if b"ftyp" in audio_bytes[4:12]:
            return "audio/mp4"
            
        # AAC Header: ADTS frame sync (12 bits: 1111 1111 1111 = FF F)
        if audio_bytes[0] == 0xFF and (audio_bytes[1] & 0xF0) == 0xF0:
            return "audio/aac"
            
        # ID3/MP3 Header
        if audio_bytes.startswith(b"ID3") or (audio_bytes[0] == 0xFF and (audio_bytes[1] & 0xE0) == 0xE0):
            return "audio/mpeg"
            
        # OGG Header: OggS
        if audio_bytes.startswith(b"OggS"):
            return "audio/ogg"
            
        # FLAC Header: fLaC
        if audio_bytes.startswith(b"fLaC"):
            return "audio/flac"
            
        # Nếu không phát hiện được bằng magic bytes, sử dụng fallback dựa vào suffix
        return self._get_mime_type(fallback_suffix)


# Danh sách câu luyện tập theo level
PRACTICE_SENTENCES = [
    # A1 - Beginner (20 sentences)
    {"id": 1, "text": "Hello, how are you?", "level": "A1", "category": "greeting"},
    {"id": 2, "text": "My name is John.", "level": "A1", "category": "greeting"},
    {"id": 3, "text": "Nice to meet you.", "level": "A1", "category": "greeting"},
    {"id": 4, "text": "I like coffee.", "level": "A1", "category": "daily"},
    {"id": 5, "text": "Where is the bathroom?", "level": "A1", "category": "travel"},
    {"id": 6, "text": "Thank you very much.", "level": "A1", "category": "greeting"},
    {"id": 7, "text": "What time is it?", "level": "A1", "category": "daily"},
    {"id": 8, "text": "I am a student.", "level": "A1", "category": "daily"},
    {"id": 9, "text": "This is my friend.", "level": "A1", "category": "social"},
    {"id": 10, "text": "I live in a big house.", "level": "A1", "category": "daily"},
    {"id": 11, "text": "Can you help me?", "level": "A1", "category": "social"},
    {"id": 12, "text": "I have a cat.", "level": "A1", "category": "hobby"},
    {"id": 13, "text": "The sun is hot today.", "level": "A1", "category": "weather"},
    {"id": 14, "text": "I want to drink water.", "level": "A1", "category": "daily"},
    {"id": 15, "text": "She is my sister.", "level": "A1", "category": "family"},
    {"id": 16, "text": "I study English every day.", "level": "A1", "category": "daily"},
    {"id": 17, "text": "Good morning, everyone.", "level": "A1", "category": "greeting"},
    {"id": 18, "text": "The book is on the desk.", "level": "A1", "category": "daily"},
    {"id": 19, "text": "I am happy to see you.", "level": "A1", "category": "social"},
    {"id": 20, "text": "Where do you live?", "level": "A1", "category": "social"},

    # A2 - Elementary (20 sentences)
    {"id": 21, "text": "I would like to order a coffee, please.", "level": "A2", "category": "daily"},
    {"id": 22, "text": "Could you help me find the train station?", "level": "A2", "category": "travel"},
    {"id": 23, "text": "I have been studying English for two years.", "level": "A2", "category": "daily"},
    {"id": 24, "text": "The weather is beautiful today.", "level": "A2", "category": "daily"},
    {"id": 25, "text": "Can I have the menu, please?", "level": "A2", "category": "travel"},
    {"id": 26, "text": "I usually wake up at seven o'clock.", "level": "A2", "category": "daily"},
    {"id": 27, "text": "I went to the cinema yesterday.", "level": "A2", "category": "hobby"},
    {"id": 28, "text": "Do you want to go for a walk?", "level": "A2", "category": "social"},
    {"id": 29, "text": "I am looking for a new job.", "level": "A2", "category": "business"},
    {"id": 30, "text": "He is taller than his brother.", "level": "A2", "category": "social"},
    {"id": 31, "text": "What are you doing this weekend?", "level": "A2", "category": "social"},
    {"id": 32, "text": "I need to buy some vegetables.", "level": "A2", "category": "daily"},
    {"id": 33, "text": "Could you pass me the salt?", "level": "A2", "category": "daily"},
    {"id": 34, "text": "I think this movie is very funny.", "level": "A2", "category": "hobby"},
    {"id": 35, "text": "My phone is out of battery.", "level": "A2", "category": "daily"},
    {"id": 36, "text": "I forgot to bring my umbrella.", "level": "A2", "category": "weather"},
    {"id": 37, "text": "She speaks English very well.", "level": "A2", "category": "social"},
    {"id": 38, "text": "How much does this cost?", "level": "A2", "category": "travel"},
    {"id": 39, "text": "I am going to visit my parents.", "level": "A2", "category": "family"},
    {"id": 40, "text": "The park is across the street.", "level": "A2", "category": "travel"},

    # B1 - Intermediate (20 sentences)
    {"id": 41, "text": "I think technology has changed the way we communicate.", "level": "B1", "category": "discussion"},
    {"id": 42, "text": "If I had more time, I would travel around the world.", "level": "B1", "category": "discussion"},
    {"id": 43, "text": "She suggested that we should meet at the restaurant.", "level": "B1", "category": "daily"},
    {"id": 44, "text": "The presentation went better than I expected.", "level": "B1", "category": "business"},
    {"id": 45, "text": "I am looking forward to meeting you next week.", "level": "B1", "category": "business"},
    {"id": 46, "text": "Environmental protection is everyone's responsibility.", "level": "B1", "category": "discussion"},
    {"id": 47, "text": "I have been working at this company since 2015.", "level": "B1", "category": "business"},
    {"id": 48, "text": "It is important to learn from our mistakes.", "level": "B1", "category": "discussion"},
    {"id": 49, "text": "Could you please clarify what you mean by that?", "level": "B1", "category": "social"},
    {"id": 50, "text": "I am not used to driving in heavy traffic.", "level": "B1", "category": "daily"},
    {"id": 51, "text": "The number of people using the internet is increasing.", "level": "B1", "category": "discussion"},
    {"id": 52, "text": "I am planning to move to another city next month.", "level": "B1", "category": "daily"},
    {"id": 53, "text": "We need to find a solution to this problem.", "level": "B1", "category": "business"},
    {"id": 54, "text": "I apologize for the delay in my response.", "level": "B1", "category": "social"},
    {"id": 55, "text": "She is very passionate about her work.", "level": "B1", "category": "social"},
    {"id": 56, "text": "I strongly agree with your point of view.", "level": "B1", "category": "discussion"},
    {"id": 57, "text": "The government should invest more in public transport.", "level": "B1", "category": "discussion"},
    {"id": 58, "text": "I was surprised by the news I heard today.", "level": "B1", "category": "social"},
    {"id": 59, "text": "It takes about forty minutes to get to the airport.", "level": "B1", "category": "travel"},
    {"id": 60, "text": "I am responsible for managing the project team.", "level": "B1", "category": "business"},

    # B2 - Upper Intermediate (20 sentences)
    {"id": 61, "text": "Although the project was challenging, we managed to deliver it on time.", "level": "B2", "category": "business"},
    {"id": 62, "text": "The research indicates that regular exercise significantly improves mental health.", "level": "B2", "category": "discussion"},
    {"id": 63, "text": "I strongly believe that education should be accessible to everyone.", "level": "B2", "category": "discussion"},
    {"id": 64, "text": "Would you mind elaborating on the key findings of your report?", "level": "B2", "category": "business"},
    {"id": 65, "text": "The consequences of global warming are becoming increasingly evident.", "level": "B2", "category": "discussion"},
    {"id": 66, "text": "He managed to persuade the investors to support the new venture.", "level": "B2", "category": "business"},
    {"id": 67, "text": "The study suggests that there is a strong link between diet and health.", "level": "B2", "category": "discussion"},
    {"id": 68, "text": "I am writing to express my dissatisfaction with the service I received.", "level": "B2", "category": "social"},
    {"id": 69, "text": "It is highly recommended that you book your tickets in advance.", "level": "B2", "category": "travel"},
    {"id": 70, "text": "The company has experienced significant growth over the past decade.", "level": "B2", "category": "business"},
    {"id": 71, "text": "Artificial intelligence is expected to revolutionize many industries.", "level": "B2", "category": "discussion"},
    {"id": 72, "text": "I was under the impression that the meeting had been canceled.", "level": "B2", "category": "social"},
    {"id": 73, "text": "The project requires a high level of technical expertise.", "level": "B2", "category": "business"},
    {"id": 74, "text": "We should take into account the environmental impact of our decisions.", "level": "B2", "category": "discussion"},
    {"id": 75, "text": "The manager is known for her exceptional leadership skills.", "level": "B2", "category": "business"},
    {"id": 76, "text": "I am looking for a challenging role that offers career progression.", "level": "B2", "category": "business"},
    {"id": 77, "text": "The statistics reveal a steady decline in unemployment rates.", "level": "B2", "category": "discussion"},
    {"id": 78, "text": "It is essential to stay up to date with the latest market trends.", "level": "B2", "category": "business"},
    {"id": 79, "text": "The new regulations aim to improve safety standards in the workplace.", "level": "B2", "category": "business"},
    {"id": 80, "text": "I would like to take this opportunity to thank you for your support.", "level": "B2", "category": "social"},

    # IELTS Speaking - Part 1 (10 sentences)
    {"id": 81, "text": "I live in a vibrant neighborhood with many local amenities.", "level": "B2", "category": "ielts_p1"},
    {"id": 82, "text": "One of my favorite hobbies is capturing beautiful landscapes through photography.", "level": "B2", "category": "ielts_p1"},
    {"id": 83, "text": "My hometown is famous for its historical landmarks and delicious street food.", "level": "B1", "category": "ielts_p1"},
    {"id": 84, "text": "I find it challenging to balance my work and personal life effectively.", "level": "B2", "category": "ielts_p1"},
    {"id": 85, "text": "Public transport in my city is quite efficient and affordable for residents.", "level": "B1", "category": "ielts_p1"},
    {"id": 86, "text": "I prefer reading physical books rather than using an electronic device.", "level": "B1", "category": "ielts_p1"},
    {"id": 87, "text": "Technology has significantly revolutionized the way we interact with each other.", "level": "B2", "category": "ielts_p1"},
    {"id": 88, "text": "I usually enjoy spending my weekends exploring the great outdoors.", "level": "A2", "category": "ielts_p1"},
    {"id": 89, "text": "My primary goal is to achieve a high band score in the IELTS exam.", "level": "B2", "category": "ielts_p1"},
    {"id": 90, "text": "Working in a team allows for a diverse range of perspectives and ideas.", "level": "B2", "category": "ielts_p1"},

    # IELTS Speaking - Part 2 (20 sentences)
    {"id": 91, "text": "I would like to describe a traditional festival that is celebrated in my country.", "level": "B2", "category": "ielts_p2"},
    {"id": 92, "text": "The event takes place annually and attracts thousands of visitors from all over.", "level": "B2", "category": "ielts_p2"},
    {"id": 93, "text": "It was a truly memorable experience that I will cherish for a lifetime.", "level": "B2", "category": "ielts_p2"},
    {"id": 94, "text": "The atmosphere was incredibly electric and filled with joy and excitement.", "level": "B2", "category": "ielts_p2"},
    {"id": 95, "text": "I first heard about this place through a close friend of mine who lives there.", "level": "B1", "category": "ielts_p2"},
    {"id": 96, "text": "What impressed me the most was the stunning architecture and the friendly locals.", "level": "B2", "category": "ielts_p2"},
    {"id": 97, "text": "I have been planning to visit this destination for quite a long time now.", "level": "B1", "category": "ielts_p2"},
    {"id": 98, "text": "The journey was quite long, but the scenic views made it absolutely worth it.", "level": "B2", "category": "ielts_p2"},
    {"id": 99, "text": "I would recommend this book to anyone who is interested in historical fiction.", "level": "B1", "category": "ielts_p2"},
    {"id": 100, "text": "The protagonist of the story is a very determined and courageous individual.", "level": "B2", "category": "ielts_p2"},
    {"id": 101, "text": "It taught me a valuable lesson about the importance of perseverance and hard work.", "level": "B2", "category": "ielts_p2"},
    {"id": 102, "text": "The movie was directed by a world-renowned filmmaker and received critical acclaim.", "level": "B2", "category": "ielts_p2"},
    {"id": 103, "text": "I felt a great sense of accomplishment after finishing the difficult task.", "level": "B2", "category": "ielts_p2"},
    {"id": 104, "text": "The scenery was so breathtaking that I couldn't stop taking pictures.", "level": "B2", "category": "ielts_p2"},
    {"id": 105, "text": "One of the highlights of the trip was trying the local traditional cuisine.", "level": "B1", "category": "ielts_p2"},
    {"id": 106, "text": "The person I admire most is someone who has dedicated their life to charity.", "level": "B2", "category": "ielts_p2"},
    {"id": 107, "text": "This technological device has made my daily life much more convenient and efficient.", "level": "B2", "category": "ielts_p2"},
    {"id": 108, "text": "I was initially very nervous, but I eventually managed to stay calm and focused.", "level": "B2", "category": "ielts_p2"},
    {"id": 109, "text": "The project required a lot of collaboration and effective communication among team members.", "level": "B2", "category": "ielts_p2"},
    {"id": 110, "text": "I am looking forward to seeing how this city will evolve in the future.", "level": "B1", "category": "ielts_p2"},

    # IELTS Speaking - Part 3 (20 sentences)
    {"id": 111, "text": "From my perspective, social media has a profound impact on modern communication.", "level": "B2", "category": "ielts_p3"},
    {"id": 112, "text": "There are several factors that contribute to the increasing levels of urban pollution.", "level": "C1", "category": "ielts_p3"},
    {"id": 113, "text": "It is widely believed that education is the most powerful tool for social change.", "level": "B2", "category": "ielts_p3"},
    {"id": 114, "text": "The government should implement stricter regulations to protect the environment.", "level": "B2", "category": "ielts_p3"},
    {"id": 115, "text": "Globalization has led to a more interconnected world, but it also has its drawbacks.", "level": "C1", "category": "ielts_p3"},
    {"id": 116, "text": "In many cultures, family values play a crucial role in shaping an individual's character.", "level": "B2", "category": "ielts_p3"},
    {"id": 117, "text": "The rapid advancement of artificial intelligence raises many ethical concerns.", "level": "C1", "category": "ielts_p3"},
    {"id": 118, "text": "Economic development should not come at the expense of environmental sustainability.", "level": "C1", "category": "ielts_p3"},
    {"id": 119, "text": "The influence of advertising on consumer behavior is a topic of intense debate.", "level": "B2", "category": "ielts_p3"},
    {"id": 120, "text": "Many people argue that the traditional education system needs a major overhaul.", "level": "C1", "category": "ielts_p3"},
    {"id": 121, "text": "The benefits of tourism are significant, but it can also lead to cultural degradation.", "level": "B2", "category": "ielts_p3"},
    {"id": 122, "text": "It is essential for young people to develop critical thinking skills in the digital age.", "level": "C1", "category": "ielts_p3"},
    {"id": 123, "text": "The gap between the rich and the poor is widening in many developed countries.", "level": "C1", "category": "ielts_p3"},
    {"id": 124, "text": "Remote work has become more prevalent, offering both flexibility and challenges.", "level": "B2", "category": "ielts_p3"},
    {"id": 125, "text": "The importance of preserving cultural heritage cannot be overstated.", "level": "C1", "category": "ielts_p3"},
    {"id": 126, "text": "Public health initiatives are vital for preventing the spread of infectious diseases.", "level": "B2", "category": "ielts_p3"},
    {"id": 127, "text": "The role of the media in a democratic society is to provide objective information.", "level": "C1", "category": "ielts_p3"},
    {"id": 128, "text": "Urbanization has resulted in the loss of many green spaces in major cities.", "level": "B2", "category": "ielts_p3"},
    {"id": 129, "text": "Technological innovation is key to solving many of the world's current problems.", "level": "C1", "category": "ielts_p3"},
    {"id": 130, "text": "The future of the workforce will likely be shaped by automation and robotics.", "level": "C1", "category": "ielts_p3"},

    # IELTS Speaking - Part 4 (Academic/Advanced) (20 sentences)
    {"id": 131, "text": "The theoretical framework of this research is based on a multidisciplinary approach.", "level": "C1", "category": "ielts_p4"},
    {"id": 132, "text": "Empirical evidence suggests that there is a significant correlation between the two variables.", "level": "C1", "category": "ielts_p4"},
    {"id": 133, "text": "The socio-economic implications of the policy change require careful consideration.", "level": "C1", "category": "ielts_p4"},
    {"id": 134, "text": "Sustainable development necessitates a balance between economic growth and ecological integrity.", "level": "C2", "category": "ielts_p4"},
    {"id": 135, "text": "The fundamental principles of international law are designed to maintain global order.", "level": "C1", "category": "ielts_p4"},
    {"id": 136, "text": "The cognitive development of children is influenced by both genetic and environmental factors.", "level": "C1", "category": "ielts_p4"},
    {"id": 137, "text": "The historical context of the event provides a deeper understanding of its significance.", "level": "C1", "category": "ielts_p4"},
    {"id": 138, "text": "The implementation of the strategy encountered several unforeseen obstacles.", "level": "C1", "category": "ielts_p4"},
    {"id": 139, "text": "Scientific research is essential for addressing the challenges of climate change.", "level": "C1", "category": "ielts_p4"},
    {"id": 140, "text": "The ethical dilemmas posed by biotechnology require a comprehensive regulatory framework.", "level": "C2", "category": "ielts_p4"},
    {"id": 141, "text": "The global financial system is characterized by its complexity and interconnectedness.", "level": "C1", "category": "ielts_p4"},
    {"id": 142, "text": "The preservation of biodiversity is a critical issue for the future of our planet.", "level": "C1", "category": "ielts_p4"},
    {"id": 143, "text": "The transition to renewable energy sources is a major priority for many nations.", "level": "C1", "category": "ielts_p4"},
    {"id": 144, "text": "The concept of corporate social responsibility has gained significant traction in recent years.", "level": "C1", "category": "ielts_p4"},
    {"id": 145, "text": "The impact of artificial intelligence on the labor market is a subject of ongoing debate.", "level": "C1", "category": "ielts_p4"},
    {"id": 146, "text": "The promotion of gender equality is a fundamental human rights objective.", "level": "C1", "category": "ielts_p4"},
    {"id": 147, "text": "The effectiveness of the educational intervention was evaluated through a randomized controlled trial.", "level": "C2", "category": "ielts_p4"},
    {"id": 148, "text": "The integration of technology in the classroom has transformed the learning experience.", "level": "C1", "category": "ielts_p4"},
    {"id": 149, "text": "The causes of social inequality are multifaceted and deeply rooted in historical structures.", "level": "C2", "category": "ielts_p4"},
    {"id": 150, "text": "The pursuit of scientific knowledge is driven by curiosity and the desire to understand the world.", "level": "C1", "category": "ielts_p4"},

    # Additional IELTS Part 1 (10 sentences)
    {"id": 151, "text": "I enjoy listening to a wide variety of music genres, from classical to modern pop.", "level": "B1", "category": "ielts_p1"},
    {"id": 152, "text": "My daily routine usually starts with a healthy breakfast and a quick exercise session.", "level": "B1", "category": "ielts_p1"},
    {"id": 153, "text": "I find that spending time in nature helps me to relax and clear my mind.", "level": "B1", "category": "ielts_p1"},
    {"id": 154, "text": "Learning a new language opens up many opportunities for travel and career growth.", "level": "B2", "category": "ielts_p1"},
    {"id": 155, "text": "I am particularly fond of traditional dishes that are passed down through generations.", "level": "B2", "category": "ielts_p1"},
    {"id": 156, "text": "The weather in my city can be quite unpredictable, especially during the spring season.", "level": "B1", "category": "ielts_p1"},
    {"id": 157, "text": "I believe that maintaining a healthy work-life balance is crucial for overall well-being.", "level": "B2", "category": "ielts_p1"},
    {"id": 158, "text": "Socializing with friends and family is one of my favorite ways to spend my free time.", "level": "B1", "category": "ielts_p1"},
    {"id": 159, "text": "I often use the internet to stay informed about current events and global news.", "level": "B1", "category": "ielts_p1"},
    {"id": 160, "text": "My goal is to travel to different countries and experience diverse cultures firsthand.", "level": "B2", "category": "ielts_p1"},
]


# Initialize service singleton
pronunciation_service = PronunciationService()
print(f"DEBUG: Practice sentences loaded: {len(PRACTICE_SENTENCES)}")

# Log sentence count
print(f"DEBUG: Practice sentences loaded: {len(PRACTICE_SENTENCES)}")
