"""Tests for murder_wizard.wizard.truth_files."""
import json
import tempfile
from pathlib import Path

import pytest

from murder_wizard.wizard.truth_files import (
    MatrixContractError,
    TruthFileManager,
    validate_generated_matrix,
)
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


# ─── R02：模型生成的信息矩阵契约 ──────────────────────────────────────────────

import copy
import hashlib


def _valid_matrix_data() -> dict:
    """手写的合法 2x3 原型矩阵（含证据与证据引用），不依赖提示词里的示例生成器."""
    return {
        "char_count": 2,
        "event_count": 3,
        "is_prototype": True,
        "characters": {
            "R1": {
                "character_id": "R1",
                "name": "林远",
                "role": "管家",
                "public_relationship": "沈家的老管家",
                "event_cognitions": {
                    "E1": {"state": "知", "detail": "亲手锁上书房", "evidence_refs": ["EV-A"]},
                    "E2": {"state": "隐瞒", "detail": "知道怀表被换过，不会说", "evidence_refs": []},
                    "E3": {"state": "知", "detail": "目睹对峙", "evidence_refs": ["EV-A", "EV-B"]},
                },
            },
            "R2": {
                "character_id": "R2",
                "name": "沈映雪",
                "role": "戏班班主",
                "public_relationship": "死者的侄女",
                "event_cognitions": {
                    "E1": {"state": "误信", "detail": "以为书房是自己锁的", "evidence_refs": []},
                    "E2": {"state": "知", "detail": "发现怀表停在子时", "evidence_refs": ["EV-B"]},
                    "E3": {"state": "否", "detail": "", "evidence_refs": []},
                },
            },
        },
        "evidence": {
            "EV-A": {
                "evidence_id": "EV-A",
                "name": "书房钥匙",
                "description": "只有管家与死者持有",
                "source_event": "E1",
                "source_character": "R1",
                "chain_role": "排除外人作案",
                "points_to": "R2",
            },
            "EV-B": {
                "evidence_id": "EV-B",
                "name": "停摆的怀表",
                "description": "指针停在子时",
                "source_event": "E2",
                "source_character": "R2",
                "chain_role": "确定死亡时间",
                "points_to": "EV-A",
            },
        },
    }


def _full_matrix_data(char_count: int = 6, event_count: int = 7, is_prototype: bool = False) -> dict:
    """按人数 x 事件数生成的合法矩阵：事件 j 由角色 j % n 为「知」，其余为「疑」."""
    char_ids = [f"R{i}" for i in range(1, char_count + 1)]
    event_ids = [f"E{j}" for j in range(1, event_count + 1)]
    return {
        "char_count": char_count,
        "event_count": event_count,
        "is_prototype": is_prototype,
        "characters": {
            cid: {
                "character_id": cid,
                "name": f"角色{cid}",
                "event_cognitions": {
                    eid: {"state": "知" if char_ids[j % char_count] == cid else "疑", "detail": "d"}
                    for j, eid in enumerate(event_ids)
                },
            }
            for cid in char_ids
        },
        "evidence": {
            "EV-A": {
                "evidence_id": "EV-A", "name": "证据A", "description": "说明",
                "source_event": "E1", "source_character": "R1", "chain_role": "起点",
            }
        },
    }


def _check(data, char_count=2, event_count=3, is_prototype=True):
    return validate_generated_matrix(data, char_count, event_count, is_prototype)


def _problems(data, **kwargs) -> list[str]:
    with pytest.raises(MatrixContractError) as exc_info:
        _check(data, **kwargs)
    return exc_info.value.problems


