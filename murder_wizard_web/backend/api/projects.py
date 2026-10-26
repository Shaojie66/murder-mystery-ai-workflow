"""Project CRUD and workbench API endpoints."""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.auth_deps import require_auth
from core.project_bootstrap import build_brief_from_answers, ensure_project_bootstrap
from core.sse_manager import sse_manager
from murder_wizard.wizard.session import SessionManager
from murder_wizard.wizard.state_machine import MurderWizardState, Stage

router = APIRouter(prefix="/api/projects", tags=["projects"])

MURDER_WIZARD_BASE = Path.home() / ".murder-wizard" / "projects"
_PROJECT_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

_STAGE_LABELS = {
    "idle": "未开始",
    "stage_1_mechanism": "机制设计",
    "stage_2_script": "剧本创作",
    "stage_3_visual": "视觉物料",
    "stage_4_test": "用户测试",
    "stage_5_commercial": "商业化",
    "stage_6_print": "印刷生产",
    "stage_7_promo": "宣发内容",
    "stage_8_community": "社区运营",
}

_ARTIFACT_GROUPS = {
    "core": {
        "label": "创作基础",
        "files": ["brief.md", "outline.md", "mechanism.md"],
    },
    "script": {
        "label": "剧本正文",
        "files": [
            "information_matrix.md",
            "background.md",
            "characters.md",
            "scripts_b.md",
            "dm_manual.md",
            "endings.md",
            "state/character_matrix.json",
        ],
    },
    "test": {
        "label": "测试与审计",
        "files": ["test_guide.md", "feedback.md", "iteration_report.md", "audit_report.md"],
    },
    "release": {
        "label": "发布与运营",
        "files": [
            "commercial.md",
            "script.pdf",
            "线索卡.pdf",
            "print_order.json",
            "promo_content.md",
            "community_plan.md",
        ],
    },
    "visual": {
        "label": "视觉物料",
        "files": ["image-prompts.md"],
    },
}


def _validate_project_name(name: str) -> None:
    """Validate project name to prevent path traversal attacks."""
    if not name:
        raise HTTPException(status_code=400, detail="Project name cannot be empty")
    if name in (".", ".."):
        raise HTTPException(status_code=400, detail="Invalid project name")
    if ".." in name or "/" in name or "\\" in name:
        raise HTTPException(status_code=400, detail="Project name cannot contain path separators or '..'")
    if name.startswith("-"):
        raise HTTPException(status_code=400, detail="Project name cannot start with '-'")
    if name.startswith("."):
        raise HTTPException(status_code=400, detail="Project name cannot start with '.'")
    if not _PROJECT_NAME_RE.fullmatch(name):
        raise HTTPException(
            status_code=400,
            detail="Project name may only contain letters, numbers, dot, underscore, and hyphen",
        )


def _project_path(name: str) -> Path:
    """Resolve a validated project path and re-check it stays under the base dir."""
    _validate_project_name(name)
    project_path = (MURDER_WIZARD_BASE / name).resolve()
    base_path = MURDER_WIZARD_BASE.resolve()
    if project_path.parent != base_path:
        raise HTTPException(status_code=400, detail="Invalid project path")
    return project_path


def _stage_slug_for_session_data(session_data: dict) -> str:
    slug = session_data.get("current_stage_slug")
    if slug:
        return slug
    raw = session_data.get("current_stage", "idle")
    try:
        return Stage.from_value(raw).slug
    except Exception:
        return "unknown"


def _list_artifacts(project_path: Path) -> dict[str, "ArtifactInfo"]:
    """List all known artifact files and their status."""
    result: dict[str, ArtifactInfo] = {}
    for group in _ARTIFACT_GROUPS.values():
        for rel_name in group["files"]:
            f = project_path / rel_name
            if f.exists():
                stat = f.stat()
                result[rel_name] = ArtifactInfo(
                    name=rel_name,
                    exists=True,
                    size=stat.st_size,
                    modified=str(stat.st_mtime),
                )
            else:
                result[rel_name] = ArtifactInfo(name=rel_name, exists=False)
    return result


def _group_artifacts(artifacts: dict[str, "ArtifactInfo"]) -> list["ArtifactGroup"]:
    groups: list[ArtifactGroup] = []
    for group_id, config in _ARTIFACT_GROUPS.items():
        groups.append(
            ArtifactGroup(
                id=group_id,
                label=config["label"],
                items=[artifacts[name] for name in config["files"]],
            )
        )
    return groups


