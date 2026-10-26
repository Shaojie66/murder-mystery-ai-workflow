"""Phase runner - executes each stage's LLM workflow."""
import json
import os
import time
import signal
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from murder_wizard.wizard.session import SessionManager
from murder_wizard.wizard.state_machine import MurderWizardState, Stage
from murder_wizard.llm.client import create_llm_adapter, LLMResponse
from murder_wizard.llm.cache import LLMCache
from murder_wizard.prompts.loader import (
    EXAMPLE_PLACEHOLDER_MARK,
    PromptLoader,
    PromptRenderError,
    is_blank_text,
    is_example_placeholder_text,
)
from murder_wizard.wizard.schemas import CharacterMatrix
from murder_wizard.wizard.audit import (
    EDITABLE_FILES, MAX_ISSUES_PER_ROUND, ROUND_FILES, ROUND_NUMBER, ROUND_TITLE, ROUNDS,
    ApplyResult, AuditMaterials, AuditOutcome, AuditParseError, AuditStatus, WaiverFile,
    apply_fixes as apply_audit_patches, apply_waivers, assign_refs, fix_contract, hint_lines,
    load_waivers, output_contract, parse_fix_output, parse_round_output, render_report,
    run_static_checks,
)
from murder_wizard.wizard.truth_files import (
    MatrixContractError,
    TruthFileManager,
    validate_generated_matrix,
)


# PhaseRunner._extract_json_from_response 的工作量上限（字符）：预算 = BASE + PER_CHAR * 回复长度。
# 每次失败的尝试至少记 MIN_ATTEMPT_COST（失败再便宜也限制尝试次数），RecursionError 按 RECURSION_COST 记。
_EXTRACT_BUDGET_BASE = 2_000_000
_EXTRACT_BUDGET_PER_CHAR = 16
_EXTRACT_MIN_ATTEMPT_COST = 2048
_EXTRACT_RECURSION_COST = 8192


