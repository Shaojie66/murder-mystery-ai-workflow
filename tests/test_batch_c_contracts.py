"""批次 C 合同测试：SSE/任务状态、包导入、PDF 判定、resume 持久化、init 类型。"""
import asyncio
import json
import re
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from core.sse_manager import SSEManager  # 与路由实际使用的是同一条导入路径


# ── 任务对象与事件合同（单元） ─────────────────────────────────────────

def test_manager_try_start_is_exclusive_and_release_frees():
    async def go():
        m = SSEManager()
        a = m.try_start("p")
        assert a is not None and m.try_start("p") is None and m.is_running("p")
        assert m.request_cancel("p") and a.cancel_requested and m.is_running("p")  # 取消不释放写锁
        m.release("p", a)
        assert not m.is_running("p") and m.try_start("p") is not None
        assert m.request_cancel("nope") is False
    asyncio.run(go())


def test_events_are_json_and_queue_is_drained_before_exit_even_from_threads():
    async def go():
        m = SSEManager()
        c = m.try_start("p")

        def worker():
            for i in range(50):
                c.put("token", {"i": i, "t": "中文"})
            c.put("end", {"status": "success", "success": True})
            c.close()
        await asyncio.to_thread(worker)
        got = [e async for e in c.event_stream()]
        assert [e["event"] for e in got][-1] == "end" and len(got) == 51
        assert all(isinstance(e["data"], str) and json.loads(e["data"]) is not None for e in got)
        assert json.loads(got[-1]["data"])["success"] is True
        c.put("late", {})  # 关闭后不再接受
    asyncio.run(go())


def test_package_does_not_import_through_machine_specific_symlinks():
    root = Path(__file__).parent.parent
    offenders = []
    for base in (root / "murder_wizard", root / "murder_wizard_web" / "backend"):
        for p in base.rglob("*.py"):
            if p.is_symlink() or any(part.is_symlink() for part in p.parents if part.is_relative_to(root)):
                continue
            if re.search(r"murder_wizard\.(core|api)\b", p.read_text(encoding="utf-8")):
                offenders.append(str(p.relative_to(root)))
    assert not offenders, offenders


# ── HTTP 跨层合同（真实路由 + 模拟引擎） ───────────────────────────────

@pytest.fixture
def auth_headers():
    from core.auth import encode_token
    return {"Authorization": f"Bearer {encode_token('test-user')}"}


@pytest.fixture
def client_and_project(auth_headers):
    """HOME 已被 conftest 隔离到临时目录；直接建一个最小作品，不经过模型。"""
    from murder_wizard.wizard.session import SessionManager
    from murder_wizard.wizard.state_machine import MurderWizardState
    from murder_wizard_web.backend.main import app
    SessionManager("ssec").save(MurderWizardState(project_name="ssec", story_type="mechanic", is_prototype=True, outline="# o"))
    with TestClient(app) as client:
        yield client, "ssec", auth_headers


def _events(resp):
    out, ev = [], None
    for line in resp.iter_lines():
        if line.startswith("event:"):
            ev = line.split(":", 1)[1].strip()
        elif line.startswith("data:") and ev:
            out.append((ev, json.loads(line.split(":", 1)[1].strip())))
            ev = None
    return out


def test_run_phase_streams_json_events_and_terminal_end_success(client_and_project):
    client, name, h = client_and_project
    import core.phase_runner_web as W

    async def fake(self, stage, analyze=False):
        self.emit("stage_complete", {"phase": stage, "success": True})
        return True
    with patch.object(W.PhaseRunnerWeb, "run_phase", fake):
        with client.stream("POST", f"/api/projects/{name}/phases/1/run", json={}, headers=h) as r:
            ev = _events(r)
    assert ev[-1] == ("end", {"status": "success", "success": True, "cancel_requested": False})
    assert ("stage_complete", {"phase": 1, "success": True}) in ev
    assert client.get(f"/api/projects/{name}/phases/1/status", headers=h).json()["running"] is False


