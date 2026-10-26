"""Integration tests for Murder Wizard Web API.

Tests project CRUD and phase status endpoints using FastAPI TestClient
with mocked LLM adapter.

The conftest.py session-scoped fixture sets HOME to an isolated temp directory
BEFORE any modules are imported, so MURDER_WIZARD_BASE is correctly isolated
from the start.
"""
import json
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "murder_wizard_web" / "backend"))


class MockLLMResponse:
    """Fake LLM response matching LLMResponse dataclass."""
    def __init__(self, content: str = "", tokens_used: int = 100, cost: float = 0.01):
        self.content = content
        self.tokens_used = tokens_used
        self.cost = cost
        self.model = "mock-model"


def _mock_llm_factory():
    def mock_create(provider=None, settings=None):
        mock = MagicMock()
        mock.complete = lambda prompt, system="": MockLLMResponse(content="# 机制设计\n\nmock content")
        mock.complete_streaming = lambda p, s=0: iter(["streaming content"])
        return mock
    return mock_create


# The isolated murder-wizard base directory (set by conftest.py via HOME env)
_MURDER_WIZARD_BASE = Path.home() / ".murder-wizard" / "projects"


def _clean_projects_dir():
    """Remove all projects from the isolated test directory."""
    if _MURDER_WIZARD_BASE.exists():
        import shutil
        for p in _MURDER_WIZARD_BASE.iterdir():
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)


@pytest.fixture(autouse=True)
def clean_isolated_projects():
    """Clean isolated projects directory before and after each test."""
    _clean_projects_dir()
    yield
    _clean_projects_dir()


@pytest.fixture
def auth_headers():
    """Return a valid Authorization header for test requests."""
    from core.auth import encode_token
    token = encode_token("test-user")
    return {"Authorization": f"Bearer {token}"}


