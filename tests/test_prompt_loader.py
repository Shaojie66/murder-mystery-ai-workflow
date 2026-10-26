"""Tests for murder_wizard.prompts.loader."""
import json
import re

import pytest
from murder_wizard.prompts.loader import PromptLoader, PromptRenderError
from murder_wizard.wizard.schemas import CharacterMatrix


class TestPromptLoader:
    """PromptLoader tests."""

    def test_load_raw_caches(self):
        loader = PromptLoader()
        content1 = loader._load_raw("00_guided_questionnaire.md")
        content2 = loader._load_raw("00_guided_questionnaire.md")
        assert content1 is content2  # same object due to caching

    def test_load_raw_unknown_file_raises(self):
        loader = PromptLoader()
        with pytest.raises(FileNotFoundError):
            loader._load_raw("nonexistent.md")

    def test_render_substitutes_variables(self):
        loader = PromptLoader()
        # Use a template with known variable
        prompt = loader.information_matrix(
            brief_content="测试大纲内容",
            mechanism_content="测试机制内容",
            story_type="推理本",
            is_prototype=True,
        )
        assert "测试大纲内容" in prompt
        assert "测试机制内容" in prompt
        assert "请为2位角色" in prompt
        assert "E1-E3" in prompt  # prototype: 3 events

    def test_render_is_prototype_false(self):
        loader = PromptLoader()
        prompt = loader.information_matrix(
            brief_content="b",
            mechanism_content="m",
            story_type="s",
            is_prototype=False,
        )
        assert "请为6位角色" in prompt
        assert "E1-E7" in prompt  # full: 7 events

    def test_mechanism_design_q2_has_variables(self):
        loader = PromptLoader()
        prompt = loader.mechanism_design(
            brief_content="brief",
            story_type="mechanic",
            is_prototype=True,
            q1_result="评分8分",
            mechanism_content="mech",
        )
        assert "brief" in prompt
        assert "评分8分" in prompt

    def test_prepare_vars_adds_derived(self):
        loader = PromptLoader()
        vars = loader._prepare_vars({"is_prototype": True})
        assert vars["mode_label"] == "原型模式"
        assert vars["char_count"] == 2
        assert vars["event_count"] == 3
        assert vars["word_count_a"] == "800-1200"

    def test_prepare_vars_full_mode(self):
        loader = PromptLoader()
        vars = loader._prepare_vars({"is_prototype": False})
        assert vars["mode_label"] == "完整模式"
        assert vars["char_count"] == 6
        assert vars["event_count"] == 7
        assert vars["word_count_a"] == "1500-2500"

    def test_prepare_vars_fill_rules_proto(self):
        loader = PromptLoader()
        vars = loader._prepare_vars({"is_prototype": True})
        assert "凶手必须拥有核心事件的关键碎片" in vars["fill_rules"]
        assert "2人拼图 = 完整真相" in vars["fill_rules"]

    def test_prepare_vars_fill_rules_full(self):
        loader = PromptLoader()
        vars = loader._prepare_vars({"is_prototype": False})
        assert "凶手（R1）必须拥有" in vars["fill_rules"]
        assert "至少2个角色对核心事件有[误信]" in vars["fill_rules"]

    def test_prepare_vars_matrix_table(self):
        loader = PromptLoader()
        # 2-player
        vars = loader._load_raw  # no, call _prepare_vars
        vars = loader._prepare_vars({"is_prototype": True, "char_count": 2, "event_count": 3})
        assert "R1" in vars["matrix_table"]
        assert "R2" in vars["matrix_table"]
        assert "E3" in vars["matrix_table"]
        assert vars["matrix_table"].count("|") > 5  # has table structure

    def test_consistency_round1(self):
        loader = PromptLoader()
        prompt = loader.consistency_round1(
            characters_content="角色剧本内容",
            matrix_content="信息矩阵内容",
            is_prototype=True,
        )
        assert "角色剧本内容" in prompt
        assert "信息矩阵内容" in prompt
        assert "第一轮" in prompt

    def test_consistency_round2(self):
        loader = PromptLoader()
        prompt = loader.consistency_round2(
            characters_content="c",
            matrix_content="m",
            mechanism_content="机制内容",
            is_prototype=False,
        )
        assert "机制内容" in prompt
        assert "第二轮" in prompt

    def test_consistency_round3(self):
        loader = PromptLoader()
        prompt = loader.consistency_round3(
            full_script="完整剧本",
            matrix_content="矩阵",
            mechanism_content="机制",
        )
        assert "完整剧本" in prompt
        assert "第三轮" in prompt

    def test_system_prompts_all_return_string(self):
        loader = PromptLoader()
        for name in [
            "system_mechanism_designer",
            "system_script_writer",
            "system_visual_designer",
            "system_auditor",
            "system_balance_analyst",
            "system_ending_auditor",
            "system_test_designer",
            "system_commercial_consultant",
            "system_promo_writer",
            "system_community_operations",
            "system_outline_generator",
        ]:
            method = getattr(loader, name)
            result = method()
            assert isinstance(result, str)
            assert len(result) > 10

    def test_system_mechanism_designer_type_specific(self):
        """Each story type gets a distinct system prompt."""
        loader = PromptLoader()
        types = ["emotion", "reasoning", "fun", "horror", "mechanic"]
        prompts = [loader.system_mechanism_designer(t) for t in types]
        # All should be strings
        assert all(isinstance(p, str) for p in prompts)
        # All should be distinct (different content per type)
        assert len(set(prompts)) == len(prompts), "Each story type should have a unique system prompt"
        # emotion type should mention emotion-specific keywords
        emotion_prompt = loader.system_mechanism_designer("emotion")
        assert "情感" in emotion_prompt
        # reasoning type should mention reasoning-specific keywords
        reasoning_prompt = loader.system_mechanism_designer("reasoning")
        assert "证据" in reasoning_prompt or "推理" in reasoning_prompt

    def test_system_script_writer_type_specific(self):
        """Each story type gets a distinct system prompt for script writing."""
        loader = PromptLoader()
        types = ["emotion", "reasoning", "fun", "horror", "mechanic"]
        prompts = [loader.system_script_writer(t) for t in types]
        assert all(isinstance(p, str) for p in prompts)
        assert len(set(prompts)) == len(prompts), "Each story type should have a unique script writer prompt"
        # emotion type should mention emotion-specific content
        emotion_prompt = loader.system_script_writer("emotion")
        assert "情感" in emotion_prompt
        # horror type should mention horror-specific content
        horror_prompt = loader.system_script_writer("horror")
        assert "恐怖" in horror_prompt or "恐惧" in horror_prompt

    def test_expand_system_prompts_match_type_specific_ones(self):
        """Expand operations should use the same type-specific prompts as PhaseRunner.

        Regression test: expand was previously using hardcoded generic strings instead
        of type-specific system_mechanism_designer and system_script_writer.
        """
        loader = PromptLoader()
        for story_type in ["emotion", "reasoning", "fun", "horror", "mechanic"]:
            # expand Phase 1 should use system_mechanism_designer
            expand_p1 = loader.system_mechanism_designer(story_type)
            # expand Phase 2 (character script) should use system_script_writer
            expand_p2 = loader.system_script_writer(story_type)
            assert isinstance(expand_p1, str), f"{story_type}: mechanism designer should return string"
            assert isinstance(expand_p2, str), f"{story_type}: script writer should return string"
            assert len(expand_p1) > 10
            assert len(expand_p2) > 10


