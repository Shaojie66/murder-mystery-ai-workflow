"""Web-adapted PhaseRunner that emits SSE events instead of using Rich console."""
import asyncio
import re
import json
from typing import Optional
from pathlib import Path
from io import StringIO

from rich.console import Console
from murder_wizard.wizard.session import SessionManager
from murder_wizard.wizard.state_machine import MurderWizardState, Stage


class SSEConsole(Console):
    """Rich Console replacement that emits SSE events to an asyncio.Queue.

    Inherits from Console to properly support Rich's Progress/Live components,
    but intercepts print() to emit SSE tokens instead of writing to stdout.
    """

    def __init__(self, queue: asyncio.Queue, *args, **kwargs):
        # Initialize Console with a dummy file to avoid real stdout
        super().__init__(file=StringIO(), *args, **kwargs)
        self._queue = queue

    def get_time(self) -> float:
        """Return current time for Rich Progress compatibility."""
        import time
        return time.time()

    def print(self, text: str | object = "", **kwargs) -> None:
        """Intercept print to emit as SSE token, not write to actual console."""
        # Convert to string and strip markup
        if hasattr(text, '__rich_console__'):
            # It's a Rich renderable - render it
            from rich.console import RenderResult
            from io import StringIO
            with StringIO() as f:
                console = Console(file=f, force_terminal=False)
                console.print(text)
                clean = f.getvalue()
        else:
            clean = self._strip_rich(str(text))

        if clean and clean.strip():
            self._queue.put_nowait({"event": "token", "data": {"content": clean.strip(), "delta": True}})

    def _strip_rich(self, text: str) -> str:
        """Remove Rich ANSI/style markup from text."""
        # Skip empty lines from progress spinners
        if not text.strip():
            return ""
        # Remove ANSI color codes
        ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
        clean = ansi_escape.sub('', text)
        # 用 Rich 自己解析标记：真标记被去掉，rich.markup.escape 转义过的 [E4]、[1, 2] 按字面保留
        from rich.errors import MarkupError
        from rich.text import Text
        try:
            clean = Text.from_markup(clean).plain
        except MarkupError:
            pass
        return clean.strip()


class ProgressTracker:
    """Track Rich Progress spinner output and emit progress events."""

    def __init__(self, queue: asyncio.Queue):
        self._queue = queue
        self._current_task = ""

    def set_task(self, task: str) -> None:
        """Set current task description."""
        self._current_task = task
        self._queue.put_nowait({
            "event": "progress",
            "data": {"step": task, "percent": 0}
        })

    def complete(self) -> None:
        """Mark current task complete."""
        self._queue.put_nowait({
            "event": "progress",
            "data": {"step": self._current_task, "percent": 100}
        })


