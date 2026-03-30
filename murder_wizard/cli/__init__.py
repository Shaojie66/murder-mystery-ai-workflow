"""murder-wizard CLI entry point."""
import click
from rich.console import Console

from murder_wizard.wizard.state_machine import MurderWizardState
from murder_wizard.wizard.session import SessionManager

console = Console()


@click.group()
@click.version_option(version="0.5.0")
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


@main.command()
@click.argument("project_name")
@click.option("--clear", is_flag=True, help="清空缓存")
def cache(project_name: str, clear: bool):
    """查看或管理 LLM 缓存

    缓存基于 prompt+system+operation 的 hash，重复调用同一阶段时直接返回缓存结果。
    """
    from murder_wizard.llm.cache import LLMCache
    from murder_wizard.wizard.session import SessionManager

    session = SessionManager(project_name)
    cache = LLMCache(session.project_path)

    if clear:
        cache.clear()
        console.print("[green]缓存已清空[/green]")
        return

    stats = cache.stats()
    console.print(f"[cyan]缓存条目：{stats['entries']}[/cyan]")
    console.print(f"[cyan]缓存大小：{stats['size_bytes']} bytes[/cyan]")

    if stats["entries"] > 0:
        console.print("\n[yellow]使用 --clear 清空缓存[/yellow]")


@main.command()
@click.argument("project_name")
def audit(project_name: str):
    """完整穿帮审计：深度分析角色剧本、信息矩阵、机制设计

    基于信息矩阵逐格核对，检查：
    - 角色是否提及当时不知道的信息（P1致命穿帮）
    - 机制漏洞和平衡性问题
    - 结局逻辑和唯一性

    生成 audit_report.md，建议在上线前独立运行。

    示例：
      murder-wizard audit myproject
    """
    from murder_wizard.cli.commands import run_audit
    session = SessionManager(project_name)
    run_audit(session, console)


if __name__ == "__main__":
    main()
