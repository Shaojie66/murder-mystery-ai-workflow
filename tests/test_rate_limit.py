"""Tests for llm/rate_limit.py."""
import tempfile
import shutil
import time
import threading
import pytest
from murder_wizard.llm.rate_limit import RateLimiter


class TestRateLimiter:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_basic_creation(self):
        limiter = RateLimiter(max_concurrent=2, delay_between_calls=0.1)
        assert limiter._semaphore._value == 2
        assert limiter._delay == 0.1

    def test_max_concurrent_must_be_positive(self):
        with pytest.raises(ValueError):
            RateLimiter(max_concurrent=0)
        with pytest.raises(ValueError):
            RateLimiter(max_concurrent=-1)

    def test_parallel_runs_in_parallel(self):
        """验证任务确实是并行运行的（不是串行）。"""
        limiter = RateLimiter(max_concurrent=3, delay_between_calls=0)
        results = []

        def slow_task(task_id):
            time.sleep(0.1)
            results.append(task_id)
            return task_id

        tasks = [(f"task_{i}", (i,), {}) for i in range(3)]
        start = time.time()
        output = limiter.run_parallel(tasks, lambda *args, **kwargs: slow_task(args[0]))
        elapsed = time.time() - start

        assert len(output) == 3
        # 3 个并发任务各 0.1s，如果是串行至少 0.3s
        # 并行的话应该在 ~0.1s 完成（有 0.05s 误差容限）
        assert elapsed < 0.2, f"Expected parallel <0.2s, got {elapsed:.2f}s"

    def test_semaphore_limits_concurrency(self):
        """验证同时只有 max_concurrent 个任务在运行。"""
        limiter = RateLimiter(max_concurrent=2, delay_between_calls=0)
        max_seen = [0]
        current = [0]
        lock = threading.Lock()

        def counting_task(task_id):
            with lock:
                current[0] += 1
                max_seen[0] = max(max_seen[0], current[0])
            time.sleep(0.05)
            with lock:
                current[0] -= 1
            return task_id

        tasks = [(f"task_{i}", (i,), {}) for i in range(6)]
        limiter.run_parallel(tasks, lambda *args, **kwargs: counting_task(args[0]))

        # 最多只应该同时有 2 个任务运行
        assert max_seen[0] <= 2

    def test_results_ordered(self):
        """验证结果顺序与输入顺序一致。"""
        limiter = RateLimiter(max_concurrent=2, delay_between_calls=0)

        def make_task(x):
            def task():
                time.sleep(0.01)
                return x * 2
            return task

        tasks = [("id0", (0,), {}), ("id1", (1,), {}), ("id2", (2,), {})]
        output = limiter.run_parallel(tasks, lambda *args, **kwargs: make_task(args[0])())

        ids = [item[0] for item in output]
        assert ids == ["id0", "id1", "id2"]

    def test_delay_between_calls(self):
        """验证调用之间有延迟。"""
        limiter = RateLimiter(max_concurrent=1, delay_between_calls=0.2)
        times = []

        def record_time():
            times.append(time.time())
            return 0

        tasks = [("t0", (), {}), ("t1", (), {}), ("t2", (), {})]
        limiter.run_parallel(tasks, lambda *a, **kw: record_time())

        # 检查延迟
        for i in range(1, len(times)):
            gap = times[i] - times[i - 1]
            assert gap >= 0.18, f"Expected >= 0.18s gap, got {gap:.3f}s"

    def test_error_in_task_returns_none(self):
        """验证任务抛出异常时不会导致整个 run_parallel 崩溃。"""
        limiter = RateLimiter(max_concurrent=2, delay_between_calls=0)

        # 使用可访问 task_id 的 wrapper 来路由
        results = {}

        def router(task_key):
            def call():
                if task_key.startswith("fail"):
                    raise RuntimeError("intentional failure")
                return "ok"
            return call

        # 构建 tasks：每个任务携带自己的 task_id（作为 args[0]）
        tasks = [
            ("fail", ("fail",), {}),
            ("ok", ("ok",), {}),
        ]
        output = limiter.run_parallel(
            tasks,
            lambda *args, **kwargs: router(args[0])()
        )

        result_map = dict(output)
        assert result_map["fail"] is None
        assert result_map["ok"] == "ok"
