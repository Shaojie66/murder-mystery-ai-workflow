"""Tests for CLI commands."""
from rich.console import Console

from murder_wizard.cli.commands import show_status
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
