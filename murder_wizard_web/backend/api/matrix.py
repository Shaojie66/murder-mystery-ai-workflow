"""Information matrix API endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
from typing import Optional

from murder_wizard.wizard.truth_files import TruthFileManager
from murder_wizard.wizard.schemas import CognitiveState

router = APIRouter(prefix="/api/projects/{project_name}/matrix", tags=["matrix"])

MURDER_WIZARD_BASE = Path.home() / ".murder-wizard" / "projects"


def _validate_project_name(name: str) -> None:
    if not name or name in (".", ".."):
        raise HTTPException(status_code=400, detail="Invalid project name")
    if ".." in name or "/" in name or "\\" in name:
        raise HTTPException(status_code=400, detail="Project name cannot contain path separators or '..'")


class UpdateCellRequest(BaseModel):
    state: str
    detail: str = ""
    evidence_refs: list[str] = None


class AddEvidenceRequest(BaseModel):
    evidence_id: str
    name: str
    description: str
    source_event: str
    source_character: str
    chain_role: str = ""
    points_to: str = ""


@router.get("")
async def get_matrix(project_name: str):
    """Get the full character matrix."""
    _validate_project_name(project_name)
    project_path = MURDER_WIZARD_BASE / project_name
    if not project_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    mgr = TruthFileManager(project_path)
    matrix = mgr.load_matrix()

    if matrix is None:
        raise HTTPException(status_code=404, detail="Matrix not found")

    return matrix.model_dump(mode="json")


@router.put("/cells/{char_id}/{event_id}")
async def update_cell(project_name: str, char_id: str, event_id: str, req: UpdateCellRequest):
    """Update a single cell's cognition state."""
    _validate_project_name(project_name)
    project_path = MURDER_WIZARD_BASE / project_name
    if not project_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    mgr = TruthFileManager(project_path)
    matrix = mgr.load_matrix()

    if matrix is None:
        raise HTTPException(status_code=404, detail="Matrix not found")

    if char_id not in matrix.characters:
        raise HTTPException(status_code=404, detail=f"Character {char_id} not found")

    if event_id not in matrix.characters[char_id].event_cognitions:
        # Initialize the cognition entry
        matrix.characters[char_id].event_cognitions[event_id] = CognitiveState(
            state=req.state, detail=req.detail, evidence_refs=req.evidence_refs or []
        )
    else:
        matrix.characters[char_id].event_cognitions[event_id].state = req.state
        matrix.characters[char_id].event_cognitions[event_id].detail = req.detail
        matrix.characters[char_id].event_cognitions[event_id].evidence_refs = req.evidence_refs or []

    mgr.save_matrix(matrix)

    return {
        "updated": True,
        "character_id": char_id,
        "event_id": event_id,
        "new_state": req.state,
    }


@router.post("/evidence")
async def add_evidence(project_name: str, req: AddEvidenceRequest):
    """Add an evidence item to the matrix."""
    _validate_project_name(project_name)
    project_path = MURDER_WIZARD_BASE / project_name
    if not project_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    mgr = TruthFileManager(project_path)
    matrix = mgr.load_matrix()

    if matrix is None:
        raise HTTPException(status_code=404, detail="Matrix not found")

    item = mgr.add_evidence(
        evidence_id=req.evidence_id,
        name=req.name,
        description=req.description,
        source_event=req.source_event,
        source_character=req.source_character,
        chain_role=req.chain_role,
        points_to=req.points_to,
    )

    mgr.save_matrix(matrix)

    return {"added": True, "evidence_id": req.evidence_id}


@router.post("/initialize")
async def initialize_matrix(project_name: str, char_count: int = 6, event_count: int = 7, is_prototype: bool = False):
    """Initialize a new character matrix for a project."""
    _validate_project_name(project_name)
    project_path = MURDER_WIZARD_BASE / project_name
    if not project_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    mgr = TruthFileManager(project_path)

    # Check if matrix already exists
    existing = mgr.load_matrix()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Matrix already exists")

    matrix = mgr.create_matrix(char_count=char_count, event_count=event_count, is_prototype=is_prototype)
    mgr.save_matrix(matrix)

    return {"created": True, "char_count": char_count, "event_count": event_count}
