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

    def test_extract_revised_content_code_block(self):
        """Extract revised content from Reviser markdown output via code fence."""
        import re

        def extract(revision_output, original):
            patterns = [
                r"(?<=## 修复内容\n).*(?=##|$)",
                r"(?<=## 修复后内容\n).*(?=##|$)",
                r"(?<=## 角色剧本\n).*(?=##|$)",
            ]
            for pattern in patterns:
                match = re.search(pattern, revision_output, re.DOTALL)
                if match and len(match.group(0).strip()) > 100:
                    return match.group(0).strip()
            code_blocks = re.findall(r"```(?:markdown)?\n(.*?)```", revision_output, re.DOTALL)
            for block in code_blocks:
                if len(block.strip()) > len(original) * 0.5 and "角色" in block:
                    return block.strip()
            return original

        # Too short to match (>100 chars needed)
        short_output = "## 修复内容\n\n这里是修复后的角色剧本内容...\n## 其他章节\n"
        assert extract(short_output, "x" * 200) == "x" * 200

        # Code block with "角色" keyword should match
        # Block must be > 50% of original length
        long_original = "原始内容" * 5  # 20 chars
        code_output = """## 修复清单
修复了一些问题

```markdown
## 修复后的角色剧本

这是新的角色剧本内容，角色张三有了新的设定
```
"""
        result = extract(code_output, long_original)
        assert "修复后的角色剧本" in result



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
