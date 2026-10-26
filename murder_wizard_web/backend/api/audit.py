"""Audit API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from pathlib import Path

from core.auth_deps import require_auth

router = APIRouter(
    prefix="/api/projects/{project_name}/audit",
    tags=["audit"],
    dependencies=[Depends(require_auth)],
)

MURDER_WIZARD_BASE = Path.home() / ".murder-wizard" / "projects"


def _validate_project_name(name: str) -> None:
    if not name or name in (".", ".."):
        raise HTTPException(status_code=400, detail="Invalid project name")
    if ".." in name or "/" in name or "\\" in name:
        raise HTTPException(status_code=400, detail="Project name cannot contain path separators or '..'")


@router.get("/report")
async def get_audit_report(project_name: str):
    """Get the latest audit report."""
    _validate_project_name(project_name)
    project_path = MURDER_WIZARD_BASE / project_name
    if not project_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    report_file = project_path / "audit_report.md"
    if not report_file.exists():
        raise HTTPException(status_code=404, detail="Audit report not found")

    content = report_file.read_text(encoding="utf-8")
    stat = report_file.stat()

    return {
        "content": content,
        "modified": str(stat.st_mtime),
        "size": stat.st_size,
    }
