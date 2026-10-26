"""审计测试夹具：临时作品目录 + 脚本化 LLM（不读 ~/.murder-wizard，不用真实 key）。"""
import json
import re
from unittest.mock import MagicMock, patch

from rich.console import Console

from murder_wizard.cli.phase_runner import PhaseRunner
from murder_wizard.llm.client import LLMResponse
from murder_wizard.prompts.loader import build_matrix_example
from murder_wizard.wizard.audit import AUDIT_FILES, SCHEMA_TAG
from murder_wizard.wizard.session import SessionManager
from murder_wizard.wizard.state_machine import MurderWizardState, Stage

NAMES = {"R1": "林深", "R2": "苏晚", "R3": "周岩", "R4": "顾明", "R5": "宋青", "R6": "唐宁"}


def make_project(tmp_path, prototype: bool = True):
    """返回 (runner, project_path)。材料齐全，a 本含全部角色姓名，矩阵为合法 JSON。"""
    session = SessionManager("demo", base_path=str(tmp_path))
    state = MurderWizardState(project_name="demo", story_type="mechanic",
                              current_stage=Stage.STAGE_2_SCRIPT, outline="# Outline",
                              is_prototype=prototype)
    session.save(state)
    root = session.project_path
    chars, events = (2, 3) if prototype else (6, 7)
    names = [NAMES[f"R{i + 1}"] for i in range(chars)]
    body = "、".join(names)
    for f in AUDIT_FILES:
        (root / f).write_text(f"# {f}\n哨兵-{f}\n角色：{body}\n", encoding="utf-8")
    data = build_matrix_example(chars, events, prototype)
    for cid, c in data["characters"].items():
        c["name"] = NAMES[cid]
    (root / "state").mkdir(exist_ok=True)
    (root / "state" / "character_matrix.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    with patch.object(PhaseRunner, "_setup_llm"):
        runner = PhaseRunner(session, state, Console(record=True, width=140))
    runner.llm = MagicMock()
    runner.llm.model = "mock-model"
    return runner, root


def seen_from_prompt(prompt: str) -> dict:
    out = {}
    for m in re.finditer(r"<<<FILE (\S+) · 开始标记 (\w+)>>>", prompt):
        end = re.search(rf"<<<END {re.escape(m.group(1))} · 结束标记 (\w+)>>>", prompt)
        out[m.group(1)] = m.group(2) + end.group(1)
    return out


def good_reply(kind: str, prompt: str, issues=(), has_more: bool = False) -> str:
    block = {"schema": SCHEMA_TAG, "round": kind, "files_seen": seen_from_prompt(prompt),
             "has_more": has_more, "issues": list(issues)}
    return "```json\n" + json.dumps(block, ensure_ascii=False) + "\n```"


def issue(sev="P0", file="characters.md", quote="哨兵-characters.md", dim="知识边界", problem="角色提及了不该知道的事"):
    return {"severity": sev, "dimension": dim, "characters": ["R1"], "events": ["E2"],
            "location": {"file": file, "anchor": "开头", "quote": quote}, "problem": problem, "fix": "删除该句"}


def kind_of(prompt: str) -> str:
    m = re.search(r"审计轮次标识：(\w+)", prompt)
    return m.group(1) if m else ""


class Script:
    """按提示词里的轮次标识路由的脚本化 LLM。replies: {kind: callable(prompt)->str 或 str}。"""

    def __init__(self, runner, replies=None, fix_reply=None):
        self.replies = replies or {}
        self.fix_reply = fix_reply
        self.calls = []
        runner.llm.complete.side_effect = self._complete

    def _complete(self, prompt, system="", **_):
        k = kind_of(prompt) or ("fixes" if "审计修复建议" in prompt else "other")
        self.calls.append(k)
        r = self.replies.get(k)
        if k == "fixes":
            text = self.fix_reply(prompt) if callable(self.fix_reply) else (self.fix_reply or "")
        elif r is None:
            text = good_reply(k, prompt)
        else:
            text = r(prompt) if callable(r) else r
        return LLMResponse(content=text, tokens_used=10, cost=0.01, model="mock-model")
