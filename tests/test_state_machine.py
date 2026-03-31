"""Tests for state_machine.py"""
import pytest
from murder_wizard.wizard.state_machine import MurderWizardState, Stage


class TestMurderWizardState:
    def test_default_initialization(self):
        state = MurderWizardState(project_name="test_project")
        assert state.project_name == "test_project"
        assert state.story_type == "mechanic"
        assert state.current_stage == Stage.IDLE
        assert state.is_prototype == False
        assert state.outline is None

    def test_to_dict(self):
        state = MurderWizardState(
            project_name="test",
            story_type="emotion",
            current_stage=Stage.STAGE_1_MECHANISM,
            outline="# Test Outline",
            is_prototype=True,
        )
        data = state.to_dict()
        assert data["project_name"] == "test"
        assert data["story_type"] == "emotion"
        assert data["current_stage"] == Stage.STAGE_1_MECHANISM.value
        assert data["current_stage_slug"] == "stage_1_mechanism"
        assert data["outline"] == "# Test Outline"
        assert data["is_prototype"] == True

    def test_from_dict(self):
        data = {
            "project_name": "test",
            "story_type": "puzzle",
            "current_stage": "stage_2_script",
            "outline": "Test",
            "is_prototype": False,
        }
        state = MurderWizardState.from_dict(data)
        assert state.project_name == "test"
        assert state.story_type == "puzzle"
        assert state.current_stage == Stage.STAGE_2_SCRIPT

    def test_can_advance_to_valid_transition(self):
        state = MurderWizardState(
            project_name="test",
            current_stage=Stage.STAGE_1_MECHANISM,
        )
        assert state.can_advance_to(Stage.STAGE_2_SCRIPT) == True

    def test_can_advance_to_invalid_transition(self):
        state = MurderWizardState(
            project_name="test",
            current_stage=Stage.STAGE_1_MECHANISM,
        )
        assert state.can_advance_to(Stage.STAGE_3_VISUAL) == False

    def test_advance_to(self):
        state = MurderWizardState(
            project_name="test",
            current_stage=Stage.STAGE_1_MECHANISM,
        )
        state.advance_to(Stage.STAGE_2_SCRIPT)
        assert state.current_stage == Stage.STAGE_2_SCRIPT

    def test_advance_to_invalid_raises(self):
        state = MurderWizardState(
            project_name="test",
            current_stage=Stage.STAGE_1_MECHANISM,
        )
        with pytest.raises(ValueError):
            state.advance_to(Stage.STAGE_4_TEST)


class TestStage:
    def test_stage_values(self):
        assert Stage.STAGE_1_MECHANISM.value < Stage.STAGE_4_TEST.value
        assert Stage.STAGE_4_TEST.value < Stage.STAGE_8_COMMUNITY.value
        assert Stage.STAGE_1_MECHANISM.slug == "stage_1_mechanism"
        assert Stage.STAGE_4_TEST.slug == "stage_4_test"
        assert Stage.STAGE_8_COMMUNITY.slug == "stage_8_community"

    def test_stage_from_string(self):
        stage = Stage.from_value("stage_2_script")
        assert stage == Stage.STAGE_2_SCRIPT

    def test_stage_from_numeric_value(self):
        stage = Stage.from_value(Stage.STAGE_2_SCRIPT.value)
        assert stage == Stage.STAGE_2_SCRIPT
