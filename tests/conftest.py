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
