"""murder-wizard CLI entry point."""
import click
from rich.console import Console

from murder_wizard.wizard.state_machine import MurderWizardState
from murder_wizard.wizard.session import SessionManager

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def main():
    """murder-wizard: 剧本杀创作向导"""
    pass


@main.command()
@click.argument("project_name")
@click.option("--type", "story_type", type=click.Choice(["emotion", "mechanic", "puzzle"]), default=None, help="剧本类型")
@click.option("--prototype/--full", "is_prototype", default=True, help="原型模式（默认开启，2人小本快速验证）")
def init(project_name: str, story_type: str, is_prototype: bool):
    """初始化新剧本杀项目

    原型模式（默认）：先生成2人版本，快速验证后 expand 扩写为完整6人版本
    """
    from murder_wizard.cli.wizard_tui import run_init_wizard
    session = SessionManager(project_name)
    state = MurderWizardState(
        story_type=story_type or "mechanic",
        project_name=project_name,
        is_prototype=is_prototype
    )
    run_init_wizard(session, state, console)


@main.command()
@click.argument("project_name")
def status(project_name: str):
    """查看项目状态"""
    from murder_wizard.cli.commands import show_status
    session = SessionManager(project_name)
    show_status(session, console)


@main.command()
@click.argument("project_name")
@click.argument("stage", type=int, nargs=1)
@click.option("--analyze", is_flag=True, help="分析反馈并生成迭代建议（阶段4）")
def phase(project_name: str, stage: int, analyze: bool):
    """运行指定阶段 (1-8)

    示例：
      murder-wizard phase myproject 4       # 生成测试指南
      murder-wizard phase myproject 4 --analyze  # 分析反馈
    """
    from murder_wizard.cli.commands import run_phase
    session = SessionManager(project_name)
    run_phase(session, stage, console, analyze=analyze)


@main.command()
@click.argument("project_name")
def expand(project_name: str):
    """将原型扩写为完整版本"""
    from murder_wizard.cli.commands import run_expand
    session = SessionManager(project_name)
    run_expand(session, console)


@main.command()
@click.argument("project_name")
def resume(project_name: str):
    """从上次中断处继续"""
    from murder_wizard.cli.commands import resume_project
    session = SessionManager(project_name)
    resume_project(session, console)


if __name__ == "__main__":
    main()
