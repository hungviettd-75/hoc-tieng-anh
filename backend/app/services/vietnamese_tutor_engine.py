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
        Tạo response thân thiện từ list corrections áp dụng Sandwich Feedback (Động viên -> Sửa lỗi -> Mẫu chuẩn).
        """
        if not corrections:
            import random
            return random.choice(self.PERFECT_RESPONSES)

        # Auto-adjust level dựa trên error rate
        adjusted_level = self._adjust_level(user_level, error_rate)
        config = self.LEVEL_CONFIG.get(adjusted_level, self.LEVEL_CONFIG["A2"])

        parts = []

        # 1. ĐỘNG VIÊN (Encouragement) - Phần đầu của bánh kẹp Sandwich
        import random
        encouragement = random.choice(self.ENCOURAGEMENTS_VI) if config["vi_ratio"] > 0.5 else random.choice(self.ENCOURAGEMENTS_EN)
        parts.append(f"✨ **{encouragement}**")
        parts.append("")

        # 2. SỬA LỖI & MẪU CHUẨN (Corrections & Model Answers) - Phần nhân của bánh kẹp Sandwich
        # Format corrections (max 3 lỗi để tránh bị quá tải nhận thức - cognitive overload)
        for i, c in enumerate(corrections[:3]):
            parts.append(f"### 📍 Điểm cần lưu ý #{i+1}:")
            parts.append(self._format_single_correction(c, config))
            parts.append("")

        # 3. GỢI MỞ & ĐỒNG HÀNH (Closing & Next Step Prompt) - Phần sau của bánh kẹp Sandwich
        if len(corrections) == 1:
            parts.append("💪 *Hãy thử nói lại câu trên để sửa lỗi nhé! Bạn làm được mà!*" if config["vi_ratio"] > 0.5 else "💪 *Let's try saying it again with the fix! You can do it!*")
        else:
            count = len(corrections)
            parts.append(
                f"💪 *Chúng ta có {count} lỗi nhỏ. Đừng lo lắng, hãy thử thực hành lại từng câu một nhé!*"
                if config["vi_ratio"] > 0.5
                else f"💪 *We detected {count} minor errors. No worries, let's practice speaking them again one by one!*"
            )

        return "\n".join(parts)

    def _format_single_correction(self, c: CorrectionItem, config: Dict) -> str:
        """Format 1 correction item thành cấu trúc Thẻ Vàng / Thẻ Xanh Markdown tối ưu."""
        lines = []

        if c.error_type == "pronunciation":
            if config["vi_ratio"] > 0.5:
                lines.append(f"⚠️ **AI Correction [Thẻ Vàng]:**")
                lines.append(f"> ❌ Từ phát âm chưa đúng: *'{c.original}'*")
                lines.append(f"> ✅ Cách phát âm chuẩn: **'{c.correction}'** {c.ipa}")
                if c.hint_vi and config["detail"] != "low":
                    lines.append(f"> 💡 *Mẹo nhỏ [quick tip]:* {c.hint_vi}")
            else:
                lines.append(f"⚠️ **AI Correction [Yellow Card]:**")
                lines.append(f"> ❌ Mispronounced: *'{c.original}'*")
                lines.append(f"> ✅ Correct pronunciation: **'{c.correction}'** {c.ipa}")
                if c.hint_vi and config["detail"] == "high":
                    lines.append(f"> 💡 *Quick tip:* {c.hint_vi}")

        elif c.error_type == "grammar":
            if config["vi_ratio"] > 0.5:
                lines.append(f"⚠️ **AI Correction [Thẻ Vàng]:**")
                lines.append(f"> ❌ Lỗi ngữ pháp: *'{c.original}'*")
                lines.append(f"> 📝 Chi tiết lỗi: {c.explanation_vi}")
                if c.correction:
                    lines.append(f"✅ **Perfect Way [Thẻ Xanh]:**")
                    lines.append(f"> Nên nói là [better say]: **'{c.correction}'**")
            else:
                lines.append(f"⚠️ **AI Correction [Yellow Card]:**")
                lines.append(f"> ❌ Grammatical error: *'{c.original}'*")
                lines.append(f"> 📝 Explanation: {c.explanation_en or c.explanation_vi}")
                if c.correction:
                    lines.append(f"✅ **Perfect Way [Green Card]:**")
                    lines.append(f"> You should say: **'{c.correction}'**")

        elif c.error_type == "natural_speaking":
            if config["vi_ratio"] > 0.5:
                lines.append(f"🗣️ **Natural Speaking [Diễn đạt tự nhiên]:**")
                lines.append(f"> ❌ Cách bạn nói: *'{c.original}'* (hơi gượng hoặc giống dịch từng từ [word-by-word translation])")
                lines.append(f"> ✅ Người bản xứ thường nói: **'{c.correction}'**")
                if getattr(c, 'explanation_vi', ''):
                    lines.append(f"> 💡 *Giải thích thêm:* {c.explanation_vi}")
            else:
                lines.append(f"🗣️ **Natural Speaking [Native Expression]:**")
                lines.append(f"> ❌ Your way: *'{c.original}'*")
                lines.append(f"> ✅ Native way: **'{c.correction}'**")
                if getattr(c, 'explanation_en', ''):
                    lines.append(f"> 💡 *Note:* {c.explanation_en}")

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
