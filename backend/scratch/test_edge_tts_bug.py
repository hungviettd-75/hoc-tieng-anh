import edge_tts
import asyncio

async def test(text, voice="vi-VN-NamMinhNeural"):
    print(f"Testing text: '{text}'")
    try:
        communicate = edge_tts.Communicate(text, voice)
        audio = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio += chunk["data"]
        if audio:
            print(f"-> SUCCESS: {len(audio)} bytes")
        else:
            print("-> FAILED: empty audio")
    except Exception as e:
        print(f"-> EXCEPTION: {e}")

async def main():
    print("--- Test 1: Full text ---")
    await test("Chào bạn! Hôm nay chúng ta sẽ cùng luyện chủ đề Du lịch nhé! Bạn cứ thoải mái nhé, mình bắt đầu trước!")
    
    print("\n--- Test 2: Split by sentence ---")
    await test("Chào bạn")
    await test("Hôm nay chúng ta sẽ cùng luyện chủ đề Du lịch nhé")
    await test("Bạn cứ thoải mái nhé, mình bắt đầu trước")
    
    print("\n--- Test 3: With punctuation ---")
    await test("Chào bạn!")
    await test("Hôm nay chúng ta sẽ cùng luyện chủ đề Du lịch nhé!")
    
    print("\n--- Test 4: Other sentences ---")
    await test("(Dịch: Chào buổi tối! Chào mừng đến khách sạn. Bạn đã đặt phòng chưa?)")
    await test("Bạn có thể trả lời:")
    await test("(Dịch: Chào buổi tối! Chào mừng đến khách sạn. Bạn đã đặt phòng chưa?) Bạn có thể trả lời:")

if __name__ == "__main__":
    asyncio.run(main())
