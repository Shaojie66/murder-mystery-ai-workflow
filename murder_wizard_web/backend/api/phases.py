"""Phase execution API with SSE streaming."""
import asyncio
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from core.auth_deps import require_auth
from core.sse_manager import sse_manager
from core.phase_runner_web import PhaseRunnerWeb

router = APIRouter(
    prefix="/api/projects/{project_name}",
    tags=["phases"],
    dependencies=[Depends(require_auth)],
)


def _validate_project_name(name: str) -> None:
    if not name or name in (".", ".."):
        raise HTTPException(status_code=400, detail="Invalid project name")
    if ".." in name or "/" in name or "\\" in name:
        raise HTTPException(status_code=400, detail="Project name cannot contain path separators or '..'")


class RunPhaseRequest(BaseModel):
    analyze: bool = False


def _require_project(project_name: str) -> None:
    _validate_project_name(project_name)
    if not (Path.home() / ".murder-wizard" / "projects" / project_name).is_dir():
        raise HTTPException(status_code=404, detail="Project not found")


def _begin(project_name: str):
    """同步登记作品写任务（先于响应），重复运行稳定得到 409。"""
    conn = sse_manager.try_start(project_name)
    if conn is None:
        raise HTTPException(status_code=409, detail="An operation is already running for this project")
    return conn


def _stream(conn, project_name: str, call):
    """在工作线程里跑同步引擎；保证先送达 end 终态事件，再关闭队列并释放作品写锁。

    HTTP 200 / 连接结束不代表业务成功，成败以 end 事件的 status 为准：success | failed | cancelled。
    """
    async def work():
        try:
            ok = await asyncio.to_thread(call)
            # 底层调用无法被打断：以实际结果为准，取消只是一个请求（cancel_requested 单独报告）
            status = "success" if ok else ("cancelled" if conn.cancel_requested else "failed")
            conn.status = status
            conn.put("end", {"status": status, "success": status == "success",
                             "cancel_requested": conn.cancel_requested})
        except BaseException as e:  # noqa: BLE001 - 终态必须送达
            conn.status = "failed"
            conn.put("error", {"message": str(e), "type": type(e).__name__})
            conn.put("end", {"status": "failed", "success": False, "cancel_requested": conn.cancel_requested})
        finally:
            conn.close()
            sse_manager.release(project_name, conn)

    conn.task = asyncio.create_task(work())

    async def events():
        # 客户端断开不会停止底层调用：任务线程结束前作品写锁继续占用
        async for event in conn.event_stream():
            yield event
    return EventSourceResponse(events())


@router.get("/phases/{stage}/status")
async def phase_status(project_name: str, stage: int):
    """作品当前是否有写入任务（与运行、取消共用同一个任务对象）。"""
    _validate_project_name(project_name)
    conn = sse_manager.get(project_name)
    return {"running": conn is not None, "status": conn.status if conn else None,
            "cancel_requested": bool(conn and conn.cancel_requested)}


@router.post("/phases/{stage}/run")
async def run_phase(project_name: str, stage: int, req: RunPhaseRequest):
    """运行阶段 1-8（SSE）。req.analyze 仅对阶段 4 生效（分析 feedback.md）。"""
    _require_project(project_name)
    if not 1 <= stage <= 8:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {stage}")
    conn = _begin(project_name)
    runner = PhaseRunnerWeb(project_name, conn)
    return _stream(conn, project_name, lambda: asyncio.run(runner.run_phase(stage, req.analyze)))


@router.post("/expand")
async def run_expand(project_name: str, accept_overwrite: bool = False):
    """原型扩写（SSE）。会覆盖并重新生成多份作品文件，必须显式传 accept_overwrite=true 才会调用模型。"""
    _require_project(project_name)
    conn = _begin(project_name)
    runner = PhaseRunnerWeb(project_name, conn)
    return _stream(conn, project_name, lambda: asyncio.run(runner.run_expand(accept_overwrite=accept_overwrite)))


@router.post("/audit")
async def run_audit(project_name: str, force: bool = False):
    """只读审计（SSE）。成败看 audit_complete / end 事件里的 status，不看 HTTP 状态。"""
    _require_project(project_name)
    conn = _begin(project_name)
    runner = PhaseRunnerWeb(project_name, conn)
    return _stream(conn, project_name, lambda: asyncio.run(runner.run_audit(force=force)))


@router.post("/phases/{stage}/cancel")
async def cancel_phase(project_name: str, stage: int):
    """请求取消。底层同步调用无法被打断：任务结束前作品写锁继续占用，最终以 end 事件为准。"""
    _validate_project_name(project_name)
    requested = sse_manager.request_cancel(project_name)
    return {"cancelled": False, "cancel_requested": requested, "stopped": False,
            "note": "已请求取消；正在进行的模型调用不会被打断，任务结束前作品仍处于运行状态" if requested else "没有正在运行的任务"}
