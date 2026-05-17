import asyncio
import sys
import os
sys.path.append(os.getcwd())
from app.services.ai_service import gemini_service

async def test():
    try:
        res = await gemini_service.get_structured_correction("I want go to school")
        print("Result:", res)
    except Exception as e:
        print("Error:", e)

asyncio.run(test())
