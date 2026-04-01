"""Prompt 模板加载器 — 从包内 prompts/ 目录加载并渲染模板."""
import re
from importlib import resources
from string import Template
from typing import Optional


class PromptLoader:
    """加载 murder_wizard.prompts 包内的 markdown 模板，并进行变量替换."""

    def __init__(self):
        self._cache: dict[str, str] = {}

    def _load_raw(self, filename: str) -> str:
        """从包内加载原始模板内容（带缓存）."""
        if filename in self._cache:
            return self._cache[filename]

        try:
            import murder_wizard.prompts as pkg

            file_ref = resources.files(pkg).joinpath(filename)
            content = file_ref.read_text(encoding="utf-8")
            self._cache[filename] = content
            return content
        except Exception as e:
            raise FileNotFoundError(
                f"无法加载 prompt 模板 {filename!r}，"
                f"请确认 murder_wizard/prompts/ 目录存在且包含该文件"
            ) from e

    def _prepare_vars(self, variables: dict) -> dict:
        """预处理变量：布尔值转字符串，添加衍生变量."""
        vars = dict(variables)
        # is_prototype → 原型/完整 模式标签
        if "is_prototype" in vars:
            is_proto = vars["is_prototype"]
            vars["mode_label"] = "原型模式" if is_proto else "完整模式"
            vars["is_prototype_bool"] = "true" if is_proto else "false"
        # char_count
        if "char_count" not in vars:
            vars["char_count"] = 2 if vars.get("is_prototype") else 6
        # event_count
        if "event_count" not in vars:
            vars["event_count"] = 3 if vars.get("is_prototype") else 7
        # word_count_a
        if "word_count_a" not in vars:
            vars["word_count_a"] = "800-1200" if vars.get("is_prototype") else "1500-2500"
        # fill_rules
        if "fill_rules" not in vars:
            is_proto = vars.get("is_prototype")
            if is_proto:
                vars["fill_rules"] = (
                    "1. 凶手必须拥有核心事件的关键碎片\n"
                    "2. 至少1个角色对核心事件有[误信]\n"
                    "3. 每个角色至少对1个事件有[疑]状态\n"
                    "4. 2人拼图 = 完整真相"
                )
            else:
                vars["fill_rules"] = (
                    "1. 凶手（R1）必须拥有[知]核心事件的关键碎片\n"
                    "2. 至少2个角色对核心事件有[误信]\n"
                    "3. 至少1个角色在核心事件前[隐瞒]关键信息\n"
                    "4. 每个角色至少对2个事件有[疑]状态\n"
                    "5. 没有任何角色拥有全部真相——拼图完整不等于任何单角色知道全部"
                )
        # matrix_table（默认空白矩阵）
        if "matrix_table" not in vars:
            cc = vars.get("char_count", 6)
            ec = vars.get("event_count", 7)
            header = "| | " + " | ".join([f"R{i+1}" for i in range(cc)]) + " |"
            sep = "|" + "|".join(["---" for _ in range(cc + 1)]) + "|"
            rows = []
            for i in range(ec):
                label = f"E{i+1}" + ("（核心）" if i == ec - 1 else "")
                rows.append(f"| {label} | " + " | ".join(["" for _ in range(cc)]) + " |")
            vars["matrix_table"] = "\n".join([header, sep] + rows)
        return vars

    def render(self, filename: str, json_only: bool = False, **variables) -> str:
        """渲染模板，将 {{variable}} 替换为对应值.

        示例：
            loader.render("01_mechanism_design.md",
                          outline="xxx",
                          story_type="推理本",
                          is_prototype=True)

        Args:
            json_only: 如果为 True，只返回 JSON section，跳过 Markdown 部分。
        """
        template = self._load_raw(filename)
        vars = self._prepare_vars(variables)
        vars["json_only"] = json_only

        def replacer(m):
            key = m.group(1).strip()
            if key in vars:
                val = vars[key]
                return str(val) if val is not None else ""
            return m.group(0)  # 未找到变量保留原样

        result = re.sub(r"\{\{([^}]+)\}\}", replacer, template)

        # Handle conditional blocks: {{#if var}}...{{/if}} and {{#ifnot var}}...{{/ifnot}}
        json_only = vars.get("json_only", False)

        # {{#if json_only}}...{{/if}} — only if json_only is True
        result = re.sub(r"\{\{#if\s+(\w+)\}\}(.*?)\{\{/if\}\}", 
                        lambda m: m.group(2) if vars.get(m.group(1).strip(), False) else "", 
                        result, flags=re.DOTALL)
        # {{#ifnot json_only}}...{{/ifnot}} — only if json_only is False
        result = re.sub(r"\{\{#ifnot\s+(\w+)\}\}(.*?)\{\{/ifnot\}\}",
                        lambda m: m.group(2) if not vars.get(m.group(1).strip(), False) else "",
                        result, flags=re.DOTALL)

        return result

    # ──────────────────────────────────────────────────────────────────
    # Layer 0 — 创意问卷（init 向导）
    # ──────────────────────────────────────────────────────────────────

    def questionnaire(self) -> str:
        """Layer 0：加载创意问卷模板（原始内容，用于 TUI 向导展示）."""
        return self._load_raw("00_guided_questionnaire.md")

    def brief(self, **variables) -> str:
        """Layer 0 输出：brief.md 渲染."""
        return self.render("00_guided_questionnaire.md", **variables)

    # ──────────────────────────────────────────────────────────────────
    # Layer 1 — 类型化设计（根据 story_type 选择模板）
    # ──────────────────────────────────────────────────────────────────

    # 类型→模板映射
    _STAGE1_TEMPLATE_MAP = {
        "emotion": "01_emotion_design.md",
        "reasoning": "01_reasoning_design.md",
        "fun": "01_fun_design.md",
        "horror": "01_horror_design.md",
        "mechanic": "01_mechanism_design.md",
    }

    _SYSTEM_PROMPT_MAP = {
        "emotion": "system_emotion_designer",
        "reasoning": "system_reasoning_designer",
        "fun": "system_fun_designer",
        "horror": "system_horror_designer",
        "mechanic": "system_mechanism_designer",
    }

    def stage1_design(self, **variables) -> str:
        """Layer 1：类型化设计 prompt.

        根据 story_type 自动选择对应模板：
        - emotion    → 01_emotion_design.md（情感本）
        - reasoning  → 01_reasoning_design.md（推理本）
        - fun       → 01_fun_design.md（欢乐本）
        - horror    → 01_horror_design.md（恐怖本）
        - mechanic  → 01_mechanism_design.md（机制本）
        """
        story_type = variables.get("story_type", "mechanic")
        template_name = self._STAGE1_TEMPLATE_MAP.get(story_type, "01_mechanism_design.md")
        return self.render(template_name, **variables)

    def system_stage1_designer(self, story_type: str) -> str:
        """获取阶段1的系统 prompt.

        Args:
            story_type: 故事类型 (emotion/reasoning/fun/horror/mechanic)
        """
        method_name = self._SYSTEM_PROMPT_MAP.get(story_type, "system_mechanism_designer")
        method = getattr(self, method_name, None)
        if method is None:
            return self.system_mechanism_designer()
        return method()

    def mechanism_design(self, **variables) -> str:
        """Layer 1：机制设计 prompt（mechanism.md 输出）.

        注意：mechanic 类型请优先使用 stage1_design()。
        """
        return self.render("01_mechanism_design.md", **variables)

    # ──────────────────────────────────────────────────────────────────
    # Layer 2 — 剧本创作
    # ──────────────────────────────────────────────────────────────────

    def information_matrix(self, **variables) -> str:
        """Layer 2 Q1：信息矩阵生成."""
        return self.render("02_script_generation.md", **variables)

    def character_background(self, **variables) -> str:
        """Layer 2 Q2：角色背景生成."""
        return self.render("02_script_generation.md", **variables)

    def character_script_a(self, **variables) -> str:
        """Layer 2 Q3：a本（阅读本）生成."""
        return self.render("02_script_generation.md", **variables)

    # ──────────────────────────────────────────────────────────────────
    # JSON Truth File generation（inkos-style structured output）
    # ──────────────────────────────────────────────────────────────────

    def information_matrix_json(self, **variables) -> str:
        """Layer 2 Q1：信息矩阵生成 — JSON 格式输出.

        请求 LLM 输出结构化 JSON 而非 Markdown 表格，
        以便后续用 Zod schema 校验和程序化处理。
        """
        return self.render("02_script_generation.md", json_only=True, **variables)

    def character_script_b(self, **variables) -> str:
        """Layer 2 Q4：b本（线索本）生成."""
        return self.render("02_script_generation.md", **variables)

    def dm_manual(self, **variables) -> str:
        """Layer 2 Q5：DM手册生成."""
        return self.render("02_script_generation.md", **variables)

    def ending_expansion(self, **variables) -> str:
        """Layer 2 Q6：结局扩展."""
        return self.render("02_script_generation.md", **variables)

    # ──────────────────────────────────────────────────────────────────
    # Layer 3 — 视觉物料
    # ──────────────────────────────────────────────────────────────────

    def visual_materials(self, **variables) -> str:
        """Layer 3：视觉物料 prompt（image-prompts.md 输出）."""
        return self.render("03_visual_materials.md", **variables)

    # ──────────────────────────────────────────────────────────────────
    # Layer 3 — 穿帮检测
    # ──────────────────────────────────────────────────────────────────

    def consistency_round1(self, **variables) -> str:
        """Layer 3 第一轮：信息矩阵逐格检查."""
        return self.render("04_consistency_check.md", **variables)

    def consistency_round2(self, **variables) -> str:
        """Layer 3 第二轮：机制一致性检查."""
        return self.render("04_consistency_check.md", **variables)

    def consistency_round3(self, **variables) -> str:
        """Layer 3 第三轮：结局合理性检查."""
        return self.render("04_consistency_check.md", **variables)

    def consistency_synthesis(self, **variables) -> str:
        """Layer 3 综合：三轮汇总评估."""
        return self.render("04_consistency_check.md", **variables)

    def consistency_reviser(self, **variables) -> str:
        """Layer 3 修正：Reviser 自动修复 P0/P1 问题."""
        return self.render("05_reviser.md", **variables)

    # ──────────────────────────────────────────────────────────────────
    # 便捷系统 prompt
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def system_emotion_designer() -> str:
        return """你是一个专业的剧本杀情感设计师。

擅长设计：
1. 角色情感弧线和情感冲突
2. 人物关系网络和关系动态
3. 沉浸式情感体验
4. 情感抉择的两难性
5. 情感共鸣点

你设计的情感本要：
- 每个角色都有可共鸣的情感伤口
- 人物关系本身是游戏机制
- 玩家能在游戏中产生真实的情感波动
- 有让人印象深刻的情感高光时刻"""

    @staticmethod
    def system_reasoning_designer() -> str:
        return """你是一个专业的剧本杀推理设计师。

擅长设计：
1. 线索链和逻辑推理
2. 公平性和信息可及性
3. 悬念铺垫和逐步揭露
4. 谜题设计和谜题难度曲线
5. 防杠和引导机制

你设计的推理本要：
- 线索链形成唯一闭合解
- 信息对所有玩家基本对等
- 有足够的干扰项和误导
- 破解真相时有强烈的成就感"""

    @staticmethod
    def system_fun_designer() -> str:
        return """你是一个专业的剧本杀欢乐设计师。

擅长设计：
1. 喜剧人设和笑点设计
2. 社交互动和碰撞机制
3. 反转和意外
4. 阵营对抗和社交博弈
5. 轻松愉快的游戏氛围

你设计的欢乐本要：
- 每个角色本身就是喜剧担当
- 有足够的社交碰撞点
- 玩家能主动创造笑点
- 结局让玩家笑着离开"""

    @staticmethod
    def system_horror_designer() -> str:
        return """你是一个专业的剧本杀恐怖设计师。

擅长设计：
1. 恐怖氛围和心理压迫
2. 悬念营造和未知恐惧
3. 渐进式恐惧升级
4. 角色心理弱点
5. 真相揭露的情感冲击

你设计的恐怖本要：
- 氛围即产品，不是靠jump scare
- 想象力比实际更可怕
- 有喘息空间但不破坏整体恐怖感
- 结局有余味，走出房间后还感到意犹未尽"""

    def system_mechanism_designer(self, story_type: str = "mechanic") -> str:
        """获取类型化的机制设计系统提示词.

        Args:
            story_type: 故事类型 (emotion/reasoning/fun/horror/mechanic)
        """
        dispatch_map = {
            "emotion": self.system_emotion_designer,
            "reasoning": self.system_reasoning_designer,
            "fun": self.system_fun_designer,
            "horror": self.system_horror_designer,
            "mechanic": self.system_mechanic_designer,
        }
        method = dispatch_map.get(story_type, self.system_mechanic_designer)
        return method()

    @staticmethod
    def system_mechanic_designer() -> str:
        return """你是一个专业的剧本杀机制设计师。

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

    def system_script_writer(self, story_type: str = "mechanic") -> str:
        """获取类型化的剧本写作系统提示词.

        Args:
            story_type: 故事类型 (emotion/reasoning/fun/horror/mechanic)
        """
        dispatch_map = {
            "emotion": self.system_script_writer_emotion,
            "reasoning": self.system_script_writer_reasoning,
            "fun": self.system_script_writer_fun,
            "horror": self.system_script_writer_horror,
            "mechanic": self.system_script_writer_mechanic,
        }
        method = dispatch_map.get(story_type, self.system_script_writer_mechanic)
        return method()

    @staticmethod
    def system_script_writer_emotion() -> str:
        return """你是一个专业的剧本杀情感本作家。

