"""murder-wizard CLI commands implementation."""
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from murder_wizard.wizard.session import SessionManager
from murder_wizard.wizard.state_machine import Stage


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
        (Stage.STAGE_1_MECHANISM, "阶段1：机制设计", "outline.md"),
        (Stage.STAGE_2_SCRIPT, "阶段2：剧本创作", "characters.md, 六本初稿"),
        (Stage.STAGE_3_VISUAL, "阶段3：视觉物料", "角色立绘, 封面, 线索卡"),
        (Stage.STAGE_4_TEST, "阶段4：用户测试", "内测反馈"),
        (Stage.STAGE_5_COMMERCIAL, "阶段5：商业化", "成本核算表"),
        (Stage.STAGE_6_PRINT, "阶段6：印刷生产", "PDF排版"),
        (Stage.STAGE_7_PROMO, "阶段7：宣发内容", "文案/图文"),
        (Stage.STAGE_8_COMMUNITY, "阶段8：社区运营", "社群"),
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
        artifact_files = artifacts.split(", ")
        all_exist = all((session.project_path / f).exists() for f in artifact_files if f)

        table.add_row(name, status, artifacts if all_exist else f"[dim]{artifacts}[/dim]")

    console.print(table)

    # 显示消耗
    total_cost = session.get_total_cost()
    if total_cost > 0:
        console.print(f"\n[dim]API 总消耗：约 ¥{total_cost:.2f}[/dim]")

    # 显示当前阶段
    if state.outline:
        console.print(f"\n[cyan]当前阶段：{current.value}[/cyan]")


def run_phase(session: SessionManager, stage: int, console: Console):
    """运行指定阶段"""
    state = session.load()

    if state is None:
        console.print("[red]未找到项目状态[/red]")
        return

    if stage < 1 or stage > 8:
        console.print("[red]阶段必须是 1-8[/red]")
        return

    console.print(f"[cyan]运行阶段 {stage}...[/cyan]")

    # TODO: 实现各阶段的完整逻辑
    # 这里先占位，后续实现

    if stage == 1:
        _run_stage_1_mechanism(session, state, console)
    elif stage == 2:
        _run_stage_2_script(session, state, console)
    elif stage == 3:
        _run_stage_3_visual(session, state, console)
    else:
        console.print(f"[yellow]阶段 {stage} 尚未实现[/yellow]")
        console.print("预计在后续版本中支持")


def _run_stage_1_mechanism(session, state, console):
    """阶段1：机制设计"""
    console.print("[cyan]阶段1：机制设计[/cyan]")
    # TODO: 实现完整的机制设计流程
    console.print("[yellow]完整实现待添加[/yellow]")


def _run_stage_2_script(session, state, console):
    """阶段2：剧本创作"""
    console.print("[cyan]阶段2：剧本创作[/cyan]")
    # TODO: 实现完整的剧本创作流程
    console.print("[yellow]完整实现待添加[/yellow]")


def _run_stage_3_visual(session, state, console):
    """阶段3：视觉物料"""
    console.print("[cyan]阶段3：视觉物料[/cyan]")
    # TODO: 实现完整的视觉物料生成流程
    console.print("[yellow]完整实现待添加[/yellow]")


def run_expand(session: SessionManager, console: Console):
    """expand 操作：将原型扩写为完整版本"""
    state = session.load()

    if state is None:
        console.print("[red]未找到项目状态[/red]")
        return

    if not state.is_prototype:
        console.print("[yellow]当前不是原型模式，无需 expand[/yellow]")
        return

    console.print("[cyan]正在 expand 原型为完整版本...[/cyan]")
    # TODO: 实现 expand 逻辑
    console.print("[yellow]expand 实现待添加[/yellow]")


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

    # 继续当前阶段
    show_status(session, console)
