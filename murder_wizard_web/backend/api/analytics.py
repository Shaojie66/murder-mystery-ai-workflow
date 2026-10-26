"""Analytics API - tracks landing page A/B test events."""
from datetime import datetime
from typing import Optional, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

from core.jsonl_store import JsonlStore

# 事件追加写入 ~/.murder-wizard/landing/events.jsonl，首次使用时回放；工具不自动删除。
_events: list[dict] = []
_store = JsonlStore("events.jsonl", "landing-event/1")
_loaded = False
_corrupt = 0


def _ensure_loaded() -> None:
    global _loaded, _corrupt
    if _loaded:
        return
    records, _corrupt = _store.replay()
    for r in records:
        if isinstance(r.get("event"), str):
            _events.append({k: v for k, v in r.items() if k != "schema"})
    _loaded = True


class TrackRequest(BaseModel):
    event: str
    variant: Optional[str] = None
    url: Optional[str] = None
    duration: Optional[int] = None
    referrer: Optional[str] = None
    visit_id: Optional[str] = None  # 一次访问的标识：同一 visit_id 的 page_view 只计一次
    props: Optional[dict[str, Any]] = None


@router.post("/track")
async def track_event(data: TrackRequest):
    """Track an analytics event.

    Events are stored in memory for development.
    For production, integrate with Plausible Analytics or a custom database.
    """
    event_data = {
        "event": data.event,
        "variant": data.variant,
        "url": data.url,
        "duration": data.duration,
        "referrer": data.referrer,
        "visit_id": data.visit_id,
        "props": data.props or {},
        "timestamp": datetime.utcnow().isoformat(),
    }
    _ensure_loaded()
    try:
        _store.append(event_data)  # 先写盘再改内存
    except OSError:
        raise HTTPException(status_code=503, detail="storage_unavailable")
    _events.append(event_data)
    return {"status": "ok"}


@router.get("/events")
async def get_events(
    limit: int = 100,
    event_type: Optional[str] = None,
    variant: Optional[str] = None,
):
    """Get tracked events for the metrics dashboard.

    Returns events in reverse chronological order (newest first).
    """
    _ensure_loaded()
    filtered = _events

    if event_type:
        filtered = [e for e in filtered if e["event"] == event_type]

    if variant:
        filtered = [e for e in filtered if e.get("variant") == variant]

    return {
        "events": filtered[-limit:],
        "total": len(_events),
        "summary": _get_summary(filtered),
    }


@router.get("/summary")
async def get_summary():
    """Get a summary of all tracked events for the A/B test dashboard."""
    _ensure_loaded()
    return _get_summary(_events)


def _unique_views(events: list[dict], variant: Optional[str] = None) -> int:
    """page_view 按 visit_id 去重（没有 visit_id 的旧事件逐条计）。page_leave 不是访问。"""
    seen: set[str] = set()
    n = 0
    for e in events:
        if e["event"] != "page_view" or (variant is not None and e.get("variant") != variant):
            continue
        vid = e.get("visit_id")
        if vid:
            if vid in seen:
                continue
            seen.add(vid)
        n += 1
    return n


def _unique_submits(events: list[dict], variant: str) -> int:
    seen: set[str] = set()
    n = 0
    for e in events:
        if e["event"] != "email_submit" or e.get("variant") != variant:
            continue
        vid = e.get("visit_id")
        if vid:
            if vid in seen:
                continue
            seen.add(vid)
        n += 1
    return n


def _get_summary(events: list[dict]) -> dict:
    """统计口径：访问数按 visit_id 去重；variant_a/b 是各版本的访问数；数据追加写盘，重启后回放。"""
    views_a, views_b = _unique_views(events, "a"), _unique_views(events, "b")
    durations = [e["duration"] for e in events if e["event"] == "page_leave" and e.get("duration")]
    return {
        "total_events": len(events),
        "page_views": _unique_views(events),
        "email_submissions": sum(1 for e in events if e["event"] == "email_submit"),
        "modal_opens": sum(1 for e in events if e["event"] == "modal_open"),
        "cta_clicks": sum(1 for e in events if e["event"] == "cta_click"),
        "scroll_50": sum(1 for e in events if e["event"] == "scroll_50"),
        "scroll_100": sum(1 for e in events if e["event"] == "scroll_100"),
        "variant_a": views_a,
        "variant_b": views_b,
        "avg_duration": (sum(durations) / len(durations)) if durations else 0,
        "conversion_rate_a": (_unique_submits(events, "a") / views_a * 100) if views_a else 0,
        "conversion_rate_b": (_unique_submits(events, "b") / views_b * 100) if views_b else 0,
        "persisted": True,
        "corrupt_lines": _corrupt,
    }