# ─── R01：阶段 2 分步骤模板 + 严格渲染 ───────────────────────────────────────

# (loader 方法, 模板文件, 本步标题, 本步必填输入)——必填输入取自模板的实际占位符
STAGE_2_STEPS = [
    ("information_matrix", "02_q1_matrix.md", "## Q1：信息矩阵生成", ("brief_content", "mechanism_content")),
    ("information_matrix_json", "02_q1_matrix.md", "## Q1：信息矩阵生成", ("brief_content", "mechanism_content")),
    ("character_background", "02_q2_background.md", "## Q2：角色背景生成", ("matrix_content", "brief_content")),
    ("character_script_a", "02_q3_script_a.md", "## Q3：a本（阅读本）生成",
     ("background_content", "matrix_content", "mechanism_content")),
    ("character_script_b", "02_q4_script_b.md", "## Q4：b本（线索本）生成",
     ("a_content", "matrix_content", "mechanism_content")),
    ("dm_manual", "02_q5_dm_manual.md", "## Q5：DM手册生成",
     ("full_script", "matrix_content", "mechanism_content")),
    ("ending_expansion", "02_q6_endings.md", "## Q6：结局扩展", ("full_script", "matrix_content", "dm_manual")),
]
ALL_STEP_HEADINGS = sorted({heading for _, _, heading, _ in STAGE_2_STEPS})

