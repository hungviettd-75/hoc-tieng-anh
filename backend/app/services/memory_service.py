from pinecone import Pinecone
from app.core.config import settings
from app.services.ai_service import gemini_service
from typing import List, Dict, Any
import time

class MemoryService:
    def __init__(self):
        self.index = None
        if not settings.PINECONE_API_KEY or settings.PINECONE_API_KEY == "your_actual_api_key_here":
            print("WARNING: Pinecone API Key is not set or using placeholder. Memory features will be disabled.")
            return

        try:
            self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
            self.index_name = settings.PINECONE_INDEX_NAME
            
            # Kiểm tra xem index có tồn tại không
            existing_indexes = [idx.name for idx in self.pc.list_indexes()]
            if self.index_name not in existing_indexes:
                print(f"ERROR: Pinecone index '{self.index_name}' not found.")
                print(f"TIP: Please create an index named '{self.index_name}' with Dimension: 768 and Metric: Cosine in your Pinecone dashboard.")
                self.index = None
                return

            self.index = self.pc.Index(self.index_name)
            print(f"DEBUG: Successfully connected to Pinecone index: {self.index_name}")
        except Exception as e:
            if "404" in str(e):
                print(f"ERROR: Pinecone index '{self.index_name}' does not exist on your account.")
            else:
                print(f"ERROR: Failed to initialize Pinecone: {e}")
            self.index = None

    async def store_memory(self, user_id: int, text: str, metadata: Dict[str, Any] = None):
        """
        Lưu một ký ức mới vào Pinecone.
        """
        if self.index is None:
            return None
            
        try:
            embedding = await gemini_service.get_embedding(text)
            
            vector_id = f"user_{user_id}_{int(time.time())}"
            
            if metadata is None:
                metadata = {}
            
            metadata.update({
                "user_id": user_id,
                "text": text,
                "timestamp": time.time()
            })
            
            self.index.upsert(vectors=[(vector_id, embedding, metadata)])
            return vector_id
        except Exception as e:
            print(f"WARN: Failed to store memory: {e}")
            return None

    async def retrieve_relevant_memories(self, user_id: int, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Tìm kiếm các ký ức liên quan dựa trên query.
        """
        if self.index is None:
            return []
            
        try:
            query_embedding = await gemini_service.get_embedding(query)
            
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                filter={"user_id": {"$eq": user_id}},
                include_metadata=True
            )
            
            memories = []
            for match in results.matches:
                if match.score > 0.7: # Ngưỡng tin cậy
                    memories.append({
                        "text": match.metadata["text"],
                        "score": match.score,
                        "metadata": match.metadata
                    })
            
            return memories
        except Exception as e:
            print(f"WARN: Failed to retrieve relevant memories: {e}")
            return []

    async def summarize_and_store_conversation(self, user_id: int, messages: List[Dict[str, str]]):
        """
        Tóm tắt cuộc hội thoại và lưu vào bộ nhớ dài hạn.
        """
        if not messages:
            return
            
        conversation_text = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
        
        prompt = (
            f"Please summarize the following English learning conversation. "
            f"Focus on: 1. Learning goals discussed, 2. Vocabulary the user learned or struggled with, "
            f"3. Grammar mistakes made, 4. Speaking habits or personal interests revealed.\n\n"
            f"Conversation:\n{conversation_text}\n\n"
            f"Summary for AI Long-term Memory:"
        )
        
        # Dùng Gemini để tóm tắt
        response = await gemini_service.model.generate_content_async(prompt)
        summary = response.text
        
        await self.store_memory(user_id, summary, {"type": "session_summary"})
        return summary

memory_service = MemoryService()
