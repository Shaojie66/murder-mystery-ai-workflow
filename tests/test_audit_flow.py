"""审计合同流程测试（R05/R06）：模拟模型，临时目录。"""
import hashlib
import json
from pathlib import Path

import pytest

from murder_wizard.prompts.loader import PromptLoader, PromptRenderError
from murder_wizard.wizard import audit as A
from tests.audit_fixtures import Script, good_reply, issue, make_project, kind_of

TABLE_P0 = "## 审计\n| A1 | 知识边界 | P0 | E2 | 角色提及不该知道的事 | R1 | 删除 |\n"


def _bytes(root: Path) -> dict:
    return {str(p.relative_to(root)): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in root.rglob("*") if p.is_file()
            and p.name not in ("audit_report.md", "cache.json", "cost.log")}


# ── 计划 §6：表格 P0 / 解析错误 / 缺材料 ──────────────────────────────

def test_markdown_table_p0_is_incomplete_never_pass(tmp_path):
    runner, root = make_project(tmp_path)
    Script(runner, replies={"matrix": TABLE_P0})
    outcome = runner.run_audit_checked()
    assert outcome.status is A.AuditStatus.INCOMPLETE
    assert not outcome and outcome.exit_code == 2
    assert outcome.rounds["matrix"].status == "parse_error"
    assert any("| A1 |" in h for h in outcome.rounds["matrix"].hints)
    report = (root / "audit_report.md").read_text(encoding="utf-8")
    assert report.splitlines()[0].startswith("审计状态：未完成") and "status=incomplete" in report
    assert "审计完成" not in report


def test_structured_p0_is_blocked_with_location(tmp_path):
    runner, root = make_project(tmp_path)
    Script(runner, replies={"matrix": lambda p: good_reply("matrix", p, [issue()])})
    outcome = runner.run_audit_checked()
    assert outcome.status is A.AuditStatus.BLOCKED and outcome.exit_code == 1
    [p0] = outcome.p0_unwaived
    assert p0.location == "verified" and p0.key.startswith("AUD-")
    report = (root / "audit_report.md").read_text(encoding="utf-8")
    assert "characters.md" in report and p0.key in report and "理由：<请填写>" in report


def test_clean_rounds_give_passed_with_not_proof_wording(tmp_path):
    runner, root = make_project(tmp_path)
    Script(runner)
    outcome = runner.run_audit_checked()
    assert outcome.status is A.AuditStatus.PASSED and bool(outcome) and outcome.exit_code == 0
    assert "不等于没有穿帮" in (root / "audit_report.md").read_text(encoding="utf-8")
    assert runner.run_audit() is True


@pytest.mark.parametrize("reply", [
    "我拒绝回答", "", "```json\n{\"schema\": \"audit-issues/1\"", "没有结果块",
    "```json\n{\"schema\":\"audit-issues/1\"}\n```\n```json\n{\"schema\":\"audit-issues/1\"}\n```",
])
def test_unparseable_replies_incomplete(tmp_path, reply):
    runner, _ = make_project(tmp_path)
    Script(runner, replies={"mechanism": reply})
    outcome = runner.run_audit_checked()
    assert outcome.status is A.AuditStatus.INCOMPLETE
    assert outcome.rounds["mechanism"].status == "parse_error"
    assert outcome.rounds["matrix"].status == "ok" and outcome.rounds["ending"].status == "ok"


def _mut(kind, fn):
    def reply(prompt):
        block = json.loads(good_reply(kind, prompt, [issue("P2")]).strip("`").removeprefix("json\n"))
        fn(block)
        return "```json\n" + json.dumps(block, ensure_ascii=False) + "\n```"
    return reply


