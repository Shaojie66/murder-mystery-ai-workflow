"""murder-wizard CLI commands implementation."""
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from murder_wizard.wizard.session import SessionManager
from murder_wizard.wizard.state_machine import Stage
from murder_wizard.cli.phase_runner import PhaseRunner


def show_status(session: SessionManager, console: Console):
    """显示项目状态"""
    state = session.load()

    if state is None:
        console.print("[red]未找到项目状态[/red]")
        console.print("请先运行：murder-wizard init <项目名>")
        return

    # 构建状态表格
    table = Table(title=f"项目：{state.project_name}")
    table.add_column("阶段", style="cyan")
    table.add_column("状态", style="green")
    table.add_column("产物", style="yellow")

    stages = [
        (Stage.STAGE_1_MECHANISM, "阶段1：机制设计", ["mechanism.md"]),
        (Stage.STAGE_2_SCRIPT, "阶段2：剧本创作", ["characters.md", "information_matrix.md"]),
        (Stage.STAGE_3_VISUAL, "阶段3：视觉物料", ["image-prompts.md"]),
        (Stage.STAGE_4_TEST, "阶段4：用户测试", []),
        (Stage.STAGE_5_COMMERCIAL, "阶段5：商业化", []),
        (Stage.STAGE_6_PRINT, "阶段6：印刷生产", []),
        (Stage.STAGE_7_PROMO, "阶段7：宣发内容", []),
        (Stage.STAGE_8_COMMUNITY, "阶段8：社区运营", []),
    ]

    current = state.current_stage

    for stage_enum, name, artifacts in stages:
        if current.value > stage_enum.value:
            status = "[green]✓ 已完成[/green]"
        elif current.value == stage_enum.value:
            status = "[yellow]→ 进行中[/yellow]"
        else:
            status = "[dim]○ 待开始[/dim]"

        # 检查产物文件是否存在
        missing = [f for f in artifacts if not (session.project_path / f).exists()]
        artifact_str = ", ".join(artifacts) if artifacts else "—"
        if missing:
            artifact_str = f"[dim]{artifact_str}[/dim] [red]缺: {', '.join(missing)}[/red]"

        table.add_row(name, status, artifact_str)

    console.print(table)

    # 原型模式标记
    if state.is_prototype:
        console.print("\n[yellow]⚠ 原型模式 - 需运行 expand 扩写为完整版本[/yellow]")

    # 显示消耗
    total_cost = session.get_total_cost()
    if total_cost > 0:
        console.print(f"\n[dim]API 总消耗：约 ¥{total_cost:.2f}[/dim]")


def run_phase(session: SessionManager, stage: int, console: Console):
    """运行指定阶段"""
    state = session.load()

    if state is None:
        console.print("[red]未找到项目状态[/red]")
        return

    if stage < 1 or stage > 8:
        console.print("[red]阶段必须是 1-8[/red]")
        return

    console.print(Panel.fit(f"[bold cyan]murder-wizard[/bold cyan] - 阶段 {stage}", border_style="cyan"))

    try:
        runner = PhaseRunner(session, state, console)

        if stage == 1:
            runner.run_stage_1()
        elif stage == 2:
            runner.run_stage_2()
        elif stage == 3:
            runner.run_stage_3()
        elif stage == 4:
            _run_stage_4(session, state, console)
        elif stage == 5:
            _run_stage_5(session, state, console)
        elif stage == 6:
            _run_stage_6(session, state, console)
        elif stage == 7:
            _run_stage_7(session, state, console)
        elif stage == 8:
            _run_stage_8(session, state, console)
        else:
            console.print(f"[yellow]阶段 {stage} 尚未实现[/yellow]")

        console.print("\n[bold green]阶段完成！[/bold green]")
        console.print(f"运行 [cyan]murder-wizard status {state.project_name}[/cyan] 查看状态")

    except Exception as e:
        console.print(f"[red]阶段执行失败：{e}[/red]")


def _run_stage_4(session, state, console):
    """阶段4：用户测试"""
    console.print("[yellow]阶段4（用户测试）尚未实现[/yellow]")
    console.print("预计在第二批中支持")


def _run_stage_5(session, state, console):
    """阶段5：商业化"""
    console.print("[yellow]阶段5（商业化）尚未实现[/yellow]")
    console.print("预计在第二批中支持")


def _run_stage_6(session, state, console):
    """阶段6：印刷生产"""
    console.print("[yellow]阶段6（印刷生产）尚未实现[/yellow]")
    console.print("预计在第二批中支持")


def _run_stage_7(session, state, console):
    """阶段7：宣发内容"""
    console.print("[yellow]阶段7（宣发内容）尚未实现[/yellow]")
    console.print("预计在第三批中支持")


def _run_stage_8(session, state, console):
    """阶段8：社区运营"""
    console.print("[yellow]阶段8（社区运营）尚未实现[/yellow]")
    console.print("预计在第三批中支持")


def run_expand(session: SessionManager, console: Console):
    """expand 操作：将原型扩写为完整版本"""
    state = session.load()

    if state is None:
        console.print("[red]未找到项目状态[/red]")
        return

    if not state.is_prototype:
        console.print("[yellow]当前不是原型模式，无需 expand[/yellow]")
        return

    console.print(Panel.fit("[bold cyan]murder-wizard[/bold cyan] - Expand 原型扩写", border_style="cyan"))

    try:
        runner = PhaseRunner(session, state, console)
        runner.run_expand()
        console.print("\n[bold green]Expand 完成！[/bold green]")

    except Exception as e:
        console.print(f"[red]Expand 失败：{e}[/red]")


def resume_project(session: SessionManager, console: Console):
    """从中断处继续"""
    state = session.load()

    if state is None:
        # 尝试从文件恢复
        state = session.recover_from_files()
        if state is None:
            console.print("[red]无法恢复项目状态[/red]")
            console.print("请先运行：murder-wizard init <项目名>")
            return
        console.print("[yellow]从输出文件恢复项目状态[/yellow]")

    console.print(f"[green]已恢复：{state.project_name}[/green]")
    console.print(f"当前阶段：{state.current_stage.value}")

    if state.is_prototype:
        console.print("[yellow]原型模式 - 可运行 expand[/yellow]")

    # 继续当前阶段
    show_status(session, console)
