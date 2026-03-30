"""Tests for murder_wizard.prompts.loader."""
import pytest
from murder_wizard.prompts.loader import PromptLoader


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
            story_type="机制本",
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
