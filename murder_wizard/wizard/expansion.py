"""expand（原型 2 人 3 事件 → 完整 6 人 7 事件）的纯逻辑：预检、增量矩阵并入、校验、候选组装。

不调模型、不打印、不写文件（仅 load_baseline 读文件，且不 mkdir）。
保留靠构造：characters/background/scripts_b 的新文件 = 旧文件原文 + 追加段；
矩阵 = 原型矩阵 + 增量，原型 R1/R2 × E1-E3 单元格与原证据不经过模型。
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Mapping, Optional

from murder_wizard.wizard.schemas import CharacterEntry, CharacterMatrix, CognitiveState, EvidenceItem
from murder_wizard.wizard.truth_files import MatrixContractError, validate_generated_matrix

ORIGINAL_IDS = ("R1", "R2")
NEW_IDS = ("R3", "R4", "R5", "R6")
ALL_IDS = ORIGINAL_IDS + NEW_IDS
PROTO_EVENTS = ("E1", "E2", "E3")
NEW_EVENTS = ("E4", "E5", "E6", "E7")
ALL_EVENTS = PROTO_EVENTS + NEW_EVENTS
STAGE_2_FILES = ("information_matrix.md", "background.md", "characters.md",
                 "scripts_b.md", "dm_manual.md", "endings.md")
MATRIX_REL = "state/character_matrix.json"
SESSION_REL = "session.json"
APPEND_ONLY = ("characters.md", "background.md", "scripts_b.md")
REGENERATED = ("information_matrix.md", "dm_manual.md", "endings.md", MATRIX_REL)
COMMIT_ORDER = (MATRIX_REL, "information_matrix.md", "background.md", "characters.md",
                "scripts_b.md", "dm_manual.md", "endings.md")
APPEND_HEADING_PREFIX = "扩写追加"
STALE_CANDIDATES = ("image-prompts.md", "test_guide.md", "iteration_report.md", "commercial.md",
                    "script.pdf", "clue_cards.pdf", "promo_content.md", "community_plan.md",
                    "consistency_report.md", "audit_report.md")

# 模板 → 必填输入（测试断言与模板占位符一致）
EXPAND_PROMPTS = {
    "02_expand_matrix.md": ("brief_content", "mechanism_content", "proto_matrix_json",
                            "proto_characters_content", "delta_json_example"),
    "02_expand_background.md": ("char_id", "char_name", "char_role", "char_public_relationship",
                                "brief_content", "matrix_content", "background_content"),
    "02_expand_script_a_ext.md": ("char_id", "char_name", "matrix_content", "background_content",
                                  "retained_script", "mechanism_content", "new_events_text",
                                  "known_new_events", "forbidden_events"),
    "02_expand_script_a.md": ("char_id", "char_name", "background_content", "matrix_content",
                              "mechanism_content", "new_events_text", "known_events",
                              "forbidden_events", "word_count_a", "retained_scripts"),
    "02_expand_script_b_ext.md": ("char_id", "char_name", "a_content", "original_scripts_b",
                                  "matrix_content", "mechanism_content", "new_evidence_text"),
}


class ExpandStatus(str, Enum):
    APPLIED = "applied"
    DECLINED = "declined"
    NOT_PROTOTYPE = "not_prototype"
    REFUSED = "refused"
    FAILED_CALL = "failed_call"
    FAILED_VALIDATION = "failed_validation"
    FAILED_INTERNAL = "failed_internal"
    CHANGED_DURING_RUN = "changed_during_run"
    COMMIT_RESTORED = "commit_restored"
    COMMIT_RESTORE_INCOMPLETE = "commit_restore_incomplete"


@dataclass
class ExpandResult:
    status: ExpandStatus
    problems: list = field(default_factory=list)
    failed_step: Optional[str] = None
    cost: float = 0.0
    calls: int = 0
    cached_calls: int = 0
    backup_tag: str = ""
    backups: dict = field(default_factory=dict)
    written: list = field(default_factory=list)
    restore_failed: list = field(default_factory=list)
    stale: list = field(default_factory=list)


class ExpandRefused(ValueError):
    def __init__(self, problems, status: ExpandStatus = ExpandStatus.REFUSED):
        self.problems = list(problems)
        self.status = status
        super().__init__("；".join(self.problems))


class ExpandContractError(ValueError):
    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__("；".join(self.problems))


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_matrix_json(m: CharacterMatrix) -> str:
    return json.dumps(m.model_dump(mode="json", exclude={"meta"}), ensure_ascii=False, indent=1)


@dataclass(frozen=True)
class ExpandBaseline:
    outline: str
    mechanism: str
    matrix: CharacterMatrix
    matrix_json: str
    texts: Mapping
    names: Mapping
    fingerprints: Mapping


def load_baseline(project_path: Path, state) -> ExpandBaseline:
    """预检：一次列全问题；零写入；不实例化 TruthFileManager（它会 mkdir state/）。"""
    root = Path(project_path)
    if not state.is_prototype:
        raise ExpandRefused(["当前不是原型，跳过 expand"], ExpandStatus.NOT_PROTOTYPE)
    problems: list = []
    outline = state.outline or ""
    if not outline.strip():
        problems.append("缺少大纲（outline 为空）")
    texts: dict = {}
    fingerprints: dict = {}
    for rel in ("mechanism.md", *STAGE_2_FILES):
        path = root / rel
        if not path.is_file():
            problems.append(f"缺少 {rel}（expand 不会生成原型缺失的材料；请先完成阶段2——注意阶段2会重新生成并覆盖已有的阶段2文件）")
            continue
        data = path.read_bytes()
        fingerprints[rel] = _sha(data)
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            problems.append(f"{rel} 不是合法 UTF-8")
            continue
        if not text.strip():
            problems.append(f"{rel} 为空")
            continue
        texts[rel] = text
    matrix = None
    mpath = root / MATRIX_REL
    if not mpath.is_file():
        problems.append(f"缺少 {MATRIX_REL}（expand 不做 Markdown 自动转换，请先重新生成阶段2）")
    else:
        mbytes = mpath.read_bytes()
        fingerprints[MATRIX_REL] = _sha(mbytes)
        try:
            raw = json.loads(mbytes.decode("utf-8"))
            if isinstance(raw, dict) and (raw.get("char_count"), raw.get("event_count")) != (2, 3):
                backups = sorted(p.name for p in root.glob("*.proto.*"))
                problems.append(
                    f"{MATRIX_REL} 不是 2×3 原型矩阵（char_count={raw.get('char_count')}, event_count={raw.get('event_count')}）："
                    "疑似上次 expand 提交被中断或作品已被改动。"
                    + (f"可手工用备份恢复（把 *.proto.<时间戳> 拷回原名，含 session.json）：{'、'.join(backups)}" if backups else "")
                )
            else:
                matrix = validate_generated_matrix(raw, char_count=2, event_count=3, is_prototype=True,
                                                   brief_content=outline)
        except MatrixContractError as e:
            problems.extend(f"原型矩阵未通过校验：{p}（expand 不做 Markdown 自动转换）" for p in e.problems)
        except (ValueError, TypeError) as e:
            problems.append(f"{MATRIX_REL} 无法解析：{e}")
    if not (root / SESSION_REL).is_file():
        problems.append(f"缺少 {SESSION_REL}（提交需要先备份它；缺失时 expand 无法安全写入，请先 resume 重建）")
        sbytes = b""
    else:
        sbytes = (root / SESSION_REL).read_bytes()
    fingerprints[SESSION_REL] = _sha(sbytes)
    names: dict = {}
    if matrix is not None:
        names = {cid: matrix.characters[cid].name.strip() for cid in ORIGINAL_IDS}
        chars_text = texts.get("characters.md", "")
        if len(set(names.values())) != 2 or not all(names.values()):
            problems.append("R1/R2 姓名为空或重复")
        else:
            for cid, nm in names.items():
                if nm not in chars_text:
                    problems.append(f"{cid} 的姓名「{nm}」没有出现在 characters.md（矩阵与 a 本对不上）")
        if APPEND_HEADING_PREFIX in chars_text:
            problems.append("characters.md 已含「扩写追加」，疑似上次 expand 被中断，请先核对备份")
    if problems:
        raise ExpandRefused(problems)
    return ExpandBaseline(outline, texts["mechanism.md"], matrix, canonical_matrix_json(matrix),
                          texts, names, fingerprints)


# ─── JSON 抽取（字符串感知） ───────────────────────────────────────────

_FENCE = re.compile(r"```(?:json|JSON)?[ \t]*\n(.*?)```", re.DOTALL)


def extract_json_object(text: str, required_keys=()) -> Optional[dict]:
    cands = [m.group(1) for m in _FENCE.finditer(text or "")]
    s = text or ""
    # 行内：字符串感知的花括号计数
    i = 0
    while i < len(s) and len(cands) < 50:
        if s[i] == "{":
            depth, in_str, esc, j = 0, False, False, i
            while j < len(s):
                ch = s[j]
                if in_str:
                    if esc:
                        esc = False
                    elif ch == "\\":
                        esc = True
                    elif ch == '"':
                        in_str = False
                elif ch == '"':
                    in_str = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        cands.append(s[i:j + 1])
                        break
                j += 1
            i = j + 1 if depth == 0 and j < len(s) else i + 1
        else:
            i += 1
    for c in cands:
        try:
            data = json.loads(c, strict=False)
        except ValueError:
            continue
        if isinstance(data, dict) and all(k in data for k in required_keys):
            return data
    return None


# ─── 增量矩阵并入 ──────────────────────────────────────────────────────

DELTA_KEYS = {"new_events", "new_characters", "added_cognitions", "new_evidence"}


def build_delta_example(proto: CharacterMatrix) -> dict:
    used = set(proto.evidence)
    letters = [c for c in "DEFGHJKLMNPQ" if f"EV-{c}" not in used]
    ev_id = f"EV-{letters[0]}"
    cog = lambda state, refs=(): {"state": state, "detail": "认知说明（示例）", "evidence_refs": list(refs)}
    new_chars = {}
    for k, cid in enumerate(NEW_IDS):
        cogs = {e: cog("否") for e in ALL_EVENTS}
        cogs[NEW_EVENTS[k]] = cog("知", [ev_id] if k == 0 else [])
        cogs["E1"] = cog("疑")
        new_chars[cid] = {"name": f"新角色{cid}姓名（示例）".replace("示例", "占位"),
                          "role": "社会身份（占位）", "public_relationship": "公开关系（占位）",
                          "event_cognitions": cogs}
    added = {cid: {e: cog("疑" if e == "E4" else "否") for e in NEW_EVENTS} for cid in ORIGINAL_IDS}
    return {
        "new_events": {e: {"title": f"{e} 新事件标题（占位）", "summary": f"{e} 事件摘要（占位）"} for e in NEW_EVENTS},
        "new_characters": new_chars,
        "added_cognitions": added,
        "new_evidence": {ev_id: {"name": "新证据名（占位）", "description": "证据描述（占位）",
                                 "source_event": "E4", "source_character": "R3",
                                 "chain_role": "指向 R3（占位）", "points_to": "R3"}},
    }


@dataclass(frozen=True)
class MergedMatrix:
    matrix: CharacterMatrix
    new_events: Mapping


def _cell_problems(label: str, cells, events, problems: list) -> dict:
    out = {}
    if not isinstance(cells, dict) or set(cells) != set(events):
        problems.append(f"{label} 的事件键必须恰为 {'、'.join(events)}")
        return out
    for e, c in cells.items():
        try:
            out[e] = CognitiveState.model_validate(c)
        except Exception as ex:  # noqa: BLE001
            problems.append(f"{label} {e} 的认知单元格不合法：{str(ex).splitlines()[0]}")
    return out


def merge_delta(proto: CharacterMatrix, text: str, outline: str = "") -> MergedMatrix:
    data = extract_json_object(text, required_keys=("new_characters",))
    if data is None:
        raise ExpandContractError(["响应里没有可解析的增量 JSON（可能被 4096 输出上限截断、格式错误或没有 JSON）"])
    problems: list = []
    if set(data) != DELTA_KEYS:
        problems.append("顶层键必须恰为 new_events、new_characters、added_cognitions、new_evidence")
        raise ExpandContractError(problems)
    ev = data["new_events"]
    new_events: dict = {}
    if not isinstance(ev, dict) or set(ev) != set(NEW_EVENTS):
        problems.append("new_events 键必须恰为 E4-E7")
    else:
        for e, v in ev.items():
            if (not isinstance(v, dict) or not isinstance(v.get("title"), str) or not isinstance(v.get("summary"), str)
                    or not v["title"].strip() or not v["summary"].strip()):
                problems.append(f"{e} 缺少 title 或 summary（须为非空字符串）")
            else:
                new_events[e] = (v["title"].strip(), v["summary"].strip())
    nc = data["new_characters"]
    new_entries: dict = {}
    if not isinstance(nc, dict) or set(nc) != set(NEW_IDS):
        problems.append("new_characters 键必须恰为 R3-R6")
    else:
        for cid, c in nc.items():
            if not isinstance(c, dict):
                problems.append(f"{cid} 不是对象")
                continue
            extra = set(c) - set(CharacterEntry.model_fields)
            if extra:
                problems.append(f"{cid} 含未知字段：{'、'.join(sorted(extra))}")
            if c.get("character_id", cid) != cid:
                problems.append(f"{cid} 的 character_id 与键不一致")
            for f in ("name", "role", "public_relationship"):
                if not isinstance(c.get(f), str) or not c[f].strip():
                    problems.append(f"{cid} 缺少 {f}（须为非空字符串）")
            cells = _cell_problems(cid, c.get("event_cognitions"), ALL_EVENTS, problems)
            if cells and all(v.state == "否" for v in cells.values()):
                problems.append(f"{cid} 的认知全是「否」")
            if cells and len(cells) == len(ALL_EVENTS) and not any(cells[e].state != "否" for e in NEW_EVENTS) :
                problems.append(f"{cid} 在新增事件 E4-E7 中全是「否」")
            if not problems:
                try:
                    new_entries[cid] = CharacterEntry(
                        **{**{k: v for k, v in c.items() if k in CharacterEntry.model_fields},
                           "character_id": cid, "event_cognitions": cells})
                except Exception as ex:  # noqa: BLE001 - 类型错误一律是契约问题，不是内部异常
                    problems.append(f"{cid} 不合法：{str(ex).splitlines()[0]}")
    ad = data["added_cognitions"]
    added: dict = {}
    if not isinstance(ad, dict) or set(ad) != set(ORIGINAL_IDS):
        problems.append("added_cognitions 键必须恰为 R1/R2")
    else:
        for cid, cells in ad.items():
            got = _cell_problems(f"added_cognitions.{cid}", cells, NEW_EVENTS, problems)
            if got and all(v.state == "否" for v in got.values()):
                problems.append(f"{cid} 在 E4-E7 中全是「否」，没有补齐原有角色在新事件中的视角")
            added[cid] = got
    ne = data["new_evidence"]
    new_ev: dict = {}
    if not isinstance(ne, dict) or not 1 <= len(ne) <= 6:
        problems.append("new_evidence 需要 1-6 条")
    else:
        for eid, item in ne.items():
            if eid in proto.evidence:
                problems.append(f"新证据 {eid} 与原型证据 id 冲突")
                continue
            try:
                if isinstance(item, dict) and item.get("evidence_id", eid) != eid:
                    raise ValueError("evidence_id 与键不一致")
                new_ev[eid] = EvidenceItem.model_validate({**item, "evidence_id": eid})
            except Exception as ex:  # noqa: BLE001
                problems.append(f"新证据 {eid} 不合法：{str(ex).splitlines()[0]}")
    names = [proto.characters[c].name.strip() for c in ORIGINAL_IDS] + [
        str(nc[c].get("name", "")).strip() for c in NEW_IDS if isinstance(nc, dict) and isinstance(nc.get(c), dict)]
    if len({_sq(n) for n in names}) != len(names):
        problems.append("六位角色姓名去空白后必须互不相同")
    for n in names:
        if "【" in n or "】" in n or "示例" in n:
            problems.append(f"姓名含非法字符或示例占位：{n}")
    if problems:
        raise ExpandContractError(problems)

    full = copy.deepcopy(proto.model_dump())
    for cid in ORIGINAL_IDS:
        for e, cell in added[cid].items():
            full["characters"][cid]["event_cognitions"][e] = cell.model_dump()
    for cid, entry in new_entries.items():
        full["characters"][cid] = entry.model_dump()
    full["evidence"] = {**full["evidence"], **{k: v.model_dump() for k, v in new_ev.items()}}
    full.update(char_count=6, event_count=7, is_prototype=False)
    try:
        matrix = validate_generated_matrix(full, char_count=6, event_count=7, is_prototype=False, brief_content=outline)
    except MatrixContractError as e:
        raise ExpandContractError(e.problems) from e
    drift = verify_prototype_retained(proto, matrix)
    if drift:
        raise ExpandContractError(drift)
    matrix.meta.note = "Expanded by expand; prototype cells retained; passed matrix contract validation"
    return MergedMatrix(matrix, new_events)


def _sq(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def verify_prototype_retained(proto: CharacterMatrix, full: CharacterMatrix) -> list:
    out = []
    for cid in ORIGINAL_IDS:
        a, b = proto.characters[cid], full.characters.get(cid)
        if b is None:
            out.append(f"{cid} 丢失")
            continue
        for e in PROTO_EVENTS:
            if a.event_cognitions[e] != b.event_cognitions.get(e):
                out.append(f"{cid} 的原型认知 {e} 被改动")
        da, db = a.model_dump(exclude={"event_cognitions"}), b.model_dump(exclude={"event_cognitions"})
        if da != db:
            out.append(f"{cid} 的原型字段被改动")
    for eid, item in proto.evidence.items():
        if full.evidence.get(eid) != item:
            out.append(f"原型证据 {eid} 被改动或丢失")
    return out


def render_matrix_markdown(matrix: CharacterMatrix, new_events: Mapping) -> str:
    L = ["# 信息矩阵（expand 后：6 人 × 7 事件）", "",
         "> E1-E3 与 R1/R2 在这三个事件中的原认知保持不变；E4-E7 为 expand 新增（只续写，晚于 E3）。", "",
         "## 事件", ""]
    for e in PROTO_EVENTS:
        L.append(f"- {e}：原型事件，定义见 mechanism.md 与原型剧本，未改动")
    for e in NEW_EVENTS:
        t, s = new_events[e]
        L.append(f"- {e}：{t} — {s}")
    L += ["", "## 认知矩阵", "", "| | " + " | ".join(ALL_IDS) + " |", "|" + "---|" * 7]
    for e in ALL_EVENTS:
        L.append(f"| {e} | " + " | ".join(matrix.characters[c].event_cognitions[e].state for c in ALL_IDS) + " |")
    L += ["", "## 角色", ""] + [f"- {c}：{matrix.characters[c].name}（{matrix.characters[c].role}）" for c in ALL_IDS]
    L += ["", "## 证据", "", "| 证据ID | 名称 | 来源事件 | 持有者 | 指向 |", "|---|---|---|---|---|"]
    for eid, it in matrix.evidence.items():
        L.append(f"| {eid} | {it.name} | {it.source_event} | {it.source_character} | {it.points_to} |")
    L += ["", "## 完整 JSON", "", "```json",
          json.dumps(matrix.model_dump(mode="json", exclude={"meta"}), ensure_ascii=False, indent=1), "```", ""]
    return "\n".join(L)


# ─── 逐步校验器（返回可直接展示的中文问题列表） ────────────────────────

_HEADING = re.compile(r"^\s*#{1,6}\s*(.+)$", re.MULTILINE)
_TAG = re.compile(r"[\[【]\s*E(\d{1,2})\s*[\]】]")


def _headings(text: str) -> list:
    return [m.group(1) for m in _HEADING.finditer(text or "")]


def check_headings(text: str, name: str, keywords) -> list:
    hs = _headings(text)
    out = []
    if not any(f"【{name}】" in h for h in hs):
        out.append(f"缺少含「【{name}】」的标题")
    for kw in keywords:
        if not any(kw in h for h in hs):
            out.append(f"缺少标题「{kw}」")
    return out


def foreign_headings(text: str, other_names) -> list:
    return [f"混入了其他角色「{n}」的标题" for n in other_names if any(f"【{n}】" in h for h in _headings(text))]


def event_tags(text: str) -> set:
    return {f"E{int(m.group(1))}" for m in _TAG.finditer(text or "")}


def check_event_tags(text: str, cells: Mapping, required) -> list:
    tags = event_tags(text)
    out = []
    for t in sorted(tags - set(ALL_EVENTS)):
        out.append(f"出现未定义的事件标签 {t}")
    for t in sorted(tags & set(ALL_EVENTS)):
        if cells.get(t) == "否":
            out.append(f"提到了矩阵中该角色为「否」的事件 {t}（穿帮）")
    for t in required:
        if t not in tags:
            out.append(f"矩阵中该角色「知」的事件 {t} 没有出现标签 [{t}]")
    return out


def check_tail(text: str, last_marker: str, min_chars: int = 30) -> list:
    idx = (text or "").rfind(last_marker)
    if idx < 0:
        return [f"缺少「{last_marker}」，疑似被单次输出上限 4096 tokens 截断"]
    rest = text[idx + len(last_marker):].strip()
    if len(rest) < min_chars:
        return [f"「{last_marker}」之后正文不足 {min_chars} 字，疑似被单次输出上限 4096 tokens 截断"]
    return []


# ─── 候选组装与终闸 ───────────────────────────────────────────────────

def append_section(original: str, heading: str, body: str) -> str:
    joiner = "" if original.endswith("\n\n") else ("\n" if original.endswith("\n") else "\n\n")
    return f"{original}{joiner}# {heading}\n\n{body.strip()}\n"


@dataclass
class ExpandCandidate:
    texts: dict

    def files(self) -> dict:
        return dict(self.texts)


def assemble_candidate(base: ExpandBaseline, merged: MergedMatrix, parts: Mapping) -> ExpandCandidate:
    join = lambda d, ids: "\n\n".join(d[i].strip() for i in ids)
    chars = append_section(base.texts["characters.md"], f"{APPEND_HEADING_PREFIX}：原有角色在新增事件（E4-E7）中的视角", join(parts["asupp"], ORIGINAL_IDS))
    chars = append_section(chars, f"{APPEND_HEADING_PREFIX}：新增角色 a本（R3-R6）", join(parts["a"], NEW_IDS))
    bg = append_section(base.texts["background.md"], f"{APPEND_HEADING_PREFIX}：新增角色背景设定（R3-R6）", join(parts["bg"], NEW_IDS))
    sb = append_section(base.texts["scripts_b.md"], f"{APPEND_HEADING_PREFIX}：原有角色 b本补充", join(parts["bsupp"], ORIGINAL_IDS))
    sb = append_section(sb, f"{APPEND_HEADING_PREFIX}：新增角色 b本（R3-R6）", join(parts["b"], NEW_IDS))
    return ExpandCandidate({
        "characters.md": chars, "background.md": bg, "scripts_b.md": sb,
        "dm_manual.md": parts["dm"].strip() + "\n", "endings.md": parts["endings"].strip() + "\n",
        "information_matrix.md": render_matrix_markdown(merged.matrix, merged.new_events),
        MATRIX_REL: merged.matrix.model_dump_json(ensure_ascii=False, indent=2),
    })


def verify_candidate(base: ExpandBaseline, files: Mapping) -> list:
    """结构契约终闸：提交前用候选，提交后用磁盘读回。不是语义一致性证明。"""
    out: list = []
    for rel in APPEND_ONLY:
        if not files.get(rel, "").startswith(base.texts[rel]):
            out.append(f"{rel} 不是以原文开头（原文没有被逐字保留）")
    for rel in (*STAGE_2_FILES, MATRIX_REL):
        if not str(files.get(rel, "")).strip():
            out.append(f"{rel} 为空")
    if out:
        return out
    try:
        matrix = validate_generated_matrix(json.loads(files[MATRIX_REL]), char_count=6, event_count=7,
                                           is_prototype=False, brief_content=base.outline)
    except MatrixContractError as e:
        return [f"矩阵 JSON 未通过校验：{p}" for p in e.problems]
    except ValueError as e:
        return [f"矩阵 JSON 无法解析：{e}"]
    out += verify_prototype_retained(base.matrix, matrix)
    names = {c: matrix.characters[c].name for c in ALL_IDS}
    for rel in ("characters.md", "scripts_b.md", "dm_manual.md", "information_matrix.md"):
        for c, n in names.items():
            if n not in files[rel]:
                out.append(f"{rel} 中没有角色 {c}（{n}）")
    for c in NEW_IDS:
        if names[c] not in files["background.md"]:
            out.append(f"background.md 中没有新增角色 {c}（{names[c]}）")
    dm = files["dm_manual.md"]
    for e in ALL_EVENTS:
        if e not in dm:
            out.append(f"dm_manual.md 缺少事件 {e}")
        if e not in files["information_matrix.md"]:
            out.append(f"information_matrix.md 缺少事件 {e}")
    for eid, it in matrix.evidence.items():
        if eid not in dm and it.name not in dm:
            out.append(f"dm_manual.md 没有提到证据 {eid}")
        if eid not in files["information_matrix.md"]:
            out.append(f"information_matrix.md 缺少证据 {eid}")
    if not all(x in files["endings.md"].replace(" ", "") for x in ("结局A", "结局B", "结局C")):
        out.append("endings.md 缺少结局A/B/C")
    for rel in ("dm_manual.md", "endings.md", "information_matrix.md"):
        if "{{" in files[rel]:
            out.append(f"{rel} 含残留 {{{{ }}}}")
    return out
