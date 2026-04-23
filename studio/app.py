"""raptor-studio FastAPI entry point.

Read-only web UI for browsing raptor project data.

    uvicorn studio.app:app --reload
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from studio.config import APP_TAGLINE, APP_TITLE, RAPTOR_PROJECTS_DIR
from studio.services.raptor_reader import get_project, list_projects

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title=APP_TITLE)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


def _ctx(request: Request, **kwargs) -> dict:
    return {
        "request": request,
        "app_title": APP_TITLE,
        "app_tagline": APP_TAGLINE,
        **kwargs,
    }


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    projects = list_projects()
    runs = [run for p in projects for run in p.runs()]
    findings_count = sum(len(r.findings()) for r in runs)
    return templates.TemplateResponse(
        "dashboard.html",
        _ctx(
            request,
            projects=projects[:5],
            recent_runs=sorted(runs, key=lambda r: r.timestamp, reverse=True)[:10],
            stats={
                "projects": len(projects),
                "runs": len(runs),
                "findings": findings_count,
            },
            projects_dir=str(RAPTOR_PROJECTS_DIR),
        ),
    )


@app.get("/projects", response_class=HTMLResponse)
def projects_index(request: Request):
    return templates.TemplateResponse(
        "projects.html",
        _ctx(request, projects=list_projects(), projects_dir=str(RAPTOR_PROJECTS_DIR)),
    )


@app.get("/projects/{name}", response_class=HTMLResponse)
def project_detail(request: Request, name: str):
    proj = get_project(name)
    if proj is None:
        raise HTTPException(404, f"project not found: {name}")
    return templates.TemplateResponse(
        "project.html", _ctx(request, project=proj, runs=proj.runs())
    )


@app.get(
    "/projects/{name}/runs/{run_name}/findings", response_class=HTMLResponse
)
def findings(request: Request, name: str, run_name: str):
    proj = get_project(name)
    if proj is None:
        raise HTTPException(404, f"project not found: {name}")
    run = next((r for r in proj.runs() if r.name == run_name), None)
    if run is None:
        raise HTTPException(404, f"run not found: {run_name}")
    return templates.TemplateResponse(
        "findings.html",
        _ctx(request, project=proj, run=run, findings=run.findings()),
    )


@app.get("/api/health")
def health():
    return JSONResponse(
        {
            "status": "ok",
            "app": APP_TITLE,
            "projects_dir": str(RAPTOR_PROJECTS_DIR),
            "projects_dir_exists": RAPTOR_PROJECTS_DIR.is_dir(),
        }
    )
