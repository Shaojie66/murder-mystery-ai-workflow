"""LLM response caching to avoid redundant API calls."""
import hashlib
import json
import threading
from pathlib import Path
from typing import Optional

from murder_wizard.llm.client import LLMResponse


class LLMCache:
    """LLM 调用缓存

    基于 prompt + system + operation 的 hash 缓存响应，
    存储在项目目录的 cache.json 中。线程安全。
    """

    def __init__(self, cache_dir: Path):
        self.cache_file = cache_dir / "cache.json"
        self._cache: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        """从磁盘加载缓存"""
        if self.cache_file.exists():
            try:
                self._cache = json.loads(self.cache_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                self._cache = {}

    def _save(self) -> None:
        """原子写入缓存到磁盘（写 temp 再 rename）

        先在内存里编码一遍：含孤立代理项等无法编码为 UTF-8 的文字在这里就抛出，不会先建出一个空的 .tmp；
        写入或替换中途失败也清掉 .tmp。磁盘上的格式不变。
        """
        text = json.dumps(self._cache, ensure_ascii=False, indent=2)
        text.encode("utf-8")
        tmp = self.cache_file.with_suffix(".json.tmp")
        try:
            tmp.write_text(text, encoding="utf-8")
            tmp.replace(self.cache_file)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise

    def _make_key(self, operation: str, prompt: str, system: str, model: str, max_tokens: Optional[int] = None) -> str:
        """生成缓存键"""
        # 包含 operation 可以区分不同阶段的同名 prompt
        raw = f"{operation}|{model}|{system}|{prompt}"
        if max_tokens is not None:  # 输出上限不同，结果不同；默认上限保持原键不变
            raw += f"|mt={max_tokens}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

    def get(self, operation: str, prompt: str, system: str, model: str, max_tokens: Optional[int] = None) -> Optional[LLMResponse]:
        """命中缓存返回 LLMResponse，未命中返回 None（线程安全）"""
        with self._lock:
            key = self._make_key(operation, prompt, system, model, max_tokens)
            entry = self._cache.get(key)
            if entry is None:
                return None
            return LLMResponse(
                content=entry["content"],
                tokens_used=entry["tokens_used"],
                cost=entry["cost"],
                model=entry["model"],
                stop_reason=entry.get("stop_reason"),
            )

    def set(self, operation: str, prompt: str, system: str, model: str, response: LLMResponse, max_tokens: Optional[int] = None) -> None:
        """写入缓存（线程安全）

        写盘失败（磁盘满、回复里有无法编码的字符……）时恢复调用前的内存状态再抛出：
        否则这条没存成功的回复会留在内存里被后续 get() 重放，之后每一次 set() 也都会因它写盘失败。
        """
        with self._lock:
            key = self._make_key(operation, prompt, system, model, max_tokens)
            previous = self._cache.get(key)
            self._cache[key] = {
                "content": response.content,
                "tokens_used": response.tokens_used,
                "cost": response.cost,
                "model": response.model,
                "stop_reason": response.stop_reason,
                "operation": operation,
            }
            try:
                self._save()
            except BaseException:
                if previous is None:
                    del self._cache[key]
                else:
                    self._cache[key] = previous
                raise

    def invalidate(self, operation: str, prompt: str, system: str, model: str, max_tokens: Optional[int] = None) -> bool:
        """删除这一次调用对应的缓存条目（线程安全）。

        用于调用方校验后拒绝了响应的场景：不删的话，重试会永远命中同一个被拒绝的响应。
        只删与 (operation, prompt, system, model) 完全匹配的条目；返回是否确实删除了条目。
        """
        with self._lock:
            key = self._make_key(operation, prompt, system, model, max_tokens)
            if key not in self._cache:
                return False
            del self._cache[key]
            self._save()
            return True

    def clear(self) -> None:
        """清空缓存（线程安全）"""
        with self._lock:
            self._cache = {}
            if self.cache_file.exists():
                self.cache_file.unlink()

    def stats(self) -> dict:
        """返回缓存统计（线程安全）"""
        with self._lock:
            return {
                "entries": len(self._cache),
                "size_bytes": self.cache_file.stat().st_size if self.cache_file.exists() else 0,
            }
