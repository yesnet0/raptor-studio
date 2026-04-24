# raptor-studio

Web UI for [raptor](https://github.com/gadievron/raptor) — browse findings, watch runs, diff project versions, review exploit PoCs.

Companion project. Consumes raptor's project data (`~/.raptor/projects/*.json` + per-run output directories) and renders it as a browsable web surface. Eventual target: absorb into raptor upstream as `packages/studio/`.

## Status

Early scaffold. Read-only. Not for production.

## Quick start

Raptor itself should be cloned to `~/Projects/raptor/` (the default `RAPTOR_HOME`):

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

Projects created from the UI land in `~/.raptor/projects/<name>.json` — the same location raptor's own CLI uses, so they are fully interchangeable. Output dirs default to `$RAPTOR_HOME/out/projects/<name>`.

## Environment

| Variable | Default | Purpose |
|---|---|---|
| `RAPTOR_PROJECTS_DIR` | `~/.raptor/projects` | Where raptor stores project registry entries (read + write) |
| `RAPTOR_HOME` | `~/Projects/raptor` | Location of raptor source checkout |
| `RAPTOR_OUTPUT_BASE` | `$RAPTOR_HOME/out/projects` | Default base path for new projects' output dirs |
| `STUDIO_DATA_DIR` | `~/.raptor-studio` | Reserved: studio's own cache / provenance sidecars |
| `RAPTOR_MODELS_CONFIG` | `~/.config/raptor/models.json` | Raptor's per-role LLM config (read + written by Settings page) |

## Structure

```
studio/
├── app.py              # FastAPI entry point
├── config.py           # runtime paths from env
├── services/
│   └── raptor_reader.py    # read-only reader for raptor project data
├── templates/
│   ├── base.html       # shell, nav, inline CSS
│   ├── dashboard.html
│   ├── projects.html
│   ├── project.html
│   └── findings.html
└── static/
```

The package layout mirrors what it would look like as `packages/studio/` inside raptor — the intended eventual home.

## Roadmap

Phase 1 (raptor-literate read-only):
- [x] Projects list
- [x] Per-project sidebar with three pipeline lanes (source / binary / forensics)
- [x] Project overview with lane-status cards and next-action CTA
- [x] Findings viewer with raptor's full schema (`final_status`, verdict × impact, feasibility, chain_breaks, what_would_help, exploitation_paths, validation trail)
- [x] Runs list, per-stage pages (Understand / Scan / Validate / Fuzz / Crash analysis / OSS forensics)
- [x] Exploits, Patches, Reports browsers
- [x] Activity (JSONL audit log tail)
- [x] Global Settings: raptor's `~/.config/raptor/models.json` with per-role models (analysis / code / consensus / fallback), env-var status, budget cap display
- [ ] Mermaid dataflow rendering from `attack-surface.json` / `dataflow_*.json`

Phase 2 (interactive):
- [x] Create new project (writes raptor-compatible JSON to `~/.raptor/projects/`)
- [x] Save model configuration
- [x] Scan / agentic / codeql / fuzz trigger from UI (SQLite-backed job queue + subprocess worker)
- [x] Live run monitoring (SSE tailing `$STUDIO_DATA_DIR/job-logs/<id>.log`)
- [ ] Run diff (resolved / carried / new findings)
- [ ] OSS forensics walkthrough
- [ ] Per-persona panels on finding pages

Phase 3 (upstream):
- [ ] Issue on gadievron/raptor proposing absorption as `packages/studio/`
- [ ] PR

See [docs/UX_RECONCILIATION.md](docs/UX_RECONCILIATION.md) for the design rationale.

Phase 3 (upstream):
- [ ] Issue on gadievron/raptor proposing absorption
- [ ] PR to move code under `packages/studio/`

## License

MIT (matches raptor).
