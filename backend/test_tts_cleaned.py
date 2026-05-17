import edge_tts
import asyncio
import re

async def main():
    text = "Chào bạn, tôi là AI English Coach. Bạn phát âm chữ 'student' chưa đúng. Phải phát âm là: 'student' /ˈstjuːdnt/. Chú ý âm đuôi 't' nhé."
    
    # Simulate the cleaning in speaking.py
    clean_text = re.sub(r'/[^/]+/', '', text)
    clean_text = re.sub(r'[^\w\s,.?!:;\'"()]', '', clean_text)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    print(f"Cleaned text: {clean_text}")
    
    voice = "en-US-AndrewMultilingualNeural"
    output = "test_vi_cleaned.mp3"
    
    print(f"Synthesizing with {voice}...")
    communicate = edge_tts.Communicate(clean_text, voice)
    await communicate.save(output)
    print(f"Saved to {output}")

if __name__ == "__main__":
    asyncio.run(main())