class TestProjectsAPI:
    """Test /api/projects endpoints."""

    def test_list_projects_requires_auth(self):
        """GET /api/projects rejects unauthenticated access."""
        from fastapi.testclient import TestClient
        from murder_wizard_web.backend.main import app

        with TestClient(app) as client:
            response = client.get("/api/projects")
            assert response.status_code == 401

    def test_create_project_all_five_types(self, auth_headers):
        """POST /api/projects creates projects for all 5 story types."""
        from fastapi.testclient import TestClient
        from murder_wizard_web.backend.main import app

        with patch("murder_wizard.llm.client.create_llm_adapter", _mock_llm_factory()):
            with TestClient(app) as client:
                for story_type in ["emotion", "reasoning", "fun", "horror", "mechanic"]:
                    response = client.post(
                        "/api/projects",
                        json={
                            "name": f"test-{story_type}",
                            "story_type": story_type,
                            "is_prototype": True,
                            "era": "现代",
                            "answers": {},
                        },
                        headers=auth_headers,
                    )
                    assert response.status_code == 200, f"Failed for {story_type}: {response.text}"
                    data = response.json()
                    assert data["name"] == f"test-{story_type}"
                    assert data["status"] == "created"

    def test_get_project_returns_story_type_and_prototype_flag(self, auth_headers):
        """GET /api/projects/{name} returns correct story_type and is_prototype."""
        from fastapi.testclient import TestClient
        from murder_wizard_web.backend.main import app

        with patch("murder_wizard.llm.client.create_llm_adapter", _mock_llm_factory()):
            with TestClient(app) as client:
                client.post(
                    "/api/projects",
                    json={
                        "name": "test-get-type",
                        "story_type": "reasoning",
                        "is_prototype": False,
                        "era": "现代",
                        "answers": {},
                    },
                    headers=auth_headers,
                )
                response = client.get("/api/projects/test-get-type", headers=auth_headers)
                assert response.status_code == 200
                data = response.json()
                assert data["story_type"] == "reasoning"
                assert data["is_prototype"] == False

    def test_delete_project_removes_it(self, auth_headers):
        """DELETE /api/projects/{name} removes the project."""
        from fastapi.testclient import TestClient
        from murder_wizard_web.backend.main import app

        with patch("murder_wizard.llm.client.create_llm_adapter", _mock_llm_factory()):
            with TestClient(app) as client:
                client.post(
                    "/api/projects",
                    json={
                        "name": "to-delete",
                        "story_type": "mechanic",
                        "is_prototype": True,
                        "era": "现代",
                        "answers": {},
                    },
                    headers=auth_headers,
                )
                assert client.get("/api/projects/to-delete", headers=auth_headers).status_code == 200
                response = client.delete("/api/projects/to-delete", headers=auth_headers)
                assert response.status_code == 200
                assert client.get("/api/projects/to-delete", headers=auth_headers).status_code == 404

    @pytest.mark.parametrize("bad_name", ["../escape", "..", ".hidden", "/tmp/x", "bad/name"])
    def test_create_project_rejects_path_traversal_names(self, auth_headers, bad_name):
        """Project creation rejects invalid names before touching disk."""
        from fastapi.testclient import TestClient
        from murder_wizard_web.backend.main import app

        with patch("murder_wizard.llm.client.create_llm_adapter", _mock_llm_factory()):
            with TestClient(app) as client:
                create_response = client.post(
                    "/api/projects",
                    json={
                        "name": bad_name,
                        "story_type": "mechanic",
                        "is_prototype": True,
                        "era": "现代",
                        "answers": {},
                    },
                    headers=auth_headers,
                )
                assert create_response.status_code == 400

    @pytest.mark.parametrize("bad_name", [".hidden"])
    def test_get_delete_project_reject_invalid_segment_names(self, auth_headers, bad_name):
        """Get/delete endpoints reject invalid path-segment names that reach the handler."""
        from fastapi.testclient import TestClient
        from murder_wizard_web.backend.main import app

        with patch("murder_wizard.llm.client.create_llm_adapter", _mock_llm_factory()):
            with TestClient(app) as client:
                get_response = client.get(f"/api/projects/{bad_name}", headers=auth_headers)
                assert get_response.status_code == 400

                delete_response = client.delete(f"/api/projects/{bad_name}", headers=auth_headers)
                assert delete_response.status_code == 400

    def test_list_projects_returns_correct_count(self, auth_headers):
        """GET /api/projects returns exactly the projects created in this test."""
        from fastapi.testclient import TestClient
        from murder_wizard_web.backend.main import app

        with patch("murder_wizard.llm.client.create_llm_adapter", _mock_llm_factory()):
            with TestClient(app) as client:
                # Create 3 projects with unique names
                created = []
                for name, stype in [("list-a", "emotion"), ("list-b", "reasoning"), ("list-c", "horror")]:
                    r = client.post(
                        "/api/projects",
                        json={"name": name, "story_type": stype, "is_prototype": True, "era": "现代", "answers": {}},
                        headers=auth_headers,
                    )
                    assert r.status_code == 200
                    created.append(name)
                # List — should only return the 3 we just created (isolated dir)
                response = client.get("/api/projects", headers=auth_headers)
                assert response.status_code == 200
                data = response.json()
                names = [p["name"] for p in data["projects"]]
                assert set(names) == set(created), f"Expected {set(created)}, got {set(names)}"

    def test_create_project_generates_outline_and_full_mode_brief(self, auth_headers):
        """Create flow persists brief.md, outline.md, and session outline for full mode."""
        from fastapi.testclient import TestClient
        from murder_wizard_web.backend.main import app

        with patch("murder_wizard.llm.client.create_llm_adapter", _mock_llm_factory()):
            with TestClient(app) as client:
                response = client.post(
                    "/api/projects",
                    json={
                        "name": "full-mode",
                        "story_type": "reasoning",
                        "is_prototype": False,
                        "era": "民国",
                        "answers": {"核心冲突": "真相 vs 忠诚"},
                    },
                    headers=auth_headers,
                )
                assert response.status_code == 200

        project_path = _MURDER_WIZARD_BASE / "full-mode"
        brief = (project_path / "brief.md").read_text(encoding="utf-8")
        outline = (project_path / "outline.md").read_text(encoding="utf-8")
        session_data = json.loads((project_path / "session.json").read_text(encoding="utf-8"))

        assert "完整模式（6人）" in brief
        assert outline == "# 机制设计\n\nmock content"
        assert session_data["outline"] == outline

    def test_create_project_rolls_back_on_outline_failure(self, auth_headers):
        """Outline bootstrap failure does not leave a half-created project behind."""
        from fastapi.testclient import TestClient
        from murder_wizard_web.backend.main import app

        def _failing_factory(provider=None, settings=None):
            mock = MagicMock()
            mock.complete.side_effect = RuntimeError("outline failed")
            return mock

        with patch("murder_wizard.llm.client.create_llm_adapter", _failing_factory):
            with TestClient(app) as client:
                response = client.post(
                    "/api/projects",
                    json={
                        "name": "broken-outline",
                        "story_type": "mechanic",
                        "is_prototype": True,
                        "era": "现代",
                        "answers": {},
                    },
                    headers=auth_headers,
                )

        assert response.status_code == 502
        assert not (_MURDER_WIZARD_BASE / "broken-outline").exists()

    def test_workbench_repairs_missing_outline_and_returns_read_model(self, auth_headers):
        """Workbench request repairs missing outline state and returns grouped workbench DTO."""
        from fastapi.testclient import TestClient
        from murder_wizard.wizard.session import SessionManager
        from murder_wizard.wizard.state_machine import MurderWizardState, Stage
        from murder_wizard_web.backend.main import app

        project_path = _MURDER_WIZARD_BASE / "repair-me"
        project_path.mkdir(parents=True, exist_ok=True)
        (project_path / "brief.md").write_text("# brief", encoding="utf-8")

        session = SessionManager("repair-me")
        session.save(
            MurderWizardState(
                project_name="repair-me",
                story_type="mechanic",
                current_stage=Stage.IDLE,
                outline="",
                is_prototype=True,
            )
        )

        with patch("murder_wizard.llm.client.create_llm_adapter", _mock_llm_factory()):
            with TestClient(app) as client:
                response = client.get("/api/projects/repair-me/workbench", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert set(data.keys()) == {"project", "workflow", "readiness", "artifacts", "quick_actions"}
        assert data["readiness"]["outline_ready"] is True
        assert data["project"]["artifacts"]["outline.md"]["exists"] is True
        assert (project_path / "outline.md").read_text(encoding="utf-8") == "# 机制设计\n\nmock content"

    def test_project_scoped_routes_require_auth(self, auth_headers):
        """All project-scoped routes reject missing auth and allow authenticated access."""
        from fastapi.testclient import TestClient
        from murder_wizard_web.backend.main import app

        with patch("murder_wizard.llm.client.create_llm_adapter", _mock_llm_factory()):
            with TestClient(app) as client:
                create = client.post(
                    "/api/projects",
                    json={"name": "auth-scope", "story_type": "mechanic", "is_prototype": True, "era": "现代", "answers": {}},
                    headers=auth_headers,
                )
                assert create.status_code == 200

                unauth_routes = [
                    ("get", "/api/projects/auth-scope"),
                    ("get", "/api/projects/auth-scope/workbench"),
                    ("get", "/api/projects/auth-scope/files"),
                    ("get", "/api/projects/auth-scope/phases/1/status"),
                    ("post", "/api/projects/auth-scope/phases/1/run"),
                    ("post", "/api/projects/auth-scope/expand"),
                    ("post", "/api/projects/auth-scope/audit"),
                    ("get", "/api/projects/auth-scope/audit/report"),
                    ("get", "/api/projects/auth-scope/matrix"),
                    ("get", "/api/projects/auth-scope/costs"),
                ]

                for method, url in unauth_routes:
                    response = getattr(client, method)(url)
                    assert response.status_code == 401, f"{method.upper()} {url} should require auth"

                auth_routes = [
                    ("get", "/api/projects/auth-scope"),
                    ("get", "/api/projects/auth-scope/workbench"),
                    ("get", "/api/projects/auth-scope/files"),
                    ("get", "/api/projects/auth-scope/phases/1/status"),
                    ("get", "/api/projects/auth-scope/audit/report"),
                    ("get", "/api/projects/auth-scope/matrix"),
                    ("get", "/api/projects/auth-scope/costs"),
                ]

                for method, url in auth_routes:
                    response = getattr(client, method)(url, headers=auth_headers)
                    assert response.status_code != 401, f"{method.upper()} {url} should allow auth"


class TestPhasesAPI:
    """Test /api/projects/{name}/phases/* endpoints."""

    def test_phase_status_shows_not_running_after_creation(self, auth_headers):
        """Newly created project has no running phase."""
        from fastapi.testclient import TestClient
        from murder_wizard_web.backend.main import app

        with patch("murder_wizard.llm.client.create_llm_adapter", _mock_llm_factory()):
            with TestClient(app) as client:
                client.post(
                    "/api/projects",
                    json={"name": "status-test", "story_type": "emotion", "is_prototype": True, "era": "现代", "answers": {}},
                    headers=auth_headers,
                )
                response = client.get("/api/projects/status-test/phases/1/status", headers=auth_headers)
                assert response.status_code == 200
                data = response.json()
                assert data["running"] == False

    def test_cancel_without_running_task_reports_nothing_cancelled(self, auth_headers):
        """取消只是请求：没有运行中的任务时 cancel_requested=False，且从不宣称已停止。"""
        from fastapi.testclient import TestClient
        from murder_wizard_web.backend.main import app

        with patch("murder_wizard.llm.client.create_llm_adapter", _mock_llm_factory()):
            with TestClient(app) as client:
                response = client.post("/api/projects/nonexistent/phases/1/cancel", headers=auth_headers)
                assert response.status_code == 200
                body = response.json()
                assert body["cancel_requested"] is False and body["stopped"] is False
