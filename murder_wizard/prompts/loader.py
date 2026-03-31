"""Prompt template loader with type-specific support."""

from pathlib import Path
from typing import Dict, Any, List

# Default templates
_DEFAULT_TEMPLATE_DIR = Path(__file__).parent

# Stage 1 templates (机制设计)
_STAGE1_TEMPLATE_MAP = {
    "emotion": "01_emotion_mechanism.md",
    "reasoning": "01_reasoning_mechanism.md",
    "fun": "01_fun_mechanism.md",
    "horror": "01_horror_mechanism.md",
    "mechanic": "01_mechanic_mechanism.md",
}

# Stage 2 templates (角色剧本)
_STAGE2_TEMPLATE_MAP = {
    "emotion": "02_emotion_script.md",
    "reasoning": "02_reasoning_script.md",
    "fun": "02_fun_script.md",
    "horror": "02_horror_script.md",
    "mechanic": "02_mechanic_script.md",
}

# Stage 3 templates (图像提示词)
_STAGE3_TEMPLATE_MAP = {
    "emotion": "03_emotion_images.md",
    "reasoning": "03_reasoning_images.md",
    "fun": "03_fun_images.md",
    "horror": "03_horror_images.md",
    "mechanic": "03_mechanic_images.md",
}

# Stage 4 templates (测试指南)
_STAGE4_TEMPLATE_MAP = {
    "emotion": "04_emotion_testing.md",
    "reasoning": "04_reasoning_testing.md",
    "fun": "04_fun_testing.md",
    "horror": "04_horror_testing.md",
    "mechanic": "04_mechanic_testing.md",
}

# Stage 5 templates (商业化)
_STAGE5_TEMPLATE_MAP = {
    "emotion": "05_emotion_marketing.md",
    "reasoning": "05_reasoning_marketing.md",
    "fun": "05_fun_marketing.md",
    "horror": "05_horror_marketing.md",
    "mechanic": "05_mechanic_marketing.md",
}

# 质量门禁：每个阶段完成后的自检清单
QUALITY_GATES = {
    1: [
        "机制设计是否完整覆盖所有角色？",
        "核心机制是否有足够的深度和亮点？",
        "机制是否与故事类型匹配？",
        "是否有明显的逻辑漏洞或自相矛盾？",
    ],
    2: [
        "每个角色是否有清晰的动机和背景？",
        "角色之间的关系是否清晰有深度？",
        "剧本是否有足够的戏剧冲突？",
        "关键情节点是否有良好的铺垫？",
    ],
    3: [
        "图像提示词是否足够具体明确？",
        "是否覆盖了所有关键场景和角色？",
        "视觉风格是否与故事基调一致？",
        "是否有足够的创意和独特性？",
    ],
    4: [
        "测试指南是否覆盖了所有关键体验点？",
        "问题设计是否能有效评估玩家体验？",
        "是否有足够的测试维度？",
        "测试结果是否能指导改进？",
    ],
    5: [
        "营销方案是否有明确的差异化定位？",
        "目标受众分析是否准确？",
        "推广渠道是否与受众匹配？",
        "ROI预测是否合理可执行？",
    ],
}

# 类型特性清单：用于质量检验
TYPE_CHECKLIST = {
    "emotion": ["情感弧线", "角色成长", "情感高光", "关系动态", "抉择两难"],
    "reasoning": ["证据链完整", "逻辑自洽", "公平性", "反转合理", "线索交织"],
    "fun": ["笑点分布", "社交碰撞", "即兴空间", "误会自然", "角色组合"],
    "horror": ["氛围铺垫", "恐惧升级", "悬念营造", "留白艺术", "真相揭示"],
    "mechanic": ["阵营平衡", "策略深度", "翻盘机制", "技能设计", "博弈节点"],
}


