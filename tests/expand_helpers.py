"""expand 测试夹具：合法 2x3 原型项目 + 按提示词路由的脚本化模型（临时目录，无真实 key）。"""
import json
import re

from murder_wizard.llm.client import LLMResponse
from murder_wizard.wizard import expansion as X
from murder_wizard.wizard.truth_files import validate_generated_matrix
from tests.audit_fixtures import make_project

NEW_NAMES = {"R3": "周岩", "R4": "顾明", "R5": "宋青", "R6": "唐宁"}
OPS = (["expand_matrix"] + [f"expand_bg_{c}" for c in X.NEW_IDS] + [f"expand_asupp_{c}" for c in X.ORIGINAL_IDS]
       + [f"expand_a_{c}" for c in X.NEW_IDS] + [f"expand_b_{c}" for c in X.NEW_IDS]
       + [f"expand_bsupp_{c}" for c in X.ORIGINAL_IDS] + ["expand_dm", "expand_endings"])


def make_prototype_project(tmp_path):
    runner, root = make_project(tmp_path, prototype=True)
    (root / "information_matrix.md").write_text("原型矩阵（模型原始响应）\n", encoding="utf-8")
    (root / "characters.md").write_bytes("# a 本\r\n## 【林深】：开场白\r\n原文 [E1] [E2] [E3]\r\n## 【苏晚】：开场白\r\n原文{x}\r\n".encode("utf-8"))
    return runner, root


def proto_matrix(root):
    return validate_generated_matrix(json.loads((root / X.MATRIX_REL).read_text(encoding="utf-8")),
                                     char_count=2, event_count=3, is_prototype=True)


def snapshot_tree(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*")
            if p.is_file() and p.name not in ("cache.json", "cost.log")}


def delta_for(proto):
    d = X.build_delta_example(proto)
    for cid, nm in NEW_NAMES.items():
        d["new_characters"][cid]["name"] = nm
    return d


class ScriptedLLM:
    def __init__(self, runner, root, *, fail=None, on_call=None, delta=None, overrides=None, truncate=()):
        self.runner, self.root = runner, root
        self.fail, self.on_call, self.overrides = fail or {}, on_call, overrides or {}
        self.truncate = set(truncate)
        self.max_tokens_seen = []
        self.ops = []
        proto = proto_matrix(root)
        self.delta = delta if delta is not None else delta_for(proto)
        self.merged = X.merge_delta(proto, json.dumps(self.delta, ensure_ascii=False)).matrix
        mx = self.merged
        self.name = {c: mx.characters[c].name for c in X.ALL_IDS}
        self.cells = {c: {e: mx.characters[c].event_cognitions[e].state for e in X.ALL_EVENTS} for c in X.ALL_IDS}
        runner.llm.complete.side_effect = self._complete

    def tags(self, cid, evs):
        return " ".join(f"[{e}]" for e in evs if self.cells[cid][e] != "否")

    def op_of(self, p):
        m = None
        if "# expand 第 1 步" in p:
            return "expand_matrix"
        if "总篇幅不超过约 2400 字" in p:
            return "expand_dm"
        if "每个结局约 600 字内" in p:
            return "expand_endings"
        for pat, fmt in ((r"# expand 背景设定：新增角色 (R\d)", "expand_bg_{}"),
                         (r"# expand：原有角色 (R\d)【.*】在新增事件中的视角", "expand_asupp_{}"),
                         (r"# expand：新增角色 (R\d)【", "expand_a_{}"),
                         (r"# expand：原有角色 (R\d)【.*】的 b 本补充", "expand_bsupp_{}")):
            m = re.search(pat, p)
            if m:
                return fmt.format(m.group(1))
        m = re.search(r"只为【(.+?)】一位角色生成，输出以", p)
        if m:
            cid = next(c for c, n in self.name.items() if n == m.group(1))
            return f"expand_b_{cid}"
        return "unknown"

    def good(self, op):
        mx, nm = self.merged, self.name
        if op == "expand_matrix":
            return "```json\n" + json.dumps(self.delta, ensure_ascii=False) + "\n```"
        kind, _, cid = op.rpartition("_")
        pad = "这是一段用于通过尾部长度检查的足够长的正文内容。"
        if kind == "expand_bg":
            return (f"## 【{nm[cid]}】背景设定\n### 基础档案\n{pad}\n### 三层信息\n{pad}\n### 内心弧线\n{pad}\n"
                    f"### 暗线\n{pad}\n### a本边界约束\n可以说：{pad}")
        if kind == "expand_asupp":
            return (f"## 【{nm[cid]}】：新增事件回忆\n{self.tags(cid, X.NEW_EVENTS)} {pad}\n## 【{nm[cid]}】：关系更新\n{pad}\n"
                    f"## 【{nm[cid]}】：当前处境更新\n{pad}")
        if kind == "expand_a":
            return (f"## 【{nm[cid]}】：开场白\n{pad}\n## 【{nm[cid]}】：关系自述\n{pad}\n"
                    f"## 【{nm[cid]}】：关键事件回忆\n{self.tags(cid, X.ALL_EVENTS)} {pad}\n## 【{nm[cid]}】：当前处境\n{pad}")
        if kind == "expand_b":
            return (f"## 【{nm[cid]}】：新发现\n线索1：甲\n线索2：乙\n线索3：丙\n## 【{nm[cid]}】：抉择时刻\n选项A {pad}\n"
                    f"## 【{nm[cid]}】：隐藏信息\n{pad}")
        if kind == "expand_bsupp":
            return f"## 【{nm[cid]}】：新发现（新增事件补充）\n{self.tags(cid, X.NEW_EVENTS)} {pad}{pad}"
        if op == "expand_dm":
            body = " ".join(nm.values()) + " " + " ".join(X.ALL_EVENTS) + " " + " ".join(mx.evidence)
            return "\n".join(f"第{n}部分：{body}" for n in "一二三四五") + f"\n第六部分：应急预案 {pad}"
        return "结局A：真相大白型。\n结局B：反转型。\n结局C：开放式 " + pad * 2

    def _complete(self, prompt, system="", **kw):
        op = self.op_of(prompt)
        self.max_tokens_seen.append(kw.get("max_tokens"))
        self.ops.append(op)
        if self.on_call:
            self.on_call(len(self.ops), op)
        mode = self.fail.get(op)
        if mode == "raise":
            raise RuntimeError(f"{op} 调用失败")
        text = "垃圾输出" if mode == "invalid" else self.overrides.get(op, self.good(op))
        return LLMResponse(content=text, tokens_used=10, cost=0.01, model="mock-model",
                           stop_reason="max_tokens" if op in self.truncate else "end_turn")