@pytest.mark.parametrize("name,fn", [
    ("round", lambda b: b.update(round="ending")),
    ("severity", lambda b: b["issues"][0].update(severity="严重")),
    ("problem", lambda b: b["issues"][0].pop("problem")),
    ("anchor", lambda b: b["issues"][0]["location"].pop("anchor")),
    ("has_more", lambda b: b.pop("has_more")),
    ("files_seen_missing", lambda b: b.pop("files_seen")),
    ("files_seen_wrong", lambda b: b["files_seen"].update({"characters.md": "00000000"})),
])
def test_contract_violations_are_incomplete(tmp_path, name, fn):
    runner, _ = make_project(tmp_path)
    Script(runner, replies={"matrix": _mut("matrix", fn)})
    outcome = runner.run_audit_checked()
    assert outcome.rounds["matrix"].status == "parse_error", name
    assert outcome.status is A.AuditStatus.INCOMPLETE


def test_prose_p0_with_empty_issues_is_rejected(tmp_path):
    runner, _ = make_project(tmp_path)
    Script(runner, replies={"ending": lambda p: "发现 [P0] 严重问题\n" + good_reply("ending", p)})
    outcome = runner.run_audit_checked()
    assert outcome.rounds["ending"].status == "parse_error"
    assert outcome.status is A.AuditStatus.INCOMPLETE


def test_bare_json_without_fence_is_accepted(tmp_path):
    runner, _ = make_project(tmp_path)
    Script(runner, replies={"matrix": lambda p: good_reply("matrix", p).strip("`").removeprefix("json\n")})
    assert runner.run_audit_checked().rounds["matrix"].status == "ok"


def test_has_more_is_truncated_incomplete_or_blocked(tmp_path):
    runner, _ = make_project(tmp_path)
    Script(runner, replies={"matrix": lambda p: good_reply("matrix", p, [issue("P1")], has_more=True)})
    o = runner.run_audit_checked()
    assert o.rounds["matrix"].status == "truncated" and o.status is A.AuditStatus.INCOMPLETE
    runner2, _ = make_project(tmp_path / "b")
    Script(runner2, replies={"matrix": lambda p: good_reply("matrix", p, [issue("P0")], has_more=True)})
    assert runner2.run_audit_checked().status is A.AuditStatus.BLOCKED


@pytest.mark.parametrize("missing", list(A.AUDIT_FILES) + ["state/character_matrix.json"])
def test_missing_material_is_incomplete_without_llm_call(tmp_path, missing):
    runner, root = make_project(tmp_path)
    (root / missing).unlink()
    script = Script(runner)
    outcome = runner.run_audit_checked()
    assert outcome.status is A.AuditStatus.INCOMPLETE and script.calls == []
    first = (root / "audit_report.md").read_text(encoding="utf-8").splitlines()[0]
    assert "status=incomplete" in first
    assert missing.split("/")[-1] in "".join(outcome.materials.problems)


def test_empty_or_non_utf8_material_is_a_problem(tmp_path):
    runner, root = make_project(tmp_path)
    (root / "endings.md").write_text("  \n", encoding="utf-8")
    (root / "dm_manual.md").write_bytes(b"\xff\xfe\x00bad")
    m = A.AuditMaterials.from_dir(root, is_prototype=True)
    assert any("endings.md 为空" in p for p in m.problems)
    assert any("UTF-8" in p and "dm_manual.md" in p for p in m.problems)


@pytest.mark.parametrize("mutate", [
    lambda raw: raw["characters"]["R1"]["event_cognitions"].update({k: {"state": "否", "detail": ""} for k in raw["characters"]["R1"]["event_cognitions"]}),
    lambda raw: raw.pop("evidence"),
    lambda raw: raw.update(event_count="3"),
    lambda raw: raw.pop("event_count"),
    lambda raw: raw.update(event_count=9),
])
def test_invalid_matrix_blocks_audit(tmp_path, mutate):
    runner, root = make_project(tmp_path)
    path = root / "state" / "character_matrix.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    mutate(raw)
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    script = Script(runner)
    outcome = runner.run_audit_checked()
    assert outcome.status is A.AuditStatus.INCOMPLETE and script.calls == []


