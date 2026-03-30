"""LLM response caching to avoid redundant API calls."""
import hashlib
import json
from pathlib import Path
from typing import Optional

from murder_wizard.llm.client import LLMResponse


class LLMCache:
    """LLM 调用缓存

    基于 prompt + system + operation 的 hash 缓存响应，
    存储在项目目录的 cache.json 中。
    """

    def __init__(self, cache_dir: Path):
        self.cache_file = cache_dir / "cache.json"
        self._cache: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        """从磁盘加载缓存"""
        if self.cache_file.exists():
            try:
                self._cache = json.loads(self.cache_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                self._cache = {}

    def _save(self) -> None:
        """持久化缓存到磁盘"""
        self.cache_file.write_text(
            json.dumps(self._cache, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def _make_key(self, operation: str, prompt: str, system: str, model: str) -> str:
        """生成缓存键"""
        # 包含 operation 可以区分不同阶段的同名 prompt
        raw = f"{operation}|{model}|{system}|{prompt}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

    def get(self, operation: str, prompt: str, system: str, model: str) -> Optional[LLMResponse]:
        """命中缓存返回 LLMResponse，未命中返回 None"""
        key = self._make_key(operation, prompt, system, model)
        entry = self._cache.get(key)
        if entry is None:
            return None
        return LLMResponse(
            content=entry["content"],
            tokens_used=entry["tokens_used"],
            cost=entry["cost"],
            model=entry["model"],
        )

    def set(self, operation: str, prompt: str, system: str, model: str, response: LLMResponse) -> None:
        """写入缓存"""
        key = self._make_key(operation, prompt, system, model)
        self._cache[key] = {
            "content": response.content,
            "tokens_used": response.tokens_used,
            "cost": response.cost,
            "model": response.model,
            "operation": operation,
        }
        self._save()

    def clear(self) -> None:
        """清空缓存"""
        self._cache = {}
        if self.cache_file.exists():
            self.cache_file.unlink()

    def stats(self) -> dict:
        """返回缓存统计"""
        return {
            "entries": len(self._cache),
            "size_bytes": self.cache_file.stat().st_size if self.cache_file.exists() else 0,
        }