@pytest.mark.parametrize("mode,status", [("false", "failed"), ("raise", "failed")])
def test_failed_or_raising_run_ends_with_failed_not_success(client_and_project, mode, status):
    client, name, h = client_and_project
    import core.phase_runner_web as W

    async def fake(self, stage, analyze=False):
        if mode == "raise":
            raise RuntimeError("引擎崩了")
        return False
    with patch.object(W.PhaseRunnerWeb, "run_phase", fake):
        with client.stream("POST", f"/api/projects/{name}/phases/2/run", json={}, headers=h) as r:
            assert r.status_code == 200  # HTTP 200 不代表业务成功
            ev = _events(r)
    assert ev[-1][0] == "end" and ev[-1][1]["status"] == status and ev[-1][1]["success"] is False
    if mode == "raise":
        assert any(e == "error" and "引擎崩了" in d["message"] for e, d in ev)


def test_long_call_does_not_block_status_and_cancel_is_only_a_request(client_and_project):
    client, name, h = client_and_project
    import threading
    import core.phase_runner_web as W
    gate = threading.Event()

    async def slow(self, stage, analyze=False):
        gate.wait(5)
        return True
    seen = {}

    def poll():
        time.sleep(0.3)
        seen["status"] = client.get(f"/api/projects/{name}/phases/1/status", headers=h).json()
        seen["dup"] = client.post(f"/api/projects/{name}/phases/1/run", json={}, headers=h).status_code
        seen["cancel"] = client.post(f"/api/projects/{name}/phases/1/cancel", headers=h).json()
        seen["after_cancel"] = client.get(f"/api/projects/{name}/phases/1/status", headers=h).json()
        gate.set()
    t = threading.Thread(target=poll)
    with patch.object(W.PhaseRunnerWeb, "run_phase", slow):
        t.start()
        with client.stream("POST", f"/api/projects/{name}/phases/1/run", json={}, headers=h) as r:
            ev = _events(r)
    t.join()
    assert seen["status"]["running"] is True and seen["dup"] == 409
    assert seen["cancel"]["cancel_requested"] is True and seen["cancel"]["stopped"] is False
    assert seen["after_cancel"]["running"] is True  # 取消不释放写锁
    # 取消请求不能抹掉已完成并写盘的真实结果
    assert ev[-1][1] == {"status": "success", "success": True, "cancel_requested": True}
    assert client.get(f"/api/projects/{name}/phases/1/status", headers=h).json()["running"] is False


def test_invalid_stage_and_missing_project_are_rejected_without_running(client_and_project):
    client, name, h = client_and_project
    assert client.post(f"/api/projects/{name}/phases/9/run", json={}, headers=h).status_code == 400
    assert client.post("/api/projects/nonexistent/phases/1/run", json={}, headers=h).status_code == 404
    assert client.post("/api/projects/nonexistent/audit", headers=h).status_code == 404


def test_analyze_flag_reaches_stage_4_analyze_path(tmp_path):
    from murder_wizard_web.backend.core.phase_runner_web import PhaseRunnerWeb
    conn = MagicMock()
    r = PhaseRunnerWeb("demo", conn)
    runner = MagicMock()
    runner.run_stage_4_analyze.return_value = True
    r.session = MagicMock()
    with patch("murder_wizard.cli.phase_runner.PhaseRunner", return_value=runner):
        assert asyncio.run(r.run_phase(4, analyze=True)) is True
        runner.run_stage_4_analyze.assert_called_once()
        runner.run_stage_4.assert_not_called()
        asyncio.run(r.run_phase(4, analyze=False))
        runner.run_stage_4.assert_called_once()


def test_expand_endpoint_without_accept_overwrite_fails_before_model(client_and_project):
    client, name, h = client_and_project
    with client.stream("POST", f"/api/projects/{name}/expand", headers=h) as r:
        ev = _events(r)
    done = [d for e, d in ev if e == "expand_complete"]
    assert done and done[0]["success"] is False and ev[-1][1]["success"] is False


# ── R10：PDF 判定、resume 持久化、init 类型 ─────────────────────────────

def _runner(tmp_path):
    from tests.test_phase_runner import _make_runner
    return _make_runner(tmp_path)