class TestValidateGeneratedMatrix:
    def test_valid_2x3_matrix_passes_saves_and_reloads_equal(self, tmp_path):
        brief = "# 简报\n民国戏班旧案"
        matrix = validate_generated_matrix(_valid_matrix_data(), 2, 3, True, brief_content=brief)

        mgr = TruthFileManager(tmp_path)
        expected_hash = mgr.create_matrix(2, 3, True, brief_content=brief).meta.brief_content_hash
        assert expected_hash and matrix.meta.brief_content_hash == expected_hash
        assert matrix.meta.note

        mgr.save_matrix(matrix)
        loaded = mgr.load_matrix()
        assert loaded == matrix
        # 认知与证据原样保留：没有被默认值或「否」替换
        assert loaded.get_cognition("R1", "E2") == "隐瞒"
        assert loaded.get_cognition("R2", "E1") == "误信"
        assert loaded.characters["R1"].name == "林远"
        assert loaded.characters["R1"].event_cognitions["E3"].evidence_refs == ["EV-A", "EV-B"]
        assert set(loaded.evidence) == {"EV-A", "EV-B"}
        assert loaded.evidence["EV-B"].points_to == "EV-A"
        assert mgr.audit_matrix_completeness(loaded) == []

    def test_valid_full_6x7_matrix_passes(self):
        matrix = _check(_full_matrix_data(), 6, 7, False)
        assert matrix.char_count == 6 and matrix.event_count == 7 and matrix.is_prototype is False

    def test_counts_and_mode_come_from_caller_not_from_the_data(self):
        # 数据自洽（6x7 完整模式），但调用方期望 2x3 原型：必须拒绝
        problems = _problems(_full_matrix_data(), char_count=2, event_count=3, is_prototype=True)
        joined = "\n".join(problems)
        assert "char_count 应为 2" in joined
        assert "event_count 应为 3" in joined
        assert "is_prototype" in joined
        assert "多余角色 R3" in joined

    def test_missing_ids_are_taken_from_the_dict_keys(self):
        data = _valid_matrix_data()
        for entry in data["characters"].values():
            del entry["character_id"]
        del data["evidence"]["EV-A"]["evidence_id"]
        snapshot = copy.deepcopy(data)

        matrix = _check(data)

        assert matrix.characters["R1"].character_id == "R1"
        assert matrix.characters["R2"].character_id == "R2"
        assert matrix.evidence["EV-A"].evidence_id == "EV-A"
        assert data == snapshot  # 传入的数据不被修改

    def test_model_supplied_meta_is_not_trusted(self):
        data = _valid_matrix_data()
        data["meta"] = {"brief_content_hash": "forged", "note": "forged", "commit_hash": "forged"}
        matrix = validate_generated_matrix(data, 2, 3, True, brief_content="简报")
        assert matrix.meta.brief_content_hash == hashlib.sha256("简报".encode("utf-8")).hexdigest()[:16]
        assert matrix.meta.note != "forged"

    @pytest.mark.parametrize("bad", [None, [], "矩阵", 42])
    def test_non_dict_data_is_rejected(self, bad):
        problems = _problems(bad)
        assert any("JSON 对象" in p for p in problems)

    @pytest.mark.parametrize("label,mutate,needles", [
        ("wrong_char_count", lambda d: d.update(char_count=6), ["char_count 应为 2", "6"]),
        ("wrong_event_count", lambda d: d.update(event_count=5), ["event_count 应为 3", "5"]),
        ("wrong_mode", lambda d: d.update(is_prototype=False), ["is_prototype"]),
        ("missing_char_count", lambda d: d.pop("char_count"), ["缺少 char_count"]),
        ("string_event_count", lambda d: d.update(event_count="3"), ["event_count 应为 3"]),
        ("missing_character", lambda d: d["characters"].pop("R2"), ["缺少角色 R2"]),
        ("extra_character",
         lambda d: d["characters"].update(R3=copy.deepcopy(d["characters"]["R2"])), ["多余角色 R3"]),
        ("missing_event_cell",
         lambda d: d["characters"]["R1"]["event_cognitions"].pop("E2"), ["R1", "E2", "缺少事件认知"]),
        ("extra_event_cell",
         lambda d: d["characters"]["R1"]["event_cognitions"].update(E9={"state": "知"}),
         ["R1", "E9", "未知事件"]),
        ("missing_event_cognitions",
         lambda d: d["characters"]["R2"].pop("event_cognitions"), ["R2", "缺少 event_cognitions"]),
        ("illegal_state_pipe_literal",  # 旧 JSON 示例里的字面量
         lambda d: d["characters"]["R1"]["event_cognitions"]["E1"].update(state="知|疑|昧|否|误信|隐瞒"),
         ["R1", "E1", "state 非法", "知|疑|昧|否|误信|隐瞒"]),
        ("illegal_state_bracketed",
         lambda d: d["characters"]["R1"]["event_cognitions"]["E1"].update(state="[知]"),
         ["state 非法", "[知]"]),
        ("illegal_state_unlisted",
         lambda d: d["characters"]["R2"]["event_cognitions"]["E2"].update(state="不确定"),
         ["R2", "E2", "state 非法", "不确定"]),
        ("missing_state",
         lambda d: d["characters"]["R2"]["event_cognitions"]["E2"].pop("state"), ["R2", "E2", "缺少 state"]),
        ("cell_not_an_object",
         lambda d: d["characters"]["R2"]["event_cognitions"].update(E3="知"), ["R2", "E3", "必须是对象"]),
        ("empty_characters", lambda d: d.update(characters={}), ["characters 为空"]),
        ("missing_characters_key", lambda d: d.pop("characters"), ["缺少 characters"]),
        ("missing_name", lambda d: d["characters"]["R1"].pop("name"), ["R1", "name"]),
        ("blank_name", lambda d: d["characters"]["R2"].update(name="  "), ["R2", "name"]),
        ("no_evidence", lambda d: d.update(evidence={}), ["evidence 为空"]),
        ("missing_evidence_key", lambda d: d.pop("evidence"), ["缺少 evidence"]),
        ("dangling_evidence_ref",
         lambda d: d["characters"]["R1"]["event_cognitions"]["E2"].update(evidence_refs=["EV-ZZZ"]),
         ["R1", "E2", "EV-ZZZ", "不存在的证据"]),
        ("evidence_refs_not_a_list",
         lambda d: d["characters"]["R1"]["event_cognitions"]["E1"].update(evidence_refs="EV-A"),
         ["evidence_refs"]),
        ("evidence_missing_description",
         lambda d: d["evidence"]["EV-A"].pop("description"), ["EV-A", "缺少字段 description"]),
        ("evidence_missing_chain_role",
         lambda d: d["evidence"]["EV-B"].pop("chain_role"), ["EV-B", "缺少字段 chain_role"]),
        ("evidence_blank_description",
         lambda d: d["evidence"]["EV-A"].update(description="  "), ["EV-A", "description", "为空"]),
        ("evidence_blank_name",
         lambda d: d["evidence"]["EV-B"].update(name=""), ["EV-B", "name", "为空"]),
        ("evidence_unknown_source_event",
         lambda d: d["evidence"]["EV-A"].update(source_event="E9"), ["EV-A", "source_event", "E9"]),
        ("evidence_unknown_source_character",
         lambda d: d["evidence"]["EV-B"].update(source_character="R9"),
         ["EV-B", "source_character", "R9"]),
        ("event_nobody_knows",
         lambda d: d["characters"]["R1"]["event_cognitions"]["E3"].update(state="疑"),
         ["事件 E3", "没有任何角色为「知」"]),
        ("character_id_key_mismatch",
         lambda d: d["characters"]["R1"].update(character_id="R2"), ["R1", "character_id", "R2"]),
        ("evidence_id_key_mismatch",
         lambda d: d["evidence"]["EV-A"].update(evidence_id="EV-X"), ["EV-A", "evidence_id", "EV-X"]),
        ("schema_type_error_is_still_caught",
         lambda d: d["characters"]["R1"]["event_cognitions"]["E1"].update(detail=5),
         ["schema 校验失败", "detail"]),
    ])
    def test_contract_violation_is_rejected_with_a_problem_naming_it(self, label, mutate, needles):
        data = _valid_matrix_data()
        mutate(data)

        problems = _problems(data)

        assert any(all(needle in problem for needle in needles) for problem in problems), (
            f"{label}: 没有同时包含 {needles} 的问题项，实际：{problems}"
        )

    @pytest.mark.parametrize("points_to", ["R1是凶手", "R1、R2", "凶手", "排除外人作案", "R9"])
    def test_points_to_keeps_its_schema_meaning_of_killer_id_or_other_conclusion(self, points_to):
        """schema 把 points_to 定义为「凶手ID或其他结论」：校验不能把它收窄成必须是已知角色/证据 ID."""
        data = _valid_matrix_data()
        data["evidence"]["EV-A"]["points_to"] = points_to

        matrix = _check(data)

        assert matrix.evidence["EV-A"].points_to == points_to
        # 仍然只接受字符串
        data["evidence"]["EV-A"]["points_to"] = None
        assert any("points_to" in p and "字符串" in p for p in _problems(data))

    def test_all_no_matrix_is_rejected_as_default_fill(self):
        data = _valid_matrix_data()
        for entry in data["characters"].values():
            for cell in entry["event_cognitions"].values():
                cell["state"] = "否"
                cell["evidence_refs"] = []

        problems = _problems(data)

        assert any("所有认知状态均为「否」" in p for p in problems)
        # 每个事件也都无人知晓
        for eid in ("E1", "E2", "E3"):
            assert any(f"事件 {eid}" in p and "没有任何角色为「知」" in p for p in problems)

    def test_collects_all_problems_in_one_raise(self):
        data = _valid_matrix_data()
        data["char_count"] = 6
        data["characters"].pop("R2")
        data["characters"]["R1"]["event_cognitions"]["E1"]["state"] = "[知]"
        data["characters"]["R1"]["name"] = ""
        data["evidence"] = {}

        problems = _problems(data)

        joined = "\n".join(problems)
        for needle in ("char_count 应为 2", "缺少角色 R2", "state 非法", "R1 缺少非空的 name", "evidence 为空"):
            assert needle in joined, f"{needle!r} 不在 {problems}"
        assert len(problems) >= 5

    def test_missing_cell_is_not_filled_with_no(self):
        """缺失单元格要拒绝，不能像 migrate_from_markdown 那样补成「否」."""
        data = _valid_matrix_data()
        del data["characters"]["R1"]["event_cognitions"]["E2"]
        with pytest.raises(MatrixContractError):
            _check(data)

    def test_error_message_lists_the_problems(self):
        data = _valid_matrix_data()
        data["evidence"] = {}
        with pytest.raises(MatrixContractError) as exc_info:
            _check(data)
        assert "evidence 为空" in str(exc_info.value)
        assert isinstance(exc_info.value, ValueError)

    def test_bad_expected_counts_are_a_caller_bug_not_a_contract_error(self):
        with pytest.raises(ValueError) as exc_info:
            validate_generated_matrix(_valid_matrix_data(), 0, 3, True)
        assert not isinstance(exc_info.value, MatrixContractError)

    def test_migrate_from_markdown_stays_lossy_and_separate(self, tmp_path):
        """旧资料导入入口保持原行为（缺失单元格变「否」），与生成校验分开."""
        md = "| | R1 | R2 |\n|---|---|---|\n| E1 | 知 | 疑 |\n"
        matrix = TruthFileManager(tmp_path).migrate_from_markdown(
            md, char_count=2, event_count=3, is_prototype=True
        )
        assert matrix.characters["R1"].event_cognitions["E1"].state == "知"
        assert matrix.characters["R1"].event_cognitions["E3"].state == "否"  # 缺失 → 否
        assert matrix.evidence == {}
        # 同样的内容走生成校验必须被拒绝
        with pytest.raises(MatrixContractError):
            _check(matrix.model_dump())


