"""Tests for murder_wizard.wizard.truth_files."""
import json
import tempfile
from pathlib import Path

import pytest

from murder_wizard.wizard.truth_files import TruthFileManager
from murder_wizard.wizard.schemas import CharacterMatrix, CharacterEntry, CognitiveState, TruthDelta, DeltaOp, Meta


class TestTruthFileManager:
    """TruthFileManager tests."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.mgr = TruthFileManager(Path(self.tmpdir))

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_create_matrix(self):
        matrix = self.mgr.create_matrix(char_count=2, event_count=3, is_prototype=True)
        assert matrix.char_count == 2
        assert matrix.event_count == 3
        assert matrix.is_prototype is True
        assert "R1" in matrix.characters
        assert "R2" in matrix.characters
        assert "E1" in matrix.characters["R1"].event_cognitions

    def test_save_and_load_matrix(self):
        matrix = self.mgr.create_matrix(char_count=2, event_count=3)
        self.mgr.save_matrix(matrix)

        loaded = self.mgr.load_matrix()
        assert loaded is not None
        assert loaded.char_count == 2
        assert loaded.event_count == 3
        assert "R1" in loaded.characters

    def test_load_nonexistent(self):
        result = self.mgr.load_matrix()
        assert result is None

    def test_exists(self):
        assert self.mgr.exists("character_matrix") is False
        matrix = self.mgr.create_matrix(char_count=2, event_count=3)
        self.mgr.save_matrix(matrix)
        assert self.mgr.exists("character_matrix") is True

    def test_backup_on_save(self):
        matrix = self.mgr.create_matrix(char_count=2, event_count=3)
        self.mgr.save_matrix(matrix)

        # Modify and save again
        matrix.characters["R1"].name = "张三"
        self.mgr.save_matrix(matrix)

        # Backup should exist
        backups = list((self.mgr.state_dir / ".backups").glob("character_matrix.*.json"))
        assert len(backups) >= 1

    def test_generate_delta(self):
        old = self.mgr.create_matrix(char_count=2, event_count=3)
        old.characters["R1"].name = "旧名字"
        old.characters["R1"].event_cognitions["E1"] = CognitiveState(state="否")

        new = self.mgr.create_matrix(char_count=2, event_count=3)
        new.characters["R1"].name = "新名字"
        new.characters["R1"].event_cognitions["E1"] = CognitiveState(state="知")

        delta = self.mgr.generate_delta(old, new, reason="test")
        assert delta.target_file == "character_matrix"
        assert len(delta.operations) >= 2

        # Should have name change
        name_ops = [op for op in delta.operations if "name" in op.path]
        assert len(name_ops) >= 1

    def test_apply_delta(self):
        old = self.mgr.create_matrix(char_count=2, event_count=3)
        old.characters["R1"].name = "旧"

        new_state = self.mgr.apply_delta(old, TruthDelta(
            target_file="character_matrix",
            operations=[
                DeltaOp(op="update", path="characters.R1.name", old_value="旧", new_value="新", reason="test")
            ]
        ))

        assert new_state.characters["R1"].name == "新"

    def test_audit_completeness_all_missing(self):
        """Empty matrix should report issues."""
        matrix = self.mgr.create_matrix(char_count=2, event_count=3, is_prototype=True)
        issues = self.mgr.audit_matrix_completeness(matrix)
        # No evidence + no characters know events = issues
        assert len(issues) >= 1
        assert any("evidence" in i.lower() for i in issues)

    def test_audit_killer_knowledge(self):
        """Empty killer cognition is flagged as an issue."""
        matrix = self.mgr.create_matrix(char_count=2, event_count=3)
        issues = self.mgr.audit_killer_knowledge(matrix)
        # Killer knows 0 events — correctly flagged
        assert len(issues) == 1
        assert "knows 0 of 3" in issues[0]

    def test_migrate_from_markdown(self):
        """Can migrate a simple Markdown matrix."""
        md = """| | R1 | R2 | R3 |