REALISTIC_INPUTS = {
    "brief_content": "简报：民国戏班里的一桩旧案",
    "mechanism_content": "机制：三轮搜证，公开投票",
    "matrix_content": "矩阵：R1 对 E1 为知，R2 对 E1 为误信",
    "background_content": "背景：班主任的长子多年前离开了戏班",
    "a_content": "a本：开场白，我是戏班的账房",
    "full_script": "完整剧本：a本与b本合并稿",
    "dm_manual": "DM手册：主持流程与真相手册",
}


def _inputs(required):
    return {name: REALISTIC_INPUTS[name] for name in required}


def _extract_json_example(prompt: str) -> dict:
    blocks = re.findall(r"```json\n(.*?)\n```", prompt, flags=re.DOTALL)
    assert len(blocks) == 1, f"prompt 中应恰有一个 JSON 示例，实际 {len(blocks)}"
    return json.loads(blocks[0])


class TestStage2StepIsolation:
    """每个阶段 2 步骤的 prompt 只含本步任务，且无残留占位符."""

    @pytest.mark.parametrize("is_prototype", [True, False])
    @pytest.mark.parametrize("method,template,heading,required", STAGE_2_STEPS)
    def test_prompt_contains_only_its_own_step(self, method, template, heading, required, is_prototype):
        prompt = getattr(PromptLoader(), method)(**_inputs(required), is_prototype=is_prototype)

        assert heading in prompt
        for other in ALL_STEP_HEADINGS:
            if other != heading:
                assert other not in prompt, f"{method} 的 prompt 混入了其他步骤：{other}"

    @pytest.mark.parametrize("is_prototype", [True, False])
    @pytest.mark.parametrize("method,template,heading,required", STAGE_2_STEPS)
    def test_no_unresolved_placeholders_with_realistic_inputs(self, method, template, heading, required, is_prototype):
        prompt = getattr(PromptLoader(), method)(**_inputs(required), is_prototype=is_prototype)

        assert re.findall(r"\{\{[^}]*\}\}", prompt) == []
        for value in _inputs(required).values():
            assert value in prompt

    @pytest.mark.parametrize("method,template,heading,required", STAGE_2_STEPS)
    def test_required_inputs_match_actual_template_placeholders(self, method, template, heading, required):
        loader = PromptLoader()
        derived = {"char_count", "event_count", "word_count_a", "fill_rules", "matrix_table", "matrix_json_example"}
        raw = loader._load_raw(template)
        names = set()
        for json_only in (True, False):
            resolved = loader._resolve_conditionals(raw, {"json_only": json_only})
            names |= {m.strip() for m in re.findall(r"\{\{([^}]+)\}\}", resolved)}

        assert names - derived == set(required)
        assert tuple(loader.STAGE_2_REQUIRED_INPUTS[method]) == tuple(required)
        assert loader.STAGE_2_TEMPLATES[method] == template

    def test_legacy_combined_template_kept_with_note(self):
        head = PromptLoader()._load_raw("02_script_generation.md")[:800]
        assert "02_q1_matrix.md" in head
        assert "不再加载" in head


