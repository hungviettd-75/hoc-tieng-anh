import google.generativeai as genai
import os
import sys

# Add parent dir to path to import app.core.config
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.core.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)
result = genai.embed_content(model="models/gemini-embedding-001", content="test")
print(f"Dimension: {len(result['embedding'])}")
