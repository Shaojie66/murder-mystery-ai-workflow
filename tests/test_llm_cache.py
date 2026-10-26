"""Tests for llm/cache.py"""
import tempfile
import shutil
from pathlib import Path
import pytest
from murder_wizard.llm.cache import LLMCache
from murder_wizard.llm.client import LLMResponse


class TestLLMCache:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cache = LLMCache(Path(self.temp_dir))

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cache_miss_returns_none(self):
        result = self.cache.get("op", "prompt", "system", "gpt-4o")
        assert result is None

    def test_cache_set_and_get(self):
        response = LLMResponse(content="test", tokens_used=100, cost=0.01, model="gpt-4o")
        self.cache.set("op", "prompt", "system", "gpt-4o", response)

        cached = self.cache.get("op", "prompt", "system", "gpt-4o")
        assert cached is not None
        assert cached.content == "test"
        assert cached.cost == 0.01

    def test_different_operation_not_cached(self):
        response = LLMResponse(content="test", tokens_used=100, cost=0.01, model="gpt-4o")
        self.cache.set("op1", "prompt", "system", "gpt-4o", response)

        cached = self.cache.get("op2", "prompt", "system", "gpt-4o")
        assert cached is None

    def test_different_prompt_not_cached(self):
        response = LLMResponse(content="test", tokens_used=100, cost=0.01, model="gpt-4o")
        self.cache.set("op", "prompt1", "system", "gpt-4o", response)

        cached = self.cache.get("op", "prompt2", "system", "gpt-4o")
        assert cached is None

    def test_different_system_not_cached(self):
        response = LLMResponse(content="test", tokens_used=100, cost=0.01, model="gpt-4o")
        self.cache.set("op", "prompt", "system1", "gpt-4o", response)

        cached = self.cache.get("op", "prompt", "system2", "gpt-4o")
        assert cached is None

    def test_clear(self):
        response = LLMResponse(content="test", tokens_used=100, cost=0.01, model="gpt-4o")
        self.cache.set("op", "prompt", "system", "gpt-4o", response)
        assert self.cache.stats()["entries"] == 1

        self.cache.clear()
        assert self.cache.stats()["entries"] == 0

    def test_stats(self):
        assert self.cache.stats()["entries"] == 0
        assert self.cache.stats()["size_bytes"] == 0

        response = LLMResponse(content="test", tokens_used=100, cost=0.01, model="gpt-4o")
        self.cache.set("op", "prompt", "system", "gpt-4o", response)
        assert self.cache.stats()["entries"] == 1
        assert self.cache.stats()["size_bytes"] > 0

    def test_persistence_across_instances(self):
        response = LLMResponse(content="test", tokens_used=100, cost=0.01, model="gpt-4o")
        self.cache.set("op", "prompt", "system", "gpt-4o", response)

        # 重新创建 cache 实例，应能读取
        cache2 = LLMCache(Path(self.temp_dir))
        cached = cache2.get("op", "prompt", "system", "gpt-4o")
        assert cached is not None
        assert cached.content == "test"

    # ─── invalidate：校验后被拒绝的响应必须能被逐出缓存 ───────────────────────

    def test_invalidate_removes_the_entry_and_reports_it(self):
        response = LLMResponse(content="bad", tokens_used=100, cost=0.01, model="gpt-4o")
        self.cache.set("op", "prompt", "system", "gpt-4o", response)

        assert self.cache.invalidate("op", "prompt", "system", "gpt-4o") is True

        assert self.cache.get("op", "prompt", "system", "gpt-4o") is None
        assert self.cache.stats()["entries"] == 0

    def test_invalidate_missing_entry_returns_false(self):
        assert self.cache.invalidate("op", "prompt", "system", "gpt-4o") is False
        assert self.cache.stats()["entries"] == 0

    def test_invalidate_only_removes_the_exact_call(self):
        response = LLMResponse(content="keep", tokens_used=1, cost=0.0, model="gpt-4o")
        target = ("op", "prompt", "system", "gpt-4o")
        others = [
            ("op2", "prompt", "system", "gpt-4o"),   # 不同 operation
            ("op", "prompt2", "system", "gpt-4o"),   # 不同 prompt
            ("op", "prompt", "system2", "gpt-4o"),   # 不同 system
            ("op", "prompt", "system", "claude"),    # 不同 model
        ]
        self.cache.set(*target, response)
        for other in others:
            self.cache.set(*other, response)

        assert self.cache.invalidate(*target) is True

        assert self.cache.get(*target) is None
        for other in others:
            assert self.cache.get(*other) is not None, f"误删了 {other}"

    def test_invalidate_is_persisted_to_disk(self):
        response = LLMResponse(content="bad", tokens_used=100, cost=0.01, model="gpt-4o")
        self.cache.set("op", "prompt", "system", "gpt-4o", response)
        self.cache.set("op", "other", "system", "gpt-4o", response)

        self.cache.invalidate("op", "prompt", "system", "gpt-4o")

        cache2 = LLMCache(Path(self.temp_dir))  # 新实例只读磁盘
        assert cache2.get("op", "prompt", "system", "gpt-4o") is None
        assert cache2.get("op", "other", "system", "gpt-4o") is not None

    def test_invalidate_then_set_stores_a_fresh_response(self):
        bad = LLMResponse(content="bad", tokens_used=1, cost=0.0, model="gpt-4o")
        good = LLMResponse(content="good", tokens_used=1, cost=0.0, model="gpt-4o")
        self.cache.set("op", "prompt", "system", "gpt-4o", bad)
        self.cache.invalidate("op", "prompt", "system", "gpt-4o")
        self.cache.set("op", "prompt", "system", "gpt-4o", good)

        assert self.cache.get("op", "prompt", "system", "gpt-4o").content == "good"

    def test_invalidate_is_thread_safe_with_concurrent_set_and_invalidate(self):
        import threading

        response = LLMResponse(content="x", tokens_used=1, cost=0.0, model="gpt-4o")
        errors: list[BaseException] = []

        def worker(index: int) -> None:
            try:
                self.cache.set("op", f"prompt-{index}", "system", "gpt-4o", response)
                if index % 2 == 0:
                    assert self.cache.invalidate("op", f"prompt-{index}", "system", "gpt-4o") is True
            except BaseException as exc:  # noqa: BLE001 - 收集线程内的任何失败
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(40)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert errors == []
        assert self.cache.stats()["entries"] == 20
        for index in range(40):
            hit = self.cache.get("op", f"prompt-{index}", "system", "gpt-4o")
            assert (hit is None) == (index % 2 == 0)
        # 磁盘上的内容与内存一致（没有被并发写坏）
        assert LLMCache(Path(self.temp_dir)).stats()["entries"] == 20

    # ─── set：写盘失败不能把没存成功的回复留在内存里 ──────────────────────────────

    def test_set_that_cannot_be_saved_leaves_no_entry_behind_and_the_cache_keeps_working(self):
        """回复里有真正的孤立代理项（\\ud800）时写盘抛 UnicodeEncodeError：条目不能留在内存里被后续 get() 重放。"""
        bad = LLMResponse(content="回复\ud800尾巴", tokens_used=1, cost=0.0, model="gpt-4o")
        good = LLMResponse(content="正常回复", tokens_used=1, cost=0.0, model="gpt-4o")

        with pytest.raises(UnicodeEncodeError):
            self.cache.set("op", "prompt", "system", "gpt-4o", bad)

        assert self.cache.get("op", "prompt", "system", "gpt-4o") is None, "写盘失败的回复被缓存重放了"
        assert self.cache.stats()["entries"] == 0
        assert not list(Path(self.temp_dir).glob("*.tmp")), "失败后留下了临时文件"
        # 之后的正常写入不受影响（旧代码里坏条目留在内存，后面每次 set 都会写盘失败）
        self.cache.set("op", "other", "system", "gpt-4o", good)
        assert self.cache.get("op", "other", "system", "gpt-4o").content == "正常回复"
        assert LLMCache(Path(self.temp_dir)).get("op", "other", "system", "gpt-4o").content == "正常回复"

    def test_failed_set_puts_back_the_previous_entry_for_the_same_call(self):
        old = LLMResponse(content="旧回复", tokens_used=1, cost=0.0, model="gpt-4o")
        bad = LLMResponse(content="新回复\ud800", tokens_used=1, cost=0.0, model="gpt-4o")
        self.cache.set("op", "prompt", "system", "gpt-4o", old)
        before = self.cache.cache_file.read_bytes()

        with pytest.raises(UnicodeEncodeError):
            self.cache.set("op", "prompt", "system", "gpt-4o", bad)

        assert self.cache.get("op", "prompt", "system", "gpt-4o").content == "旧回复"
        assert self.cache.cache_file.read_bytes() == before, "写盘失败不应改动磁盘上的缓存"
        assert not list(Path(self.temp_dir).glob("*.tmp"))

    def test_set_restores_memory_when_the_disk_write_fails_for_any_reason(self):
        from unittest.mock import patch

        response = LLMResponse(content="x", tokens_used=1, cost=0.0, model="gpt-4o")
        self.cache.set("op", "kept", "system", "gpt-4o", response)

        with patch.object(Path, "replace", side_effect=OSError(28, "No space left on device")):
            with pytest.raises(OSError):
                self.cache.set("op", "lost", "system", "gpt-4o", response)

        assert self.cache.get("op", "lost", "system", "gpt-4o") is None
        assert self.cache.get("op", "kept", "system", "gpt-4o") is not None
        assert not list(Path(self.temp_dir).glob("*.tmp")), "替换失败后留下了临时文件"
        assert LLMCache(Path(self.temp_dir)).stats()["entries"] == 1
