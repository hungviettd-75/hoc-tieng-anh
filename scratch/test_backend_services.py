import sys
import os
import asyncio

# Thiết lập mã hóa utf-8 cho console output trên Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Thêm thư mục backend vào sys.path để có thể import
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

async def test_services():
    print("--- TESTING BACKEND SERVICES ---")
    try:
        from app.core.config import settings
        key_preview = settings.GEMINI_API_KEY[:5] + "..." if settings.GEMINI_API_KEY else "None"
        print(f"Loaded GEMINI_API_KEY: {key_preview}")
        print(f"Loaded PINECONE_API_KEY: {settings.PINECONE_API_KEY[:5] + '...' if settings.PINECONE_API_KEY else 'None'}")
        
        # Test Gemini Service initialization
        print("\n1. Initializing GeminiService...")
        from app.services.ai_service import gemini_service
        print("GeminiService initialized.")
        
        # Test basic Gemini generation
        print("\n2. Calling Gemini streaming response...")
        response_generator = gemini_service.get_streaming_response(
            history=[],
            user_message="Hello, I want to practice English. Say a short welcome in Vietnamese."
        )
        async for chunk in response_generator:
            print(chunk, end="", flush=True)
        print("\nGemini streaming test completed successfully.")
        
        # Test Memory Service initialization
        print("\n3. Initializing MemoryService...")
        from app.services.memory_service import memory_service
        print("MemoryService initialized.")
        
        print("\n4. Calling MemoryService search...")
        memories = await memory_service.retrieve_relevant_memories(user_id=1, query="hello")
        print(f"Retrieved memories: {memories}")
        
        print("\n--- ALL TESTS COMPLETED SUCCESSFULLY ---")
    except Exception as e:
        print("\n--- TEST FAILED ---")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_services())