擅长设计：
1. 角色情感弧线和成长轨迹
2. 人物关系网络和关系动态
3. 沉浸式情感体验和情感高潮
4. 情感抉择的两难性
5. 角色心理弱点和情感共鸣点

你写作的情感本要：
- 每个角色都有可共鸣的情感伤口
- 人物关系本身是游戏机制
- 玩家能在游戏中产生真实的情感波动
- 有让人印象深刻的情感高光时刻"""

    @staticmethod
    def system_script_writer_reasoning() -> str:
        return """你是一个专业的剧本杀推理本作家。

擅长设计：
1. 线索链和逻辑推理
2. 公平性和信息可及性
3. 悬念铺垫和逐步揭露
4. 角色行为动机的合理性
5. 结局的唯一解和成就感

你写作的推理本要：
- 线索链形成唯一闭合解
- 信息对所有玩家基本对等
- 有足够的干扰项和误导
- 破解真相时有强烈的成就感"""

    @staticmethod
    def system_script_writer_fun() -> str:
        return """你是一个专业的剧本杀欢乐本作家。

擅长设计：
1. 喜剧人设和笑点设计
2. 社交互动和碰撞机制
3. 反转和意外
4. 阵营对抗和社交博弈
5. 轻松愉快的游戏氛围

你写作的欢乐本要：
- 每个角色本身就是喜剧担当
- 有足够的社交碰撞点
- 玩家能主动创造笑点
- 结局让玩家笑着离开"""

    @staticmethod
    def system_script_writer_horror() -> str:
        return """你是一个专业的剧本杀恐怖本作家。