class PromptLoader:
    """Loads and renders prompt templates with type-specific support."""

    def __init__(self, template_dir: Path = None):
        self.template_dir = template_dir or _DEFAULT_TEMPLATE_DIR

    def render(self, template_name: str, **variables) -> str:
        """Render a template with variables."""
        template_path = self.template_dir / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        content = template_path.read_text(encoding="utf-8")

        # Replace placeholders
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            content = content.replace(placeholder, str(value))

        return content

    def stage1_design(self, **variables) -> str:
        """Load Stage 1 design prompt for story type."""
        story_type = variables.get("story_type", "mechanic")
        template_name = _STAGE1_TEMPLATE_MAP.get(story_type, "01_mechanic_mechanism.md")
        return self.render(template_name, **variables)

    def stage2_script(self, **variables) -> str:
        """Load Stage 2 script prompt for story type."""
        story_type = variables.get("story_type", "mechanic")
        template_name = _STAGE2_TEMPLATE_MAP.get(story_type, "02_mechanic_script.md")
        return self.render(template_name, **variables)

    def stage3_image(self, **variables) -> str:
        """Load Stage 3 image prompt for story type."""
        story_type = variables.get("story_type", "mechanic")
        template_name = _STAGE3_TEMPLATE_MAP.get(story_type, "03_mechanic_images.md")
        return self.render(template_name, **variables)

    def stage4_testing(self, **variables) -> str:
        """Load Stage 4 testing prompt for story type."""
        story_type = variables.get("story_type", "mechanic")
        template_name = _STAGE4_TEMPLATE_MAP.get(story_type, "04_mechanic_testing.md")
        return self.render(template_name, **variables)

    def stage5_marketing(self, **variables) -> str:
        """Load Stage 5 marketing prompt for story type."""
        story_type = variables.get("story_type", "mechanic")
        template_name = _STAGE5_TEMPLATE_MAP.get(story_type, "05_mechanic_marketing.md")
        return self.render(template_name, **variables)

    def get_quality_gate(self, stage: int) -> List[str]:
        """Get quality gate checklist for a stage."""
        return QUALITY_GATES.get(stage, [])

    def get_type_checklist(self, story_type: str) -> List[str]:
        """Get type-specific quality checklist."""
        return TYPE_CHECKLIST.get(story_type, [])

    def _build_verification_section(self, stage: int, story_type: str) -> str:
        """Build verification section for output."""
        gates = self.get_quality_gate(stage)
        type_checks = self.get_type_checklist(story_type)

        section = "\n\n## 自检清单 (完成输出前请逐项确认)\n\n"
        section += "### 通用质量门禁\n"
        for i, gate in enumerate(gates, 1):
            section += f"- [ ] {gate}\n"

        if type_checks:
            section += f"\n### {story_type.upper()} 类型特性检查\n"
            for check in type_checks:
                section += f"- [ ] 包含{check}\n"

        section += "\n### 输出格式要求\n"
        section += "- [ ] 使用清晰的层级标题\n"
        section += "- [ ] 关键信息用加粗标注\n"
        section += "- [ ] 列表项使用一致的格式\n"
        section += "- [ ] 避免冗余描述，直击重点\n"

        return section

    def system_stage1_designer(self, story_type: str) -> str:
        """Get system prompt for Stage 1 designer based on story type.

        Inspired by Claude Code's progressive harness pattern:
        - Clear role definition
        - Specific output format requirements
        - Quality gate checkpoints
        - Type-specific expertise emphasis
        """
        base_prompt = f"""你是一个专业的剧本杀{self._get_type_name(story_type)}设计师。

## 你的核心能力
{self._get_designer_expertise(story_type)}

## 工作原则
1. **完整性**：确保机制设计覆盖所有角色和场景
2. **一致性**：机制与故事基调高度匹配
3. **可玩性**：设计要有趣味性和重复可玩价值
4. **平衡性**：多方博弈要有公平性

## 输出要求
- 每个角色必须有明确的机制定位
- 核心机制要有独特的记忆点
- 辅助机制要服务于核心机制
- 预留扩展空间

## 验证标准
完成设计后，请确认：
- 机制是否能支撑完整的游戏体验？
- 各角色是否有足够的策略选择？
- 是否有明确的胜负判定标准？
"""
        return base_prompt

    def system_stage2_writer(self, story_type: str) -> str:
        """Get system prompt for Stage 2 writer based on story type."""
        base_prompt = f"""你是一个专业的剧本杀{self._get_type_name(story_type)}作家。

## 你的核心能力
{self._get_writer_expertise(story_type)}

## 工作原则
1. **沉浸感**：让玩家完全代入角色
2. **戏剧性**：冲突要有张力，节奏要紧凑
3. **个性化**：每个角色要有独特的语言风格和行为逻辑
4. **留白**：给玩家想象和即兴的空间

## 输出要求
- 每个角色剧本要有独立的视角和秘密
- 对话要符合角色性格和背景
- 情感/冲突点要有明确的触发机制
- 关键线索要有适当的隐藏和揭示时机

## 验证标准
完成剧本后，请确认：
- 玩家能否通过剧本理解自己的角色？
- 角色之间是否有足够的互动点？
- 关键情节点是否有足够的铺垫？
- 剧本长度是否适合游戏时长？
"""
        return base_prompt

    def system_stage3_artist(self, story_type: str) -> str:
        """Get system prompt for Stage 3 artist based on story type."""
        base_prompt = f"""你是一个专业的剧本杀{self._get_type_name(story_type)}美术指导。

## 你的核心能力
{self._get_artist_expertise(story_type)}

## 工作原则
1. **一致性**：视觉风格要与故事基调完全匹配
2. **功能性**：图像要服务于游戏体验
3. **创意性**：要有独特的视觉记忆点
4. **可执行性**：提示词要能被AI图像生成器理解

## 输出要求
- 每个图像提示词要包含：场景/角色/氛围/构图
- 视觉风格描述要具体（色调/光影/视角）
- 关键道具和元素要明确标注
- 留出AI创作的空间

## 验证标准
完成提示词后，请确认：
- 提示词是否足够具体可执行？
- 视觉风格是否统一协调？
- 是否覆盖了所有关键场景？
- 图像是否能辅助叙事？
"""
        return base_prompt

    def system_stage4_tester(self, story_type: str) -> str:
        """Get system prompt for Stage 4 tester based on story type."""
        base_prompt = f"""你是一个专业的剧本杀{self._get_type_name(story_type)}测试师。

## 你的核心能力
{self._get_tester_expertise(story_type)}

## 工作原则
1. **玩家视角**：从玩家体验出发设计测试
2. **全面性**：覆盖所有关键体验维度
3. **可操作性**：测试问题要具体可执行
4. **改进导向**：测试结果要能指导优化

## 输出要求
- 每项测试要有明确的评估标准
- 问题设计要能引发真实反馈
- 要考虑不同类型玩家的体验差异
- 提供定量和定性结合的评估方式

## 验证标准
完成测试指南后，请确认：
- 是否覆盖了核心体验点？
- 测试问题是否能得到有效反馈？
- 是否考虑了边界情况和异常处理？
- 测试结果是否能指导改进？
"""
        return base_prompt

    def system_stage5_marketer(self, story_type: str) -> str:
        """Get system prompt for Stage 5 marketer based on story type."""
        base_prompt = f"""你是一个专业的剧本杀{self._get_type_name(story_type)}营销专家。

## 你的核心能力
{self._get_marketer_expertise(story_type)}

## 工作原则
1. **差异化**：明确本产品的独特卖点
2. **精准性**：准确触达目标受众
3. **可行性**：方案要能在实际渠道执行
4. **ROI导向**：考虑投入产出比

## 输出要求
- 目标受众画像要具体明确
- 核心卖点要有记忆点
- 推广渠道要与受众匹配
- 预算分配要有优先级

## 验证标准
完成营销方案后，请确认：
- 是否找到了差异化定位？
- 受众分析是否有数据支撑？
- 渠道选择是否合理？
- 预期效果是否可衡量？
"""
        return base_prompt

    def _get_type_name(self, story_type: str) -> str:
        """Get display name for story type."""
        names = {
            "emotion": "情感本",
            "reasoning": "推理本",
            "fun": "欢乐本",
            "horror": "恐怖本",
            "mechanic": "机制本",
        }
        return names.get(story_type, story_type)

    def _get_designer_expertise(self, story_type: str) -> str:
        """Get designer expertise description."""
        expertise = {
            "emotion": """- 设计触动人心的情感故事弧线
- 创造复杂的情感关系网络
- 打造让人泪目的角色成长
- 设计两难的情感抉择时刻
- 构建情感冲突的渐进升级""",

            "reasoning": """- 设计严密的逻辑谜题结构
- 构建完整的证据链和多路径验证
- 创造意想不到但合理的多重反转
- 确保推理的公平性和唯一解
- 设计干扰项和红鲱鱼的运用技巧""",

            "fun": """- 设计让人捧腹的喜剧人设
- 创造自然的误会和反转机制
- 制造高效的社交碰撞点
- 让每个角色都有专属笑点
- 平衡即兴发挥与剧情引导""",

            "horror": """- 营造层层递进的恐惧氛围
- 设计渐进式的心理压迫升级
- 创造让人欲罢不能的悬念
- 用留白和想象增强恐怖感
- 构建合理的恐怖真相揭示""",

            "mechanic": """- 设计平衡的游戏机制和阵营
- 创造丰富的策略选择空间
- 确保各方的翻盘可能性
- 设计有趣的技能和资源系统
- 平衡运气与策略的占比""",
        }
        return expertise.get(story_type, expertise["mechanic"])

    def _get_writer_expertise(self, story_type: str) -> str:
        """Get writer expertise description."""
        expertise = {
            "emotion": """- 细腻动人的角色内心独白
- 两难的情感抉择场景
- 让人印象深刻的关键台词
- 动态变化的情感关系
- 细腻的情感铺垫和爆发""",

            "reasoning": """- 逻辑严密的推理过程呈现
- 公平但有挑战的证据链
- 合理的干扰项和自我辩护
- 清晰的信息获取路径
- 引人入胜的推理节奏""",

            "fun": """- 让人捧腹的台词和场景
- 自然的误会和反转
- 充足的即兴发挥空间
- 每个角色的专属笑点
- 欢乐的社交互动引导""",

            "horror": """- 压抑恐惧的氛围营造
- 留白创造的想象空间
- 渐进升级的恐怖体验
- 震撼的真相揭示
- 角色面对恐惧的反应""",

            "mechanic": """- 策略性强的角色剧本
- 清晰的阵营归属和目标
- 关键的博弈时刻设计
- 游戏机制的自然融入
- 胜负条件的明确表达""",
        }
        return expertise.get(story_type, expertise["mechanic"])

    def _get_artist_expertise(self, story_type: str) -> str:
        """Get artist expertise description."""
        expertise = {
            "emotion": """- 将情感时刻视觉化的能力
- 引起情感共鸣的画面构图
- 传达细腻情感的色调设计
- 角色关系的表现技巧
- 氛围与情绪的视觉表达""",

            "reasoning": """- 线索和证据的视觉化
- 信息丰富的画面构图
- 悬疑感十足的视觉风格
- 图表和时间线的设计
- 专业刑侦感的呈现""",

            "fun": """- 夸张有趣的喜剧角色设计
- 欢快活泼的视觉风格
- 色彩传递的欢乐氛围
- 有记忆点的视觉元素
- 反差萌的视觉表现""",

            "horror": """- 压抑恐惧的氛围营造
- 阴影和色调的恐怖表达
- 留有想象空间的画面
- 悬念的视觉营造
- 恐怖真相的视觉暗示""",

            "mechanic": """- 游戏机制的可视化
- 清晰的界面和信息展示
- 策略感的视觉表达
- 技能和资源的设计
- 阵营标识的视觉系统""",
        }
        return expertise.get(story_type, expertise["mechanic"])

    def _get_tester_expertise(self, story_type: str) -> str:
        """Get tester expertise description."""
        expertise = {
            "emotion": """- 评估情感共鸣的触发效果
- 测试角色弧线的完整性
- 检验情感冲突的强度
- 验证情感铺垫的充分性
- 测量结局的余韵效果""",

            "reasoning": """- 测试逻辑的自洽性
- 评估证据链的完整性
- 检验推理的公平性
- 验证难度曲线
- 检查是否存在逻辑漏洞""",

            "fun": """- 测试社交活跃度
- 评估笑点的有效性
- 检验即兴空间
- 验证误会/反转自然度
- 测量整体欢乐氛围""",

            "horror": """- 测试恐惧氛围的营造
- 评估恐惧升级的节奏
- 检验悬念的有效性
- 验证留白的效果
- 测量恐怖阈值""",

            "mechanic": """- 测试游戏平衡性
- 评估策略深度
- 检验翻盘机制
- 验证胜负判定
- 测量游戏节奏""",
        }
        return expertise.get(story_type, expertise["mechanic"])

    def _get_marketer_expertise(self, story_type: str) -> str:
        """Get marketer expertise description."""
        expertise = {
            "emotion": """- 打情感牌的营销策略
- 情感共鸣的宣传设计
- 感人营销文案的创作
- 目标受众的精准定位
- 口碑传播的引爆点""",

            "reasoning": """- 打"烧脑"牌的营销策略
- 悬疑感的宣传设计
- 挑战性营销文案创作
- 推理爱好者精准定位
- 智识阶层的传播路径""",

            "fun": """- 打"欢乐"牌的营销策略
- 社交传播的内容设计
- 病毒式传播的引爆点
- 轻松娱乐的定位传播
- 聚会场景的营销切入""",

            "horror": """- 打"刺激"牌的营销策略
- 恐怖氛围的宣传设计
- 悬念引流的文案创作
- 恐怖爱好者的精准定位
- 沉浸体验的营销卖点""",

            "mechanic": """- 打"策略"牌的营销策略
- 竞技感的宣传设计
- 策略深度营销文案创作
- 桌游玩家的精准定位
- 对抗体验的营销卖点""",
        }
        return expertise.get(story_type, expertise["mechanic"])