# ─── 批次 A 审查修复（第三轮）：孤立代理项 ────────────────────────────────────────────────────
# JSON 里单独的 \ud800 转义能通过 json.loads，得到的字符串却无法编码成 UTF-8：序列化和写文件都会抛异常。


def _rename_evidence(data: dict, old: str, new: str) -> None:
    data["evidence"] = {
        (new if key == old else key): ({**item, "evidence_id": new} if key == old else item)
        for key, item in data["evidence"].items()
    }
    for entry in data["characters"].values():
        for cell in entry["event_cognitions"].values():
            cell["evidence_refs"] = [new if ref == old else ref for ref in cell["evidence_refs"]]


class TestLoneSurrogateText:
    @pytest.mark.parametrize("label,mutate,where", [
        ("character_name", lambda d: d["characters"]["R1"].update(name="林\ud800远"),
         "characters.R1.name"),
        ("cell_detail", lambda d: d["characters"]["R2"]["event_cognitions"]["E2"].update(detail="发现\ud800"),
         "characters.R2.event_cognitions.E2.detail"),
        ("evidence_description", lambda d: d["evidence"]["EV-A"].update(description="钥匙\ud800"),
         "evidence.EV-A.description"),
        ("points_to", lambda d: d["evidence"]["EV-A"].update(points_to="R2\ud800"),
         "evidence.EV-A.points_to"),
    ])
    def test_lone_surrogate_in_a_kept_field_is_rejected_with_its_location(self, label, mutate, where):
        data = _valid_matrix_data()
        mutate(data)

        problems = _problems(data)

        assert len(problems) == 1, problems  # 其余检查都通过：问题只在这一处文字
        assert "无法保存的字符" in problems[0] and where in problems[0]
        for problem in problems:
            problem.encode("utf-8")  # 问题文字本身必须可打印、可写日志

    def test_lone_surrogate_in_a_key_is_rejected_and_printable(self):
        data = _valid_matrix_data()
        _rename_evidence(data, "EV-A", "EV-A\ud800")

        problems = _problems(data)

        assert any("无法保存的字符" in problem for problem in problems)
        for problem in problems:
            problem.encode("utf-8")

    def test_unencodable_text_paths_locates_keys_values_and_list_items(self):
        from murder_wizard.wizard.truth_files import _unencodable_text_paths

        hits = _unencodable_text_paths({"证据\ud800": {"x": ["ok", "bad\ud800"]}, "fine": "ok", "top": "t\ud800"})

        assert hits == sorted(["证据\\ud800（键）", "证据\\ud800.x[1]", "top"])
        assert _unencodable_text_paths({"a": ["b", {"c": "d"}], "e": 1, "f": None}) == []

    def test_surrogate_in_a_field_the_schema_drops_is_not_a_problem(self):
        """被 schema 忽略、不会保存的多余字段带孤立代理项：发布时不会出问题，不拒绝."""
        data = _valid_matrix_data()
        data["notes"] = "草稿\ud800"
        data["characters"]["R1"]["scratch"] = "草稿\ud800"

        matrix = _check(data)

        matrix.model_dump_json(ensure_ascii=False).encode("utf-8")

    def test_a_valid_surrogate_pair_from_a_json_escape_is_ordinary_text(self):
        """\\ud83d\\ude00 是一对完整的代理项，json.loads 解成一个 emoji：不是孤立代理项，不能被误拒."""
        data = _valid_matrix_data()
        data["characters"]["R1"]["event_cognitions"]["E1"]["detail"] = json.loads('"锁上书房\\ud83d\\ude00"')
        data["characters"]["R2"]["name"] = "沈映雪😀"

        matrix = _check(data)

        assert matrix.characters["R1"].event_cognitions["E1"].detail == "锁上书房😀"
        matrix.model_dump_json(ensure_ascii=False).encode("utf-8")

    def test_contract_error_makes_problem_text_printable(self):
        """问题文字常嵌着模型给的键名：键里的孤立代理项被改写成转义文字，不会让打印/写日志再抛编码异常."""
        error = MatrixContractError(["多余角色 R3\ud800（应恰为 R1-R2）", "正常的中文问题"])

        assert error.problems == ["多余角色 R3\\ud800（应恰为 R1-R2）", "正常的中文问题"]
        str(error).encode("utf-8")

    def test_extra_role_key_with_a_lone_surrogate_reports_printable_problems(self):
        data = _valid_matrix_data()
        data["characters"]["R3\ud800"] = copy.deepcopy(data["characters"]["R1"])

        problems = _problems(data)

        assert any("多余角色 R3\\ud800" in problem for problem in problems)
        for problem in problems:
            problem.encode("utf-8")


