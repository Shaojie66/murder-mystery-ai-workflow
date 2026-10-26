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
        (Stage.STAGE_4_TEST, "阶段4：用户测试", ["test_guide.md"]),
        (Stage.STAGE_5_COMMERCIAL, "阶段5：商业化", ["commercial.md"]),
        (Stage.STAGE_6_PRINT, "阶段6：印刷生产", ["script.pdf"]),
        (Stage.STAGE_7_PROMO, "阶段7：宣发内容", ["promo_content.md"]),
        (Stage.STAGE_8_COMMUNITY, "阶段8：社区运营", ["community_plan.md"]),
    ]

    current = state.current_stage

    for stage_enum, name, artifacts in stages:
        if current > stage_enum:
            status = "[green]✓ 已完成[/green]"
        elif current == stage_enum:
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


def run_phase(session: SessionManager, stage: int, console: Console, analyze: bool = False) -> bool:
    """运行指定阶段

    Args:
        session: 会话管理器
        stage: 阶段编号 (1-8)
        console: Rich 控制台
        analyze: 是否为分析模式（阶段4）

    Returns:
        阶段是否真正成功（调用方据此决定退出码）
    """
    state = session.load()

    if state is None:
        console.print("[red]未找到项目状态[/red]")
        return False

    if stage < 1 or stage > 8:
        console.print("[red]阶段必须是 1-8[/red]")
        return False

    console.print(Panel.fit(f"[bold cyan]murder-wizard[/bold cyan] - 阶段 {stage}", border_style="cyan"))

    try:
        runner = PhaseRunner(session, state, console)

        if stage == 1:
            ok = runner.run_stage_1()
        elif stage == 2:
            ok = runner.run_stage_2()
        elif stage == 3:
            ok = runner.run_stage_3()
        elif stage == 4:
            if analyze:
                ok = _run_stage_4_analyze(session, state, console, runner)
            else:
                ok = runner.run_stage_4()
        elif stage == 5:
            ok = runner.run_stage_5()
        elif stage == 6:
            ok = runner.run_stage_6()
        elif stage == 7:
            ok = runner.run_stage_7()
        elif stage == 8:
            ok = runner.run_stage_8()
        else:
            console.print(f"[yellow]阶段 {stage} 尚未实现[/yellow]")
            ok = False

        if ok:
            console.print("\n[bold green]阶段完成！[/bold green]")
            console.print(f"运行 [cyan]murder-wizard status {state.project_name}[/cyan] 查看状态")
        else:
            console.print("\n[bold red]阶段失败，请检查上方错误信息[/bold red]")
        return bool(ok)

    except Exception as e:
        console.print(f"[red]阶段执行失败：{e}[/red]")
        return False


def _run_stage_4_analyze(session, state, console, runner: PhaseRunner) -> bool:
    """阶段4分析模式：分析用户反馈并生成迭代建议（逻辑在 PhaseRunner.run_stage_4_analyze）"""
    return runner.run_stage_4_analyze()


def _confirm_expand(console: Console):
    """交互确认回调：展示覆盖范围与新角色/新事件，默认「否」。"""
    from rich.markup import escape
    from rich.prompt import Confirm

    def confirm(plan) -> bool:
        console.print("\n[bold]候选已生成并通过结构校验。将要写入：[/bold]")
        for e in plan.entries:
            console.print(f"  {escape(e.relpath)} — {e.treatment}")
        console.print("新角色：" + escape("、".join(f"{k} {v}" for k, v in plan.new_character_names.items())))
        for eid, title, summary in plan.new_events:
            console.print(f"  {eid}：{escape(title)} — {escape(summary)}")
        try:
            return Confirm.ask("确认覆盖当前作品？（会先备份）", default=False)
        except (EOFError, KeyboardInterrupt):
            return False
    return confirm


