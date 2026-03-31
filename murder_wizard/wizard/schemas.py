"""Zod schemas for murder-wizard truth files.

Inspired by inkos: structured JSON truth files with Zod validation,
immutable versioning, and delta updates.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ─── Shared Meta (defined first — referenced by all models) ─────────────────────

class Meta(BaseModel):
    """Common metadata for all truth files."""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    commit_hash: str = "auto"
    brief_content_hash: str = ""  # SHA256 of brief.md at creation time
    note: str = ""


# ─── Cognitive States ──────────────────────────────────────────────────────────

class CognitiveState(BaseModel):
    """A single character's knowledge state for one event."""
    state: Literal["知", "疑", "昧", "否", "误信", "隐瞒"] = Field(
        description="角色对该事件的认知状态"
    )
    detail: str = Field(default="", description="补充说明（如：知什么、疑什么）")
    evidence_refs: list[str] = Field(default_factory=list, description="相关证据ID列表")


# ─── Character Entry & Matrix ─────────────────────────────────────────────────

class CharacterEntry(BaseModel):
    """Single character's full information across all events."""
    character_id: str
    name: str = ""
    role: str = ""  # 社会身份标签
    public_relationship: str = ""  # 公开关系
    secret_relationship: dict[str, str] = Field(default_factory=dict)  # 对其他角色的秘密关系

    # 三层信息
    surface_info: str = Field(default="", description="表层信息（自我介绍时说）")
    middle_info: str = Field(default="", description="中层信息（通过a本读出）")
    deep_info: str = Field(default="", description="深层信息（只存在于DM手册）")

    # 内心弧线
    belief_before: str = Field(default="", description="游戏前相信X")
    belief_trigger: str = Field(default="", description="因Y事件，信念开始动摇")
    belief_after: str = Field(default="", description="结局是否接受新真相")

    # a本边界约束
    can_say: list[str] = Field(default_factory=list, description="开场可主动说出")
    cannot_say: list[str] = Field(default_factory=list, description="不能主动说")
    must_deny: list[str] = Field(default_factory=list, description="即使有证据也死不承认")

    # 该角色对所有事件的认知状态
    event_cognitions: dict[str, CognitiveState] = Field(default_factory=dict)
    # key = event_id, e.g. "E1", "E2"


class EvidenceItem(BaseModel):
    """Single evidence item in the evidence chain."""
    evidence_id: str  # e.g. "EV-A"
    name: str
    description: str
    source_event: str  # 哪个事件产生
    source_character: str  # 谁持有/谁可以接触
    chain_role: str  # 在证据链中的作用
    points_to: str = Field(default="", description="指向（凶手ID或其他结论）")


class CharacterMatrix(BaseModel):
    """Character × Event information matrix (replaces information_matrix.md).

    This is the primary truth file — the source of truth for all role consistency.
    """
    version: str = Field(default="1.0.0", description="Truth file schema version")
    char_count: int
    event_count: int
    is_prototype: bool

    characters: dict[str, CharacterEntry] = Field(
        default_factory=dict,
        description="key = character_id, e.g. 'R1', 'R2'"
    )

    # 证据链
    evidence: dict[str, EvidenceItem] = Field(default_factory=dict)

    # Metadata
    meta: Meta = Field(default_factory=Meta)

    def get_cognition(self, character_id: str, event_id: str) -> str | None:
        """Get character's cognitive state for an event."""
        char = self.characters.get(character_id)
        if not char:
            return None
        cog = char.event_cognitions.get(event_id)
        return cog.state if cog else None

    def all_know(self, event_id: str) -> list[str]:
        """Return all characters who [知] this event."""
        return [
            cid for cid, char in self.characters.items()
            if char.event_cognitions.get(event_id, CognitiveState(state="否")).state == "知"
        ]


# ─── Game State ───────────────────────────────────────────────────────────────

