"""Phase runner - executes each stage's LLM workflow."""
import json
import time
import signal
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from murder_wizard.wizard.session import SessionManager
from murder_wizard.wizard.state_machine import MurderWizardState, Stage
from murder_wizard.llm.client import create_llm_adapter, LLMResponse


class PhaseRunner:
    """阶段执行器"""

    def __init__(self, session: SessionManager, state: MurderWizardState, console: Console):
        self.session = session
        self.state = state
        self.console = console
        self.llm = None
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
        """调用 LLM，带重试和成本记录"""
        try:
            response = self.llm.complete(prompt, system=system)
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
        """expand：将原型扩写为完整版本

        基于已有内容，扩写到完整的6人+5-7事件
        """
        self.console.print("[cyan]正在 expand 原型为完整版本...[/cyan]")

        if not self.state.is_prototype:
            self.console.print("[yellow]当前不是原型，跳过 expand[/yellow]")
            return False

        try:
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=self.console) as progress:
                task = progress.add_task("expand 扩写中...", total=None)

                # 读取原型内容
                outline = self.state.outline or ""
                mechanism = (self.session.project_path / "mechanism.md").read_text(encoding="utf-8") if (self.session.project_path / "mechanism.md").exists() else ""
                characters = (self.session.project_path / "characters.md").read_text(encoding="utf-8") if (self.session.project_path / "characters.md").exists() else ""

                expand_prompt = f"""将以下原型剧本扩写为完整版本：

原型大纲：
{outline}

原型机制：
{mechanism}

原型角色：
{characters}

扩写要求：
1. 角色从2人扩写到6人
2. 事件从3条扩写到5-7条
3. 保持原有角色设定不变
4. 新角色要与原有角色逻辑自洽
5. 更新信息矩阵
6. 更新角色剧本

格式：Markdown
"""

                response = self._call_llm(
                    expand_prompt,
                    system="你是一个专业的剧本杀作家，擅长将简化原型扩写为完整剧本。",
                    operation="expand"
                )

            # 备份原文件
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            if (self.session.project_path / "characters.md").exists():
                (self.session.project_path / "characters.md").rename(
                    self.session.project_path / f"characters.md.proto.{timestamp}"
                )
            if (self.session.project_path / "information_matrix.md").exists():
                (self.session.project_path / "information_matrix.md").rename(
                    self.session.project_path / f"information_matrix.md.proto.{timestamp}"
                )

            # 保存新文件
            chars_file = self.session.project_path / "characters.md"
            chars_file.write_text(response.content, encoding="utf-8")

            self.state.characters = {"raw": response.content}
            self.state.is_prototype = False
            self.session.save(self.state)

            self.console.print(f"[green]expand 完成！[/green]")
            self._show_cost_warning(response.cost)
            return True

        except Exception as e:
            self.console.print(f"[red]expand 失败：{e}[/red]")
            return False

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

