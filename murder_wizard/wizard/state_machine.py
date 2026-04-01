"""murder-wizard state machine.

State transitions:
IDLE -> TYPE_SELECT -> STORY_BRIEF -> CHARACTER_DESIGN -> PLOT_BUILD -> ASSET_PROMPT -> OUTPUT
"""
from enum import IntEnum
from dataclasses import dataclass
from typing import Optional


class Stage(IntEnum):
    """剧本杀创作阶段"""
    IDLE = 0
    TYPE_SELECT = 1
    STORY_BRIEF = 2
    CHARACTER_DESIGN = 3
    PLOT_BUILD = 4
    ASSET_PROMPT = 5
    OUTPUT = 6

    # 完整8阶段
    STAGE_1_MECHANISM = 7
    STAGE_2_SCRIPT = 8
    STAGE_3_VISUAL = 9
    STAGE_4_TEST = 10
    STAGE_5_COMMERCIAL = 11
    STAGE_6_PRINT = 12
    STAGE_7_PROMO = 13
    STAGE_8_COMMUNITY = 14

    @property
    def slug(self) -> str:
        """稳定的字符串标识，用于持久化和展示。"""
        return _STAGE_SLUGS[self]

    @classmethod
    def from_value(cls, value: "Stage | int | str") -> "Stage":
        """兼容旧字符串值和新数值。"""
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            try:
                return _STAGE_FROM_SLUG[value]
            except KeyError as exc:
                raise ValueError(f"Unknown stage: {value}") from exc
        return cls(value)


@dataclass
class MurderWizardState:
    """Wizard 状态"""
    project_name: str
    story_type: str = "emotion"  # emotion, reasoning, fun, horror, mechanic
    current_stage: Stage = Stage.IDLE

    # 阶段产物
    outline: Optional[str] = None  # 大纲
    characters: Optional[dict] = None  # 角色信息
    plot: Optional[dict] = None  # 剧本结构
    image_prompts: Optional[dict] = None  # 图像提示词

    # 原型模式
    is_prototype: bool = False
    prototype_characters: Optional[list] = None  # 原型中包含的角色

    def _can_advance_to(self, next_stage: Stage) -> bool:
        """检查是否可以转换到下一阶段（内部使用）"""
        transitions = {
            Stage.IDLE: [Stage.TYPE_SELECT],
            Stage.TYPE_SELECT: [Stage.STORY_BRIEF, Stage.STAGE_1_MECHANISM],
            Stage.STORY_BRIEF: [Stage.CHARACTER_DESIGN, Stage.STAGE_1_MECHANISM],
            Stage.CHARACTER_DESIGN: [Stage.PLOT_BUILD, Stage.STAGE_2_SCRIPT],
            Stage.PLOT_BUILD: [Stage.ASSET_PROMPT, Stage.STAGE_3_VISUAL],
            Stage.ASSET_PROMPT: [Stage.OUTPUT],
            Stage.OUTPUT: [Stage.STAGE_4_TEST],
            # 8阶段模式
            Stage.STAGE_1_MECHANISM: [Stage.STAGE_2_SCRIPT],
            Stage.STAGE_2_SCRIPT: [Stage.STAGE_3_VISUAL],
            Stage.STAGE_3_VISUAL: [Stage.STAGE_4_TEST],
            Stage.STAGE_4_TEST: [Stage.STAGE_5_COMMERCIAL],
            Stage.STAGE_5_COMMERCIAL: [Stage.STAGE_6_PRINT],
            Stage.STAGE_6_PRINT: [Stage.STAGE_7_PROMO],
            Stage.STAGE_7_PROMO: [Stage.STAGE_8_COMMUNITY],
            Stage.STAGE_8_COMMUNITY: [],
        }
        return next_stage in transitions.get(self.current_stage, [])

    def advance_to(self, next_stage: Stage) -> None:
        """转换到下一阶段"""
        if self._can_advance_to(next_stage):
            self.current_stage = next_stage
        else:
            raise ValueError(f"Cannot transition from {self.current_stage} to {next_stage}")

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "project_name": self.project_name,
            "story_type": self.story_type,
            "current_stage": self.current_stage.value,
            "current_stage_slug": self.current_stage.slug,
            "outline": self.outline,
            "characters": self.characters,
            "plot": self.plot,
            "image_prompts": self.image_prompts,
            "is_prototype": self.is_prototype,
            "prototype_characters": self.prototype_characters,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MurderWizardState":
        """从字典恢复"""
        state = cls(
            project_name=data["project_name"],
            story_type=data.get("story_type", "mechanic"),
            current_stage=Stage.from_value(
                data.get("current_stage", data.get("current_stage_slug", "idle"))
            ),
            outline=data.get("outline"),
            characters=data.get("characters"),
            plot=data.get("plot"),
            image_prompts=data.get("image_prompts"),
            is_prototype=data.get("is_prototype", False),
            prototype_characters=data.get("prototype_characters"),
        )
        return state


_STAGE_SLUGS = {
    Stage.IDLE: "idle",
    Stage.TYPE_SELECT: "type_select",
    Stage.STORY_BRIEF: "story_brief",
    Stage.CHARACTER_DESIGN: "character_design",
    Stage.PLOT_BUILD: "plot_build",
    Stage.ASSET_PROMPT: "asset_prompt",
    Stage.OUTPUT: "output",
    Stage.STAGE_1_MECHANISM: "stage_1_mechanism",
    Stage.STAGE_2_SCRIPT: "stage_2_script",
    Stage.STAGE_3_VISUAL: "stage_3_visual",
    Stage.STAGE_4_TEST: "stage_4_test",
    Stage.STAGE_5_COMMERCIAL: "stage_5_commercial",
    Stage.STAGE_6_PRINT: "stage_6_print",
    Stage.STAGE_7_PROMO: "stage_7_promo",
    Stage.STAGE_8_COMMUNITY: "stage_8_community",
}

_STAGE_FROM_SLUG = {slug: stage for stage, slug in _STAGE_SLUGS.items()}
