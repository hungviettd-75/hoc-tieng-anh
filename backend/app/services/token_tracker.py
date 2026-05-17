"""
Token Tracker - Monitor usage and optimize cost.
"""
from typing import Dict
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class SessionStats:
    total_tokens: int = 0
    llm_calls: int = 0
    local_handled: int = 0
    duration_seconds: int = 0

    @property
    def cost_estimate_usd(self) -> float:
        # Gemini 1.5 Flash cost: ~$0.075 / 1M tokens
        return (self.total_tokens / 1_000_000) * 0.075

    @property
    def tokens_saved_estimate(self) -> int:
        # Estimate: each local handled request saves ~300 tokens
        return self.local_handled * 300


class TokenTracker:
    def __init__(self):
        self._sessions: Dict[int, SessionStats] = defaultdict(SessionStats)
        self._global_tokens = 0

    def add_usage(self, user_id: int, tokens: int, route: str):
        session = self._sessions[user_id]
        session.total_tokens += tokens
        self._global_tokens += tokens

        if route in ("llm_full", "llm_light"):
            session.llm_calls += 1
        elif route in ("local", "cache"):
            session.local_handled += 1

    def get_stats(self, user_id: int) -> Dict:
        session = self._sessions[user_id]
        return {
            "tokens_used": session.total_tokens,
            "cost_usd": round(session.cost_estimate_usd, 5),
            "tokens_saved": session.tokens_saved_estimate,
            "optimization_ratio": round(
                session.local_handled / max(1, session.llm_calls + session.local_handled) * 100, 1
            ),
        }

    def reset_session(self, user_id: int):
        if user_id in self._sessions:
            del self._sessions[user_id]


# Singleton
token_tracker = TokenTracker()