class TestStage2StrictRendering:
    """缺失/为空的必填输入在调用模型前被拒绝."""

    @pytest.mark.parametrize("method,template,heading,required", STAGE_2_STEPS)
    def test_each_missing_input_is_reported(self, method, template, heading, required):
        for missing in required:
            inputs = _inputs(required)
            del inputs[missing]
            with pytest.raises(PromptRenderError) as exc_info:
                getattr(PromptLoader(), method)(**inputs, is_prototype=True)
            assert missing in exc_info.value.missing
            assert missing in str(exc_info.value)
            assert template in str(exc_info.value)

    @pytest.mark.parametrize("bad_value", ["", "   \n\t", None])
    @pytest.mark.parametrize("method,template,heading,required", STAGE_2_STEPS)
    def test_empty_blank_or_none_input_is_rejected(self, method, template, heading, required, bad_value):
        inputs = _inputs(required)
        inputs[required[0]] = bad_value
        with pytest.raises(PromptRenderError) as exc_info:
            getattr(PromptLoader(), method)(**inputs, is_prototype=False)
        assert required[0] in exc_info.value.missing

    def test_all_missing_inputs_listed_in_one_error(self):
        with pytest.raises(PromptRenderError) as exc_info:
            PromptLoader().character_script_a(is_prototype=True)
        message = str(exc_info.value)
        for name in ("background_content", "matrix_content", "mechanism_content"):
            assert name in message
            assert name in exc_info.value.missing

    @pytest.mark.parametrize("bad_value", [None, "true", 1])
    def test_is_prototype_must_be_a_bool(self, bad_value):
        with pytest.raises(PromptRenderError) as exc_info:
            PromptLoader().ending_expansion(
                **_inputs(("full_script", "matrix_content", "dm_manual")), is_prototype=bad_value
            )
        assert "is_prototype" in exc_info.value.missing

    def test_is_prototype_absent_does_not_fall_back_to_full_mode(self):
        with pytest.raises(PromptRenderError) as exc_info:
            PromptLoader().character_background(**_inputs(("matrix_content", "brief_content")))
        assert "is_prototype" in exc_info.value.missing

    def test_error_is_a_value_error(self):
        assert issubclass(PromptRenderError, ValueError)

    @pytest.mark.parametrize("json_only", [True, False])
    def test_user_content_with_template_syntax_survives_verbatim(self, json_only):
        tricky = "{{foo}} / {{#if json_only}}x{{/if}} / {{#ifnot json_only}}y{{/ifnot}} / {{brief_content}}"
        loader = PromptLoader()
        render = loader.information_matrix_json if json_only else loader.information_matrix

        prompt = render(brief_content=tricky, mechanism_content=tricky, is_prototype=True)

        assert prompt.count(tricky) == 2

    def test_strict_render_is_opt_in_other_templates_stay_lenient(self):
        """Stage 1/3/审计仍走宽松渲染：缺变量不报错，未知占位符原样保留（回归保护）."""
        prompt = PromptLoader().consistency_round1(
            characters_content="角色剧本内容", matrix_content="信息矩阵内容", is_prototype=True
        )
        assert "角色剧本内容" in prompt
        assert "{{mechanism_content}}" in prompt