def _build_project_details(name: str, state: MurderWizardState, project_path: Path) -> "ProjectDetails":
    artifacts = _list_artifacts(project_path)
    current_stage = state.current_stage.slug if state.current_stage else "idle"

    can_expand = (
        state.is_prototype
        and artifacts.get("characters.md", ArtifactInfo(name="characters.md", exists=False)).exists
    )
    can_audit = artifacts.get("characters.md", ArtifactInfo(name="characters.md", exists=False)).exists

    created_at = None
    session_file = project_path / "session.json"
    if session_file.exists():
        try:
            session_data = json.loads(session_file.read_text(encoding="utf-8"))
            created_at = session_data.get("created_at")
        except Exception:
            created_at = None

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


def _next_stage_number(stage_slug: str) -> int | None:
    stage_order = [
        "idle",
        "stage_1_mechanism",
        "stage_2_script",
        "stage_3_visual",
        "stage_4_test",
        "stage_5_commercial",
        "stage_6_print",
        "stage_7_promo",
        "stage_8_community",
    ]
    if stage_slug not in stage_order:
        return 1
    index = stage_order.index(stage_slug)
    if index == 0:
        return 1
    if stage_slug == "stage_8_community":
        return None
    return index + 1


def _build_workflow(project_name: str, project: "ProjectDetails") -> "WorkflowInfo":
    next_stage = _next_stage_number(project.current_stage)
    current_stage_number = 0
    match = re.match(r"stage_(\d+)_", project.current_stage)
    if match:
        current_stage_number = int(match.group(1))
    next_stage_slug = None
    if next_stage is not None:
        next_stage_slug = {
            1: "stage_1_mechanism",
            2: "stage_2_script",
            3: "stage_3_visual",
            4: "stage_4_test",
            5: "stage_5_commercial",
            6: "stage_6_print",
            7: "stage_7_promo",
            8: "stage_8_community",
        }.get(next_stage)
    return WorkflowInfo(
        current_stage=project.current_stage,
        current_stage_label=_STAGE_LABELS.get(project.current_stage, project.current_stage),
        current_stage_number=current_stage_number,
        next_stage=next_stage,
        next_stage_label=_STAGE_LABELS.get(next_stage_slug or "", None),
        running=sse_manager.is_running(project_name),
        can_expand=project.can_expand,
        can_audit=project.can_audit,
    )


def _build_quick_actions(project: "ProjectDetails", workflow: "WorkflowInfo") -> list["QuickAction"]:
    actions = [
        QuickAction(
            id="open_files",
            label="打开文件编辑",
            href=f"/projects/{project.name}/files/brief.md",
            enabled=project.artifacts.get("brief.md", ArtifactInfo(name="brief.md", exists=False)).exists,
            kind="navigate",
        ),
        QuickAction(
            id="open_matrix",
            label="打开信息矩阵",
            href=f"/projects/{project.name}/matrix",
            enabled=project.artifacts.get("state/character_matrix.json", ArtifactInfo(name="state/character_matrix.json", exists=False)).exists
            or project.artifacts.get("information_matrix.md", ArtifactInfo(name="information_matrix.md", exists=False)).exists,
            kind="navigate",
        ),
        QuickAction(
            id="run_audit",
            label="运行穿帮审计",
            href=f"/projects/{project.name}/phase/audit",
            enabled=project.can_audit,
            kind="navigate",
        ),
    ]

    if workflow.next_stage is not None:
        actions.insert(
            0,
            QuickAction(
                id="run_next_stage",
                label=f"运行下一阶段：{workflow.next_stage_label or workflow.next_stage}",
                href=f"/projects/{project.name}/phase/{workflow.next_stage}",
                enabled=True,
                kind="navigate",
            ),
        )

    return actions


class CreateProjectRequest(BaseModel):
    name: str
    story_type: str = "emotion"
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


class ArtifactGroup(BaseModel):
    id: str
    label: str
    items: list[ArtifactInfo]


class WorkflowInfo(BaseModel):
    current_stage: str
    current_stage_label: str
    current_stage_number: Optional[int] = None
    next_stage: Optional[int] = None
    next_stage_label: Optional[str] = None
    running: bool
    can_expand: bool
    can_audit: bool


class ReadinessInfo(BaseModel):
    brief_ready: bool
    outline_ready: bool
    outline_source: str
    blockers: list[str]


class QuickAction(BaseModel):
    id: str
    label: str
    href: str
    enabled: bool
    kind: str


class ProjectWorkbench(BaseModel):
    project: ProjectDetails
    workflow: WorkflowInfo
    readiness: ReadinessInfo
    artifacts: list[ArtifactGroup]
    quick_actions: list[QuickAction]


