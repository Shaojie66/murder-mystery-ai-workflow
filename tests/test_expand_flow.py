"""expand 合同测试（R03/R04）：模拟模型，临时目录。"""
import json
import re

import pytest

from murder_wizard.llm.cache import LLMCache
from murder_wizard.wizard import expansion as X
from murder_wizard.wizard import file_commit as FC
from murder_wizard.wizard.truth_files import validate_generated_matrix
from tests.expand_helpers import (NEW_NAMES, OPS, ScriptedLLM, delta_for, make_prototype_project,
                                  proto_matrix, snapshot_tree)

S = X.ExpandStatus


def _proto_from(before):
    return validate_generated_matrix(json.loads(before[X.MATRIX_REL].decode("utf-8")), 2, 3, True)


# ── 成功路径 ───────────────────────────────────────────────────────────

def test_success_commits_complete_six_person_materials(tmp_path):
    runner, root = make_prototype_project(tmp_path)
    before = snapshot_tree(root)
    llm = ScriptedLLM(runner, root)
    assert runner.run_expand(accept_overwrite=True) is True
    res = runner.last_expand_result
    assert res.status is S.APPLIED and llm.ops == OPS and res.calls == 19
    for rel in X.APPEND_ONLY:  # 原文逐字节保留（含 CRLF 与花括号）
        assert (root / rel).read_bytes().startswith(before[rel])
    m = validate_generated_matrix(json.loads((root / X.MATRIX_REL).read_text(encoding="utf-8")), 6, 7, False)
    assert not X.verify_prototype_retained(_proto_from(before), m)
    for rel in ("characters.md", "scripts_b.md", "dm_manual.md", "information_matrix.md"):
        text = (root / rel).read_text(encoding="utf-8")
        assert all(n in text for n in [*NEW_NAMES.values(), "林深", "苏晚"]), rel
    for rel, bname in res.backups.items():  # 8 个备份与原文件字节相同
        assert (root / bname).read_bytes() == before[rel]
    assert len(res.backups) == 8 and X.SESSION_REL in res.backups and X.MATRIX_REL in res.backups
    state = runner.session.load()
    assert state.is_prototype is False and runner.state.is_prototype is False
    assert set(state.characters) == {"raw", "background", "scripts_b", "dm_manual", "endings"}
    assert state.characters["raw"] == (root / "characters.md").read_bytes().decode("utf-8")
    assert "尚未审计" in runner.console.export_text()


def test_each_step_prompt_is_full_mode_without_leftovers(tmp_path):
    runner, root = make_prototype_project(tmp_path)
    prompts = []
    ScriptedLLM(runner, root)
    orig = runner.llm.complete.side_effect
    runner.llm.complete.side_effect = lambda p, system="", **k: (prompts.append(p), orig(p, system=system))[1]
    runner.run_expand(accept_overwrite=True)
    assert len(prompts) == 19 and all("{{" not in p for p in prompts)
    assert "R6" in prompts[0] and "E7" in prompts[0]
    assert "# expand 第 1 步" not in "".join(prompts[1:])


def test_degraded_single_pass_path_is_gone():
    from murder_wizard.cli.phase_runner import PhaseRunner
    for n in ("_expand_single_pass", "_build_expand_phase1_prompt", "_build_new_chars_prompt",
              "_parse_new_character_names", "_build_single_char_prompt", "_assemble_expanded_script",
              "_extract_matrix_from_phase1"):
        assert not hasattr(PhaseRunner, n)


# ── 任一必要步骤失败：原型完好 ─────────────────────────────────────────

@pytest.mark.parametrize("mode", ["raise", "invalid"])
@pytest.mark.parametrize("op", OPS)
def test_any_required_step_failure_leaves_prototype_intact(tmp_path, op, mode):
    runner, root = make_prototype_project(tmp_path)
    before = snapshot_tree(root)
    llm = ScriptedLLM(runner, root, fail={op: mode})
    assert runner.run_expand(accept_overwrite=True) is False
    res = runner.last_expand_result
    assert res.status is (S.FAILED_CALL if mode == "raise" else S.FAILED_VALIDATION) and res.failed_step == op
    assert snapshot_tree(root) == before
    assert not list(root.rglob("*.proto.*")) and not list(root.rglob("*.expand_tmp"))
    assert runner.session.load().is_prototype is True and runner.state.is_prototype is True
    assert llm.ops == OPS[:len(llm.ops)] and llm.ops[-1] == op  # 失败步骤之后零调用
    assert not re.search(r"\d+/\d+ 成功", runner.console.export_text())


