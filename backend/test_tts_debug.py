import asyncio
import edge_tts

async def main():
    p_text = "Chào bạn nhỏ! What is your favorite food?"
    v_name = "en-US-AvaMultilingualNeural"
    
    print("Testing edge_tts with en-US-AvaMultilingualNeural...")
    try:
        communicate = edge_tts.Communicate(p_text, v_name)
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        print(f"SUCCESS: Generated {len(audio_data)} bytes of audio data!")
    except Exception as e:
        print(f"FAILED: edge_tts error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