class TestDerivedDefaultsTreatNoneAsNotProvided:
    """显式传入 None 的衍生变量按"未提供"处理（此前会渲染成空串）."""

    def test_prepare_vars_replaces_none_with_defaults(self):
        vars = PromptLoader()._prepare_vars({
            "is_prototype": True,
            "char_count": None,
            "event_count": None,
            "word_count_a": None,
            "fill_rules": None,
            "matrix_table": None,
        })
        assert vars["char_count"] == 2
        assert vars["event_count"] == 3
        assert vars["word_count_a"] == "800-1200"
        assert "凶手必须拥有核心事件的关键碎片" in vars["fill_rules"]
        assert "| E3（核心） |" in vars["matrix_table"]

    def test_mode_labels_none_means_not_provided(self):
        loader = PromptLoader()
        assert "mode_label" not in loader._prepare_vars({"mode_label": None})
        derived = loader._prepare_vars({"is_prototype": False, "mode_label": None, "is_prototype_bool": None})
        assert derived["mode_label"] == "完整模式"
        assert derived["is_prototype_bool"] == "false"

    def test_non_derived_none_is_left_alone(self):
        vars = PromptLoader()._prepare_vars({"is_prototype": True, "brief_content": None})
        assert vars["brief_content"] is None

    @pytest.mark.parametrize("is_prototype,rule,last_event", [
        (True, "2人拼图 = 完整真相", "| E3（核心） |"),
        (False, "没有任何角色拥有全部真相", "| E7（核心） |"),
    ])
    def test_q1_prompt_with_none_fill_rules_and_table_has_defaults(self, is_prototype, rule, last_event):
        prompt = PromptLoader().information_matrix_json(
            brief_content="b", mechanism_content="m", is_prototype=is_prototype,
            fill_rules=None, matrix_table=None,
        )
        assert rule in prompt
        assert last_event in prompt
        assert "## 填充规则\n\n" not in prompt  # 规则段不为空
        assert "| | R1 |" in prompt


class TestMatrixJsonExample:
    """Q1 的 JSON 示例由代码按 schema 生成，必须通过校验并明确只是格式示例."""

    @pytest.mark.parametrize("json_only", [True, False])
    @pytest.mark.parametrize("char_count,event_count,is_prototype", [(2, 3, True), (6, 7, False)])
    def test_example_in_prompt_validates_against_schema(self, char_count, event_count, is_prototype, json_only):
        loader = PromptLoader()
        render = loader.information_matrix_json if json_only else loader.information_matrix
        prompt = render(brief_content="b", mechanism_content="m", is_prototype=is_prototype)

        data = _extract_json_example(prompt)
        matrix = CharacterMatrix.model_validate(data)

        assert (matrix.char_count, matrix.event_count, matrix.is_prototype) == (char_count, event_count, is_prototype)
        assert list(matrix.characters) == [f"R{i}" for i in range(1, char_count + 1)]
        event_ids = [f"E{j}" for j in range(1, event_count + 1)]
        for cid, entry in matrix.characters.items():
            assert entry.character_id == cid
            assert list(entry.event_cognitions) == event_ids
        for eid in event_ids:
            assert matrix.all_know(eid), f"{eid} 没有任何角色为 知"

        assert matrix.evidence
        for evidence_id, item in matrix.evidence.items():
            assert item.evidence_id == evidence_id and item.description
            assert item.source_event in event_ids
            assert item.source_character in matrix.characters
        for entry in matrix.characters.values():
            for cognition in entry.event_cognitions.values():
                assert set(cognition.evidence_refs) <= set(matrix.evidence)

    @pytest.mark.parametrize("json_only", [True, False])
    def test_prompt_says_example_is_format_only(self, json_only):
        loader = PromptLoader()
        render = loader.information_matrix_json if json_only else loader.information_matrix
        prompt = render(brief_content="b", mechanism_content="m", is_prototype=True)

        assert "格式示例" in prompt
        assert "不得照抄" in prompt
        assert "知|疑|昧|否|误信|隐瞒" not in prompt  # 旧示例把候选值当成 state 的字面量

    @pytest.mark.parametrize("json_only", [True, False])
    def test_prompt_states_the_points_to_rule_in_the_hard_requirements(self, json_only):
        """校验接受任意字符串 points_to（凶手ID或其他结论）；提示词的硬性要求里要把这条规则说清楚."""
        loader = PromptLoader()
        render = loader.information_matrix_json if json_only else loader.information_matrix
        prompt = render(brief_content="b", mechanism_content="m", is_prototype=True)

        requirements = prompt.split("JSON 硬性要求")[1]
        assert "points_to" in requirements

    def test_helper_builds_valid_example_for_prototype_and_full(self):
        from murder_wizard.prompts.loader import build_matrix_example, build_matrix_example_json

        for char_count, event_count, is_prototype in ((2, 3, True), (6, 7, False)):
            example = build_matrix_example(char_count, event_count, is_prototype)
            CharacterMatrix.model_validate(example)
            assert json.loads(build_matrix_example_json(char_count, event_count, is_prototype)) == example

    @pytest.mark.parametrize("char_count,event_count", [(0, 3), (2, 0), (-1, 3), (2.5, 3), (True, 3)])
    def test_helper_rejects_invalid_sizes(self, char_count, event_count):
        from murder_wizard.prompts.loader import build_matrix_example

        with pytest.raises(ValueError):
            build_matrix_example(char_count, event_count, True)