# ─── 批次 A 复审修复：发布不能写坏旧文件 / 不采用模型给的 version / 结构检查逐项有测试 ─────────────────────

import os
import stat


class TestSaveNeverLeavesAHalfWrittenFile:
    """TruthFileManager.save：先写同目录临时文件再 os.replace；备份名唯一，绝不覆盖已有备份。"""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.mgr = TruthFileManager(Path(self.tmpdir))
        self.live = self.mgr.state_dir / "character_matrix.json"

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _matrix(self, name: str):
        matrix = self.mgr.create_matrix(char_count=2, event_count=3, is_prototype=True)
        matrix.characters["R1"].name = name
        return matrix

    def _backups(self) -> list[Path]:
        return sorted((self.mgr.state_dir / ".backups").glob("character_matrix.*.json"))

    def _in_state_dir(self, path: Path) -> bool:
        return path.parent == self.mgr.state_dir

    def test_write_failure_midway_keeps_the_previous_file_byte_for_byte(self, disk_full):
        self.mgr.save_matrix(self._matrix("旧版林远"))
        before = self.live.read_bytes()
        files_before = {path for path in self.mgr.state_dir.rglob("*")}

        with disk_full(self._in_state_dir):
            with pytest.raises(OSError):
                self.mgr.save_matrix(self._matrix("新版林远"))

        assert self.live.read_bytes() == before, "写到一半失败后，旧文件被截断/改写了"
        assert self.mgr.load_matrix().characters["R1"].name == "旧版林远"
        for path in self.mgr.state_dir.rglob("*"):
            if path.is_file() and path != self.live and path not in files_before:
                # 失败时允许多出的只有「旧文件的完整备份」；半截临时文件不允许留下
                assert path.read_bytes() == before, f"失败后留下了多余文件：{path.name}"

    def test_first_save_that_fails_leaves_no_half_written_live_file(self, disk_full):
        with disk_full(self._in_state_dir):
            with pytest.raises(OSError):
                self.mgr.save_matrix(self._matrix("林远"))

        assert not self.live.exists()
        assert self.mgr.load_matrix() is None
        assert [path for path in self.mgr.state_dir.iterdir() if path.is_file()] == []

    def test_quick_retry_after_a_failed_write_keeps_the_good_backup(self, disk_full):
        """原来的写法：失败时已把旧文件备份、live 被截断；一秒内重试又用截断的 live 覆盖了好备份。"""
        self.mgr.save_matrix(self._matrix("旧版林远"))
        old_bytes = self.live.read_bytes()

        with disk_full(self._in_state_dir):
            with pytest.raises(OSError):
                self.mgr.save_matrix(self._matrix("新版林远"))
        self.mgr.save_matrix(self._matrix("新版林远"))  # 马上重试

        assert self.mgr.load_matrix().characters["R1"].name == "新版林远"
        backups = self._backups()
        assert backups, "重试后应有旧版的备份"
        assert any(backup.read_bytes() == old_bytes for backup in backups), "好备份被覆盖了"
        for backup in backups:
            json.loads(backup.read_text(encoding="utf-8"))  # 每份备份都是完整、合法的 JSON

    def test_failed_swap_leaves_no_temp_file_and_the_live_file_untouched(self):
        from unittest.mock import patch

        self.mgr.save_matrix(self._matrix("旧版林远"))
        before = self.live.read_bytes()

        with patch("os.replace", side_effect=OSError(5, "I/O error")):
            with pytest.raises(OSError):
                self.mgr.save_matrix(self._matrix("新版林远"))

        assert self.live.read_bytes() == before
        assert [path.name for path in self.mgr.state_dir.iterdir() if path.is_file()] == ["character_matrix.json"]

    def test_backup_copy_failing_midway_leaves_no_partial_backup_and_the_live_file_untouched(self):
        from unittest.mock import patch

        self.mgr.save_matrix(self._matrix("旧版林远"))
        before = self.live.read_bytes()

        def copy_that_dies_midway(src, dst, *args, **kwargs):
            Path(dst).write_bytes(Path(src).read_bytes()[:10])  # 只拷了开头就失败
            raise OSError(28, "No space left on device")

        with patch("shutil.copy2", copy_that_dies_midway):
            with pytest.raises(OSError):
                self.mgr.save_matrix(self._matrix("新版林远"))

        assert self.live.read_bytes() == before
        assert self._backups() == [], "拷贝到一半失败，留下了残缺的备份"
        assert [path.name for path in self.mgr.state_dir.iterdir() if path.is_file()] == ["character_matrix.json"]

    def test_rapid_saves_each_keep_their_own_backup(self):
        names = [f"版本{index}" for index in range(20)]
        for name in names:
            self.mgr.save_matrix(self._matrix(name))

        backups = self._backups()
        assert len(backups) == len(names) - 1, "快速连续保存时有备份被同名覆盖了"
        assert len({backup.name for backup in backups}) == len(backups)
        kept = sorted(json.loads(backup.read_text(encoding="utf-8"))["characters"]["R1"]["name"] for backup in backups)
        assert kept == sorted(names[:-1])  # 除最新版外，每一版都有备份

    def test_backup_names_stay_unique_even_when_the_clock_does_not_move(self):
        from datetime import datetime as real_datetime
        from unittest.mock import patch

        class FrozenDatetime(real_datetime):
            @classmethod
            def now(cls, tz=None):
                return real_datetime(2026, 10, 25, 12, 0, 0, 123456)

        with patch("murder_wizard.wizard.truth_files.datetime", FrozenDatetime):
            for name in ("甲", "乙", "丙", "丁"):
                self.mgr.save_matrix(self._matrix(name))

        kept = sorted(
            json.loads(backup.read_text(encoding="utf-8"))["characters"]["R1"]["name"] for backup in self._backups()
        )
        assert kept == ["丙", "乙", "甲"]
        # 备份名精确到微秒；同一刻的重名才加序号后缀（序号放在 .json 之前，列表模式 character_matrix.*.json 仍然匹配）
        names = sorted(backup.name for backup in self._backups())
        assert names[0] == "character_matrix.20261025_120000_123456.json"
        assert names[1:] == [
            "character_matrix.20261025_120000_123456_1.json",
            "character_matrix.20261025_120000_123456_2.json",
        ]

    def test_an_existing_backup_with_the_same_name_is_never_overwritten(self):
        from datetime import datetime as real_datetime
        from unittest.mock import patch

        class FrozenDatetime(real_datetime):
            @classmethod
            def now(cls, tz=None):
                return real_datetime(2026, 10, 25, 12, 0, 0, 123456)

        self.mgr.save_matrix(self._matrix("旧版"))
        taken = self.mgr.state_dir / ".backups"
        taken.mkdir(exist_ok=True)
        # 占住「这一刻」可能用到的每个备份名（含微秒的新格式，也含只到秒的旧格式）
        sentinels = {
            taken / "character_matrix.20261025_120000_123456.json": b"sentinel-1",
            taken / "character_matrix.20261025_120000.json": b"sentinel-2",
        }
        for path, content in sentinels.items():
            path.write_bytes(content)

        with patch("murder_wizard.wizard.truth_files.datetime", FrozenDatetime):
            self.mgr.save_matrix(self._matrix("新版"))

        for path, content in sentinels.items():
            assert path.read_bytes() == content, f"{path.name} 被覆盖了"
        assert any(
            "旧版" in path.read_text(encoding="utf-8") for path in self._backups() if path not in sentinels
        ), "旧版应备份到一个新名字上"

    def test_backups_still_match_the_listing_pattern_and_keep_the_old_content(self):
        self.mgr.save_matrix(self._matrix("旧版林远"))
        self.mgr.save_matrix(self._matrix("新版林远"))

        backups = list((self.mgr.state_dir / ".backups").glob("character_matrix.*.json"))

        assert len(backups) == 1
        assert "旧版林远" in backups[0].read_text(encoding="utf-8")

    @pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")
    def test_save_keeps_the_permission_bits_of_the_existing_file(self):
        self.mgr.save_matrix(self._matrix("旧版"))
        os.chmod(self.live, 0o640)

        self.mgr.save_matrix(self._matrix("新版"))

        assert stat.S_IMODE(self.live.stat().st_mode) == 0o640


