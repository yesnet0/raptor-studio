# raptor-studio

Web UI for [raptor](https://github.com/gadievron/raptor) — browse findings, watch runs, diff project versions, review exploit PoCs.

Companion project. Consumes raptor's project data (`~/.raptor/projects/*.json` + per-run output directories) and renders it as a browsable web surface. Eventual target: absorb into raptor upstream as `packages/studio/`.

## Status

Early scaffold. Read-only. Not for production.

## Quick start

```bash
pip install -r requirements.txt
uvicorn studio.app:app --reload
# → http://localhost:8000
```

By default, reads projects from `~/.raptor/projects/`. Override with:

```bash
RAPTOR_PROJECTS_DIR=/path/to/projects uvicorn studio.app:app --reload
```

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
- [ ] Scan trigger from UI
- [ ] Live run monitoring
- [ ] Run diff (resolved / carried / new findings)

Phase 3 (upstream):
- [ ] Issue on gadievron/raptor proposing absorption
- [ ] PR to move code under `packages/studio/`

## License

MIT (matches raptor).