# ─── 批次 A 审查修复（第三轮）：严格渲染守卫 / JSON-only 变体 / 示例占位文字识别 ─────────────────


class TestStage2StrictRenderingGuards:
    @pytest.mark.parametrize("method,template,heading,required", STAGE_2_STEPS)
    def test_residual_template_variable_is_rejected_before_any_model_call(self, method, template, heading, required):
        """模板里留着无法解析的变量：渲染就失败并点名，而不是产出带 {{x}} 的半成品或抛 KeyError."""
        loader = PromptLoader()
        real_load = loader._load_raw
        loader._load_raw = lambda filename: real_load(filename) + "\n{{unknown_thing}}\n"

        with pytest.raises(PromptRenderError) as exc_info:
            getattr(loader, method)(**_inputs(required), is_prototype=True)

        assert exc_info.value.missing == ("unknown_thing",)
        assert "unknown_thing" in str(exc_info.value) and "未调用模型" in str(exc_info.value)
        assert exc_info.value.template == template

    def test_residual_variable_and_missing_input_are_reported_together(self):
        loader = PromptLoader()
        real_load = loader._load_raw
        loader._load_raw = lambda filename: real_load(filename) + "\n{{unknown_thing}}\n"

        with pytest.raises(PromptRenderError) as exc_info:
            loader.character_script_a(
                **_inputs(("matrix_content", "mechanism_content")), is_prototype=True
            )  # 缺 background_content

        assert set(exc_info.value.missing) == {"unknown_thing", "background_content"}

    @pytest.mark.parametrize("method", ["information_matrix", "information_matrix_json"])
    @pytest.mark.parametrize("bad", [{"char_count": 0}, {"event_count": 0}, {"char_count": -2}])
    def test_unavailable_json_example_is_reported_instead_of_silently_dropped(self, method, bad):
        """人数/事件数非法时生成不了 JSON 示例：不能留着空洞去调用模型，也不能抛裸 KeyError."""
        with pytest.raises(PromptRenderError) as exc_info:
            getattr(PromptLoader(), method)(
                **_inputs(("brief_content", "mechanism_content")), is_prototype=True, **bad
            )

        assert exc_info.value.missing == ("matrix_json_example",)


class TestQ1JsonOnlyVariant:
    def test_json_variant_and_markdown_variant_differ_as_documented(self):
        loader = PromptLoader()
        inputs = _inputs(("brief_content", "mechanism_content"))

        json_prompt = loader.information_matrix_json(**inputs, is_prototype=True)
        markdown_prompt = loader.information_matrix(**inputs, is_prototype=True)

        # 阶段 2 用的 JSON-only：直接输出 JSON，没有 Markdown 的证据链设计
        assert "请直接输出 JSON 格式" in json_prompt
        assert "附加：证据链设计" not in json_prompt
        assert "请在 Markdown 输出之后" not in json_prompt
        # Markdown 变体：先 Markdown（含证据链设计）后 JSON
        assert "附加：证据链设计" in markdown_prompt
        assert "请在 Markdown 输出之后" in markdown_prompt
        assert "请直接输出 JSON 格式" not in markdown_prompt