class GameState(BaseModel):
    """Mutable game state — current status, round, alive players, votes."""
    version: str = Field(default="1.0.0")
    current_round: int = 0
    phase: Literal["开场", "中盘", "结局"] = "开场"
    alive_characters: list[str] = Field(default_factory=list)
    eliminated: list[str] = Field(default_factory=list)
    votes: dict[str, str] = Field(default_factory=dict)  # voter -> target
    revealed_secrets: list[str] = Field(default_factory=list)  # event_ids revealed
    meta: Meta = Field(default_factory=Meta)


# ─── Pending Hooks ───────────────────────────────────────────────────────────

class PendingHook(BaseModel):
    """A narrative hook that needs payoff — tracked for audit."""
    hook_id: str
    setup_event: str  # E1 埋下的钩子
    payoff_event: str = ""  # E5 回收（空=未回收）
    setup_text: str  # 原文
    payoff_text: str = ""  # 回收后内容
    status: Literal["pending", "paid_off", "abandoned"] = "pending"


class PendingHooksFile(BaseModel):
    """Tracks narrative hooks across events for audit."""
    version: str = Field(default="1.0.0")
    hooks: dict[str, PendingHook] = Field(default_factory=dict)
    meta: Meta = Field(default_factory=Meta)


# ─── Chapter Summaries (for expand tracking) ────────────────────────────────

class ChapterSummary(BaseModel):
    """Summary of one event/chapter."""
    event_id: str
    title: str
    summary: str  # 1-2 sentence summary
    key_revelations: list[str] = Field(default_factory=list)
    characters_present: list[str] = Field(default_factory=list)


class ChapterSummariesFile(BaseModel):
    """Sequence of event summaries — used to track plot progression."""
    version: str = Field(default="1.0.0")
    chapters: dict[str, ChapterSummary] = Field(default_factory=dict)
    order: list[str] = Field(default_factory=list)  # ordered event_ids
    meta: Meta = Field(default_factory=Meta)


# ─── Subplot Board ────────────────────────────────────────────────────────────

class Subplot(BaseModel):
    """A side story / subplot."""
    subplot_id: str
    title: str
    description: str
    related_events: list[str] = Field(default_factory=list)
    related_characters: list[str] = Field(default_factory=list)
    status: Literal["active", "resolved", "abandoned"] = "active"


class SubplotBoardFile(BaseModel):
    """All subplots and their status."""
    version: str = Field(default="1.0.0")
    subplots: dict[str, Subplot] = Field(default_factory=dict)
    meta: Meta = Field(default_factory=Meta)


# ─── Emotional Arcs ─────────────────────────────────────────────────────────

class EmotionalStage(BaseModel):
    """One stage in an emotional arc."""
    event_id: str
    emotion: str  # e.g. "恐惧", "愤怒", "释然"
    description: str


class EmotionalArc(BaseModel):
    """One character's emotional journey across events."""
    character_id: str
    arc_type: str  # e.g. "背叛-信任", "绝望-希望"
    stages: list[EmotionalStage] = Field(default_factory=list)


class EmotionalArcsFile(BaseModel):
    """All characters' emotional arcs."""
    version: str = Field(default="1.0.0")
    arcs: dict[str, EmotionalArc] = Field(default_factory=dict)  # character_id -> arc
    meta: Meta = Field(default_factory=Meta)


# ─── JSON Delta ──────────────────────────────────────────────────────────────

class DeltaOp(BaseModel):
    """Single operation in a delta."""
    op: Literal["add", "update", "delete", "replace"] = Field(description="操作类型")
    path: str = Field(description="JSON path, e.g. 'characters.R1.event_cognitions.E1'")
    old_value: str = ""  # for update/delete — human-readable
    new_value: str = ""  # for add/update/replace
    reason: str = ""  # why this change was made


class TruthDelta(BaseModel):
    """Incremental update to a truth file — inkos-style delta.

    Instead of overwriting the entire truth file, we produce a delta
    that describes only what changed. This avoids context window bloat
    and preserves history.
    """
    version: str = Field(default="1.0.0")
    target_file: str  # e.g. "character_matrix"
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    operations: list[DeltaOp] = Field(default_factory=list)
    author: str = "llm"  # "llm" | "human" | "audit"
    note: str = ""
