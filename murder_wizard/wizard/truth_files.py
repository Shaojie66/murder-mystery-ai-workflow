"""JSON truth file manager for murder-wizard.

Inspired by inkos: immutable truth files with Zod schema validation,
JSON delta updates, and version tracking.

Truth files live in: ~/.murder-wizard/projects/<name>/state/
"""
from __future__ import annotations

import contextlib
import copy
import hashlib
import itertools
import json
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, get_args

from pydantic import BaseModel, ValidationError

from murder_wizard.wizard.schemas import (
    CharacterMatrix,
    CharacterEntry,
    CognitiveState,
    EvidenceItem,
    GameState,
    PendingHooksFile,
    ChapterSummariesFile,
    SubplotBoardFile,
    EmotionalArcsFile,
    TruthDelta,
    DeltaOp,
    Meta,
)


def _printable(text: str) -> str:
    """孤立的 UTF-16 代理项（JSON 里单独的 \\ud800 转义解出来的字符）无法编码成 UTF-8：
    改写成 \\udXXX 转义文字。其余字符原样保留。"""
    return text.encode("utf-8", "backslashreplace").decode("utf-8")


class MatrixContractError(ValueError):
    """模型生成的信息矩阵不满足契约。

    ``problems`` 是一次性收集到的全部问题（不是遇到第一个就停），每项是一句可直接展示的中文。
    问题文字常常嵌着模型给的键名、证据 ID：经 ``_printable`` 处理，保证能打印、能写日志——
    否则一个带孤立代理项的键名会让报告失败的那次打印抛编码异常，跳过后面的缓存逐出。
    """

    def __init__(self, problems):
        self.problems = [_printable(str(p)) for p in problems]
        super().__init__(
            f"信息矩阵不符合契约（{len(self.problems)} 项问题）：" + "；".join(self.problems)
        )


# 合法认知状态直接取自 schema，避免和 CognitiveState 的 Literal 各写一份
_LEGAL_STATES = tuple(get_args(CognitiveState.model_fields["state"].annotation))
_REQUIRED_EVIDENCE_FIELDS = (
    "evidence_id", "name", "description", "source_event", "source_character", "chain_role",
)


def _unencodable_text_paths(data) -> list[str]:
    """data 里无法编码为 UTF-8 的字符串（键或值）所在位置。位置文字本身可以安全打印。

    用显式栈遍历，不引入递归深度风险。
    """
    hits: list[str] = []

    def unencodable(text: str) -> bool:
        try:
            text.encode("utf-8")
        except UnicodeEncodeError:
            return True
        return False

    stack = [("", data)]
    while stack:
        path, value = stack.pop()
        if isinstance(value, str):
            if unencodable(value):
                hits.append(path or "(根)")
        elif isinstance(value, dict):
            for key, item in value.items():
                key_path = f"{path}.{_printable(str(key))}" if path else _printable(str(key))
                if isinstance(key, str) and unencodable(key):
                    hits.append(f"{key_path}（键）")
                stack.append((key_path, item))
        elif isinstance(value, list):
            stack.extend((f"{path}[{index}]", item) for index, item in enumerate(value))
    return sorted(hits)


