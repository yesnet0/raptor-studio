# raptor-studio

Web UI for [raptor](https://github.com/gadievron/raptor). Browse findings, trigger scans / fuzz / forensics, watch runs live, diff project versions, review exploit PoCs — without leaving the browser.

Companion project. Reads and writes raptor's project data (`~/.raptor/projects/*.json` + per-run output directories); projects created here are fully interchangeable with `raptor project create`. Eventual target: absorb into raptor upstream as `packages/studio/`.

**Status**: v0.0.1 — functionally complete, pre-absorption. 15 commits on `main`. 144 pytest pass + 1 skipped.

Design doc: [`docs/PRD.md`](docs/PRD.md). Design narrative: [`docs/UX_RECONCILIATION.md`](docs/UX_RECONCILIATION.md). Change log: [`docs/CHANGELOG.md`](docs/CHANGELOG.md).

---

## Quick start

Raptor itself needs to be cloned somewhere on disk:

```bash
git clone https://github.com/gadievron/raptor ~/Projects/raptor
```

Then:

```bash
cd ~/Projects/raptor-studio
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn studio.app:app --reload
# → http://localhost:8000
```

If you have no raptor projects yet, the Dashboard shows a Welcome card with a **Create your first project →** button. If you already have projects (either from raptor's CLI or from a previous studio session), they appear immediately.

Want to see a loaded demo? `PYTHONPATH=. .venv/bin/python scripts/seed_demo.py` creates three realistic projects (source analysis / binary fuzzing / OSS forensics) at `~/.raptor-studio-demo/projects/` — point the server there with `RAPTOR_PROJECTS_DIR=~/.raptor-studio-demo/projects`.

## Environment

| Variable | Default | Purpose |
|---|---|---|
| `RAPTOR_PROJECTS_DIR` | `~/.raptor/projects` | Where raptor stores project registry entries (read + write) |
| `RAPTOR_HOME` | `~/Projects/raptor` | Location of raptor source checkout (for subprocess triggering) |
| `RAPTOR_OUTPUT_BASE` | `$RAPTOR_HOME/out/projects` | Default base path for new projects' output dirs |
| `STUDIO_DATA_DIR` | `~/.raptor-studio` | Studio's own state: job queue DB, job logs, project-extras sidecars |
| `RAPTOR_MODELS_CONFIG` | `~/.config/raptor/models.json` | Raptor's per-role LLM config (read + written by Settings page) |

## Structure

```
studio/
├── app.py                              # FastAPI entry point, ~20 routes
├── config.py                           # env-driven runtime paths
├── services/
│   ├── raptor_reader.py                # read project.json + runs
│   ├── raptor_writer.py                # create projects (raptor-schema round-trip)
│   ├── project_extras.py               # studio-only sidecar (type / binary / focus / language)
│   ├── run_kind.py                     # classify runs into command families and lanes
│   ├── sarif_reader.py                 # SARIF 2.1.0 fallback for findings
│   ├── validation_reader.py            # /validate bundle + per-run artifact summary
│   ├── forensics_reader.py             # OSS-forensics walkthrough artifacts
│   ├── artifacts_reader.py             # exploits / patches / reports / activity
│   ├── diff_reader.py                  # new / carried / resolved finding classification
│   ├── models_reader.py                # ~/.config/raptor/models.json read+write
│   ├── personas.py                     # 10 raptor expert briefs + per-finding ranking
│   ├── jobs.py                         # SQLite-backed job queue
│   ├── worker.py                       # subprocess worker (daemon thread)
│   └── run_spec.py                     # kind → argv translation
├── templates/
│   ├── base.html                       # nav, inline CSS, dark/light, favicon
│   ├── dashboard.html                  # KPIs or welcome
│   ├── projects.html                   # project list
│   ├── new_project.html                # type-aware create form
│   ├── project_base.html               # shared project shell (adaptive sidebar)
│   ├── project.html                    # overview (lane cards + next-action CTA)
│   ├── project_runs.html               # flat runs list
│   ├── project_findings_all.html       # cross-run findings
│   ├── project_stage.html              # per-stage pages (Understand / Scan / …)
│   ├── project_diff.html               # diff view
│   ├── project_exploits.html           # …and patches, reports, jobs, activity, settings
│   ├── project_jobs.html
│   ├── project_new_run.html            # typed trigger form (Essentials + Advanced)
│   ├── run_detail.html                 # kind-aware per-run summary (incl. forensics)
│   ├── findings.html                   # per-run findings
│   ├── job_detail.html                 # job status + SSE log tail
│   ├── settings.html                   # raptor models.json editor
│   ├── personas.html                   # /personas browser
│   ├── glossary.html                   # /glossary
│   └── _finding_detail.html            # shared finding expansion block
└── static/
    └── velociraptor.png
```

Package layout deliberately mirrors what it would look like as `packages/studio/` inside raptor — path-moving is the only friction between this repo and an upstream PR.

## What it does

### Browsing
- Dashboard with cross-project KPIs (or welcome state when empty)
- Findings with raptor's full schema: `final_status`, verdict × impact, Stage E feasibility (protections + exploitation paths + chain_breaks + what_would_help), PoC payloads, Source/Sink/Flow, expert-persona cards
- Per-run detail: kind-aware artifact summary, scan metrics, fuzzing report, validation bundle counts, attack-surface Mermaid flowchart, OSS forensics walkthrough
- Diff two runs: new / carried / resolved with status-transition arrows
- Exploits / Patches / Reports / Activity browsers
- `/personas` global browser + `/glossary` with grouped concept cards

### Triggering
- Create projects (3 types: Source / Binary / Forensics; round-trips through raptor's CLI cleanly)
- Trigger runs via a SQLite job queue with a subprocess worker
- Pure-Python kinds (`scan`, `agentic`, `codeql`, `fuzz`): spawn `python3 raptor_*.py`
- Claude-backed kinds (`understand`, `validate`, `oss-forensics`, `crash-analysis`): wrap as `bash -c "raptor project use <name> && claude -p '<slash-command>'"`
- Live log streaming via SSE; cancel sends SIGTERM to the process group
- Every trigger form shows the **Equivalent CLI** so the UI is additive, not a wall

### Configuring
- Raptor's `~/.config/raptor/models.json` editable from `/settings` (4 role cards: analysis / code / consensus / fallback)
- Env-var fallback status table; `RAPTOR_MAX_COST` display
- Project-scoped settings page showing raptor's project.json + studio sidecar

## Roadmap

Everything the original brief asked for has shipped. Remaining work is additive polish:

- Dataflow SVG rendering (raptor writes `dataflow_*.svg`; embed on finding detail for CodeQL runs)
- Markdown rendering for `*.md` reports (currently raw `<pre>`)
- Coverage view (`gcov` + `checked_by` merge — "which files did raptor actually read?")
- Per-finding persona invocation — "Re-run with Exploit Developer persona" button
- Upstream absorption: propose on `gadievron/raptor`, then PR under `packages/studio/`

See [`docs/PRD.md`](docs/PRD.md) §8 for expected-value ordering.

## Tests

```bash
.venv/bin/pytest tests/
# 144 passed, 1 skipped
```

Breakdown: `test_raptor_reader` + `test_raptor_writer` (25) · `test_run_kind` (16) · `test_models_reader` (10) · `test_artifacts_reader` (7) · `test_sarif_reader` (6) · `test_validation_reader` (6) · `test_forensics_reader` (7) · `test_personas` (10) · `test_diff_reader` (9) · `test_run_spec` (14) · `test_jobs` (9) · `test_worker_integration` (4 — actually spawn subprocesses) · `test_project_extras` (10).

## License

MIT (matches raptor).
