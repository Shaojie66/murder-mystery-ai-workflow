"""任务/SSE 连接管理：每个作品同一时刻至多一个写入任务，运行、查询、取消共用同一个对象。

- put / put_nowait 线程安全（引擎在工作线程里跑，经 loop.call_soon_threadsafe 投递）；
- SSE data 一律是 JSON 字符串；
- 终态由任务包装器保证：先投递 end 事件，再关闭队列；event_stream 消费完队列才退出；
- cancel 只表示"请求取消"：底层同步调用无法被打断，作品写锁（登记）持续到任务线程真正结束。
"""
import asyncio
import json
import uuid
from typing import AsyncGenerator, Optional

KEEPALIVE_SECONDS = 60


class SSEConnection:
    """一个任务的事件队列与状态（status: running | success | failed | cancelled）。"""

    def __init__(self, project_name: str, loop: Optional[asyncio.AbstractEventLoop] = None):
        self.id = str(uuid.uuid4())[:8]
        self.project_name = project_name
        self.loop = loop or asyncio.get_running_loop()
        self.queue: asyncio.Queue = asyncio.Queue()
        self.status = "running"
        self.cancel_requested = False
        self.task: Optional[asyncio.Task] = None
        self._closed = False

    def put_nowait(self, item: dict) -> None:
        """线程安全投递（SSEConsole / ProgressTracker / PhaseRunnerWeb 都通过它）。"""
        if self._closed:
            return
        try:
            self.loop.call_soon_threadsafe(self.queue.put_nowait, item)
        except RuntimeError:  # 事件循环已关闭
            pass

    def put(self, event: str, data: dict) -> None:
        self.put_nowait({"event": event, "data": data})

    def close(self) -> None:
        """投递结束哨兵；之后不再接受事件。已排队的事件仍会被消费完。"""
        if self._closed:
            return
        try:
            self.loop.call_soon_threadsafe(self.queue.put_nowait, None)
        except RuntimeError:
            pass
        self._closed = True

    def request_cancel(self) -> None:
        self.cancel_requested = True

    async def event_stream(self) -> AsyncGenerator[dict, None]:
        """逐个产出 {"event", "data": JSON 字符串}，直到哨兵；哨兵之前的事件全部送达。"""
        while True:
            try:
                item = await asyncio.wait_for(self.queue.get(), timeout=KEEPALIVE_SECONDS)
            except asyncio.TimeoutError:
                yield {"event": "keepalive", "data": "{}"}
                continue
            if item is None:
                return
            yield {"event": item["event"], "data": json.dumps(item["data"], ensure_ascii=False, default=str)}


class SSEManager:
    """作品级任务登记。try_start 在发出响应之前同步登记，重复运行因此稳定得到 409。"""

    def __init__(self):
        self._connections: dict[str, SSEConnection] = {}

    def try_start(self, project_name: str) -> Optional[SSEConnection]:
        if project_name in self._connections:
            return None
        conn = SSEConnection(project_name)
        self._connections[project_name] = conn
        return conn

    def release(self, project_name: str, conn: SSEConnection) -> None:
        if self._connections.get(project_name) is conn:
            del self._connections[project_name]

    def get(self, project_name: str) -> Optional[SSEConnection]:
        return self._connections.get(project_name)

    def request_cancel(self, project_name: str) -> bool:
        conn = self._connections.get(project_name)
        if conn is None:
            return False
        conn.request_cancel()
        return True

    def is_running(self, project_name: str) -> bool:
        return project_name in self._connections


# 全局唯一实例：所有模块必须用 `core.sse_manager` 这一个导入名
sse_manager = SSEManager()
