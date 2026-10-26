"""expand 的类型化 system prompt 回归：矩阵步用机制设计师，其余用该类型的剧本作者（不用通用硬编码串）。"""
import pytest

from murder_wizard.prompts.loader import PromptLoader
from tests.expand_helpers import ScriptedLLM, make_prototype_project


@pytest.mark.parametrize("story_type", ["emotion", "reasoning", "fun", "horror", "mechanic", None])
def test_expand_uses_type_specific_system_prompts(tmp_path, story_type):
    runner, root = make_prototype_project(tmp_path)
    runner.state.story_type = story_type
    ScriptedLLM(runner, root)
    systems = []
    orig = runner.llm.complete.side_effect
    runner.llm.complete.side_effect = lambda p, system="", **k: (systems.append(system), orig(p, system=system))[1]
    assert runner.run_expand(accept_overwrite=True) is True
    loader, key = PromptLoader(), story_type or "mechanic"
    assert systems[0] == loader.system_mechanism_designer(key)
    assert all(s == loader.system_script_writer(key) for s in systems[1:])
    assert not any("你是一个专业的剧本杀作家，擅长创作" in s for s in systems)


# --- 审查修复回归：delta 中类型错误必须是 ExpandContractError，且坏响应不能留在缓存里 ---
import json as _json

from murder_wizard.wizard import expansion as _X
from tests.expand_helpers import delta_for, proto_matrix


@pytest.mark.parametrize("path,value", [
    (("new_characters", "R3", "name"), 123),
    (("new_characters", "R3", "name"), ["a"]),
    (("new_characters", "R3", "role"), 5),
    (("new_characters", "R3", "public_relationship"), {"x": 1}),
    (("new_events", "E4", "title"), 5),
    (("new_events", "E4", "summary"), ["s"]),
])
def test_merge_delta_wrong_types_are_contract_errors(tmp_path, path, value):
    _, root = make_prototype_project(tmp_path)
    proto = proto_matrix(root)
    d = delta_for(proto)
    node = d
    for k in path[:-1]:
        node = node[k]
    node[path[-1]] = value
    with pytest.raises(_X.ExpandContractError):
        _X.merge_delta(proto, _json.dumps(d, ensure_ascii=False))


def test_expand_wrong_type_response_is_not_replayed_from_cache(tmp_path):
    from murder_wizard.cli.expand_flow import ExpandFlow
    from murder_wizard.llm.client import LLMResponse
    runner, root = make_prototype_project(tmp_path)
    llm = ScriptedLLM(runner, root)
    bad = _json.loads(_json.dumps(llm.delta))
    bad["new_characters"]["R3"]["name"] = 123
    calls = []

    def comp(prompt, system="", **k):
        calls.append(1)
        return LLMResponse(content=_json.dumps(bad, ensure_ascii=False), tokens_used=1, cost=0.1, model="m")
    runner.llm.complete.side_effect = comp
    r1 = ExpandFlow(runner, accept_overwrite=True).run()
    n1 = len(calls)
    r2 = ExpandFlow(runner, accept_overwrite=True).run()
    assert r1.status != "APPLIED" and r2.status == r1.status
    assert "INTERNAL" not in str(r1.status).upper()
    assert len(calls) > n1  # 第二次必须重新调用模型，而不是重放坏缓存


def test_expand_refuses_before_any_model_call_when_session_json_missing(tmp_path):
    from murder_wizard.cli.expand_flow import ExpandFlow
    runner, root = make_prototype_project(tmp_path)
    llm = ScriptedLLM(runner, root)
    (root / "session.json").unlink()
    res = ExpandFlow(runner, accept_overwrite=True).run()
    assert res.status.value == "refused" and any("session.json" in p for p in res.problems)
    assert runner.llm.complete.call_count == 0 and res.cost == 0
