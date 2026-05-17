import edge_tts
import asyncio

async def main():
    text = "Chào bạn, tôi là AI English Coach. Bạn phát âm chữ 'student' chưa đúng. Phải phát âm là: 'student' /ˈstjuːdnt/. Chú ý âm đuôi 't' nhé."
    voice = "en-US-AndrewMultilingualNeural"
    output = "test_vi.mp3"
    
    print(f"Synthesizing with {voice}...")
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output)
    print(f"Saved to {output}")

if __name__ == "__main__":
    asyncio.run(main())
