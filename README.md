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

Phase 1 (read-only):
- [x] Projects list
- [x] Per-project run browser
- [x] Findings viewer
- [ ] Mermaid dataflow rendering
- [ ] Exploit PoC browser

Phase 2 (interactive):
- [x] Create new project (writes raptor-compatible JSON)
- [ ] Scan trigger from UI
- [ ] Live run monitoring
- [ ] Run diff (resolved / carried / new findings)

Phase 3 (upstream):
- [ ] Issue on gadievron/raptor proposing absorption
- [ ] PR to move code under `packages/studio/`

## License

MIT (matches raptor).
