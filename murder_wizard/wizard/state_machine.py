"""murder-wizard state machine.

State transitions:
IDLE -> TYPE_SELECT -> STORY_BRIEF -> CHARACTER_DESIGN -> PLOT_BUILD -> ASSET_PROMPT -> OUTPUT
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional


class Stage(str, Enum):
    """剧本杀创作阶段"""
    IDLE = "idle"
    TYPE_SELECT = "type_select"
    STORY_BRIEF = "story_brief"
    CHARACTER_DESIGN = "character_design"
    PLOT_BUILD = "plot_build"
    ASSET_PROMPT = "asset_prompt"
    OUTPUT = "output"

    # 完整8阶段
    STAGE_1_MECHANISM = "stage_1_mechanism"
    STAGE_2_SCRIPT = "stage_2_script"
    STAGE_3_VISUAL = "stage_3_visual"
    STAGE_4_TEST = "stage_4_test"
    STAGE_5_COMMERCIAL = "stage_5_commercial"
    STAGE_6_PRINT = "stage_6_print"
    STAGE_7_PROMO = "stage_7_promo"
    STAGE_8_COMMUNITY = "stage_8_community"


@dataclass
class MurderWizardState:
    """Wizard 状态"""
    project_name: str
    story_type: str = "mechanic"  # emotion, mechanic, puzzle
    current_stage: Stage = Stage.IDLE

    # 阶段产物
    outline: Optional[str] = None  # 大纲
    characters: Optional[dict] = None  # 角色信息
    plot: Optional[dict] = None  # 剧本结构
    image_prompts: Optional[dict] = None  # 图像提示词

    # 原型模式
    is_prototype: bool = False
    prototype_characters: Optional[list] = None  # 原型中包含的角色

    def can_advance_to(self, next_stage: Stage) -> bool:
        """检查是否可以转换到下一阶段"""
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
        if self.can_advance_to(next_stage):
            self.current_stage = next_stage
        else:
            raise ValueError(f"Cannot transition from {self.current_stage} to {next_stage}")

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "project_name": self.project_name,
            "story_type": self.story_type,
            "current_stage": self.current_stage.value,
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
            current_stage=Stage(data.get("current_stage", "idle")),
            outline=data.get("outline"),
            characters=data.get("characters"),
            plot=data.get("plot"),
            image_prompts=data.get("image_prompts"),
            is_prototype=data.get("is_prototype", False),
            prototype_characters=data.get("prototype_characters"),
        )
        return state