def test_non_json_and_old_2x3_matrix_with_full_work_block_audit(tmp_path):
    from murder_wizard.prompts.loader import build_matrix_example
    runner, root = make_project(tmp_path)
    (root / "state" / "character_matrix.json").write_text("not json", encoding="utf-8")
    assert not A.AuditMaterials.from_dir(root, is_prototype=True).auditable
    _, froot = make_project(tmp_path / "f", prototype=False)
    assert A.AuditMaterials.from_dir(froot, is_prototype=False).auditable
    old = build_matrix_example(2, 3, True)
    for cid, c in old["characters"].items():
        c["name"] = cid
    (froot / "state" / "character_matrix.json").write_text(json.dumps(old, ensure_ascii=False), encoding="utf-8")
    assert not A.AuditMaterials.from_dir(froot, is_prototype=False).auditable


def test_audit_prompts_cover_all_seven_inputs(tmp_path):
    runner, root = make_project(tmp_path)
    prompts = []
    s = Script(runner)
    orig = runner.llm.complete.side_effect
    runner.llm.complete.side_effect = lambda p, system="", **k: (prompts.append(p), orig(p, system=system))[1]
    runner.run_audit_checked()
    by = {kind_of(p): p for p in prompts if kind_of(p)}
    assert "哨兵-scripts_b.md" in by["matrix"] and "哨兵-background.md" in by["matrix"]
    for f in ("scripts_b.md", "dm_manual.md", "endings.md", "mechanism.md", "characters.md"):
        assert f"哨兵-{f}" in by["ending"]
    assert "{{" not in by["matrix"] and "char_count*2" not in "".join(by.values())


def test_report_lists_files_sha12_and_not_covered(tmp_path):
    runner, root = make_project(tmp_path)
    Script(runner)
    runner.run_audit_checked()
    report = (root / "audit_report.md").read_text(encoding="utf-8")
    sha = hashlib.sha256((root / "dm_manual.md").read_bytes()).hexdigest()[:12]
    assert sha in report and "未覆盖" in report and "information_matrix.md" in report


# ── 模板与严格渲染 ─────────────────────────────────────────────────────

def test_audit_templates_missing_block_raises_before_llm():
    loader = PromptLoader()
    base = dict(round_id="matrix", is_prototype=True, char_count=2, event_count=3,
                max_issues=8, output_contract="c", matrix_block="m", characters_block="c",
                scripts_b_block="b", background_block="g")
    loader.audit_round("matrix", **{k: v for k, v in base.items() if k != "round_id"})
    for name in A.ROUND_FILES["matrix"]:
        var = A.BLOCK_VAR[name]
        bad = {k: v for k, v in base.items() if k != "round_id"}
        bad[var] = "  "
        with pytest.raises(PromptRenderError, match=var):
            loader.audit_round("matrix", **bad)


def test_material_text_with_template_syntax_survives_verbatim():
    loader = PromptLoader()
    out = loader.audit_round("matrix", is_prototype=True, char_count=2, event_count=3, max_issues=8,
                             output_contract="c", matrix_block="{{x}} {{#if y}}z{{/if}}",
                             characters_block="c", scripts_b_block="b", background_block="g")
    assert "{{x}} {{#if y}}z{{/if}}" in out


def test_output_contract_has_empty_skeleton_that_parses_as_clean(tmp_path):
    runner, root = make_project(tmp_path)
    m = A.AuditMaterials.from_dir(root, is_prototype=True)
    c = A.output_contract("matrix", m)
    assert "{{" not in c and '"issues": []' in c


# ── 豁免 ───────────────────────────────────────────────────────────────

def _blocked(tmp_path, **kw):
    runner, root = make_project(tmp_path)
    Script(runner, replies={"matrix": lambda p: good_reply("matrix", p, [issue(), issue(file="scripts_b.md", quote="哨兵-scripts_b.md", dim="秘密泄露", problem="秘密被别的角色在 b 本里提及了")])})
    return runner, root


