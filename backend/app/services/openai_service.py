import openai
from app.core.config import settings
from typing import List, Dict, AsyncGenerator
import json

class OpenAIService:
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.system_instruction = (
            "You are an expert AI English Coach. Your goal is to help users improve their English fluency.\n"
            "1. Be empathetic, encouraging, and professional.\n"
            "2. If the user makes a grammar mistake, provide a brief correction at the end of your response using the format: [CORRECTION] ...\n"
            "3. Use a level of English suitable for the user.\n"
            "4. Keep responses concise to facilitate a back-and-forth conversation.\n"
            "5. Always respond in English, but you can explain complex terms in Vietnamese if necessary."
        )

    async def get_streaming_response(self, history: List[Dict[str, str]], user_message: str) -> AsyncGenerator[str, None]:
        messages = [{"role": "system", "content": self.system_instruction}]
        for h in history:
            messages.append(h)
        messages.append({"role": "user", "content": user_message})

        stream = await self.client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=messages,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def get_correction(self, user_message: str) -> Dict:
        """
        Phân tích và sửa lỗi ngữ pháp cho một tin nhắn cụ thể.
        """
        prompt = f"Analyze the following English sentence and correct any grammar mistakes. If it's perfect, say 'Perfect!'. Sentence: '{user_message}'"
        
        response = await self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
        )
        
        return {"correction": response.choices[0].message.content}

openai_service = OpenAIService()