@pytest.mark.parametrize("name,mutate", [
    ("missing_R5", lambda d: d["new_characters"].pop("R5")),
    ("extra_event", lambda d: d["new_events"].update(E8={"title": "x", "summary": "y"})),
    ("proto_cell_rewritten", lambda d: d["added_cognitions"]["R1"].update(E1={"state": "否", "detail": "", "evidence_refs": []})),
    ("evidence_conflict", lambda d: d["new_evidence"].update({"EV-A": next(iter(d["new_evidence"].values()))})),
    ("new_char_all_no", lambda d: d["new_characters"]["R3"].update(event_cognitions={f"E{i}": {"state": "否", "detail": "", "evidence_refs": []} for i in range(1, 8)})),
    ("R1_all_no", lambda d: d["added_cognitions"].update(R1={e: {"state": "否", "detail": "", "evidence_refs": []} for e in X.NEW_EVENTS})),
    ("dup_name", lambda d: d["new_characters"]["R4"].update(name="周岩")),
    ("bracket_name", lambda d: d["new_characters"]["R4"].update(name="【顾明】")),
    ("bad_state", lambda d: d["new_characters"]["R4"]["event_cognitions"]["E2"].update(state="严重")),
    ("event_nobody_knows", lambda d: [d["new_characters"][c]["event_cognitions"]["E5"].update(state="否") for c in X.NEW_IDS]),
    ("extra_top_key", lambda d: d.update(extra=1)),
    ("no_json", None),
])
def test_invalid_delta_fails_closed_and_evicts_cache(tmp_path, name, mutate):
    runner, root = make_prototype_project(tmp_path)
    llm = ScriptedLLM(runner, root)
    if mutate is None:
        text = "没有 JSON"
    else:
        bad = json.loads(json.dumps(delta_for(proto_matrix(root))))
        mutate(bad)
        text = "```json\n" + json.dumps(bad, ensure_ascii=False) + "\n```"
    llm.overrides["expand_matrix"] = text
    before = snapshot_tree(root)
    assert runner.run_expand(accept_overwrite=True) is False
    res = runner.last_expand_result
    assert res.status is S.FAILED_VALIDATION and res.failed_step == "expand_matrix" and res.problems
    assert snapshot_tree(root) == before and llm.ops == ["expand_matrix"]
    assert LLMCache(root).stats()["entries"] == 0  # 被拒响应的缓存已清除
    runner.run_expand(accept_overwrite=True)
    assert llm.ops[:2] == ["expand_matrix", "expand_matrix"]  # 重跑重新调用模型，不重放坏响应


@pytest.mark.parametrize("op,text,needle", [
    ("expand_dm", "第一部分 林深 苏晚 周岩 顾明 宋青 唐宁 E1 E2 E3 E4 E5 E6 E7", "4096"),
    ("expand_endings", "结局A 结局B", "结局C"),
    ("expand_a_R3", "## 【周岩】：开场白\n内容\n## 【周岩】：关系自述\n内容\n## 【周岩】：关键事件回忆\n[E1]", "当前处境"),
    ("expand_b_R3", "## 【周岩】：新发现\n线索1：甲\n## 【周岩】：抉择时刻\nx\n## 【周岩】：隐藏信息\n足够长的一句话内容内容内容", "线索2"),
])
def test_truncation_proxies_rejected(tmp_path, op, text, needle):
    runner, root = make_prototype_project(tmp_path)
    ScriptedLLM(runner, root, overrides={op: text})
    before = snapshot_tree(root)
    assert runner.run_expand(accept_overwrite=True) is False
    res = runner.last_expand_result
    assert res.failed_step == op and needle in "".join(res.problems)
    assert snapshot_tree(root) == before


@pytest.mark.parametrize("kind", ["forbidden_event", "foreign_heading"])
def test_cross_knowledge_and_foreign_headings_rejected(tmp_path, kind):
    runner, root = make_prototype_project(tmp_path)
    probe = ScriptedLLM(runner, root)
    forbidden = next(e for e in X.ALL_EVENTS if probe.cells["R3"][e] == "否")
    bad = probe.good("expand_a_R3") + (f"\n[{forbidden}] 不该知道" if kind == "forbidden_event" else "\n## 【顾明】：开场白\n混入他人")
    probe.overrides["expand_a_R3"] = bad
    assert runner.run_expand(accept_overwrite=True) is False
    assert runner.last_expand_result.failed_step == "expand_a_R3"


# ── 前置条件、确认、并发 ─────────────────────────────────────────────

@pytest.mark.parametrize("what", ["missing_dm", "missing_mechanism", "missing_matrix", "all_no_matrix",
                                  "matrix_6x7", "already_appended", "name_mismatch", "empty_outline"])
