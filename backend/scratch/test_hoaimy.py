import edge_tts
import asyncio

async def test_voice(voice_name):
    text = "Chào bạn! Hôm nay chúng ta sẽ cùng luyện chủ đề Du lịch nhé!"
    output = f"test_{voice_name.replace(':', '_').replace('-', '_')}.mp3"
    print(f"\nSynthesizing with {voice_name}...")
    try:
        communicate = edge_tts.Communicate(text, voice_name)
        await communicate.save(output)
        print(f"-> SUCCESS for {voice_name}!")
        return True
    except Exception as e:
        print(f"-> FAILED for {voice_name}: {e}")
        return False

async def main():
    voices = ["vi-VN-HoaiMyNeural", "vi-VN-NamMinhNeural", "en-US-AvaMultilingualNeural", "en-US-AndrewMultilingualNeural", "en-US-BrianMultilingualNeural"]
    for v in voices:
        await test_voice(v)

if __name__ == "__main__":
    asyncio.run(main())
