import asyncio
import os
import sys

# Thêm directory hiện tại vào sys.path để import được app
sys.path.append(os.getcwd())

from app.services.ai_service import gemini_service

async def main():
    text = "I has a dog"
    print(f"Testing text: {text}")
    result = await gemini_service.get_correction(text)
    print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
