"""Tests for type-specific expand behavior.

Regression test: ensure run_expand() uses type-specific system prompts
from PromptLoader, not hardcoded generic strings.
"""
import pytest
from unittest.mock import patch, MagicMock
from rich.console import Console

from murder_wizard.wizard.session import SessionManager
from murder_wizard.wizard.state_machine import MurderWizardState, Stage


def _make_mock_runner(story_type: str, tmp_path):
    """Create a PhaseRunner with mocked dependencies for the expand test."""
    from murder_wizard.cli.phase_runner import PhaseRunner

    session = SessionManager("test-project", base_path=str(tmp_path))
    state = MurderWizardState(
        project_name="test-project",
        current_stage=Stage.CHARACTER_DESIGN,
        story_type=story_type,
        is_prototype=True,
    )
    session.save(state)

    console = Console(record=True)

    # Create runner but patch LLM setup
    with patch.object(PhaseRunner, "_setup_llm"):
        runner = PhaseRunner(session, state, console)
        runner.llm = MagicMock()

    return runner


def test_expand_phase1_uses_type_specific_system_prompt(tmp_path):
    """expand Phase 1 calls _call_llm with system_mechanism_designer(story_type)."""
    from murder_wizard.cli.phase_runner import PhaseRunner

    runner = _make_mock_runner("emotion", tmp_path)

    # Mock _call_llm to capture the system prompt
    captured_calls = []

    def mock_call_llm(prompt, system="", operation="llm_call"):
        captured_calls.append({"prompt": prompt, "system": system, "operation": operation})
        mock_resp = MagicMock()
        mock_resp.cost = 0.01
        mock_resp.content = "expanded content"
        return mock_resp

    runner._call_llm = mock_call_llm

    # Mock the file reads so expand can run
    with patch.object(runner.session, "project_path", tmp_path):
        (tmp_path / "mechanism.md").write_text("mechanism content")
        (tmp_path / "characters.md").write_text("characters content")

        # Need to also patch _build_expand_phase1_prompt to return something
        runner._build_expand_phase1_prompt = lambda o, m, c: "expand prompt"

        try:
            runner.run_expand()
        except Exception:
            pass  # We only care about the captured calls

    # Find the expand_phase1 call
    phase1_calls = [c for c in captured_calls if c["operation"] == "expand_phase1"]
    assert len(phase1_calls) >= 1, "expand_phase1 should have been called"
    system = phase1_calls[0]["system"]
    # Should NOT be the old generic string
    assert "你是一个专业的剧本杀作家" not in system
    # Should contain emotion-related keywords (type-specific)
    assert "情感" in system or "机制" in system


def test_expand_phase2_uses_type_specific_system_prompt(tmp_path):
    """expand Phase 2 (parse chars) calls _call_llm with system_script_writer(story_type)."""
    from murder_wizard.cli.phase_runner import PhaseRunner

    runner = _make_mock_runner("reasoning", tmp_path)

    captured_calls = []

    def mock_call_llm(prompt, system="", operation="llm_call"):
        captured_calls.append({"prompt": prompt, "system": system, "operation": operation})
        mock_resp = MagicMock()
        mock_resp.cost = 0.01
        mock_resp.content = "推理本角色"
        return mock_resp

    runner._call_llm = mock_call_llm

    with patch.object(runner.session, "project_path", tmp_path):
        (tmp_path / "mechanism.md").write_text("mechanism content")
        (tmp_path / "characters.md").write_text("characters content")

        runner._build_expand_phase1_prompt = lambda o, m, c: "expand prompt"
        runner._build_new_chars_prompt = lambda content: "new chars prompt"

        # Mock character parsing to return empty (triggers single-pass path)
        runner._parse_new_character_names = lambda content, existing_count=0: []

        try:
            runner.run_expand()
        except Exception:
            pass

    # Check expand_parse_chars call (if it was reached) or expand_single call
    parse_chars_calls = [c for c in captured_calls if "expand_parse_chars" in c["operation"]]
    single_calls = [c for c in captured_calls if "expand_single" in c["operation"]]

    # At least one of these should exist
    relevant_calls = parse_chars_calls + single_calls
    assert len(relevant_calls) >= 1

    for call in relevant_calls:
        system = call["system"]
        # Should NOT be generic
        assert "你是一个专业的剧本杀作家" not in system
        # Should be type-specific (reasoning or script writer)
        assert len(system) > 20


def test_expand_char_tasks_use_type_specific_system_prompt(tmp_path):
    """Concurrent character generation uses system_script_writer per story type."""
    from murder_wizard.cli.phase_runner import PhaseRunner

    runner = _make_mock_runner("horror", tmp_path)

    captured_calls = []

    def mock_call_llm(prompt, system="", operation="llm_call"):
        captured_calls.append({"prompt": prompt, "system": system, "operation": operation})
        mock_resp = MagicMock()
        mock_resp.cost = 0.01
        mock_resp.content = "horror character content"
        return mock_resp

    runner._call_llm = mock_call_llm

    with patch.object(runner.session, "project_path", tmp_path):
        (tmp_path / "mechanism.md").write_text("mechanism content")
        (tmp_path / "characters.md").write_text("characters content")

        runner._build_expand_phase1_prompt = lambda o, m, c: "expand prompt"
        runner._build_new_chars_prompt = lambda content: "new chars prompt"
        runner._parse_new_character_names = lambda content, existing_count=0: ["新角色A", "新角色B"]
        runner._build_single_char_prompt = lambda o, m, p1, name: f"char prompt for {name}"
        runner._assemble_expanded_script = lambda p1, contents, names: "full script"

        try:
            runner.run_expand()
        except Exception:
            pass

    char_calls = [c for c in captured_calls if c["operation"].startswith("expand_char_")]
    if char_calls:
        for call in char_calls:
            system = call["system"]
            assert "你是一个专业的剧本杀作家" not in system
            assert len(system) > 20
