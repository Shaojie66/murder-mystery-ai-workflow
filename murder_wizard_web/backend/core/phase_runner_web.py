"""Web-adapted PhaseRunner that emits SSE events instead of using Rich console."""
import asyncio
import re
import json
from typing import Optional
from pathlib import Path

from murder_wizard.wizard.session import SessionManager
from murder_wizard.wizard.state_machine import MurderWizardState, Stage
from murder_wizard.wizard.truth_files import TruthFileManager


class SSEConsole:
    """Console replacement that emits SSE events to an asyncio.Queue."""

    def __init__(self, queue: asyncio.Queue):
        self._queue = queue
        self._buffer = ""
        self._get_time = __import__('time').time

    def get_time(self) -> float:
        """Return current time for Rich Progress compatibility."""
        return self._get_time()

    def log(self, text: str, **kwargs) -> None:
        """Rich log method - just print to avoid Rich-specific behavior."""
        self.print(text, **kwargs)

    def set_live(self, *args, **kwargs) -> None:
        """Rich set_live - no-op for SSE console."""
        pass

    def clear_live(self, *args, **kwargs) -> None:
        """Rich clear_live - no-op for SSE console."""
        pass

    def print(self, text: str, **kwargs) -> None:
        """Strip Rich markup and send as token event."""
        # Remove Rich markup: [color], [/color], bold markers, etc.
        clean = self._strip_rich(text)
        if clean:
            self._queue.put_nowait({"event": "token", "data": {"content": clean, "delta": True}})

    def _strip_rich(self, text: str) -> str:
        """Remove Rich ANSI/style markup from text."""
        # Skip empty lines from progress spinners
        if not text.strip():
            return ""
        # Remove ANSI color codes
        ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
        clean = ansi_escape.sub('', text)
        # Remove Rich markup like [bold], [/bold], [cyan], etc.
        rich_markup = re.compile(r'\[/?(?:bold|italic|red|green|yellow|blue|magenta|cyan|white|dim|bright|on)\]')
        clean = rich_markup.sub('', clean)
        # Remove other Rich markup patterns
        clean = re.sub(r'\[/?[^]]+\]', '', clean)
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

    def _emit_cost(self, tokens: int, cost: float) -> None:
        """Emit cost update."""
        self._total_cost += cost
        self._total_tokens += tokens
        self.emit("cost", {"tokens": tokens, "cost": cost, "total_cost": self._total_cost})

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

        # Monkey-patch the _call_llm to intercept cost events
        original_call_llm = runner._call_llm

        async def patched_call_llm(prompt: str, system: str = "", operation: str = "llm_call"):
            result = await original_call_llm(prompt, system, operation)
            if result:
                self._emit_cost(result.tokens_used, result.cost)
            return result

        runner._call_llm = patched_call_llm

        # Monkey-patch console.print to emit tokens
        original_console_print = runner.console.print
        runner.console.print = self.sse_console.print

        try:
            if stage == 1:
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

    async def run_audit(self) -> bool:
        """Run the full audit with Reviser auto-fix loop."""
        from murder_wizard.cli.phase_runner import PhaseRunner

        state = self.session.load()
        if state is None:
            self.emit("error", {"message": "Project session not found"})
            return False

        runner = PhaseRunner(self.session, state, self.sse_console)

        # Monkey-patch _call_llm to track costs
        original_call_llm = runner._call_llm

        async def patched_call_llm(prompt: str, system: str = "", operation: str = "llm_call"):
            result = await original_call_llm(prompt, system, operation)
            if result:
                self._emit_cost(result.tokens_used, result.cost)
            return result

        runner._call_llm = patched_call_llm
        runner.console.print = self.sse_console.print

        try:
            success = runner.run_audit()
            self.emit("audit_complete", {
                "success": success,
                "total_cost": self._total_cost,
            })
            return success
        except Exception as e:
            self.emit("error", {"message": str(e), "type": type(e).__name__})
            return False

    async def run_expand(self) -> bool:
        """Run prototype expansion to full version."""
        from murder_wizard.cli.phase_runner import PhaseRunner

        state = self.session.load()
        if state is None:
            self.emit("error", {"message": "Project session not found"})
            return False

        runner = PhaseRunner(self.session, state, self.sse_console)

        original_call_llm = runner._call_llm

        async def patched_call_llm(prompt: str, system: str = "", operation: str = "llm_call"):
            result = await original_call_llm(prompt, system, operation)
            if result:
                self._emit_cost(result.tokens_used, result.cost)
            return result

        runner._call_llm = patched_call_llm
        runner.console.print = self.sse_console.print

        try:
            success = runner.run_expand()
            self.emit("expand_complete", {
                "success": success,
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
