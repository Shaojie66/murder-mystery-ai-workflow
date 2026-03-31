"""PDF generation API endpoints."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path

router = APIRouter(prefix="/api/projects/{project_name}/pdf", tags=["pdf"])

MURDER_WIZARD_BASE = Path.home() / ".murder-wizard" / "projects"


class GeneratePDFRequest(BaseModel):
    type: str = "script"  # "script" or "clue_cards"


@router.post("/generate")
async def generate_pdf(project_name: str, req: GeneratePDFRequest):
    """Generate PDF from current characters.md."""
    project_path = MURDER_WIZARD_BASE / project_name
    if not project_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        from murder_wizard.print.pdf_gen import PDFGenerator

        generator = PDFGenerator(project_path)

        if req.type == "script":
            result_path = generator.generate_script_pdf()
        elif req.type == "clue_cards":
            result_path = generator.generate_clue_cards()
        else:
            raise HTTPException(status_code=400, detail="Invalid PDF type")

        return {
            "generated": True,
            "filename": result_path.name,
            "path": str(result_path),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


@router.get("/status")
async def get_print_status(project_name: str):
    """Check print readiness."""
    project_path = MURDER_WIZARD_BASE / project_name
    if not project_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    characters_md = project_path / "characters.md"
    mechanism_md = project_path / "mechanism.md"
    script_pdf = project_path / "script.pdf"
    clue_cards = project_path / "线索卡.pdf"
    materials_dir = project_path / "materials"

    checklist = {
        "characters.md": characters_md.exists(),
        "mechanism.md": mechanism_md.exists(),
        "script.pdf": script_pdf.exists(),
        "clue_cards.pdf": clue_cards.exists(),
        "materials/": materials_dir.exists(),
    }

    issues = []
    if not checklist["characters.md"]:
        issues.append("缺少 characters.md")
    if not checklist["script.pdf"]:
        issues.append("缺少 script.pdf（运行阶段6生成）")
    if not checklist["clue_cards.pdf"]:
        issues.append("缺少线索卡（运行阶段6生成）")

    ready = checklist["characters.md"] and checklist["mechanism.md"]

    return {
        "ready": ready,
        "issues": issues,
        "checklist": checklist,
    }


@router.get("/script.pdf")
async def get_script_pdf(project_name: str):
    """Download script.pdf."""
    project_path = MURDER_WIZARD_BASE / project_name
    if not project_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    pdf_path = project_path / "script.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="script.pdf not found")

    return FileResponse(path=pdf_path, filename="script.pdf", media_type="application/pdf")