def test_preconditions_fail_before_any_model_call(tmp_path, what):
    import shutil
    runner, root = make_prototype_project(tmp_path)
    mpath = root / X.MATRIX_REL
    raw = json.loads(mpath.read_text(encoding="utf-8"))
    if what == "missing_dm":
        (root / "dm_manual.md").unlink()
    elif what == "missing_mechanism":
        (root / "mechanism.md").unlink()
    elif what == "missing_matrix":
        shutil.rmtree(root / "state")
    elif what == "all_no_matrix":
        for c in raw["characters"].values():
            for cell in c["event_cognitions"].values():
                cell["state"] = "否"
        mpath.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    elif what == "matrix_6x7":
        raw["char_count"], raw["event_count"] = 6, 7
        mpath.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        (root / "characters.md.proto.20200101_000000").write_text("x", encoding="utf-8")
    elif what == "already_appended":
        (root / "characters.md").write_text("林深 苏晚\n# 扩写追加：x\n", encoding="utf-8")
    elif what == "name_mismatch":
        (root / "characters.md").write_text("只有林深\n", encoding="utf-8")
    elif what == "empty_outline":
        runner.state.outline = ""
    runner.llm.complete.side_effect = AssertionError("不应调用模型")
    before = snapshot_tree(root)
    assert runner.run_expand(accept_overwrite=True) is False
    assert runner.last_expand_result.status is S.REFUSED
    assert runner.llm.complete.call_count == 0 and snapshot_tree(root) == before
    assert what == "missing_matrix" and not (root / "state").exists() or what != "missing_matrix"


def test_requires_confirmation_before_any_spend_and_decline_keeps_work(tmp_path):
    runner, root = make_prototype_project(tmp_path)
    llm = ScriptedLLM(runner, root)
    before = snapshot_tree(root)
    assert runner.run_expand() is False  # Web 无参路径：没有确认入口
    assert runner.last_expand_result.status is S.REFUSED and llm.ops == []
    assert runner.run_expand(confirm=lambda plan: False) is False
    assert runner.last_expand_result.status is S.DECLINED and snapshot_tree(root) == before
    assert runner.session.load().is_prototype is True and len(llm.ops) == 19
    assert runner.run_expand(confirm=lambda plan: False) is False
    assert len(llm.ops) == 19  # 再次运行全部命中缓存
    seen = {}
    assert runner.run_expand(confirm=lambda plan: seen.setdefault("p", plan) is not None) is True
    assert set(seen["p"].candidate_files) >= set(X.COMMIT_ORDER) | {"mechanism.md"}
    assert seen["p"].new_character_names == NEW_NAMES and len(llm.ops) == 19


def test_concurrent_edit_before_commit_is_detected(tmp_path):
    runner, root = make_prototype_project(tmp_path)
    edited = {}

    def on_call(n, op):
        if n == 5:
            (root / "characters.md").write_text("作者刚改过 林深 苏晚", encoding="utf-8")
            edited["t"] = (root / "characters.md").read_bytes()
    ScriptedLLM(runner, root, on_call=on_call)
    assert runner.run_expand(accept_overwrite=True) is False
    assert runner.last_expand_result.status is S.CHANGED_DURING_RUN
    assert (root / "characters.md").read_bytes() == edited["t"] and not list(root.rglob("*.proto.*"))


def test_rerun_replays_accepted_steps_from_cache(tmp_path):
    runner, root = make_prototype_project(tmp_path)
    llm = ScriptedLLM(runner, root, fail={"expand_dm": "invalid"})
    assert runner.run_expand(accept_overwrite=True) is False and len(llm.ops) == 18
    llm.fail.clear()
    assert runner.run_expand(accept_overwrite=True) is True
    assert llm.ops[18:] == ["expand_dm", "expand_endings"]
    assert runner.last_expand_result.cached_calls == 17


# ── 提交失败与回滚 ───────────────────────────────────────────────────

def _no_proto(root):
    return {r: b for r, b in snapshot_tree(root).items() if ".proto." not in r}


@pytest.mark.parametrize("k", range(1, 8))
def test_commit_write_failure_rolls_back(tmp_path, monkeypatch, k):
    runner, root = make_prototype_project(tmp_path)
    ScriptedLLM(runner, root)
    before = snapshot_tree(root)
    real, n = FC._replace, {"n": 0}

    def flaky(a, b):
        n["n"] += 1
        if n["n"] == k:
            raise OSError("disk full")
        return real(a, b)
    monkeypatch.setattr(FC, "_replace", flaky)
    assert runner.run_expand(accept_overwrite=True) is False
    assert runner.last_expand_result.status is S.COMMIT_RESTORED
    assert _no_proto(root) == before
    assert runner.session.load().is_prototype is True and runner.state.is_prototype is True