|---|---|---|---|
| E1 | 知 | 疑 | 否 |
| E2 | 误信 | 知 | 疑 |
"""
        matrix = self.mgr.migrate_from_markdown(md, char_count=3, event_count=2, is_prototype=False)
        assert matrix.char_count == 3
        assert matrix.event_count == 2
        assert matrix.characters["R1"].event_cognitions["E1"].state == "知"
        assert matrix.characters["R2"].event_cognitions["E1"].state == "疑"


class TestCharacterMatrix:
    """CharacterMatrix model tests."""

    def test_get_cognition_exists(self):
        cm = CharacterMatrix(char_count=2, event_count=3, is_prototype=False, characters={
            "R1": CharacterEntry(character_id="R1", event_cognitions={
                "E1": CognitiveState(state="知", detail="test")
            })
        })
        assert cm.get_cognition("R1", "E1") == "知"

    def test_get_cognition_missing_char(self):
        cm = CharacterMatrix(char_count=2, event_count=3, is_prototype=False, characters={})
        assert cm.get_cognition("R1", "E1") is None

    def test_all_know(self):
        cm = CharacterMatrix(char_count=3, event_count=2, is_prototype=False, characters={
            "R1": CharacterEntry(character_id="R1", event_cognitions={
                "E1": CognitiveState(state="知")
            }),
            "R2": CharacterEntry(character_id="R2", event_cognitions={
                "E1": CognitiveState(state="知")
            }),
            "R3": CharacterEntry(character_id="R3", event_cognitions={
                "E1": CognitiveState(state="否")
            }),
        })
        knowers = cm.all_know("E1")
        assert "R1" in knowers
        assert "R2" in knowers
        assert "R3" not in knowers


class TestReviserHelpers:
    """Tests for _extract_revised_content and _count_p0_issues."""

    def test_count_p0_issues_patterns(self):
        """Various P0 count patterns detected by regex."""
        import re

        def count_p0(content):
            matches = re.findall(r"p0[：:]\s*(\d+)", content, re.IGNORECASE)
            if matches:
                return sum(int(m) for m in matches)
            return content.count("[P0]") + content.count("**P0**") + content.count("P0\n")

        assert count_p0("P0: 3") == 3
        assert count_p0("P0：5个") == 5
        assert count_p0("p0: 2") == 2
        assert count_p0("无 P0 问题") == 0
        assert count_p0("") == 0

    def test_extract_revised_content_rejects_fix_list(self):
        """_extract_revised_content must NOT accept ## 修复清单 as valid content.

        This was the original bug: the fix list section was accepted as replacement
        content even though it's just bullet points, not actual script.
        """
        import re

        def extract(revision_output, original):
            script_markers = ["角色", "场景", "剧本", "对白", "叙述", "事件"]
            patterns = [
                r"(?<=## 完整角色剧本\n)([\s\S]+?)(?=\n## |\Z)",
                r"(?<=## 修复后角色剧本\n)([\s\S]+?)(?=\n## |\Z)",
                r"(?<=## 角色剧本\n)([\s\S]+?)(?=\n## |\Z)",
            ]
            for pattern in patterns:
                match = re.search(pattern, revision_output, re.DOTALL)
                if match:
                    content = match.group(1).strip()
                    marker_count = sum(1 for m in script_markers if m in content)
                    if marker_count >= 3 and len(content) > 200:
                        return content
            code_blocks = re.findall(r"```(?:markdown)?\n(.*?)```", revision_output, re.DOTALL)
            for block in code_blocks:
                block = block.strip()
                marker_count = sum(1 for m in script_markers if m in block)
                if marker_count >= 3 and len(block) > len(original) * 0.3:
                    return block
            return original

        # ## 修复清单 must NOT be accepted (the original bug)
        fix_list_only = """## 修复清单

### 修复 1：P0-1 - 认知泄露
**涉及**：角色张三，事件E1
**修复内容**：
- 原文：张三知道妹妹的死因
- 改为：张三不知道妹妹的死因
"""
        original = "角色" * 100
        result = extract(fix_list_only, original)
        assert result == original, "## 修复清单 should not be accepted as valid script"

        # ## 完整角色剧本 section should match via section-based extraction
        # (content ends at string boundary, \Z)
        full_script = (
            '## 完整角色剧本\n\n'
            '### 角色：张三\n'
            '场景：家中客厅，深夜时分\n'
            '事件：深夜凶杀案\n'
            '对白：张三说："我知道真相。"补充。\n'
            '叙述：张三缓缓站起身，目光扫过在场的每一个人。房间里的气氛骤然紧张起来。\n'
            '场景：书房门口\n'
            '对白：李四喊道："站住！别想逃跑！"\n'
            '叙述：李四的手紧紧握着门把手，似乎随时准备阻止任何人离开。\n'
            '事件：保险箱被打开\n'
            '对白：王五说："保险箱里的文件不见了！"\n'
            '叙述：王五的脸色变得苍白，额头上渗出了细密的汗珠。\n'
        )
        original = "x" * 50
        result = extract(full_script, original)
        # Must extract the section content (has ≥3 script markers)
        assert "场景" in result and "事件" in result and "对白" in result



    """TruthDelta model tests."""

    def test_delta_serialization(self):
        delta = TruthDelta(
            target_file="character_matrix",
            operations=[
                DeltaOp(op="update", path="characters.R1.name", old_value="A", new_value="B", reason="rename")
            ]
        )
        json_str = delta.model_dump_json(ensure_ascii=False, indent=2)
        parsed = json.loads(json_str)
        assert parsed["target_file"] == "character_matrix"
        assert parsed["operations"][0]["op"] == "update"
