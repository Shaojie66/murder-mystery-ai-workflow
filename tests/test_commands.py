"""Tests for CLI commands."""
from unittest.mock import patch

from rich.console import Console

from murder_wizard.cli.commands import run_phase, show_status
from murder_wizard.wizard.session import SessionManager
from murder_wizard.wizard.state_machine import MurderWizardState, Stage


def test_show_status_uses_stage_ordering(tmp_path):
    session = SessionManager("demo", base_path=str(tmp_path))
    session.save(
        MurderWizardState(
            project_name="demo",
            current_stage=Stage.STAGE_2_SCRIPT,
        )
    )

    console = Console(record=True, width=120)
    show_status(session, console)
    output = console.export_text()

    assert "阶段1：机制设计" in output
    assert "阶段2：剧本创作" in output
    assert "阶段3：视觉物料" in output
    assert "✓ 已完成" in output
    assert "→ 进行中" in output
    assert "○ 待开始" in output


def test_run_phase_stage_4_routes_analyze_to_special_handler(tmp_path):
    session = SessionManager("demo", base_path=str(tmp_path))
    session.save(MurderWizardState(project_name="demo", current_stage=Stage.STAGE_4_TEST))
    console = Console(record=True, width=120)

    with patch("murder_wizard.cli.commands.PhaseRunner") as runner_cls, patch(
        "murder_wizard.cli.commands._run_stage_4_analyze",
        return_value=True,
    ) as analyze_fn:
        run_phase(session, 4, console, analyze=True)

    analyze_fn.assert_called_once()
    runner_cls.return_value.run_stage_4.assert_not_called()


def test_run_phase_stage_4_without_analyze_uses_runner(tmp_path):
    session = SessionManager("demo", base_path=str(tmp_path))
    session.save(MurderWizardState(project_name="demo", current_stage=Stage.STAGE_4_TEST))
    console = Console(record=True, width=120)

    with patch("murder_wizard.cli.commands.PhaseRunner") as runner_cls, patch(
        "murder_wizard.cli.commands._run_stage_4_analyze",
        return_value=True,
    ) as analyze_fn:
        runner_cls.return_value.run_stage_4.return_value = True
        run_phase(session, 4, console, analyze=False)

    runner_cls.return_value.run_stage_4.assert_called_once()
    analyze_fn.assert_not_called()


# ── expand 命令（R03/R04）──────────────────────────────────────────────

def test_expand_non_tty_without_yes_refuses_before_constructing_runner(tmp_path, monkeypatch):
    from unittest.mock import patch
    from rich.console import Console
    from murder_wizard.cli import commands as C
    from tests.expand_helpers import make_prototype_project
    runner, root = make_prototype_project(tmp_path)
    monkeypatch.setattr("sys.stdin", type("S", (), {"isatty": lambda self: False})())
    with patch.object(C, "PhaseRunner") as P:
        assert C.run_expand(runner.session, Console(record=True)) is False
        P.assert_not_called()


def test_expand_yes_passes_accept_overwrite_and_failure_exits_1(tmp_path, monkeypatch):
    from unittest.mock import patch
    from click.testing import CliRunner
    import murder_wizard.cli as cli
    from murder_wizard.cli import commands as C
    from tests.expand_helpers import ScriptedLLM, make_prototype_project
    for fail, code in ((None, 0), ({"expand_dm": "invalid"}, 1)):
        runner, root = make_prototype_project(tmp_path / str(code))
        ScriptedLLM(runner, root, fail=fail)
        monkeypatch.setattr(cli, "SessionManager", lambda name, _r=runner: _r.session)
        with patch.object(C, "PhaseRunner", return_value=runner):
            res = CliRunner().invoke(cli.main, ["expand", "demo", "--yes"])
        assert res.exit_code == code, res.output
        assert ("Expand 完成" in res.output) == (code == 0)