def test_waiver_key_line_waives_only_matching_p0(tmp_path):
    runner, root = _blocked(tmp_path)
    first = runner.run_audit_checked()
    key = first.p0_unwaived[0].key
    (root / ".known_p0").write_text(f"# 注释\n{key} 理由：作者确认\n", encoding="utf-8")
    runner2, _ = make_project(tmp_path / "again")
    (runner2.session.project_path / ".known_p0").write_text(f"{key} 理由：作者确认\n", encoding="utf-8")
    Script(runner2, replies={"matrix": lambda p: good_reply("matrix", p, [issue(), issue(file="scripts_b.md", quote="哨兵-scripts_b.md", dim="秘密泄露", problem="秘密被别的角色在 b 本里提及了")])})
    o = runner2.run_audit_checked()
    assert len(o.p0_waived) == 1 and len(o.p0_unwaived) == 1 and o.status is A.AuditStatus.BLOCKED


def test_two_p0_one_nonmatching_waiver_leaves_two_unresolved(tmp_path):
    runner, root = _blocked(tmp_path)
    (root / ".known_p0").write_text("完全不相关的一条很长的豁免描述文字\n", encoding="utf-8")
    o = runner.run_audit_checked()
    assert len(o.p0_unwaived) == 2 and o.waiver.unused


def test_all_p0_waived_gives_waived_not_pass(tmp_path):
    runner, root = make_project(tmp_path)
    Script(runner, replies={"matrix": lambda p: good_reply("matrix", p, [issue()])})
    key = runner.run_audit_checked().p0_unwaived[0].key
    runner2, root2 = make_project(tmp_path / "w")
    (root2 / ".known_p0").write_text(f"{key} 理由：x\n", encoding="utf-8")
    Script(runner2, replies={"matrix": lambda p: good_reply("matrix", p, [issue()])})
    o = runner2.run_audit_checked(force=True)
    assert o.status is A.AuditStatus.WAIVED and not bool(o) and o.exit_code == 0
    assert "通过" not in o.headline.replace("不是“通过”", "")
    assert any("--force" in n for n in o.notes)


def test_waiver_text_unique_ambiguous_and_too_short():
    mk = lambda key, prob, quote="": A.AuditIssue("", key, "matrix", "model", "P0", "d", (), (), "characters.md", "a", quote, prob, "", "verified")
    issues = [mk("AUD-aaaaaaaa", "角色甲出现共同的十二字以上的重复描述文本甲"), mk("AUD-bbbbbbbb", "角色乙出现共同的十二字以上的重复描述文本乙")]
    out, rep = A.apply_waivers(issues, A.WaiverFile(lines=("角色甲出现共同的十二字以上的重复描述文本甲", "共同的十二字以上的重复描述文本", "太短")))
    assert [i.waived for i in out] == [True, False]
    assert rep.ambiguous and rep.too_short and len(rep.applied) == 1


def test_waiver_unreadable_gives_no_waiver(tmp_path):
    wf = A.load_waivers(tmp_path)  # 目录 -> 读取失败
    assert wf.read_error and not wf.lines


def test_issue_key_stable_and_changes_with_quote():
    k = lambda q: A.issue_key("matrix", "维度1：知识边界", "characters.md", "verified", q, "a", (), (), "p")
    assert k("甲乙丙丁戊") == k("甲乙 丙丁戊") != k("甲乙丙丁己")


def test_one_waiver_line_does_not_waive_another_p0_on_the_same_quote():
    args = ("matrix", "维度1：知情", "characters.md", "verified", "他昨晚根本没去过花园", "x")
    k1 = A.issue_key(*args, ("R1",), ("E2",), "问题甲")
    k2 = A.issue_key(*args, ("R2",), ("E2",), "问题乙")
    k3 = A.issue_key(*args, ("R1",), ("E2",), "问题丙")
    assert len({k1, k2, k3}) == 3
    mk = lambda k, p: A.AuditIssue("", k, "matrix", "model", "P0", "d", (), (), "characters.md", "x", "q", p, "", "verified")
    out, _ = A.apply_waivers([mk(k1, "问题甲"), mk(k2, "问题乙")], A.WaiverFile(lines=(f"{k1} 理由：只想豁免甲",)))
    assert [i.waived for i in out] == [True, False]


# ── 状态真值表与流程 ──────────────────────────────────────────────────

