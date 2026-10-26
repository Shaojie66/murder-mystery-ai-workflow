"""Project bootstrap helpers for the web workbench."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from murder_wizard.llm import client as llm_client
from murder_wizard.llm.client import LLMResponse
from murder_wizard.prompts.loader import PromptLoader
from murder_wizard.wizard.session import SessionManager
from murder_wizard.wizard.state_machine import MurderWizardState


_STORY_TYPE_LABELS = {
    "emotion": "情感本",
    "reasoning": "推理本",
    "fun": "欢乐本",
    "horror": "恐怖本",
    "mechanic": "机制本",
}


@dataclass
class BootstrapResult:
    brief_content: str
    outline_content: str
    outline_source: str


def build_brief_from_answers(
    project_name: str,
    story_type: str,
    era: str,
    is_prototype: bool,
    answers: Optional[dict],
) -> str:
    """Build a deterministic brief from web form input."""
    story_type_label = _STORY_TYPE_LABELS.get(story_type, story_type)
    mode_label = "原型模式（2人）" if is_prototype else "完整模式（6人）"

    lines = [
        "# 剧本杀创作简报",
        "",
        "> 由 Murder Wizard Web 创建",
        f"> 项目：{project_name}",
        f"> 创作模式：{mode_label}",
        f"> 剧本类型：{story_type_label}",
        "",
        "---",
        "",
        "## 核心定位",
        "",
        f"- **项目名**：{project_name}",
        f"- **剧本类型**：{story_type_label}",
        f"- **时代背景**：{era}",
        f"- **制作模式**：{mode_label}",
        "",
    ]

    if answers:
        lines.extend([
            "## 创作问卷",
            "",
        ])
        for key, value in answers.items():
            lines.append(f"- **{key}**：{value}")
        lines.append("")
    else:
        lines.extend([
            "## 默认创作方向",
            "",
            f"- 以「{story_type_label}」为核心体验，先产出一个{mode_label}版本。",
            "- 优先保证事件线清晰、角色动机可写、后续阶段可连续推进。",
            "- 本简报由网页快速创建流程生成，后续内容以生成的大纲为准。",
            "",
        ])

    lines.extend([
        "---",
        "",
        "*本文件是所有后续 prompt 的默认上下文。*",
    ])
    return "\n".join(lines)


def _build_outline_prompt(brief_content: str, is_prototype: bool) -> str:
    char_hint = "两位角色设定简述" if is_prototype else "六位角色设定简述"
    event_hint = "3个关键事件" if is_prototype else "5-7个关键事件"
    return f"""基于以下创意简报，为这个剧本杀生成详细大纲：

{brief_content}

请生成：
1. 故事梗概（200字）
2. {char_hint}
3. 核心事件线（{event_hint}）
4. 结局走向建议

格式：Markdown，包含表格（如事件表、角色技能表）"""


def _generate_outline(brief_content: str, is_prototype: bool) -> LLMResponse:
    loader = PromptLoader()
    provider = os.environ.get("LLM_PROVIDER")
    llm = llm_client.create_llm_adapter(provider)
    return llm.complete(
        _build_outline_prompt(brief_content, is_prototype),
        system=loader.system_outline_generator(),
    )


def ensure_project_bootstrap(
    session: SessionManager,
    state: MurderWizardState,
    *,
    project_name: str,
    story_type: str,
    era: str = "现代",
    is_prototype: bool,
    answers: Optional[dict] = None,
) -> BootstrapResult:
    """Ensure a project has a persisted brief, outline, and session outline field."""
    project_path = session.project_path
    brief_file = project_path / "brief.md"
    outline_file = project_path / "outline.md"

    brief_content = ""
    if brief_file.exists():
        brief_content = brief_file.read_text(encoding="utf-8").strip()
    if not brief_content:
        brief_content = build_brief_from_answers(
            project_name=project_name,
            story_type=story_type,
            era=era,
            is_prototype=is_prototype,
            answers=answers,
        )
        brief_file.write_text(brief_content, encoding="utf-8")

    outline_content = (state.outline or "").strip()
    outline_source = "session_state"
    response: LLMResponse | None = None

    if not outline_content and outline_file.exists():
        outline_content = outline_file.read_text(encoding="utf-8").strip()
        outline_source = "outline_file"

    if not outline_content:
        response = _generate_outline(brief_content, is_prototype)
        outline_content = response.content.strip()
        outline_source = "generated_from_brief"

    outline_file.write_text(outline_content, encoding="utf-8")

    state.story_type = story_type
    state.is_prototype = is_prototype
    state.outline = outline_content
    session.save(state)

    if response is not None:
        session.log_cost("outline_generation", response.tokens_used, response.cost)

    return BootstrapResult(
        brief_content=brief_content,
        outline_content=outline_content,
        outline_source=outline_source,
    )
