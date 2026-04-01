"""Phase execution API with SSE streaming."""
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from core.sse_manager import sse_manager
from core.phase_runner_web import PhaseRunnerWeb

router = APIRouter(prefix="/api/projects/{project_name}", tags=["phases"])


class RunPhaseRequest(BaseModel):
    analyze: bool = False


@router.get("/phases/{stage}/status")
async def phase_status(project_name: str, stage: int):
    """Check if a phase is currently running."""
    return {"running": sse_manager.is_running(project_name)}


async def phase_event_generator(project_name: str, stage: int, analyze: bool):
    """SSE generator for phase execution."""
    from murder_wizard.core.sse_manager import sse_manager

    queue: asyncio.Queue = asyncio.Queue()

    # Create SSE connection
    conn = await sse_manager.create_connection(project_name)

    # Start the phase runner in background
    runner = PhaseRunnerWeb(project_name, queue)

    async def run_and_emit():
        await runner.run_phase(stage, analyze)
        await sse_manager.cancel_connection(project_name)

    task = asyncio.create_task(run_and_emit())

    # Stream events from the queue
    try:
        while True:
            event = await asyncio.wait_for(queue.get(), timeout=60)
            if event is None:
                break
            yield {"event": event["event"], "data": event["data"]}
    except asyncio.TimeoutError:
        yield {"event": "keepalive", "data": {}}
    except GeneratorExit:
        pass
    finally:
        if not task.done():
            runner.cancel()
            task.cancel()


@router.post("/phases/{stage}/run")
async def run_phase(project_name: str, stage: int, req: RunPhaseRequest):
    """Run a phase with SSE streaming output."""
    from murder_wizard.core.sse_manager import sse_manager

    if sse_manager.is_running(project_name):
        raise HTTPException(status_code=409, detail="A phase is already running for this project")

    async def event_generator():
        # Create connection to get its queue
        conn = await sse_manager.create_connection(project_name)
        # Use the connection's queue for the runner so events flow correctly
        runner = PhaseRunnerWeb(project_name, conn.queue)
        task_result: BaseException | None = None

        async def run_and_emit():
            nonlocal task_result
            try:
                await runner.run_phase(stage, req.analyze)
            except BaseException as e:
                task_result = e
            finally:
                await sse_manager.cancel_connection(project_name)

        task = asyncio.create_task(run_and_emit())

        try:
            # Stream events from the connection's queue
            async for event in conn.event_stream():
                yield event
        except (asyncio.CancelledError, GeneratorExit):
            if not task.done():
                runner.cancel()
                task.cancel()
        finally:
            # Await task to avoid unobserved exception
            if not task.done():
                runner.cancel()
                task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except BaseException as e:
                if task_result is None:
                    task_result = e
            if task_result is not None:
                yield {"event": "error", "data": {"message": str(task_result)}}

    return EventSourceResponse(event_generator())


@router.post("/expand")
async def run_expand(project_name: str):
    """Run prototype expansion with SSE streaming."""
    from murder_wizard.core.sse_manager import sse_manager

    if sse_manager.is_running(project_name):
        raise HTTPException(status_code=409, detail="An operation is already running for this project")

    async def event_generator():
        conn = await sse_manager.create_connection(project_name)
        runner = PhaseRunnerWeb(project_name, conn.queue)
        task_result: BaseException | None = None

        async def run_and_emit():
            nonlocal task_result
            try:
                await runner.run_expand()
            except BaseException as e:
                task_result = e
            finally:
                await sse_manager.cancel_connection(project_name)

        task = asyncio.create_task(run_and_emit())

        try:
            async for event in conn.event_stream():
                yield event
        except (asyncio.CancelledError, GeneratorExit):
            if not task.done():
                runner.cancel()
                task.cancel()
        finally:
            if not task.done():
                runner.cancel()
                task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except BaseException as e:
                if task_result is None:
                    task_result = e
            if task_result is not None:
                yield {"event": "error", "data": {"message": str(task_result)}}

    return EventSourceResponse(event_generator())


@router.post("/audit")
async def run_audit(project_name: str):
    """Run full audit with SSE streaming."""
    from murder_wizard.core.sse_manager import sse_manager

    if sse_manager.is_running(project_name):
        raise HTTPException(status_code=409, detail="An operation is already running for this project")

    async def event_generator():
        conn = await sse_manager.create_connection(project_name)
        runner = PhaseRunnerWeb(project_name, conn.queue)
        task_result: BaseException | None = None

        async def run_and_emit():
            nonlocal task_result
            try:
                await runner.run_audit()
            except BaseException as e:
                task_result = e
            finally:
                await sse_manager.cancel_connection(project_name)

        task = asyncio.create_task(run_and_emit())

        try:
            async for event in conn.event_stream():
                yield event
        except (asyncio.CancelledError, GeneratorExit):
            if not task.done():
                runner.cancel()
                task.cancel()
        finally:
            if not task.done():
                runner.cancel()
                task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except BaseException as e:
                if task_result is None:
                    task_result = e
            if task_result is not None:
                yield {"event": "error", "data": {"message": str(task_result)}}

    return EventSourceResponse(event_generator())


@router.post("/phases/{stage}/cancel")
async def cancel_phase(project_name: str, stage: int):
    """Cancel a running phase."""
    from murder_wizard.core.sse_manager import sse_manager
    await sse_manager.cancel_connection(project_name)
    return {"cancelled": True}
