# Changelog

Reverse-chronological. Each entry is one commit on `main`. Test counts are cumulative (pytest).

## 2026-04-23

### (next) — Embed CodeQL dataflow SVGs inline on run detail

- `services/validation_reader` detects `dataflow_*.svg` + paired `.json` in CodeQL run dirs.
- New safe file-serving route `GET /projects/{name}/runs/{run_name}/files/{filename:path}` with path-traversal check and extension whitelist (svg / png / md / json / sarif / txt).
- `run_detail.html` gains a "Dataflow diagrams" card with responsive thumbnail grid. Click opens full-size; paired JSON linked when present.
- Tests: 148 → 150.

### 1a1b686 — Align /projects/new with the full option matrix

- Rename `ProjectExtras.binary` → `ProjectExtras.source_repo` (the label was already "Source repo" but the field name was the confusing `binary`). Reader still accepts legacy `binary` key; writer accepts `binary=` kwarg as deprecated alias.
- Add `corpus_dir` field for binary projects — project-level default for the fuzz trigger form.
- Add `vendor_report_url` field for forensics projects — automatically appended to the `/oss-forensics` slash-command prompt as "validate claims in <url>".
- `app.py` adds `_default_run_values()` helper; the fuzz trigger form's `corpus` input and the oss-forensics slash-command both pick up project-level defaults.
- Tests: 144 → 148.

### 0f10c50 — Docs refresh

- New `docs/PRD.md` canonical product doc (10 sections).
- New `docs/CHANGELOG.md` (this file).
- Updated `README.md` with accurate status, structure, and roadmap.
- Updated `docs/UX_RECONCILIATION.md` with "Shipped in…" sections for the last two passes.

### ace3ef8 — Newcomer UX pass

Design thesis: easy for newcomers, not dumbed down, options surfaced without overwhelm. Six moves:

1. Welcoming zero-state on the Dashboard (single welcome card when no projects, worker KPI when populated).
2. Progressive disclosure on `/projects/new` (4 essentials + `<details>` Advanced + smart-name JS from target basename).
3. Type-adaptive sidebar (irrelevant lanes collapsed into "Other capabilities" for typed projects).
4. Contextual empty-state CTAs on `/findings`, `/runs`, `/exploits`, `/patches`, `/reports`.
5. Progressive disclosure on trigger forms (Essentials + `<details>` Advanced, localStorage-sticky per kind).
6. Inline `<abbr>` tooltips + new `/glossary` page covering 6 concept groups.

Template + routing only. Zero service-layer change. 144 tests pass.

### 6a86777 — Project types + Claude-backed triggers

- `/projects/new` gains a 3-card project type picker (Source / Binary / Forensics). Form adapts per type; forensics URL targets preserved as-is.
- `project_extras` sidecar at `$STUDIO_DATA_DIR/project-extras/<name>.json` for studio-only metadata (type, binary, focus, language). Raptor's schema untouched.
- Claude-backed kinds (`understand`, `validate`, `oss-forensics`, `crash-analysis`) become runnable via `bash -c "raptor project use <name> && claude -p '<slash-command>'"`. Each has a typed form.
- Tests: 135 → 144 (+10 project_extras, +4 claude-backed run_spec coverage).

### b7aa80c — Seed demo script

`scripts/seed_demo.py` creates three representative projects (source-analysis webapp with two scans + full validate bundle, binary-fuzz project with AFL crashes + generated exploits, OSS forensics investigation with three hypothesis iterations). Used for screenshot tours.

### bde028a — Velociraptor avatar

Pixel-art raptor PNG at `studio/static/velociraptor.png` replaces the coral "R" letter-mark in the nav and serves as the browser favicon. Dark mode uses `filter: invert(1)` so the white PNG background disappears against dark nav.

## Earlier

### c2760e8 — Doc update

`docs/UX_RECONCILIATION.md` extended with the "Shipped in the diff + forensics + personas pass" section.

### 559d162 — Per-persona panels on findings

- `services/personas.py` reads the 10 raptor expert briefs at `$RAPTOR_HOME/tiers/personas/*.md` and maps them to findings by vuln category / tool origin / status / filename hints.
- Inline cards on every expanded finding (capped at 4, ranked by specificity).
- `/personas` global browser.
- Tests: 119 → 128.

### 2ba6866 — OSS forensics walkthrough

- `services/forensics_reader.py` loads `evidence.json`, `evidence-verification-report.md`, `hypothesis-*.md` iterations, and `forensic-report.md`.
- Run detail gains a "Forensic investigation walkthrough" card with research question, evidence count table, hypothesis timeline (confirmed/rejected badges), and the final report.
- Tests: 112 → 119.

### a70c8a8 — Run diff

- `services/diff_reader.py` classifies findings across two runs into new / carried / resolved using raptor's SARIF dedup identity `(file, line, normalized_vuln_type)`.
- `/projects/{name}/diff?a=&b=` with dropdowns + three coloured tables. Carried rows surface status and verdict transitions.
- Tests: 103 → 112.

### 3fac61d — Job queue + SSE log streaming

- `services/jobs.py` SQLite-backed queue; `services/worker.py` daemon thread spawning `subprocess.Popen(start_new_session=True)` for cancellable process groups.
- `services/run_spec.py` translates 4 runnable kinds (agentic / scan / codeql / fuzz) into argv.
- SSE endpoint `/api/jobs/{id}/stream` tails the log by byte offset at 0.4s.
- `POST /jobs/{id}/cancel` SIGTERMs the group.
- Tests: 78 → 103 (incl. 4 real-subprocess integration tests).

### a4399af — Attack-surface Mermaid

When a run has `attack-surface.json`, `run_detail.html` renders a `sources → trust-boundaries → sinks` Mermaid flowchart plus three structured lists. Strict `securityLevel`. Theme synced to dark/light toggle.

### 05c8cf2 — SARIF fallback + run detail + validation bundle

- `services/sarif_reader.py` parses SARIF 2.1.0 to raptor's finding shape; `RaptorRun.findings()` falls back when no `findings.json` exists.
- `/projects/{name}/runs/{run}` run-detail page with kind-aware summary.
- `services/validation_reader.py` loads all 8 `/validate` artifacts in one call.
- Tests: 66 → 78.

### 42ac26a — Three-lane IA reshape

- Shared `project_base.html` shell with three-lane sidebar.
- `services/run_kind.py` classifies runs and computes lane status.
- Findings template upgraded to raptor's full schema (`final_status`, verdict × impact, Stage E feasibility, chain_breaks, what_would_help, exploitation_paths, validation trail).
- Settings page for `~/.config/raptor/models.json`.
- Exploits / Patches / Reports / Activity browsers.
- Tests: 23 → 66.

### 90b5273 — Create project + raptor configured

- `services/raptor_writer.py` creates projects writing raptor's exact schema.
- Raptor cloned to `~/Projects/raptor/`. `bin/raptor project list` verified.
- Cross-schema test imports raptor's own `validate_project` and checks studio output.

### 64429e5 — Starlette 0.37+ compat

`TemplateResponse(request, name, ctx)` positional ordering for Python 3.14 / Starlette 0.37+.

### 2bf5061 — Initial scaffold

FastAPI + Jinja2 shell. Dashboard / Projects list / Projects detail / Findings. 7 tests.
