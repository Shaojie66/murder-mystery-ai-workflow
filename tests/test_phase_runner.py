"""Regression tests for phase runner resume logic."""
from unittest.mock import MagicMock, patch

from rich.console import Console

from murder_wizard.cli.phase_runner import PhaseRunner
from murder_wizard.llm.client import LLMResponse, LONG_OUTPUT_MAX_TOKENS
from murder_wizard.wizard.session import SessionManager
from murder_wizard.wizard.state_machine import MurderWizardState, Stage


def _response(content: str, *, tokens: int = 100, cost: float = 0.01) -> LLMResponse:
    return LLMResponse(content=content, tokens_used=tokens, cost=cost, model="mock-model")


def _make_runner(tmp_path, *, state: MurderWizardState | None = None):
    session = SessionManager("demo", base_path=str(tmp_path))
    if state is None:
        state = MurderWizardState(
            project_name="demo",
            story_type="mechanic",
            current_stage=Stage.STAGE_1_MECHANISM,
            outline="# Outline",
        )
    session.save(state)
    console = Console(record=True, width=120)

    with patch.object(PhaseRunner, "_setup_llm"):
        runner = PhaseRunner(session, state, console)
        runner.llm = MagicMock()

    return runner


def test_stage_2_artifact_status_detects_partial_outputs(tmp_path):
    runner = _make_runner(tmp_path)
    (runner.session.project_path / "characters.md").write_text("# chars", encoding="utf-8")

    existing, missing = runner._stage_2_artifact_status()

    assert existing == ["characters.md"]
    assert "information_matrix.md" in missing
    assert "dm_manual.md" in missing
    assert len(missing) == len(PhaseRunner.STAGE_2_REQUIRED_ARTIFACTS) - 1


def test_run_stage_2_does_not_skip_when_only_partial_outputs_exist(tmp_path):
    runner = _make_runner(tmp_path)
    (runner.session.project_path / "mechanism.md").write_text("# mechanism", encoding="utf-8")
    (runner.session.project_path / "characters.md").write_text("# chars", encoding="utf-8")

    def fail_after_first_call(*args, **kwargs):
        raise RuntimeError("stop-after-confirming-stage-started")

    runner._call_llm = fail_after_first_call

    ok = runner.run_stage_2()

    assert ok is False
    output = runner.console.export_text()
    assert "阶段2部分完成" in output
    assert "阶段2已完成，跳过" not in output


def test_run_stage_2_skips_only_when_all_outputs_exist(tmp_path):
    runner = _make_runner(tmp_path)
    (runner.session.project_path / "mechanism.md").write_text("# mechanism", encoding="utf-8")
    for artifact in PhaseRunner.STAGE_2_REQUIRED_ARTIFACTS:
        (runner.session.project_path / artifact).write_text(artifact, encoding="utf-8")

    ok = runner.run_stage_2()

    assert ok is True
    output = runner.console.export_text()
    assert "阶段2已完成，跳过" in output


def test_run_stage_1_requires_outline(tmp_path):
    runner = _make_runner(
        tmp_path,
        state=MurderWizardState(
            project_name="demo",
            story_type="mechanic",
            current_stage=Stage.IDLE,
            outline="",
        ),
    )

    ok = runner.run_stage_1()

    assert ok is False
    assert "缺少大纲" in runner.console.export_text()


def test_run_stage_1_creates_artifacts_and_advances_state(tmp_path):
    runner = _make_runner(
        tmp_path,
        state=MurderWizardState(
            project_name="demo",
            story_type="mechanic",
            current_stage=Stage.IDLE,
            outline="# Outline",
            is_prototype=True,
        ),
    )
    runner._call_llm = MagicMock(
        side_effect=[
            _response("# Q1"),
            _response("# Mechanism"),
            _response("# Q3"),
        ]
    )

    ok = runner.run_stage_1()

    assert ok is True
    assert (runner.session.project_path / "mechanism.md").exists()
    assert (runner.session.project_path / "stage1_full_design.md").exists()
    assert runner.session.load().current_stage == Stage.STAGE_1_MECHANISM


def test_run_stage_3_creates_image_prompts_and_advances_state(tmp_path):
    runner = _make_runner(tmp_path)
    (runner.session.project_path / "characters.md").write_text("# characters", encoding="utf-8")
    runner._call_llm = MagicMock(return_value=_response("# prompts"))

    ok = runner.run_stage_3()

    assert ok is True
    assert (runner.session.project_path / "image-prompts.md").exists()
    assert runner.session.load().current_stage == Stage.STAGE_3_VISUAL


def test_run_stage_4_creates_test_guide_and_advances_state(tmp_path):
    runner = _make_runner(tmp_path)
    (runner.session.project_path / "characters.md").write_text("# characters", encoding="utf-8")
    (runner.session.project_path / "mechanism.md").write_text("# mechanism", encoding="utf-8")
    runner._call_llm = MagicMock(return_value=_response("# guide"))

    ok = runner.run_stage_4()

    assert ok is True
    assert (runner.session.project_path / "test_guide.md").exists()
    assert runner.session.load().current_stage == Stage.STAGE_4_TEST


def test_run_stage_5_creates_commercial_plan_and_advances_state(tmp_path):
    runner = _make_runner(tmp_path)
    (runner.session.project_path / "characters.md").write_text("# characters", encoding="utf-8")
    (runner.session.project_path / "mechanism.md").write_text("# mechanism", encoding="utf-8")
    runner._call_llm = MagicMock(return_value=_response("# commercial"))

    ok = runner.run_stage_5()

    assert ok is True
    assert (runner.session.project_path / "commercial.md").exists()
    assert runner.session.load().current_stage == Stage.STAGE_5_COMMERCIAL


def test_run_stage_6_generates_print_artifacts_and_advances_state(tmp_path):
    runner = _make_runner(tmp_path)
    (runner.session.project_path / "characters.md").write_text("# characters", encoding="utf-8")

    fake_generator = MagicMock()
    fake_generator.check_print_ready.return_value = (True, [])
    for name in ("script.pdf", "线索卡.pdf"):
        (runner.session.project_path / name).write_bytes(b"%PDF-1.4 test")
    fake_generator.generate_script_pdf.return_value = str(runner.session.project_path / "script.pdf")
    fake_generator.generate_clue_cards.return_value = str(runner.session.project_path / "线索卡.pdf")
    fake_generator.generate_proof_order.return_value = {"copies": 50}

    with patch("murder_wizard.print.pdf_gen.PDFGenerator", return_value=fake_generator):
        ok = runner.run_stage_6()

    assert ok is True
    assert (runner.session.project_path / "print_order.json").exists()
    assert runner.session.load().current_stage == Stage.STAGE_6_PRINT


def test_run_stage_7_creates_promo_content_and_advances_state(tmp_path):
    runner = _make_runner(tmp_path)
    (runner.session.project_path / "characters.md").write_text("# characters", encoding="utf-8")
    (runner.session.project_path / "mechanism.md").write_text("# mechanism", encoding="utf-8")
    runner._call_llm = MagicMock(return_value=_response("# promo"))

    ok = runner.run_stage_7()

    assert ok is True
    assert (runner.session.project_path / "promo_content.md").exists()
    assert runner.session.load().current_stage == Stage.STAGE_7_PROMO


def test_run_stage_8_creates_community_plan_and_advances_state(tmp_path):
    runner = _make_runner(tmp_path)
    (runner.session.project_path / "characters.md").write_text("# characters", encoding="utf-8")
    (runner.session.project_path / "mechanism.md").write_text("# mechanism", encoding="utf-8")
    runner._call_llm = MagicMock(return_value=_response("# community"))

    ok = runner.run_stage_8()

    assert ok is True
    assert (runner.session.project_path / "community_plan.md").exists()
    assert runner.session.load().current_stage == Stage.STAGE_8_COMMUNITY


# ─── R01：阶段 2 提示词输入契约 ──────────────────────────────────────────────

import json

import pytest

from murder_wizard.prompts.loader import PromptRenderError
from murder_wizard.wizard.schemas import CharacterMatrix

_STAGE_2_HEADINGS = [
    "## Q1：信息矩阵生成",
    "## Q2：角色背景生成",
    "## Q3：a本（阅读本）生成",
    "## Q4：b本（线索本）生成",
    "## Q5：DM手册生成",
    "## Q6：结局扩展",
]


def _stage_2_state(*, outline: str = "# 简报\n民国戏班旧案", is_prototype: bool = True) -> MurderWizardState:
    return MurderWizardState(
        project_name="demo",
        story_type="mechanic",
        current_stage=Stage.STAGE_1_MECHANISM,
        outline=outline,
        is_prototype=is_prototype,
    )


def _flat_output(runner) -> str:
    return runner.console.export_text().replace("\n", "")


def test_run_stage_2_empty_outline_fails_before_calling_llm(tmp_path):
    runner = _make_runner(tmp_path, state=_stage_2_state(outline=""))
    (runner.session.project_path / "mechanism.md").write_text("# mechanism", encoding="utf-8")
    runner._call_llm = MagicMock(return_value=_response("不应被调用"))

    ok = runner.run_stage_2()

    assert ok is False
    runner._call_llm.assert_not_called()
    output = _flat_output(runner)
    assert "阶段2失败" in output
    assert "brief_content" in output
    assert "未调用模型" in output
    assert not (runner.session.project_path / "information_matrix.md").exists()
    assert runner.session.load().current_stage == Stage.STAGE_1_MECHANISM