class PhaseRunner:
    """阶段执行器"""

    STAGE_2_REQUIRED_ARTIFACTS = (
        "information_matrix.md",
        "background.md",
        "characters.md",
        "scripts_b.md",
        "dm_manual.md",
        "endings.md",
    )

    def __init__(self, session: SessionManager, state: MurderWizardState, console: Console):
        self.session = session
        self.state = state
        self.console = console
        self.llm = None
        self._cache = LLMCache(session.project_path)
        self._loader = PromptLoader()
        self._setup_llm()

    def _setup_llm(self):
        """初始化 LLM 适配器

        支持通过环境变量配置：
        - LLM_PROVIDER: claude / openai / ollama（默认 claude）
        - OLLAMA_BASE_URL: Ollama 服务地址（默认 http://localhost:11434/v1）
        - OLLAMA_MODEL: Ollama 模型名（默认 llama3）
        """
        try:
            provider = os.environ.get("LLM_PROVIDER", "claude")
            self.llm = create_llm_adapter(provider)
        except Exception as e:
            self.console.print(f"[red]LLM 初始化失败：{e}[/red]")
            raise

    def _call_llm(self, prompt: str, system: str = "", operation: str = "llm_call") -> LLMResponse:
        """调用 LLM，带缓存、重试和成本记录"""
        # 缓存查找
        cached = self._cache.get(operation, prompt, system, self.llm.model)
        if cached is not None:
            self.console.print(f"[dim]缓存命中：{operation}（节省 ¥{cached.cost:.4f}）[/dim]")
            self.session.log_cost(operation + "_cache_hit", 0, 0)
            return cached

        try:
            response = self.llm.complete(prompt, system=system)
            # 写入缓存
            self._cache.set(operation, prompt, system, self.llm.model, response)
            self.session.log_cost(operation, response.tokens_used, response.cost)
            return response
        except Exception as e:
            self.console.print(f"[red]LLM 调用失败：{e}[/red]")
            raise

    def run_stage_1(self) -> bool:
        """阶段1：类型化设计 — Q1验证 → Q2设计 → Q3验证 三步 pipeline

        原型模式：只生成3条核心事件（而非5-7条）
        根据 story_type 自动选择对应的设计模板和系统 prompt。
        """
        story_type = self.state.story_type or "mechanic"
        type_labels = {
            "emotion": "情感设计",
            "reasoning": "推理设计",
            "fun": "欢乐设计",
            "horror": "恐怖设计",
            "mechanic": "机制设计",
        }
        type_label = type_labels.get(story_type, "机制设计")
        self.console.print(f"[cyan]阶段1：{type_label}[/cyan]")

        # 检查前置条件
        if not self.state.outline:
            self.console.print("[red]缺少大纲，请先运行 init[/red]")
            return False

        # 检查是否已完成
        if (self.session.project_path / "mechanism.md").exists():
            self.console.print("[green]阶段1已完成，跳过[/green]")
            return True

        is_prototype = self.state.is_prototype
        event_count = 3 if is_prototype else 7
        char_count = 2 if is_prototype else 6
        system = self._loader.system_stage1_designer(story_type)
        total_cost = 0.0

        try:
            # ── Q1：概念/情感/欢乐/恐怖定位验证 ────────────────────────
            self.console.print("[cyan]Q1：概念验证...[/cyan]")
            q1_vars = {
                "brief_content": self.state.outline or "",
                "story_type": story_type,
                "is_prototype": is_prototype,
                "char_count": char_count,
                "event_count": event_count,
            }
            q1_prompt = self._loader.stage1_q1_validation(**q1_vars)
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=self.console) as progress:
                task = progress.add_task("Q1 概念验证...", total=None)
                q1_response = self._call_llm(q1_prompt, system, "stage_1_q1_validation")
            total_cost += q1_response.cost
            q1_file = self.session.project_path / "stage1_q1_validation.md"
            q1_file.write_text(q1_response.content, encoding="utf-8")
            self.console.print(f"[green]Q1 完成（{len(q1_response.content)} chars）[/green]")

            # ── Q2：核心机制/情感/角色设计 ─────────────────────────────
            self.console.print(f"[cyan]Q2：核心{type_label}...[/cyan]")
            q2_vars = {
                "brief_content": self.state.outline or "",
                "story_type": story_type,
                "is_prototype": is_prototype,
                "char_count": char_count,
                "event_count": event_count,
                "q1_result": q1_response.content,  # Q1 结果注入 Q2
            }
            q2_prompt = self._loader.stage1_q2_design(**q2_vars)
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=self.console) as progress:
                task = progress.add_task(f"Q2 {type_label}...", total=None)
                q2_response = self._call_llm(q2_prompt, system, "stage_1_mechanism")
            total_cost += q2_response.cost

            # ── Q3：平衡性/一致性验证 ──────────────────────────────────
            self.console.print("[cyan]Q3：平衡性验证...[/cyan]")
            q3_vars = {
                "brief_content": self.state.outline or "",
                "story_type": story_type,
                "is_prototype": is_prototype,
                "char_count": char_count,
                "event_count": event_count,
                "mechanism_content": q2_response.content,  # Q2 结果注入 Q3
            }
            q3_prompt = self._loader.stage1_q3_validation(**q3_vars)
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=self.console) as progress:
                task = progress.add_task("Q3 平衡性验证...", total=None)
                q3_response = self._call_llm(q3_prompt, system, "stage_1_q3_validation")
            total_cost += q3_response.cost
            q3_file = self.session.project_path / "stage1_q3_validation.md"
            q3_file.write_text(q3_response.content, encoding="utf-8")
            self.console.print(f"[green]Q3 完成（{len(q3_response.content)} chars）[/green]")

            # ── 保存产物：Q2 输出作为 mechanism.md ───────────────────
            mechanism_file = self.session.project_path / "mechanism.md"
            mechanism_file.write_text(q2_response.content, encoding="utf-8")

            # 保存完整记录（Q1+Q2+Q3）
            full_record = f"# {type_label} — 完整设计记录\n\n## Q1 概念验证\n\n{q1_response.content}\n\n---\n\n## Q2 核心设计\n\n{q2_response.content}\n\n---\n\n## Q3 平衡性验证\n\n{q3_response.content}\n"
            full_file = self.session.project_path / "stage1_full_design.md"
            full_file.write_text(full_record, encoding="utf-8")

            self.state.current_stage = Stage.STAGE_1_MECHANISM
            self.session.save(self.state)

            self.console.print(f"[green]阶段1全部完成！总消耗：${total_cost:.4f}[/green]")
            self.console.print(f"[green]核心设计：{mechanism_file}[/green]")
            self.console.print(f"[green]完整记录：{full_file}[/green]")
            self._show_cost_warning(total_cost)
            return True

        except Exception as e:
            self.console.print(f"[red]阶段1失败：{e}[/red]")
            return False

    def run_stage_2(self) -> bool:
        """阶段2：剧本创作 — 完整 Q1-Q6  pipeline

        Q1: 信息矩阵（JSON + Markdown）
        Q2: 角色背景设定
        Q3: a本（阅读本）
        Q4: b本（线索本 + 线索卡）
        Q5: DM 手册
        Q6: 结局扩展

        原型模式：2角色3事件；完整模式：6角色7事件
        """
        self.console.print("[cyan]阶段2：剧本创作（完整 pipeline）[/cyan]")

        if not (self.session.project_path / "mechanism.md").exists():
            self.console.print("[red]请先完成阶段1[/red]")
            return False

        existing, missing = self._stage_2_artifact_status()

        if not missing:
            self.console.print("[green]阶段2已完成，跳过[/green]")
            return True
        elif existing:
            self.console.print(f"[yellow]阶段2部分完成，已生成: {', '.join(existing)}，继续...[/yellow]")
        else:
            self.console.print("[cyan]开始阶段2：剧本创作[/cyan]")

        mechanism = (self.session.project_path / "mechanism.md").read_text(encoding="utf-8")
        outline = self.state.outline or ""
        char_count = 2 if self.state.is_prototype else 6
        event_count = 3 if self.state.is_prototype else 7
        total_cost = 0.0

        try:
            # ── Q1: 信息矩阵 ─────────────────────────────────────────────
            self.console.print("[cyan]Q1：生成信息矩阵...[/cyan]")
            matrix_prompt = self._build_matrix_prompt(outline, mechanism)
            matrix_system = "你是一个专业的剧本杀作家，擅长设计复杂、严谨的角色关系和事件逻辑。"
            matrix_operation = "stage_2_matrix"
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=self.console) as progress:
                task = progress.add_task("生成角色信息矩阵...", total=None)
                matrix_response = self._call_llm(
                    matrix_prompt,
                    system=matrix_system,
                    operation=matrix_operation,
                )
            total_cost += matrix_response.cost

            # 失败关闭：只有完整、合法的矩阵才能成为结果。校验先于任何写入——
            # 失败时 information_matrix.md、state/character_matrix.json、session 都保持原样。
            # 不再用 Markdown 迁移兜底（它会把缺失/非法单元格补成「否」）。
            try:
                json_data = self._extract_json_from_response(matrix_response.content)
                if json_data is None:
                    raise MatrixContractError(
                        ["响应中没有可解析的 JSON 信息矩阵（未找到含 characters 的合法 JSON 对象，"
                         "可能被截断、格式错误，或只给了 Markdown 表格）"]
                    )
                echo_problems = self._example_echo_problems(json_data)
                if echo_problems:
                    raise MatrixContractError(echo_problems)
                matrix_model = validate_generated_matrix(
                    json_data,
                    char_count=char_count,
                    event_count=event_count,
                    is_prototype=bool(self.state.is_prototype),
                    brief_content=outline,
                )
                # 发布与下游提示词用的都是校验通过的矩阵，不是模型原始回复：
                # 原始回复可能夹带未经校验的第二份矩阵或说明文字，与 character_matrix.json 不一致。
                # 先渲染再写文件：渲染失败时不会留下只写了一半的结果。
                # 渲染也在这个保护块里：一份校验通过却无法发布的回复同样已被拒绝，必须逐出缓存。
                matrix_md = self._render_matrix_markdown(matrix_model)
            except MatrixContractError as e:
                self._reject_stage_2_matrix(
                    matrix_prompt, matrix_system, matrix_operation, e.problems
                )
                return False
            except Exception as e:
                # 提取/校验/渲染本身意外失败（如嵌套过深触发 RecursionError）：这份响应同样已被拒绝，
                # 必须逐出缓存，否则重试会一直重放它、模型不会再被调用。随后交给外层报告并打印堆栈。
                self.console.print(
                    f"[red]Q1 失败：校验或渲染模型返回的信息矩阵时出现意外错误（{type(e).__name__}），"
                    "已丢弃该响应；未写入任何文件，阶段2未完成。[/red]"
                )
                self._evict_cached_response(matrix_operation, matrix_prompt, matrix_system)
                raise

            truth_mgr = TruthFileManager(self.session.project_path)
            truth_mgr.save_matrix(matrix_model, author="llm", note="Stage 2 Q1 matrix generation")
            self.console.print(f"[green]JSON 真相文件已保存[/green]")

            matrix_file = self.session.project_path / "information_matrix.md"
            matrix_file.write_text(matrix_md, encoding="utf-8")

            self.console.print(f"[green]Q1 完成：信息矩阵已保存[/green]")

            # ── Q2: 角色背景设定 ─────────────────────────────────────────
            self.console.print("[cyan]Q2：生成角色背景设定...[/cyan]")
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=self.console) as progress:
                task = progress.add_task("生成角色背景...", total=None)
                bg_response = self._call_stage_2_step(
                    "Q2（角色背景）",
                    self._build_background_prompt(outline, matrix_md),
                    self._loader.system_script_writer(self.state.story_type or "mechanic"),
                    "stage_2_background",
                )
            if bg_response is None:
                return False
            total_cost += bg_response.cost

            bg_file = self.session.project_path / "background.md"
            bg_file.write_text(bg_response.content, encoding="utf-8")
            self.console.print(f"[green]Q2 完成：背景设定已保存[/green]")

            # ── Q3: a本（阅读本）─────────────────────────────────────────
            self.console.print("[cyan]Q3：生成 a本（阅读本）...[/cyan]")
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=self.console) as progress:
                task = progress.add_task("生成角色剧本...", total=None)
                a_response = self._call_stage_2_step(
                    "Q3（a本）",
                    self._build_characters_prompt(bg_response.content, matrix_md),
                    self._loader.system_script_writer(self.state.story_type or "mechanic"),
                    "stage_2_characters",
                )
            if a_response is None:
                return False
            total_cost += a_response.cost

            chars_file = self.session.project_path / "characters.md"
            chars_file.write_text(a_response.content, encoding="utf-8")
            self.console.print(f"[green]Q3 完成：a本已保存[/green]")

            # ── Q4: b本（线索本）─────────────────────────────────────────
            self.console.print("[cyan]Q4：生成 b本（线索本）...[/cyan]")
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=self.console) as progress:
                task = progress.add_task("生成线索本...", total=None)
                b_response = self._call_stage_2_step(
                    "Q4（b本）",
                    self._build_clue_cards_prompt(a_response.content, matrix_md),
                    self._loader.system_script_writer(self.state.story_type or "mechanic"),
                    "stage_2_clue_cards",
                )
            if b_response is None:
                return False
            total_cost += b_response.cost

            b_file = self.session.project_path / "scripts_b.md"
            b_file.write_text(b_response.content, encoding="utf-8")
            self.console.print(f"[green]Q4 完成：b本已保存[/green]")

            # ── Q5: DM 手册 ─────────────────────────────────────────────
            self.console.print("[cyan]Q5：生成 DM 手册...[/cyan]")
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=self.console) as progress:
                task = progress.add_task("生成 DM 手册...", total=None)
                full_script = f"{a_response.content}\n\n{b_response.content}"
                dm_response = self._call_stage_2_step(
                    "Q5（DM 手册）",
                    self._build_dm_manual_prompt(full_script, matrix_md, mechanism),
                    self._loader.system_script_writer(self.state.story_type or "mechanic"),
                    "stage_2_dm_manual",
                )
            if dm_response is None:
                return False
            total_cost += dm_response.cost

            dm_file = self.session.project_path / "dm_manual.md"
            dm_file.write_text(dm_response.content, encoding="utf-8")
            self.console.print(f"[green]Q5 完成：DM 手册已保存[/green]")

            # ── Q6: 结局扩展 ─────────────────────────────────────────────
            self.console.print("[cyan]Q6：生成结局扩展...[/cyan]")
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=self.console) as progress:
                task = progress.add_task("生成结局...", total=None)
                ending_response = self._call_stage_2_step(
                    "Q6（结局扩展）",
                    self._build_endings_prompt(full_script, matrix_md, dm_response.content),
                    self._loader.system_script_writer(self.state.story_type or "mechanic"),
                    "stage_2_endings",
                )
            if ending_response is None:
                return False
            total_cost += ending_response.cost

            endings_file = self.session.project_path / "endings.md"
            endings_file.write_text(ending_response.content, encoding="utf-8")
            self.console.print(f"[green]Q6 完成：结局扩展已保存[/green]")

            # ── 完成 ───────────────────────────────────────────────────
            self.state.characters = {
                "raw": a_response.content,
                "background": bg_response.content,
                "scripts_b": b_response.content,
                "dm_manual": dm_response.content,
                "endings": ending_response.content,
            }
            self.state.current_stage = Stage.STAGE_2_SCRIPT
            self.session.save(self.state)

            self.console.print(f"[green]阶段2全部完成！总消耗：${total_cost:.4f}[/green]")
            self._show_cost_warning(total_cost)

            # 轻量穿帮检查
            self._run_consistency_check(a_response.content, matrix_md)

            return True

        except PromptRenderError as e:
            # 提示词输入缺失：在调用模型之前失败，不是程序异常，无需堆栈
            self.console.print(f"[red]阶段2失败：{e}[/red]")
            return False

        except Exception as e:
            self.console.print(f"[red]阶段2失败：{e}[/red]")
            import traceback
            traceback.print_exc()
            return False

    def _reject_stage_2_matrix(
        self, prompt: str, system: str, operation: str, problems: list[str]
    ) -> None:
        """Q1 响应未通过契约：报告问题，并清除这次调用的缓存，避免重试时重放同一个坏响应。"""
        self.console.print("[red]Q1 失败：模型返回的信息矩阵未通过校验，已丢弃；未写入任何文件，阶段2未完成。[/red]")
        for problem in problems:
            self.console.print(f"[red]  - {escape(problem)}[/red]")
        self._evict_cached_response(operation, prompt, system)

    def _evict_cached_response(self, operation: str, prompt: str, system: str) -> None:
        """逐出这次调用的缓存条目：_call_llm 先缓存后校验，被拒绝的响应不逐出，重试就会一直重放它。"""
        try:
            self._cache.invalidate(operation, prompt, system, self.llm.model)
            self.console.print("[yellow]已清除该次响应的缓存；重新运行阶段2会重新调用模型。[/yellow]")
        except Exception as e:
            self.console.print(f"[yellow]清除缓存失败：{escape(str(e))}（重试可能重放同一个无效响应，可用 cache 命令清空缓存）[/yellow]")

    def _call_stage_2_step(self, step: str, prompt: str, system: str, operation: str) -> Optional[LLMResponse]:
        """调用阶段2的一步（Q2-Q6）。空白或 None 回复视为失败：逐出缓存并返回 None，不写任何文件。

        下一步的严格渲染会因上游回复为空而拒绝调用；回复若已留在缓存里，重试永远重放这个空回复。
        """
        response = self._call_llm(prompt, system=system, operation=operation)
        # content 可能是 None（OpenAI/MiniMax 的 content_filter、拒答、长度截断）：与空白同样处理，
        # 否则 None.strip() 抛 AttributeError，跳过逐出，缓存里的 None 回复会被每次重试重放。
        # 只含零宽字符/BOM 的回复（str.strip 去不掉）同样视为空
        if not isinstance(response.content, str) or is_blank_text(response.content):
            self.console.print(
                f"[red]{step} 失败：模型返回了空内容，已丢弃；该步骤未写入文件，阶段2未完成。[/red]"
            )
            self._evict_cached_response(operation, prompt, system)
            return None
        return response

    def _stage_2_artifact_status(self) -> tuple[list[str], list[str]]:
        """Return existing/missing Stage 2 artifacts to support resume logic."""
        existing = [
            artifact for artifact in self.STAGE_2_REQUIRED_ARTIFACTS
            if (self.session.project_path / artifact).exists()
        ]
        missing = [
            artifact for artifact in self.STAGE_2_REQUIRED_ARTIFACTS
            if artifact not in existing
        ]
        return existing, missing

    def _build_matrix_prompt(self, outline: str, mechanism: str) -> str:
        """构建信息矩阵 prompt"""
        return self._loader.information_matrix_json(
            brief_content=outline,
            mechanism_content=mechanism,
            is_prototype=self.state.is_prototype,
        )

    def _run_consistency_check(self, characters: str, matrix: str) -> None:
        """轻量穿帮检查：检测角色剧本与信息矩阵的明显矛盾"""
        self.console.print("\n[cyan]运行穿帮检查...[/cyan]")

        prompt = self._build_consistency_check_prompt(characters, matrix)
        try:
            response = self._call_llm(
                prompt,
                system="你是一个严格的剧本杀穿帮检测员。简洁输出，只报告发现的问题，不要废话。",
                operation="consistency_check"
            )

            # 粗查：不再用子串判定“通过”（“不一致”也含“一致”）。结论以 audit 为准。
            self.console.print("[yellow]轻量检查完成（粗查，不判定通过；结果见 consistency_report.md，上线前请运行 murder-wizard audit）[/yellow]")
            self.console.print(Panel(escape(response.content[:1000]), border_style="yellow"))

            # 保存检查报告
            report_file = self.session.project_path / "consistency_report.md"
            report_file.write_text(response.content, encoding="utf-8")

        except Exception as e:
            self.console.print(f"[yellow]穿帮检查失败：{e}（不影响阶段完成）[/yellow]")

    def _build_consistency_check_prompt(self, characters: str, matrix: str) -> str:
        """构建穿帮检查 prompt"""
        return self._loader.consistency_round1(
            characters_content=characters,
            matrix_content=matrix,
            is_prototype=self.state.is_prototype,
        )

    def _build_characters_prompt(self, background_content: str, matrix: str) -> str:
        """构建角色剧本 prompt（Q3: a本）"""
        return self._loader.character_script_a(
            background_content=background_content,
            matrix_content=matrix,
            mechanism_content=(self.session.project_path / "mechanism.md").read_text(encoding="utf-8")
                if (self.session.project_path / "mechanism.md").exists() else "",
            is_prototype=self.state.is_prototype,
        )

    def _build_background_prompt(self, outline: str, matrix: str) -> str:
        """构建角色背景设定 prompt（Q2）"""
        return self._loader.character_background(
            brief_content=outline,
            matrix_content=matrix,
            is_prototype=self.state.is_prototype,
        )

    def _build_clue_cards_prompt(self, a_content: str, matrix: str) -> str:
        """构建线索本 prompt（Q4: b本）"""
        return self._loader.character_script_b(
            a_content=a_content,
            matrix_content=matrix,
            mechanism_content=(self.session.project_path / "mechanism.md").read_text(encoding="utf-8")
                if (self.session.project_path / "mechanism.md").exists() else "",
            is_prototype=self.state.is_prototype,
        )

    def _build_dm_manual_prompt(self, full_script: str, matrix: str, mechanism: str) -> str:
        """构建 DM 手册 prompt（Q5）"""
        return self._loader.dm_manual(
            full_script=full_script,
            matrix_content=matrix,
            mechanism_content=mechanism,
            is_prototype=self.state.is_prototype,
        )

    def _build_endings_prompt(self, full_script: str, matrix: str, dm_manual: str) -> str:
        """构建结局扩展 prompt（Q6）"""
        return self._loader.ending_expansion(
            full_script=full_script,
            matrix_content=matrix,
            dm_manual=dm_manual,
            is_prototype=self.state.is_prototype,
        )

    def _extract_json_from_response(self, content: str) -> dict | None:
        """从 LLM 响应中提取信息矩阵 JSON 对象（含顶层 characters 键的对象）。

        在每个可能的对象起点用 JSONDecoder.raw_decode 解析，```json 围栏里的 JSON 与裸 JSON 同等对待
        （同一份矩阵只会被找到一次）。不数括号：字符串值里的 { } 与前后说明文字里孤立的花括号都不会干扰解析。

        恰好一份 → 返回它；没有（含 content 不是文本）→ None；多于一份 → 抛 MatrixContractError。
        多份时无法判断哪份才是最终答案：只校验其中一份，另一份（草稿、被修订的版本、提示词里的示例、
        未经校验的矩阵）仍会混在回复里，所以整个回复一并拒绝。

        工作量有上限：每个失败的起点都要白扫一段文本，退化输入（如反复的 ``{"a":``）会让总量随长度二次方增长
        （实测 100 KB 约 11 秒、200 KB 约 46 秒）。累计扫描量超过 ``_EXTRACT_BUDGET_*`` 就放弃并返回 None，
        和「找不到 JSON」同样失败关闭；正常回复（说明文字、围栏、被截断的草稿）远在上限之内。
        """
        import re
        import json as _json

        if not isinstance(content, str):
            return None  # 模型没有给文本（如 content_filter 返回 null）：等同于没有 JSON

        decoder = _json.JSONDecoder()
        object_start = re.compile(r'\{\s*["}]')
        last_marker = content.rfind('"characters"')  # 矩阵对象的起点必然在它之前；没有则无需尝试（也避免退化输入的二次方开销）
        candidates: list[dict] = []
        pos = 0
        work = 0  # 失败的尝试累计白扫了多少字符
        budget = _EXTRACT_BUDGET_BASE + _EXTRACT_BUDGET_PER_CHAR * len(content)
        while True:
            found = object_start.search(content, pos)
            if found is None or found.start() > last_marker:
                break
            start = found.start()
            try:
                data, end = decoder.raw_decode(content, start)
            except (ValueError, RecursionError) as exc:
                scanned = (
                    _EXTRACT_RECURSION_COST if isinstance(exc, RecursionError)
                    else getattr(exc, "pos", start) - start  # JSONDecodeError.pos：解析走到的位置
                )
                work += max(_EXTRACT_MIN_ATTEMPT_COST, scanned)
                if work > budget:
                    return None  # 退化输入：放弃，失败关闭
                pos = start + 1  # 不是合法 JSON 对象（说明文字里的花括号、被截断等）：试下一个起点
                continue
            if isinstance(data, dict) and "characters" in data:
                candidates.append(data)
            pos = end  # 整个对象跳过（不是矩阵的对象也一样）
        if len(candidates) > 1:
            raise MatrixContractError([
                f"响应中含有 {len(candidates)} 份含 characters 的 JSON 对象，无法判断哪一份是最终答案；"
                "请只输出一份信息矩阵（不要附草稿或第二版，也不要重复提示词里的格式示例）"
            ])
        return candidates[0] if candidates else None

    @staticmethod
    def _example_echo_problems(data) -> list[str]:
        """回复是否照抄了 Q1 提示词里的格式示例：任一字符串值仍是示例的占位文字即视为照抄。

        示例本身能通过矩阵契约（契约只管结构），所以不能指望校验器拦下它；在这里按占位文字拦。
        判断见 is_example_placeholder_text：标记的写法差异（括号半角/全角、缺右括号、夹空白）与
        「只删了标记」都算照抄，不只认字面完全相同的「（示例）」。
        用显式栈遍历，不引入新的递归深度风险。
        """
        hits: list[str] = []
        stack = [("", data)]
        while stack:
            path, value = stack.pop()
            if isinstance(value, str):
                if is_example_placeholder_text(value):
                    hits.append(path or "(根)")
            elif isinstance(value, dict):
                stack.extend((f"{path}.{key}" if path else str(key), item) for key, item in value.items())
            elif isinstance(value, list):
                stack.extend((f"{path}[{index}]", item) for index, item in enumerate(value))
        if not hits:
            return []
        hits.sort()
        shown = "、".join(hits[:3]) + ("……" if len(hits) > 3 else "")
        return [
            f"响应照抄了提示词里的格式示例：{len(hits)} 处文字仍含占位标记「{EXAMPLE_PLACEHOLDER_MARK}」"
            f"或与示例的占位文字相同（如 {shown}）；示例只说明格式，必须依据 brief 与机制设计重新创作"
        ]

    @staticmethod
    def _render_matrix_markdown(matrix: CharacterMatrix) -> str:
        """把校验通过的矩阵渲染成 information_matrix.md（Q2-Q6、审计与 PDF 读到的就是这份内容）。

        只含矩阵本身，不含 meta（时间戳、提交号只属于 state/character_matrix.json）。
        """
        body = matrix.model_dump_json(ensure_ascii=False, indent=2, exclude={"meta"})
        return (
            "# 信息矩阵\n\n"
            "> 由通过校验的结构化矩阵生成，内容与 state/character_matrix.json 一致。\n\n"
            f"```json\n{body}\n```\n"
        )

    def run_stage_3(self) -> bool:
        """阶段3：视觉物料

        原型模式：只生成2张角色立绘 + 1张封面图
        """
        self.console.print("[cyan]阶段3：视觉物料[/cyan]")

        if not (self.session.project_path / "characters.md").exists():
            self.console.print("[red]请先完成阶段2[/red]")
            return False

        if (self.session.project_path / "image-prompts.md").exists():
            self.console.print("[green]阶段3已完成，跳过[/green]")
            return True

        characters = (self.session.project_path / "characters.md").read_text(encoding="utf-8")

        try:
            # 生成图像提示词
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=self.console) as progress:
                task = progress.add_task("生成图像提示词...", total=None)
                response = self._call_llm(
                    self._build_image_prompt(characters),
                    system="你是一个专业的视觉设计师，擅长为AI图像生成工具编写精确的提示词。",
                    operation="stage_3_prompts"
                )

            # 保存
            prompts_file = self.session.project_path / "image-prompts.md"
            prompts_file.write_text(response.content, encoding="utf-8")

            materials_dir = self.session.project_path / "materials"
            materials_dir.mkdir(exist_ok=True)
            (materials_dir / "角色图").mkdir(exist_ok=True)
            (materials_dir / "海报").mkdir(exist_ok=True)
            (materials_dir / "卡牌").mkdir(exist_ok=True)

            self.state.image_prompts = {"raw": response.content}
            self.state.current_stage = Stage.STAGE_3_VISUAL
            self.session.save(self.state)

            self.console.print(f"[green]图像提示词已保存到：{prompts_file}[/green]")
            self._show_cost_warning(response.cost)

            # 提示用户如何生成图像
            self.console.print("\n[yellow]提示：[/yellow]")
            self.console.print("图像提示词已生成。下一步：")
            self.console.print("1. 手动将提示词复制到即梦/海螺AI生成图像")
            self.console.print("2. 将生成的图像保存到 materials/角色图/ 目录")
            self.console.print("3. 运行 expand 将原型扩写为完整版本")

            return True

        except Exception as e:
            self.console.print(f"[red]阶段3失败：{e}[/red]")
            return False

    def _build_image_prompt(self, characters: str) -> str:
        """构建图像提示词 prompt"""
        return self._loader.visual_materials(
            characters_content=characters,
            story_type=self.state.story_type or "机制本",
            is_prototype=self.state.is_prototype,
        )

    last_expand_result = None

    def run_expand(self, *, confirm=None, accept_overwrite: bool = False) -> bool:
        """expand：把原型（2 人 3 事件）扩写为完整版（6 人 7 事件）。

        在内存里生成并校验完整候选，作者确认（confirm 回调或 accept_overwrite）后才备份并覆盖；
        没有确认入口时在调用模型之前就失败。任何失败都不改动作品。结果见 last_expand_result。
        """
        from murder_wizard.cli.expand_flow import ExpandFlow
        from murder_wizard.wizard.expansion import ExpandStatus

        self.console.print("[cyan]正在 expand 原型为完整版本...[/cyan]")
        if not self.state.is_prototype:
            self.console.print("[yellow]当前不是原型，跳过 expand[/yellow]")
            from murder_wizard.wizard.expansion import ExpandResult
            self.last_expand_result = ExpandResult(ExpandStatus.NOT_PROTOTYPE)
            return False
        self.last_expand_result = ExpandFlow(self, confirm=confirm, accept_overwrite=accept_overwrite).run()
        return self.last_expand_result.status is ExpandStatus.APPLIED

    # ──────────────────────────────────────────────────────────────────
    # 完整穿帮审计（R05/R06）：默认只读；解析失败 = 未完成；修复只在作者显式接受后写入
    # ──────────────────────────────────────────────────────────────────

    AUDIT_SYSTEM = {
        "matrix": "你是一个严格的剧本杀穿帮审计员，擅长逐格核对信息矩阵，发现最隐蔽的逻辑矛盾。",
        "mechanism": "你是一个专业的剧本杀平衡性分析师，检查机制与角色行为的一致性。",
        "ending": "你是一个严格的剧本杀结局审计员，检查结局是否合理、是否有唯一解。",
    }

    def run_audit(self, force: bool = False) -> bool:
        """兼容包装：仅当审计 PASSED（模型未报告 P0）时返回 True。--force 已弃用，不改变结论。"""
        try:
            outcome = self.run_audit_checked(force=force)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            self.console.print(f"[red]审计失败：{escape(str(e))}[/red]")
            return False
        return bool(outcome)

    def run_audit_checked(self, force: bool = False) -> AuditOutcome:
        """真正的审计入口：返回 AuditOutcome（passed / waived / blocked / incomplete）。"""
        self.console.print("[cyan]运行完整穿帮审计（只读：不会改写作品）...[/cyan]")
        materials = AuditMaterials.from_dir(
            self.session.project_path, is_prototype=bool(self.state.is_prototype)
        )
        waivers = load_waivers(self.session.project_path / ".known_p0")
        outcome = AuditOutcome.start(materials, model=str(getattr(self.llm, "model", "")), forced=force)
        if force:
            outcome.notes.append("--force 已弃用，不改变审计结论")
        try:
            self._execute_audit(outcome, waivers, suggest_fixes=True)
        except KeyboardInterrupt:
            outcome.notes.append("用户中断，未运行的轮次标记为 not_run")
            self._finalize_audit(outcome, waivers)
            self._write_audit_report(outcome)
            raise
        self._write_audit_report(outcome)
        self._print_audit_summary(outcome)
        self._show_cost_warning(outcome.cost)
        return outcome

    def audit_materials(
        self, materials: AuditMaterials, *, waivers: Optional[WaiverFile] = None,
        suggest_fixes: bool = False, force: bool = False,
    ) -> AuditOutcome:
        """对给定材料审计（如 expand 候选）：不写报告、不读 .known_p0、不提示输入。"""
        outcome = AuditOutcome.start(materials, model=str(getattr(self.llm, "model", "")), forced=force)
        self._execute_audit(outcome, waivers or WaiverFile(), suggest_fixes=suggest_fixes)
        return outcome

    def apply_audit_fixes(self, outcome: AuditOutcome, accepted_ids) -> ApplyResult:
        """把作者显式接受的补丁写入作品（先备份；失败回滚）。审计结论不变。"""
        result = apply_audit_patches(
            self.session.project_path, outcome.materials, outcome.proposals, accepted_ids
        )
        outcome.applied = result
        if not result.error:
            self._write_audit_report(outcome)
        return result

    def _finalize_audit(self, outcome: AuditOutcome, waivers: WaiverFile) -> None:
        issues = list(outcome.static_issues)
        for kind in ROUNDS:
            r = outcome.rounds[kind]
            if r.status in ("ok", "truncated"):
                issues.extend(r.issues)
        issues, outcome.waiver = apply_waivers(assign_refs(issues), waivers)
        outcome.issue_list = issues

    def _execute_audit(self, outcome: AuditOutcome, waivers: WaiverFile, suggest_fixes: bool) -> None:
        materials = outcome.materials
        if materials.problems:
            self.console.print("[red]审计材料不完整，未调用模型：[/red]")
            for p in materials.problems:
                self.console.print(f"[red]  - {escape(p)}[/red]")
            self._finalize_audit(outcome, waivers)
            return
        total = sum(materials.round_chars(k) for k in ROUNDS)
        self.console.print(
            f"[dim]将向模型服务商发送 {len(materials.texts)} 份材料，三轮合计约 {total} 字符（不截断）[/dim]"
        )
        outcome.static_issues = run_static_checks(materials)
        aborted = False
        for kind in ROUNDS:
            if aborted:
                continue
            aborted = not self._run_audit_round(kind, outcome)
        self._finalize_audit(outcome, waivers)
        if suggest_fixes and outcome.status is not AuditStatus.INCOMPLETE:
            self._suggest_fixes(outcome)

    def _run_audit_round(self, kind: str, outcome: AuditOutcome) -> bool:
        """跑一轮审计。返回 False 表示 LLM 调用失败（其后轮次不再运行）。"""
        materials = outcome.materials
        result = outcome.rounds[kind]
        n = ROUND_NUMBER[kind]
        try:
            prompt = self._loader.audit_round(
                kind,
                is_prototype=bool(self.state.is_prototype),
                char_count=materials.char_count,
                event_count=materials.event_count,
                max_issues=MAX_ISSUES_PER_ROUND,
                output_contract=output_contract(kind, materials),
                **materials.blocks_for(kind),
            )
        except (PromptRenderError, KeyError) as e:
            result.status, result.reason = "render_failed", str(e)
            self.console.print(f"[red]第{n}轮提示词渲染失败，未调用模型：{escape(str(e))}[/red]")
            return True
        result.prompt_chars = len(prompt)
        system = self.AUDIT_SYSTEM[kind]
        operation = f"audit_round{n}"
        self.console.print(f"[cyan]第{n}轮 {ROUND_TITLE[kind]}：{len(prompt)} 字符，含 {len(ROUND_FILES[kind])} 份材料[/cyan]")
        try:
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=self.console) as progress:
                progress.add_task("深度审计中...", total=None)
                resp = self._call_llm(prompt, system=system, operation=operation)
        except Exception as e:
            result.status, result.reason = "call_failed", str(e)
            outcome.notes.append(f"第{n}轮模型调用失败，其后轮次未运行：{e}")
            return False
        result.cost = resp.cost
        outcome.cost += resp.cost
        result.raw = resp.content
        try:
            parsed = parse_round_output(kind, resp.content, materials)
        except AuditParseError as e:
            result.status, result.reason = "parse_error", str(e)
            result.hints = hint_lines(resp.content)
            self.console.print(f"[yellow]第{n}轮输出无法解析：{escape(str(e))}（不计为 0 个 P0）[/yellow]")
            try:
                self._cache.invalidate(operation, prompt, system, self.llm.model)
            except Exception as ce:
                outcome.notes.append(f"清缓存失败，重跑可能重放同一个坏响应，可用 cache --clear：{ce}")
            return True
        result.issues = parsed.issues
        result.has_more = parsed.has_more
        result.status = "truncated" if parsed.has_more else "ok"
        if parsed.has_more:
            result.reason = "模型声明还有未列出的问题，无法排除被挤出的 P0"
        return True

    def _suggest_fixes(self, outcome: AuditOutcome) -> None:
        cands = [i for i in outcome.issue_list
                 if not i.waived and i.severity in ("P0", "P1") and i.file in EDITABLE_FILES][:8]
        if not cands:
            return
        materials = outcome.materials
        issues_block = "\n".join(
            f"{i.ref} [{i.severity}] {i.file}「{i.anchor}」：{i.problem}" + (f"（引用：{i.quote}）" if i.quote else "")
            for i in cands
        )
        files_block = "\n\n".join(materials.block(f) for f in dict.fromkeys(i.file for i in cands))
        try:
            prompt = self._loader.audit_fixes(
                is_prototype=bool(self.state.is_prototype),
                issues_block=issues_block, files_block=files_block, output_contract=fix_contract(),
            )
            system = self._loader.system_audit_fixer()
            resp = self._call_llm(prompt, system=system, operation="audit_fixes")
        except Exception as e:
            outcome.fix_note = f"修复建议调用失败（不影响审计结论）：{e}"
            return
        outcome.cost += resp.cost
        try:
            outcome.proposals, outcome.unfixable = parse_fix_output(resp.content, cands, materials)
        except AuditParseError as e:
            outcome.fix_note = f"修复建议无法解析（不影响审计结论）：{e}"
            try:
                self._cache.invalidate("audit_fixes", prompt, system, self.llm.model)
            except Exception:
                pass

    def _write_audit_report(self, outcome: AuditOutcome) -> None:
        report = render_report(outcome, generated_at=time.strftime("%Y-%m-%d %H:%M:%S"))
        path = self.session.project_path / "audit_report.md"
        tmp = path.with_suffix(".md.tmp")
        try:
            tmp.write_text(report, encoding="utf-8")
            os.replace(tmp, path)
            outcome.report_path = path
            outcome.report_error = ""
        except OSError as e:
            outcome.report_error = str(e)
            self.console.print(f"[red]审计报告写入失败：{escape(str(e))}[/red]")

    def _print_audit_summary(self, outcome: AuditOutcome) -> None:
        st = outcome.status
        color = {AuditStatus.PASSED: "green", AuditStatus.WAIVED: "yellow",
                 AuditStatus.BLOCKED: "red", AuditStatus.INCOMPLETE: "yellow"}[st]
        self.console.print(f"[{color}]{escape(outcome.headline)}[/{color}]")
        for i in outcome.p0_unwaived:
            self.console.print(
                f"[red]  {i.ref} · {i.key} · {escape(i.dimension)} · {escape(i.file)}「{escape(i.anchor)}」 · {escape(i.problem)}[/red]"
            )
        if outcome.p0_unwaived:
            self.console.print("[dim]确认可接受的 P0，可在 .known_p0 加一行：AUD-xxxxxxxx 理由：…（见 audit_report.md）[/dim]")
        for label, items in (("未使用的豁免行", outcome.waiver.unused), ("含糊的豁免行", outcome.waiver.ambiguous),
                             ("过短的豁免行", outcome.waiver.too_short)):
            for x in items:
                self.console.print(f"[yellow]  {label}：{escape(x)}[/yellow]")
        if outcome.waiver.read_error:
            self.console.print(f"[yellow]  .known_p0 读取失败，未应用豁免：{escape(outcome.waiver.read_error)}[/yellow]")
        if outcome.report_path:
            self.console.print(f"[green]审计报告已保存到：{outcome.report_path}[/green]")

    def _show_cost_warning(self, cost: float):
        """显示成本警告"""
        total = self.session.get_total_cost()
        self.console.print(f"\n[dim]本次消耗：约 ¥{cost:.4f}[/dim]")
        self.console.print(f"[dim]累计消耗：约 ¥{total:.4f}[/dim]")

    def run_stage_4(self) -> bool:
        """阶段4：用户测试

        生成测试指南，提示用户收集反馈并用 --analyze 分析
        """
        self.console.print("[cyan]阶段4：用户测试[/cyan]")

        if not (self.session.project_path / "characters.md").exists():
            self.console.print("[red]请先完成阶段2[/red]")
            return False

        if (self.session.project_path / "test_guide.md").exists():
            self.console.print("[green]阶段4已完成，跳过[/green]")
            return True

        characters = (self.session.project_path / "characters.md").read_text(encoding="utf-8")
        mechanism = (self.session.project_path / "mechanism.md").read_text(encoding="utf-8") if (self.session.project_path / "mechanism.md").exists() else ""

        try:
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=self.console) as progress:
                task = progress.add_task("生成测试指南...", total=None)
                response = self._call_llm(
                    self._build_test_guide_prompt(characters, mechanism),
                    system="你是一个专业的剧本杀测试设计师，擅长设计用户体验测试流程，发现游戏平衡性问题。",
                    operation="stage_4_test_guide"
                )

            guide_file = self.session.project_path / "test_guide.md"
            guide_file.write_text(response.content, encoding="utf-8")

            self.state.current_stage = Stage.STAGE_4_TEST
            self.session.save(self.state)

            self.console.print(f"[green]测试指南已保存到：{guide_file}[/green]")
            self._show_cost_warning(response.cost)

            self.console.print("\n[yellow]下一步操作：[/yellow]")
            self.console.print("1. 使用测试指南组织内测")
            self.console.print("2. 收集玩家反馈，记录到 feedback.md")
            self.console.print("3. 再次运行：murder-wizard phase <项目名> 4 --analyze")
            self.console.print("   （分析反馈并生成迭代建议）")

            return True

        except Exception as e:
            self.console.print(f"[red]阶段4失败：{e}[/red]")
            return False

    def _build_test_guide_prompt(self, characters: str, mechanism: str) -> str:
        """构建测试指南 prompt（使用 PromptLoader）"""
        # 使用 Q2 角色背景模板的一部分作为参考
        # 这里复用 system_prompt + 简洁结构
        system = self._loader.system_test_designer()
        is_proto = self.state.is_prototype
        char_count = 2 if is_proto else 6
        return f"""{system}

请基于以下内容生成测试指南。

角色剧本：
{characters}

机制设计：
{mechanism}

请生成：
1. 测试场景设置（如何布置场景、介绍规则）
2. DM主持要点（每个阶段的关键提示词）
3. 平衡性检查点（哪些环节容易出现不平衡）
4. 玩家反馈收集模板
5. 常见问题及解决方案

格式：Markdown，包含表格和清单

原型模式：聚焦{char_count}人版的快速验证流程。
"""

    def run_stage_4_analyze(self) -> bool:
        """阶段4分析模式：分析 feedback.md 并生成 iteration_report.md（经 _call_llm，成本与缓存照常）。"""
        root = self.session.project_path
        feedback_file = root / "feedback.md"
        if not feedback_file.exists():
            self.console.print("[yellow]未找到 feedback.md[/yellow]")
            self.console.print("请先收集玩家反馈，保存到 feedback.md 后再运行分析")
            return False
        feedback = feedback_file.read_text(encoding="utf-8")
        characters = (root / "characters.md").read_text(encoding="utf-8") if (root / "characters.md").exists() else ""
        mechanism = (root / "mechanism.md").read_text(encoding="utf-8") if (root / "mechanism.md").exists() else ""
        try:
            response = self._call_llm(
                f"""基于以下测试反馈，生成迭代建议：

玩家反馈：
{feedback}

原角色剧本：
{characters}

原机制设计：
{mechanism}

请分析：
1. 哪些地方存在平衡性问题
2. 哪些角色体验不佳或过于强大
3. 机制是否有漏洞或死路
4. 需要修改的具体内容（角色剧本调整/机制调整）
5. 优先级排序（高/中/低）

格式：Markdown""",
                system="你是一个专业的剧本杀平衡性分析师，擅长发现游戏问题并给出具体修改建议。",
                operation="stage_4_analyze",
            )
            report_file = root / "iteration_report.md"
            report_file.write_text(response.content, encoding="utf-8")
            self.console.print(f"[green]迭代报告已保存到：{report_file}[/green]")
            self._show_cost_warning(response.cost)
            return True
        except Exception as e:
            self.console.print(f"[red]分析失败：{escape(str(e))}[/red]")
            return False

    def run_stage_5(self) -> bool:
        """阶段5：商业化

        生成成本核算、定价策略、销售渠道
        """
        self.console.print("[cyan]阶段5：商业化[/cyan]")

        if not (self.session.project_path / "characters.md").exists():
            self.console.print("[red]请先完成阶段2[/red]")
            return False

        if (self.session.project_path / "commercial.md").exists():
            self.console.print("[green]阶段5已完成，跳过[/green]")
            return True

        characters = (self.session.project_path / "characters.md").read_text(encoding="utf-8")
        mechanism = (self.session.project_path / "mechanism.md").read_text(encoding="utf-8") if (self.session.project_path / "mechanism.md").exists() else ""

        try:
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=self.console) as progress:
                task = progress.add_task("生成商业化方案...", total=None)
                response = self._call_llm(
                    self._build_commercial_prompt(characters, mechanism),
                    system="你是一个专业的剧本杀商业化顾问，熟悉国内剧本杀市场价格、成本和渠道。",
                    operation="stage_5_commercial"
                )

            commercial_file = self.session.project_path / "commercial.md"
            commercial_file.write_text(response.content, encoding="utf-8")

            self.state.current_stage = Stage.STAGE_5_COMMERCIAL
            self.session.save(self.state)

            self.console.print(f"[green]商业化方案已保存到：{commercial_file}[/green]")
            self._show_cost_warning(response.cost)

            return True

        except Exception as e:
            self.console.print(f"[red]阶段5失败：{e}[/red]")
            return False

    def _build_commercial_prompt(self, characters: str, mechanism: str) -> str:
        """构建商业化 prompt"""
        system = self._loader.system_commercial_consultant()
        return f"""{system}

请基于以下剧本信息，生成商业化方案。

角色剧本：
{characters}

机制设计：
{mechanism}

请生成：
1. 成本核算表（印刷、道具、包装、物流）
2. 定价策略（成本加成法 vs 市场竞品对比）
3. 销售渠道（线上：淘宝/闲鱼/小红书；线下：剧本杀店/桌游吧）
4. 利润估算（按销量分档：100/500/1000套）
5. 上市时机建议（节假日、剧本杀旺季）

格式：Markdown，包含表格
"""

    def run_stage_6(self) -> bool:
        """阶段6：印刷生产

        生成 PDF 并检查印刷就绪状态
        """
        self.console.print("[cyan]阶段6：印刷生产[/cyan]")

        if not (self.session.project_path / "characters.md").exists():
            self.console.print("[red]请先完成阶段2[/red]")
            return False

        try:
            from murder_wizard.print.pdf_gen import PDFGenerator
        except ImportError:
            self.console.print("[red]缺少 pdf_gen 模块[/red]")
            return False

        generator = PDFGenerator(self.session.project_path)

        # 检查印刷就绪状态
        ready, issues = generator.check_print_ready()

        if not ready:
            self.console.print("[yellow]印刷就绪检查发现问题：[/yellow]")
            for issue in issues:
                self.console.print(f"  - {issue}")

        # 生成 PDF：必须真的产出非空文件才算成功（失败不能显示为"印刷文件生成完成"）
        pdf_failures: list[str] = []
        for label, make in (("剧本 PDF", generator.generate_script_pdf), ("线索卡 PDF", generator.generate_clue_cards)):
            try:
                out = make()
                if not out or not Path(str(out)).is_file() or Path(str(out)).stat().st_size == 0:
                    raise RuntimeError(f"未生成文件：{out}")
                self.console.print(f"[green]{label}已生成：{out}[/green]")
            except Exception as e:
                pdf_failures.append(f"{label}：{e}")
                self.console.print(f"[red]{label}生成失败：{escape(str(e))}[/red]")
        if pdf_failures:
            self.console.print("[red]阶段6失败：必要的 PDF 未生成，阶段状态未推进。[/red]")
            return False

        # 生成印刷订单信息
        order_info = generator.generate_proof_order()
        order_file = self.session.project_path / "print_order.json"
        order_file.write_text(json.dumps(order_info, ensure_ascii=False, indent=2), encoding="utf-8")
        self.console.print(f"[green]印刷订单信息已保存到：{order_file}[/green]")

        self.state.current_stage = Stage.STAGE_6_PRINT
        self.session.save(self.state)

        self.console.print("\n[bold green]印刷文件生成完成！[/bold green]")
        self.console.print("下一步：")
        self.console.print("1. 审核 PDF 文件")
        self.console.print("2. 联系印刷厂打样")
        self.console.print("3. 确认后下单量产")

        return True

    def run_stage_7(self) -> bool:
        """阶段7：宣发内容

        生成 B站/小红书/公众号推广文案
        """
        self.console.print("[cyan]阶段7：宣发内容[/cyan]")

        if not (self.session.project_path / "characters.md").exists():
            self.console.print("[red]请先完成阶段2[/red]")
            return False

        if (self.session.project_path / "promo_content.md").exists():
            self.console.print("[green]阶段7已完成，跳过[/green]")
            return True

        characters = (self.session.project_path / "characters.md").read_text(encoding="utf-8")
        mechanism = (self.session.project_path / "mechanism.md").read_text(encoding="utf-8") if (self.session.project_path / "mechanism.md").exists() else ""

        try:
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=self.console) as progress:
                task = progress.add_task("生成宣发内容...", total=None)
                response = self._call_llm(
                    self._build_promo_prompt(characters, mechanism),
                    system="你是一个专业的剧本杀宣发文案专家，熟悉B站、小红书、公众号的文案风格。",
                    operation="stage_7_promo"
                )

            promo_file = self.session.project_path / "promo_content.md"
            promo_file.write_text(response.content, encoding="utf-8")

            self.state.current_stage = Stage.STAGE_7_PROMO
            self.session.save(self.state)

            self.console.print(f"[green]宣发内容已保存到：{promo_file}[/green]")
            self._show_cost_warning(response.cost)

            return True

        except Exception as e:
            self.console.print(f"[red]阶段7失败：{e}[/red]")
            return False

    def _build_promo_prompt(self, characters: str, mechanism: str) -> str:
        """构建宣发内容 prompt"""
        system = self._loader.system_promo_writer()
        return f"""{system}

请基于以下剧本信息，生成宣发内容。

角色剧本：
{characters}

机制设计：
{mechanism}

请为以下平台生成文案：
1. B站/小红书预告文案（吸引眼球，适合传播）
2. 公众号推文（详细介绍剧情和机制，适合深度用户）
3. 淘宝/闲鱼商品描述（突出卖点，促进转化）
4. 社群里推荐语（简短有力，引发讨论）

格式：Markdown，区分不同平台"""

    def run_stage_8(self) -> bool:
        """阶段8：社区运营

        生成玩家社群运营方案和扩展包计划
        """
        self.console.print("[cyan]阶段8：社区运营[/cyan]")

        if not (self.session.project_path / "characters.md").exists():
            self.console.print("[red]请先完成阶段2[/red]")
            return False

        if (self.session.project_path / "community_plan.md").exists():
            self.console.print("[green]阶段8已完成，跳过[/green]")
            return True

        characters = (self.session.project_path / "characters.md").read_text(encoding="utf-8")
        mechanism = (self.session.project_path / "mechanism.md").read_text(encoding="utf-8") if (self.session.project_path / "mechanism.md").exists() else ""

        try:
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=self.console) as progress:
                task = progress.add_task("生成社区运营方案...", total=None)
                response = self._call_llm(
                    self._build_community_prompt(characters, mechanism),
                    system="你是一个专业的剧本杀社群运营专家，熟悉玩家社群建设和扩展包开发。",
                    operation="stage_8_community"
                )

            plan_file = self.session.project_path / "community_plan.md"
            plan_file.write_text(response.content, encoding="utf-8")

            self.state.current_stage = Stage.STAGE_8_COMMUNITY
            self.session.save(self.state)

            self.console.print(f"[green]社区运营方案已保存到：{plan_file}[/green]")
            self._show_cost_warning(response.cost)

            return True

        except Exception as e:
            self.console.print(f"[red]阶段8失败：{e}[/red]")
            return False

    def _build_community_prompt(self, characters: str, mechanism: str) -> str:
        """构建社区运营 prompt"""
        system = self._loader.system_community_operations()
        return f"""{system}

请基于以下剧本信息，生成社区运营方案。

角色剧本：
{characters}

机制设计：
{mechanism}

请生成：
1. 玩家社群建设方案（QQ/微信群、Discord、豆瓣小组）
2. 核心玩家培养计划（KOC策略）
3. 扩展包（续作/DLC）开发计划
4. 玩家反馈闭环机制
5. 盗版防护策略

格式：Markdown，包含时间线和里程碑"""
