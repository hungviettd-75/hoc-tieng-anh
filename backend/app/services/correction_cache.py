"""
Correction Cache - In-memory LRU cache, Redis-ready interface.
Tránh gọi LLM lại cho cùng lỗi.
"""
import hashlib
import time
from typing import Optional, Dict, Any
from collections import OrderedDict
from threading import Lock


class LRUCache:
    """Thread-safe LRU Cache with TTL."""

    def __init__(self, max_size: int = 500, ttl_seconds: int = 3600):
        self._cache: OrderedDict = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._lock = Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if time.time() - timestamp < self._ttl:
                    self._cache.move_to_end(key)
                    self._hits += 1
                    return value
                else:
                    del self._cache[key]
            self._misses += 1
            return None

    def set(self, key: str, value: Any):
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (value, time.time())
            if len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    def stats(self) -> Dict:
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total * 100, 1) if total > 0 else 0,
            "size": len(self._cache),
            "max_size": self._max_size,
        }


class CorrectionCache:
    """
    Cache layer cho AI corrections.
    Dùng in-memory LRU mặc định. Có thể swap sang Redis.
    """

    def __init__(self):
        self._correction_cache = LRUCache(max_size=1000, ttl_seconds=7200)
        self._response_cache = LRUCache(max_size=200, ttl_seconds=3600)

    def _make_key(self, error_type: str, original: str, correction: str) -> str:
        raw = f"{error_type}:{original.lower()}:{correction.lower()}"
        return hashlib.md5(raw.encode()).hexdigest()

    def get_correction(self, error_type: str, original: str, correction: str) -> Optional[Dict]:
        key = self._make_key(error_type, original, correction)
        return self._correction_cache.get(key)

    def set_correction(self, error_type: str, original: str, correction: str, response: Dict):
        key = self._make_key(error_type, original, correction)
        self._correction_cache.set(key, response)

    def get_ai_response(self, prompt_hash: str) -> Optional[str]:
        return self._response_cache.get(prompt_hash)

    def set_ai_response(self, prompt_hash: str, response: str):
        self._response_cache.set(prompt_hash, response)

    def hash_prompt(self, prompt: str) -> str:
        return hashlib.md5(prompt.encode()).hexdigest()

    def stats(self) -> Dict:
        return {
            "corrections": self._correction_cache.stats(),
            "responses": self._response_cache.stats(),
        }


# Singleton
correction_cache = CorrectionCache()
