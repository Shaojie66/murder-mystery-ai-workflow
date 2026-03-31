"""Tests for session.py"""
import json
import tempfile
import os
from pathlib import Path
import pytest
from murder_wizard.wizard.session import SessionManager
from murder_wizard.wizard.state_machine import MurderWizardState, Stage


class TestSessionManager:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.project_name = "test_project"
        self.session = SessionManager(self.project_name, base_path=self.temp_dir)

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_project_path_constructed(self):
        expected = Path(self.temp_dir) / self.project_name
        assert self.session.project_path == expected

    def test_save_and_load(self):
        state = MurderWizardState(
            project_name=self.project_name,
            story_type="mechanic",
            current_stage=Stage.STAGE_1_MECHANISM,
            outline="# Test Outline",
        )
        self.session.save(state)

        loaded = self.session.load()
        assert loaded is not None
        assert loaded.project_name == self.project_name
        assert loaded.story_type == "mechanic"
        assert loaded.current_stage == Stage.STAGE_1_MECHANISM
        assert loaded.outline == "# Test Outline"

    def test_load_returns_none_when_no_session(self):
        result = self.session.load()
        assert result is None

    def test_load_returns_none_for_invalid_stage_value(self):
        self.session.ensure_project_dir()
        self.session.session_file.write_text(
            json.dumps(
                {
                    "project_name": self.project_name,
                    "story_type": "mechanic",
                    "current_stage": "not-a-stage",
                }
            ),
            encoding="utf-8",
        )

        result = self.session.load()
        assert result is None

    def test_save_creates_directory(self):
        state = MurderWizardState(project_name=self.project_name)
        assert not self.session.project_path.exists()
        self.session.save(state)
        assert self.session.project_path.exists()

    def test_log_cost(self):
        self.session.ensure_project_dir()
        self.session.log_cost("test_operation", 1000, 0.05)

        assert self.session.cost_log.exists()
        with open(self.session.cost_log) as f:
            entry = json.loads(f.readline())
        assert entry["operation"] == "test_operation"
        assert entry["tokens"] == 1000
        assert entry["cost"] == 0.05

    def test_get_total_cost(self):
        self.session.ensure_project_dir()
        self.session.log_cost("op1", 1000, 0.05)
        self.session.log_cost("op2", 2000, 0.10)

        total = self.session.get_total_cost()
        assert total == pytest.approx(0.15)

    def test_get_total_cost_empty(self):
        total = self.session.get_total_cost()
        assert total == 0.0

    def test_list_projects(self):
        self.session.ensure_project_dir()
        projects = self.session.list_projects()
        assert self.project_name in projects

    def test_list_projects_empty(self):
        session = SessionManager("nonexistent", base_path=self.temp_dir)
        projects = session.list_projects()
        assert "nonexistent" not in projects

    def test_recover_from_files(self):
        # Create outline file
        self.session.ensure_project_dir()
        outline_file = self.session.project_path / "outline.md"
        outline_file.write_text("# Test Outline", encoding="utf-8")

        state = self.session.recover_from_files()
        assert state is not None
        assert state.outline == "# Test Outline"
        assert state.current_stage == Stage.STORY_BRIEF

    def test_recover_from_files_no_files(self):
        self.session.ensure_project_dir()
        state = self.session.recover_from_files()
        assert state is None
