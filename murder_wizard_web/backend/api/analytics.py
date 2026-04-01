"""Analytics API - tracks landing page A/B test events."""
from datetime import datetime
from typing import Optional, Any
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

# In-memory storage for development
# In production, use a proper database
_events: list[dict] = []


class TrackRequest(BaseModel):
    event: str
    variant: Optional[str] = None
    url: Optional[str] = None
    duration: Optional[int] = None
    referrer: Optional[str] = None
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
        "props": data.props or {},
        "timestamp": datetime.utcnow().isoformat(),
    }
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
    return _get_summary(_events)


def _get_summary(events: list[dict]) -> dict:
    """Compute summary statistics from events."""
    if not events:
        return {
            "total_events": 0,
            "page_views": 0,
            "email_submissions": 0,
            "modal_opens": 0,
            "cta_clicks": 0,
            "scroll_50": 0,
            "scroll_100": 0,
            "variant_a": 0,
            "variant_b": 0,
            "avg_duration": 0,
        }

    summary = {
        "total_events": len(events),
        "page_views": sum(1 for e in events if e["event"] == "page_view"),
        "email_submissions": sum(1 for e in events if e["event"] == "email_submit"),
        "modal_opens": sum(1 for e in events if e["event"] == "modal_open"),
        "cta_clicks": sum(1 for e in events if e["event"] == "cta_click"),
        "scroll_50": sum(1 for e in events if e["event"] == "scroll_50"),
        "scroll_100": sum(1 for e in events if e["event"] == "scroll_100"),
        "variant_a": sum(1 for e in events if e.get("variant") == "a"),
        "variant_b": sum(1 for e in events if e.get("variant") == "b"),
    }

    # Calculate average session duration
    durations = [e.get("duration", 0) for e in events if e.get("duration")]
    if durations:
        summary["avg_duration"] = sum(durations) / len(durations)

    # Calculate conversion rates
    page_views_a = sum(1 for e in events if e["event"] == "page_view" and e.get("variant") == "a")
    page_views_b = sum(1 for e in events if e["event"] == "page_view" and e.get("variant") == "b")
    submits_a = sum(1 for e in events if e["event"] == "email_submit" and e.get("variant") == "a")
    submits_b = sum(1 for e in events if e["event"] == "email_submit" and e.get("variant") == "b")

    summary["conversion_rate_a"] = (submits_a / page_views_a * 100) if page_views_a > 0 else 0
    summary["conversion_rate_b"] = (submits_b / page_views_b * 100) if page_views_b > 0 else 0

    return summary