@router.get("", response_model=dict)
async def list_projects(user_id: str = Depends(require_auth)):
    """List all murder-wizard projects."""
    projects = []
    if not MURDER_WIZARD_BASE.exists():
        return {"projects": []}

    for project_dir in MURDER_WIZARD_BASE.iterdir():
        if not project_dir.is_dir():
            continue

        session_file = project_dir / "session.json"
        story_type = "unknown"
        is_prototype = True
        current_stage = "unknown"
        created_at = None

        if session_file.exists():
            try:
                session_data = json.loads(session_file.read_text(encoding="utf-8"))
                story_type = session_data.get("story_type", "mechanic")
                is_prototype = session_data.get("is_prototype", True)
                current_stage = _stage_slug_for_session_data(session_data)
                created_at = session_data.get("created_at")
            except Exception:
                pass

        artifacts = _list_artifacts(project_dir)
        projects.append(
            {
                "name": project_dir.name,
                "path": str(project_dir),
                "story_type": story_type,
                "is_prototype": is_prototype,
                "current_stage": current_stage,
                "created_at": created_at,
                "artifact_count": sum(1 for artifact in artifacts.values() if artifact.exists),
            }
        )

    projects.sort(key=lambda project: project.get("name") or "", reverse=False)
    return {"projects": projects}


@router.post("", response_model=dict)
async def create_project(req: CreateProjectRequest, user_id: str = Depends(require_auth)):
    """Create a new project and make it immediately stage-1 runnable."""
    project_path = _project_path(req.name)
    if project_path.exists():
        raise HTTPException(status_code=409, detail="Project already exists")

    project_path.mkdir(parents=True, exist_ok=True)
    session = SessionManager(req.name)
    state = MurderWizardState(
        project_name=req.name,
        story_type=req.story_type,
        is_prototype=req.is_prototype,
        current_stage=Stage.IDLE,
    )

    try:
        bootstrap = ensure_project_bootstrap(
            session,
            state,
            project_name=req.name,
            story_type=req.story_type,
            era=req.era,
            is_prototype=req.is_prototype,
            answers=req.answers,
        )
    except Exception as exc:
        shutil.rmtree(project_path, ignore_errors=True)
        raise HTTPException(status_code=502, detail=f"Failed to initialize project outline: {exc}") from exc

    return {
        "name": req.name,
        "status": "created",
        "brief_file": str(project_path / "brief.md"),
        "outline_file": str(project_path / "outline.md"),
        "outline_source": bootstrap.outline_source,
    }


@router.get("/{name}", response_model=ProjectDetails)
async def get_project(name: str, user_id: str = Depends(require_auth)):
    """Get detailed project info."""
    project_path = _project_path(name)
    if not project_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    session = SessionManager(name)
    state = session.load()
    if state is None:
        raise HTTPException(status_code=404, detail="Project session not found")

    return _build_project_details(name, state, project_path)


@router.get("/{name}/workbench", response_model=ProjectWorkbench)
async def get_project_workbench(name: str, user_id: str = Depends(require_auth)):
    """Return the canonical read model for all project workbench pages."""
    project_path = _project_path(name)
    if not project_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    session = SessionManager(name)
    state = session.load()
    if state is None:
        raise HTTPException(status_code=404, detail="Project session not found")

    bootstrap = ensure_project_bootstrap(
        session,
        state,
        project_name=name,
        story_type=state.story_type,
        is_prototype=state.is_prototype,
    )

    project = _build_project_details(name, state, project_path)
    workflow = _build_workflow(name, project)

    blockers = []
    if not project.artifacts.get("brief.md", ArtifactInfo(name="brief.md", exists=False)).exists:
        blockers.append("missing_brief")
    if not project.artifacts.get("outline.md", ArtifactInfo(name="outline.md", exists=False)).exists:
        blockers.append("missing_outline")

    readiness = ReadinessInfo(
        brief_ready=project.artifacts.get("brief.md", ArtifactInfo(name="brief.md", exists=False)).exists,
        outline_ready=bool((state.outline or "").strip())
        and project.artifacts.get("outline.md", ArtifactInfo(name="outline.md", exists=False)).exists,
        outline_source=bootstrap.outline_source,
        blockers=blockers,
    )

    return ProjectWorkbench(
        project=project,
        workflow=workflow,
        readiness=readiness,
        artifacts=_group_artifacts(project.artifacts),
        quick_actions=_build_quick_actions(project, workflow),
    )


@router.delete("/{name}")
async def delete_project(name: str, user_id: str = Depends(require_auth)):
    """Delete a project and all its files."""
    project_path = _project_path(name)
    if not project_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    shutil.rmtree(project_path)
    return {"deleted": name}
