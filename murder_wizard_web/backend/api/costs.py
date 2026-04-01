"""Cost tracking API endpoints."""
from fastapi import APIRouter, HTTPException
from pathlib import Path
import json

router = APIRouter(prefix="/api/projects/{project_name}/costs", tags=["costs"])

MURDER_WIZARD_BASE = Path.home() / ".murder-wizard" / "projects"


def _validate_project_name(name: str) -> None:
    if not name or name in (".", ".."):
        raise HTTPException(status_code=400, detail="Invalid project name")
    if ".." in name or "/" in name or "\\" in name:
        raise HTTPException(status_code=400, detail="Project name cannot contain path separators or '..'")


@router.get("")
async def get_costs(project_name: str):
    """Get cost breakdown for a project."""
    _validate_project_name(project_name)
    project_path = MURDER_WIZARD_BASE / project_name
    if not project_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    cost_log = project_path / "cost.log"
    if not cost_log.exists():
        return {
            "total_cost": 0.0,
            "total_tokens": 0,
            "by_operation": [],
            "by_date": [],
            "by_model": {},
        }

    total_cost = 0.0
    total_tokens = 0
    by_operation: dict = {}
    by_date: dict = {}
    by_model: dict = {}

    try:
        for line in cost_log.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            op = entry.get("operation", "unknown")
            tokens = entry.get("tokens_used", 0)
            cost = entry.get("cost", 0.0)
            model = entry.get("model", "unknown")
            timestamp = entry.get("timestamp", "")

            total_cost += cost
            total_tokens += tokens

            if op not in by_operation:
                by_operation[op] = {"operation": op, "tokens": 0, "cost": 0.0, "count": 0}
            by_operation[op]["tokens"] += tokens
            by_operation[op]["cost"] += cost
            by_operation[op]["count"] += 1

            if model not in by_model:
                by_model[model] = {"model": model, "tokens": 0, "cost": 0.0}
            by_model[model]["tokens"] += tokens
            by_model[model]["cost"] += cost

            if timestamp:
                date = timestamp[:10]  # YYYY-MM-DD
                if date not in by_date:
                    by_date[date] = {"date": date, "cost": 0.0}
                by_date[date]["cost"] += cost

    except (json.JSONDecodeError, KeyError):
        pass

    return {
        "total_cost": round(total_cost, 4),
        "total_tokens": total_tokens,
        "by_operation": list(by_operation.values()),
        "by_date": sorted(by_date.values(), key=lambda x: x["date"]),
        "by_model": by_model,
    }


@router.get("/summary")
async def get_cost_summary(project_name: str):
    """Lightweight cost summary for project cards."""
    _validate_project_name(project_name)
    project_path = MURDER_WIZARD_BASE / project_name
    if not project_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    cost_log = project_path / "cost.log"
    if not cost_log.exists():
        return {"total_cost": 0.0, "operation_count": 0}

    total_cost = 0.0
    operation_count = 0

    try:
        for line in cost_log.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            total_cost += entry.get("cost", 0.0)
            operation_count += 1
    except (json.JSONDecodeError, KeyError):
        pass

    return {"total_cost": round(total_cost, 4), "operation_count": operation_count}
