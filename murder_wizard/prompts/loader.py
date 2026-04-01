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
    # Layer 1 — 机制设计
    # ──────────────────────────────────────────────────────────────────

    def mechanism_design(self, **variables) -> str:
        """Layer 1：机制设计 prompt（mechanism.md 输出）."""
        return self.render("01_mechanism_design.md", **variables)

    # ──────────────────────────────────────────────────────────────────
    # Layer 2 — 剧本创作（类型化）
    # ──────────────────────────────────────────────────────────────────

    # 类型 → 模板映射
    _STAGE2_TEMPLATE_MAP = {
        "emotion": "02_emotion_script.md",
        "reasoning": "02_reasoning_script.md",
        "fun": "02_fun_script.md",
        "horror": "02_horror_script.md",
        "mechanic": "02_mechanic_script.md",
    }

    _STAGE3_TEMPLATE_MAP = {
        "emotion": "03_emotion_images.md",
        "reasoning": "03_reasoning_images.md",
        "fun": "03_fun_images.md",
        "horror": "03_horror_images.md",
        "mechanic": "03_mechanic_images.md",
    }

    _STAGE4_TEMPLATE_MAP = {
        "emotion": "04_emotion_testing.md",
        "reasoning": "04_reasoning_testing.md",
        "fun": "04_fun_testing.md",
        "horror": "04_horror_testing.md",
        "mechanic": "04_mechanic_testing.md",
    }

    _STAGE5_TEMPLATE_MAP = {
        "emotion": "05_emotion_marketing.md",
        "reasoning": "05_reasoning_marketing.md",
        "fun": "05_fun_marketing.md",
        "horror": "05_horror_marketing.md",
        "mechanic": "05_mechanic_marketing.md",
    }

    def _type_template(self, story_type: str, template_map: dict) -> str:
        """根据 story_type 获取对应的模板文件."""
        return template_map.get(story_type, template_map.get("mechanic"))

    def stage2_script(self, **variables) -> str:
        """Layer 2：剧本创作（类型化模板）."""
        story_type = variables.get("story_type", "mechanic")
        template = self._type_template(story_type, self._STAGE2_TEMPLATE_MAP)
        return self.render(template, **variables)

    def stage3_images(self, **variables) -> str:
        """Layer 3：视觉物料（类型化模板）."""
        story_type = variables.get("story_type", "mechanic")
        template = self._type_template(story_type, self._STAGE3_TEMPLATE_MAP)
        return self.render(template, **variables)

    def stage4_test(self, **variables) -> str:
        """Layer 4：用户测试（类型化模板）."""
        story_type = variables.get("story_type", "mechanic")
        template = self._type_template(story_type, self._STAGE4_TEMPLATE_MAP)
        return self.render(template, **variables)

    def stage5_marketing(self, **variables) -> str:
        """Layer 5：商业化（类型化模板）."""
        story_type = variables.get("story_type", "mechanic")
        template = self._type_template(story_type, self._STAGE5_TEMPLATE_MAP)
        return self.render(template, **variables)

    # 向下兼容的别名（仍然使用通用模板）
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
    def system_mechanism_designer() -> str:
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

    @staticmethod
    def system_script_writer(story_type: str = "mechanic") -> str:
        """系统提示词：剧本作家（类型化）"""
        prompts = {
            "emotion": """你是一个专业的剧本杀情感本作家。

擅长设计：
1. 细腻的情感弧线（角色从开场到结局的情绪变化）
2. 沉浸式内心独白（让玩家真正代入角色）
3. 两难情感抉择（让玩家在情感上难以取舍）
4. 关系动态变化（从恨到爱、从信任到背叛）
5. 让人印象深刻的关键台词和金句

你创作的角色剧本：
- 情感铺垫充分，不突兀
- 给玩家留想象空间，不过度解释
- 秘密和谎言服务于情感冲突
- 每对关系都有情感历史和动态变化""",
            "reasoning": """你是一个专业的剧本杀推理本作家。

擅长设计：
1. 严谨的证据链（每个证据都有来源和证明内容）
2. 公平的信息分发（每个玩家有同等获取线索的机会）
3. 多路径验证（关键证据不只一个来源）
4. 逻辑严密的推理过程（不跳步，有迹可循）
5. 合理的干扰项（让玩家能排除但需要思考）

你创作的角色剧本：
- 时间线精确，空间关系清晰
- 凶手的策略合理，不是随机杀人
- 不在场证明经得起推敲
- 自我辩护有逻辑漏洞供玩家反驳""",
            "fun": """你是一个专业的剧本杀欢乐本作家。

擅长设计：
1. 鲜明的喜剧人设（核心笑点、反差萌）
2. 自然产生的误会和反转（不尴尬）
3. 即兴发挥空间（玩家可以选择参与程度）
4. 社交碰撞点（开场5分钟内的互动）
5. 专属笑点（每个角色都有独特的笑料来源）

你创作的角色剧本：
- 台词有即兴空间，不僵硬
- 误会自然产生，不刻意
- 社交定位清晰，适合群体互动
- 玩家可以选择表演深度""",
            "horror": """你是一个专业的剧本杀恐怖本作家。

擅长设计：
1. 心理压迫感（让玩家真正感到紧张）
2. 渐进式恐惧升级（铺垫充分，爆发有力）
3. 留白艺术（想象力比直接描写更可怕）
4. 悬念结构（分步揭示，维持好奇心）
5. 恐怖氛围营造（不过于直白）

你创作的角色剧本：
- 氛围铺垫充分，不上来就吓人
- 恐怖元素服务故事，不脱离
- 留白给玩家想象空间
- 恐惧根源和心理弱点清晰""",
            "mechanic": """你是一个专业的剧本杀机制本作家。

擅长设计：
1. 策略性角色行动（每个角色都有独特策略）
2. 阵营对抗和胜负判定机制
3. 平衡性（各阵营都有获胜机会）
4. 信息优势和生存能力设计
5. 翻盘机制（落后时也有逆转可能）

你创作的角色剧本：
- 阵营归属清晰，策略选择多样
- 证据与机制相互配合
- 没有必定胜利的策略组合
- 投票/淘汰机制防止一边倒""",
        }
        return prompts.get(story_type, prompts["mechanic"])

    @staticmethod
    def system_visual_designer(story_type: str = "mechanic") -> str:
        """系统提示词：视觉设计师（类型化）"""
        prompts = {
            "emotion": """你是一个专业的AI图像提示词工程师，专注于情感本视觉风格。

擅长创作：
1. 情感场景图（关键情感时刻的视觉化）
2. 氛围感强烈的情感画面（不张扬但有感染力）
3. 角色情感表达（通过表情和姿态传达内心）
4. 柔和但有层次的色调（符合情感基调）

你的提示词要：
- 描述具体的情感氛围而非抽象概念
- 包含角色的情感状态和肢体语言
- 光线和色调服务于情感表达
- 给AI足够的创作空间""",
            "reasoning": """你是一个专业的AI图像提示词工程师，专注于推理本视觉风格。

擅长创作：
1. 线索和证据的视觉呈现
2. 场景空间关系图
3. 时间线可视化
4. 逻辑推理过程图解

你的提示词要：
- 清晰展示空间布局和时间关系
- 证据和线索要有视觉标识
- 保持逻辑严谨性
- 适合证据卡和线索卡设计""",
            "fun": """你是一个专业的AI图像提示词工程师，专注于欢乐本视觉风格。

擅长创作：
1. 喜剧人设形象图
2. 社交场景互动图
3. 夸张但不低俗的表情包风格
4. 角色反差萌形象

你的提示词要：
- 活泼明亮的色调
- 夸张的表情和肢体语言
- 角色特点鲜明易辨认
- 有喜剧感但不尴尬""",
            "horror": """你是一个专业的AI图像提示词工程师，专注于恐怖本视觉风格。

擅长创作：
1. 恐怖氛围场景（不过于直白）
2. 心理压迫感画面
3. 留白式恐惧表达
4. 悬念感强烈的构图

你的提示词要：
- 通过阴影和色调营造不安感
- 留白给想象力空间
- 不过于血腥或直白
- 暗示比展示更可怕""",
            "mechanic": """你是一个专业的AI图像提示词工程师，专注于机制本视觉风格。

擅长创作：
1. 角色功能定位图
2. 游戏流程和阶段图
3. 阵营分布可视化
4. 胜负状态展示图

你的提示词要：
- 清晰展示机制和规则
- 阵营颜色区分明确
- 适合作为游戏物料
- 策略感强烈""",
        }
        return prompts.get(story_type, prompts["mechanic"])

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
    def system_test_designer(story_type: str = "mechanic") -> str:
        """系统提示词：测试设计师（类型化）"""
        prompts = {
            "emotion": """你是一个专业的剧本杀情感本测试设计师。

测试重点：
1. 情感共鸣测试（玩家是否有情感投入）
2. 角色代入感（玩家是否理解角色动机）
3. 情感抉择体验（两难选择是否有意义）
4. 结局情感落点（是否有余韵）

你设计的测试要：
- 关注情感体验而非机制
- 评估角色关系的深度
- 检验情感铺垫是否充分
- 收集玩家的情感反馈""",
            "reasoning": """你是一个专业的剧本杀推理本测试设计师。

测试重点：
1. 线索充足性（线索是否足够推理）
2. 逻辑自洽性（推理过程是否有漏洞）
3. 难度曲线（是否循序渐进）
4. 干扰项有效性（是否能被合理排除）

你设计的测试要：
- 评估推理过程的完整性
- 检验证据链的闭合性
- 测试公平性（是否所有玩家都有机会）
- 收集推理时间数据""",
            "fun": """你是一个专业的剧本杀欢乐本测试设计师。

测试重点：
1. 社交活跃度（玩家是否积极互动）
2. 即兴发挥空间（玩家是否愿意表演）
3. 误会反转效果（笑点是否自然）
4. 群体互动体验（是否适合团体）

你设计的测试要：
- 关注社交活跃度而非胜负
- 评估即兴表演的空间
- 检验误会反转的自然度
- 收集玩家参与度数据""",
            "horror": """你是一个专业的剧本杀恐怖本测试设计师。

测试重点：
1. 恐惧阈值测试（是否太恐怖/不够恐怖）
2. 氛围持续性（恐怖感是否贯穿始终）
3. 悬念效果（玩家是否想继续探索）
4. 留白接受度（玩家是否喜欢暗示风格）

你设计的测试要：
- 关注恐怖氛围而非jump scare
- 评估恐惧的渐进式升级
- 检验留白是否有效
- 收集玩家的恐惧反馈""",
            "mechanic": """你是一个专业的剧本杀机制本测试设计师。

测试重点：
1. 平衡性测试（各阵营是否均等）
2. 策略多样性（是否有多种有效策略）
3. 翻盘机制（落后方是否有逆转可能）
4. 节奏控制（游戏时间是否合适）

你设计的测试要：
- 关注策略平衡而非剧情
- 评估各阵营的获胜概率
- 检验翻盘机制的公平性
- 收集游戏时间数据""",
        }
        return prompts.get(story_type, prompts["mechanic"])

    @staticmethod
    def system_commercial_consultant(story_type: str = "mechanic") -> str:
        """系统提示词：商业化顾问（类型化）"""
        prompts = {
            "emotion": """你是一个专业的剧本杀情感本商业化顾问，熟悉国内剧本杀市场价格、成本和渠道。

擅长：
1. 情感共鸣营销（打感情牌）
2. 角色CP炒作（粉丝经济）
3. 沉浸式体验包装
4. 情感本定价策略（通常略高）

你提供的方案要强调情感体验和角色代入，设计情感向宣发内容，突出"哭过"、"破防"等关键词。""",
            "reasoning": """你是一个专业的剧本杀推理本商业化顾问，熟悉国内剧本杀市场价格、成本和渠道。

擅长：
1. 烧脑挑战营销（打智商牌）
2. 公平性保证宣传
3. 推理难度分级
4. 推理本定价策略（中高价位）

你提供的方案要强调逻辑严密和公平性，设计挑战向宣发内容，突出"烧脑"、"硬核"等关键词。""",
            "fun": """你是一个专业的剧本杀欢乐本商业化顾问，熟悉国内剧本杀市场价格、成本和渠道。

擅长：
1. 社交娱乐营销（打欢乐牌）
2. 聚会团建推荐
3. 搞笑片段传播
4. 欢乐本定价策略（亲民价位）

你提供的方案要强调社交娱乐和放松，设计欢乐向宣发内容，突出"笑死"、"玩得嗨"等关键词。""",
            "horror": """你是一个专业的剧本杀恐怖本商业化顾问，熟悉国内剧本杀市场价格、成本和渠道。

擅长：
1. 惊悚体验营销（打刺激牌）
2. 氛围沉浸式包装
3. 恐怖程度分级提示
4. 恐怖本定价策略（中高价位）

你提供的方案要强调惊悚氛围和沉浸感，设计恐怖向宣发内容，突出"吓人"、"刺激"等关键词。""",
            "mechanic": """你是一个专业的剧本杀机制本商业化顾问，熟悉国内剧本杀市场价格、成本和渠道。

擅长：
1. 策略博弈营销（打策略牌）
2. 阵营对抗宣传
3. 重玩性强调
4. 机制本定价策略（中高价位）

你提供的方案要强调策略性和对抗性，设计策略向宣发内容，突出"烧脑"、"策略"、"阵营对抗"等关键词。""",
        }
        return prompts.get(story_type, prompts["mechanic"])

    @staticmethod
    def system_promo_writer() -> str:
        return """你是一个专业的剧本杀宣发文案专家，熟悉B站、小红书、公众号的文案风格。"""

    @staticmethod
    def system_community_operations() -> str:
        return """你是一个专业的剧本杀社群运营专家，熟悉玩家社群建设和扩展包开发。"""

    @staticmethod
    def system_outline_generator() -> str:
        return """你是一个专业的剧本杀作家，擅长创作有趣、平衡的剧本杀游戏。"""
