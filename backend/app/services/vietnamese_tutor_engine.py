"""
Vietnamese Tutor Engine - Tạo phản hồi tiếng Việt thân thiện.
Adaptive language mixing theo level.
"""
from typing import List, Dict
from app.services.lightweight_nlp_engine import CorrectionItem


class VietnameseTutorEngine:
    """
    Engine tạo Vietnamese-guided responses.
    Adaptive: Beginner=90% Vietnamese, Advanced=90% English
    """

    # Level thresholds
    LEVEL_CONFIG = {
        "A1": {"vi_ratio": 0.95, "emoji": True, "detail": "high"},
        "A2": {"vi_ratio": 0.85, "emoji": True, "detail": "high"},
        "B1": {"vi_ratio": 0.60, "emoji": True, "detail": "medium"},
        "B2": {"vi_ratio": 0.30, "emoji": False, "detail": "low"},
        "C1": {"vi_ratio": 0.10, "emoji": False, "detail": "low"},
        "C2": {"vi_ratio": 0.05, "emoji": False, "detail": "low"},
    }

    ENCOURAGEMENTS_VI = [
        "Bạn gần đúng rồi 😊", "Tốt lắm, sửa chút xíu nhé 👍",
        "Cố lên, bạn đang tiến bộ! 🌟", "Không sao, thử lại nhé 💪",
        "Giỏi quá! Chỉ cần chỉnh nhẹ thôi ✨",
    ]

    ENCOURAGEMENTS_EN = [
        "Almost there!", "Good try, small fix needed 👍",
        "Keep going, you're improving! 🌟", "No worries, try again 💪",
    ]

    PERFECT_RESPONSES = [
        "Tuyệt vời! Phát âm chuẩn rồi! 🎉",
        "Xuất sắc! Không có lỗi nào cả! 🌟",
        "Perfect! Bạn nói rất tốt! 👏",
    ]

    def format_correction_response(
        self, corrections: List[CorrectionItem], user_level: str = "A2",
        error_rate: float = 0.5
    ) -> str:
        """
        Tạo response thân thiện từ list corrections.
        """
        if not corrections:
            import random
            return random.choice(self.PERFECT_RESPONSES)

        # Auto-adjust level dựa trên error rate
        adjusted_level = self._adjust_level(user_level, error_rate)
        config = self.LEVEL_CONFIG.get(adjusted_level, self.LEVEL_CONFIG["A2"])

        parts = []

        # Encouragement
        import random
        if config["vi_ratio"] > 0.5:
            parts.append(random.choice(self.ENCOURAGEMENTS_VI))
        else:
            parts.append(random.choice(self.ENCOURAGEMENTS_EN))

        parts.append("")

        # Format corrections (max 3 để không overwhelm)
        for c in corrections[:3]:
            parts.append(self._format_single_correction(c, config))
            parts.append("")

        # Closing
        if len(corrections) == 1:
            parts.append("Hãy thử lại nhé! 😊" if config["vi_ratio"] > 0.5 else "Try again! 😊")
        else:
            count = len(corrections)
            parts.append(
                f"Có {count} chỗ cần sửa. Thử lại từng cái nhé! 💪"
                if config["vi_ratio"] > 0.5
                else f"{count} corrections. Practice each one! 💪"
            )

        return "\n".join(parts)

    def _format_single_correction(self, c: CorrectionItem, config: Dict) -> str:
        """Format 1 correction item."""
        lines = []

        if c.error_type == "pronunciation":
            if config["vi_ratio"] > 0.5:
                lines.append(f"❌ Âm này chưa đúng: '{c.original}'")
                lines.append(f"✅ Phải phát âm là: '{c.correction}' {c.ipa}")
                if c.hint_vi and config["detail"] != "low":
                    lines.append(f"💡 {c.hint_vi}")
            else:
                lines.append(f"❌ You mispronounced '{c.original}'")
                lines.append(f"✅ It should be: '{c.correction}' {c.ipa}")
                if c.hint_vi and config["detail"] == "high":
                    lines.append(f"💡 {c.hint_vi}")

        elif c.error_type == "grammar":
            if config["vi_ratio"] > 0.5:
                lines.append(f"📝 {c.explanation_vi}")
                if c.correction:
                    lines.append(f"✅ Bạn cần nói là: '{c.correction}'")
            else:
                lines.append(f"📝 {c.explanation_en or c.explanation_vi}")
                if c.correction:
                    lines.append(f"✅ Say: '{c.correction}'")

        elif c.error_type == "natural_speaking":
            if config["vi_ratio"] > 0.5:
                lines.append(f"🗣️ Cách diễn đạt tự nhiên hơn:")
                lines.append(f"✅ Người bản xứ thường nói thế này: '{c.correction}'")
                if getattr(c, 'explanation_vi', ''):
                    lines.append(f"💡 {c.explanation_vi}")
            else:
                lines.append(f"🗣️ More natural expression:")
                lines.append(f"✅ Native speakers usually say: '{c.correction}'")
                if getattr(c, 'explanation_en', ''):
                    lines.append(f"💡 {c.explanation_en}")

        return "\n".join(lines)

    def _adjust_level(self, base_level: str, error_rate: float) -> str:
        """Auto-adjust level dựa trên error rate."""
        levels = ["A1", "A2", "B1", "B2", "C1", "C2"]
        idx = levels.index(base_level) if base_level in levels else 1

        if error_rate > 0.6:
            idx = max(0, idx - 1)  # Tăng Vietnamese
        elif error_rate < 0.2:
            idx = min(len(levels) - 1, idx + 1)  # Giảm Vietnamese

        return levels[idx]

    def format_pronunciation_hint(self, word: str, ipa: str, hint_vi: str) -> Dict:
        """Format pronunciation hint cho frontend."""
        return {
            "word": word,
            "ipa": ipa,
            "hint_vi": hint_vi,
            "type": "pronunciation_hint",
        }

    def get_session_summary_vi(self, mistakes: List[Dict], total_turns: int) -> str:
        """Tạo session summary bằng tiếng Việt."""
        if not mistakes:
            return f"🎉 Tuyệt vời! {total_turns} lượt hội thoại không có lỗi nào!"

        categories = {}
        for m in mistakes:
            cat = m.get("category", "other")
            categories[cat] = categories.get(cat, 0) + 1

        lines = [f"📊 Tổng kết phiên luyện tập ({total_turns} lượt):", ""]
        for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
            label = self._category_label(cat)
            lines.append(f"• {label}: {count} lần")

        lines.append("")
        most_common = max(categories, key=categories.get)
        lines.append(f"💡 Nên tập trung luyện: {self._category_label(most_common)}")
        return "\n".join(lines)

    def _category_label(self, category: str) -> str:
        labels = {
            "th_sound": "Âm TH (θ/ð)",
            "ending_sound": "Âm cuối (d, p, t, s)",
            "sh_sound": "Âm SH (ʃ)",
            "rl_confusion": "Nhầm R/L",
            "wv_confusion": "Nhầm W/V",
            "vowel_length": "Độ dài nguyên âm",
            "subject_verb": "Hòa hợp chủ-vị",
            "article": "Mạo từ (a/an/the)",
            "vi_transfer": "Chuyển ngữ từ tiếng Việt",
            "modal_verb": "Động từ khuyết thiếu",
            "preposition": "Giới từ",
            "tense": "Thì (tense)",
            "missing_word": "Bỏ sót từ",
            "minimal_pair": "Cặp tối thiểu",
            "general": "Phát âm chung",
        }
        return labels.get(category, category)


# Singleton
vietnamese_tutor = VietnameseTutorEngine()