def test_run_stage_2_blank_mechanism_fails_before_calling_llm(tmp_path):
    runner = _make_runner(tmp_path, state=_stage_2_state())
    (runner.session.project_path / "mechanism.md").write_text("  \n\t\n", encoding="utf-8")
    runner._call_llm = MagicMock(return_value=_response("不应被调用"))

    ok = runner.run_stage_2()

    assert ok is False
    runner._call_llm.assert_not_called()
    assert "mechanism_content" in _flat_output(runner)
    assert not (runner.session.project_path / "information_matrix.md").exists()


def test_stage_2_builders_raise_prompt_render_error_for_missing_inputs(tmp_path):
    runner = _make_runner(tmp_path, state=_stage_2_state())
    # 无 mechanism.md：Q3/Q4 的机制输入缺失
    with pytest.raises(PromptRenderError) as no_matrix:
        runner._build_background_prompt("简报", "")
    assert "matrix_content" in no_matrix.value.missing

    with pytest.raises(PromptRenderError) as no_mechanism_a:
        runner._build_characters_prompt("背景", "矩阵")
    assert no_mechanism_a.value.missing == ("mechanism_content",)

    with pytest.raises(PromptRenderError) as no_mechanism_b:
        runner._build_clue_cards_prompt("a本", "矩阵")
    assert no_mechanism_b.value.missing == ("mechanism_content",)

    with pytest.raises(PromptRenderError) as no_dm:
        runner._build_endings_prompt("完整剧本", "矩阵", "  ")
    assert "dm_manual" in no_dm.value.missing


@pytest.mark.parametrize("is_prototype,rule,last_event", [
    (True, "2人拼图 = 完整真相", "| E3（核心） |"),
    (False, "没有任何角色拥有全部真相", "| E7（核心） |"),
])
def test_matrix_prompt_has_default_fill_rules_and_table(tmp_path, is_prototype, rule, last_event):
    runner = _make_runner(tmp_path, state=_stage_2_state(is_prototype=is_prototype))

    prompt = runner._build_matrix_prompt("简报", "机制")

    assert rule in prompt
    assert last_event in prompt
    assert "| | R1 |" in prompt
    assert "## 填充规则\n\n" not in prompt


def test_run_stage_2_sends_each_step_only_its_own_prompt(tmp_path):
    runner = _make_runner(tmp_path, state=_stage_2_state(is_prototype=True))
    (runner.session.project_path / "mechanism.md").write_text("# 机制：三轮搜证", encoding="utf-8")

    matrix_json = json.dumps(_matrix_data(), ensure_ascii=False)
    prompts: list[str] = []

    def fake_llm(prompt, system="", operation="llm_call", max_tokens=None):
        prompts.append(prompt)
        if operation == "stage_2_matrix":
            return _response(f"```json\n{matrix_json}\n```")
        return _response(f"# {operation} 内容")

    runner._call_llm = fake_llm

    ok = runner.run_stage_2()

    assert ok is True
    step_prompts = prompts[:6]  # 之后是轻量穿帮检查，不属于本批次
    assert len(step_prompts) == 6
    for index, (prompt, heading) in enumerate(zip(step_prompts, _STAGE_2_HEADINGS), start=1):
        assert heading in prompt, f"第 {index} 步缺少本步标题"
        for other in _STAGE_2_HEADINGS:
            if other != heading:
                assert other not in prompt, f"第 {index} 步混入了其他步骤：{other}"
        assert "{{" not in prompt, f"第 {index} 步仍有未替换变量"
    CharacterMatrix.model_validate_json(
        (runner.session.project_path / "state" / "character_matrix.json").read_text(encoding="utf-8")
    )


# ─── R02：阶段 2 Q1 失败关闭 ─────────────────────────────────────────────────
# 用真实的 PhaseRunner._call_llm（含 LLMCache），只替换适配器的 complete()，
# 这样"重试是否重放缓存里的坏响应"才是真实可观察的行为。

import copy

from murder_wizard.llm.cache import LLMCache
from murder_wizard.prompts.loader import EXAMPLE_PLACEHOLDER_MARK, PromptLoader, build_matrix_example
from murder_wizard.wizard.truth_files import (
    MatrixContractError,
    TruthFileManager,
    validate_generated_matrix,
)

_Q1_HEADING = "## Q1：信息矩阵生成"