def run_expand(session: SessionManager, console: Console, accept_overwrite: bool = False) -> bool:
    """expand 操作：将原型扩写为完整版本（作者确认后才覆盖；失败不改动作品）"""
    import sys

    state = session.load()

    if state is None:
        console.print("[red]未找到项目状态[/red]")
        return False

    if not state.is_prototype:
        console.print("[yellow]当前不是原型模式，无需 expand[/yellow]")
        return False

    if not accept_overwrite and not sys.stdin.isatty():
        console.print("[yellow]expand 会覆盖并重新生成多份作品文件，需作者确认：非交互运行请加 --yes。本次未调用模型。[/yellow]")
        return False

    console.print(Panel.fit("[bold cyan]murder-wizard[/bold cyan] - Expand 原型扩写", border_style="cyan"))

    try:
        runner = PhaseRunner(session, state, console)
        ok = runner.run_expand(confirm=None if accept_overwrite else _confirm_expand(console),
                               accept_overwrite=accept_overwrite)
        res = runner.last_expand_result
        status = res.status.value if res else "failed_internal"
        banner = {
            "applied": "[bold green]Expand 完成（已通过结构校验，尚未审计，建议运行 murder-wizard audit）[/bold green]",
            "declined": "[yellow]已放弃 expand，作品未改动[/yellow]",
            "refused": "[yellow]expand 未执行（前置条件不满足或缺少确认），作品未改动[/yellow]",
            "commit_restored": "[bold red]写入失败，已从备份恢复，原型保持可用[/bold red]",
            "commit_restore_incomplete": "[bold red]写入失败且恢复未完成，作品处于混合状态，请按上方 cp 命令从备份恢复[/bold red]",
            "changed_during_run": "[bold red]生成期间文件被修改，已放弃提交，作品未改动[/bold red]",
        }.get(status, "[bold red]Expand 失败，作品未改动，原型保持可用；请检查上方错误信息[/bold red]")
        console.print("\n" + banner)
        return ok

    except Exception as e:
        from rich.markup import escape
        console.print(f"[red]Expand 失败：{escape(str(e))}[/red]")
        return False


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
        session.save(state)  # 持久化恢复结果：否则下次仍会读到损坏/缺失的 session.json

    console.print(f"[green]已恢复：{state.project_name}[/green]")
    console.print(f"当前阶段：{state.current_stage.slug}")

    if state.is_prototype:
        console.print("[yellow]原型模式 - 可运行 expand[/yellow]")

    # 继续当前阶段
    show_status(session, console)


def _prompt_accept_fixes(console: Console, proposals) -> list:
    """交互式让作者选择要写入的补丁。空输入/EOF/Ctrl+C/异常一律视为全部不接受。"""
    from rich.markup import escape

    applicable = [p for p in proposals if p.applicable]
    console.print("\n[bold]审计给出了以下定点修复建议（默认不写入作品）：[/bold]")
    for p in applicable:
        console.print(f"[cyan]{p.fid}[/cyan] 关联 {'、'.join(p.issue_refs)} · {p.file} 第 {p.line} 行")
        console.print(f"  原文：{escape(p.matched[:400])}")
        console.print(f"  建议改为：{escape(p.replace[:400])}")
    console.print("[dim]完整内容见 audit_report.md。输入要应用的编号（如 F1,F3 或 all），直接回车表示都不接受。[/dim]")
    try:
        answer = input("应用哪些？> ").strip()
    except (EOFError, KeyboardInterrupt, Exception):
        answer = ""
    if not answer:
        console.print("[dim]未写入任何文件[/dim]")
        return []
    ids = [p.fid for p in applicable] if answer.lower() == "all" else [x.strip().upper() for x in answer.split(",") if x.strip()]
    known = {p.fid for p in applicable}
    for x in ids:
        if x not in known:
            console.print(f"[yellow]忽略未知或不可应用的编号：{escape(x)}[/yellow]")
    return [x for x in ids if x in known]


def run_audit(session: SessionManager, console: Console, force: bool = False, chooser="auto"):
    """完整穿帮审计：读取 a/b 本、DM 手册、结局、矩阵与机制，生成 audit_report.md。

    默认只读：不会改写作品。仅在交互终端里由作者显式选择，才会写入定点修复（先备份）。
    返回 AuditOutcome（status: passed / waived / blocked / incomplete）；状态缺失或初始化失败返回 None。

    Args:
        force: 已弃用，不再改变审计结论。
        chooser: "auto" 仅在交互终端提示；传 None 永不提示；传可调用对象用于测试。
    """
    import sys

    state = session.load()

    if state is None:
        console.print("[red]未找到项目状态[/red]")
        return None

    console.print(Panel.fit("[bold cyan]murder-wizard[/bold cyan] - 完整穿帮审计", border_style="cyan"))

    try:
        runner = PhaseRunner(session, state, console)
        if force:
            console.print("[yellow]--force 已弃用，不改变审计结论[/yellow]")
        outcome = runner.run_audit_checked(force=force)
        if outcome.proposals and any(p.applicable for p in outcome.proposals):
            if chooser == "auto":
                interactive = sys.stdin.isatty() and getattr(console, "is_terminal", False)
                chooser = _prompt_accept_fixes if interactive else None
            if chooser is not None:
                accepted = chooser(console, outcome.proposals)
                if accepted:
                    result = runner.apply_audit_fixes(outcome, accepted)
                    if result.error:
                        console.print(f"[red]修复未写入或已回滚：{result.error}[/red]")
                    else:
                        console.print(f"[green]已应用 {'、'.join(result.applied_ids)}，备份：{'、'.join(result.backups)}[/green]")
                        console.print("[yellow]审计结论不变；请重新运行 audit 验证修改后的文本。[/yellow]")
        return outcome
    except Exception as e:
        from rich.markup import escape
        console.print(f"[red]审计失败：{escape(str(e))}[/red]")
        return None
