"""追加写的 JSONL 存储：留资与统计的最小持久化。

约定（docs/local-only-boundary.md）：
- 位置 ~/.murder-wizard/landing/{subscriptions,events}.jsonl，目录 0700、文件 0600（邮箱是个人信息）；
- 每行一个 JSON 对象，带 schema 版本字段；只追加，工具永不自动删除、不改写；
- 启动（首次使用）时回放；损坏的行跳过并计数，不让服务起不来；
- 写入失败必须让调用方知道（先写盘再改内存），不能返回"已记录"；
- 只适合本地单进程：多进程同时写没有保证。
"""
import json
import logging
import os
import threading
from pathlib import Path
from typing import Iterator

log = logging.getLogger(__name__)
_lock = threading.Lock()


def landing_dir() -> Path:
    """每次调用时才解析 HOME，便于测试隔离。"""
    return Path.home() / ".murder-wizard" / "landing"


class JsonlStore:
    def __init__(self, filename: str, schema: str):
        self.filename = filename
        self.schema = schema

    @property
    def path(self) -> Path:
        return landing_dir() / self.filename

    def append(self, record: dict) -> None:
        """追加一行并 fsync；任何失败都抛出 OSError，由调用方决定如何告知用户。"""
        line = json.dumps({"schema": self.schema, **record}, ensure_ascii=False) + "\n"
        with _lock:
            d = landing_dir()
            d.mkdir(parents=True, exist_ok=True)
            try:
                os.chmod(d, 0o700)
            except OSError:
                pass
            fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
            try:
                os.write(fd, line.encode("utf-8"))
                os.fsync(fd)
            finally:
                os.close(fd)

    def replay(self) -> tuple[list[dict], int]:
        """返回 (有效记录, 损坏行数)。文件不存在 = 空；不会抛出。"""
        records: list[dict] = []
        bad = 0
        try:
            raw = self.path.read_bytes()
        except FileNotFoundError:
            return records, 0
        except OSError as e:
            log.warning("无法读取 %s：%s", self.path, e)
            return records, 0
        for n, chunk in enumerate(raw.split(b"\n"), 1):
            if not chunk.strip():
                continue
            try:
                obj = json.loads(chunk.decode("utf-8"))
                if not isinstance(obj, dict) or obj.get("schema") != self.schema:
                    raise ValueError("schema 不符")
                records.append(obj)
            except (ValueError, UnicodeDecodeError):
                bad += 1
                log.warning("%s 第 %d 行已损坏，已跳过", self.path.name, n)
        return records, bad
