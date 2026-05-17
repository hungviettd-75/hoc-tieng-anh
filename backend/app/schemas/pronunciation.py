from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class WordScoreSchema(BaseModel):
    word: str
    is_correct: bool
    confidence: float


class PronunciationMetricSchema(BaseModel):
    metric: str  # fluency, pronunciation, confidence, intonation
    score: float
    feedback: str


class PronunciationAnalysisResponse(BaseModel):
    session_id: int
    overall_score: float
    target_text: str
    transcribed_text: str
    metrics: List[PronunciationMetricSchema]
    word_scores: List[WordScoreSchema]
    feedback: str


class PronunciationSessionSchema(BaseModel):
    id: int
    target_text: str
    transcribed_text: Optional[str] = None
    overall_score: float
    created_at: Optional[datetime] = None
    metrics: List[PronunciationMetricSchema] = []

    class Config:
        from_attributes = True


class PronunciationHistoryResponse(BaseModel):
    sessions: List[PronunciationSessionSchema]
    total_sessions: int
    average_score: float


class PronunciationAnalyticsResponse(BaseModel):
    total_sessions: int
    average_overall: float
    average_fluency: float
    average_pronunciation: float
    average_confidence: float
    average_intonation: float
    recent_trend: str  # improving, declining, stable
    best_score: float
    practice_streak: int


class PracticeSentenceSchema(BaseModel):
    id: int
    text: str
    level: str
    category: str