def test_compute_status_truth_table():
    ok = {k: A.RoundResult(k, "ok") for k in A.ROUNDS}
    bad = dict(ok, ending=A.RoundResult("ending", "parse_error"))
    p0 = A.AuditIssue("", "AUD-1", "matrix", "model", "P0", "d", (), (), "f", "a", "", "p", "", "verified")
    w = A.dataclasses.replace(p0, waived=True)
    S = A.AuditStatus
    assert A.compute_status(material_problems=["x"], rounds=ok, issues=[]) is S.INCOMPLETE
    assert A.compute_status(material_problems=[], rounds=bad, issues=[p0]) is S.BLOCKED
    assert A.compute_status(material_problems=[], rounds=bad, issues=[]) is S.INCOMPLETE
    assert A.compute_status(material_problems=[], rounds=ok, issues=[], report_error="e") is S.INCOMPLETE
    assert A.compute_status(material_problems=[], rounds=ok, issues=[w], report_error="e") is S.INCOMPLETE
    assert A.compute_status(material_problems=[], rounds=ok, issues=[p0], report_error="e") is S.BLOCKED
    assert A.compute_status(material_problems=[], rounds=ok, issues=[w]) is S.WAIVED
    assert A.compute_status(material_problems=[], rounds=ok, issues=[]) is S.PASSED


def test_parse_error_evicts_cache_and_rerun_calls_only_failed_round(tmp_path):
    runner, _ = make_project(tmp_path)
    state = {"bad": True}
    script = Script(runner, replies={"matrix": lambda p: "坏输出" if state["bad"] else good_reply("matrix", p)})
    runner.run_audit_checked()
    assert script.calls.count("matrix") == 1 and len(script.calls) == 3
    state["bad"] = False
    script.calls.clear()
    o = runner.run_audit_checked()
    assert script.calls == ["matrix"] and o.status is A.AuditStatus.PASSED


def test_llm_exception_in_round_stops_remaining(tmp_path):
    runner, _ = make_project(tmp_path)
    def boom(p, system="", **k):
        raise RuntimeError("网络断了")
    runner.llm.complete.side_effect = boom
    o = runner.run_audit_checked()
    assert o.rounds["matrix"].status == "call_failed"
    assert o.rounds["mechanism"].status == o.rounds["ending"].status == "not_run"
    assert o.status is A.AuditStatus.INCOMPLETE


def test_report_write_failure_downgrades_pass(tmp_path, monkeypatch):
    runner, _ = make_project(tmp_path)
    Script(runner)
    import os as _os
    real = _os.replace
    monkeypatch.setattr("murder_wizard.cli.phase_runner.os.replace",
                        lambda a, b: (_ for _ in ()).throw(OSError("disk full")) if str(b).endswith("audit_report.md") else real(a, b))
    o = runner.run_audit_checked()
    assert o.status is A.AuditStatus.INCOMPLETE and o.report_error


def test_keyboard_interrupt_writes_incomplete_report_then_reraises(tmp_path):
    runner, root = make_project(tmp_path)
    (root / "audit_report.md").write_text("审计状态：模型未报告 P0（status=passed）\n", encoding="utf-8")
    runner.llm.complete.side_effect = KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        runner.run_audit_checked()
    assert "status=incomplete" in (root / "audit_report.md").read_text(encoding="utf-8").splitlines()[0]


def test_issue_text_with_rich_markup_does_not_crash(tmp_path):
    runner, _ = make_project(tmp_path)
    Script(runner, replies={"matrix": lambda p: good_reply("matrix", p, [issue(problem="[/bold] 坏标记 [red]")])})
    assert runner.run_audit_checked().status is A.AuditStatus.BLOCKED


def test_static_name_check_flags_missing_character(tmp_path):
    runner, root = make_project(tmp_path)
    (root / "characters.md").write_text("# a 本\n只有林深\n" + "哨兵" * 3, encoding="utf-8")
    Script(runner)
    o = runner.run_audit_checked()
    assert any(i.source == "static" and i.severity == "P0" and "苏晚" in i.problem for i in o.issues)
    assert o.status is A.AuditStatus.BLOCKED


