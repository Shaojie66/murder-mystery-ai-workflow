"""File read/write API endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
import os

router = APIRouter(prefix="/api/projects/{project_name}/files", tags=["files"])

MURDER_WIZARD_BASE = Path.home() / ".murder-wizard" / "projects"


class SaveFileRequest(BaseModel):
    content: str


class FileInfo(BaseModel):
    name: str
    type: str
    size: int
    modified: str


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


def _get_file_type(name: str) -> str:
    if name.endswith(".md"):
        return "markdown"
    elif name.endswith(".pdf"):
        return "pdf"
    elif name.endswith(".json"):
        return "json"
    elif name.endswith(".txt"):
        return "text"
    return "unknown"


@router.get("")
async def list_files(project_name: str):
    """List all files in a project."""
    _validate_project_name(project_name)
    project_path = MURDER_WIZARD_BASE / project_name
    if not project_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    files = []
    for f in project_path.rglob("*"):
        if f.is_file() and not f.name.startswith("."):
            stat = f.stat()
            rel_path = str(f.relative_to(project_path))
            files.append({
                "name": rel_path,
                "type": _get_file_type(rel_path),
                "size": stat.st_size,
                "modified": str(stat.st_mtime),
            })

    return {"files": sorted(files, key=lambda x: x["name"])}


@router.get("/{filename:path}/download")
async def download_file(project_name: str, filename: str):
    """Download a file."""
    from fastapi.responses import FileResponse

    _validate_project_name(project_name)
    project_path = MURDER_WIZARD_BASE / project_name
    if not project_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    if ".." in filename or filename.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = project_path / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    media_type = "application/pdf" if filename.endswith(".pdf") else "application/octet-stream"

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type,
    )


@router.get("/{filename:path}")
async def get_file(project_name: str, filename: str):
    """Get file content."""
    _validate_project_name(project_name)
    project_path = MURDER_WIZARD_BASE / project_name
    if not project_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    # Security: prevent path traversal
    if ".." in filename or filename.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = project_path / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Not a file")

    stat = file_path.stat()
    content = file_path.read_text(encoding="utf-8", errors="replace")

    return {
        "name": filename,
        "content": content,
        "type": _get_file_type(filename),
        "size": stat.st_size,
        "modified": str(stat.st_mtime),
    }


@router.put("/{filename:path}")
async def save_file(project_name: str, filename: str, req: SaveFileRequest):
    """Save file content."""
    _validate_project_name(project_name)
    project_path = MURDER_WIZARD_BASE / project_name
    if not project_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    # Security: prevent path traversal
    if ".." in filename or filename.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = project_path / filename

    # Ensure parent directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    file_path.write_text(req.content, encoding="utf-8")
    stat = file_path.stat()

    return {
        "saved": True,
        "filename": filename,
        "size": stat.st_size,
        "modified": str(stat.st_mtime),
    }