class PhaseRunnerWeb:
    """Web-adapted PhaseRunner that uses SSE for output.

    Wraps the existing PhaseRunner class, replacing its Rich console
    output with SSE events via an asyncio.Queue.
    """

    def __init__(self, project_name: str, sse_queue: asyncio.Queue):
        self.project_name = project_name
        self.sse_queue = sse_queue
        self.sse_console = SSEConsole(sse_queue)
        self.progress = ProgressTracker(sse_queue)
        self._cancelled = False

        # Paths
        self.project_path = Path.home() / ".murder-wizard" / "projects" / project_name
        self.session = SessionManager(project_name)

        # Track cost
        self._total_cost = 0.0
        self._total_tokens = 0

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        self._cancelled = True

    def emit(self, event: str, data: dict) -> None:
        """Emit an SSE event."""
        if not self._cancelled:
            self.sse_queue.put_nowait({"event": event, "data": data})

    def _patch_runner(self, runner):
        """Patch a PhaseRunner instance to emit cost events via SSE."""
        original = runner._call_llm

        def patched(prompt: str, system: str = "", operation: str = "llm_call"):
            # 缓存命中不产生花费（CLI 与 cost.log 都记 0）：先无副作用地探测，再调用
            try:
                hit = runner._cache.get(operation, prompt, system, runner.llm.model) is not None
            except Exception:  # noqa: BLE001
                hit = False
            result = original(prompt, system, operation)
            if result:
                cost, tokens = (0.0, 0) if hit else (result.cost, result.tokens_used)
                self._total_cost += cost
                self._total_tokens += tokens
                self.emit("cost", {"tokens": tokens, "cost": cost, "total_cost": self._total_cost, "cached": hit})
            return result

        runner._call_llm = patched
        runner.console.print = self.sse_console.print

    async def run_phase(self, stage: int, analyze: bool = False) -> bool:
        """Run a single phase (1-8). Returns success status."""
        from murder_wizard.cli.phase_runner import PhaseRunner

        state = self.session.load()
        if state is None:
            self.emit("error", {"message": "Project session not found"})
            return False

        self.emit("start", {"phase": stage, "stage": f"stage_{stage}_*" if stage < 10 else str(stage)})

        # Create the real PhaseRunner but capture its LLM calls
        # We wrap _call_llm to intercept costs
        runner = PhaseRunner(self.session, state, self.sse_console)
        self._patch_runner(runner)

        try:
            if stage == 4 and analyze:
                success = runner.run_stage_4_analyze()
            elif stage == 1:
                success = runner.run_stage_1()
            elif stage == 2:
                success = runner.run_stage_2()
            elif stage == 3:
                success = runner.run_stage_3()
            elif stage == 4:
                success = runner.run_stage_4()
            elif stage == 5:
                success = runner.run_stage_5()
            elif stage == 6:
                success = runner.run_stage_6()
            elif stage == 7:
                success = runner.run_stage_7()
            elif stage == 8:
                success = runner.run_stage_8()
            else:
                self.emit("error", {"message": f"Invalid stage: {stage}"})
                return False

            # Reload session to get updated state
            updated_state = self.session.load()
            artifacts = self._get_artifacts(updated_state)

            self.emit("stage_complete", {
                "phase": stage,
                "success": success,
                "artifacts": artifacts,
                "total_cost": self._total_cost,
                "total_tokens": self._total_tokens,
            })
            return success

        except Exception as e:
            self.emit("error", {"message": str(e), "type": type(e).__name__})
            return False

    async def run_audit(self, force: bool = False) -> bool:
        """Run the read-only audit; success is True only for status passed."""
        from murder_wizard.cli.phase_runner import PhaseRunner

        state = self.session.load()
        if state is None:
            self.emit("error", {"message": "Project session not found"})
            return False

        runner = PhaseRunner(self.session, state, self.sse_console)
        self._patch_runner(runner)

        try:
            outcome = runner.run_audit_checked(force=force)
            success = bool(outcome)
            payload = outcome.to_summary_dict()
            payload.update({"success": success, "total_cost": self._total_cost})
            self.emit("audit_complete", payload)
            return success
        except Exception as e:
            self.emit("error", {"message": str(e), "type": type(e).__name__})
            return False

    async def run_expand(self, accept_overwrite: bool = False) -> bool:
        """Run prototype expansion to full version."""
        from murder_wizard.cli.phase_runner import PhaseRunner

        state = self.session.load()
        if state is None:
            self.emit("error", {"message": "Project session not found"})
            return False

        runner = PhaseRunner(self.session, state, self.sse_console)
        self._patch_runner(runner)

        try:
            success = runner.run_expand(accept_overwrite=accept_overwrite)
            res = runner.last_expand_result
            self.emit("expand_complete", {
                "success": success,
                "status": res.status.value if res else "failed_internal",
                "problems": list(res.problems) if res else [],
                "failed_step": res.failed_step if res else None,
                "backups": dict(res.backups) if res else {},
                "total_cost": self._total_cost,
            })
            return success
        except Exception as e:
            self.emit("error", {"message": str(e), "type": type(e).__name__})
            return False

    def _get_artifacts(self, state: Optional[MurderWizardState]) -> list[str]:
        """Return list of artifact filenames that exist."""
        if state is None:
            return []
        artifacts = []
        project_files = list(self.project_path.glob("*.md")) + list(self.project_path.glob("*.pdf"))
        return [f.name for f in project_files]