def _example_free_texts(char_count: int = 6, event_count: int = 7, is_prototype: bool = False) -> list[str]:
    from murder_wizard.prompts.loader import EXAMPLE_PLACEHOLDER_MARK, build_matrix_example

    texts, stack = [], [build_matrix_example(char_count, event_count, is_prototype)]
    while stack:
        value = stack.pop()
        if isinstance(value, str):
            if EXAMPLE_PLACEHOLDER_MARK in value:
                texts.append(value)
        elif isinstance(value, dict):
            stack.extend(value.values())
        elif isinstance(value, list):
            stack.extend(value)
    return texts


class TestExamplePlaceholderRecognition:
    """生成路径靠它拒绝照抄示例的回复：标记写法的差异或只删标记都不能蒙混过关."""

    MARK_VARIANTS = ["（示例）", "(示例)", "（ 示例 ）", "（示例", "［示例］", "[示例]", "【示例】", "（示 例）", "（示​例）", "示例"]

    @pytest.mark.parametrize("mark", MARK_VARIANTS + [""])
    def test_every_example_text_is_recognised_whatever_the_mark_looks_like(self, mark):
        from murder_wizard.prompts.loader import EXAMPLE_PLACEHOLDER_MARK, is_example_placeholder_text

        texts = _example_free_texts()

        assert len(texts) >= 60  # 6 位角色 x (姓名/身份/关系 + 7 个认知说明) + 3 条证据 x 3 段文字
        for text in texts:
            assert is_example_placeholder_text(text.replace(EXAMPLE_PLACEHOLDER_MARK, mark)), text

    @pytest.mark.parametrize("mark", [m for m in MARK_VARIANTS if m != "示例"])
    def test_authored_text_that_still_carries_a_mark_is_recognised(self, mark):
        """作者写了真内容却漏删标记（写法不限）：同样是没清理干净的占位，不能因为正文是新写的就放过."""
        from murder_wizard.prompts.loader import is_example_placeholder_text

        assert is_example_placeholder_text("林远" + mark)
        assert is_example_placeholder_text("他亲手锁上书房" + mark)

    @pytest.mark.parametrize("text", [
        "林远",
        "戏班班主",
        "亲手锁上书房",
        "他当众示例了开锁手法",                 # 「示例」作普通词
        "证据描述了一把只有管家持有的钥匙",         # 含示例里的词，但不是整句相同
        "社会身份复杂的戏班账房",
        "示例",
        "",
        "   ",
    ])
    def test_story_text_is_not_mistaken_for_the_example(self, text):
        from murder_wizard.prompts.loader import is_example_placeholder_text

        assert is_example_placeholder_text(text) is False

    def test_whole_sentence_equal_to_an_example_text_is_recognised_even_with_padding(self):
        from murder_wizard.prompts.loader import is_example_placeholder_text

        assert is_example_placeholder_text("社会身份")
        assert is_example_placeholder_text("  认知说明\n")
        assert is_example_placeholder_text("角色３姓名")  # 全角数字，NFKC 之后与示例相同


# ─── 批次 A 复审修复：Q3 人数措辞 / 严格渲染只替换一次 / 只含不可见字符的输入算空 ─────────────────────


