import asyncio
import edge_tts

async def main():
    try:
        voices = await edge_tts.VoicesManager.create()
        # Loc cac giong tieng Viet (vi)
        vi_voices = voices.find(Locale="vi-VN")
        print("Available Vietnamese voices:")
        for v in vi_voices:
            print(f"- {v['Name']} (Gender: {v['Gender']})")
            
        # Loc cac giong tieng Anh (en)
        en_voices = voices.find(Locale="en-GB")
        print("\nAvailable British English voices:")
        for v in en_voices:
            print(f"- {v['Name']} (Gender: {v['Gender']})")
    except Exception as e:
        print(f"Error list voices: {e}")

if __name__ == "__main__":
    asyncio.run(main())