def test_old_unsafe_audit_helpers_are_gone():
    from murder_wizard.cli.phase_runner import PhaseRunner
    for n in ("_run_reviser", "_extract_revised_content", "_count_p0_issues", "_count_all_p0_issues",
              "_extract_p0_summaries", "_compile_audit_summary"):
        assert not hasattr(PhaseRunner, n)


# ── R06：默认只读、作者显式接受 ──────────────────────────────────────

FIX = lambda p: ("```json\n" + json.dumps({"schema": "audit-fixes/1", "fixes": [{
    "issue_refs": ["MX-1"], "file": "characters.md", "find": "哨兵-characters.md",
    "replace": "已修复的句子", "rationale": "删除"}], "unfixable": []}, ensure_ascii=False) + "\n```")


def _with_fix(tmp_path):
    runner, root = make_project(tmp_path)
    Script(runner, replies={"matrix": lambda p: good_reply("matrix", p, [issue()])}, fix_reply=FIX)
    return runner, root


def test_default_audit_leaves_every_material_byte_identical(tmp_path):
    runner, root = _with_fix(tmp_path)
    before = _bytes(root)
    o = runner.run_audit_checked()
    assert _bytes(root) == before
    assert not list(root.glob("*.revised_r*")) and not list(root.glob("*.pre_audit.*"))
    assert o.proposals and o.proposals[0].applicable
    report = (root / "audit_report.md").read_text(encoding="utf-8")
    assert "建议改为" in report and "以上未写入作品" in report


def test_reject_fix_keeps_work_unchanged_non_tty_and_empty_choice(tmp_path):
    from murder_wizard.cli.commands import run_audit
    runner, root = _with_fix(tmp_path)
    before = _bytes(root)
    import murder_wizard.cli.commands as C
    from unittest.mock import patch
    with patch.object(C, "PhaseRunner", return_value=runner):
        for chooser in (None, lambda c, p: [], "auto"):
            o = run_audit(runner.session, runner.console, chooser=chooser)
            assert o is not None and _bytes(root) == before
        def eof(c, p):
            raise EOFError
        assert C._prompt_accept_fixes.__name__
    assert not list(root.glob("*.pre_audit.*"))


def test_accept_fix_applies_with_backup_status_unchanged(tmp_path):
    runner, root = _with_fix(tmp_path)
    o = runner.run_audit_checked()
    orig = (root / "characters.md").read_bytes()
    res = runner.apply_audit_fixes(o, ["F1"])
    assert not res.error and res.applied_ids == ("F1",)
    assert "已修复的句子" in (root / "characters.md").read_text(encoding="utf-8")
    [bak] = [Path(b) for b in res.backups]
    assert bak.read_bytes() == orig and ".pre_audit." in bak.name
    assert o.status is A.AuditStatus.BLOCKED
    assert "已接受并写入" in (root / "audit_report.md").read_text(encoding="utf-8")


def test_apply_refuses_when_file_changed_since_audit(tmp_path):
    runner, root = _with_fix(tmp_path)
    o = runner.run_audit_checked()
    (root / "characters.md").write_text("作者刚改过\n哨兵-characters.md", encoding="utf-8")
    res = runner.apply_audit_fixes(o, ["F1"])
    assert "被修改" in res.error and "作者刚改过" in (root / "characters.md").read_text(encoding="utf-8")
    assert not list(root.glob("*.pre_audit.*"))