def _authored(value):
    """把示例的占位标记换成作者自己的文字：得到一份"作者写的"矩阵。示例是提示词里的模板，不是合法答案（见 R02 照抄示例用例）。

    不能只删标记：剩下的「角色1姓名」「认知说明」仍是示例原文，照抄检查（正确地）会拒绝它。
    """
    if isinstance(value, str):
        return value.replace(EXAMPLE_PLACEHOLDER_MARK, "·作者稿")
    if isinstance(value, dict):
        return {key: _authored(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_authored(item) for item in value]
    return value


def _matrix_data(is_prototype: bool = True) -> dict:
    char_count, event_count = (2, 3) if is_prototype else (6, 7)
    return _authored(build_matrix_example(char_count, event_count, is_prototype))


def _fenced(data: dict) -> str:
    return "```json\n" + json.dumps(data, ensure_ascii=False, indent=2) + "\n```"


def _mutated(mutate, is_prototype: bool = True) -> str:
    data = _matrix_data(is_prototype)
    mutate(data)
    return _fenced(data)


def _set_all_states(data: dict, state: str) -> None:
    for entry in data["characters"].values():
        for cell in entry["event_cognitions"].values():
            cell["state"] = state


def _nobody_knows_e3(data: dict) -> None:
    for entry in data["characters"].values():
        cell = entry["event_cognitions"]["E3"]
        if cell["state"] == "知":
            cell["state"] = "疑"


_VALID_JSON_TEXT = _fenced(_matrix_data())


def _surrogate_escape_reply(mutate) -> str:
    """回复文本里写的是 JSON 转义 \\ud800（孤立代理项）：json.loads 能解析，解出的字符串却无法编码成 UTF-8。

    mutate 用占位词 SURROGATE 标出位置。不能直接把孤立代理项放进 Python 字符串：那样缓存写盘就先失败了，测不到校验。
    """
    data = _matrix_data()
    mutate(data)
    return _fenced(data).replace("SURROGATE", "\\ud800")


# (id, 构造坏响应, 控制台输出里必须出现的问题片段)
_BAD_Q1_RESPONSES = [
    ("markdown_table_only",
     lambda: "# 信息矩阵\n\n| | R1 | R2 |\n|---|---|---|\n| E1 | 知 | 疑 |\n| E2 | 知 | 否 |\n| E3 | 知 | 知 |\n",
     ["没有可解析的 JSON"]),
    ("empty_response", lambda: "", ["没有可解析的 JSON"]),
    ("truncated_json", lambda: _VALID_JSON_TEXT[: len(_VALID_JSON_TEXT) // 2], ["没有可解析的 JSON"]),
    ("malformed_json",
     lambda: '```json\n{"characters": {"R1": {"event_cognitions": {\'E1\': 1,}}}}\n```',
     ["没有可解析的 JSON"]),
    ("old_example_pipe_literal_state",
     lambda: _mutated(lambda d: d["characters"]["R1"]["event_cognitions"]["E1"].update(
         state="知|疑|昧|否|误信|隐瞒")),
     ["state 非法"]),
    ("bracketed_state",
     lambda: _mutated(lambda d: d["characters"]["R2"]["event_cognitions"]["E2"].update(state="[疑]")),
     ["state 非法"]),
    # 看起来像 Rich 标记的模型文本（闭合标签）：问题文字不转义就会让失败处理自己抛 MarkupError，
    # 逐出缓存的那一行永远执行不到，重试被缓存里的坏响应卡死
    ("markup_like_state",
     lambda: _mutated(lambda d: d["characters"]["R2"]["event_cognitions"]["E2"].update(state="[/疑]")),
     ["state 非法", "[/疑]"]),
    ("missing_character", lambda: _mutated(lambda d: d["characters"].pop("R2")), ["缺少角色 R2"]),
    ("missing_event_cell",
     lambda: _mutated(lambda d: d["characters"]["R1"]["event_cognitions"].pop("E2")),
     ["缺少事件认知"]),
    ("empty_characters", lambda: _mutated(lambda d: d.update(characters={})), ["characters 为空"]),
    ("all_no_matrix", lambda: _mutated(lambda d: _set_all_states(d, "否")), ["所有认知状态均为「否」"]),
    ("no_evidence", lambda: _mutated(lambda d: d.update(evidence={})), ["evidence 为空"]),
    ("evidence_missing_field",
     lambda: _mutated(lambda d: d["evidence"]["EV-A"].pop("description")),
     ["缺少字段 description"]),
    ("dangling_evidence_ref",
     lambda: _mutated(lambda d: d["characters"]["R1"]["event_cognitions"]["E2"].update(
         evidence_refs=["EV-ZZZ"])),
     ["EV-ZZZ", "不存在的证据"]),
    ("event_nobody_knows", lambda: _mutated(_nobody_knows_e3), ["事件 E3", "没有任何角色为「知」"]),
    ("full_mode_matrix_in_prototype_run",
     lambda: _fenced(_matrix_data(is_prototype=False)),
     ["char_count 应为 2", "多余角色 R3"]),
    # 通过了全部结构检查，却无法编码成 UTF-8：发布时才崩溃的话，被拒绝的回复就留在缓存里被无限重放
    ("lone_surrogate_escape",
     lambda: _surrogate_escape_reply(lambda d: d["characters"]["R1"]["event_cognitions"]["E1"].update(
         detail="说明SURROGATE")),
     ["无法保存的字符", "characters.R1.event_cognitions.E1.detail"]),
]
_BAD_Q1_IDS = [case[0] for case in _BAD_Q1_RESPONSES]


def _squashed(text: str) -> str:
    """去掉全部空白：Rich 折行可能吃掉空格，比较时两边都压缩."""
    return "".join(text.split())


def _attach_llm(runner, q1_responses: list[str]) -> dict:
    """让适配器 complete() 对 Q1 按顺序返回 q1_responses，其余步骤返回占位内容。"""
    runner.llm.model = "mock-model"
    queue = list(q1_responses)
    calls = {"q1": 0, "other": 0, "prompts": []}

    def complete(prompt, system="", max_tokens=None):
        calls["prompts"].append(prompt)
        if _Q1_HEADING in prompt:
            calls["q1"] += 1
            return _response(queue.pop(0))
        calls["other"] += 1
        return _response("# 后续步骤内容")

    runner.llm.complete.side_effect = complete
    return calls


def _stage_2_runner(tmp_path, q1_responses: list[str], *, is_prototype: bool = True):
    runner = _make_runner(tmp_path, state=_stage_2_state(is_prototype=is_prototype))
    (runner.session.project_path / "mechanism.md").write_text("# 机制：三轮搜证", encoding="utf-8")
    return runner, _attach_llm(runner, q1_responses)


def _seed_previous_matrix(runner) -> None:
    """预置此前有效的矩阵与 information_matrix.md（作者已确认的旧作品）。"""
    data = _matrix_data()
    data["characters"]["R1"]["name"] = "旧版林远"
    previous = validate_generated_matrix(data, 2, 3, True, brief_content="旧简报")
    TruthFileManager(runner.session.project_path).save_matrix(previous)
    (runner.session.project_path / "information_matrix.md").write_text(
        "# 旧矩阵（作者已确认）\n", encoding="utf-8"
    )


def _snapshot(runner) -> dict[str, bytes]:
    """项目目录下全部文件的原始字节。cache.json / cost.log 是调用模型的预期副作用，不计入。"""
    root = runner.session.project_path
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name not in ("cache.json", "cost.log")
    }


def _cached_operations(project_path) -> list[str]:
    cache_file = project_path / "cache.json"
    if not cache_file.exists():
        return []
    return [entry["operation"] for entry in json.loads(cache_file.read_text(encoding="utf-8")).values()]


def _published_matrix_md(data: dict | None = None, is_prototype: bool = True) -> str:
    """information_matrix.md 的预期内容：由校验通过的矩阵生成，而不是模型的原始回复。"""
    char_count, event_count = (2, 3) if is_prototype else (6, 7)
    matrix = validate_generated_matrix(
        data if data is not None else _matrix_data(is_prototype), char_count, event_count, is_prototype
    )
    return PhaseRunner._render_matrix_markdown(matrix)


@pytest.mark.parametrize("make_response,needles", [case[1:] for case in _BAD_Q1_RESPONSES], ids=_BAD_Q1_IDS)
def test_run_stage_2_bad_q1_fails_and_keeps_previous_work_byte_identical(tmp_path, make_response, needles):
    runner, calls = _stage_2_runner(tmp_path, [make_response()])
    _seed_previous_matrix(runner)
    before = _snapshot(runner)

    ok = runner.run_stage_2()

    assert ok is False
    assert calls["q1"] == 1, "一次尝试只应调用一次模型"
    assert calls["other"] == 0, "Q1 失败后不应继续 Q2-Q6"
    # 旧矩阵、information_matrix.md、session.json 及其余全部文件逐字节不变，也没有生成新文件
    assert _snapshot(runner) == before
    assert runner.session.load().current_stage == Stage.STAGE_1_MECHANISM
    output = _squashed(_flat_output(runner))
    assert "Q1失败" in output
    for needle in needles:
        assert _squashed(needle) in output, f"控制台没有报出问题：{needle}"
    assert "阶段2全部完成" not in output
    # 被拒绝的响应不再留在缓存里
    assert "stage_2_matrix" not in _cached_operations(runner.session.project_path)


@pytest.mark.parametrize("make_response", [case[1] for case in _BAD_Q1_RESPONSES], ids=_BAD_Q1_IDS)
def test_run_stage_2_bad_q1_writes_no_default_matrix_when_nothing_existed(tmp_path, make_response):
    runner, calls = _stage_2_runner(tmp_path, [make_response()])
    project = runner.session.project_path
    before = _snapshot(runner)

    with patch.object(TruthFileManager, "migrate_from_markdown", autospec=True) as migrate:
        ok = runner.run_stage_2()

    assert ok is False
    migrate.assert_not_called()  # 生成路径不再用有损的 Markdown 迁移兜底
    assert not (project / "state").exists(), "不应创建 state 目录"
    assert not (project / "state" / "character_matrix.json").exists(), "不应写出（默认「否」的）矩阵"
    assert not (project / "information_matrix.md").exists()
    assert _snapshot(runner) == before
    assert runner.session.load().current_stage == Stage.STAGE_1_MECHANISM
    assert calls["q1"] == 1 and calls["other"] == 0


@pytest.mark.parametrize("is_prototype,wrong_data", [
    (True, _matrix_data(is_prototype=False)),
    (False, _matrix_data(is_prototype=True)),
], ids=["prototype_run_got_6x7", "full_run_got_2x3"])
def test_run_stage_2_rejects_matrix_sized_for_the_other_mode(tmp_path, is_prototype, wrong_data):
    runner, calls = _stage_2_runner(tmp_path, [_fenced(wrong_data)], is_prototype=is_prototype)
    before = _snapshot(runner)

    ok = runner.run_stage_2()

    assert ok is False
    assert _snapshot(runner) == before
    assert not (runner.session.project_path / "state").exists()
    expected_chars = 2 if is_prototype else 6
    assert _squashed(f"char_count 应为 {expected_chars}") in _squashed(_flat_output(runner))


def test_retry_after_bad_q1_calls_the_llm_again_instead_of_replaying_the_cached_response(tmp_path):
    bad = _mutated(lambda d: d["characters"].pop("R2"))
    runner, calls = _stage_2_runner(tmp_path, [bad, _VALID_JSON_TEXT])
    project = runner.session.project_path

    assert runner.run_stage_2() is False
    assert calls["q1"] == 1
    # 坏响应已从磁盘缓存逐出（新实例只读磁盘）
    assert LLMCache(project).stats()["entries"] == 0

    # 同一个 runner 重试：必须重新调用模型，而不是命中缓存里的坏响应
    assert runner.run_stage_2() is True
    assert calls["q1"] == 2, "重试没有重新调用模型：缓存里的坏响应被重放了"
    assert "缓存命中：stage_2_matrix" not in _flat_output(runner)
    loaded = TruthFileManager(project).load_matrix()
    assert loaded is not None and set(loaded.characters) == {"R1", "R2"}
    assert runner.session.load().current_stage == Stage.STAGE_2_SCRIPT


def test_retry_with_a_fresh_runner_does_not_replay_the_cached_bad_response(tmp_path):
    bad = _mutated(lambda d: d["characters"]["R1"]["event_cognitions"].pop("E2"))
    first, first_calls = _stage_2_runner(tmp_path, [bad])
    assert first.run_stage_2() is False
    assert first_calls["q1"] == 1

    # 重新启动 CLI 等价于新建 PhaseRunner：缓存从磁盘重新加载
    second = _make_runner(tmp_path, state=_stage_2_state())
    second_calls = _attach_llm(second, [_VALID_JSON_TEXT])

    assert second.run_stage_2() is True
    assert second_calls["q1"] == 1
    assert (second.session.project_path / "state" / "character_matrix.json").exists()


def test_repeated_bad_attempts_each_call_the_llm_once_and_never_write(tmp_path):
    bad_responses = [
        "# 只有 Markdown，没有 JSON",
        _mutated(lambda d: d.update(characters={})),
        _mutated(lambda d: _set_all_states(d, "否")),
    ]
    runner, calls = _stage_2_runner(tmp_path, bad_responses)
    _seed_previous_matrix(runner)
    before = _snapshot(runner)

    for attempt, _ in enumerate(bad_responses, start=1):
        assert runner.run_stage_2() is False
        assert calls["q1"] == attempt, f"第 {attempt} 次尝试应恰好调用一次模型"
        assert _snapshot(runner) == before

    assert calls["other"] == 0


def test_run_stage_2_valid_q1_saves_matrix_writes_markdown_and_continues(tmp_path):
    response_text = "# 信息矩阵\n\n| | R1 | R2 |\n|---|---|---|\n| E1 | 知 | 疑 |\n\n" + _VALID_JSON_TEXT
    runner, calls = _stage_2_runner(tmp_path, [response_text])
    project = runner.session.project_path

    ok = runner.run_stage_2()

    assert ok is True
    assert calls["q1"] == 1
    expected = validate_generated_matrix(_matrix_data(), 2, 3, True, brief_content="# 简报\n民国戏班旧案")
    loaded = TruthFileManager(project).load_matrix()
    assert loaded is not None
    assert loaded.characters == expected.characters
    assert loaded.evidence == expected.evidence
    assert (loaded.char_count, loaded.event_count, loaded.is_prototype) == (2, 3, True)
    assert loaded.meta.brief_content_hash == expected.meta.brief_content_hash
    # 发布的是校验通过的矩阵，不是模型原始回复：回复里与 JSON 不一致的 Markdown 表格不会进入文件和下游提示词
    published = (project / "information_matrix.md").read_text(encoding="utf-8")
    assert published == _published_matrix_md()
    assert "| E1 | 知 | 疑 |" not in published
    republished = validate_generated_matrix(runner._extract_json_from_response(published), 2, 3, True)
    assert republished.characters == loaded.characters and republished.evidence == loaded.evidence
    # Q2-Q6 照常执行，且拿到的是发布的矩阵，而不是原始回复
    assert calls["other"] >= 5
    assert all(published in prompt for prompt in calls["prompts"][1:6])
    assert not any("| E1 | 知 | 疑 |" in prompt for prompt in calls["prompts"])
    for artifact in PhaseRunner.STAGE_2_REQUIRED_ARTIFACTS:
        assert (project / artifact).exists(), artifact
    assert runner.session.load().current_stage == Stage.STAGE_2_SCRIPT
    # 通过校验的响应保留在缓存里（只有被拒绝的才逐出）
    assert "stage_2_matrix" in _cached_operations(project)


@pytest.mark.parametrize("is_prototype", [True, False], ids=["prototype_2x3", "full_6x7"])
def test_run_stage_2_valid_q1_is_accepted_in_both_modes(tmp_path, is_prototype):
    data = _matrix_data(is_prototype)
    runner, calls = _stage_2_runner(tmp_path, [_fenced(data)], is_prototype=is_prototype)

    assert runner.run_stage_2() is True

    loaded = TruthFileManager(runner.session.project_path).load_matrix()
    assert set(loaded.characters) == set(data["characters"])
    for cid, entry in data["characters"].items():
        for eid, cell in entry["event_cognitions"].items():
            assert loaded.get_cognition(cid, eid) == cell["state"]  # 认知原样保留，没有被改成「否」
    assert runner.session.load().current_stage == Stage.STAGE_2_SCRIPT


def test_run_stage_2_valid_q1_replaces_previous_matrix_and_keeps_a_backup(tmp_path):
    runner, calls = _stage_2_runner(tmp_path, [_VALID_JSON_TEXT])
    _seed_previous_matrix(runner)
    project = runner.session.project_path

    assert runner.run_stage_2() is True

    loaded = TruthFileManager(project).load_matrix()
    assert loaded.characters["R1"].name != "旧版林远"
    backups = list((project / "state" / ".backups").glob("character_matrix.*.json"))
    assert len(backups) == 1
    assert "旧版林远" in backups[0].read_text(encoding="utf-8")
    assert (project / "information_matrix.md").read_text(encoding="utf-8") == _published_matrix_md()


@pytest.mark.parametrize("is_prototype,char_count,event_count", [(True, 2, 3), (False, 6, 7)],
                         ids=["prototype", "full"])
@pytest.mark.parametrize("render", ["stage_2_builder", "markdown_template"])
def test_q1_prompt_example_passes_the_matrix_contract(tmp_path, is_prototype, char_count, event_count, render):
    """R01 与 R02 的衔接：提示词里教给模型的示例，必须能通过模型输出要过的同一道校验。"""
    runner = _make_runner(tmp_path, state=_stage_2_state(is_prototype=is_prototype))
    if render == "stage_2_builder":
        prompt = runner._build_matrix_prompt("简报", "机制")
    else:
        prompt = PromptLoader().information_matrix(
            brief_content="简报", mechanism_content="机制", is_prototype=is_prototype
        )

    example = runner._extract_json_from_response(prompt)

    assert example is not None, "Q1 提示词里没有可解析的 JSON 示例"
    matrix = validate_generated_matrix(example, char_count, event_count, is_prototype, brief_content="简报")
    assert len(matrix.characters) == char_count
    assert all(len(entry.event_cognitions) == event_count for entry in matrix.characters.values())
    assert matrix.evidence
    # 校验确实在按模式把关：同一份示例换成另一种模式的期望就必须被拒绝
    other_chars, other_events = (6, 7) if is_prototype else (2, 3)
    with pytest.raises(MatrixContractError):
        validate_generated_matrix(copy.deepcopy(example), other_chars, other_events, not is_prototype)


# ─── 批次 A 审查修复：意外错误也逐出缓存 / 裸 JSON 提取 / points_to / 空回复 ──────────────


@pytest.mark.parametrize("target,error", [
    ("validate_generated_matrix", RecursionError("maximum recursion depth exceeded")),
    ("validate_generated_matrix", RuntimeError("validator bug")),
    ("_extract_json_from_response", ValueError("extractor bug")),
], ids=["validator_recursion_error", "validator_runtime_error", "extractor_error"])
def test_unexpected_error_while_judging_q1_evicts_the_cached_response(tmp_path, target, error):
    """校验/提取意外抛出非 MatrixContractError 的异常时，响应同样被拒绝：不能留在缓存里被无限重放。"""
    runner, calls = _stage_2_runner(tmp_path, [_VALID_JSON_TEXT, _VALID_JSON_TEXT])
    project = runner.session.project_path
    before = _snapshot(runner)
    if target == "validate_generated_matrix":
        broken = patch("murder_wizard.cli.phase_runner.validate_generated_matrix", side_effect=error)
    else:
        broken = patch.object(PhaseRunner, target, side_effect=error)

    with broken:
        ok = runner.run_stage_2()

    assert ok is False
    assert calls["q1"] == 1 and calls["other"] == 0
    assert _snapshot(runner) == before, "失败不得写入任何文件"
    assert "stage_2_matrix" not in _cached_operations(project)
    assert LLMCache(project).stats()["entries"] == 0
    assert runner.session.load().current_stage == Stage.STAGE_1_MECHANISM
    output = _squashed(_flat_output(runner))
    assert "Q1失败" in output and type(error).__name__ in output
    assert "阶段2全部完成" not in output

    # 修好之后重试：必须重新调用模型，而不是重放缓存里被拒绝的响应
    assert runner.run_stage_2() is True
    assert calls["q1"] == 2, "重试没有重新调用模型：被拒绝的响应仍在缓存里"
    assert "缓存命中：stage_2_matrix" not in _flat_output(runner)
    assert TruthFileManager(project).load_matrix() is not None


def _bare(data: dict, *, indent: int | None = 2) -> str:
    return json.dumps(data, ensure_ascii=False, indent=indent)


def _with_detail(text: str):
    def mutate(data: dict) -> None:
        data["characters"]["R1"]["event_cognitions"]["E1"]["detail"] = text
    return mutate


def _bare_with_braces_in_strings():
    data = _matrix_data()
    _with_detail("他在门口说：用 } 表示未知，用 { 表示开始")(data)
    data["evidence"]["EV-A"]["description"] = '纸条上写着 {"x": 1} 和一个孤零零的 }'
    return data


# (id, 构造裸 JSON 响应，期望提取出的对象)
_BARE_JSON_CASES = [
    ("closing_brace_in_string",
     lambda d: _bare(d), lambda: _mutate_copy(_with_detail("用 } 表示未知"))),
    ("opening_brace_in_string",
     lambda d: _bare(d), lambda: _mutate_copy(_with_detail("用 { 表示开始"))),
    ("braces_and_json_literal_in_strings",
     lambda d: _bare(d, indent=None), _bare_with_braces_in_strings),
    ("lone_brace_in_leading_prose",
     lambda d: "好的，下面是矩阵（注意：{ 表示开始）：\n" + _bare(d), _matrix_data),
    ("trailing_prose_braces_after_matrix_with_brace_in_string",
     lambda d: _bare(d) + "\n以上就是矩阵。注意 } 与 { 的用法。",
     lambda: _mutate_copy(_with_detail("用 } 表示未知"))),
    ("decoy_json_object_before_matrix_with_brace_in_string",
     lambda d: '先给结论：{"note": "按要求输出"}\n' + _bare(d),
     lambda: _mutate_copy(_with_detail("用 } 表示未知"))),
]


def _mutate_copy(mutate) -> dict:
    data = _matrix_data()
    mutate(data)
    return data


@pytest.mark.parametrize("build,expected", [case[1:] for case in _BARE_JSON_CASES],
                         ids=[case[0] for case in _BARE_JSON_CASES])
def test_extractor_finds_valid_unfenced_json_regardless_of_braces_in_strings_or_prose(tmp_path, build, expected):
    runner = _make_runner(tmp_path, state=_stage_2_state())
    want = expected()

    got = runner._extract_json_from_response(build(want))

    assert got == want


@pytest.mark.parametrize("data,response", [
    (_bare_with_braces_in_strings(), _bare(_bare_with_braces_in_strings())),
    (_matrix_data(), "好的，下面是矩阵（注意：{ 表示开始）：\n" + _bare(_matrix_data(), indent=None)),
], ids=["braces_in_string_values", "lone_brace_in_prose"])
def test_run_stage_2_accepts_valid_unfenced_q1_json_with_braces(tmp_path, data, response):
    """json_only 提示词要求直接输出 JSON，不加代码围栏：这条主路径不能因花括号被误判为「被截断」。

    要断言保存的内容就是模型给的那份：只看角色键，全「否」的降级矩阵同样满足（旧代码正是如此通过）。
    """
    runner, calls = _stage_2_runner(tmp_path, [response])

    ok = runner.run_stage_2()

    assert ok is True
    assert calls["q1"] == 1
    assert "没有可解析的 JSON" not in _squashed(_flat_output(runner))
    loaded = TruthFileManager(runner.session.project_path).load_matrix()
    assert loaded is not None and set(loaded.characters) == {"R1", "R2"}
    for cid, entry in data["characters"].items():
        for eid, cell in entry["event_cognitions"].items():
            saved = loaded.characters[cid].event_cognitions[eid]
            assert (saved.state, saved.detail, saved.evidence_refs) == (
                cell["state"], cell["detail"], cell["evidence_refs"]
            ), f"{cid}/{eid} 与模型给出的认知不一致"
    assert len(loaded.evidence) == len(data["evidence"]) == 3
    for key, item in data["evidence"].items():
        assert loaded.evidence[key].description == item["description"]
    assert any(
        cell.state != "否" for entry in loaded.characters.values() for cell in entry.event_cognitions.values()
    )
    if "用 }" in response:
        assert loaded.characters["R1"].event_cognitions["E1"].detail == "他在门口说：用 } 表示未知，用 { 表示开始"
    assert runner.session.load().current_stage == Stage.STAGE_2_SCRIPT


def test_extractor_takes_a_complete_object_but_stays_fail_closed_and_cheap_on_anything_else(tmp_path):
    """换成 raw_decode 后：完整对象（哪怕字符串里有花括号）能取出；不完整/不是矩阵的输入仍返回 None，且不退化成二次方耗时。"""
    import time

    runner = _make_runner(tmp_path, state=_stage_2_state())
    data = _bare_with_braces_in_strings()
    full = _bare(data)
    assert runner._extract_json_from_response(full) == data

    not_a_complete_matrix = [
        "",
        "# 信息矩阵\n\n| | R1 | R2 |\n|---|---|---|\n| E1 | 知 | 疑 |\n",
        full[: len(full) // 2],
        full[:-1],  # 只差最后一个 }
        '{"note": "只有一个不含 characters 的对象"}',
        '说明文字 { 没有闭合 "characters"',
    ]
    for text in not_a_complete_matrix:
        assert runner._extract_json_from_response(text) is None, text[:60]

    started = time.monotonic()
    assert runner._extract_json_from_response('{"a":' * 20000) is None
    assert runner._extract_json_from_response('{"' * 50000) is None
    assert time.monotonic() - started < 1.0


@pytest.mark.parametrize("points_to", ["R1是凶手", "R1、R2", "排除外人作案"], ids=["with_id", "two_ids", "conclusion"])
def test_run_stage_2_accepts_free_text_points_to(tmp_path, points_to):
    """schema 里 points_to 是「凶手ID或其他结论」：不能被收窄成只能填已知 ID。"""
    data = _matrix_data()
    data["evidence"]["EV-A"]["points_to"] = points_to
    runner, calls = _stage_2_runner(tmp_path, [_fenced(data)])

    assert runner.run_stage_2() is True

    loaded = TruthFileManager(runner.session.project_path).load_matrix()
    assert loaded.evidence["EV-A"].points_to == points_to
    assert runner.session.load().current_stage == Stage.STAGE_2_SCRIPT


# Q2-Q6：（步骤名, 控制台里的步骤标签, 缓存 operation, 本步标题, 本步产物）
_STAGE_2_STEPS = [
    ("Q2", "Q2（角色背景）", "stage_2_background", _STAGE_2_HEADINGS[1], "background.md"),
    ("Q3", "Q3（a本）", "stage_2_characters", _STAGE_2_HEADINGS[2], "characters.md"),
    ("Q4", "Q4（b本）", "stage_2_clue_cards", _STAGE_2_HEADINGS[3], "scripts_b.md"),
    ("Q5", "Q5（DM 手册）", "stage_2_dm_manual", _STAGE_2_HEADINGS[4], "dm_manual.md"),
    ("Q6", "Q6（结局扩展）", "stage_2_endings", _STAGE_2_HEADINGS[5], "endings.md"),
]


def _blank_then_good_llm(runner, heading: str, blank: str) -> dict:
    """Q1 返回合法矩阵；本步第一次返回空白，之后返回正常内容；其余步骤返回占位内容。"""
    runner.llm.model = "mock-model"
    seen = {"target": 0}

    def complete(prompt, system="", max_tokens=None):
        if _Q1_HEADING in prompt:
            return _response(_VALID_JSON_TEXT)
        if heading in prompt:
            seen["target"] += 1
            return _response(blank if seen["target"] == 1 else "# 重新生成的内容")
        return _response("# 其他步骤内容")

    runner.llm.complete.side_effect = complete
    return seen


@pytest.mark.parametrize(
    "blank",
    ["", "  \n\t ", None, "\u200b\u200b", "\ufeff\u2060 \n"],
    ids=["empty", "whitespace_only", "null", "zero_width_only", "bom_and_word_joiner_only"],
)
@pytest.mark.parametrize("step,label,operation,heading,artifact", _STAGE_2_STEPS,
                         ids=[case[0] for case in _STAGE_2_STEPS])
def test_blank_step_reply_fails_naming_the_step_and_retry_calls_the_model_again(
    tmp_path, step, label, operation, heading, artifact, blank
):
    """空回复要在本步就失败并逐出缓存；否则下一步的严格渲染把它当成缺输入，重试又重放同一个空回复。"""
    runner = _make_runner(tmp_path, state=_stage_2_state())
    project = runner.session.project_path
    (project / "mechanism.md").write_text("# 机制：三轮搜证", encoding="utf-8")
    seen = _blank_then_good_llm(runner, heading, blank)

    assert runner.run_stage_2() is False

    assert seen["target"] == 1
    output = _squashed(_flat_output(runner))
    assert _squashed(f"{label}失败") in output and "空内容" in output
    assert "缺少必填输入" not in output, "应在本步报告空回复，而不是等到下一步报缺输入"
    assert "阶段2全部完成" not in output
    assert not (project / artifact).exists(), "空回复不能写成产物文件"
    assert operation not in _cached_operations(project)
    assert runner.session.load().current_stage == Stage.STAGE_1_MECHANISM

    assert runner.run_stage_2() is True
    assert seen["target"] == 2, "重试没有重新调用模型：空回复被缓存重放了"
    assert f"缓存命中：{operation}" not in _flat_output(runner)
    assert (project / artifact).read_text(encoding="utf-8") == "# 重新生成的内容"
    assert runner.session.load().current_stage == Stage.STAGE_2_SCRIPT


@pytest.mark.parametrize("poison", ["", None, "\u200b\ufeff"], ids=["empty", "null", "zero_width_only"])
def test_blank_reply_already_poisoned_in_the_cache_is_evicted_and_the_next_run_recovers(tmp_path, poison):
    """旧版本留下的坏缓存（Q2 空回复或 null 回复）：本次失败并逐出，下一次重新调用模型，不需要手动清缓存。"""
    runner = _make_runner(tmp_path, state=_stage_2_state())
    project = runner.session.project_path
    (project / "mechanism.md").write_text("# 机制：三轮搜证", encoding="utf-8")
    seen = _blank_then_good_llm(runner, _STAGE_2_HEADINGS[1], "# 重新生成的内容")  # 模型第一次被问到时就给正常内容
    bg_prompt = runner._build_background_prompt("# 简报\n民国戏班旧案", _published_matrix_md())
    bg_system = runner._loader.system_script_writer("mechanic")
    runner._cache.set("stage_2_background", bg_prompt, bg_system, "mock-model", _response(poison), max_tokens=LONG_OUTPUT_MAX_TOKENS)

    assert runner.run_stage_2() is False
    assert seen["target"] == 0, "第一次命中的是缓存里的空回复"
    assert "stage_2_background" not in _cached_operations(project)

    assert runner.run_stage_2() is True
    assert seen["target"] == 1
    assert (project / "background.md").read_text(encoding="utf-8") == "# 重新生成的内容"


# ─── 批次 A 审查修复（第二轮）：多份矩阵 / 照抄示例 / null 回复 ──────────────────────────


def _renamed(name: str) -> dict:
    data = _matrix_data()
    data["characters"]["R1"]["name"] = name
    return data


# (id, 构造回复)：回复里含有不止一份带 characters 的 JSON 对象——不论其中哪份合法、哪份先出现
_MULTI_MATRIX_REPLIES = [
    ("valid_a_then_valid_b",
     lambda: _fenced(_matrix_data()) + "\n\n修订后的版本：\n\n" + _fenced(_renamed("修订版林远"))),
    ("draft_b_then_final_a",
     lambda: "草稿：\n" + _fenced(_renamed("草稿林远")) + "\n\n最终版：\n" + _fenced(_matrix_data())),
    ("valid_a_then_invalid_all_no",
     lambda: _fenced(_matrix_data()) + "\n\n备选方案：\n" + _mutated(lambda d: _set_all_states(d, "否"))),
    ("prompt_example_quoted_before_the_answer",
     lambda: "提示词里的格式示例：\n" + _fenced(build_matrix_example(2, 3, True))
     + "\n\n我的答案：\n" + _fenced(_matrix_data())),
    ("invalid_snippet_then_valid_fence",
     lambda: _fenced({"characters": {}}) + "\n\n" + _fenced(_matrix_data())),
    ("bare_then_fenced",
     lambda: _bare(_matrix_data()) + "\n\n另一版：\n" + _fenced(_renamed("另一版林远"))),
]


@pytest.mark.parametrize("make_response", [case[1] for case in _MULTI_MATRIX_REPLIES],
                         ids=[case[0] for case in _MULTI_MATRIX_REPLIES])
def test_run_stage_2_rejects_a_reply_with_more_than_one_matrix(tmp_path, make_response):
    """只校验了其中一份，另一份就会原样混进 information_matrix.md 和 Q2-Q6 的输入：整个回复一并拒绝。"""
    runner, calls = _stage_2_runner(tmp_path, [make_response(), _VALID_JSON_TEXT])
    project = runner.session.project_path
    _seed_previous_matrix(runner)
    before = _snapshot(runner)

    assert runner.run_stage_2() is False

    assert calls["q1"] == 1 and calls["other"] == 0, "不得把任何一份矩阵交给 Q2-Q6"
    assert _snapshot(runner) == before
    assert runner.session.load().current_stage == Stage.STAGE_1_MECHANISM
    output = _squashed(_flat_output(runner))
    assert "Q1失败" in output and _squashed("含有 2 份") in output and "阶段2全部完成" not in output
    assert "stage_2_matrix" not in _cached_operations(project)

    # 重试必须重新调用模型；这一次回复只有一份矩阵，发布的就是它
    assert runner.run_stage_2() is True
    assert calls["q1"] == 2, "重试没有重新调用模型：含多份矩阵的回复被缓存重放了"
    assert (project / "information_matrix.md").read_text(encoding="utf-8") == _published_matrix_md()
    assert runner.session.load().current_stage == Stage.STAGE_2_SCRIPT


def test_extractor_counts_a_fenced_matrix_once_and_ignores_objects_without_characters(tmp_path):
    runner = _make_runner(tmp_path, state=_stage_2_state())
    data = _matrix_data()

    # 围栏里的矩阵既是围栏也是裸 JSON：只算一份
    assert runner._extract_json_from_response(_fenced(data)) == data
    # 不含 characters 的对象不算矩阵，不构成歧义
    decoys = '{"note": "说明"}\n' + _fenced(data) + '\n{"other": {"x": 1}}'
    assert runner._extract_json_from_response(decoys) == data
    # 三份就是三份
    with pytest.raises(MatrixContractError) as many:
        runner._extract_json_from_response(_fenced(data) + _bare(data) + _fenced(_renamed("甲")))
    assert "含有 3 份" in many.value.problems[0]


@pytest.mark.parametrize("content", [None, 123, ["x"]], ids=["none", "int", "list"])
def test_extractor_treats_non_text_content_as_no_json(tmp_path, content):
    runner = _make_runner(tmp_path, state=_stage_2_state())

    assert runner._extract_json_from_response(content) is None


# ─── 照抄 Q1 提示词里的示例 ───────────────────────────────────────────────────────


def _echo_with(mutate) -> str:
    """作者写的矩阵，再用 mutate 把一部分文字换回示例里的占位文字。"""
    data = _matrix_data()
    mutate(data, build_matrix_example(2, 3, True))
    return _fenced(data)


_ECHO_REPLIES = [
    ("verbatim_example", lambda: _fenced(build_matrix_example(2, 3, True)), "21 处"),
    ("verbatim_example_unfenced", lambda: _bare(build_matrix_example(2, 3, True)), "21 处"),
    ("only_one_name_left_as_example",
     lambda: _echo_with(lambda d, ex: d["characters"]["R2"].update(name=ex["characters"]["R2"]["name"])),
     "1 处"),
    ("only_one_evidence_text_left_as_example",
     lambda: _echo_with(lambda d, ex: d["evidence"]["EV-B"].update(description=ex["evidence"]["EV-B"]["description"])),
     "1 处"),
    ("only_one_cell_detail_left_as_example",
     lambda: _echo_with(lambda d, ex: d["characters"]["R1"]["event_cognitions"]["E3"].update(
         detail=ex["characters"]["R1"]["event_cognitions"]["E3"]["detail"])),
     "1 处"),
    # 占位文字藏在列表字段里（can_say 是 list[str]，会被保存）
    ("placeholder_left_inside_a_list_field",
     lambda: _echo_with(lambda d, ex: d["characters"]["R1"].update(
         can_say=["开场可以说的真话", ex["characters"]["R1"]["role"]])),
     "1 处"),
]


@pytest.mark.parametrize("make_response,hits", [case[1:] for case in _ECHO_REPLIES],
                         ids=[case[0] for case in _ECHO_REPLIES])
def test_run_stage_2_rejects_a_reply_that_echoes_the_prompt_example(tmp_path, make_response, hits):
    """示例本身通过了矩阵契约（契约只管结构），所以照抄它的回复靠占位标记拦下，不能当成阶段 2 成功。"""
    runner, calls = _stage_2_runner(tmp_path, [make_response(), _VALID_JSON_TEXT])
    project = runner.session.project_path
    before = _snapshot(runner)

    assert runner.run_stage_2() is False

    assert calls["q1"] == 1 and calls["other"] == 0
    assert _snapshot(runner) == before
    assert not (project / "state").exists() and not (project / "information_matrix.md").exists()
    assert runner.session.load().current_stage == Stage.STAGE_1_MECHANISM
    output = _squashed(_flat_output(runner))
    assert "Q1失败" in output and "照抄了提示词里的格式示例" in output
    assert _squashed(f"{hits}文字仍含占位标记「{EXAMPLE_PLACEHOLDER_MARK}」") in output
    assert "阶段2全部完成" not in output
    assert "stage_2_matrix" not in _cached_operations(project)

    # 重试：重新调用模型，保存的是作者写的内容，不含任何占位文字
    assert runner.run_stage_2() is True
    assert calls["q1"] == 2, "重试没有重新调用模型：照抄示例的回复被缓存重放了"
    saved = (project / "state" / "character_matrix.json").read_text(encoding="utf-8")
    assert EXAMPLE_PLACEHOLDER_MARK not in saved
    assert EXAMPLE_PLACEHOLDER_MARK not in (project / "information_matrix.md").read_text(encoding="utf-8")


def test_every_free_text_field_of_the_q1_example_carries_the_placeholder_mark():
    """照抄靠标记识别：示例里新增或改动的自由文本字段若漏了标记，就会绕过照抄检查。"""
    example = build_matrix_example(2, 3, True)
    texts = []
    for entry in example["characters"].values():
        texts += [entry["name"], entry["role"], entry["public_relationship"]]
        texts += [cell["detail"] for cell in entry["event_cognitions"].values()]
    for item in example["evidence"].values():
        texts += [item["name"], item["description"], item["chain_role"]]

    assert len(texts) == 2 * 3 + 2 * 3 + 3 * 3
    assert all(EXAMPLE_PLACEHOLDER_MARK in text for text in texts)
    # 示例通过契约（有意为之），所以不能指望校验器拦下它
    validate_generated_matrix(example, 2, 3, True)
    assert PhaseRunner._example_echo_problems(example)
    assert PhaseRunner._example_echo_problems(_matrix_data()) == []


# ─── Q1 的 null 回复 ─────────────────────────────────────────────────────────────


def test_null_q1_reply_is_rejected_as_having_no_json_and_retry_calls_the_model_again(tmp_path):
    runner, calls = _stage_2_runner(tmp_path, [None, _VALID_JSON_TEXT])
    project = runner.session.project_path
    before = _snapshot(runner)

    assert runner.run_stage_2() is False

    assert calls["q1"] == 1 and calls["other"] == 0
    assert _snapshot(runner) == before
    output = _squashed(_flat_output(runner))
    assert "没有可解析的JSON" in output
    assert "意外错误" not in output, "null 回复是被拒绝的输入，不是程序异常"
    assert "stage_2_matrix" not in _cached_operations(project)

    assert runner.run_stage_2() is True
    assert calls["q1"] == 2
    assert (project / "state" / "character_matrix.json").exists()


def test_q1_prompt_tells_the_model_to_give_one_matrix_and_no_placeholder_text(tmp_path):
    """回复含多份矩阵或占位文字会被整个拒绝：提示词必须事先说清楚，而不是让模型靠运气避开。"""
    runner = _make_runner(tmp_path, state=_stage_2_state())

    requirements = runner._build_matrix_prompt("简报", "机制").split("JSON 硬性要求")[1]

    assert "只给出**一份**最终的 JSON 矩阵" in requirements
    assert f"不要保留示例里的「{EXAMPLE_PLACEHOLDER_MARK}」占位文字" in requirements


# ─── 批次 A 审查修复（第三轮）：孤立代理项 / 渲染失败 / 照抄示例的写法变体 / 步骤提示词守卫 ──────


def _extra_role_key_with_surrogate(data: dict) -> None:
    data["characters"]["R3SURROGATE"] = copy.deepcopy(data["characters"]["R1"])


# (id, 构造回复, 控制台里必须出现的位置)——每个位置都是校验后会被保存的字段
_SURROGATE_REPLIES = [
    ("character_name",
     lambda: _surrogate_escape_reply(lambda d: d["characters"]["R1"].update(name="林SURROGATE")),
     "characters.R1.name"),
    ("cell_detail",
     lambda: _surrogate_escape_reply(lambda d: d["characters"]["R2"]["event_cognitions"]["E2"].update(
         detail="发现SURROGATE")),
     "characters.R2.event_cognitions.E2.detail"),
    ("evidence_description",
     lambda: _surrogate_escape_reply(lambda d: d["evidence"]["EV-A"].update(description="钥匙SURROGATE")),
     "evidence.EV-A.description"),
]


@pytest.mark.parametrize("make_response,where", [case[1:] for case in _SURROGATE_REPLIES],
                         ids=[case[0] for case in _SURROGATE_REPLIES])
def test_run_stage_2_lone_surrogate_reply_is_rejected_cleanly_and_not_replayed(tmp_path, capsys, make_response, where):
    """孤立代理项能通过 json.loads 和全部结构检查，却无法序列化/写文件：必须在校验里指明位置并拒绝，
    而不是发布时才崩溃——崩溃时被拒绝的回复仍留在缓存里，重试永远重放它。"""
    runner, calls = _stage_2_runner(tmp_path, [make_response(), _VALID_JSON_TEXT])
    project = runner.session.project_path
    _seed_previous_matrix(runner)
    before = _snapshot(runner)

    assert runner.run_stage_2() is False

    assert calls["q1"] == 1 and calls["other"] == 0
    assert _snapshot(runner) == before
    assert runner.session.load().current_stage == Stage.STAGE_1_MECHANISM
    output = _flat_output(runner)
    assert "无法保存的字符" in _squashed(output) and _squashed(where) in _squashed(output)
    assert "意外错误" not in output, "这是被拒绝的回复，不是程序异常"
    assert "Traceback" not in capsys.readouterr().err
    output.encode("utf-8")  # 报告本身不能带着无法编码的字符
    assert "stage_2_matrix" not in _cached_operations(project)

    assert runner.run_stage_2() is True
    assert calls["q1"] == 2, "重试没有重新调用模型：带孤立代理项的回复被缓存重放了"
    assert "缓存命中：stage_2_matrix" not in _flat_output(runner)
    assert (project / "information_matrix.md").read_text(encoding="utf-8") == _published_matrix_md()


def test_run_stage_2_problem_text_with_a_lone_surrogate_key_is_printable_and_still_evicts(tmp_path, capsys):
    """问题文字会嵌入模型给的键名：键里的孤立代理项若原样打印，报告失败的那次打印就抛异常，
    后面的缓存逐出被跳过——和渲染失败一样，重试永远重放同一个坏回复。"""
    reply = _surrogate_escape_reply(_extra_role_key_with_surrogate)
    runner, calls = _stage_2_runner(tmp_path, [reply, _VALID_JSON_TEXT])
    project = runner.session.project_path
    before = _snapshot(runner)

    assert runner.run_stage_2() is False

    assert calls["q1"] == 1 and calls["other"] == 0
    assert _snapshot(runner) == before
    output = _flat_output(runner)
    assert "多余角色" in output and "R3\\ud800" in output  # 键里的孤立代理项以转义文字出现，不是原字符
    assert "Traceback" not in capsys.readouterr().err
    output.encode("utf-8")
    assert "stage_2_matrix" not in _cached_operations(project)

    assert runner.run_stage_2() is True
    assert calls["q1"] == 2


def test_render_failure_after_validation_evicts_the_cached_response_and_writes_nothing(tmp_path):
    """渲染在写文件之前、在保护块之内：校验通过却无法发布的回复同样被拒绝——不写任何文件、逐出缓存。"""
    runner, calls = _stage_2_runner(tmp_path, [_VALID_JSON_TEXT, _VALID_JSON_TEXT])
    project = runner.session.project_path
    _seed_previous_matrix(runner)
    before = _snapshot(runner)

    with patch.object(PhaseRunner, "_render_matrix_markdown", side_effect=RuntimeError("render bug")):
        ok = runner.run_stage_2()

    assert ok is False
    assert calls["q1"] == 1 and calls["other"] == 0
    assert _snapshot(runner) == before, "渲染失败时 information_matrix.md 与 character_matrix.json 都不能被改写"
    assert "stage_2_matrix" not in _cached_operations(project)
    assert LLMCache(project).stats()["entries"] == 0
    assert runner.session.load().current_stage == Stage.STAGE_1_MECHANISM
    output = _squashed(_flat_output(runner))
    assert "Q1失败" in output and "RuntimeError" in output and "阶段2全部完成" not in output

    assert runner.run_stage_2() is True
    assert calls["q1"] == 2, "重试没有重新调用模型：校验通过却无法渲染的回复被缓存重放了"
    assert (project / "information_matrix.md").read_text(encoding="utf-8") == _published_matrix_md()


# 占位标记的写法变体：模型改了标点、全半角或空白，示例仍是照抄的
_MARK_VARIANTS = [
    ("ascii_parens", "(示例)"),
    ("spaced_fullwidth_parens", "（ 示例 ）"),
    ("missing_closing_paren", "（示例"),
    ("fullwidth_square_brackets", "［示例］"),
    ("ascii_square_brackets", "[示例]"),
    ("lenticular_brackets", "【示例】"),
    ("space_inside_the_word", "（示 例）"),
    ("zero_width_inside_the_word", "（示​例）"),
]
# 只改标记、没有重新创作的其它形态
_MARK_REMOVED_VARIANTS = [
    ("mark_deleted", ""),
    ("mark_left_as_bare_word", "示例"),
]


def _example_reply_with_mark(mark: str) -> str:
    text = json.dumps(build_matrix_example(2, 3, True), ensure_ascii=False, indent=2)
    return "```json\n" + text.replace(EXAMPLE_PLACEHOLDER_MARK, mark) + "\n```"


@pytest.mark.parametrize("mark", [case[1] for case in _MARK_VARIANTS + _MARK_REMOVED_VARIANTS],
                         ids=[case[0] for case in _MARK_VARIANTS + _MARK_REMOVED_VARIANTS])
def test_run_stage_2_rejects_an_example_copy_whatever_the_mark_looks_like(tmp_path, mark):
    """照抄检查不能只认字面完全相同的「（示例）」：改标点/全半角/空白，或只删标记，都是照抄。"""
    runner, calls = _stage_2_runner(tmp_path, [_example_reply_with_mark(mark), _VALID_JSON_TEXT])
    project = runner.session.project_path
    before = _snapshot(runner)

    assert runner.run_stage_2() is False

    assert calls["q1"] == 1 and calls["other"] == 0
    assert _snapshot(runner) == before
    assert not (project / "state").exists() and not (project / "information_matrix.md").exists()
    output = _squashed(_flat_output(runner))
    assert "Q1失败" in output and "照抄了提示词里的格式示例" in output
    assert _squashed(f"21 处文字仍含占位标记「{EXAMPLE_PLACEHOLDER_MARK}」") in output
    assert "阶段2全部完成" not in output
    assert "stage_2_matrix" not in _cached_operations(project)

    assert runner.run_stage_2() is True
    assert calls["q1"] == 2, "重试没有重新调用模型：照抄示例的回复被缓存重放了"
    assert "·作者稿" in (project / "state" / "character_matrix.json").read_text(encoding="utf-8")


def test_example_echo_check_flags_only_whole_placeholder_texts_not_story_text(tmp_path):
    data = _matrix_data()
    data["characters"]["R1"]["event_cognitions"]["E1"]["detail"] = "他当众示例了开锁手法，并说「证据描述」不全"
    data["characters"]["R2"]["role"] = "社会身份复杂的戏班账房"
    data["evidence"]["EV-A"]["description"] = "证据描述了一把只有管家持有的钥匙"
    assert PhaseRunner._example_echo_problems(data) == []

    data["characters"]["R2"]["role"] = "社会身份"  # 整句就是示例里的占位文字
    problems = PhaseRunner._example_echo_problems(data)
    assert len(problems) == 1 and "1 处" in problems[0] and "characters.R2.role" in problems[0]


# ─── 步骤提示词的守卫：残留变量、JSON-only 变体、PromptRenderError 分支 ──────────────────────────


def test_matrix_prompt_is_the_json_only_variant(tmp_path):
    """阶段 2 的 Q1 要的是只含 JSON 的输出：Markdown 变体（附加证据链设计、先 Markdown 后 JSON）不能混进来。"""
    runner = _make_runner(tmp_path, state=_stage_2_state())

    prompt = runner._build_matrix_prompt("简报", "机制")

    assert "请直接输出 JSON 格式" in prompt
    assert "附加：证据链设计" not in prompt
    assert "请在 Markdown 输出之后" not in prompt


def test_run_stage_2_residual_template_variable_fails_cleanly_before_calling_the_model(tmp_path, capsys):
    """模板里有无法解析的变量：调用模型前失败，只报明确的一句话，不当成程序异常打印堆栈。"""
    runner = _make_runner(tmp_path, state=_stage_2_state())
    project = runner.session.project_path
    (project / "mechanism.md").write_text("# 机制：三轮搜证", encoding="utf-8")
    real_load = runner._loader._load_raw
    runner._loader._load_raw = lambda filename: real_load(filename) + "\n{{unknown_thing}}\n"
    runner._call_llm = MagicMock(return_value=_response("不应被调用"))
    before = _snapshot(runner)

    assert runner.run_stage_2() is False

    runner._call_llm.assert_not_called()
    output = _squashed(_flat_output(runner))
    assert "阶段2失败" in output and "unknown_thing" in output and "未调用模型" in output
    assert "Traceback" not in capsys.readouterr().err
    assert _snapshot(runner) == before
    assert runner.session.load().current_stage == Stage.STAGE_1_MECHANISM


# ─── 批次 A 复审修复：JSON 提取有上限 / 不采用模型的 version / 写盘失败不留坏缓存 / 其余守卫 ─────────────────


def test_extractor_gives_up_fast_on_degenerate_input_instead_of_going_quadratic(tmp_path):
    """反复的 {"a": 之类的退化输入：每个失败起点都白扫一遍后文，耗时随长度二次方增长
    （修复前 100 KB 约 11 秒、200 KB 约 46 秒）。现在放弃并失败关闭，不再卡住整个阶段。"""
    import time

    runner = _make_runner(tmp_path, state=_stage_2_state())
    data = _matrix_data()
    degenerate = {
        "nested_open_then_marker": '{"a":' * 40000 + '"characters"',
        "nested_open_then_valid_matrix": '{"a":' * 40000 + _fenced(data),
        "nested_arrays_then_marker": '{"a":{"b":[' * 20000 + '"characters"',
        "flat_broken_then_valid_matrix": '{"a" 1}' * 30000 + _bare(data),
        "characters_key_repeated": '{"characters":' * 15000,
    }

    for name, text in degenerate.items():
        assert len(text) >= 200_000, name
        started = time.monotonic()
        got = runner._extract_json_from_response(text)
        elapsed = time.monotonic() - started

        assert elapsed < 2.0, f"{name}：提取耗时 {elapsed:.1f}s，退化输入没有被限制"
        assert got is None or got == data, f"{name}：只能失败关闭，或找到那份唯一合法的矩阵"


def test_extractor_still_finds_a_valid_matrix_after_long_prose_a_fence_or_a_broken_draft(tmp_path):
    runner = _make_runner(tmp_path, state=_stage_2_state())
    data = _matrix_data()
    prose = '先说两句。{ 这里有个花括号 {"x" 1} 还有 {"a": 1} 。' * 600
    assert len(prose) >= 20_000  # 其中 600 处写坏的 {"x" 1}：每处都是一次失败的起点

    assert runner._extract_json_from_response(prose + _fenced(data)) == data
    assert runner._extract_json_from_response("```text\n" + prose + "\n```\n\n" + _bare(data)) == data
    assert runner._extract_json_from_response("说明文字。" * 4000 + _fenced(data)) == data  # 20 KB 不含花括号的说明
    # 被截断的草稿在前、完整的最终版在后：草稿不算一份矩阵，最终版照常找到
    full = _matrix_data(is_prototype=False)
    text = _bare(full)
    assert runner._extract_json_from_response(text[: len(text) // 2] + "\n\n最终版：\n" + text) == full


def test_extractor_skips_the_whole_decoded_object_so_a_nested_characters_key_is_not_a_second_matrix(tmp_path):
    runner = _make_runner(tmp_path, state=_stage_2_state())
    data = _matrix_data()
    data["notes"] = {"characters": {"R1": "备注里也有一个 characters 键"}}

    # 矩阵里嵌着另一个含 characters 的对象：整个对象解析完就跳过，只算外层这一份（否则会误报「含有 2 份」）
    assert runner._extract_json_from_response(_bare(data)) == data
    # 只提取顶层对象：被包在别的对象里的矩阵不算（不会从包装里把它抠出来再去校验）
    assert runner._extract_json_from_response(_bare({"result": _matrix_data()})) is None


def test_example_echo_check_also_looks_inside_lists_and_reports_the_path(tmp_path):
    example = build_matrix_example(2, 3, True)
    placeholder = example["characters"]["R1"]["role"]
    data = _matrix_data()
    assert PhaseRunner._example_echo_problems(data) == []

    data["characters"]["R1"]["can_say"] = ["开场可以说的真话", placeholder]
    data["extra"] = [{"nested": ["正常文字", placeholder]}]
    problems = PhaseRunner._example_echo_problems(data)

    assert len(problems) == 1 and "2 处" in problems[0]
    assert "characters.R1.can_say[1]" in problems[0] and "extra[0].nested[1]" in problems[0]


def test_model_supplied_version_is_not_published(tmp_path):
    data = _matrix_data()
    data["version"] = "banana"
    runner, calls = _stage_2_runner(tmp_path, [_fenced(data)])
    project = runner.session.project_path

    assert runner.run_stage_2() is True

    default = CharacterMatrix.model_fields["version"].default
    saved = json.loads((project / "state" / "character_matrix.json").read_text(encoding="utf-8"))
    assert saved["version"] == default
    published = (project / "information_matrix.md").read_text(encoding="utf-8")
    assert "banana" not in published and f'"version": "{default}"' in published
    assert published == _published_matrix_md()


def test_reply_that_cannot_be_cached_is_not_replayed_and_does_not_poison_the_next_calls(tmp_path, capsys):
    """回复里有真正的孤立代理项：写缓存失败。内存里不能留下这条回复——否则重试直接命中它（模型不再被调用），
    而且之后每一次写缓存都会失败。"""
    bad = _fenced(_matrix_data()) + "\n尾巴\ud800"  # 矩阵本身合法，孤立代理项在围栏之外
    runner, calls = _stage_2_runner(tmp_path, [bad, _VALID_JSON_TEXT])
    project = runner.session.project_path

    assert runner.run_stage_2() is False
    capsys.readouterr()  # 丢弃失败时打印的堆栈

    assert calls["q1"] == 1 and calls["other"] == 0
    assert runner._cache.stats()["entries"] == 0
    assert not (project / "cache.json.tmp").exists()

    assert runner.run_stage_2() is True  # 同一个 runner 上直接重试
    assert calls["q1"] == 2, "重试没有重新调用模型：写盘失败的回复留在内存缓存里被重放了"
    assert "缓存命中：stage_2_matrix" not in _flat_output(runner)
    assert (project / "information_matrix.md").read_text(encoding="utf-8") == _published_matrix_md()
    assert runner.session.load().current_stage == Stage.STAGE_2_SCRIPT


def test_matrix_write_failing_midway_keeps_the_previous_matrix_and_a_retry_recovers(tmp_path, disk_full, capsys):
    """发布矩阵时磁盘写到一半失败：旧矩阵必须原样可读（原来是被截断的半个 JSON），重试成功后旧版仍有完好的备份。"""
    runner, calls = _stage_2_runner(tmp_path, [_VALID_JSON_TEXT, _VALID_JSON_TEXT])
    _seed_previous_matrix(runner)
    project = runner.session.project_path
    live = project / "state" / "character_matrix.json"
    old_bytes = live.read_bytes()
    old_md = (project / "information_matrix.md").read_bytes()

    with disk_full(lambda path: path.parent == project / "state"):
        assert runner.run_stage_2() is False
    capsys.readouterr()

    assert live.read_bytes() == old_bytes, "写到一半失败后旧矩阵被截断/改写了"
    assert TruthFileManager(project).load_matrix().characters["R1"].name == "旧版林远"
    assert (project / "information_matrix.md").read_bytes() == old_md
    assert runner.session.load().current_stage == Stage.STAGE_1_MECHANISM
    assert "阶段2全部完成" not in _flat_output(runner)

    assert runner.run_stage_2() is True  # 磁盘恢复后重试
    assert TruthFileManager(project).load_matrix().characters["R1"].name != "旧版林远"
    backups = list((project / "state" / ".backups").glob("character_matrix.*.json"))
    assert any(backup.read_bytes() == old_bytes for backup in backups), "旧版的完好备份被覆盖了"
    for backup in backups:
        json.loads(backup.read_text(encoding="utf-8"))  # 没有任何一份备份是坏的


@pytest.mark.parametrize("which", ["outline", "mechanism"])
def test_run_stage_2_input_made_only_of_invisible_characters_fails_before_calling_the_model(tmp_path, which):
    """零宽空格/BOM 之类的格式字符 str.strip() 去不掉：只含它们的简报或机制设计就是空的，调用模型之前就失败。"""
    invisible = "​﻿⁠"
    runner = _make_runner(tmp_path, state=_stage_2_state(outline=invisible if which == "outline" else "# 简报"))
    (runner.session.project_path / "mechanism.md").write_text(
        invisible if which == "mechanism" else "# 机制：三轮搜证", encoding="utf-8"
    )
    runner._call_llm = MagicMock(return_value=_response("不应被调用"))

    assert runner.run_stage_2() is False

    runner._call_llm.assert_not_called()
    output = _flat_output(runner)
    assert ("brief_content" if which == "outline" else "mechanism_content") in output
    assert "未调用模型" in output
    assert not (runner.session.project_path / "information_matrix.md").exists()
