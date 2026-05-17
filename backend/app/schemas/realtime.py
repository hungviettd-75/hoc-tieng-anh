"""
Realtime WebSocket message schemas.
"""
from pydantic import BaseModel
from typing import List, Optional


class RealtimeCorrectionSchema(BaseModel):
    error_type: str          # "pronunciation" | "grammar"
    severity: str            # "low" | "medium" | "high"
    original: str
    correction: str
    ipa: str = ""
    explanation_vi: str = ""
    hint_vi: str = ""
    category: str = ""


class PronunciationHintSchema(BaseModel):
    word: str
    ipa: str
    hint_vi: str


class TutorResponseSchema(BaseModel):
    content: str
    corrections: List[RealtimeCorrectionSchema] = []
    hints: List[PronunciationHintSchema] = []
    language_mix: str = "vi-heavy"  # "vi-heavy" | "balanced" | "en-heavy"
    route_used: str = "local"      # "local" | "cache" | "llm_light" | "llm_full"
    tokens_used: int = 0


class SessionSummarySchema(BaseModel):
    total_turns: int
    total_corrections: int
    local_corrections: int
    llm_corrections: int
    tokens_saved: int
    top_mistakes: List[dict] = []
    summary_vi: str = ""
