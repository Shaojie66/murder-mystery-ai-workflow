"""User identity and analytics API endpoints."""
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional, Any
import time

from core.auth import encode_token, decode_token

router = APIRouter(prefix="/api/user", tags=["user"])

# In-memory stores for stub data (reset on restart)
_projects_used = 0
_plan_clicks = 0


def _get_user_id(authorization: Optional[str]) -> str | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:]
    return decode_token(token)


class TokenRequest(BaseModel):
    user_id: str


class TokenResponse(BaseModel):
    token: str


class PlanInfo(BaseModel):
    plan: str = "free"
    project_limit: int = 3
    projects_used: int = 0
    is_upgrade_available: bool = True


class ClickResponse(BaseModel):
    success: bool = True
    total_clicks: int


class EventResponse(BaseModel):
    success: bool = True


class ProjectsUsedResponse(BaseModel):
    projects_used: int


class ActivateProResponse(BaseModel):
    success: bool = True
    plan: str = "pro"


class AnalyticsData(BaseModel):
    clicks: dict = {"total": 0, "by_trigger": {}, "all": []}
    funnel: dict = {"by_action": {}, "totals": {}, "events": []}


class FunnelEventData(BaseModel):
    event_type: str
    project_name: str
    stage: Optional[int] = None
    success: Optional[bool] = None
    metadata: Optional[str] = None


class FunnelSummary(BaseModel):
    projects_created: int = 0
    expands_triggered: int = 0
    expands_completed: int = 0
    phase_started: dict = {}
    phase_completed: dict = {}


class FunnelAnalytics(BaseModel):
    events: list = []
    by_project: dict = {}
    summary: FunnelSummary = FunnelSummary()


@router.post("/auth/token", response_model=TokenResponse)
async def create_token(req: TokenRequest):
    """Issue a JWT for a device/user ID."""
    token = encode_token(req.user_id)
    return TokenResponse(token=token)


@router.get("/me")
async def get_me(authorization: Optional[str] = Header(None)):
    """Get current user identity from JWT."""
    user_id = _get_user_id(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return {"user_id": user_id}


@router.get("/plan", response_model=PlanInfo)
async def get_plan(authorization: Optional[str] = Header(None)):
    """Stub: return free tier plan info."""
    return PlanInfo(
        plan="free",
        project_limit=3,
        projects_used=_projects_used,
        is_upgrade_available=True,
    )


@router.post("/plan/upgrade-click", response_model=ClickResponse)
async def record_upgrade_click(trigger: str = "", authorization: Optional[str] = Header(None)):
    """Stub: record an upgrade click."""
    global _plan_clicks
    _plan_clicks += 1
    return ClickResponse(success=True, total_clicks=_plan_clicks)


@router.post("/plan/experiment-event", response_model=EventResponse)
async def record_experiment_event(
    trigger: str = "",
    action: str = "view",
    user_plan: str = "free",
    authorization: Optional[str] = Header(None),
):
    """Stub: record an experiment event."""
    return EventResponse(success=True)


@router.post("/plan/projects-used", response_model=ProjectsUsedResponse)
async def increment_projects_used(authorization: Optional[str] = Header(None)):
    """Stub: increment projects used counter."""
    global _projects_used
    _projects_used += 1
    return ProjectsUsedResponse(projects_used=_projects_used)


@router.get("/plan/analytics", response_model=AnalyticsData)
async def get_analytics(authorization: Optional[str] = Header(None)):
    """Stub: return empty analytics data."""
    return AnalyticsData()


@router.post("/plan/activate-pro", response_model=ActivateProResponse)
async def activate_pro(authorization: Optional[str] = Header(None)):
    """Stub: activate pro version."""
    return ActivateProResponse(success=True, plan="pro")


@router.post("/plan/funnel-event", response_model=EventResponse)
async def record_funnel_event(
    event_type: str = "",
    project_name: str = "",
    stage: Optional[int] = None,
    success: Optional[bool] = None,
    metadata: Optional[str] = None,
    authorization: Optional[str] = Header(None),
):
    """Stub: record a funnel event."""
    return EventResponse(success=True)


@router.get("/plan/funnel-analytics", response_model=FunnelAnalytics)
async def get_funnel_analytics(authorization: Optional[str] = Header(None)):
    """Stub: return empty funnel analytics."""
    return FunnelAnalytics()
