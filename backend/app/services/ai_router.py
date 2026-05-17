"""
Smart AI Router - Quyết định khi nào dùng local vs LLM.
"""
from typing import List, Dict, Optional
from dataclasses import dataclass
from app.services.lightweight_nlp_engine import lightweight_nlp, CorrectionItem


@dataclass
class RoutingDecision:
    route: str              # "local" | "cache" | "llm_light" | "llm_full"
    corrections: List[CorrectionItem]
    needs_llm: bool
    reason: str
    estimated_tokens: int = 0


class AIRouter:
    """
    Quyết định routing cho mỗi speaking request.
    Ưu tiên: local > cache > llm_light > llm_full
    """

    def __init__(self):
        self._error_history: Dict[int, List[str]] = {}  # user_id -> recent error categories
        self._correction_count: Dict[int, int] = {}      # user_id -> corrections sent count
        self._last_correction_time: Dict[int, float] = {}

    def route(
        self,
        user_id: int,
        target_text: str,
        transcribed_text: str,
        conversation_context: str = "",
    ) -> RoutingDecision:
        """
        Phân tích input và quyết định routing.
        """
        # Step 1: Local detection
        corrections = lightweight_nlp.detect_all_errors(target_text, transcribed_text)

        if not corrections:
            # Không có lỗi → không cần correction
            return RoutingDecision(
                route="local", corrections=[], needs_llm=False,
                reason="no_errors_detected", estimated_tokens=0,
            )

        # Step 2: Check nếu tất cả lỗi đều có Vietnamese explanation sẵn
        all_have_explanation = all(c.explanation_vi for c in corrections)

        if all_have_explanation and not conversation_context:
            # Tất cả lỗi đã có explanation local → không cần LLM
            return RoutingDecision(
                route="local", corrections=corrections, needs_llm=False,
                reason="all_errors_handled_locally", estimated_tokens=0,
            )

        # Step 3: Check severity - chỉ lỗi nghiêm trọng mới cần LLM enhance
        high_severity = [c for c in corrections if c.severity == "high"]
        has_complex = any(c.category in ("general", "missing_word") for c in corrections)

        if not high_severity and not has_complex:
            return RoutingDecision(
                route="local", corrections=corrections, needs_llm=False,
                reason="only_simple_errors", estimated_tokens=0,
            )

        # Step 4: Cần LLM cho lỗi phức tạp
        if conversation_context:
            return RoutingDecision(
                route="llm_full", corrections=corrections, needs_llm=True,
                reason="complex_with_context", estimated_tokens=500,
            )

        return RoutingDecision(
            route="llm_light", corrections=corrections, needs_llm=True,
            reason="complex_errors_need_ai", estimated_tokens=200,
        )

    def should_interrupt(
        self, user_id: int, corrections: List[CorrectionItem], current_time: float
    ) -> bool:
        """
        Smart interruption: chỉ ngắt khi lỗi nghiêm trọng hoặc lặp lại.
        """
        if not corrections:
            return False

        # Debounce: tối thiểu 5 giây giữa các corrections
        last_time = self._last_correction_time.get(user_id, 0)
        if current_time - last_time < 5.0:
            return False

        # Chỉ interrupt cho lỗi high severity
        high = [c for c in corrections if c.severity == "high"]
        if high:
            self._last_correction_time[user_id] = current_time
            return True

        # Hoặc lỗi lặp lại >= 2 lần
        history = self._error_history.get(user_id, [])
        for c in corrections:
            if history.count(c.category) >= 1:  # Đã lỗi 1 lần trước đó
                self._last_correction_time[user_id] = current_time
                return True

        # Track errors
        for c in corrections:
            self._error_history.setdefault(user_id, []).append(c.category)
        # Giữ tối đa 20 lỗi gần nhất
        if user_id in self._error_history:
            self._error_history[user_id] = self._error_history[user_id][-20:]

        return False

    def get_user_stats(self, user_id: int) -> Dict:
        """Thống kê routing cho user."""
        return {
            "error_history": self._error_history.get(user_id, []),
            "total_corrections": self._correction_count.get(user_id, 0),
        }


# Singleton
ai_router = AIRouter()
