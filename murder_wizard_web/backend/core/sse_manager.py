"""SSE connection manager for tracking active streams per project."""
import asyncio
from typing import AsyncGenerator, Optional
import uuid


class SSEConnection:
    """A single SSE connection with its queue."""

    def __init__(self, project_name: str):
        self.id = str(uuid.uuid4())[:8]
        self.project_name = project_name
        self.queue: asyncio.Queue[Optional[dict]] = asyncio.Queue()
        self._cancelled = False

    async def event_stream(self) -> AsyncGenerator[str, None]:
        """Yield SSE-formatted events from the queue."""
        while not self._cancelled:
            try:
                event = await asyncio.wait_for(self.queue.get(), timeout=60)
                if event is None:
                    # End signal
                    yield f"event: end\ndata: {{}}\n\n"
                    break
                yield f"event: {event['event']}\ndata: {event['data']}\n\n"
            except asyncio.TimeoutError:
                # Keepalive: send a comment every 60s
                yield f": keepalive\n\n"

    def put(self, event: str, data: dict) -> None:
        """Add an event to the queue (thread-safe)."""
        if not self._cancelled:
            try:
                self.queue.put_nowait({"event": event, "data": data})
            except asyncio.QueueFull:
                pass

    def cancel(self) -> None:
        """Signal this connection to end."""
        self._cancelled = True
        self.queue.put_nowait(None)


class SSEManager:
    """Manages all active SSE connections. One connection per project."""

    def __init__(self):
        self._connections: dict[str, SSEConnection] = {}
        self._lock = asyncio.Lock()

    async def create_connection(self, project_name: str) -> SSEConnection:
        """Create a new SSE connection for a project."""
        async with self._lock:
            # Cancel existing connection if any
            await self.cancel_connection(project_name)
            conn = SSEConnection(project_name)
            self._connections[project_name] = conn
            return conn

    async def get_connection(self, project_name: str) -> Optional[SSEConnection]:
        """Get existing connection for a project."""
        async with self._lock:
            return self._connections.get(project_name)

    async def cancel_connection(self, project_name: str) -> None:
        """Cancel and remove connection for a project."""
        async with self._lock:
            if project_name in self._connections:
                self._connections[project_name].cancel()
                del self._connections[project_name]

    def is_running(self, project_name: str) -> bool:
        """Check if a project is currently running."""
        return project_name in self._connections


# Global SSE manager instance
sse_manager = SSEManager()
