import asyncio
import re
import edge_tts

async def test_hybrid_tts_logic():
    text = (
        "Chào bạn! Hôm nay chúng ta sẽ cùng luyện chủ đề Du lịch nhé! "
        "Bạn cứ thoải mái nhé, mình bắt đầu trước! 😊 "
        "Good evening! Welcome to our hotel. Do you have a reservation? "
        "(Dịch: Chào buổi tối! Chào mừng đến khách sạn. Bạn đã đặt phòng chưa?) "
        "💡 Bạn có thể trả lời: \"Yes, I have a reservation.\" (Dịch: Vâng, tôi đã đặt phòng.)"
    )
    
    # Mô phỏng logic làm sạch của speaking.py
    text = re.sub(r'/[^/]+/', '', text) # Xóa IPA
    text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
    text = re.sub(r'[❌✅💡📝🗣️😊👍🌟💪✨🎉👏📊📌📍⚠️•|*#\-]', '', text)
    
    # 2. Tách văn bản thành các phân đoạn ngôn ngữ thông minh
    sentences = re.split(r'(?<=[.?!])\s+|\n+', text)
    raw_parts = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        sub_parts = re.split(r'([\"\'“][^\"\'“”]+[\"\'”]|(?<=:\s)[A-Za-z\s,\.\?\!]+(?=\s*(?:\(|$)))', sentence)
        
        for sub in sub_parts:
            if not sub:
                continue
            sub = sub.strip()
            sub_clean = re.sub(r'^[\"\'“]|[\"\'”]$', '', sub).strip()
            if not sub_clean:
                continue
                
            is_vi = bool(re.search(r'[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệđìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ]', sub_clean.lower()))
            lang = "vi" if is_vi else "en"
            raw_parts.append({"text": sub_clean, "lang": lang})

    if not raw_parts:
        raw_parts = [{"text": text, "lang": "vi"}]

    # 3. Gộp các phần cùng ngôn ngữ
    parts = []
    current_part = raw_parts[0]
    for next_part in raw_parts[1:]:
        if next_part["lang"] == current_part["lang"]:
            current_part["text"] += " " + next_part["text"]
        else:
            parts.append(current_part)
            current_part = next_part
    parts.append(current_part)

    print("Parsed Parts:")
    for idx, part in enumerate(parts):
        print(f"[{idx}] Lang: {part['lang']} -> Text: '{part['text']}'")
        
    # Thử gọi edge-tts tạo file âm thanh ghép nối
    raw_pcm_data = bytearray()
    for part in parts:
        p_text = part["text"]
        p_lang = part["lang"]
        if not re.search(r'[a-zA-ZÀ-ỹ0-9]', p_text):
            continue
            
        v_name = "en-US-AvaMultilingualNeural" if p_lang == "vi" else "en-GB-SoniaNeural"
        print(f"Synthesizing part: [{p_lang}] '{p_text}' with {v_name}...")
        try:
            communicate = edge_tts.Communicate(p_text, v_name)
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            
            if audio_data and audio_data.startswith(b"ID3"):
                size_bytes = audio_data[6:10]
                tag_size = (size_bytes[0] << 21) | (size_bytes[1] << 14) | (size_bytes[2] << 7) | size_bytes[3]
                total_id3_size = 10 + tag_size
                audio_data = audio_data[total_id3_size:]
                
            if audio_data:
                raw_pcm_data.extend(audio_data)
                print(f"-> Part synthesized successfully ({len(audio_data)} bytes)")
        except Exception as e:
            print(f"-> Part failed: {e}")
            
    if raw_pcm_data:
        with open("test_hybrid_output.mp3", "wb") as f:
            f.write(raw_pcm_data)
        print("Successfully saved hybrid test audio to test_hybrid_output.mp3")

if __name__ == "__main__":
    asyncio.run(test_hybrid_tts_logic())
