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
