import edge_tts
import asyncio

async def test(text, voice):
    print(f"Testing with {voice}: '{text}'")
    try:
        communicate = edge_tts.Communicate(text, voice)
        audio = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio += chunk["data"]
        if audio:
            print(f"-> SUCCESS: {len(audio)} bytes")
            return True
        else:
            print("-> FAILED: empty audio")
            return False
    except Exception as e:
        print(f"-> EXCEPTION: {e}")
        return False

async def main():
    text_list = [
        "Chào bạn! Hôm nay chúng ta sẽ cùng luyện chủ đề Du lịch nhé! Bạn cứ thoải mái nhé, mình bắt đầu trước!",
        "Hôm nay chúng ta sẽ cùng luyện chủ đề Du lịch nhé",
        "Bạn cứ thoải mái nhé, mình bắt đầu trước",
        "(Dịch: Chào buổi tối! Chào mừng đến khách sạn. Bạn đã đặt phòng chưa?)",
        "Bạn có thể trả lời:",
        "Good evening! Welcome to our hotel. Do you have a reservation?"
    ]
    
    voices = ["en-US-AndrewMultilingualNeural", "en-US-AvaMultilingualNeural", "en-US-BrianMultilingualNeural"]
    
    for voice in voices:
        print(f"\n===== TESTING VOICE: {voice} =====")
        all_ok = True
        for text in text_list:
            ok = await test(text, voice)
            if not ok:
                all_ok = False
        print(f"Result for {voice}: {'ALL SUCCESS' if all_ok else 'SOME FAILED'}")

if __name__ == "__main__":
    asyncio.run(main())