@pytest.mark.parametrize("case", ["session", "backup", "interrupt"])
def test_session_backup_and_interrupt_failures_restore(tmp_path, monkeypatch, case):
    runner, root = make_prototype_project(tmp_path)
    ScriptedLLM(runner, root)
    before = snapshot_tree(root)
    if case == "session":
        monkeypatch.setattr(runner.session, "save", lambda s: (_ for _ in ()).throw(OSError("save failed")))
    elif case == "backup":
        monkeypatch.setattr(FC, "_copy", lambda a, b: (_ for _ in ()).throw(OSError("no space")))
    else:
        monkeypatch.setattr(FC, "_replace", lambda a, b: (_ for _ in ()).throw(KeyboardInterrupt()))
    if case == "interrupt":
        with pytest.raises(KeyboardInterrupt):
            runner.run_expand(accept_overwrite=True)
    else:
        assert runner.run_expand(accept_overwrite=True) is False
        assert runner.last_expand_result.status is S.COMMIT_RESTORED
    assert _no_proto(root) == before and runner.state.is_prototype is True


def test_restore_failure_reports_incomplete_with_cp_commands(tmp_path, monkeypatch):
    runner, root = make_prototype_project(tmp_path)
    ScriptedLLM(runner, root)
    real, n = FC._replace, {"n": 0}

    def flaky(a, b):
        n["n"] += 1
        if n["n"] >= 2:
            raise OSError("boom")
        return real(a, b)
    monkeypatch.setattr(FC, "_replace", flaky)
    assert runner.run_expand(accept_overwrite=True) is False
    res = runner.last_expand_result
    assert res.status is S.COMMIT_RESTORE_INCOMPLETE and res.restore_failed
    out = runner.console.export_text()
    assert "cp " in out and "混合状态" in out


# ── file_commit 与纯函数 ─────────────────────────────────────────────

def test_file_commit_unit(tmp_path):
    (tmp_path / "a.md").write_text("A", encoding="utf-8")
    FC.commit_files(tmp_path, {"a.md": "A2"}, backup_tag="proto", stamp="T1")
    assert (tmp_path / "a.md.proto.T1").read_text() == "A"
    with pytest.raises(FC.CommitFailed) as e:
        FC.commit_files(tmp_path, {"a.md": "A3"}, backup_tag="proto", stamp="T1", verify=lambda: ["不一致"])
    assert (tmp_path / "a.md").read_text() == "A2" and (tmp_path / "a.md.proto.T1").read_text() == "A"
    assert e.value.report.tag == "T1_2" and (tmp_path / "a.md.proto.T1_2").exists()
    for bad in ("../x.md", "/etc/x", "missing.md"):
        with pytest.raises(FC.CommitFailed) as ei:
            FC.commit_files(tmp_path, {bad: "x"}, backup_tag="proto")
        assert ei.value.stage == "precheck"
    assert not list(tmp_path.glob("*.expand_tmp"))


def test_pure_functions(tmp_path):
    runner, root = make_prototype_project(tmp_path)
    proto = proto_matrix(root)
    assert X.append_section("原文\r\n", "H", "b").startswith("原文\r\n")
    assert X.append_section("无换行", "H", "b").startswith("无换行")
    assert X.extract_json_object('前言 {"a": "}{", "characters": 1} 后记', ["characters"]) == {"a": "}{", "characters": 1}
    assert X.extract_json_object("没有", ["characters"]) is None
    merged = X.merge_delta(proto, json.dumps(delta_for(proto), ensure_ascii=False))
    assert not X.verify_prototype_retained(proto, merged.matrix)
    tampered = merged.matrix.model_copy(deep=True)
    tampered.characters["R1"].event_cognitions["E1"].detail = "被改"
    assert X.verify_prototype_retained(proto, tampered)
    md1, md2 = (X.render_matrix_markdown(merged.matrix, merged.new_events) for _ in range(2))
    assert md1 == md2 and all(e in md1 for e in X.ALL_EVENTS) and all(k in md1 for k in merged.matrix.evidence)
    assert X.check_tail("abc", "第六部分") and X.check_event_tags("[E9]", {}, [])
    assert X.check_headings("## 【甲】开头", "乙", [])


def test_templates_contract():
    from murder_wizard.cli.phase_runner import PhaseRunner
    from murder_wizard.prompts.loader import PromptLoader, PromptRenderError
    loader = PromptLoader()
    for tpl, required in X.EXPAND_PROMPTS.items():
        assert set(re.findall(r"\{\{(\w+)\}\}", loader._load_raw(tpl))) == set(required), tpl
        vals = {k: "x" for k in required}
        vals["brief_content" if "brief_content" in vals else required[0]] = "{{x}}"
        out = loader.render(tpl, strict=True, required_inputs=required, is_prototype=False, **vals)
        assert "{{x}}" in out and "{{" not in out.replace("{{x}}", "")
        missing = {k: "x" for k in required[1:]}
        with pytest.raises(PromptRenderError):
            loader.render(tpl, strict=True, required_inputs=required, is_prototype=False, **missing)
    assert set(X.STAGE_2_FILES) == set(PhaseRunner.STAGE_2_REQUIRED_ARTIFACTS)
