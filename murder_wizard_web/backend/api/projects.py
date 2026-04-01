"""Project CRUD API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import json
import shutil

from murder_wizard.wizard.session import SessionManager
from murder_wizard.wizard.state_machine import MurderWizardState, Stage
from core.auth import decode_token

router = APIRouter(prefix="/api/projects", tags=["projects"])


async def require_auth(authorization: Optional[str] = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization[7:]
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user_id

MURDER_WIZARD_BASE = Path.home() / ".murder-wizard" / "projects"


class CreateProjectRequest(BaseModel):
    name: str
    story_type: str = "emotion"  # emotion, reasoning, fun, horror, mechanic
    is_prototype: bool = True
    era: str = "现代"
    answers: Optional[dict] = None


class ArtifactInfo(BaseModel):
    name: str
    exists: bool
    size: Optional[int] = None
    modified: Optional[str] = None


class ProjectDetails(BaseModel):
    name: str
    story_type: str
    is_prototype: bool
    current_stage: str
    created_at: Optional[str] = None
    artifacts: dict[str, ArtifactInfo]
    can_expand: bool
    can_audit: bool


def _list_artifacts(project_path: Path) -> dict[str, ArtifactInfo]:
    """List all possible artifact files and their status."""
    artifact_names = [
        "brief.md",
        "mechanism.md",
        "information_matrix.md",
        "characters.md",
        "image-prompts.md",
        "test_guide.md",
        "feedback.md",
        "iteration_report.md",
        "commercial.md",
        "script.pdf",
        "线索卡.pdf",
        "promo_content.md",
        "community_plan.md",
        "audit_report.md",
    ]
    state_dir = project_path / "state"
    state_files = ["character_matrix.json"] if state_dir.exists() else []

    all_files = artifact_names + state_files
    result = {}
    for name in all_files:
        f = project_path / name
        if f.exists():
            stat = f.stat()
            result[name] = ArtifactInfo(
                name=name,
                exists=True,
                size=stat.st_size,
                modified=str(stat.st_mtime),
            )
        else:
            result[name] = ArtifactInfo(name=name, exists=False)
    return result


@router.get("", response_model=dict)
async def list_projects():
    """List all murder-wizard projects."""
    projects = []
    if not MURDER_WIZARD_BASE.exists():
        return {"projects": []}

    for project_dir in MURDER_WIZARD_BASE.iterdir():
        if not project_dir.is_dir():
            continue
        session_file = project_dir / "session.json"
        if session_file.exists():
            try:
                session_data = json.loads(session_file.read_text(encoding="utf-8"))
                # MurderWizardState.to_dict() serializes to top level, not under "state"
                stage = session_data.get("current_stage", "idle")
                story_type = session_data.get("story_type", "mechanic")
                is_prototype = session_data.get("is_prototype", True)
                created_at = session_data.get("created_at")
                if isinstance(created_at, (int, float)):
                    import datetime
                    created_at = datetime.datetime.fromtimestamp(created_at).isoformat()
            except Exception:
                stage = "unknown"
                story_type = "unknown"
                is_prototype = True
                created_at = None
        else:
            stage = "unknown"
            story_type = "unknown"
            is_prototype = True
            created_at = None

        artifacts = _list_artifacts(project_dir)
        projects.append({
            "name": project_dir.name,
            "path": str(project_dir),
            "story_type": story_type,
            "is_prototype": is_prototype,
            "current_stage": stage,
            "created_at": created_at,
            "artifact_count": sum(1 for a in artifacts.values() if a.exists),
        })

    projects.sort(key=lambda p: p.get("created_at") or "", reverse=True)
    return {"projects": projects}


@router.post("", response_model=dict)
async def create_project(req: CreateProjectRequest, user_id: str = Depends(require_auth)):
    """Create a new project (simplified init without interactive wizard)."""
    project_path = MURDER_WIZARD_BASE / req.name

    if project_path.exists():
        raise HTTPException(status_code=409, detail="Project already exists")

    # Create project directory
    project_path.mkdir(parents=True, exist_ok=True)

    # Create brief.md from answers if provided
    brief_content = ""
    if req.answers:
        brief_content = _build_brief_from_answers(req.story_type, req.era, req.answers)
        (project_path / "brief.md").write_text(brief_content, encoding="utf-8")

    # Initialize session state
    state = MurderWizardState(
        project_name=req.name,
        story_type=req.story_type,
        is_prototype=req.is_prototype,
        current_stage=Stage.IDLE,
    )
    session = SessionManager(req.name)
    session.save(state)

    return {
        "name": req.name,
        "status": "created",
        "brief_file": str(project_path / "brief.md") if brief_content else None,
    }


def _build_brief_from_answers(story_type: str, era: str, answers: dict) -> str:
    """Build brief.md content from wizard answers."""
    lines = [
        f"# 剧本杀项目大纲",
        f"",
        f"**类型**: {story_type}",
        f"**时代**: {era}",
        f"**模式**: {'原型模式（2人）' if True else '完整模式（6人）'}",
        f"",
    ]
    if answers:
        lines.append("## 创作问卷")
        for k, v in answers.items():
            lines.append(f"- **{k}**: {v}")
    return "\n".join(lines)


@router.get("/{name}", response_model=ProjectDetails)
async def get_project(name: str):
    """Get detailed project info."""
    project_path = MURDER_WIZARD_BASE / name
    if not project_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    session = SessionManager(name)
    state = session.load()

    if state is None:
        raise HTTPException(status_code=404, detail="Project session not found")

    artifacts = _list_artifacts(project_path)

    # Determine stage from artifacts and state
    current_stage = state.current_stage.slug if state.current_stage else "idle"

    # Check if expand is available (has stage 2 done, is prototype)
    can_expand = (
        state.is_prototype
        and ("characters.md" in artifacts and artifacts["characters.md"].exists)
    )

    # Audit is available once characters.md exists
    can_audit = "characters.md" in artifacts and artifacts["characters.md"].exists

    import datetime
    created_at = None
    session_file = project_path / "session.json"
    if session_file.exists():
        try:
            session_data = json.loads(session_file.read_text(encoding="utf-8"))
            ts = session_data.get("created_at")
            if ts and isinstance(ts, (int, float)):
                created_at = datetime.datetime.fromtimestamp(ts).isoformat()
        except Exception:
            pass

    return ProjectDetails(
        name=name,
        story_type=state.story_type,
        is_prototype=state.is_prototype,
        current_stage=current_stage,
        created_at=created_at,
        artifacts=artifacts,
        can_expand=can_expand,
        can_audit=can_audit,
    )


@router.delete("/{name}")
async def delete_project(name: str):
    """Delete a project and all its files."""
    project_path = MURDER_WIZARD_BASE / name
    if not project_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    shutil.rmtree(project_path)
    return {"deleted": name}