def test_stage_6_fails_when_a_required_pdf_is_missing_and_does_not_advance(tmp_path):
    from murder_wizard.wizard.state_machine import Stage
    runner = _runner(tmp_path)
    (runner.session.project_path / "characters.md").write_text("# c", encoding="utf-8")
    gen = MagicMock()
    gen.check_print_ready.return_value = (True, [])
    (runner.session.project_path / "script.pdf").write_bytes(b"%PDF")
    gen.generate_script_pdf.return_value = str(runner.session.project_path / "script.pdf")
    gen.generate_clue_cards.side_effect = RuntimeError("字体缺失")
    with patch("murder_wizard.print.pdf_gen.PDFGenerator", return_value=gen):
        assert runner.run_stage_6() is False
    assert runner.session.load().current_stage != Stage.STAGE_6_PRINT
    assert "印刷文件生成完成" not in runner.console.export_text()
    # 返回了路径但文件不存在，同样失败
    gen.generate_clue_cards.side_effect = None
    gen.generate_clue_cards.return_value = str(runner.session.project_path / "不存在.pdf")
    with patch("murder_wizard.print.pdf_gen.PDFGenerator", return_value=gen):
        assert runner.run_stage_6() is False


def test_resume_persists_recovered_state(tmp_path):
    from rich.console import Console
    from murder_wizard.cli.commands import resume_project
    from murder_wizard.wizard.session import SessionManager
    s = SessionManager("rec", base_path=str(tmp_path))
    s.ensure_project_dir()
    (s.project_path / "mechanism.md").write_text("# m", encoding="utf-8")
    s.session_file.write_text("{损坏", encoding="utf-8")
    assert s.load() is None
    resume_project(s, Console(record=True))
    assert s.load() is not None  # 恢复结果已落盘，重新载入可用


def test_init_type_choices_are_the_five_real_story_types():
    import click
    import murder_wizard.cli as cli
    opt = next(p for p in cli.init.params if p.name == "story_type")
    assert set(opt.type.choices) == {"emotion", "reasoning", "fun", "horror", "mechanic"}


# --- 审查修复回归 ---
def test_sse_console_keeps_escaped_bracket_text_and_strips_real_markup():
    from rich.markup import escape
    from murder_wizard_web.backend.core.phase_runner_web import SSEConsole
    c = SSEConsole(asyncio.Queue())
    assert c._strip_rich(escape("缺少标签 [E4]，矩阵 [1, 2]")) == "缺少标签 [E4]，矩阵 [1, 2]"
    assert c._strip_rich(escape("矩阵键 [R1][E2]")) == "矩阵键 [R1][E2]"
    assert c._strip_rich("[bold red]失败[/bold red]：" + escape("[red]x[/red]")) == "失败：[red]x[/red]"


def test_web_cost_events_do_not_count_cache_hits():
    from murder_wizard.llm.client import LLMResponse
    from murder_wizard_web.backend.core.phase_runner_web import PhaseRunnerWeb
    q = asyncio.Queue()
    r = PhaseRunnerWeb("demo", q)
    runner = MagicMock()
    resp = LLMResponse(content="x", tokens_used=10, cost=0.5, model="m")
    runner._call_llm = lambda p, s="", o="op": resp
    runner.llm.model = "m"
    runner._cache.get.side_effect = [None, resp]  # 第一次未命中，第二次命中
    r._patch_runner(runner)
    runner._call_llm("a")
    runner._call_llm("a")
    assert r._total_cost == 0.5 and r._total_tokens == 10
    costs = [q.get_nowait()["data"] for _ in range(2)]
    assert [c["cost"] for c in costs] == [0.5, 0.0]


def test_init_explicit_type_and_mode_are_not_asked_or_overridden():
    from click.testing import CliRunner
    import murder_wizard.cli as cli
    seen = {}

    def fake(session, state, console, ask_mode=True, ask_type=True):
        seen.update(type=state.story_type, proto=state.is_prototype, ask_mode=ask_mode, ask_type=ask_type)
    with patch("murder_wizard.cli.wizard_tui.run_init_wizard", fake):
        assert CliRunner().invoke(cli.main, ["init", "demo", "--type", "horror", "--full"]).exit_code == 0
        assert seen == {"type": "horror", "proto": False, "ask_mode": False, "ask_type": False}
        seen.clear()
        assert CliRunner().invoke(cli.main, ["init", "demo"]).exit_code == 0
        assert seen["ask_mode"] is True and seen["ask_type"] is True


