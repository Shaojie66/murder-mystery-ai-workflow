"""Murder Wizard Web Dashboard - FastAPI Backend."""
import sys
from pathlib import Path

# Add backend/ to path so we can import api/ and core/ as top-level packages
_backend_dir = Path(__file__).parent
sys.path.insert(0, str(_backend_dir))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import projects, phases, files, matrix, costs, audit, pdf

app = FastAPI(title="Murder Wizard Web API", version="0.6.0")

# CORS: allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(projects.router)
app.include_router(phases.router)
app.include_router(files.router)
app.include_router(matrix.router)
app.include_router(costs.router)
app.include_router(audit.router)
app.include_router(pdf.router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "murder-wizard-web"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