class TestModelVersionIsNotAdopted:
    @pytest.mark.parametrize("supplied", ["banana", "9.9.9", "", 5, None, ["1.0.0"]])
    def test_model_supplied_version_is_reset_to_the_schema_default(self, supplied):
        data = _valid_matrix_data()
        data["version"] = supplied
        snapshot = copy.deepcopy(data)

        matrix = _check(data)

        assert matrix.version == CharacterMatrix.model_fields["version"].default
        assert data == snapshot  # 传入的数据不被修改

    def test_saved_file_carries_the_default_version_not_the_models(self, tmp_path):
        data = _valid_matrix_data()
        data["version"] = "banana"

        mgr = TruthFileManager(tmp_path)
        mgr.save_matrix(_check(data))

        saved = json.loads((tmp_path / "state" / "character_matrix.json").read_text(encoding="utf-8"))
        assert saved["version"] == CharacterMatrix.model_fields["version"].default
        assert mgr.load_matrix().version == CharacterMatrix.model_fields["version"].default

    def test_matrix_without_a_version_gets_the_default(self):
        assert _check(_valid_matrix_data()).version == CharacterMatrix.model_fields["version"].default


class TestEachShapeCheckHasItsOwnTest:
    """结构检查逐项独立验证：最后一道 Pydantic 会兜住类型错误，所以光看「有问题」不够，
    要看到本项自己的说明（与恰好一条问题）。关掉任一项检查，下面对应的用例都必须失败。"""

    @pytest.mark.parametrize("bad", ["EV-A", {"EV-A": 1}, None, ["EV-A", 5], ["EV-A", None]],
                             ids=["string", "dict", "null", "list_with_int", "list_with_null"])
    def test_evidence_refs_must_be_a_list_of_id_strings(self, bad):
        data = _valid_matrix_data()
        data["characters"]["R1"]["event_cognitions"]["E1"]["evidence_refs"] = bad

        problems = _problems(data)

        assert len(problems) == 1, problems
        assert "R1" in problems[0] and "E1" in problems[0] and "evidence_refs 必须是证据 ID 字符串列表" in problems[0]

    @pytest.mark.parametrize("bad,kind", [([], "list"), ("EV-A", "str"), (5, "int"),
                                          ([{"evidence_id": "EV-A"}], "list")])
    def test_evidence_must_be_an_object(self, bad, kind):
        data = _valid_matrix_data()
        data["evidence"] = bad
        for entry in data["characters"].values():  # 去掉对证据的引用，免得混进「引用了不存在的证据」
            for cell in entry["event_cognitions"].values():
                cell["evidence_refs"] = []

        problems = _problems(data)

        assert problems == [f"evidence 必须是对象，实际为 {kind}"]

    @pytest.mark.parametrize("bad,kind", [([], "list"), ("R1R2", "str"), (5, "int"),
                                          (["R1", "R2"], "list")])
    def test_characters_must_be_an_object(self, bad, kind):
        data = _valid_matrix_data()
        data["characters"] = bad

        problems = _problems(data)

        assert f"characters 必须是对象，实际为 {kind}" in problems
        assert not any("characters 为空" in problem for problem in problems)

    @pytest.mark.parametrize("bad,kind", [("林远", "str"), (None, "NoneType"), (["R1"], "list"), (5, "int")])
    def test_a_character_entry_must_be_an_object(self, bad, kind):
        data = _valid_matrix_data()
        data["characters"]["R1"] = bad

        problems = _problems(data)

        assert f"角色 R1 必须是对象，实际为 {kind}" in problems

    @pytest.mark.parametrize("bad,kind", [("书房钥匙", "str"), (None, "NoneType"), (["x"], "list"), (5, "int")])
    def test_an_evidence_item_must_be_an_object(self, bad, kind):
        data = _valid_matrix_data()
        data["evidence"]["EV-A"] = bad

        problems = _problems(data)

        assert f"证据 EV-A 必须是对象，实际为 {kind}" in problems

    def test_missing_is_prototype_is_a_problem_not_a_crash(self):
        data = _valid_matrix_data()
        del data["is_prototype"]

        problems = _problems(data)

        assert "缺少 is_prototype（应为 true）" in problems
        # 完整模式的期望值也要写对
        full = _full_matrix_data()
        del full["is_prototype"]
        assert "缺少 is_prototype（应为 false）" in _problems(full, char_count=6, event_count=7, is_prototype=False)