def test_init_wizard_type_menu_offers_only_real_story_types():
    from rich.console import Console
    from murder_wizard.cli import wizard_tui as T
    from murder_wizard.prompts.loader import PromptLoader
    from murder_wizard.wizard.state_machine import MurderWizardState
    answers = iter(["2", "2"])  # 完整模式、推理本
    state = MurderWizardState(project_name="w", story_type="mechanic", is_prototype=True)

    class Stop(Exception):
        pass

    def ask(prompt, *a, **k):
        if "创作模式" in prompt or "剧本类型" in prompt:
            return next(answers)
        raise Stop
    with patch.object(T.Prompt, "ask", side_effect=ask), patch.object(T.signal, "signal"):
        with pytest.raises(Stop):
            T.run_init_wizard(MagicMock(), state, Console(record=True))
    assert state.story_type == "reasoning" and state.is_prototype is False
    loader = PromptLoader()
    assert loader.system_script_writer(state.story_type) != loader.system_script_writer("puzzle")


def test_cancel_requested_and_run_failed_is_cancelled(client_and_project):
    client, name, h = client_and_project
    import core.phase_runner_web as W

    async def fake(self, stage, analyze=False):
        self.sse_queue.cancel_requested = True
        return False
    with patch.object(W.PhaseRunnerWeb, "run_phase", fake):
        with client.stream("POST", f"/api/projects/{name}/phases/1/run", json={}, headers=h) as r:
            ev = _events(r)
    assert ev[-1][1] == {"status": "cancelled", "success": False, "cancel_requested": True}


def test_phase_command_exits_nonzero_when_stage_fails(tmp_path):
    from click.testing import CliRunner
    import murder_wizard.cli as cli
    from murder_wizard.wizard.session import SessionManager
    from murder_wizard.wizard.state_machine import MurderWizardState
    SessionManager("exitp").save(MurderWizardState(project_name="exitp", story_type="mechanic", is_prototype=True, outline="# o"))
    for ret, code in ((False, 1), (True, 0)):
        runner = MagicMock()
        runner.run_stage_6.return_value = ret
        with patch("murder_wizard.cli.commands.PhaseRunner", return_value=runner):
            res = CliRunner().invoke(cli.main, ["phase", "exitp", "6"])
        assert res.exit_code == code, res.output
    # 阶段抛异常同样非零；项目不存在也非零
    runner.run_stage_6.side_effect = RuntimeError("PDF 炸了")
    with patch("murder_wizard.cli.commands.PhaseRunner", return_value=runner):
        assert CliRunner().invoke(cli.main, ["phase", "exitp", "6"]).exit_code == 1
    assert CliRunner().invoke(cli.main, ["phase", "nosuchproj", "1"]).exit_code == 1


def test_sse_manager_is_a_single_instance_across_routers_and_modules():
    import sys
    import api.phases as phases
    import api.projects as projects
    import core.sse_manager as sm
    assert phases.sse_manager is projects.sse_manager is sm.sse_manager
    assert phases.sse_manager.__class__ is SSEManager
    dupes = [n for n, m in sys.modules.items() if n.endswith("core.sse_manager") and m is not sm]
    assert not dupes, dupes  # 不允许出现第二个模块对象（别名导入路径会得到第二个管理器）


def test_phase_page_sends_analyze_flag_for_stage_4():
    src = Path(__file__).parent.parent / "murder_wizard_web" / "frontend" / "src"
    api = (src / "api" / "phases.ts").read_text(encoding="utf-8")
    page = (src / "pages" / "PhaseExecution.tsx").read_text(encoding="utf-8")
    assert "JSON.stringify({ analyze: false })" not in api and "JSON.stringify({ analyze })" in api
    assert "analyze: mode === 'phase' && stageNum === 4 && analyze" in page
    assert "setAnalyze(e.target.checked)" in page
