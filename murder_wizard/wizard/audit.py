"""审计合同（R05/R06）：材料、结构化问题、解析、豁免、状态、报告、作者接受的修复。

纯逻辑模块：不依赖 rich / PhaseRunner / LLM，不 mkdir、不实例化 TruthFileManager。
"通过"只表示模型在已覆盖材料上未报告 P0，不等于没有穿帮。
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, Mapping, Optional

from murder_wizard.wizard.truth_files import MatrixContractError, validate_generated_matrix

SCHEMA_TAG = "audit-issues/1"
FIX_SCHEMA_TAG = "audit-fixes/1"
ROUNDS = ("matrix", "mechanism", "ending")
ROUND_NUMBER = {"matrix": 1, "mechanism": 2, "ending": 3}
ROUND_PREFIX = {"matrix": "MX", "mechanism": "MC", "ending": "ED", "static": "ST"}
ROUND_TITLE = {"matrix": "信息矩阵逐格", "mechanism": "机制一致性", "ending": "结局合理性"}
SEVERITIES = ("P0", "P1", "P2")
MAX_ISSUES_PER_ROUND = 8
MAX_FIXES = 6
AUDIT_FILES = ("mechanism.md", "characters.md", "scripts_b.md", "dm_manual.md", "endings.md", "background.md")
MATRIX_NAME = "character_matrix.json"
MATRIX_REL = Path("state") / MATRIX_NAME
ROUND_FILES = {
    "matrix": (MATRIX_NAME, "characters.md", "scripts_b.md", "background.md"),
    "mechanism": ("mechanism.md", MATRIX_NAME, "characters.md", "scripts_b.md", "dm_manual.md"),
    "ending": ("mechanism.md", MATRIX_NAME, "characters.md", "scripts_b.md", "dm_manual.md", "endings.md"),
}
EDITABLE_FILES = ("characters.md", "scripts_b.md", "dm_manual.md", "endings.md")
# is_prototype -> (角色数, 最少事件, 最多事件)
EXPECTED_SHAPE = {True: (2, 3, 3), False: (6, 5, 7)}
BLOCK_VAR = {
    "mechanism.md": "mechanism_block", MATRIX_NAME: "matrix_block", "characters.md": "characters_block",
    "scripts_b.md": "scripts_b_block", "dm_manual.md": "dm_manual_block",
    "endings.md": "endings_block", "background.md": "background_block",
}
ALL_INPUTS = (*AUDIT_FILES[:1], MATRIX_NAME, *AUDIT_FILES[1:])
NOT_COVERED = ("information_matrix.md（模型原始响应，矩阵以 state/character_matrix.json 为准）",
               "创意简报（只通过 mechanism.md 间接体现）")


class AuditStatus(str, Enum):
    PASSED = "passed"
    WAIVED = "waived"
    BLOCKED = "blocked"
    INCOMPLETE = "incomplete"

    @property
    def label(self) -> str:
        return {"passed": "模型未报告 P0", "waived": "已豁免",
                "blocked": "未通过", "incomplete": "未完成"}[self.value]


class AuditParseError(ValueError):
    pass


# ─── 材料 ────────────────────────────────────────────────────────────────

def _sha12(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:12]


def _tokens(text: str) -> tuple[str, str]:
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return h[:4], h[4:8]


@dataclass(frozen=True)
class MaterialRecord:
    name: str
    present: bool
    chars: int
    sha12: str
    problem: str = ""


@dataclass(frozen=True)
class AuditMaterials:
    is_prototype: bool
    char_count: int
    event_count: int
    texts: Mapping[str, str]
    records: tuple
    char_names: Mapping[str, str]
    problems: tuple
    notes: tuple = ()

    @property
    def auditable(self) -> bool:
        return not self.problems

    @classmethod
    def from_dir(cls, root: Path, *, is_prototype: bool) -> "AuditMaterials":
        root = Path(root)
        raw_texts: dict[str, tuple[Optional[str], bytes, str]] = {}
        for name in AUDIT_FILES:
            path = root / name
            if not path.exists():
                raw_texts[name] = (None, b"", f"缺少 {name}")
                continue
            try:
                data = path.read_bytes()
            except OSError as e:
                raw_texts[name] = (None, b"", f"无法读取 {name}：{e}")
                continue
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                raw_texts[name] = (None, data, f"无法按 UTF-8 读取 {name}")
                continue
            if not text.strip():
                raw_texts[name] = (None, data, f"{name} 为空")
                continue
            raw_texts[name] = (text, data, "")
        matrix_bytes = b""
        matrix_raw = None
        matrix_problem = ""
        mpath = root / MATRIX_REL
        if not mpath.exists():
            matrix_problem = (f"缺少 {MATRIX_REL.as_posix()}（本工具不会自动转换旧作品，"
                              "请先重新生成阶段 2 或由作者显式导入）")
        else:
            try:
                matrix_bytes = mpath.read_bytes()
                matrix_raw = json.loads(matrix_bytes.decode("utf-8"))
            except (OSError, UnicodeDecodeError, ValueError) as e:
                matrix_problem = f"{MATRIX_REL.as_posix()} 无法解析：{e}"
        return cls._build(raw_texts, matrix_raw, matrix_bytes, matrix_problem, is_prototype)

    @classmethod
    def from_texts(cls, texts: Mapping[str, str], matrix_raw, *, is_prototype: bool) -> "AuditMaterials":
        raw: dict[str, tuple[Optional[str], bytes, str]] = {}
        for name in AUDIT_FILES:
            text = texts.get(name)
            if text is None:
                raw[name] = (None, b"", f"缺少 {name}")
            elif not str(text).strip():
                raw[name] = (None, b"", f"{name} 为空")
            else:
                raw[name] = (text, text.encode("utf-8"), "")
        problem = ""
        data = b""
        parsed = None
        if matrix_raw is None:
            problem = f"缺少 {MATRIX_REL.as_posix()}"
        elif isinstance(matrix_raw, str):
            data = matrix_raw.encode("utf-8")
            try:
                parsed = json.loads(matrix_raw)
            except ValueError as e:
                problem = f"矩阵 JSON 无法解析：{e}"
        else:
            parsed = dict(matrix_raw)
            data = json.dumps(parsed, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return cls._build(raw, parsed, data, problem, is_prototype)

    @classmethod
    def _build(cls, raw, matrix_raw, matrix_bytes, matrix_problem, is_prototype) -> "AuditMaterials":
        problems: list[str] = []
        records: list[MaterialRecord] = []
        texts: dict[str, str] = {}
        for name in AUDIT_FILES:
            text, data, problem = raw[name]
            if problem:
                problems.append(problem)
            else:
                texts[name] = text
            records.append(MaterialRecord(name, text is not None, len(text or ""), _sha12(data) if data else "", problem))
        expected_chars, lo, hi = EXPECTED_SHAPE[bool(is_prototype)]
        char_count, event_count = expected_chars, 0
        char_names: dict[str, str] = {}
        mproblem = matrix_problem
        if not mproblem:
            if not isinstance(matrix_raw, dict):
                mproblem = "矩阵 JSON 不是对象"
            elif isinstance(matrix_raw.get("event_count"), bool) or not isinstance(matrix_raw.get("event_count"), int):
                mproblem = "矩阵 event_count 缺失或不是整数"
            else:
                event_count = matrix_raw["event_count"]
                try:
                    model = validate_generated_matrix(
                        matrix_raw, char_count=expected_chars, event_count=event_count,
                        is_prototype=bool(is_prototype),
                    )
                except MatrixContractError as e:
                    ps = list(e.problems)
                    extra = f"；另有 {len(ps) - 5} 项" if len(ps) > 5 else ""
                    mproblem = "矩阵未通过校验：" + "；".join(ps[:5]) + extra
                except ValueError as e:
                    mproblem = f"矩阵未通过校验：{e}"
                else:
                    if not lo <= event_count <= hi:
                        mproblem = f"矩阵事件数 {event_count} 不在该作品状态允许的 {lo}-{hi} 内"
                    else:
                        char_names = {cid: c.name for cid, c in model.characters.items()}
                        dumped = json.dumps(model.model_dump(mode="json", exclude={"meta"}),
                                            ensure_ascii=False, indent=1)
                        texts[MATRIX_NAME] = dumped
        if mproblem:
            problems.append(mproblem)
        records.append(MaterialRecord(MATRIX_NAME, not matrix_problem, len(texts.get(MATRIX_NAME, "")),
                                      _sha12(matrix_bytes) if matrix_bytes else "", mproblem))
        return cls(bool(is_prototype), char_count, event_count, texts, tuple(records),
                   char_names, tuple(problems))

    def block(self, name: str) -> str:
        text = self.texts[name]
        s, e = _tokens(text)
        return f"<<<FILE {name} · 开始标记 {s}>>>\n{text}\n<<<END {name} · 结束标记 {e}>>>"

    def blocks_for(self, kind: str) -> dict:
        return {BLOCK_VAR[n]: self.block(n) for n in ROUND_FILES[kind]}

    def expected_seen(self, kind: str) -> dict:
        return {n: "".join(_tokens(self.texts[n])) for n in ROUND_FILES[kind]}

    def round_chars(self, kind: str) -> int:
        return sum(len(self.texts.get(n, "")) for n in ROUND_FILES[kind])


# ─── 问题与结果 ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AuditIssue:
    ref: str
    key: str
    round: str
    source: str
    severity: str
    dimension: str
    characters: tuple
    events: tuple
    file: str
    anchor: str
    quote: str
    problem: str
    fix: str
    location: str
    waived: bool = False
    waiver_note: str = ""


@dataclass
class RoundResult:
    round: str
    status: str = "not_run"   # ok | truncated | parse_error | call_failed | render_failed | not_run
    issues: tuple = ()
    has_more: bool = False
    reason: str = ""
    raw: str = ""
    hints: tuple = ()
    prompt_chars: int = 0
    cost: float = 0.0


@dataclass(frozen=True)
class FixProposal:
    fid: str
    issue_refs: tuple
    file: str
    find: str
    replace: str
    rationale: str
    applicable: bool
    reason: str = ""
    matched: str = ""
    start: int = -1
    end: int = -1
    line: int = 0


@dataclass
class WaiverFile:
    lines: tuple = ()
    read_error: str = ""


@dataclass
class WaiverReport:
    applied: list = field(default_factory=list)
    unused: list = field(default_factory=list)
    ambiguous: list = field(default_factory=list)
    too_short: list = field(default_factory=list)
    read_error: str = ""


@dataclass
class ApplyResult:
    applied_ids: tuple = ()
    files: tuple = ()
    backups: tuple = ()
    error: str = ""
    rolled_back: bool = False


def compute_status(*, material_problems, rounds: Mapping[str, RoundResult], issues, report_error: str = "") -> AuditStatus:
    if material_problems:
        return AuditStatus.INCOMPLETE
    if any(i.severity == "P0" and not i.waived for i in issues):
        return AuditStatus.BLOCKED
    if any(r.status != "ok" for r in rounds.values()):
        return AuditStatus.INCOMPLETE
    if report_error:
        return AuditStatus.INCOMPLETE
    if any(i.severity == "P0" and i.waived for i in issues):
        return AuditStatus.WAIVED
    return AuditStatus.PASSED


@dataclass
class AuditOutcome:
    materials: AuditMaterials
    rounds: dict
    model: str = ""
    forced: bool = False
    static_issues: list = field(default_factory=list)
    issue_list: list = field(default_factory=list)
    waiver: WaiverReport = field(default_factory=WaiverReport)
    proposals: list = field(default_factory=list)
    unfixable: list = field(default_factory=list)
    fix_note: str = ""
    notes: list = field(default_factory=list)
    cost: float = 0.0
    report_path: Optional[Path] = None
    report_error: str = ""
    applied: Optional[ApplyResult] = None

    @classmethod
    def start(cls, materials: AuditMaterials, *, model: str = "", forced: bool = False) -> "AuditOutcome":
        return cls(materials=materials, rounds={k: RoundResult(k) for k in ROUNDS}, model=model, forced=forced)

    @property
    def issues(self) -> list:
        return self.issue_list

    @property
    def p0_unwaived(self) -> list:
        return [i for i in self.issue_list if i.severity == "P0" and not i.waived]

    @property
    def p0_waived(self) -> list:
        return [i for i in self.issue_list if i.severity == "P0" and i.waived]

    def counts(self) -> dict:
        return {s: sum(1 for i in self.issue_list if i.severity == s) for s in SEVERITIES}

    @property
    def complete(self) -> bool:
        return not self.materials.problems and all(r.status == "ok" for r in self.rounds.values())

    @property
    def status(self) -> AuditStatus:
        return compute_status(material_problems=self.materials.problems, rounds=self.rounds,
                              issues=self.issue_list, report_error=self.report_error)

    @property
    def exit_code(self) -> int:
        return {AuditStatus.PASSED: 0, AuditStatus.WAIVED: 0,
                AuditStatus.BLOCKED: 1, AuditStatus.INCOMPLETE: 2}[self.status]

    @property
    def headline(self) -> str:
        st = self.status
        c = self.counts()
        if st is AuditStatus.PASSED:
            return f"审计完成：模型未报告 P0（P1 {c['P1']} / P2 {c['P2']}）。这是模型审计结果，不是没有穿帮的证明。"
        if st is AuditStatus.WAIVED:
            return f"P0 共 {len(self.p0_waived)} 个，均由作者在 .known_p0 逐项豁免；结论不是“通过”。"
        if st is AuditStatus.BLOCKED:
            return f"审计未通过：{len(self.p0_unwaived)} 个 P0 未解决（{len(self.p0_waived)} 个已豁免）"
        return "审计未完成：" + self.incomplete_reason() + "。这不是通过。"

    def incomplete_reason(self) -> str:
        if self.materials.problems:
            return "；".join(self.materials.problems)
        bad = [f"第{ROUND_NUMBER[k]}轮{ROUND_TITLE[k]} {r.status}" + (f"（{r.reason}）" if r.reason else "")
               for k, r in self.rounds.items() if r.status != "ok"]
        if bad:
            return "；".join(bad)
        if self.report_error:
            return f"审计报告写入失败：{self.report_error}"
        return ""

    def __bool__(self) -> bool:
        return self.status is AuditStatus.PASSED

    def to_summary_dict(self) -> dict:
        return {"status": self.status.value, "complete": self.complete,
                "p0_unresolved": len(self.p0_unwaived), "p0_waived": len(self.p0_waived),
                "counts": self.counts(), "cost": self.cost, "model": self.model,
                "report_file": "audit_report.md"}


# ─── 位置、键、静态检查 ──────────────────────────────────────────────────

def _squash(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def _norm_dimension(text: str) -> str:
    return re.sub(r"^维度\d*[：:]", "", _squash(text))


def _ws_pattern(text: str) -> "re.Pattern":
    chars = [c for c in text if not c.isspace()]
    return re.compile(r"\s*".join(re.escape(c) for c in chars))


def _find_all(text: str, needle: str) -> list:
    if len([c for c in needle if not c.isspace()]) == 0:
        return []
    return [m.span() for m in _ws_pattern(needle).finditer(text)]


def issue_key(round_id: str, dimension: str, file: str, location: str, quote: str, anchor: str,
              characters, events, problem: str) -> str:
    if location == "verified":
        where = _squash(quote)
    else:
        where = _squash(anchor)
    # 同一句引文上可有多个不同 P0：角色、事件、问题描述都进 key，豁免才能逐项匹配
    basis = (f"{round_id}|{_norm_dimension(dimension)}|{file}|{where}|"
             f"{','.join(sorted(characters))}|{','.join(sorted(events))}|{_squash(problem)}")
    return "AUD-" + hashlib.sha256(basis.encode("utf-8")).hexdigest()[:8]


def run_static_checks(materials: AuditMaterials) -> list:
    """确定性检查：矩阵里的每个角色姓名必须出现在 a 本；b 本/DM 手册缺失为 P1。"""
    out: list = []
    for cid, name in sorted(materials.char_names.items()):
        sq = _squash(name)
        if not sq:
            continue
        for file, sev in (("characters.md", "P0"), ("scripts_b.md", "P1"), ("dm_manual.md", "P1")):
            if file in materials.texts and sq not in _squash(materials.texts[file]):
                dim = "角色完整性"
                problem = f"矩阵中的角色 {cid}（{name}）没有出现在 {file}"
                out.append(AuditIssue(
                    ref="", key=issue_key("static", dim, file, "static", "", "", (cid,), (), f"{cid}|{name}"),
                    round="static", source="static", severity=sev, dimension=dim, characters=(cid,), events=(),
                    file=file, anchor="全文", quote="", problem=problem,
                    fix=f"补全 {name} 在 {file} 中的内容；若只是称呼不同请核对后按键豁免", location="verified"))
    return out


# ─── 输出合同与解析 ──────────────────────────────────────────────────────

def output_contract(kind: str, materials: AuditMaterials) -> str:
    seen = {n: "<开始标记+结束标记>" for n in ROUND_FILES[kind]}
    skeleton = json.dumps({"schema": SCHEMA_TAG, "round": kind, "files_seen": seen,
                           "has_more": False, "issues": []}, ensure_ascii=False)
    files = "、".join(ROUND_FILES[kind])
    return (
        "【输出合同】只输出一个 json 代码块，块外不要写任何文字。骨架（issues 为空数组，请按需填入）：\n"
        f"```json\n{skeleton}\n```\n"
        f"- files_seen：对本轮每个文件（{files}）回填其块头“开始标记”与块尾“结束标记”拼成的 8 位十六进制串，"
        "用来证明你看到了每份文件的开头和结尾。\n"
        f"- 每条 issue 字段：severity（只能是 P0、P1、P2）、dimension、characters（如 [\"R1\"]，可空）、"
        "events（如 [\"E2\"]，可空）、location{file（必须是上面列出的文件名之一）, anchor（可检索的位置描述）, "
        "quote（逐字摘录，至多 60 字，可空）}、problem（至多 80 字）、fix（至多 60 字）。\n"
        f"- 至多 {MAX_ISSUES_PER_ROUND} 条，按严重度降序；还有未列出的问题则 has_more 填 true，否则 false。"
    )


@dataclass
class ParsedRound:
    issues: tuple
    has_more: bool
    prose: str


_FENCE_RE = re.compile(r"```(?:json|JSON)?[ \t]*\n(.*?)```", re.DOTALL)


def scan_prose_p0(text: str) -> list:
    hits = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("|") and any(c.strip().strip("*").strip() == "P0" for c in s.split("|")):
            hits.append(s)
        elif "[P0]" in s or "**P0**" in s or re.search(r"P0\s*[:：]\s*[1-9]", s):
            hits.append(s)
    return hits


def hint_lines(text: str) -> tuple:
    return tuple(h[:120] for h in scan_prose_p0(text)[:5])


def _str_list(value, label: str, idx: int) -> tuple:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise AuditParseError(f"第 {idx} 条 {label} 必须是字符串列表")
    return tuple(v.strip() for v in value)


def _extract_block(kind: str, text: str) -> tuple:
    blocks = [(m.group(1), m.span()) for m in _FENCE_RE.finditer(text) if SCHEMA_TAG in m.group(1)]
    if len(blocks) > 1:
        raise AuditParseError(f"响应里有 {len(blocks)} 个审计结果块，只允许 1 个")
    if blocks:
        body, (a, b) = blocks[0]
        return body, text[:a] + text[b:]
    stripped = text.strip()
    if stripped.startswith("{") and SCHEMA_TAG in stripped:
        return stripped, ""
    if SCHEMA_TAG in text:
        raise AuditParseError("找到审计标记但没有完整结果块，输出可能被截断")
    raise AuditParseError("未找到审计结果块")


def parse_round_output(kind: str, text: str, materials: AuditMaterials) -> ParsedRound:
    body, prose = _extract_block(kind, text or "")
    try:
        data = json.loads(body, strict=False)
    except ValueError as e:
        raise AuditParseError(f"结果块不是合法 JSON：{e}") from e
    if not isinstance(data, dict):
        raise AuditParseError("结果块顶层必须是对象")
    if data.get("schema") != SCHEMA_TAG:
        raise AuditParseError(f"schema 必须是 {SCHEMA_TAG}")
    if data.get("round") != kind:
        raise AuditParseError(f"round 应为 {kind}，实际为 {data.get('round')!r}")
    has_more = data.get("has_more")
    if not isinstance(has_more, bool):
        raise AuditParseError("has_more 缺失或不是布尔值")
    seen = data.get("files_seen")
    expected = materials.expected_seen(kind)
    if not isinstance(seen, dict):
        raise AuditParseError("files_seen 缺失")
    for name, token in expected.items():
        got = re.sub(r"[^0-9a-f]", "", str(seen.get(name, "")).lower())
        if got != token:
            raise AuditParseError(f"files_seen 对 {name} 的回显标记不符，模型可能没有看到完整材料（提供商静默截断？）")
    raw_issues = data.get("issues")
    if not isinstance(raw_issues, list):
        raise AuditParseError("issues 必须是列表")
    parsed: list = []
    for idx, item in enumerate(raw_issues, 1):
        if not isinstance(item, dict):
            raise AuditParseError(f"第 {idx} 条不是对象")
        sev = str(item.get("severity", "")).strip().upper()
        if sev not in SEVERITIES:
            raise AuditParseError(f"第 {idx} 条 severity 必须是 P0/P1/P2，实际为 {item.get('severity')!r}")
        dim, problem = item.get("dimension"), item.get("problem")
        if not isinstance(dim, str) or not dim.strip() or not isinstance(problem, str) or not problem.strip():
            raise AuditParseError(f"第 {idx} 条缺少 dimension 或 problem")
        loc = item.get("location")
        if not isinstance(loc, dict) or not isinstance(loc.get("file"), str) or not loc["file"].strip() \
                or not isinstance(loc.get("anchor"), str) or not loc["anchor"].strip():
            raise AuditParseError(f"第 {idx} 条 location 必须含 file 与 anchor")
        chars = _str_list(item.get("characters"), "characters", idx)
        events = _str_list(item.get("events"), "events", idx)
        quote = loc.get("quote") if isinstance(loc.get("quote"), str) else ""
        fix = item.get("fix") if isinstance(item.get("fix"), str) else ""
        file = loc["file"].strip()
        if file not in materials.texts:
            location = "unknown_file"
        elif len(_squash(quote)) < 4:
            location = "no_quote"
        else:
            n = len(_find_all(materials.texts[file], quote))
            location = "verified" if n == 1 else ("quote_not_found" if n == 0 else "ambiguous")
        key = issue_key(kind, dim, file, location, quote, loc["anchor"], chars, events, problem)
        parsed.append(AuditIssue(ref="", key=key, round=kind, source="model", severity=sev,
                                 dimension=dim.strip(), characters=chars, events=events, file=file,
                                 anchor=loc["anchor"].strip(), quote=quote.strip(), problem=problem.strip(),
                                 fix=fix.strip(), location=location))
    if not any(i.severity == "P0" for i in parsed) and scan_prose_p0(prose):
        raise AuditParseError("正文提到 P0，但结构化结果里没有 P0")
    seen_keys, dedup = set(), []
    for i in parsed:
        k = (i.key, i.severity, _squash(i.problem))
        if k not in seen_keys:
            seen_keys.add(k)
            dedup.append(i)
    return ParsedRound(tuple(dedup), has_more, prose)


# ─── 豁免 ────────────────────────────────────────────────────────────────

_KEY_LINE_RE = re.compile(r"^(AUD-[0-9a-f]{8})(?:\s+(.*))?$")


def load_waivers(path: Path) -> WaiverFile:
    path = Path(path)
    if not path.exists():
        return WaiverFile()
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return WaiverFile(read_error=str(e))
    lines = tuple(l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith("#"))
    return WaiverFile(lines=lines)


def apply_waivers(issues: list, wf: WaiverFile) -> tuple:
    report = WaiverReport(read_error=wf.read_error)
    waived: dict = {}  # key -> note
    for line in wf.lines:
        m = _KEY_LINE_RE.match(line)
        if m:
            key, note = m.group(1), (m.group(2) or "").strip()
            hits = [i for i in issues if i.key == key]
            if any(i.severity == "P0" for i in hits):
                waived[key] = note
                report.applied.append(line)
            elif hits:
                report.unused.append(f"{line}（只有 P0 可豁免）")
            else:
                report.unused.append(line)
            continue
        sq = _squash(line)
        if len(sq) < 12:
            report.too_short.append(line)
            continue
        # 含糊判定看全部 P0（与豁免行的先后顺序无关）
        keys = {i.key for i in issues if i.severity == "P0"
                and (sq in _squash(i.problem) or sq in _squash(i.quote))}
        if len(keys) == 1:
            waived[next(iter(keys))] = line
            report.applied.append(line)
        elif len(keys) > 1:
            report.ambiguous.append(line)
        else:
            report.unused.append(line)
    out = [dataclasses.replace(i, waived=True, waiver_note=waived[i.key])
           if (i.severity == "P0" and i.key in waived) else i for i in issues]
    return out, report


def assign_refs(issues: list) -> list:
    counters: dict = {}
    out = []
    for i in issues:
        counters[i.round] = counters.get(i.round, 0) + 1
        out.append(dataclasses.replace(i, ref=f"{ROUND_PREFIX[i.round]}-{counters[i.round]}"))
    return out


# ─── 修复建议（R06）──────────────────────────────────────────────────────

def fix_contract() -> str:
    skeleton = json.dumps({"schema": FIX_SCHEMA_TAG, "fixes": [], "unfixable": []}, ensure_ascii=False)
    return (
        "【输出合同】只输出一个 json 代码块，块外不要写任何文字：\n"
        f"```json\n{skeleton}\n```\n"
        "- fixes 每项：issue_refs（如 [\"MX-1\"]）、file（只能是下列可编辑文件）、find（从文件逐字复制的原文，"
        "6-200 字，必须在该文件中唯一）、replace（替换文本，至多 400 字，不得与 find 相同）、rationale。\n"
        f"- 至多 {MAX_FIXES} 条；无法用定点替换修复的问题放进 unfixable：[{{\"issue_ref\":\"MC-2\",\"reason\":\"…\"}}]。"
    )


def parse_fix_output(text: str, issues: list, materials: AuditMaterials) -> tuple:
    """返回 (proposals, unfixable)。结构不合法抛 AuditParseError。"""
    blocks = [m.group(1) for m in _FENCE_RE.finditer(text or "") if FIX_SCHEMA_TAG in m.group(1)]
    if len(blocks) != 1:
        stripped = (text or "").strip()
        if not blocks and stripped.startswith("{") and FIX_SCHEMA_TAG in stripped:
            blocks = [stripped]
        else:
            raise AuditParseError("未找到唯一的修复结果块")
    try:
        data = json.loads(blocks[0], strict=False)
    except ValueError as e:
        raise AuditParseError(f"修复结果块不是合法 JSON：{e}") from e
    if not isinstance(data, dict) or data.get("schema") != FIX_SCHEMA_TAG or not isinstance(data.get("fixes"), list):
        raise AuditParseError("修复结果块结构不符")
    known = {i.ref for i in issues if i.file in EDITABLE_FILES}
    proposals: list = []
    spans: dict = {}
    for n, item in enumerate(data["fixes"][:MAX_FIXES], 1):
        if not isinstance(item, dict):
            raise AuditParseError(f"第 {n} 条补丁不是对象")
        refs = tuple(r for r in item.get("issue_refs", []) if isinstance(r, str)) if isinstance(item.get("issue_refs"), list) else ()
        file = item.get("file") if isinstance(item.get("file"), str) else ""
        find = item.get("find") if isinstance(item.get("find"), str) else ""
        repl = item.get("replace") if isinstance(item.get("replace"), str) else ""
        why = item.get("rationale") if isinstance(item.get("rationale"), str) else ""
        reason, start, end, matched, line = "", -1, -1, "", 0
        text_of = materials.texts.get(file, "")
        if not refs or any(r not in known for r in refs):
            reason = "issue_refs 为空或不是可修复的问题"
        elif file not in EDITABLE_FILES:
            reason = "文件不可由工具改写"
        elif not 6 <= len(_squash(find)) <= 400:
            reason = "find 长度不在 6-400 字内"
        elif not repl.strip() or _squash(repl) == _squash(find):
            reason = "replace 为空或与 find 相同"
        else:
            spans_found = _find_all(text_of, find)
            if len(spans_found) != 1:
                reason = f"find 在 {file} 中命中 {len(spans_found)} 次（需要唯一）"
            else:
                start, end = spans_found[0]
                matched = text_of[start:end]
                line = text_of.count("\n", 0, start) + 1
                if any(not (end <= s or start >= e) for s, e in spans.get(file, [])):
                    reason = "与同文件的另一条补丁区间重叠"
                else:
                    spans.setdefault(file, []).append((start, end))
        proposals.append(FixProposal(f"F{n}", refs, file, find, repl, why, not reason, reason, matched, start, end, line))
    unfixable = []
    for item in data.get("unfixable", []) if isinstance(data.get("unfixable"), list) else []:
        if isinstance(item, dict):
            unfixable.append((str(item.get("issue_ref", "")), str(item.get("reason", ""))))
    return proposals, unfixable


def apply_fixes(project: Path, materials: AuditMaterials, proposals: list, accepted_ids,
                *, now: Callable[[], datetime] = datetime.now) -> ApplyResult:
    """作者显式接受的补丁才会写入：预检全过 → 备份 → 逐文件临时文件+替换，失败回滚。"""
    project = Path(project)
    by_id = {p.fid: p for p in proposals}
    chosen = []
    for fid in accepted_ids:
        p = by_id.get(fid)
        if p is None or not p.applicable:
            return ApplyResult(error=f"{fid} 不存在或不可应用，未写入任何文件")
        chosen.append(p)
    if not chosen:
        return ApplyResult(error="没有接受任何补丁，未写入任何文件")
    rec = {r.name: r for r in materials.records}
    originals: dict = {}
    for p in chosen:
        if p.file not in originals:
            path = project / p.file
            try:
                data = path.read_bytes()
            except OSError as e:
                return ApplyResult(error=f"无法读取 {p.file}：{e}，未写入任何文件")
            if _sha12(data) != rec[p.file].sha12:
                return ApplyResult(error=f"{p.file} 在审计后被修改，请重新审计；未写入任何文件")
            originals[p.file] = data
    new_texts: dict = {}
    for file, data in originals.items():
        text = data.decode("utf-8")
        spans = []
        for p in (x for x in chosen if x.file == file):
            found = _find_all(text, p.find)
            if len(found) != 1:
                return ApplyResult(error=f"{p.fid} 的原文在 {file} 中不再唯一，未写入任何文件")
            spans.append((found[0][0], found[0][1], p.replace))
        spans.sort()
        for (s1, e1, _), (s2, e2, _) in zip(spans, spans[1:]):
            if e1 > s2:
                return ApplyResult(error=f"{file} 中的补丁区间重叠，未写入任何文件")
        for s, e, repl in reversed(spans):
            text = text[:s] + repl + text[e:]
        new_texts[file] = text
    stamp = now().strftime("%Y%m%d_%H%M%S")
    backups: list = []
    for file in originals:
        dest = project / f"{file}.pre_audit.{stamp}"
        n = 0
        while dest.exists():
            n += 1
            dest = project / f"{file}.pre_audit.{stamp}-{n}"
        try:
            shutil.copy2(project / file, dest)
        except OSError as e:
            return ApplyResult(error=f"备份 {file} 失败：{e}，未修改任何内容文件", backups=tuple(map(str, backups)))
        backups.append(dest)
    attempted: list = []
    try:
        for file, text in new_texts.items():
            tmp = project / f"{file}.audit_tmp"
            attempted.append(file)  # os.replace 与 append 之间被中断时也要回滚这一份
            tmp.write_bytes(text.encode("utf-8"))
            os.replace(tmp, project / file)
    except BaseException as e:  # noqa: BLE001 - Ctrl+C / SystemExit 也必须回滚，再原样抛出
        rolled = True
        for file in attempted:
            try:
                (project / file).write_bytes(originals[file])
            except OSError:
                rolled = False
            try:
                (project / f"{file}.audit_tmp").unlink()
            except OSError:
                pass
        if not isinstance(e, Exception):
            raise
        return ApplyResult(error=f"写入失败：{e}；备份位于 " + "、".join(str(b) for b in backups),
                           backups=tuple(str(b) for b in backups), rolled_back=rolled)
    return ApplyResult(applied_ids=tuple(p.fid for p in chosen), files=tuple(new_texts),
                       backups=tuple(str(b) for b in backups))


# ─── 报告 ────────────────────────────────────────────────────────────────

def render_report(outcome: AuditOutcome, *, generated_at: str) -> str:
    st = outcome.status
    m = outcome.materials
    L: list = [f"审计状态：{st.label}（status={st.value}）", "", "# 穿帮审计报告", ""]
    L += [f"- 结论：{outcome.headline}", f"- 生成时间：{generated_at}", f"- 模型：{outcome.model or '未知'}",
          f"- 作品状态：{'原型' if m.is_prototype else '完整版'}"]
    if outcome.forced:
        L.append("- 已指定 --force：该参数已弃用，不改变审计结论")
    L += ["", "> “通过”只表示模型在下列已覆盖材料上未报告 P0，不等于没有穿帮，不替代真人试玩。", "",
          "## 审计输入", "", "| 文件 | 参与轮次 | 字数 | sha12 | 状态 |", "|---|---|---|---|---|"]
    for r in m.records:
        rounds = "、".join(str(ROUND_NUMBER[k]) for k in ROUNDS if r.name in ROUND_FILES[k]) or "-"
        label = r.name + ("（来源 state/character_matrix.json）" if r.name == MATRIX_NAME else "")
        L.append(f"| {label} | {rounds} | {r.chars} | {r.sha12 or '-'} | {r.problem or '已读取'} |")
    L += ["", "未覆盖：" + "；".join(NOT_COVERED)]
    if m.problems:
        L += ["", "## 材料问题", ""] + [f"- {p}" for p in m.problems]
    if outcome.notes:
        L += ["", "## 说明", ""] + [f"- {n}" for n in outcome.notes]
    L += ["", "## 轮次状态", "", "| 轮次 | 状态 | P0 | P1 | P2 | 发送字符 | 原因 |", "|---|---|---|---|---|---|---|"]
    for k in ROUNDS:
        r = outcome.rounds[k]
        cnt = {s: sum(1 for i in r.issues if i.severity == s) for s in SEVERITIES}
        L.append(f"| 第{ROUND_NUMBER[k]}轮 {ROUND_TITLE[k]} | {r.status} | {cnt['P0']} | {cnt['P1']} | {cnt['P2']} "
                 f"| {r.prompt_chars} | {r.reason or ''} |")
        if r.has_more:
            L[-1] += " 另有未列出的问题，修复后重跑 |"
    L += ["", "## 问题清单", ""]

    def fmt(i: AuditIssue, copy_waiver: bool = False) -> list:
        out = [f"### {i.ref} [{i.severity}] {i.dimension}" + ("（已豁免）" if i.waived else ""),
               f"- key：{i.key}", f"- 角色：{'、'.join(i.characters) or '-'}　事件：{'、'.join(i.events) or '-'}",
               f"- 位置：{i.file}「{i.anchor}」（定位校验：{i.location}）"]
        if i.quote:
            out.append(f"- 引用：{i.quote}")
        out += [f"- 问题：{i.problem}", f"- 建议：{i.fix or '-'}"]
        if i.waived:
            out.append(f"- 豁免：{i.waiver_note or i.key}")
        elif copy_waiver:
            out.append(f"- 若确认可接受，在 .known_p0 加一行：`{i.key} 理由：<请填写>`")
        return out

    groups = (("未豁免 P0", [i for i in outcome.issue_list if i.severity == "P0" and not i.waived], True),
              ("已豁免 P0", outcome.p0_waived, False),
              ("P1", [i for i in outcome.issue_list if i.severity == "P1"], False),
              ("P2", [i for i in outcome.issue_list if i.severity == "P2"], False))
    for title, items, cw in groups:
        L += [f"## {title}（{len(items)}）", ""]
        for i in items:
            L += fmt(i, cw) + [""]
    w = outcome.waiver
    L += ["## 豁免情况", "", f"- 生效：{len(w.applied)}　未使用：{len(w.unused)}　含糊：{len(w.ambiguous)}　过短：{len(w.too_short)}"]
    for label, items in (("未使用", w.unused), ("含糊（命中多个问题，均未豁免）", w.ambiguous), ("过短（忽略）", w.too_short)):
        L += [f"  - {label}：{x}" for x in items]
    if w.read_error:
        L.append(f"- .known_p0 读取失败，未应用任何豁免：{w.read_error}")
    L += ["", "## 修复建议", ""]
    if outcome.proposals:
        for p in outcome.proposals:
            L += [f"### {p.fid}　关联 {'、'.join(p.issue_refs)}　{p.file}" + (f" 第 {p.line} 行" if p.line else ""),
                  f"- 状态：{'可应用' if p.applicable else '不可应用：' + p.reason}",
                  f"- 原文：{p.matched or p.find}", f"- 建议改为：{p.replace}", f"- 理由：{p.rationale}", ""]
        L.append("以上未写入作品。可手动修改，或在命令行交互终端里审计后选择应用。")
    else:
        L.append("没有可应用的定点补丁；各问题的文字建议见上。")
    if outcome.fix_note:
        L.append(f"补丁说明：{outcome.fix_note}")
    for ref, reason in outcome.unfixable:
        L.append(f"- {ref} 无法用定点替换修复：{reason}")
    if outcome.applied is not None:
        a = outcome.applied
        L += ["", "## 已接受并写入的修复", ""]
        if a.error:
            L.append(f"写入失败：{a.error}（已回滚：{a.rolled_back}）")
        else:
            L += [f"- 已应用：{'、'.join(a.applied_ids)}；文件：{'、'.join(a.files)}",
                  f"- 备份：{'、'.join(a.backups)}",
                  "- 注意：本报告前面各节描述的是修改前的文本，请重新运行 audit 验证。"]
    failed = [r for r in outcome.rounds.values() if r.status in ("parse_error", "truncated") and r.raw]
    if failed:
        L += ["", "## 附录：失败轮次原文", ""]
        for r in failed:
            raw = r.raw if len(r.raw) <= 3000 else r.raw[:3000] + "\n…（已截断）"
            L += [f"### 第{ROUND_NUMBER[r.round]}轮 {r.status}：{r.reason}", "```", raw, "```"]
            L += [f"- 疑似 P0 行：{h}" for h in r.hints]
    return "\n".join(L) + "\n"
