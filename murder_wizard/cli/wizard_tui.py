"""murder-wizard TUI - Terminal UI with Rich."""
import signal
import sys
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown

from murder_wizard.wizard.state_machine import MurderWizardState, Stage
from murder_wizard.wizard.session import SessionManager
from murder_wizard.llm.client import create_llm_adapter


console = Console()


def handle_interrupt(signum, frame):
    """Ctrl+C 处理：保存状态并退出"""
    console.print("\n[yellow]保存进度...[/yellow]")
    # 状态已在 run_init_wizard 中定期保存
    console.print("[green]已保存，下次可使用 resume 命令继续。[/green]")
    sys.exit(0)


def run_init_wizard(session: SessionManager, state: MurderWizardState, console: Console):
    """运行初始化向导"""
    signal.signal(signal.SIGINT, handle_interrupt)

    console.print(Panel.fit(
        "[bold cyan]murder-wizard[/bold cyan] - 剧本杀创作向导\n"
        "一个人 + AI，从灵感到商业化发布的完整创作系统",
        border_style="cyan"
    ))

    # 选择剧本类型
    if not state.story_type:
        console.print("\n[bold]第一步：选择剧本类型[/bold]")
        console.print("1. [red]情感本[/red] - 注重角色情感和故事体验")
        console.print("2. [yellow]机制本[/yellow] - 注重游戏机制和阵营对抗")
        console.print("3. [blue]推理本[/blue] - 注重解谜和线索推理")

        choice = Prompt.ask(
            "\n请选择剧本类型",
            choices=["1", "2", "3"],
            default="2"
        )
        type_map = {"1": "emotion", "2": "mechanic", "3": "puzzle"}
        state.story_type = type_map[choice]

    # 收集基本信息
    console.print(f"\n[bold]当前类型：{state.story_type}[/bold]")

    # 时代背景
    era = Prompt.ask("\n时代背景（默认：现代）", default="现代")
    setting = Prompt.ask("故事背景简介")

    # 核心冲突
    conflict = Prompt.ask("核心冲突（主线矛盾）")

    # 阵营（如果是机制本）
    factions = ""
    if state.story_type == "mechanic":
        factions = Prompt.ask("阵营设置（如：正派/反派/中立）", default="待定")

    # 游戏目标
    goal = Prompt.ask("游戏目标（玩家需要达成什么）")

    # 保存初始状态
    session.save(state)

    # 生成大纲
    console.print("\n[cyan]正在生成大纲...[/cyan]")

    prompt = f"""作为一个剧本杀作家，请为以下设定生成详细大纲：

类型：{state.story_type}
时代：{era}
背景：{setting}
核心冲突：{conflict}
{f"阵营：{factions}" if factions else ""}
游戏目标：{goal}

请生成：
1. 故事梗概（200字）
2. 六位角色设定简述
3. 核心事件线（3-5个关键事件）
4. 结局走向建议

格式：Markdown
"""

    try:
        llm = create_llm_adapter("claude")
        response = llm.complete(prompt, system="你是一个专业的剧本杀作家，擅长创作有趣、平衡的剧本杀游戏。")
        state.outline = response.content
        session.log_cost("outline_generation", response.tokens_used, response.cost)
        session.save(state)

        console.print(Panel.fit(
            "[green]大纲生成完成！[/green]\n\n" +
            response.content[:500] + "...",
            title="大纲预览"
        ))

        # 保存大纲到文件
        outline_file = session.project_path / "outline.md"
        outline_file.write_text(response.content, encoding="utf-8")
        console.print(f"[green]大纲已保存到：{outline_file}[/green]")

    except Exception as e:
        console.print(f"[red]生成失败：{e}[/red]")
        console.print("[yellow]请检查 API 密钥配置或网络连接[/yellow]")
        return

    console.print("\n[bold green]初始化完成！[/bold green]")
    console.print("下一步：")
    console.print("  - [cyan]murder-wizard phase <项目名> 1[/cyan] - 运行阶段1（机制设计）")
    console.print("  - [cyan]murder-wizard status <项目名>[/cyan] - 查看项目状态")
