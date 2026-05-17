"""
Lightweight NLP Engine - Xử lý lỗi phổ biến KHÔNG cần LLM.
"""
import re
import difflib
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class CorrectionItem:
    error_type: str       # "pronunciation" | "grammar"
    severity: str         # "low" | "medium" | "high"
    original: str
    correction: str
    ipa: str = ""
    explanation_vi: str = ""
    explanation_en: str = ""
    hint_vi: str = ""
    category: str = ""


class LightweightNLPEngine:
    def __init__(self):
        self._init_pronunciation_map()
        self._init_grammar_rules()

    def _init_pronunciation_map(self):
        # (correct_word, ipa, explanation_vi, hint_vi, severity, category)
        self.pronunciation_map: Dict[str, Tuple] = {
            # TH Sound
            "sink": ("think", "/θɪŋk/", "Không phải 'sink' mà là 'think'", "Âm TH: đặt lưỡi nhẹ giữa hai răng rồi thổi hơi", "high", "th_sound"),
            "sank": ("thank", "/θæŋk/", "Không phải 'sank' mà là 'thank'", "Âm TH: đặt lưỡi nhẹ giữa hai răng", "high", "th_sound"),
            "sing": ("thing", "/θɪŋ/", "Không phải 'sing' mà là 'thing'", "Âm TH: lưỡi đặt nhẹ giữa hai răng", "high", "th_sound"),
            "sree": ("three", "/θriː/", "Không phải 'sree' mà là 'three'", "Âm TH: lưỡi giữa hai răng + R", "high", "th_sound"),
            "de": ("the", "/ðə/", "Không phải 'de' mà là 'the'", "Âm TH hữu thanh: lưỡi giữa răng + rung", "medium", "th_sound"),
            "dat": ("that", "/ðæt/", "Không phải 'dat' mà là 'that'", "Âm TH hữu thanh: lưỡi giữa răng", "medium", "th_sound"),
            "dis": ("this", "/ðɪs/", "Không phải 'dis' mà là 'this'", "Âm TH hữu thanh: lưỡi giữa răng", "medium", "th_sound"),
            "den": ("then", "/ðɛn/", "Không phải 'den' mà là 'then'", "Âm TH hữu thanh", "medium", "th_sound"),
            "dey": ("they", "/ðeɪ/", "Không phải 'dey' mà là 'they'", "Âm TH hữu thanh", "medium", "th_sound"),
            "tink": ("think", "/θɪŋk/", "Không phải 'tink' mà là 'think'", "Âm TH khác T: lưỡi giữa răng", "high", "th_sound"),
            # Ending Sounds
            "wor": ("word", "/wɜːrd/", "'word' cần có âm D ở cuối", "Đừng nuốt âm cuối D", "medium", "ending_sound"),
            "goo": ("good", "/ɡʊd/", "'good' cần có âm D ở cuối", "Phát âm rõ D cuối", "medium", "ending_sound"),
            "nee": ("need", "/niːd/", "'need' cần có âm D ở cuối", "Giữ âm D cuối rõ ràng", "medium", "ending_sound"),
            "hel": ("help", "/hɛlp/", "'help' cần có âm P ở cuối", "Mím môi để tạo âm P cuối", "medium", "ending_sound"),
            # SH Sound
            "sip": ("ship", "/ʃɪp/", "Không phải 'sip' mà là 'ship'", "Âm SH: tròn môi + thổi hơi", "medium", "sh_sound"),
            "sow": ("show", "/ʃoʊ/", "Không phải 'sow' mà là 'show'", "Âm SH: tròn môi", "medium", "sh_sound"),
            # R/L Confusion
            "light": ("right", "/raɪt/", "'right' bắt đầu bằng R không phải L", "Âm R: cuộn lưỡi lên", "medium", "rl_confusion"),
            "lice": ("rice", "/raɪs/", "'rice' bắt đầu bằng R", "Cuộn lưỡi cho âm R", "medium", "rl_confusion"),
            # W/V Confusion
            "vine": ("wine", "/waɪn/", "'wine' bắt đầu bằng W không phải V", "Âm W: tròn môi như huýt sáo", "medium", "wv_confusion"),
            "vet": ("wet", "/wɛt/", "'wet' bắt đầu bằng W", "Âm W: tròn môi, không dùng răng", "medium", "wv_confusion"),
            # Vowel Length
            "ship": ("sheep", "/ʃiːp/", "'sheep' có nguyên âm dài /iː/", "Kéo dài âm 'ee'", "medium", "vowel_length"),
            "bit": ("beat", "/biːt/", "'beat' có nguyên âm dài /iː/", "Kéo dài âm 'ea'", "medium", "vowel_length"),
        }
        self.minimal_pairs = {
            ("think", "sink"), ("think", "tink"), ("thank", "sank"),
            ("three", "tree"), ("three", "sree"), ("the", "de"),
            ("that", "dat"), ("this", "dis"), ("they", "dey"),
            ("she", "see"), ("ship", "sip"), ("show", "sow"),
            ("sheep", "ship"), ("beat", "bit"), ("right", "light"),
            ("rice", "lice"), ("wine", "vine"), ("wet", "vet"),
        }

    def _init_grammar_rules(self):
        self.grammar_rules: List[Dict] = [
            {
                "pattern": r'\b(want|need|hope|decide|try|learn)\s+([a-z]+)\b',
                "correction": r"\1 to \2",
                "explanation_vi": r"Sau '\1' cần có 'to' trước động từ tiếp theo",
                "explanation_en": r"Use 'to' after '\1'",
                "severity": "medium", "category": "grammar",
            },
            {
                "pattern": r'\bwhy\s+you\s+(don\'t|not|not|doesn\'t)\b',
                "correction": r"why \1 you",
                "explanation_vi": "Trong câu hỏi, trợ động từ phải đứng trước chủ ngữ",
                "explanation_en": "In questions, the auxiliary verb comes before the subject",
                "severity": "high", "category": "grammar",
            },
            {
                "pattern": r'\bi\s+from\b',
                "correction": "I am from",
                "explanation_vi": "Thiếu động từ 'am' trong câu 'I am from...'",
                "explanation_en": "Don't forget the verb 'am'",
                "severity": "medium", "category": "grammar",
            },
            {
                "pattern": r'\bi\s+agree\b',
                "correction": "I agree",
                "explanation_vi": "Dùng 'I agree', không dùng 'I am agree'",
                "explanation_en": "Use 'I agree'",
                "severity": "low", "category": "vi_transfer",
            },
            {
                "pattern": r'\bshe\s+say\b',
                "correction": "she says",
                "explanation_vi": "Với He/She/It động từ 'say' phải thêm 's'",
                "explanation_en": "Use 'says' with he/she/it",
                "severity": "medium", "category": "subject_verb",
            },
            {
                "pattern": r'\b(he|she|it)\s+(don\'t)\b',
                "correction": "doesn't",
                "explanation_vi": "Với He/She/It phải dùng 'doesn't'",
                "explanation_en": "Use 'doesn't' with he/she/it",
                "severity": "high", "category": "subject_verb",
            },
            {
                "pattern": r'\b(i|you|we|they)\s+(has)\b',
                "correction": "have",
                "explanation_vi": "Với I/You/We/They phải dùng 'have'",
                "explanation_en": "Use 'have' with I/you/we/they",
                "severity": "high", "category": "subject_verb",
            },
            {
                "pattern": r'\b(i)\s+is\b',
                "correction": "I am",
                "explanation_vi": "Với 'I' phải dùng 'am'",
                "explanation_en": "Use 'am' with 'I'",
                "severity": "high", "category": "subject_verb",
            },
            {
                "pattern": r'\b(you|we|they)\s+is\b',
                "correction": "are",
                "explanation_vi": "Với You/We/They phải dùng 'are'",
                "explanation_en": "Use 'are' with you/we/they",
                "severity": "high", "category": "subject_verb",
            },
            {
                "pattern": r'\ba\s+([aeiou]\w+)\b',
                "correction": "an",
                "explanation_vi": "Trước nguyên âm dùng 'an' thay vì 'a'",
                "explanation_en": "Use 'an' before vowel sounds",
                "severity": "medium", "category": "article",
            },
            {
                "pattern": r'\bi\s+very\s+like\b',
                "correction": "I really like",
                "explanation_vi": "Dùng 'really like', không đặt 'very' trước 'like'",
                "explanation_en": "Use 'really like' or 'like very much'",
                "severity": "medium", "category": "vi_transfer",
            },
            {
                "pattern": r'\bcan\s+to\s+(\w+)\b',
                "correction": "can + verb",
                "explanation_vi": "Sau 'can' không cần 'to'",
                "explanation_en": "'Can' is followed directly by base verb",
                "severity": "medium", "category": "modal_verb",
            },
            {
                "pattern": r'\b(listen)\s+(?!to\b)(\w+)\b',
                "correction": "listen to",
                "explanation_vi": "'Listen' luôn đi với 'to'",
                "explanation_en": "'Listen' always needs 'to'",
                "severity": "medium", "category": "preposition",
            },
            # --- PAST TENSE RULES ---
            {
                "pattern": r'\byesterday\s+(i|we|they|he|she)\s+(go)\b',
                "correction": "went",
                "explanation_vi": "Bạn cần nói ở thì quá khứ vì có từ 'yesterday' (hôm qua)",
                "explanation_en": "Use past tense 'went' with 'yesterday'",
                "severity": "high", "category": "grammar",
            },
            {
                "pattern": r'\blast\s+(night|week|month|year)\s+(i|we|they|he|she)\s+(am|is|are)\b',
                "correction": "was/were",
                "explanation_vi": "Bạn cần nói ở thì quá khứ vì có từ 'last' (trước/qua)",
                "explanation_en": "Use past tense with 'last'",
                "severity": "high", "category": "grammar",
            },
            # --- NATURAL SPEAKING RULES ---
            {
                "pattern": r'\bi\s+think\s+yes\b',
                "correction": "I think so",
                "explanation_vi": "Đây là cách diễn đạt tự nhiên thay cho 'I think yes'.",
                "explanation_en": "More natural than 'I think yes'.",
                "severity": "low", "category": "natural_speaking", "error_type": "natural_speaking",
            },
            {
                "pattern": r'\bhow\s+to\s+say\b',
                "correction": "How do you say",
                "explanation_vi": "Cách hỏi tự nhiên là 'How do you say...' chứ không phải 'How to say...'",
                "explanation_en": "Use 'How do you say...'",
                "severity": "low", "category": "natural_speaking", "error_type": "natural_speaking",
            },
            {
                "pattern": r'\bi\s+am\s+fine\s+thank\s+you\s+and\s+you\b',
                "correction": "I'm doing well, thanks. How about you?",
                "explanation_vi": "Câu 'I am fine thank you and you' nghe khá cứng nhắc như sách giáo khoa.",
                "explanation_en": "A bit robotic. Try something more conversational.",
                "severity": "low", "category": "natural_speaking", "error_type": "natural_speaking",
            }
        ]

    def detect_pronunciation_errors(self, target_text: str, transcribed_text: str) -> List[CorrectionItem]:
        corrections = []
        target_words = self._normalize(target_text).split() if target_text else []
        transcribed_words = self._normalize(transcribed_text).split()
        
        # Nếu đang ở chế độ Free-Talk (không có target_text)
        if not target_text or target_text == transcribed_text:
            for s_word in transcribed_words:
                if s_word in self.pronunciation_map:
                    correct, ipa, expl_vi, hint_vi, sev, cat = self.pronunciation_map[s_word]
                    corrections.append(CorrectionItem(
                        error_type="pronunciation", severity=sev,
                        original=s_word, correction=correct, ipa=ipa,
                        explanation_vi=expl_vi, hint_vi=hint_vi, category=cat,
                    ))
            return corrections

        # Nếu có target_text (Practice mode)
        matcher = difflib.SequenceMatcher(None, target_words, transcribed_words)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'replace':
                for idx in range(i1, i2):
                    t_word = target_words[idx]
                    s_idx = j1 + (idx - i1)
                    s_word = transcribed_words[s_idx] if s_idx < j2 else ""
                    if s_word and s_word != t_word:
                        c = self._check_pronunciation(t_word, s_word)
                        if c:
                            corrections.append(c)
            elif tag == 'delete':
                for idx in range(i1, i2):
                    corrections.append(CorrectionItem(
                        error_type="pronunciation", severity="medium",
                        original="(missing)", correction=target_words[idx],
                        explanation_vi=f"Bạn bỏ sót từ '{target_words[idx]}'",
                        category="missing_word",
                    ))
        return corrections

    def detect_grammar_errors(self, text: str) -> List[CorrectionItem]:
        corrections = []
        text_lower = text.lower().strip()
        for rule in self.grammar_rules:
            match = re.search(rule["pattern"], text_lower, re.IGNORECASE)
            if match:
                corrections.append(CorrectionItem(
                    error_type=rule.get("error_type", "grammar"), severity=rule["severity"],
                    original=match.group(0), correction=rule["correction"],
                    explanation_vi=rule["explanation_vi"],
                    explanation_en=rule.get("explanation_en", ""),
                    category=rule["category"],
                ))
        return corrections

    def detect_all_errors(self, target_text: str, transcribed_text: str) -> List[CorrectionItem]:
        errors = []
        errors.extend(self.detect_pronunciation_errors(target_text, transcribed_text))
        errors.extend(self.detect_grammar_errors(transcribed_text))
        return errors

    def _check_pronunciation(self, target: str, spoken: str) -> Optional[CorrectionItem]:
        if spoken in self.pronunciation_map:
            correct, ipa, expl_vi, hint_vi, sev, cat = self.pronunciation_map[spoken]
            if correct == target:
                return CorrectionItem(
                    error_type="pronunciation", severity=sev,
                    original=spoken, correction=target, ipa=ipa,
                    explanation_vi=expl_vi, hint_vi=hint_vi, category=cat,
                )
        pair = (target, spoken)
        rev = (spoken, target)
        if pair in self.minimal_pairs or rev in self.minimal_pairs:
            return CorrectionItem(
                error_type="pronunciation", severity="medium",
                original=spoken, correction=target,
                explanation_vi=f"Bạn nói '{spoken}' thay vì '{target}'",
                category="minimal_pair",
            )
        sim = difflib.SequenceMatcher(None, target, spoken).ratio()
        if 0.4 < sim < 0.9:
            return CorrectionItem(
                error_type="pronunciation", severity="low",
                original=spoken, correction=target,
                explanation_vi=f"Gần đúng: '{spoken}' → '{target}'",
                category="general",
            )
        return None

    def _normalize(self, text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text

    def get_error_stats(self, corrections: List[CorrectionItem]) -> Dict:
        stats = {"total": len(corrections), "pronunciation": 0, "grammar": 0, "high": 0, "categories": {}}
        for c in corrections:
            stats[c.error_type] = stats.get(c.error_type, 0) + 1
            if c.severity == "high":
                stats["high"] += 1
            stats["categories"][c.category] = stats["categories"].get(c.category, 0) + 1
        return stats


# Singleton
lightweight_nlp = LightweightNLPEngine()