def validate_generated_matrix(
    data,
    char_count: int,
    event_count: int,
    is_prototype: bool,
    brief_content: str = "",
) -> CharacterMatrix:
    """校验模型生成的信息矩阵，通过才返回 CharacterMatrix，否则一次性抛出全部问题。

    唯一允许的归一化：缺失的 ``character_id`` / ``evidence_id`` 取自所在 dict 的键
    （已存在但与键不同则是错误）。其余一律不补默认值：缺失的单元格不是「否」，
    非法状态不是「否」，缺失的证据字段是错误。

    契约：data 为 dict；char_count / event_count / is_prototype 与调用方给出的期望一致；
    角色键恰为 R1..Rn，每位角色有非空 name 且 event_cognitions 键恰为 E1..Em、状态合法；
    至少一条证据（其必填字段不能缺失或为空白）；证据的 source_event / source_character 引用已知事件 / 角色；
    points_to 为字符串（凶手 ID 或其他结论，沿用 schema 语义，不限定取值）；认知里的 evidence_refs 都存在于 evidence；
    每个事件至少有一位角色为「知」。

    不修改传入的 data；返回矩阵的 meta 由本函数生成（brief_content_hash / note），
    模型自带的 meta 不采用。顶层 ``version`` 是存档格式的版本号，不是剧本内容：同样不采用模型给的值，
    一律重置为 schema 默认值（选择重置而不是因它拒绝整个回复；没给也是默认值）。
    """
    for label, value in (("char_count", char_count), ("event_count", event_count)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"期望的 {label} 必须是 >= 1 的整数，收到 {value!r}")
    expected_proto = bool(is_prototype)

    if not isinstance(data, dict):
        raise MatrixContractError([f"矩阵必须是 JSON 对象，实际为 {type(data).__name__}"])

    data = copy.deepcopy(data)
    data.pop("version", None)  # 不采用模型给的 version：落到 schema 默认值
    char_ids = [f"R{i}" for i in range(1, char_count + 1)]
    event_ids = [f"E{j}" for j in range(1, event_count + 1)]
    char_range = f"R1-R{char_count}"
    event_range = f"E1-E{event_count}"

    problems: list[str] = []
    # 已用更具体的话报告过的 schema 位置（loc 前缀）：最后的 Pydantic 校验不再重复报
    flagged: list[tuple] = []

    def flag(message: str, *loc) -> None:
        problems.append(message)
        if loc:
            flagged.append(tuple(loc))

    # ── 数量与模式 ─────────────────────────────────────────────────────
    for field, expected in (("char_count", char_count), ("event_count", event_count)):
        if field not in data:
            flag(f"缺少 {field}（应为 {expected}）", field)
        else:
            actual = data[field]
            if isinstance(actual, bool) or not isinstance(actual, int) or actual != expected:
                flag(f"{field} 应为 {expected}，实际为 {actual!r}", field)
    if "is_prototype" not in data:
        flag(f"缺少 is_prototype（应为 {str(expected_proto).lower()}）", "is_prototype")
    elif not isinstance(data["is_prototype"], bool) or data["is_prototype"] != expected_proto:
        flag(
            f"is_prototype 应为 {str(expected_proto).lower()}，实际为 {data['is_prototype']!r}",
            "is_prototype",
        )

    # ── 证据（先收集 id，角色认知要引用它）──────────────────────────────
    evidence = data.get("evidence")
    evidence_ids: set[str] = set()
    if evidence is None:
        flag("缺少 evidence：至少需要一条证据")
    elif not isinstance(evidence, dict):
        flag(f"evidence 必须是对象，实际为 {type(evidence).__name__}", "evidence")
    elif not evidence:
        flag("evidence 为空：至少需要一条证据")
    else:
        evidence_ids = {str(key) for key in evidence}

    # ── 角色与认知 ─────────────────────────────────────────────────────
    characters = data.get("characters")
    valid_cells: dict[tuple[str, str], dict] = {}
    if characters is None:
        flag("缺少 characters：矩阵没有任何角色")
    elif not isinstance(characters, dict):
        flag(f"characters 必须是对象，实际为 {type(characters).__name__}", "characters")
    elif not characters:
        flag("characters 为空：矩阵没有任何角色")
    else:
        missing_chars = [cid for cid in char_ids if cid not in characters]
        extra_chars = [key for key in characters if key not in char_ids]
        if missing_chars:
            flag(f"缺少角色 {', '.join(missing_chars)}（应恰为 {char_range}）")
        if extra_chars:
            flag(f"多余角色 {', '.join(str(k) for k in extra_chars)}（应恰为 {char_range}）")
            flagged.extend(("characters", key) for key in extra_chars)

        for cid in char_ids:
            if cid not in characters:
                continue
            entry = characters[cid]
            if not isinstance(entry, dict):
                flag(f"角色 {cid} 必须是对象，实际为 {type(entry).__name__}", "characters", cid)
                continue
            if "character_id" not in entry:
                entry["character_id"] = cid  # 允许的归一化：取自键
            elif entry["character_id"] != cid:
                flag(
                    f"角色键 {cid} 与 character_id {entry['character_id']!r} 不一致",
                    "characters", cid, "character_id",
                )
            name = entry.get("name")
            if not isinstance(name, str) or not name.strip():
                flag(f"角色 {cid} 缺少非空的 name", "characters", cid, "name")

            cognitions = entry.get("event_cognitions")
            if not isinstance(cognitions, dict):
                flag(f"角色 {cid} 缺少 event_cognitions（应含 {event_range}）",
                     "characters", cid, "event_cognitions")
                continue
            missing_events = [eid for eid in event_ids if eid not in cognitions]
            extra_events = [key for key in cognitions if key not in event_ids]
            if missing_events:
                flag(f"角色 {cid} 缺少事件认知 {', '.join(missing_events)}"
                     f"（缺失不会按「否」补位，应恰为 {event_range}）")
            if extra_events:
                flag(f"角色 {cid} 含未知事件 {', '.join(str(k) for k in extra_events)}"
                     f"（应恰为 {event_range}）")
                flagged.extend(("characters", cid, "event_cognitions", key) for key in extra_events)

            for eid in event_ids:
                if eid not in cognitions:
                    continue
                cell = cognitions[eid]
                loc = ("characters", cid, "event_cognitions", eid)
                if not isinstance(cell, dict):
                    flag(f"角色 {cid} 在 {eid} 的认知必须是对象，实际为 {type(cell).__name__}", *loc)
                    continue
                valid_cells[(cid, eid)] = cell
                state = cell.get("state")
                if "state" not in cell:
                    flag(f"角色 {cid} 在 {eid} 的认知缺少 state", *loc)
                elif not isinstance(state, str) or state not in _LEGAL_STATES:
                    flag(
                        f"角色 {cid} 在 {eid} 的 state 非法：{state!r}"
                        f"（只能是 {'、'.join(_LEGAL_STATES)} 之一，不带方括号）",
                        *loc, "state",
                    )
                refs = cell.get("evidence_refs", [])
                if not isinstance(refs, list) or any(not isinstance(ref, str) for ref in refs):
                    flag(f"角色 {cid} 在 {eid} 的 evidence_refs 必须是证据 ID 字符串列表",
                         *loc, "evidence_refs")
                else:
                    dangling = [ref for ref in refs if ref not in evidence_ids]
                    if dangling:
                        flag(f"角色 {cid} 在 {eid} 引用了不存在的证据 {', '.join(dangling)}")

    # ── 证据字段与引用 ─────────────────────────────────────────────────
    if isinstance(evidence, dict):
        for key, item in evidence.items():
            loc = ("evidence", key)
            if not isinstance(item, dict):
                flag(f"证据 {key} 必须是对象，实际为 {type(item).__name__}", *loc)
                continue
            if "evidence_id" not in item:
                item["evidence_id"] = key  # 允许的归一化：取自键
            elif item["evidence_id"] != key:
                flag(f"证据键 {key} 与 evidence_id {item['evidence_id']!r} 不一致",
                     *loc, "evidence_id")
            for field in _REQUIRED_EVIDENCE_FIELDS:
                value = item.get(field)
                if value is None:
                    flag(f"证据 {key} 缺少字段 {field}", *loc, field)
                elif isinstance(value, str) and not value.strip():
                    flag(f"证据 {key} 的字段 {field} 为空", *loc, field)
            source_event = item.get("source_event")
            if source_event is not None and source_event not in event_ids:
                flag(f"证据 {key} 的 source_event {source_event!r} 不是已知事件（应为 {event_range}）",
                     *loc, "source_event")
            source_character = item.get("source_character")
            if source_character is not None and source_character not in char_ids:
                flag(f"证据 {key} 的 source_character {source_character!r} 不是已知角色"
                     f"（应为 {char_range}）", *loc, "source_character")
            # points_to 在 schema 里是「凶手ID或其他结论」：不限定取值，只要求是字符串，
            # 不能把已有字段语义收窄成「必须是已知角色/证据 ID」。
            points_to = item.get("points_to", "")
            if not isinstance(points_to, str):
                flag(f"证据 {key} 的 points_to 必须是字符串", *loc, "points_to")

    # ── 事件覆盖：每个事件至少一位角色「知」 ───────────────────────────────
    for eid in event_ids:
        if not any(valid_cells.get((cid, eid), {}).get("state") == "知" for cid in char_ids):
            flag(f"事件 {eid} 没有任何角色为「知」：无人知晓的事件，证据链断裂")
    if valid_cells and all(cell.get("state") == "否" for cell in valid_cells.values()):
        flag("所有认知状态均为「否」：疑似默认填充，不是有效矩阵")

    # ── 最后一道：Pydantic（捕获上面没有逐项检查的类型错误），已报告的位置不重复 ──
    data["meta"] = Meta(
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
        commit_hash=_git_commit() or "no-git",
        brief_content_hash=_sha256(brief_content),
        note="Generated by Stage 2 Q1; passed matrix contract validation",
    ).model_dump()
    matrix = None
    try:
        matrix = CharacterMatrix.model_validate(data)
    except ValidationError as exc:
        for err in exc.errors():
            loc = tuple(err["loc"])
            if any(loc[:len(prefix)] == prefix for prefix in flagged):
                continue
            problems.append(f"schema 校验失败：{'.'.join(str(p) for p in loc)}：{err['msg']}")

    # 文字必须能保存：孤立的 UTF-16 代理项（JSON 里单独的 \\ud800 转义）能通过 json.loads 和上面的所有检查，
    # 却无法编码成 UTF-8，序列化和写文件都会抛异常。这是模型回复本身的问题，在这里指明位置并拒绝。
    # 只查校验后保留下来的字段：被 schema 忽略的多余字段不会被保存，不构成问题。
    if matrix is not None:
        bad_text = _unencodable_text_paths(matrix.model_dump())
        if bad_text:
            shown = "、".join(bad_text[:3]) + ("……" if len(bad_text) > 3 else "")
            problems.append(
                f"{len(bad_text)} 处文字含无法保存的字符（孤立的 UTF-16 代理项，"
                f"通常是 JSON 里单独出现的 \\ud800 之类转义，如 emoji 被截断）：{shown}；请改成完整的字符"
            )

    if problems:
        raise MatrixContractError(problems)
    if matrix is None:  # 防御：不可能出现（失败必然产生问题项）
        raise MatrixContractError(["schema 校验失败"])
    return matrix