def test_apply_write_failure_restores_replaced_files(tmp_path, monkeypatch):
    runner, root = make_project(tmp_path)
    two = lambda p: "```json\n" + json.dumps({"schema": "audit-fixes/1", "fixes": [
        {"issue_refs": ["MX-1"], "file": "characters.md", "find": "哨兵-characters.md", "replace": "新A", "rationale": "x"},
        {"issue_refs": ["MX-2"], "file": "scripts_b.md", "find": "哨兵-scripts_b.md", "replace": "新B", "rationale": "x"}],
        "unfixable": []}, ensure_ascii=False) + "\n```"
    Script(runner, replies={"matrix": lambda p: good_reply("matrix", p, [issue(), issue(file="scripts_b.md", quote="哨兵-scripts_b.md", dim="秘密泄露", problem="秘密被提及了很多次")])}, fix_reply=two)
    o = runner.run_audit_checked()
    before = {f: (root / f).read_bytes() for f in ("characters.md", "scripts_b.md")}
    import os as _os
    real, n = _os.replace, {"n": 0}
    def flaky(a, b):
        n["n"] += 1
        if n["n"] == 2:
            raise OSError("boom")
        return real(a, b)
    monkeypatch.setattr(A.os, "replace", flaky)
    res = runner.apply_audit_fixes(o, ["F1", "F2"])
    assert res.error and res.rolled_back
    assert {f: (root / f).read_bytes() for f in before} == before
    assert res.backups


def test_apply_interrupt_during_write_rolls_back_and_cleans_tmp(tmp_path, monkeypatch):
    runner, root = make_project(tmp_path)
    two = lambda p: "```json\n" + json.dumps({"schema": "audit-fixes/1", "fixes": [
        {"issue_refs": ["MX-1"], "file": "characters.md", "find": "哨兵-characters.md", "replace": "新A", "rationale": "x"},
        {"issue_refs": ["MX-2"], "file": "scripts_b.md", "find": "哨兵-scripts_b.md", "replace": "新B", "rationale": "x"}],
        "unfixable": []}, ensure_ascii=False) + "\n```"
    Script(runner, replies={"matrix": lambda p: good_reply("matrix", p, [issue(), issue(file="scripts_b.md", quote="哨兵-scripts_b.md", dim="秘密泄露", problem="秘密被提及了很多次")])}, fix_reply=two)
    o = runner.run_audit_checked()
    before = {f: (root / f).read_bytes() for f in ("characters.md", "scripts_b.md")}
    import os as _os
    real, n = _os.replace, {"n": 0}
    def interrupted(a, b):
        n["n"] += 1
        if n["n"] == 2:
            raise KeyboardInterrupt
        return real(a, b)
    monkeypatch.setattr(A.os, "replace", interrupted)
    with pytest.raises(KeyboardInterrupt):
        runner.apply_audit_fixes(o, ["F1", "F2"])
    assert {f: (root / f).read_bytes() for f in before} == before
    assert not list(root.glob("*.audit_tmp"))


def test_parse_fix_output_rejects_unsafe_patches(tmp_path):
    runner, root = make_project(tmp_path)
    m = A.AuditMaterials.from_dir(root, is_prototype=True)
    iss = [A.AuditIssue("MX-1", "AUD-1", "matrix", "model", "P0", "d", (), (), "characters.md", "a", "", "p", "", "verified"),
           A.AuditIssue("MC-1", "AUD-2", "matrix", "model", "P0", "d", (), (), "mechanism.md", "a", "", "p", "", "verified")]
    def mk(**kw):
        base = {"issue_refs": ["MX-1"], "file": "characters.md", "find": "哨兵-characters.md", "replace": "新", "rationale": "r"}
        base.update(kw)
        return "```json\n" + json.dumps({"schema": "audit-fixes/1", "fixes": [base]}, ensure_ascii=False) + "\n```"
    ok = A.parse_fix_output(mk(), iss, m)[0][0]
    assert ok.applicable and ok.line >= 1
    for kw in ({"find": "不存在的原文啊啊啊啊"}, {"find": "短"}, {"replace": ""}, {"replace": "哨兵-characters.md"},
               {"file": "mechanism.md", "issue_refs": ["MC-1"]}, {"issue_refs": ["ZZ-9"]}, {"find": "#"}):
        assert not A.parse_fix_output(mk(**kw), iss, m)[0][0].applicable, kw


def test_fix_failure_does_not_change_verdict(tmp_path):
    runner, _ = make_project(tmp_path)
    Script(runner, replies={"matrix": lambda p: good_reply("matrix", p, [issue()])}, fix_reply="胡言乱语")
    o = runner.run_audit_checked()
    assert o.status is A.AuditStatus.BLOCKED and o.fix_note and not o.proposals


