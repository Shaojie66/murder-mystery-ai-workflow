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
from murder_wizard.prompts.loader import PromptLoader


console = Console()


def handle_interrupt(signum, frame):
    """Ctrl+C 处理：保存状态并退出"""
    console.print("\n[yellow]保存进度...[/yellow]")
    console.print("[green]已保存，下次可使用 resume 命令继续。[/green]")
    sys.exit(0)


def _ask_question(console: Console, q_num: str, title: str, hint: str = "", multiline: bool = False) -> str:
    """向用户提问，支持多行输入。返回用户输入的字符串。"""
    console.print(f"\n[bold cyan]Q{q_num} — {title}[/bold cyan]")
    if hint:
        console.print(f"[dim]{hint}[/dim]")
    if multiline:
        console.print("[dim](输入空行结束多行输入)[/dim]")
        lines = []
        while True:
            line = Prompt.ask("", default="")
            if line == "":
                break
            lines.append(line)
        return "\n".join(lines)
    else:
        return Prompt.ask("[bold]请回答[/bold]", default="")


def _compile_brief(
    q1_type: str,
    q1_moment: str,
    q2_equation: str,
    q3_constraint: str,
    q4_emotions: str,
    q5_diff: str,
    q5_moment: str,
    q6_done: str,
    q6_priority: str,
    era: str,
    mode_label: str,
    story_type_label: str,
) -> str:
    """将问卷答案编译为 brief.md 内容。"""
    return f"""# 剧本杀创作简报

> 由 murder-wizard init 向导生成
> 创作模式：{mode_label}
> 剧本类型：{story_type_label}

---

## 核心定位

- **题材**：{q1_type}
- **核心瞬间**：{q1_moment}
- **时代背景**：{era}

## 核心方程式

{q2_equation}

---

## 人物约束

{q3_constraint}

---

## 戏剧内核

**玩家记住的三个情绪时刻：**
{q4_emotions}

---

## 独特记忆点

- **差异化**：{q5_diff}
- **脑子里一直有的画面**：{q5_moment}

---

## 质量标准

- **"做完"的定义**：{q6_done}
- **优先做的事**：{q6_priority}

---

*本文件是所有后续 prompt 的默认上下文，每生成一个内容块前都应引用。*
"""


