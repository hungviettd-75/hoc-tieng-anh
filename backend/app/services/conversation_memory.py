"""
Optimized Conversation Memory - Giảm token gửi lên LLM.
Rolling summaries + short context windows.
"""
from typing import List, Dict


class ConversationMemory:
    """
    Quản lý conversation context tối ưu token.
    - Chỉ giữ 4 messages gần nhất (2 user + 2 assistant)
    - Rolling summary mỗi 6 turns
    - Track mistakes trong session
    """

    def __init__(self, max_recent: int = 20, summary_interval: int = 24):
        self._sessions: Dict[int, Dict] = {}
        self._max_recent = max_recent
        self._summary_interval = summary_interval

    def get_or_create(self, user_id: int) -> Dict:
        if user_id not in self._sessions:
            self._sessions[user_id] = {
                "history": [],
                "summary": "",
                "mistakes": [],
                "turn_count": 0,
                "topic": "",
            }
        return self._sessions[user_id]

    def add_turn(self, user_id: int, user_msg: str, ai_msg: str):
        session = self.get_or_create(user_id)
        session["history"].append({"role": "user", "content": user_msg})
        session["history"].append({"role": "assistant", "content": ai_msg})
        session["turn_count"] += 1

        # Rolling: chỉ giữ max_recent messages
        if len(session["history"]) > self._max_recent * 2:
            # Tóm tắt phần cũ vào summary
            old = session["history"][:-self._max_recent * 2]
            old_text = " | ".join([f"{m['role']}: {m['content'][:50]}" for m in old])
            if session["summary"]:
                session["summary"] = f"{session['summary']} | {old_text}"
            else:
                session["summary"] = old_text
            # Giới hạn summary length
            if len(session["summary"]) > 300:
                session["summary"] = session["summary"][-300:]
            session["history"] = session["history"][-self._max_recent * 2:]

    def add_mistake(self, user_id: int, mistake: Dict):
        session = self.get_or_create(user_id)
        session["mistakes"].append(mistake)
        # Giữ tối đa 10 mistakes gần nhất
        if len(session["mistakes"]) > 10:
            session["mistakes"] = session["mistakes"][-10:]

    def get_compact_context(self, user_id: int) -> str:
        """
        Trả về context gọn nhẹ cho LLM prompt.
        Tiết kiệm ~70% tokens so với full history.
        """
        session = self.get_or_create(user_id)
        parts = []

        if session["summary"]:
            parts.append(f"Background info about user: {session['summary']}")

        if session["mistakes"]:
            recent_mistakes = session["mistakes"][-5:]
            mistake_text = ", ".join([
                f"said '{m.get('original', '')}' but correct is '{m.get('correction', '')}'"
                for m in recent_mistakes
            ])
            parts.append(f"Recent student grammar mistakes to note: {mistake_text}")

        for msg in session["history"]:
            role = "Student" if msg["role"] == "user" else "Coach"
            content = msg["content"][:100]  # Truncate long messages
            parts.append(f"{role}: {content}")

        return "\n".join(parts)

    def get_history_for_gemini(self, user_id: int) -> List[Dict]:
        """Trả về history format cho Gemini API."""
        session = self.get_or_create(user_id)
        return list(session["history"])

    def get_recent_mistakes(self, user_id: int) -> List[Dict]:
        session = self.get_or_create(user_id)
        return session.get("mistakes", [])

    def clear(self, user_id: int):
        if user_id in self._sessions:
            del self._sessions[user_id]

    def get_session_stats(self, user_id: int) -> Dict:
        session = self.get_or_create(user_id)
        return {
            "turn_count": session["turn_count"],
            "history_length": len(session["history"]),
            "summary_length": len(session.get("summary", "")),
            "mistake_count": len(session.get("mistakes", [])),
        }


# Singleton
conversation_memory = ConversationMemory()
