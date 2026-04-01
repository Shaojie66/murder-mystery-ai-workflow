"""Integration tests for Murder Wizard Web API.

Tests project CRUD and phase status endpoints using FastAPI TestClient
with mocked LLM adapter.

The conftest.py session-scoped fixture sets HOME to an isolated temp directory
BEFORE any modules are imported, so MURDER_WIZARD_BASE is correctly isolated
from the start.
"""
import pytest
import os
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


class TestProjectsAPI:
    """Test /api/projects endpoints."""

    def test_create_project_all_five_types(self):
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
                    )
                    assert response.status_code == 200, f"Failed for {story_type}: {response.text}"
                    data = response.json()
                    assert data["name"] == f"test-{story_type}"
                    assert data["status"] == "created"

    def test_get_project_returns_story_type_and_prototype_flag(self):
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
                )
                response = client.get("/api/projects/test-get-type")
                assert response.status_code == 200
                data = response.json()
                assert data["story_type"] == "reasoning"
                assert data["is_prototype"] == False

    def test_delete_project_removes_it(self):
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
                )
                assert client.get("/api/projects/to-delete").status_code == 200
                response = client.delete("/api/projects/to-delete")
                assert response.status_code == 200
                assert client.get("/api/projects/to-delete").status_code == 404

    def test_list_projects_returns_correct_count(self):
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
                    )
                    assert r.status_code == 200
                    created.append(name)
                # List — should only return the 3 we just created (isolated dir)
                response = client.get("/api/projects")
                assert response.status_code == 200
                data = response.json()
                names = [p["name"] for p in data["projects"]]
                assert set(names) == set(created), f"Expected {set(created)}, got {set(names)}"


class TestPhasesAPI:
    """Test /api/projects/{name}/phases/* endpoints."""

    def test_phase_status_shows_not_running_after_creation(self):
        """Newly created project has no running phase."""
        from fastapi.testclient import TestClient
        from murder_wizard_web.backend.main import app

        with patch("murder_wizard.llm.client.create_llm_adapter", _mock_llm_factory()):
            with TestClient(app) as client:
                client.post(
                    "/api/projects",
                    json={"name": "status-test", "story_type": "emotion", "is_prototype": True, "era": "现代", "answers": {}},
                )
                response = client.get("/api/projects/status-test/phases/1/status")
                assert response.status_code == 200
                data = response.json()
                assert data["running"] == False

    def test_cancel_returns_cancelled_true(self):
        """Cancel endpoint always returns cancelled=True."""
        from fastapi.testclient import TestClient
        from murder_wizard_web.backend.main import app

        with patch("murder_wizard.llm.client.create_llm_adapter", _mock_llm_factory()):
            with TestClient(app) as client:
                response = client.post("/api/projects/nonexistent/phases/1/cancel")
                assert response.status_code == 200
                assert response.json()["cancelled"] == True