class TestOtherCharactersWording:
    """char_count 是角色总数（原型 2 / 完整 6），不是「其他角色」的数量。"""

    @pytest.mark.parametrize("is_prototype,total", [(True, 2), (False, 6)], ids=["prototype", "full"])
    def test_q3_does_not_tell_each_character_it_has_total_many_other_characters(self, is_prototype, total):
        prompt = PromptLoader().character_script_a(
            **_inputs(("background_content", "matrix_content", "mechanism_content")), is_prototype=is_prototype
        )

        assert f"其他{total}位" not in prompt
        # 点明的是矩阵里的角色范围与「除自己以外」，而不是一个错的数量
        assert f"R1-R{total}" in prompt
        assert "除自己以外" in prompt
        assert "不得增加矩阵之外的角色" in prompt

    @pytest.mark.parametrize("is_prototype", [True, False], ids=["prototype", "full"])
    @pytest.mark.parametrize("method,template,heading,required", STAGE_2_STEPS)
    def test_no_step_prompt_counts_the_other_characters_with_the_total(
        self, method, template, heading, required, is_prototype
    ):
        prompt = getattr(PromptLoader(), method)(**_inputs(required), is_prototype=is_prototype)

        assert re.findall(r"(?:其他|其余|另外)\s*\d+\s*(?:位|个|名|人)", prompt) == []


class TestRenderIsSinglePass:
    @pytest.mark.parametrize("method,template,heading,required", STAGE_2_STEPS)
    def test_user_text_naming_a_known_placeholder_is_not_substituted_again(self, method, template, heading, required):
        """用户内容里恰好写着某个已知占位符（同一次渲染里另一个输入的名字，或派生变量名）：
        替换只做一遍，它必须原样留在 prompt 里，而不是被换成别的输入的内容。"""
        inputs = {name: f"VALUE_OF_{name}" for name in required}
        first, second = required[0], required[1]
        inputs[first] = f"引用 {{{{{second}}}}} 与 {{{{char_count}}}} 的原文"

        prompt = getattr(PromptLoader(), method)(**inputs, is_prototype=True)

        assert inputs[first] in prompt, "用户文本被改写了（二次替换）"
        assert prompt.count(f"VALUE_OF_{second}") == 1, "另一个输入的内容被二次替换到了用户文本里"

    def test_the_documented_example_brief_text_survives_verbatim(self):
        prompt = PromptLoader().information_matrix_json(
            brief_content="{{mechanism_content}}", mechanism_content="MECH", is_prototype=True
        )

        assert "【brief.md 完整内容】\n{{mechanism_content}}\n" in prompt
        assert prompt.count("MECH") == 1


class TestInvisibleTextCountsAsBlank:
    """零宽空格 U+200B、BOM U+FEFF 等格式字符（Unicode 类别 Cf）str.strip() 去不掉，但对模型来说没有内容。"""

    BLANKS = ["​", "﻿", "​‌‍⁠", " ​\n﻿\t", "­؜᠎"]

    @pytest.mark.parametrize("bad_value", BLANKS, ids=["zwsp", "bom", "format_chars", "mixed_with_space", "soft_hyphen_etc"])
    @pytest.mark.parametrize("method,template,heading,required", STAGE_2_STEPS)
    def test_required_input_made_only_of_invisible_characters_is_rejected(
        self, method, template, heading, required, bad_value
    ):
        inputs = _inputs(required)
        inputs[required[-1]] = bad_value

        with pytest.raises(PromptRenderError) as exc_info:
            getattr(PromptLoader(), method)(**inputs, is_prototype=False)

        assert exc_info.value.missing == (required[-1],)
        assert "未调用模型" in str(exc_info.value)

    @pytest.mark.parametrize("text", ["​真正的内容", "内容﻿", "​·​", "a", "0"])
    def test_text_with_any_visible_character_is_not_blank(self, text):
        inputs = _inputs(("brief_content", "mechanism_content"))
        inputs["brief_content"] = text

        assert text in PromptLoader().information_matrix_json(**inputs, is_prototype=True)

    @pytest.mark.parametrize("value,blank", [
        (None, True), ("", True), ("  \n\t", True), ("​", True), ("﻿​ ", True),
        ("x", False), ("​x", False), ("。", False), ("⠀", False),
    ])
    def test_is_blank_text(self, value, blank):
        from murder_wizard.prompts.loader import is_blank_text

        assert is_blank_text(value) is blank
