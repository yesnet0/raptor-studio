"""raptor-studio FastAPI entry point.

Read-only web UI for browsing raptor project data.

    uvicorn studio.app:app --reload
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from studio.config import (
    APP_TAGLINE,
    APP_TITLE,
    RAPTOR_OUTPUT_BASE,
    RAPTOR_PROJECTS_DIR,
)
from studio.services.raptor_reader import get_project, list_projects
from studio.services.raptor_writer import ProjectCreateError, create_project

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title=APP_TITLE)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


def _ctx(**kwargs) -> dict:
    return {"app_title": APP_TITLE, "app_tagline": APP_TAGLINE, **kwargs}


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    projects = list_projects()
    runs = [run for p in projects for run in p.runs()]
    findings_count = sum(len(r.findings()) for r in runs)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        _ctx(
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
        request,
        "projects.html",
        _ctx(projects=list_projects(), projects_dir=str(RAPTOR_PROJECTS_DIR)),
    )


def _new_project_ctx(**overrides):
    default_output = str((RAPTOR_OUTPUT_BASE.expanduser() / "<name>"))
    ctx = {
        "form": {},
        "error": None,
        "default_output": default_output,
        "projects_dir": str(RAPTOR_PROJECTS_DIR),
    }
    ctx.update(overrides)
    return _ctx(**ctx)


@app.get("/projects/new", response_class=HTMLResponse)
def new_project_form(request: Request):
    return templates.TemplateResponse(
        request, "new_project.html", _new_project_ctx()
    )


@app.post("/projects/new")
def new_project_submit(
    request: Request,
    name: str = Form(""),
    target: str = Form(""),
    description: str = Form(""),
    output_dir: str = Form(""),
):
    try:
        proj = create_project(
            name=name.strip(),
            target=target.strip(),
            description=description.strip(),
            output_dir=output_dir.strip() or None,
        )
    except ProjectCreateError as e:
        return templates.TemplateResponse(
            request,
            "new_project.html",
            _new_project_ctx(
                form={
                    "name": name,
                    "target": target,
                    "description": description,
                    "output_dir": output_dir,
                },
                error=str(e),
            ),
            status_code=400,
        )
    return RedirectResponse(url=f"/projects/{proj.name}", status_code=303)


@app.get("/projects/{name}", response_class=HTMLResponse)
def project_detail(request: Request, name: str):
    proj = get_project(name)
    if proj is None:
        raise HTTPException(404, f"project not found: {name}")
    return templates.TemplateResponse(
        request, "project.html", _ctx(project=proj, runs=proj.runs())
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
        request,
        "findings.html",
        _ctx(project=proj, run=run, findings=run.findings()),
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
