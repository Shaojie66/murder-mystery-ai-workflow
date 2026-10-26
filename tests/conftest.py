"""conftest.py - Set up isolated HOME directory for murder-wizard tests.

This runs at pytest collection time, BEFORE any test modules are imported.
Setting HOME here ensures that when `murder_wizard_web.backend.api.projects`
is first imported (when TestClient(app) references it), the Path.home() call
inside that module returns our isolated temp directory.

For per-test cleanup, the autouse fixture in test_api_integration.py
handles removing any created projects.
"""
import os
import sys
from pathlib import Path
import tempfile

# Create a session-scoped temp directory
_MW_TEST_HOME = Path(tempfile.mkdtemp(prefix="murder-wizard-test-"))
os.environ["HOME"] = str(_MW_TEST_HOME)

# Ensure the backend is on the path for imports
_repo_root = Path(__file__).parent.parent
_backend_path = _repo_root / "murder_wizard_web" / "backend"
if str(_backend_path) not in sys.path:
    sys.path.insert(0, str(_backend_path))


# ─── 故障注入：写文件写到一半磁盘满 ────────────────────────────────────────────
import contextlib
import errno
import io
from unittest.mock import patch

import pytest


class _DiskFullFile:
    """包住真实文件对象：第一次 write 只写进三分之一的内容，然后像磁盘满一样抛 ENOSPC。"""

    def __init__(self, handle):
        self._handle = handle

    def write(self, data):
        self._handle.write(data[: len(data) // 3])
        self._handle.flush()
        raise OSError(errno.ENOSPC, "No space left on device")

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self._handle.close()
        return False

    def __getattr__(self, name):
        return getattr(self._handle, name)


@pytest.fixture
def disk_full():
    """``with disk_full(match):`` 期间，路径满足 ``match(Path)`` 的写模式 open() 都会写到一半失败。

    不依赖被测代码用哪个 API 写文件：builtins.open、io.open（pathlib 走这里）、Path.write_text 都会被拦到。
    """

    @contextlib.contextmanager
    def inject(match):
        real_open = io.open

        def fake_open(file, mode="r", *args, **kwargs):
            handle = real_open(file, mode, *args, **kwargs)
            if (
                isinstance(file, (str, bytes, os.PathLike))
                and any(flag in mode for flag in "wax")
                and match(Path(os.fsdecode(file)))
            ):
                return _DiskFullFile(handle)
            return handle

        with patch("builtins.open", fake_open), patch("io.open", fake_open):
            yield

    return inject
