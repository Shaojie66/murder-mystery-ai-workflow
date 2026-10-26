"""expand 编排：在内存里生成并校验完整 6 人候选，作者确认后才备份并覆盖。

所有模型调用经 runner._call_llm（成本记录、缓存、Web 的 _patch_runner 都依赖它）；
所有输出经 runner.console，动态文本一律 escape。任何失败都不会改动作品。
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import dataclass, field
from typing import Callable, Optional

from rich.markup import escape

from murder_wizard.llm.client import LONG_OUTPUT_MAX_TOKENS
from murder_wizard.prompts.loader import PromptRenderError
from murder_wizard.wizard import expansion as X
from murder_wizard.wizard.file_commit import CommitFailed, commit_files


class ExpandStop(Exception):
    def __init__(self, status: X.ExpandStatus, problems, step: Optional[str] = None):
        self.status, self.problems, self.step = status, list(problems), step
        super().__init__("；".join(self.problems))


@dataclass
class PlanEntry:
    relpath: str
    treatment: str
    size_bytes: int


@dataclass
class ExpandPlan:
    entries: list
    new_character_names: dict
    new_events: list
    candidate_files: dict
    stale: list
    calls: int
    cost: float


class ExpandFlow:
    TOTAL_STEPS = 19

    def __init__(self, runner, *, confirm: Optional[Callable[[ExpandPlan], bool]] = None,
                 accept_overwrite: bool = False):
        self.runner = runner
        self.confirm = confirm
        self.accept_overwrite = accept_overwrite
        self.result = X.ExpandResult(X.ExpandStatus.FAILED_INTERNAL)
        self._k = 0

    # ── 小工具 ────────────────────────────────────────────────────────
    def _say(self, text: str) -> None:
        self.runner.console.print(text)

    def _prompt(self, tpl: str, **vars) -> str:
        return self.runner._loader.render(tpl, strict=True, required_inputs=X.EXPAND_PROMPTS[tpl],
                                          is_prototype=False, **vars)

    def _step(self, op: str, prompt: str, system: str, validate: Callable[[str], list]) -> str:
        self._k += 1
        self._say(f"[cyan]第 {self._k}/{self.TOTAL_STEPS} 步：{escape(op)}[/cyan]")
        r = self.runner
        cached = r._cache.get(op, prompt, system, r.llm.model, max_tokens=LONG_OUTPUT_MAX_TOKENS) is not None
        try:
            resp = r._call_llm(prompt, system=system, operation=op, max_tokens=LONG_OUTPUT_MAX_TOKENS)
        except Exception as e:  # noqa: BLE001
            raise ExpandStop(X.ExpandStatus.FAILED_CALL, [f"模型调用失败：{e}"], op) from e
        self.result.calls += 1
        if cached:
            self.result.cached_calls += 1
        else:
            self.result.cost += float(getattr(resp, "cost", 0.0) or 0.0)
        if getattr(resp, "truncated", False):
            # 明确的截断信号：不再靠"末段标题 + 最小正文"去猜
            problems = [f"模型输出被单次输出上限（{LONG_OUTPUT_MAX_TOKENS} tokens）截断（stop_reason={resp.stop_reason}），内容不完整"]
        else:
            problems = validate(resp.content)
        if problems:
            try:
                r._cache.invalidate(op, prompt, system, r.llm.model, max_tokens=LONG_OUTPUT_MAX_TOKENS)
            except Exception:  # noqa: BLE001
                pass
            head, tail = resp.content[:160], resp.content[-160:]
            self._say(f"[red]{escape(op)} 未通过校验，响应已丢弃（缓存已清除），作品未改动：[/red]")
            for p in problems:
                self._say(f"[red]  - {escape(p)}[/red]")
            self._say(f"[dim]响应开头：{escape(head)}\n响应结尾：{escape(tail)}[/dim]")
            raise ExpandStop(X.ExpandStatus.FAILED_VALIDATION, problems, op)
        return resp.content

    # ── 主流程 ────────────────────────────────────────────────────────
    def run(self) -> X.ExpandResult:
        try:
            return self._run()
        except ExpandStop as e:
            self.result.status, self.result.problems, self.result.failed_step = e.status, e.problems, e.step
        except PromptRenderError as e:
            self.result.status, self.result.problems = X.ExpandStatus.FAILED_VALIDATION, [str(e)]
            self._say(f"[red]提示词渲染失败，未调用模型：{escape(str(e))}[/red]")
        except Exception as e:  # noqa: BLE001
            self.result.status, self.result.problems = X.ExpandStatus.FAILED_INTERNAL, [f"{type(e).__name__}: {e}"]
            self._say(f"[red]expand 意外失败：{escape(str(e))}（提交前未写入任何文件）[/red]")
        if self.result.status not in (X.ExpandStatus.APPLIED,):
            self._say(f"[dim]已花费约 ¥{self.result.cost:.4f}（不退费；重跑时通过校验的步骤命中缓存）[/dim]")
        return self.result

    def _run(self) -> X.ExpandResult:
        r, st = self.runner, self.runner.state
        root = r.session.project_path
        res = self.result
        try:
            base = X.load_baseline(root, st)
        except X.ExpandRefused as e:
            res.status, res.problems = e.status, e.problems
            for p in e.problems:
                self._say(f"[yellow]{escape(p)}[/yellow]")
            if e.status is not X.ExpandStatus.NOT_PROTOTYPE:
                self._say("[dim]本次未调用模型，作品未改动。[/dim]")
            return res
        scope = ("expand 会在 characters.md、background.md、scripts_b.md 原文之后追加内容，"
                 "并整份重新生成 information_matrix.md、dm_manual.md、endings.md、state/character_matrix.json；"
                 "覆盖前会备份 8 个文件（含 session.json）为 <文件>.proto.<时间戳>。")
        if self.confirm is None and not self.accept_overwrite:
            res.status = X.ExpandStatus.REFUSED
            res.problems = [scope + "需作者确认（CLI 交互确认或 --yes）；本次未调用模型"]
            self._say(f"[yellow]{escape(res.problems[0])}[/yellow]")
            return res
        res.stale = [f for f in X.STALE_CANDIDATES if (root / f).exists()]
        self._say(f"[cyan]{escape(scope)}约 {self.TOTAL_STEPS} 次调用，缓存命中不再计费。[/cyan]")
        if res.stale:
            self._say(f"[yellow]下列下游产物会过期，需手动重新生成：{escape('、'.join(res.stale))}[/yellow]")

        loader = r._loader
        stype = st.story_type or "mechanic"
        designer, writer = loader.system_mechanism_designer(stype), loader.system_script_writer(stype)
        mech, brief = base.mechanism, base.outline
        proto = base.matrix
        self._k = 0

        # 1 矩阵增量
        holder: dict = {}

        def v_matrix(text):
            try:
                holder["m"] = X.merge_delta(proto, text, brief)
                return []
            except X.ExpandContractError as e:
                return e.problems
        example = json.dumps(X.build_delta_example(proto), ensure_ascii=False, indent=1)
        self._step("expand_matrix", self._prompt(
            "02_expand_matrix.md", brief_content=brief, mechanism_content=mech, proto_matrix_json=base.matrix_json,
            proto_characters_content=base.texts["characters.md"], delta_json_example=example), designer, v_matrix)
        merged = holder["m"]
        mx = merged.matrix
        matrix_md = X.render_matrix_markdown(mx, merged.new_events)
        name = {c: mx.characters[c].name for c in X.ALL_IDS}
        cells = {c: {e: mx.characters[c].event_cognitions[e].state for e in X.ALL_EVENTS} for c in X.ALL_IDS}
        new_events_text = "\n".join(f"{e}：{t} — {s}" for e, (t, s) in merged.new_events.items())
        others = lambda cid: [name[c] for c in X.ALL_IDS if c != cid]
        known = lambda cid, evs: "、".join(e for e in evs if cells[cid][e] != "否") or "无"
        forbidden = lambda cid: "、".join(e for e in X.ALL_EVENTS if cells[cid][e] == "否") or "无"
        required = lambda cid, evs: [e for e in evs if cells[cid][e] == "知"]

        # 2-5 背景
        bg_new: dict = {}
        for cid in X.NEW_IDS:
            ch = mx.characters[cid]
            bg_so_far = base.texts["background.md"] + "".join("\n\n" + t for t in bg_new.values())
            v = lambda t, cid=cid: (X.check_headings(t, name[cid], ["背景设定", "基础档案", "三层信息", "内心弧线", "暗线", "a本边界约束"])
                                    + X.foreign_headings(t, others(cid)) + X.check_tail(t, "a本边界约束", 20))
            bg_new[cid] = self._step(f"expand_bg_{cid}", self._prompt(
                "02_expand_background.md", char_id=cid, char_name=name[cid], char_role=ch.role,
                char_public_relationship=ch.public_relationship, brief_content=brief,
                matrix_content=matrix_md, background_content=bg_so_far), writer, v)
        bg_all = base.texts["background.md"] + "".join("\n\n" + t for t in bg_new.values())

        # 6-7 R1/R2 a 本补充
        asupp: dict = {}
        for cid in X.ORIGINAL_IDS:
            v = lambda t, cid=cid: (X.check_headings(t, name[cid], ["新增事件回忆", "关系更新", "当前处境更新"])
                                    + X.foreign_headings(t, others(cid))
                                    + X.check_event_tags(t, cells[cid], required(cid, X.NEW_EVENTS))
                                    + X.check_tail(t, "当前处境更新", 20))
            asupp[cid] = self._step(f"expand_asupp_{cid}", self._prompt(
                "02_expand_script_a_ext.md", char_id=cid, char_name=name[cid], matrix_content=matrix_md,
                background_content=bg_all, retained_script=base.texts["characters.md"], mechanism_content=mech,
                new_events_text=new_events_text, known_new_events=known(cid, X.NEW_EVENTS),
                forbidden_events=forbidden(cid)), writer, v)
        retained = base.texts["characters.md"] + "".join("\n\n" + t for t in asupp.values())

        # 8-11 新角色 a 本
        a_new: dict = {}
        for cid in X.NEW_IDS:
            def v(t, cid=cid):
                p = (X.check_headings(t, name[cid], ["开场白", "关系自述", "关键事件回忆", "当前处境"])
                     + X.foreign_headings(t, others(cid))
                     + X.check_event_tags(t, cells[cid], required(cid, X.ALL_EVENTS)) + X.check_tail(t, "当前处境", 20))
                if not X.event_tags(t):
                    p.append("没有任何 [E#] 事件标签")
                return p
            a_new[cid] = self._step(f"expand_a_{cid}", self._prompt(
                "02_expand_script_a.md", char_id=cid, char_name=name[cid], background_content=bg_all,
                matrix_content=matrix_md, mechanism_content=mech, new_events_text=new_events_text,
                known_events=known(cid, X.ALL_EVENTS), forbidden_events=forbidden(cid),
                word_count_a="1200-1800", retained_scripts=retained), writer, v)

        # 12-15 新角色 b 本
        b_new: dict = {}
        for cid in X.NEW_IDS:
            def v(t, cid=cid):
                p = (X.check_headings(t, name[cid], ["新发现", "抉择时刻", "隐藏信息"]) + X.foreign_headings(t, others(cid))
                     + X.check_event_tags(t, cells[cid], []) + X.check_tail(t, "隐藏信息", 10))
                p += [f"缺少「{k}」" for k in ("线索1：", "线索2：", "线索3：") if k not in t]
                return p
            prompt = loader.character_script_b(a_content=a_new[cid], matrix_content=matrix_md,
                                               mechanism_content=mech, is_prototype=False)
            prompt += (f"\n\n只为【{name[cid]}】一位角色生成，输出以“## 【{name[cid]}】：新发现”开头，"
                       "线索卡逐行写作 线索1：/线索2：/线索3：。")
            b_new[cid] = self._step(f"expand_b_{cid}", prompt, writer, v)

        # 16-17 R1/R2 b 本补充
        new_ev_text = "\n".join(f"{k}：{it.name} — {it.description}" for k, it in mx.evidence.items()
                                if k not in proto.evidence)
        bsupp: dict = {}
        for cid in X.ORIGINAL_IDS:
            v = lambda t, cid=cid: (X.check_headings(t, name[cid], ["新发现"]) + X.foreign_headings(t, others(cid))
                                    + X.check_event_tags(t, cells[cid], []) + X.check_tail(t, "新发现", 30))
            bsupp[cid] = self._step(f"expand_bsupp_{cid}", self._prompt(
                "02_expand_script_b_ext.md", char_id=cid, char_name=name[cid],
                a_content=base.texts["characters.md"] + "\n\n" + asupp[cid], original_scripts_b=base.texts["scripts_b.md"],
                matrix_content=matrix_md, mechanism_content=mech, new_evidence_text=new_ev_text), writer, v)

        parts = {"bg": bg_new, "asupp": asupp, "a": a_new, "b": b_new, "bsupp": bsupp, "dm": "-", "endings": "-"}
        pre = X.assemble_candidate(base, merged, parts).files()
        full_script = pre["characters.md"] + "\n\n" + pre["scripts_b.md"]

        # 18 DM 手册
        def v_dm(t):
            p = [f"缺少角色 {c}（{n}）" for c, n in name.items() if n not in t]
            p += [f"缺少事件 {e}" for e in X.ALL_EVENTS if e not in t]
            p += [f"没有提到证据 {k}" for k, it in mx.evidence.items() if k not in t and it.name not in t]
            p += [f"缺少「第{n}部分」" for n in "一二三四五六" if f"第{n}部分" not in t]
            return p + X.check_tail(t, "第六部分", 30)
        dm = self._step("expand_dm", loader.dm_manual(
            full_script=full_script, matrix_content=matrix_md, mechanism_content=mech, is_prototype=False)
            + "\n\n总篇幅不超过约 2400 字，必须输出第一至第六部分；第二部分真相手册逐行使用 E1-E7 编号；"
              "第四部分证据链使用证据 ID 或名称。", writer, v_dm)

        # 19 结局
        def v_end(t):
            p = [f"缺少{k}" for k in ("结局A", "结局B", "结局C") if k not in t.replace(" ", "")]
            return p + X.check_tail(t, "结局C", 30)
        endings = self._step("expand_endings", loader.ending_expansion(
            full_script=full_script, matrix_content=matrix_md, dm_manual=dm, is_prototype=False)
            + "\n\n每个结局约 600 字内。", writer, v_end)

        parts["dm"], parts["endings"] = dm, endings
        cand = X.assemble_candidate(base, merged, parts)
        files = cand.files()
        problems = X.verify_candidate(base, files)
        if problems:
            for p in problems:
                self._say(f"[red]候选终闸未通过：{escape(p)}[/red]")
            raise ExpandStop(X.ExpandStatus.FAILED_VALIDATION, problems, "candidate")

        plan = ExpandPlan(
            entries=[PlanEntry(rel, "追加原文之后" if rel in X.APPEND_ONLY else ("矩阵真相文件" if rel == X.MATRIX_REL else "整份重新生成"),
                               len(files[rel].encode("utf-8"))) for rel in X.COMMIT_ORDER] + [PlanEntry(X.SESSION_REL, "会话状态", 0)],
            new_character_names={c: name[c] for c in X.NEW_IDS},
            new_events=[(e, t, s) for e, (t, s) in merged.new_events.items()],
            candidate_files={**files, "mechanism.md": mech}, stale=res.stale, calls=res.calls, cost=res.cost)
        if not self.accept_overwrite:
            try:
                ok = bool(self.confirm(plan))
            except (EOFError, KeyboardInterrupt):
                ok = False
            if not ok:
                res.status = X.ExpandStatus.DECLINED
                self._say("[yellow]已放弃，作品未改动。再次运行会命中缓存得到同一候选（免费）；要换样本先 murder-wizard cache <name> --clear。[/yellow]")
                return res

        # 提交前乐观并发检查（不是写锁）
        for rel, old in base.fingerprints.items():
            p = root / rel
            now = hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else ""
            if now != old and not (rel == X.SESSION_REL and not p.exists() and old == hashlib.sha256(b"").hexdigest()):
                res.status = X.ExpandStatus.CHANGED_DURING_RUN
                res.problems = [f"{rel} 在生成期间被修改，已放弃提交；你的修改保留，作品未改动"]
                self._say(f"[red]{escape(res.problems[0])}[/red]")
                return res

        new_state = dataclasses.replace(st, is_prototype=False, characters={
            "raw": files["characters.md"], "background": files["background.md"],
            "scripts_b": files["scripts_b.md"], "dm_manual": files["dm_manual.md"], "endings": files["endings.md"]})

        def after_write():
            r.session.save(new_state)

        def verify():
            disk = {rel: (root / rel).read_bytes().decode("utf-8") for rel in X.COMMIT_ORDER}
            out = [f"{rel} 读回与候选不一致" for rel in X.COMMIT_ORDER if disk[rel] != files[rel]]
            loaded = r.session.load()
            if loaded is None or loaded.is_prototype:
                out.append("session.json 读回后 is_prototype 仍为 True")
            return out + X.verify_candidate(base, disk)

        try:
            rep = commit_files(root, {rel: files[rel] for rel in X.COMMIT_ORDER}, backup_tag="proto",
                               also_backup=(X.SESSION_REL,), after_write=after_write, verify=verify)
        except CommitFailed as e:
            res.backups, res.backup_tag = e.report.backups, e.report.tag
            res.restore_failed = e.report.restore_failed
            res.problems = e.problems
            if e.report.restore_failed:
                res.status = X.ExpandStatus.COMMIT_RESTORE_INCOMPLETE
                self._say("[red]写入失败且恢复未完成，作品处于混合状态。请逐个把备份拷回原名：[/red]")
                for rel in e.report.restore_failed:
                    self._say(f"[red]  cp {escape(e.report.backups[rel])} {escape(rel)}[/red]")
            else:
                res.status = X.ExpandStatus.COMMIT_RESTORED
                self._say(f"[red]写入失败，已从备份恢复：{escape('；'.join(e.problems))}（is_prototype 仍为 True）[/red]")
            return res
        st.is_prototype = False
        st.characters = new_state.characters
        res.status, res.backups, res.backup_tag, res.written = X.ExpandStatus.APPLIED, rep.backups, rep.tag, rep.written
        self._say("[green]expand 已完成：通过结构校验，尚未审计，建议运行 murder-wizard audit。[/green]")
        self._say("追加（原文逐字保留）：" + "、".join(X.APPEND_ONLY) + "；整份重新生成：" + "、".join(X.REGENERATED))
        self._say("备份（把 *.proto." + escape(rep.tag) + " 全部拷回原名，含 session.json，才能还原原型）：" + escape("、".join(rep.backups.values())))
        self._say(f"[dim]本次约 ¥{res.cost:.4f}（缓存命中 {res.cached_calls}/{res.calls} 次）[/dim]")
        return res