def run_init_wizard(session: SessionManager, state: MurderWizardState, console: Console):
    """运行初始化向导 — YC Office Hours 风格创意问卷"""
    signal.signal(signal.SIGINT, handle_interrupt)

    console.print(Panel.fit(
        "[bold cyan]murder-wizard[/bold cyan] - 剧本杀创作向导\n"
        "一个人 + AI，从灵感到商业化发布的完整创作系统",
        border_style="cyan"
    ))

    # ─── 创作模式 ───────────────────────────────────────────────────
    console.print("\n[bold]第一步：选择创作模式[/bold]")
    console.print("1. [green]原型模式（推荐）[/green] - 先做一个2人小本，快速验证")
    console.print("2. [cyan]完整模式[/cyan] - 6人完整剧本，周期更长")

    mode_choice = Prompt.ask(
        "\n请选择创作模式",
        choices=["1", "2"],
        default="1"
    )
    state.is_prototype = (mode_choice == "1")
    mode_label = "原型模式" if state.is_prototype else "完整模式"

    # ─── 剧本类型 ───────────────────────────────────────────────────
    console.print("\n[bold]第二步：选择剧本类型[/bold]")
    console.print("1. [red]情感本[/red] - 注重角色情感和故事体验")
    console.print("2. [yellow]机制本[/yellow] - 注重游戏机制和阵营对抗")
    console.print("3. [blue]推理本[/blue] - 注重解谜和线索推理")

    type_choice = Prompt.ask(
        "\n请选择剧本类型",
        choices=["1", "2", "3"],
        default="2"
    )
    type_map = {"1": "emotion", "2": "mechanic", "3": "puzzle"}
    type_label_map = {"1": "情感本", "2": "机制本", "3": "推理本"}
    state.story_type = type_map[type_choice]
    story_type_label = type_label_map[type_choice]

    console.print(f"\n[bold]当前类型：{story_type_label}，{mode_label}[/bold]")

    # ─── 时代背景 ───────────────────────────────────────────────────
    era = Prompt.ask("\n时代背景（默认：现代）", default="现代")

    # ─── 6 个创意问题 ─────────────────────────────────────────────
    console.print("\n[bold cyan]━━━━━━━━━━ 创意问卷 ━━━━━━━━━━[/bold cyan]")
    console.print("[dim]参考 YC Office Hours 六问法，帮助 AI 理解你真正想做什么样的剧本[/dim]")
    console.print("[dim]可以直接回答，也可以让 AI 追问帮你厘清[/dim]\n")

    # Q1 — 题材定位
    q1_type = _ask_question(
        console, "1", "题材定位",
        hint="不是'6人本''硬核推理'这种泛泛分类。\n"
             "是：一个真实历史切片 / 一种极致情感体验 / 一个思想实验？\n"
             "或者别的完全不同的东西？",
    )
    if q1_type:
        follow_up = Confirm.ask(
            "[cyan]AI 追问：[/cyan] 这个类型最打动你的一个瞬间是什么？\n"
            "（不是主题，是某个具体的戏剧性时刻）",
            default=False
        )
        if follow_up:
            q1_moment = _ask_question(console, "1b", "核心瞬间", multiline=True)
        else:
            q1_moment = Prompt.ask("简短描述这个瞬间（1-2句话）", default="")
    else:
        q1_moment = ""

    # Q2 — 核心冲突
    console.print()
    q2_equation = _ask_question(
        console, "2", "核心冲突",
        hint="冲突不是'有人死了'——那是事件。\n"
             "冲突是两个（或以上）不可调和的价值之间的碰撞。\n"
             "写出这个剧本的核心方程式，类似：X vs Y = ？",
        multiline=True,
    )

    # Q3 — 人物约束
    console.print()
    q3_constraint = _ask_question(
        console, "3", "人物原型",
        hint="这6个人为什么必须被困在一起？\n"
             "不是'他们都是嫌疑人'——那只是机制。\n"
             "是什么共同的历史/秘密/处境把他们绑在一起？\n"
             "每个人进来之前各自处于什么状态？",
        multiline=True,
    )
    follow_up = Confirm.ask(
        "[cyan]追问：[/cyan] 如果只能保留一个角色的戏份，你会选谁？",
        default=False
    )
    if follow_up:
        q3_extra = _ask_question(console, "3b", "保留谁", hint="为什么？")
        q3_constraint = q3_constraint + f"\n\n**只保留一个角色**：{q3_extra}"
    else:
        q3_constraint = q3_constraint

    # Q4 — 情感设计
    console.print()
    q4_emotions = _ask_question(
        console, "4", "情感设计",
        hint="玩家玩完这个剧本后，最可能记住的三样东西是什么？\n"
             "（不是学习到的知识，是感受到的情绪）\n"
             "哪个时刻他们会背脊发凉？哪个选择他们会纠结很久？\n"
             "哪个结局他们会沉默很久？",
        multiline=True,
    )
    follow_up = Confirm.ask(
        "[cyan]追问：[/cyan] 你希望玩家走出房间的时候是如释重负还是意犹未尽？",
        default=False
    )
    if follow_up:
        q4_extra = Prompt.ask("如释重负 / 意犹未尽 / 其他", default="意犹未尽")
        q4_emotions = q4_emotions + f"\n\n**离场感受**：{q4_extra}"

    # Q5 — 差异化
    console.print()
    q5_diff = _ask_question(
        console, "5", "差异化",
        hint="这个剧本和市面上同类型的相比，独特在哪？\n"
             "现有剧本很少碰的题材/视角？\n"
             "只有这个故事才有的核心机制？\n"
             "某个让人'WOW'的叙事技巧？",
        multiline=True,
    )
    follow_up = Confirm.ask(
        "[cyan]追问：[/cyan] 你有没有一个画面是脑子里一直有的？",
        default=False
    )
    if follow_up:
        q5_moment = _ask_question(console, "5b", "核心画面", multiline=True)
    else:
        q5_moment = ""

    # Q6 — 上线标准
    console.print()
    q6_done = _ask_question(
        console, "6", "上线标准",
        hint="你怎么判断这个剧本'做完了'？\n"
             "是完成某个核心机制就算？\n"
             "还是必须6个角色都有完整结局？\n"
             "还是必须经过真实用户测试才行？",
    )
    follow_up = Confirm.ask(
        "[cyan]追问：[/cyan] 如果只能做一件事（只写大纲/只做1个角色/只设计机制），你会选哪个？",
        default=False
    )
    if follow_up:
        q6_priority = Prompt.ask("优先做的事", default="")
    else:
        q6_priority = ""

    # ─── 编译 brief.md ────────────────────────────────────────────
    brief_content = _compile_brief(
        q1_type=q1_type,
        q1_moment=q1_moment,
        q2_equation=q2_equation,
        q3_constraint=q3_constraint,
        q4_emotions=q4_emotions,
        q5_diff=q5_diff,
        q5_moment=q5_moment,
        q6_done=q6_done,
        q6_priority=q6_priority,
        era=era,
        mode_label=mode_label,
        story_type_label=story_type_label,
    )

    brief_file = session.project_path / "brief.md"
    brief_file.write_text(brief_content, encoding="utf-8")
    console.print(f"\n[green]创意简报已保存到：{brief_file}[/green]")

    # 保存初始状态
    state.outline = ""  # 尚未生成
    session.save(state)

    # ─── AI 辅助生成大纲 ──────────────────────────────────────────
    if Confirm.ask("\n[cyan]需要 AI 帮你生成大纲吗？[/cyan]（推荐）", default=True):
        console.print("\n[cyan]正在生成大纲...[/cyan]")

        loader = PromptLoader()
        outline_prompt = f"""基于以下创意简报，为这个剧本杀生成详细大纲：

{brief_content}

请生成：
1. 故事梗概（200字）
2. 六位角色设定简述（原型模式先做2人）
3. 核心事件线（3-5个关键事件）
4. 结局走向建议

格式：Markdown，包含表格（如事件表、角色技能表）"""

        try:
            llm = create_llm_adapter("claude")
            response = llm.complete(
                outline_prompt,
                system=loader.system_outline_generator(),
            )
            state.outline = response.content
            session.log_cost("outline_generation", response.tokens_used, response.cost)
            session.save(state)

            console.print(Panel.fit(
                "[green]大纲生成完成！[/green]\n\n" +
                response.content[:500] + "...",
                title="大纲预览"
            ))

            outline_file = session.project_path / "outline.md"
            outline_file.write_text(response.content, encoding="utf-8")
            console.print(f"[green]大纲已保存到：{outline_file}[/green]")

        except Exception as e:
            console.print(f"[yellow]大纲生成失败：{e}[/yellow]")
            console.print("[yellow]可以稍后运行 murder-wizard phase <项目名> 1 生成大纲[/yellow]")

    # ─── 完成 ──────────────────────────────────────────────────────
    console.print("\n[bold green]初始化完成！[/bold green]")
    console.print(f"  创意简报：{brief_file}")
    if state.outline:
        console.print(f"  大纲：{session.project_path / 'outline.md'}")
    console.print("\n下一步：")
    console.print("  - [cyan]murder-wizard phase <项目名> 1[/cyan] - 运行阶段1（机制设计）")
    console.print("  - [cyan]murder-wizard status <项目名>[/cyan] - 查看项目状态")
