"""输出上限：按次指定 max_tokens、stop_reason 截断信号、被截断的响应不缓存且明确失败。"""
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from murder_wizard.llm.cache import LLMCache
from murder_wizard.llm.client import (
    DEFAULT_MAX_TOKENS, LONG_OUTPUT_MAX_TOKENS, ClaudeAdapter, LLMResponse, MiniMaxAdapter,
    OllamaAdapter, OpenAIAdapter,
)
from murder_wizard.wizard import expansion as X
from tests.expand_helpers import OPS, ScriptedLLM, make_prototype_project, snapshot_tree


def test_long_limit_is_above_the_old_default_and_truncated_reasons():
    assert LONG_OUTPUT_MAX_TOKENS > DEFAULT_MAX_TOKENS == 4096
    for r in ("max_tokens", "length"):
        assert LLMResponse("x", 1, 0.0, "m", stop_reason=r).truncated
    for r in (None, "end_turn", "stop"):
        assert not LLMResponse("x", 1, 0.0, "m", stop_reason=r).truncated
    assert not LLMResponse("x", 1, 0.0, "m").truncated  # 旧调用方不传 stop_reason：默认完整


def _anthropic_reply(stop):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text="正文")], stop_reason=stop,
                           usage=SimpleNamespace(input_tokens=10, output_tokens=5))


def _openai_reply(finish):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="正文"), finish_reason=finish)],
                           usage=SimpleNamespace(total_tokens=15))


