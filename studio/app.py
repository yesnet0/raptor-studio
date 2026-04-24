"""raptor-studio FastAPI entry point.

Read-write web UI for raptor projects.

    uvicorn studio.app:app --reload
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from studio.config import (
    APP_TAGLINE,
    APP_TITLE,
    RAPTOR_MODELS_CONFIG,
    RAPTOR_OUTPUT_BASE,
    RAPTOR_PROJECTS_DIR,
)
from studio.services.artifacts_reader import (
    list_exploits,
    list_patches,
    list_reports,
    tail_activity,
)
from studio.services.validation_reader import load_validation_bundle, summarize_run
from studio.services.models_reader import (
    PROVIDERS,
    ROLE_DESCRIPTIONS,
    ROLES,
    ModelConfig,
    ModelEntry,
    current_budget_cap,
    env_status,
    load_models_config,
    save_models_config,
)
from studio.services.raptor_reader import RaptorProject, get_project, list_projects
from studio.services.raptor_writer import ProjectCreateError, create_project
from studio.services.run_kind import (
    STAGE_DESCRIPTIONS,
    STAGE_LABELS,
    lane_for,
    lane_status,
    next_action,
    stages_for,
)

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title=APP_TITLE)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


def _ctx(**kwargs) -> dict:
    return {"app_title": APP_TITLE, "app_tagline": APP_TAGLINE, **kwargs}


def _project_ctx(project: RaptorProject, active_stage: str, **extras) -> dict:
    """Build the context dict needed by every `project_base`-derived page."""
    runs = project.runs()
    return _ctx(
        project=project,
        runs=runs,
        lane_status=lane_status(runs),
        next_action=next_action(runs),
        active_stage=active_stage,
        **extras,
    )


def _require_project(name: str) -> RaptorProject:
    proj = get_project(name)
    if proj is None:
        raise HTTPException(404, f"project not found: {name}")
    return proj


def _stage_runs(project: RaptorProject, stage: str):
    return [r for r in project.runs() if stage in stages_for(r.kind)]


def _cli_hint(stage: str, project: RaptorProject) -> dict:
    target = project.target
    hints = {
        "understand":     {"command": f"raptor project use {project.name}\nclaude\n/understand --map", "explanation": "Run inside Claude Code after selecting this project."},
        "scan":           {"command": f"raptor project use {project.name}\npython3 raptor.py scan --repo {target}", "explanation": "Static analysis with Semgrep (and CodeQL if --languages is set)."},
        "validate":       {"command": f"raptor project use {project.name}\nclaude\n/validate", "explanation": "Runs the A–F validation pipeline on existing findings."},
        "fuzz":           {"command": f"python3 raptor_fuzzing.py --binary <path-to-binary> --autonomous --duration 3600", "explanation": "Binary fuzzing mode — provide a compiled binary, not a repo."},
        "crash-analysis": {"command": "claude\n/crash-analysis <bug-tracker-url> <git-repo-url>", "explanation": "Requires rr on Linux x86_64 and a reproducer input."},
        "oss-forensics":  {"command": "claude\n/oss-forensics <github-url>", "explanation": "Needs GOOGLE_APPLICATION_CREDENTIALS for GH Archive BigQuery."},
    }
    return hints.get(stage, {"command": "", "explanation": ""})


# --- Dashboard ------------------------------------------------------------

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


# --- Projects list + new --------------------------------------------------

@app.get("/projects", response_class=HTMLResponse)
def projects_index(request: Request):
    return templates.TemplateResponse(
        request, "projects.html",
        _ctx(projects=list_projects(), projects_dir=str(RAPTOR_PROJECTS_DIR)),
    )


def _new_project_ctx(**overrides):
    default_output = str((RAPTOR_OUTPUT_BASE.expanduser() / "<name>"))
    ctx = {
        "form": {}, "error": None,
        "default_output": default_output,
        "projects_dir": str(RAPTOR_PROJECTS_DIR),
    }
    ctx.update(overrides)
    return _ctx(**ctx)


@app.get("/projects/new", response_class=HTMLResponse)
def new_project_form(request: Request):
    return templates.TemplateResponse(request, "new_project.html", _new_project_ctx())


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
            name=name.strip(), target=target.strip(),
            description=description.strip(),
            output_dir=output_dir.strip() or None,
        )
    except ProjectCreateError as e:
        return templates.TemplateResponse(
            request, "new_project.html",
            _new_project_ctx(
                form={"name": name, "target": target, "description": description, "output_dir": output_dir},
                error=str(e),
            ),
            status_code=400,
        )
    return RedirectResponse(url=f"/projects/{proj.name}", status_code=303)


# --- Project shell: overview + top-level nav -------------------------------

@app.get("/projects/{name}", response_class=HTMLResponse)
def project_overview(request: Request, name: str):
    proj = _require_project(name)
    return templates.TemplateResponse(
        request, "project.html",
        _project_ctx(proj, active_stage="overview"),
    )


@app.get("/projects/{name}/findings", response_class=HTMLResponse)
def project_findings_all(request: Request, name: str):
    proj = _require_project(name)
    items = []
    for run in proj.runs():
        for f in run.findings():
            items.append({"run": run, "finding": f})
    return templates.TemplateResponse(
        request, "project_findings_all.html",
        _project_ctx(proj, active_stage="findings", findings=items),
    )


@app.get("/projects/{name}/runs", response_class=HTMLResponse)
def project_runs(request: Request, name: str):
    proj = _require_project(name)
    return templates.TemplateResponse(
        request, "project_runs.html",
        _project_ctx(proj, active_stage="runs", run_lane=lambda r: lane_for(r.kind)),
    )


# --- Per-stage lane pages (shared template) -------------------------------

def _stage_page(request: Request, name: str, stage: str):
    proj = _require_project(name)
    return templates.TemplateResponse(
        request, "project_stage.html",
        _project_ctx(
            proj, active_stage=stage,
            stage_key=stage,
            stage_label=STAGE_LABELS.get(stage, stage),
            stage_desc=STAGE_DESCRIPTIONS.get(stage, ""),
            stage_runs=_stage_runs(proj, stage),
            cli_hint=_cli_hint(stage, proj),
        ),
    )


@app.get("/projects/{name}/understand", response_class=HTMLResponse)
def project_understand(request: Request, name: str):
    return _stage_page(request, name, "understand")


@app.get("/projects/{name}/scan", response_class=HTMLResponse)
def project_scan(request: Request, name: str):
    return _stage_page(request, name, "scan")


@app.get("/projects/{name}/validate", response_class=HTMLResponse)
def project_validate(request: Request, name: str):
    return _stage_page(request, name, "validate")


@app.get("/projects/{name}/fuzz", response_class=HTMLResponse)
def project_fuzz(request: Request, name: str):
    return _stage_page(request, name, "fuzz")


@app.get("/projects/{name}/crash-analysis", response_class=HTMLResponse)
def project_crash_analysis(request: Request, name: str):
    return _stage_page(request, name, "crash-analysis")


@app.get("/projects/{name}/oss-forensics", response_class=HTMLResponse)
def project_oss_forensics(request: Request, name: str):
    return _stage_page(request, name, "oss-forensics")


# --- Artifacts / meta -----------------------------------------------------

@app.get("/projects/{name}/exploits", response_class=HTMLResponse)
def project_exploits(request: Request, name: str):
    proj = _require_project(name)
    return templates.TemplateResponse(
        request, "project_exploits.html",
        _project_ctx(proj, active_stage="exploits", exploits=list_exploits(proj)),
    )


@app.get("/projects/{name}/patches", response_class=HTMLResponse)
def project_patches(request: Request, name: str):
    proj = _require_project(name)
    return templates.TemplateResponse(
        request, "project_patches.html",
        _project_ctx(proj, active_stage="patches", patches=list_patches(proj)),
    )


@app.get("/projects/{name}/reports", response_class=HTMLResponse)
def project_reports(request: Request, name: str):
    proj = _require_project(name)
    return templates.TemplateResponse(
        request, "project_reports.html",
        _project_ctx(proj, active_stage="reports", reports=list_reports(proj)),
    )


@app.get("/projects/{name}/activity", response_class=HTMLResponse)
def project_activity(request: Request, name: str):
    proj = _require_project(name)
    return templates.TemplateResponse(
        request, "project_activity.html",
        _project_ctx(proj, active_stage="activity", activity=tail_activity(proj)),
    )


@app.get("/projects/{name}/settings", response_class=HTMLResponse)
def project_settings(request: Request, name: str):
    proj = _require_project(name)
    return templates.TemplateResponse(
        request, "project_settings.html",
        _project_ctx(proj, active_stage="settings"),
    )


# --- Per-run detail -------------------------------------------------------

def _require_run(proj: RaptorProject, run_name: str):
    run = next((r for r in proj.runs() if r.name == run_name), None)
    if run is None:
        raise HTTPException(404, f"run not found: {run_name}")
    return run


@app.get("/projects/{name}/runs/{run_name}", response_class=HTMLResponse)
def run_detail(request: Request, name: str, run_name: str):
    proj = _require_project(name)
    run = _require_run(proj, run_name)
    summary = summarize_run(run.directory)
    bundle = load_validation_bundle(run.directory) if summary.has_validation_bundle else None
    return templates.TemplateResponse(
        request, "run_detail.html",
        _project_ctx(
            proj, active_stage="runs",
            run=run, summary=summary, bundle=bundle,
        ),
    )


@app.get(
    "/projects/{name}/runs/{run_name}/findings", response_class=HTMLResponse
)
def run_findings(request: Request, name: str, run_name: str):
    proj = _require_project(name)
    run = _require_run(proj, run_name)
    return templates.TemplateResponse(
        request, "findings.html",
        _project_ctx(
            proj, active_stage="runs",
            run=run, findings=run.findings(),
        ),
    )


# --- Global settings ------------------------------------------------------

def _settings_ctx(**overrides):
    config = load_models_config()
    ctx = {
        "config": config,
        "roles": list(ROLES),
        "providers": list(PROVIDERS),
        "role_descriptions": ROLE_DESCRIPTIONS,
        "env_status": env_status(),
        "budget_cap": current_budget_cap(),
        "saved": False,
        "error": None,
    }
    ctx.update(overrides)
    return _ctx(**ctx)


@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    return templates.TemplateResponse(request, "settings.html", _settings_ctx())


@app.post("/settings")
async def settings_save(request: Request):
    form = await request.form()
    entries: list[ModelEntry] = []
    for role in ROLES:
        provider = (form.get(f"{role}__provider") or "").strip()
        model = (form.get(f"{role}__model") or "").strip()
        api_key = (form.get(f"{role}__api_key") or "").strip()
        if not provider and not model and not api_key:
            continue
        entries.append(ModelEntry(provider=provider, model=model, api_key=api_key, role=role))
    try:
        save_models_config(ModelConfig(entries=entries, raw_path=RAPTOR_MODELS_CONFIG), RAPTOR_MODELS_CONFIG)
    except OSError as e:
        return templates.TemplateResponse(
            request, "settings.html",
            _settings_ctx(error=f"Could not write {RAPTOR_MODELS_CONFIG}: {e}"),
            status_code=500,
        )
    return templates.TemplateResponse(request, "settings.html", _settings_ctx(saved=True))


# --- Health ---------------------------------------------------------------

@app.get("/api/health")
def health():
    return JSONResponse({
        "status": "ok",
        "app": APP_TITLE,
        "projects_dir": str(RAPTOR_PROJECTS_DIR),
        "projects_dir_exists": RAPTOR_PROJECTS_DIR.is_dir(),
        "models_config": str(RAPTOR_MODELS_CONFIG),
        "models_config_exists": RAPTOR_MODELS_CONFIG.is_file(),
    })
