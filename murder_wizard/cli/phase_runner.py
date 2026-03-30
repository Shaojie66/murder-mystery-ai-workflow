"""Phase runner - executes each stage's LLM workflow."""
import json
import time
import signal
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from murder_wizard.wizard.session import SessionManager
from murder_wizard.wizard.state_machine import MurderWizardState, Stage
from murder_wizard.llm.client import create_llm_adapter, LLMResponse
from murder_wizard.llm.cache import LLMCache


class PhaseRunner:
    """阶段执行器"""

    def __init__(self, session: SessionManager, state: MurderWizardState, console: Console):
        self.session = session
        self.state = state
        self.console = console
        self.llm = None
        self._cache = LLMCache(session.project_path)
        self._setup_llm()

    def _setup_llm(self):
        """初始化 LLM 适配器"""
        try:
            provider = "claude"  # 默认 Claude
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
        """阶段1：机制设计

        原型模式：只生成3条核心事件（而非5-7条）
        """
        self.console.print("[cyan]阶段1：机制设计[/cyan]")

        # 检查前置条件
        if not self.state.outline:
            self.console.print("[red]缺少大纲，请先运行 init[/red]")
            return False

        # 检查是否已完成
        if (self.session.project_path / "mechanism.md").exists():
            self.console.print("[green]阶段1已完成，跳过[/green]")
            return True

        prompt = self._build_mechanism_prompt()
        system = """你是一个专业的剧本杀机制设计师。

擅长设计：
1. 公平、有趣的游戏机制
2. 阵营对抗和投票机制
3. 搜证和推理机制
4. 角色技能和特殊能力
5. 回合流程和阶段划分

你设计的机制要：
- 每个阵营都有获胜机会
- 玩家有多种策略选择
- 线索有层次感（表面线索、深层线索、关键线索）
- 有记忆点（让人印象深刻的机制）"""

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                console=self.console,
            ) as progress:
                task = progress.add_task("生成机制设计...", total=None)
                response = self._call_llm(prompt, system, "stage_1_mechanism")

            # 保存产物
            mechanism_file = self.session.project_path / "mechanism.md"
            mechanism_file.write_text(response.content, encoding="utf-8")

            self.state.current_stage = Stage.STAGE_1_MECHANISM
            self.session.save(self.state)

            self.console.print(f"[green]机制设计已保存到：{mechanism_file}[/green]")
            self._show_cost_warning(response.cost)
            return True

        except Exception as e:
            self.console.print(f"[red]阶段1失败：{e}[/red]")
            return False

    def _build_mechanism_prompt(self) -> str:
        """构建机制设计 prompt"""
        is_prototype = self.state.is_prototype
        event_count = 3 if is_prototype else 7

        return f"""基于以下大纲，设计剧本杀的机制：

{self.state.outline}

类型：{self.state.story_type}

请设计：
1. 游戏阶段划分（如：夜晚/白天/特殊阶段）
2. 阵营设置（如果有阵营对抗）
3. 投票和淘汰机制
4. 搜证机制（如何获得线索）
5. 关键事件列表（{event_count}个核心事件，按时间顺序）
6. 胜负判定条件
7. 可选的特色机制（技能、道具等）

原型模式：精简设计，核心机制优先。

格式：Markdown，包含表格（如事件表、角色技能表）
"""

    def run_stage_2(self) -> bool:
        """阶段2：剧本创作

        原型模式：只生成2个角色（而非6个）
        """
        self.console.print("[cyan]阶段2：剧本创作[/cyan]")

        if not (self.session.project_path / "mechanism.md").exists():
            self.console.print("[red]请先完成阶段1[/red]")
            return False

        if (self.session.project_path / "characters.md").exists():
            self.console.print("[green]阶段2已完成，跳过[/green]")
            return True

        mechanism = (self.session.project_path / "mechanism.md").read_text(encoding="utf-8")
        outline = self.state.outline or ""

        try:
            # 第一步：生成信息矩阵
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=self.console) as progress:
                task = progress.add_task("生成角色信息矩阵...", total=None)
                matrix_response = self._call_llm(
                    self._build_matrix_prompt(outline, mechanism),
                    system="你是一个专业的剧本杀作家，擅长设计复杂、严谨的角色关系和事件逻辑。",
                    operation="stage_2_matrix"
                )

            # 第二步：生成角色脚本
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=self.console) as progress:
                task = progress.add_task("生成角色剧本...", total=None)
                char_response = self._call_llm(
                    self._build_characters_prompt(matrix_response.content),
                    system="你是一个专业的剧本杀作家，每位角色的剧本都要符合其身份、背景和视角。",
                    operation="stage_2_characters"
                )

            # 保存
            matrix_file = self.session.project_path / "information_matrix.md"
            matrix_file.write_text(matrix_response.content, encoding="utf-8")

            chars_file = self.session.project_path / "characters.md"
            chars_file.write_text(char_response.content, encoding="utf-8")

            self.state.characters = {"raw": char_response.content}
            self.state.current_stage = Stage.STAGE_2_SCRIPT
            self.session.save(self.state)

            self.console.print(f"[green]角色信息矩阵已保存到：{matrix_file}[/green]")
            self.console.print(f"[green]角色剧本已保存到：{chars_file}[/green]")
            self._show_cost_warning(matrix_response.cost + char_response.cost)

            # 轻量穿帮检查
            self._run_consistency_check(char_response.content, matrix_response.content)

            return True

        except Exception as e:
            self.console.print(f"[red]阶段2失败：{e}[/red]")
            return False

    def _build_matrix_prompt(self, outline: str, mechanism: str) -> str:
        """构建信息矩阵 prompt"""
        is_prototype = self.state.is_prototype
        char_count = 2 if is_prototype else 6

        return f"""基于以下大纲和机制设计，为{char_count}位角色创建信息矩阵。

大纲：
{outline}

机制设计：
{mechanism}

类型：{self.state.story_type}

请创建信息矩阵表，格式：

| 事件/信息 | 角色1 | 角色2 | ... | 角色N |
|-----------|-------|-------|-----|--------|

行：每个关键事件（{5 if is_prototype else 15}个左右）
列：每位角色
单元格：该角色在该事件中知道什么、做了什么、看到了什么

规则：
1. 每个人只知道自己视角的信息
2. 不能有穿帮（角色不能知道当时不知道的信息）
3. 六人拼图 = 完整真相
4. 用"?"表示该角色不知道该信息
5. 用"[盲区]"表示该事件的故意留白

原型模式：2人表格，3条事件线。
"""

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

            # 检查是否有发现问题
            content = response.content.lower().strip()
            if any(word in content for word in ["无穿帮", "未发现", "没有矛盾", "一致"]):
                self.console.print("[green]✓ 穿帮检查通过，未发现明显矛盾[/green]")
            else:
                self.console.print("[yellow]⚠ 穿帮检查发现以下问题：[/yellow]")
                self.console.print(Panel(response.content[:1000], border_style="yellow"))

            # 保存检查报告
            report_file = self.session.project_path / "consistency_report.md"
            report_file.write_text(response.content, encoding="utf-8")

        except Exception as e:
            self.console.print(f"[yellow]穿帮检查失败：{e}（不影响阶段完成）[/yellow]")

    def _build_consistency_check_prompt(self, characters: str, matrix: str) -> str:
        """构建穿帮检查 prompt"""
        return f"""请检查以下角色剧本与信息矩阵是否存在明显穿帮。

重点检查：
1. 角色是否提及了当时还不知道的信息
2. 时间线是否矛盾（如：角色在某事件前就已知某事）
3. 秘密/隐瞒信息是否被其他角色意外暴露
4. 阵营设定是否自相矛盾

角色剧本：
{characters}

信息矩阵：
{matrix}

请逐角色检查，输出格式：
- 无穿帮：输出"穿帮检查通过"
- 有穿帮：列出每个问题，格式为"角色X：在Y事件中本不应该知道Z信息"

检查结论："""

    def _build_characters_prompt(self, matrix: str) -> str:
        """构建角色剧本 prompt"""
        is_prototype = self.state.is_prototype
        char_count = 2 if is_prototype else 6

        return f"""基于以下信息矩阵，为{char_count}位角色生成完整剧本。

信息矩阵：
{matrix}

请为每位角色生成：
1. 角色背景故事（200字）
2. 角色在各个事件中的经历（按时间顺序）
3. 角色视角的"真相"（该角色认为发生了什么）
4. 角色隐藏的秘密（如果该角色有秘密的话）
5. 角色需要隐瞒的信息（不能让别人知道的事）

剧本格式：Markdown，每个角色一个章节

原型模式：每位角色的剧本约1000字，简洁但完整。
"""

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
        is_prototype = self.state.is_prototype
        char_count = 2 if is_prototype else 6

        return f"""基于以下角色设定，生成AI图像生成提示词。

角色设定：
{characters}

类型：{self.state.story_type}

请为以下内容生成提示词：
1. {char_count}张角色立绘（每位角色一张）
2. 1张封面图（整体氛围图）
3. {3 if is_prototype else 10}张线索卡底图

提示词要求：
- 风格：国风、精致、电影感
- 格式：英文为主，关键词+细节描述+风格标签
- 每张图附带3个备选变体提示词

格式：Markdown表格
| 图像 | 提示词 | 变体1 | 变体2 | 变体3 |
"""

    def run_expand(self) -> bool:
        """expand：将原型扩写为完整版本（带并发控制）

        Phase 1: 扩写事件线和信息矩阵（单次 LLM 调用）
        Phase 2: 并行生成 4 个新角色剧本（RateLimiter 控制并发）
        """
        self.console.print("[cyan]正在 expand 原型为完整版本...[/cyan]")

        if not self.state.is_prototype:
            self.console.print("[yellow]当前不是原型，跳过 expand[/yellow]")
            return False

        try:
            from murder_wizard.llm.rate_limit import RateLimiter

            # 读取原型内容
            outline = self.state.outline or ""
            mechanism = (self.session.project_path / "mechanism.md").read_text(encoding="utf-8") if (self.session.project_path / "mechanism.md").exists() else ""
            characters = (self.session.project_path / "characters.md").read_text(encoding="utf-8") if (self.session.project_path / "characters.md").exists() else ""

            # ========== Phase 1: 扩写事件线和信息矩阵 ==========
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=self.console) as progress:
                task = progress.add_task("扩写事件线和信息矩阵...", total=None)

                phase1_prompt = self._build_expand_phase1_prompt(outline, mechanism, characters)
                phase1_response = self._call_llm(
                    phase1_prompt,
                    system="你是一个专业的剧本杀作家，擅长将简化原型扩写为完整剧本。",
                    operation="expand_phase1"
                )

            self._show_cost_warning(phase1_response.cost)

            # ========== Phase 2: 并行生成 4 个新角色剧本 ==========
            self.console.print("[cyan]并行生成新角色剧本（最多2个并发）...[/cyan]")

            # 解析 Phase 1 结果，确定 4 个新角色及其设定
            new_chars_prompt = self._build_new_chars_prompt(phase1_response.content)
            new_chars_response = self._call_llm(
                new_chars_prompt,
                system="你是一个专业的剧本杀作家，擅长从扩写内容中提取角色设定。",
                operation="expand_parse_chars"
            )

            # 解析出新角色列表（从 Phase 1 结果中提取）
            char_names = self._parse_new_character_names(new_chars_response.content, existing_count=2)
            if not char_names:
                # 降级：无法解析时使用单次扩写
                self.console.print("[yellow]无法解析新角色，并发生成跳过，使用单次扩写[/yellow]")
                return self._expand_single_pass(outline, mechanism, characters, phase1_response.content)

            self.console.print(f"[cyan]新角色：{', '.join(char_names)}[/cyan]")

            # 并行生成角色剧本
            limiter = RateLimiter(max_concurrent=2, delay_between_calls=1.0)

            # 构建并行任务：每个新角色一个任务
            tasks = []
            for char_name in char_names:
                tasks.append((
                    char_name,
                    (outline, mechanism, phase1_response.content, char_name),
                    {},
                ))

            def call_char_script(args):
                o, m, p1, name = args
                prompt = self._build_single_char_prompt(o, m, p1, name)
                return self._call_llm(
                    prompt,
                    system="你是一个专业的剧本杀作家，每位角色的剧本都要符合其身份、背景和视角。",
                    operation=f"expand_char_{name}"
                )

            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=self.console) as progress:
                task = progress.add_task("生成角色剧本...", total=None)
                char_results = limiter.run_parallel(tasks, call_char_script)

            # 汇总结果
            total_cost = phase1_response.cost + new_chars_response.cost
            char_contents = []
            for char_name, response in char_results:
                if response is not None:
                    char_contents.append(f"\n\n## {char_name}\n\n{response.content}")
                    total_cost += response.cost
                else:
                    self.console.print(f"[red]角色 {char_name} 生成失败[/red]")

            # ========== 保存结果 ==========
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            if (self.session.project_path / "characters.md").exists():
                (self.session.project_path / "characters.md").rename(
                    self.session.project_path / f"characters.md.proto.{timestamp}"
                )
            if (self.session.project_path / "information_matrix.md").exists():
                (self.session.project_path / "information_matrix.md").rename(
                    self.session.project_path / f"information_matrix.md.proto.{timestamp}"
                )

            # 组装完整角色剧本
            full_script = self._assemble_expanded_script(
                phase1_response.content, char_contents, char_names
            )

            chars_file = self.session.project_path / "characters.md"
            chars_file.write_text(full_script, encoding="utf-8")

            # 保存更新后的信息矩阵（从 Phase 1 结果提取）
            matrix_content = self._extract_matrix_from_phase1(phase1_response.content)
            if matrix_content:
                matrix_file = self.session.project_path / "information_matrix.md"
                matrix_file.write_text(matrix_content, encoding="utf-8")

            self.state.characters = {"raw": full_script}
            self.state.is_prototype = False
            self.session.save(self.state)

            self.console.print(f"[green]expand 完成！[/green]")
            self._show_cost_warning(total_cost)
            return True

        except Exception as e:
            self.console.print(f"[red]expand 失败：{e}[/red]")
            import traceback
            traceback.print_exc()
            return False

    def _build_expand_phase1_prompt(self, outline: str, mechanism: str, characters: str) -> str:
        """构建 expand Phase 1 prompt：扩写事件线和信息矩阵"""
        return f"""将以下原型剧本扩写为完整版本。

原型大纲：
{outline}

原型机制：
{mechanism}

原型角色：
{characters}

Phase 1 任务：
1. 将事件从3条扩写到5-7条，保持原型事件顺序
2. 设计4个新角色的基本设定（背景、阵营、关键秘密）
3. 更新信息矩阵（6人 x 5-7事件）
4. 确定结局和核心冲突

请输出：
- 扩写后的事件列表（按时间顺序）
- 4个新角色的基本设定
- 更新的信息矩阵（Markdown 表格）
- 结局概述

格式：Markdown，清晰分区"""

    def _build_new_chars_prompt(self, phase1_content: str) -> str:
        """构建解析新角色的 prompt"""
        return f"""从以下扩写内容中，列出需要生成剧本的4个新角色名字。

内容：
{phase1_content}

请只输出4个角色名字，每行一个，格式：角色1: 名字
不要输出其他内容。"""

    def _parse_new_character_names(self, content: str, existing_count: int = 2) -> list[str]:
        """从 Phase 1 结果中解析出新角色名字列表"""
        lines = content.strip().split('\n')
        names = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # 跳过 markdown 标题
            if line.startswith('#'):
                continue
            # 尝试提取 "角色X: 名字" 或 "名字" 格式
            if ':' in line:
                name = line.split(':', 1)[1].strip()
            else:
                name = line.strip('-*# ').strip()
            if name and len(name) < 20:
                names.append(name)
            if len(names) >= 4:
                break
        return names[:4]

    def _build_single_char_prompt(self, outline: str, mechanism: str, phase1_content: str, char_name: str) -> str:
        """为单个角色生成剧本的 prompt"""
        return f"""基于以下信息，为角色「{char_name}」生成完整的角色剧本。

原大纲：
{outline}

机制设计：
{mechanism}

扩写内容（Phase 1 结果）：
{phase1_content}

请为「{char_name}」生成：
1. 角色背景故事（200字）
2. 角色在各个事件中的经历（按时间顺序，对应扩写后的5-7个事件）
3. 角色视角的"真相"（该角色认为发生了什么）
4. 角色隐藏的秘密
5. 角色需要隐瞒的信息

格式：Markdown，以 ## {char_name} 开头"""

    def _assemble_expanded_script(self, phase1_content: str, char_contents: list[str], char_names: list[str]) -> str:
        """组装最终的扩写剧本"""
        parts = [phase1_content]
        for content in char_contents:
            parts.append(content)
        return "\n\n".join(parts)

    def _extract_matrix_from_phase1(self, phase1_content: str) -> str | None:
        """从 Phase 1 结果中提取信息矩阵部分"""
        lines = phase1_content.split('\n')
        in_matrix = False
        matrix_lines = []
        for line in lines:
            if '信息矩阵' in line or 'information matrix' in line.lower():
                in_matrix = True
            if in_matrix:
                matrix_lines.append(line)
                # 检测矩阵结束（下一个大标题或非表格行）
                if line.startswith('#') and '信息矩阵' not in line:
                    break
        if matrix_lines:
            return '\n'.join(matrix_lines[:-1]) if matrix_lines[-1].startswith('#') else '\n'.join(matrix_lines)
        return None

    def _expand_single_pass(self, outline: str, mechanism: str, characters: str, phase1_content: str) -> bool:
        """降级路径：无法并发时使用单次 LLM 调用完成 expand"""
        self.console.print("[yellow]使用单次扩写模式[/yellow]")
        try:
            single_prompt = f"""将以下原型剧本扩写为完整6人版本。

原型大纲：
{outline}

原型机制：
{mechanism}

原型角色：
{characters}

Phase 1 扩写内容：
{phase1_content}

请生成完整的角色剧本（6人全部），格式：Markdown。

扩写要求：
1. 角色从2人扩写到6人
2. 事件从3条扩写到5-7条
3. 保持原有角色设定不变
4. 新角色要与原有角色逻辑自洽
"""
            response = self._call_llm(
                single_prompt,
                system="你是一个专业的剧本杀作家，擅长将简化原型扩写为完整剧本。",
                operation="expand_single"
            )

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            if (self.session.project_path / "characters.md").exists():
                (self.session.project_path / "characters.md").rename(
                    self.session.project_path / f"characters.md.proto.{timestamp}"
                )
            if (self.session.project_path / "information_matrix.md").exists():
                (self.session.project_path / "information_matrix.md").rename(
                    self.session.project_path / f"information_matrix.md.proto.{timestamp}"
                )

            chars_file = self.session.project_path / "characters.md"
            chars_file.write_text(response.content, encoding="utf-8")

            self.state.characters = {"raw": response.content}
            self.state.is_prototype = False
            self.session.save(self.state)

            self.console.print(f"[green]expand 完成（单次模式）[/green]")
            self._show_cost_warning(response.cost)
            return True
        except Exception as e:
            self.console.print(f"[red]单次扩写也失败了：{e}[/red]")
            return False


    def run_audit(self) -> bool:
        """完整穿帮审计：基于信息矩阵深度分析所有穿帮问题

        不同于阶段2后自动运行的轻量检查，audit 是独立命令，
        做深度分析，包括：角色x事件矩阵逐格核对、逻辑漏洞、
        阵营矛盾、结局合理性等。
        """
        self.console.print("[cyan]运行完整穿帮审计...[/cyan]")

        characters_file = self.session.project_path / "characters.md"
        matrix_file = self.session.project_path / "information_matrix.md"
        mechanism_file = self.session.project_path / "mechanism.md"

        if not characters_file.exists():
            self.console.print("[red]缺少 characters.md，请先完成阶段2[/red]")
            return False
        if not matrix_file.exists():
            self.console.print("[red]缺少 information_matrix.md，请先完成阶段2[/red]")
            return False

        characters = characters_file.read_text(encoding="utf-8")
        matrix = matrix_file.read_text(encoding="utf-8")
        mechanism = mechanism_file.read_text(encoding="utf-8") if mechanism_file.exists() else ""

        try:
            from rich.progress import Progress, SpinnerColumn, TextColumn

            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=self.console) as progress:
                task = progress.add_task("深度审计中（可能需要几分钟）...", total=None)

                # 第一步：角色x事件逐格检查
                response1 = self._call_llm(
                    self._build_audit_matrix_prompt(characters, matrix),
                    system="你是一个严格的剧本杀穿帮审计员，擅长逐格核对信息矩阵，发现最隐蔽的逻辑矛盾。",
                    operation="audit_matrix_check"
                )

                # 第二步：机制一致性检查
                response2 = self._call_llm(
                    self._build_audit_mechanism_prompt(characters, matrix, mechanism),
                    system="你是一个专业的剧本杀平衡性分析师，检查机制与角色行为的一致性。",
                    operation="audit_mechanism_check"
                )

                # 第三步：结局逻辑验证
                response3 = self._call_llm(
                    self._build_audit_ending_prompt(characters, matrix),
                    system="你是一个严格的剧本杀结局审计员，检查结局是否合理、是否有唯一解。",
                    operation="audit_ending_check"
                )

            # 综合报告
            report = self._compile_audit_report(
                characters, matrix, mechanism,
                response1.content, response2.content, response3.content
            )

            report_file = self.session.project_path / "audit_report.md"
            report_file.write_text(report, encoding="utf-8")

            total_cost = response1.cost + response2.cost + response3.cost
            self._show_cost_warning(total_cost)

            self.console.print(f"[green]审计报告已保存到：{report_file}[/green]")

            # 高亮问题摘要
            issues_found = self._summarize_audit_issues(response1, response2, response3)
            if issues_found > 0:
                self.console.print(f"[yellow]共发现 {issues_found} 个需要关注的问题[/yellow]")
                self.console.print("请仔细阅读 audit_report.md 中的详细分析")
            else:
                self.console.print("[green]✓ 审计通过，未发现明显问题[/green]")

            return True

        except Exception as e:
            self.console.print(f"[red]审计失败：{e}[/red]")
            return False

    def _build_audit_matrix_prompt(self, characters: str, matrix: str) -> str:
        """构建信息矩阵逐格审计 prompt"""
        return f"""你是剧本杀严格审计员。请对以下角色剧本和信息矩阵进行逐格核对审计。

## 任务
对照信息矩阵，逐角色、逐事件检查角色剧本中的描述是否与矩阵一致。

## 重点检查维度
1. **知识边界**：角色是否在某个事件中提及了当时还不知道的信息？
2. **时间线**：角色对事件的描述顺序是否符合矩阵中的时间线？
3. **秘密泄露**：角色的秘密是否被其他角色意外知道（矩阵中不应存在的知识流动）？
4. **视角真实性**：每个角色的"真相"是否与其矩阵中的角色设定一致？

## 角色剧本
{characters}

## 信息矩阵
{matrix}

## 输出格式
对每位角色输出：
### 角色X：[角色名]
- 问题列表（如无问题写"无"）
- 每个问题格式：「在事件Y中，角色A不应该知道/说出Z，因为...」
- 严重程度：P1（致命穿帮）/ P2（逻辑漏洞）/ P3（轻微不一致）

最后给出总体评估：穿帮数量、是否建议上线。
"""

    def _build_audit_mechanism_prompt(self, characters: str, matrix: str, mechanism: str) -> str:
        """构建机制一致性审计 prompt"""
        return f"""你是剧本杀平衡性分析师。请检查角色行为是否符合机制设计。

## 任务
检查角色剧本中的行为是否与机制设计一致，是否存在机制漏洞。

## 机制设计
{mechanism}

## 角色剧本
{characters}

## 信息矩阵
{matrix}

## 重点检查
1. 阵营设定是否自洽？阵营技能是否与角色背景匹配？
2. 投票机制是否有漏洞？是否存在"必定获胜"的策略？
3. 搜证顺序是否影响结果？是否存在死路（无论怎么选都必输）？
4. 关键事件是否有多解？还是只有一个正确解？
5. 是否有角色在任何情况下都无法获胜（平衡性问题）？

## 输出格式
- 机制漏洞列表（P1/P2/P3）
- 平衡性问题
- 修改建议
"""

    def _build_audit_ending_prompt(self, characters: str, matrix: str) -> str:
        """构建结局合理性审计 prompt"""
        return f"""你是剧本杀结局审计员。请检查结局设计是否合理。

## 任务
验证剧本结局是否符合逻辑、是否有唯一解、是否让所有玩家都有参与感。

## 角色剧本
{characters}

## 信息矩阵
{matrix}

## 重点检查
1. 结局是否唯一？还是存在多个可能的结局？
2. 触发结局的条件是否在游戏中可推理（不是随机）？
3. 是否有角色在结局中"消失"（没有戏份）？
4. 真相是否在游戏过程中可被发现？还是只能靠DM陈述？
5. 结局是否给玩家留下深刻印象（记忆点）？

## 输出格式
- 结局分析
- 问题列表
- 优化建议
"""

    def _compile_audit_report(self, characters: str, matrix: str, mechanism: str,
                               matrix_result: str, mechanism_result: str, ending_result: str) -> str:
        """编译完整审计报告"""
        return f"""# 剧本杀完整审计报告

> 由 murder-wizard audit 自动生成
> 生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}

## 一、信息矩阵逐格审计

{matrix_result}

---

## 二、机制一致性审计

{mechanism_result}

---

## 三、结局合理性审计

{ending_result}

---

## 四、综合评估

请根据以上三部分审计结果，综合评估：

1. **是否可以上线**：是/否/需要修改
2. **必须修复的问题**：（P1级别）
3. **建议修复的问题**：（P2级别）
4. **可选优化**：（P3级别）

## 五、修复优先级

| 优先级 | 问题 | 修复方式 |
|--------|------|---------|
| P1 | | |
| P2 | | |
| P3 | | |

---

*本报告由 AI 自动生成，仅供参考。实际体验测试仍不可替代。*
"""

    def _summarize_audit_issues(self, r1: LLMResponse, r2: LLMResponse, r3: LLMResponse) -> int:
        """从三个审计结果中统计问题数量"""
        total = 0
        for response in [r1, r2, r3]:
            content = response.content.lower()
            # 简单统计 P1/P2/P3 出现次数
            for _ in range(content.count("p1")):
                total += 1
            for _ in range(content.count("p2")):
                total += 1
            for _ in range(content.count("p3")):
                total += 1
        return total

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
        """构建测试指南 prompt"""
        return f"""基于以下角色剧本和机制设计，生成测试指南。

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
"""

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
        return f"""基于以下剧本信息，生成商业化方案。

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

        # 生成剧本 PDF
        try:
            script_pdf = generator.generate_script_pdf()
            self.console.print(f"[green]剧本 PDF 已生成：{script_pdf}[/green]")
        except Exception as e:
            self.console.print(f"[yellow]剧本 PDF 生成失败：{e}[/yellow]")

        # 生成线索卡 PDF
        try:
            clue_pdf = generator.generate_clue_cards()
            self.console.print(f"[green]线索卡 PDF 已生成：{clue_pdf}[/green]")
        except Exception as e:
            self.console.print(f"[yellow]线索卡 PDF 生成失败：{e}[/yellow]")

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
        return f"""基于以下剧本信息，生成宣发内容。

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
        return f"""基于以下剧本信息，生成社区运营方案。

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