@pytest.mark.parametrize("cls,make,stop,client_attr", [
    (ClaudeAdapter, _anthropic_reply, "max_tokens", "messages"),
    (MiniMaxAdapter, _anthropic_reply, "max_tokens", "messages"),
    (OpenAIAdapter, _openai_reply, "length", "chat"),
    (OllamaAdapter, _openai_reply, "length", "chat"),
])
def test_adapters_forward_max_tokens_and_report_stop_reason(cls, make, stop, client_attr):
    ad = object.__new__(cls)
    ad.model = "m"
    create = MagicMock(side_effect=[make(stop), make("end_turn" if client_attr == "messages" else "stop")])
    ad.client = SimpleNamespace(messages=SimpleNamespace(create=create),
                                chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    r = ad.complete("p", system="s", max_tokens=8192)
    assert create.call_args.kwargs["max_tokens"] == 8192 and r.truncated and r.stop_reason == stop
    r2 = ad.complete("p", system="s")  # 不传：沿用默认上限
    assert create.call_args.kwargs["max_tokens"] == DEFAULT_MAX_TOKENS and not r2.truncated


def test_cache_key_depends_on_max_tokens_and_round_trips_stop_reason(tmp_path):
    c = LLMCache(tmp_path)
    c.set("op", "p", "s", "m", LLMResponse("a", 1, 0.0, "m", stop_reason="end_turn"), max_tokens=8192)
    assert c.get("op", "p", "s", "m") is None  # 默认上限的键不会命中长上限的结果
    assert c.get("op", "p", "s", "m", max_tokens=4096) is None
    hit = c.get("op", "p", "s", "m", max_tokens=8192)
    assert hit.content == "a" and hit.stop_reason == "end_turn"
    assert c.invalidate("op", "p", "s", "m", max_tokens=8192) and c.get("op", "p", "s", "m", max_tokens=8192) is None


def _runner(tmp_path):
    runner, root = make_prototype_project(tmp_path)
    return runner, root


def test_call_llm_passes_limit_only_when_asked_and_never_caches_truncated(tmp_path):
    runner, _ = _runner(tmp_path)
    seen = []
    replies = iter([LLMResponse("半截", 1, 0.0, "mock-model", stop_reason="max_tokens"),
                    LLMResponse("完整", 1, 0.0, "mock-model", stop_reason="end_turn"),
                    LLMResponse("默认", 1, 0.0, "mock-model")])

    def complete(prompt, system="", **kw):
        seen.append(kw)
        return next(replies)
    runner.llm.complete.side_effect = complete
    a = runner._call_llm("p", system="s", operation="op", max_tokens=LONG_OUTPUT_MAX_TOKENS)
    assert a.truncated and runner._cache.stats()["entries"] == 0  # 截断的结果不进缓存
    b = runner._call_llm("p", system="s", operation="op", max_tokens=LONG_OUTPUT_MAX_TOKENS)
    assert b.content == "完整" and len(seen) == 2  # 重试重新调用了模型，没有重放半截结果
    assert seen[0] == {"max_tokens": LONG_OUTPUT_MAX_TOKENS}
    c = runner._call_llm("p2", system="s", operation="op")
    assert c.content == "默认" and seen[2] == {}  # 默认调用不带 max_tokens 关键字


def test_stage_2_truncated_dm_manual_fails_closed_without_writing_or_caching(tmp_path):
    from tests.test_phase_runner import _make_runner, _matrix_data, _response, _stage_2_state
    runner = _make_runner(tmp_path, state=_stage_2_state(is_prototype=True))
    root = runner.session.project_path
    (root / "mechanism.md").write_text("# 机制", encoding="utf-8")
    matrix = "```json\n" + json.dumps(_matrix_data(), ensure_ascii=False) + "\n```"
    calls = []

    def complete(prompt, system="", **kw):
        calls.append(kw.get("max_tokens"))
        n = len(calls)
        text = matrix if n == 1 else f"# 第{n}步内容"
        return LLMResponse(text, 1, 0.0, "mock-model", stop_reason="max_tokens" if n == 5 else "end_turn")
    runner.llm.complete.side_effect = complete
    assert runner.run_stage_2() is False
    assert calls == [LONG_OUTPUT_MAX_TOKENS] * 5  # Q1-Q5 都用长上限；Q6 没有被调用
    assert not (root / "dm_manual.md").exists() and not (root / "endings.md").exists()
    assert "截断" in runner.console.export_text()
    assert runner.session.load().current_stage != runner.state.current_stage.__class__.STAGE_2_SCRIPT


def test_stage_2_truncated_matrix_is_rejected_before_any_write(tmp_path):
    from tests.test_phase_runner import _make_runner, _matrix_data, _stage_2_state
    runner = _make_runner(tmp_path, state=_stage_2_state(is_prototype=True))
    root = runner.session.project_path
    (root / "mechanism.md").write_text("# 机制", encoding="utf-8")
    good = "```json\n" + json.dumps(_matrix_data(), ensure_ascii=False) + "\n```"
    runner.llm.complete.side_effect = lambda p, system="", **kw: LLMResponse(good, 1, 0.0, "mock-model", stop_reason="length")
    assert runner.run_stage_2() is False  # 即使恰好是一份合法 JSON，被截断的响应也不被信任
    assert not (root / "information_matrix.md").exists()
    assert "截断" in runner.console.export_text()


@pytest.mark.parametrize("op", ["expand_matrix", "expand_a_R3", "expand_dm", "expand_endings"])
def test_expand_truncation_signal_fails_validation_and_leaves_work_untouched(tmp_path, op):
    runner, root = make_prototype_project(tmp_path)
    before = snapshot_tree(root)
    llm = ScriptedLLM(runner, root, truncate={op})
    assert runner.run_expand(accept_overwrite=True) is False
    res = runner.last_expand_result
    assert res.status is X.ExpandStatus.FAILED_VALIDATION and res.failed_step == op
    assert "stop_reason=max_tokens" in "".join(res.problems)
    assert snapshot_tree(root) == before and llm.ops[-1] == op
    assert all(m == LONG_OUTPUT_MAX_TOKENS for m in llm.max_tokens_seen)  # 扩写每一步都用长上限
    # 截断的响应没有进缓存：重跑会重新调用模型
    llm.truncate.clear()
    n = len(llm.ops)
    assert runner.run_expand(accept_overwrite=True) is True and llm.ops[n:][0] == op
