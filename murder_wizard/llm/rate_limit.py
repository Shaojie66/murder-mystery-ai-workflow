"""LLM 调用并发控制器 - 限制 API 并行数，避免触发速率限制."""
import threading
import time
from typing import Callable, TypeVar, ParamSpec, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

P = ParamSpec('P')
T = TypeVar('T')


class RateLimiter:
    """信号量控制并发数的 RateLimiter。

    用途：expand 时并行生成多角色剧本，控制同时进行的 API 调用数。
    使用方式：
        limiter = RateLimiter(max_concurrent=2, delay_between_calls=1.0)
        results = limiter.run_parallel(tasks, call_llm_fn)
    """

    def __init__(self, max_concurrent: int = 2, delay_between_calls: float = 1.0):
        """初始化限流器。

        Args:
            max_concurrent: 最大并发数，默认 2（Claude API 限制约 5 CPM）
            delay_between_calls: 每次 API 调用之间的基础延迟（秒），默认 1.0
        """
        if max_concurrent < 1:
            raise ValueError("max_concurrent must be >= 1")
        self._semaphore = threading.Semaphore(max_concurrent)
        self._delay = delay_between_calls
        self._lock = threading.Lock()
        self._last_call_time = 0.0

    def run_parallel(
        self,
        tasks: list[tuple[str, tuple, dict]],
        call_fn: Callable[..., T],
        max_workers: int = None,
    ) -> list[tuple[str, T | None]]:
        """并行执行多个任务（带并发控制）。

        Args:
            tasks: List of (task_id, args, kwargs) tuples.
                   task_id 用于标识任务结果。
            call_fn: 被调用的函数，签名为 call_fn(*args, **kwargs) -> T
            max_workers: ThreadPoolExecutor 最大工作线程数，默认等于 max_concurrent

        Returns:
            List of (task_id, result) tuples，保持 tasks 原始顺序。
            如果某个任务失败，该任务的结果为 None。
        """
        if max_workers is None:
            max_workers = self._semaphore._value

        results: dict[str, T | None] = {}

        def _throttled_call(task_id: str, args: tuple, kwargs: dict):
            acquired = False
            try:
                acquired = self._semaphore.acquire(timeout=60)
                if not acquired:
                    raise RuntimeError(f"Could not acquire semaphore for task {task_id}")

                # 强制延迟：确保两次 API 调用之间至少有 delay 秒
                with self._lock:
                    elapsed = time.time() - self._last_call_time
                    if elapsed < self._delay:
                        time.sleep(self._delay - elapsed)
                    self._last_call_time = time.time()

                result = call_fn(*args, **kwargs)
                results[task_id] = result
            except Exception as e:
                results[task_id] = None
                raise
            finally:
                if acquired:
                    self._semaphore.release()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for task_id, args, kwargs in tasks:
                future = executor.submit(_throttled_call, task_id, args, kwargs)
                futures[future] = task_id

            for future in as_completed(futures):
                task_id = futures[future]
                try:
                    future.result(timeout=120)
                except Exception:
                    results[task_id] = None

        # 按原始顺序返回
        ordered_results = [(task_id, results[task_id]) for task_id, _, _ in tasks]
        return ordered_results

    def acquire(self):
        """手动获取一个并发槽位（配合 with 使用）。"""
        self._semaphore.acquire()

    def release(self):
        """手动释放一个并发槽位。"""
        self._semaphore.release()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *args):
        self.release()