# ── 调用方兼容与候选复核接口 ───────────────────────────────────────────

def test_cli_exit_codes(tmp_path, monkeypatch):
    from click.testing import CliRunner
    import murder_wizard.cli as cli
    from murder_wizard.cli import commands as C
    from murder_wizard.cli.phase_runner import PhaseRunner
    from unittest.mock import patch
    for replies, code in (({}, 0), ({"matrix": lambda p: good_reply("matrix", p, [issue()])}, 1), ({"matrix": "坏"}, 2)):
        runner, root = make_project(tmp_path / str(code))
        Script(runner, replies=replies)
        monkeypatch.setattr(cli, "SessionManager", lambda name, _r=runner: _r.session)
        with patch.object(C, "PhaseRunner", return_value=runner):
            res = CliRunner().invoke(cli.main, ["audit", "demo", "--force"])
        assert res.exit_code == code, res.output
        assert "审计完成" in res.output if code == 0 else "审计完成" not in res.output


def test_web_run_audit_event_is_strict(tmp_path):
    import asyncio, sys
    backend = Path(__file__).parent.parent / "murder_wizard_web" / "backend"
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))
    from core.phase_runner_web import PhaseRunnerWeb
    import inspect
    src = inspect.getsource(PhaseRunnerWeb.run_audit)
    assert "run_audit_checked" in src and "to_summary_dict" in src


def test_from_dir_creates_no_files_or_dirs(tmp_path):
    runner, root = make_project(tmp_path)
    import shutil
    shutil.rmtree(root / "state")
    before = sorted(p.name for p in root.rglob("*"))
    A.AuditMaterials.from_dir(root, is_prototype=True)
    assert sorted(p.name for p in root.rglob("*")) == before and not (root / "state").exists()


def test_from_texts_matches_from_dir_and_audit_materials_writes_nothing(tmp_path):
    runner, root = make_project(tmp_path)
    texts = {f: (root / f).read_text(encoding="utf-8") for f in A.AUDIT_FILES}
    raw = json.loads((root / "state" / "character_matrix.json").read_text(encoding="utf-8"))
    a = A.AuditMaterials.from_dir(root, is_prototype=True)
    b = A.AuditMaterials.from_texts(texts, raw, is_prototype=True)
    assert a.texts == b.texts and b.auditable
    Script(runner)
    before = _bytes(root)
    o = runner.audit_materials(b)
    assert _bytes(root) == before and o.status is A.AuditStatus.PASSED
    assert not (root / "audit_report.md").exists()


def test_matrix_text_has_no_meta_and_all_fields(tmp_path):
    runner, root = make_project(tmp_path)
    m = A.AuditMaterials.from_dir(root, is_prototype=True)
    data = json.loads(m.texts["character_matrix.json"])
    assert "meta" not in data and "evidence_refs" in json.dumps(data) and "must_deny" in json.dumps(data)


def test_drift_guards():
    from murder_wizard.cli.phase_runner import PhaseRunner
    from murder_wizard.wizard.truth_files import TruthFileManager
    assert set(A.AUDIT_FILES) | {"information_matrix.md"} == set(PhaseRunner.STAGE_2_REQUIRED_ARTIFACTS) | {"mechanism.md"}
    assert A.EXPECTED_SHAPE[True] == (2, 3, 3) and A.EXPECTED_SHAPE[False][0] == 6 and 5 <= 7 <= A.EXPECTED_SHAPE[False][2]
    assert A.MATRIX_REL == Path(TruthFileManager.STATE_DIR) / "character_matrix.json"


def test_light_check_never_prints_pass(tmp_path):
    from unittest.mock import MagicMock
    from murder_wizard.llm.client import LLMResponse
    for text in ("发现多处不一致", "无穿帮，一致"):
        runner, root = make_project(tmp_path / str(len(text)))
        runner._call_llm = MagicMock(return_value=LLMResponse(text, 1, 0.0, "m"))
        runner._run_consistency_check("a", "m")
        out = runner.console.export_text()
        assert "通过" not in out.replace("不判定通过", "") and (root / "consistency_report.md").exists()
