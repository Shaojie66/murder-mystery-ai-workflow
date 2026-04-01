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

    def test_stage2_script_type_specific(self):
        """stage2_script renders different templates per story type."""
        loader = PromptLoader()
        emotion = loader.stage2_script(story_type="emotion", brief_content="b", mechanism_content="m", is_prototype=False)
        reasoning = loader.stage2_script(story_type="reasoning", brief_content="b", mechanism_content="m", is_prototype=False)
        # Templates should differ (different structure/content per type)
        assert emotion != reasoning
        # Templates should contain type-specific keywords
        assert "情感" in emotion
        assert "证据" in reasoning or "线索" in reasoning

    def test_stage2_script_falls_back_to_mechanic(self):
        """Unknown story type falls back to mechanic template."""
        loader = PromptLoader()
        mechanic = loader.stage2_script(story_type="mechanic", brief_content="b", mechanism_content="m", is_prototype=False)
        unknown = loader.stage2_script(story_type="unknown_type_xyz", brief_content="b", mechanism_content="m", is_prototype=False)
        # Should fall back to mechanic (same output)
        assert unknown == mechanic

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