class TruthFileManager:
    """Manages all JSON truth files for a project.

    Provides:
    - Load/save with Zod/Pydantic validation
    - Backup on every write (immutable history)
    - Delta generation for incremental updates
    - Migration from old Markdown files
    - Schema version migration
    """

    STATE_DIR = "state"

    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)
        self.state_dir = self.project_path / self.STATE_DIR
        self.state_dir.mkdir(exist_ok=True)

    # ─── File paths ─────────────────────────────────────────────────────────

    def _path(self, name: str) -> Path:
        return self.state_dir / f"{name}.json"

    def _backup_path(self, name: str, timestamp: str) -> Path:
        backup_dir = self.state_dir / ".backups"
        backup_dir.mkdir(exist_ok=True)
        return backup_dir / f"{name}.{timestamp}.json"

    # ─── Generic load/save ──────────────────────────────────────────────────

    def load(self, name: str, schema_class: type) -> Optional[BaseModel]:
        """Load a truth file, validate against schema, return Pydantic model.

        Returns None if file doesn't exist.
        Raises ValidationError if content doesn't match schema.
        """
        path = self._path(name)
        if not path.exists():
            return None

        data = json.loads(path.read_text(encoding="utf-8"))
        return schema_class.model_validate(data)

    def save(self, name: str, model: BaseModel, author: str = "llm", note: str = "") -> None:
        """Save a truth file with backup.

        Writes the new content to a temp file in the same directory first and swaps it in with
        os.replace, so the live file is never half-written: if serialising or writing fails
        (disk full, ...), the previous valid file is still there byte for byte.
        Backs up the existing file (unique name, never overwrites a backup) right before the swap.
        Updates meta.updated_at.
        """
        path = self._path(name)

        # Update meta
        if hasattr(model, "meta") and model.meta:
            model.meta.updated_at = datetime.now().isoformat()
            model.meta.commit_hash = _git_commit() or "no-git"

        content = model.model_dump_json(ensure_ascii=False, indent=2)
        tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with open(tmp, "x", encoding="utf-8") as handle:
                handle.write(content)
            if path.exists():
                with contextlib.suppress(OSError):
                    shutil.copymode(path, tmp)  # os.replace 会换成新 inode：保持原文件的权限位
                self._backup_existing(name, path)
            os.replace(tmp, path)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise

    def _backup_existing(self, name: str, path: Path) -> Path:
        """把现有文件复制成一份新备份。备份名精确到微秒，重名则加序号后缀：绝不覆盖已有备份。"""
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        for attempt in itertools.count():
            backup = self._backup_path(name, stamp if attempt == 0 else f"{stamp}_{attempt}")
            try:
                os.close(os.open(backup, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))  # 先占住这个名字
            except FileExistsError:
                continue
            try:
                shutil.copy2(path, backup)
            except BaseException:
                backup.unlink(missing_ok=True)
                raise
            return backup

    def exists(self, name: str) -> bool:
        return self._path(name).exists()

    # ─── Character Matrix ────────────────────────────────────────────────────

    def load_matrix(self) -> Optional[CharacterMatrix]:
        return self.load("character_matrix", CharacterMatrix)

    def save_matrix(self, matrix: CharacterMatrix, author: str = "llm", note: str = "") -> None:
        self.save("character_matrix", matrix, author=author, note=note)

    def create_matrix(
        self,
        char_count: int = 6,
        event_count: int = 7,
        is_prototype: bool = False,
        brief_content: str = "",
    ) -> CharacterMatrix:
        """Create a new empty character matrix."""
        char_ids = [f"R{i+1}" for i in range(char_count)]
        event_ids = [f"E{i+1}" for i in range(event_count)]

        characters = {}
        for cid in char_ids:
            characters[cid] = CharacterEntry(
                character_id=cid,
                name="",
                event_cognitions={
                    eid: CognitiveState(state="否", detail="")
                    for eid in event_ids
                },
            )

        meta = Meta(
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            commit_hash=_git_commit() or "no-git",
            brief_content_hash=_sha256(brief_content),
        )

        return CharacterMatrix(
            char_count=char_count,
            event_count=event_count,
            is_prototype=is_prototype,
            characters=characters,
            evidence={},
            meta=meta,
        )

    # ─── Delta updates ───────────────────────────────────────────────────────

    def generate_delta(
        self,
        old_matrix: CharacterMatrix,
        new_matrix: CharacterMatrix,
        author: str = "llm",
        reason: str = "",
    ) -> TruthDelta:
        """Generate a delta between two character matrices.

        Compares old vs new and produces a list of operations.
        This is what inkos calls the "Reflector" output.
        """
        ops = []

        # Character-level changes
        old_chars = set(old_matrix.characters.keys())
        new_chars = set(new_matrix.characters.keys())

        for cid in new_chars - old_chars:
            ops.append(DeltaOp(
                op="add",
                path=f"characters.{cid}",
                new_value=f"CharacterEntry({new_matrix.characters[cid].name or cid})",
                reason=reason,
            ))

        for cid in old_chars - new_chars:
            ops.append(DeltaOp(
                op="delete",
                path=f"characters.{cid}",
                old_value=f"CharacterEntry({old_matrix.characters[cid].name or cid})",
                reason=reason,
            ))

        for cid in old_chars & new_chars:
            old_char = old_matrix.characters[cid]
            new_char = new_matrix.characters[cid]

            # Field-level changes within character
            for field in ["name", "role", "public_relationship"]:
                old_val = getattr(old_char, field, "")
                new_val = getattr(new_char, field, "")
                if old_val != new_val:
                    ops.append(DeltaOp(
                        op="update",
                        path=f"characters.{cid}.{field}",
                        old_value=str(old_val),
                        new_value=str(new_val),
                        reason=reason,
                    ))

            # Event cognition changes
            old_cogs = old_char.event_cognitions
            new_cogs = new_char.event_cognitions

            for eid in set(new_cogs.keys()) | set(old_cogs.keys()):
                old_state = old_cogs.get(eid, CognitiveState(state="否"))
                new_state = new_cogs.get(eid, CognitiveState(state="否"))
                if old_state.state != new_state.state:
                    ops.append(DeltaOp(
                        op="update",
                        path=f"characters.{cid}.event_cognitions.{eid}",
                        old_value=f"{old_state.state}: {old_state.detail}",
                        new_value=f"{new_state.state}: {new_state.detail}",
                        reason=reason,
                    ))

        return TruthDelta(
            target_file="character_matrix",
            timestamp=datetime.now().isoformat(),
            operations=ops,
            author=author,
            reason=reason,
        )

    def apply_delta(self, matrix: CharacterMatrix, delta: TruthDelta) -> CharacterMatrix:
        """Apply a delta to a character matrix, returning a new instance."""
        # Deep copy
        import copy
        updated = copy.deepcopy(matrix)

        for op in delta.operations:
            self._apply_op(updated, op)

        updated.meta.updated_at = datetime.now().isoformat()
        return updated

    def _apply_op(self, matrix: CharacterMatrix, op: "DeltaOp") -> None:
        """Apply a single DeltaOp to a CharacterMatrix."""
        parts = op.path.split(".")
        if len(parts) < 2:
            return

        if parts[0] == "characters" and len(parts) >= 2:
            cid = parts[1]
            if cid not in matrix.characters:
                if op.op == "add":
                    matrix.characters[cid] = CharacterEntry(character_id=cid)
                else:
                    return

            char = matrix.characters[cid]

            if len(parts) == 2:
                # Top-level character operation
                if op.op == "delete":
                    del matrix.characters[cid]
                return

            field = parts[2]

            if field == "event_cognitions" and len(parts) >= 4:
                eid = parts[3]
                if op.op in ["add", "update", "replace"]:
                    # Parse new value: "知: detail" format
                    if ":" in op.new_value:
                        state_str, detail = op.new_value.split(":", 1)
                        char.event_cognitions[eid] = CognitiveState(
                            state=state_str.strip(),
                            detail=detail.strip(),
                        )
                elif op.op == "delete":
                    char.event_cognitions.pop(eid, None)
            elif hasattr(char, field) and op.op in ["add", "update", "replace"]:
                setattr(char, field, op.new_value)

    # ─── Migration from Markdown ──────────────────────────────────────────────

    def migrate_from_markdown(
        self,
        matrix_md: str,
        char_count: int = 6,
        event_count: int = 7,
        is_prototype: bool = False,
    ) -> CharacterMatrix:
        """Parse old Markdown information_matrix.md and create CharacterMatrix JSON.

        This is a best-effort parse — the LLM-generated Markdown is
        not perfectly structured, so we do approximate parsing.

        有损（lossy）：解析不到的单元格、非法状态一律变成「否」，也不会生成证据链。
        只作为显式、单独的旧资料导入入口；生成路径（阶段 2 Q1）绝不调用它，
        模型输出的校验见 ``validate_generated_matrix``。
        """
        char_ids = [f"R{i+1}" for i in range(char_count)]
        event_ids = [f"E{i+1}" for i in range(event_count)]

        # Try to parse table from Markdown
        # Format: | | R1 | R2 | ... |
        #         | E1 | 知 | 疑 | ... |
        lines = matrix_md.split("\n")
        char_order = []
        cells: dict[str, dict[str, str]] = {}

        # Find header row to extract character order
        for line in lines:
            if line.startswith("|") and "R1" in line:
                parts = [p.strip() for p in line.split("|")[1:]]
                char_order = [p for p in parts if p.startswith("R")]
                break

        if not char_order:
            char_order = char_ids

        # Parse data rows
        for line in lines:
            if not line.startswith("|") or line.startswith("|---") or "R1" in line:
                continue
            parts = [p.strip() for p in line.split("|")[1:]]
            if not parts:
                continue
            event_id = parts[0].replace("（核心）", "").strip()
            if not event_id.startswith("E"):
                continue

            cells[event_id] = {}
            for i, state_str in enumerate(parts[1:], start=0):
                if i < len(char_order):
                    cells[event_id][char_order[i]] = state_str

        # Build CharacterMatrix
        characters: dict[str, CharacterEntry] = {}
        for cid in char_ids:
            eid_cogs: dict[str, CognitiveState] = {}
            for eid in event_ids:
                state_str = cells.get(eid, {}).get(cid, "否")
                # Extract state (first char or bracketed)
                import re
                match = re.search(r"\[([^\]]+)\]", state_str)
                state = match.group(1) if match else state_str.strip()[:2]
                valid_states = ["知", "疑", "昧", "否", "误信", "隐瞒"]
                if state not in valid_states:
                    state = "否"
                eid_cogs[eid] = CognitiveState(state=state, detail=state_str)

            characters[cid] = CharacterEntry(
                character_id=cid,
                event_cognitions=eid_cogs,
            )

        return CharacterMatrix(
            char_count=char_count,
            event_count=event_count,
            is_prototype=is_prototype,
            characters=characters,
            evidence={},
            meta=Meta(
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                commit_hash=_git_commit() or "no-git",
                brief_content_hash=_sha256(matrix_md),
                note="Migrated from information_matrix.md",
            ),
        )

    # ─── Evidence chain helpers ──────────────────────────────────────────────

    def add_evidence(
        self,
        evidence_id: str,
        name: str,
        description: str,
        source_event: str,
        source_character: str,
        chain_role: str,
        points_to: str = "",
    ) -> EvidenceItem:
        """Create but do NOT persist an evidence item — use add_evidence_to_matrix to persist."""
        return EvidenceItem(
            evidence_id=evidence_id,
            name=name,
            description=description,
            source_event=source_event,
            source_character=source_character,
            chain_role=chain_role,
            points_to=points_to,
        )

    def add_evidence_to_matrix(
        self,
        matrix: CharacterMatrix,
        evidence_id: str,
        name: str,
        description: str,
        source_event: str,
        source_character: str,
        chain_role: str,
        points_to: str = "",
    ) -> CharacterMatrix:
        """Add an evidence item to the matrix and save it atomically."""
        matrix.evidence[evidence_id] = EvidenceItem(
            evidence_id=evidence_id,
            name=name,
            description=description,
            source_event=source_event,
            source_character=source_character,
            chain_role=chain_role,
            points_to=points_to,
        )
        self.save_matrix(matrix, author="human", note=f"Added evidence {evidence_id}")
        return matrix

    # ─── Audit helpers ───────────────────────────────────────────────────────

    def audit_matrix_completeness(self, matrix: CharacterMatrix) -> list[str]:
        """Check for missing or inconsistent data in matrix.

        Returns list of issue descriptions.
        """
        issues = []

        # Check all characters have all events
        expected_chars = [f"R{i+1}" for i in range(matrix.char_count)]
        for cid in expected_chars:
            if cid not in matrix.characters:
                issues.append(f"Missing character: {cid}")
                continue
            char = matrix.characters[cid]
            expected_events = [f"E{i+1}" for i in range(matrix.event_count)]
            for eid in expected_events:
                if eid not in char.event_cognitions:
                    issues.append(f"Character {cid} missing cognition for {eid}")
                elif char.event_cognitions[eid].state == "否":
                    # Check if they should know (they are the culprit or witness)
                    pass  # "否" is valid for characters who weren't present

        # Check evidence chain completeness
        if not matrix.evidence:
            issues.append("No evidence chain defined — evidence is empty")

        # Check that at least one character knows each event
        expected_events = [f"E{i+1}" for i in range(matrix.event_count)]
        for eid in expected_events:
            knowers = matrix.all_know(eid)
            if not knowers:
                issues.append(f"Event {eid} has no character who [知] — evidence chain broken")

        return issues

    def audit_killer_knowledge(self, matrix: CharacterMatrix) -> list[str]:
        """Check that the killer (R1) has sufficient knowledge to be solvable."""
        issues = []

        killer = matrix.characters.get("R1")
        if not killer:
            issues.append("No R1 (killer) character found")
            return issues

        killer_knows = [
            eid for eid, cog in killer.event_cognitions.items()
            if cog.state in ["知", "误信"]
        ]

        if len(killer_knows) < matrix.event_count * 0.5:
            issues.append(
                f"Killer (R1) only knows {len(killer_knows)} of {matrix.event_count} events "
                f"— may be too mysterious to solve"
            )

        return issues


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _git_commit() -> str:
    """Get short git commit hash if in a git repo, else None."""
    try:
        from pathlib import Path
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _sha256(content: str) -> str:
    """SHA256 hex digest of content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