擅长设计：
1. 恐怖氛围和心理压迫
2. 悬念营造和未知恐惧
3. 渐进式恐惧升级
4. 角色心理弱点
5. 真相揭露的情感冲击

你写作的恐怖本要：
- 氛围即产品，不是靠jump scare
- 想象力比实际更可怕
- 有喘息空间但不破坏整体恐怖感
- 结局有余味，走出房间后还感到意犹未尽"""

    @staticmethod
    def system_script_writer_mechanic() -> str:
        return """你是一个专业的剧本杀作家，擅长设计复杂、严谨的角色关系和事件逻辑。"""

    @staticmethod
    def system_visual_designer() -> str:
        return """你是一个专业的视觉设计师，擅长为AI图像生成工具编写精确的提示词。"""

    @staticmethod
    def system_auditor() -> str:
        return """你是一个严格的剧本杀穿帮审计员。简洁输出，只报告发现的问题，不要废话。"""

    @staticmethod
    def system_balance_analyst() -> str:
        return """你是一个专业的剧本杀平衡性分析师，检查机制与角色行为的一致性。"""

    @staticmethod
    def system_ending_auditor() -> str:
        return """你是一个严格的剧本杀结局审计员，检查结局是否合理、是否有唯一解。"""

    @staticmethod
    def system_test_designer() -> str:
        return """你是一个专业的剧本杀测试设计师，擅长设计用户体验测试流程，发现游戏平衡性问题。"""

    @staticmethod
    def system_commercial_consultant() -> str:
        return """你是一个专业的剧本杀商业化顾问，熟悉国内剧本杀市场价格、成本和渠道。"""

    @staticmethod
    def system_promo_writer() -> str:
        return """你是一个专业的剧本杀宣发文案专家，熟悉B站、小红书、公众号的文案风格。"""

    @staticmethod
    def system_community_operations() -> str:
        return """你是一个专业的剧本杀社群运营专家，熟悉玩家社群建设和扩展包开发。"""

    @staticmethod
    def system_outline_generator() -> str:
        return """你是一个专业的剧本杀作家，擅长创作有趣、平衡的剧本杀游戏。"""
