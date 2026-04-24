# UX reconciliation: vulngraph patterns → raptor's actual shape

This document captures the design decisions that drive raptor-studio's information architecture. It's written for a reader who has touched vulngraph (from which we borrow) and is learning raptor (which we serve).

## TL;DR

Vulngraph has **one linear pipeline** (Ingest → Hunt → Precision → Pathways → Exploits → Report) because firmware RE is a sequential journey per binary. Raptor is a **branching framework** with three parallel lanes (source analysis, binary fuzzing, OSS forensics) that share a project container but do not compose into a single pipeline. The 240px project sidebar pattern carries over; the single six-stage pipeline inside it does not.

## What raptor actually is

From reading every file in `docs/` and `.claude/commands/`:

- **21 slash commands and 17 specialist agents.** This is not a tool; it's a framework with its own command system, agent taxonomy, progressive context loading, and budget controls.
- **Three execution modes that are mutually exclusive per run.** Source (`--repo`, Semgrep + CodeQL + LLM), binary (`--binary`, AFL++ + GDB + LLM), and OSS forensics (GitHub URL + GH Archive + Wayback). Not compose-able into one pipeline.
- **Two separate LLM layers.** Orchestration = Claude Code (always). Analysis = any provider via `~/.config/raptor/models.json`, with **four roles**: `analysis`, `code`, `consensus`, `fallback`.
- **Two-axis verdict model for findings.** `verdict` (exploitable / likely / difficult / unlikely / unknown) × `impact` (code_execution / dos / info_leak / resource_exhaustion / data_corruption / unknown). Null-deref can be `exploitable × dos`; format-string can be `exploitable × code_execution`. A single "severity" column is lossy.
- **Validation stages A–F on every finding.** A (not noise) → B (attacker reach + chain_breaks) → C (code verbatim, flow real) → D (not test code, not hedged) → E (binary feasibility with protections + glibc + ROP + constraints) → F (self-review). This is the core reasoning contribution; surfacing only "confidence: high/medium/low" throws it away.
- **Rich per-run artifacts beyond findings.** Attack surface, attack tree, hypotheses tried, disproven approaches, attack paths, checklist (ground truth), dataflow JSON + SVG, crash hypotheses (confirmed + rejected), rr traces, gcov coverage, exploit context with binary protections. Vulngraph has findings + exploits + pathways + diff. Raptor has an order of magnitude more kinds of artifact.
- **Nine expert personas** bound to specific packages (Exploit Developer → `llm_analysis/agent.py`, Crash Analyst → `llm_analysis/crash_agent.py`, etc.). Personas are a first-class UX primitive in raptor's CLI; they deserve surface area in the web UI too.
- **Budget is a real UX concern.** `RAPTOR_MAX_COST` caps spend per run; cost tracking is emitted per model call. Vulngraph doesn't model cost. We need to.

## What vulngraph's UX patterns do well — and what to keep

Kept wholesale:

- **Project as the container.** Everything hangs off a named project. Raptor agrees (via `/project`).
- **240px sidebar + main content shell.** Clean, proven. We use the same grid.
- **Expandable-row pattern for findings detail.** Works for raptor's rich per-finding data.
- **Dark mode by default, Inter + JetBrains Mono, monospace for paths/code.** Matches raptor's terminal heritage.
- **Stage indicators (○ pending / ◐ partial / ✓ complete).** The three-state visual is as useful for raptor as for vulngraph.
- **Empty states with configuration hints.** Raptor users will bounce off a web UI that shows nothing and explains nothing.
- **Card KPI layout on dashboard.** Kept.
- **Last-action CTA ("Next: Hunt →").** Kept, but computed per lane.

Adapted:

- **One pipeline sidebar → three-lane sidebar.** Overview + a "Navigation" cluster up top (Findings, Runs, Artifacts), then three grouped lanes (Source / Binary / Forensics), then Project meta (Activity, Settings). Each lane has its own numbered stages with their own status computation.
- **Composite score everywhere → two-axis verdict × impact, plus feasibility verdict when binary is present.** Users see `exploitable · code_execution · Full RELRO blocks GOT overwrite [binary]` instead of `composite 0.87`.
- **Mermaid attack-surface diagram → Mermaid from `attack-surface.json` (sources / sinks / trust boundaries).** Different data model, same affordance.

Dropped (do not apply):

- **COMPOSES_WITH graph edges.** Vulngraph-specific firmware concept; raptor doesn't chain findings that way.
- **EntryPoint `trust_level` with reachability math.** Different reachability model — raptor does path satisfiability via Z3 and CodeQL dataflow.
- **`disasm_hash` identity + firmware A/B diff.** Raptor diffs runs against the same repo (and uses git for source identity). Different axis.
- **"Precision hunt" 5-stage specialist pipeline.** Vulngraph-specific; raptor's equivalent is the A–F validation stages.

## Proposed information architecture

### Global nav (top)
- Dashboard · Projects · Settings

Dashboard shows cross-project stats (projects, active runs, findings by status, budget used). Settings is global (raptor's models.json + budget + default provider).

### Project sidebar (240px, left of every project page)
```
[Project Name]
target: /path/to/code
backend: source | binary | forensics

Overview                              (KPIs + next-action per lane)

── Navigation ──
Findings            (all, filterable)
Runs                (flat list, diff two)
Artifacts           (exploits + patches + reports)

── Source analysis ──
1. Understand       ○ / ◐ / ✓        (attack surface map)
2. Scan             ○ / ◐ / ✓        (Semgrep + CodeQL)
3. Validate         ○ / ◐ / ✓        (stages A–F)

── Binary fuzzing ──
1. Fuzz             ○ / ◐ / ✓        (AFL++ campaign)
2. Crash analysis   ○ / ◐ / ✓        (rr + hypotheses)

── Forensics ──
OSS forensics                        (investigate GitHub repo)

── Project ──
Activity                             (JSONL audit log)
Settings                             (project-scoped overrides)
```

Stage status is computed from run directories and `.raptor-run.json` command strings: e.g., "Scan" is ✓ if any run exists with command containing `scan`, `agentic`, or `codeql`; ◐ if any run is running; ○ if none.

### Routes (shipping in this iteration)

```
GET  /                                   dashboard (cross-project)
GET  /projects                           project list
GET  /projects/new                       new project form
POST /projects/new                       submit
GET  /projects/{name}                    overview (lane cards)
GET  /projects/{name}/findings           all findings, filtered by status/verdict/impact
GET  /projects/{name}/runs               flat run list, kind-typed
GET  /projects/{name}/runs/{run}         run detail (kind-aware)
GET  /projects/{name}/runs/{run}/findings
GET  /projects/{name}/understand         attack surface artifacts
GET  /projects/{name}/scan               scan runs overview
GET  /projects/{name}/validate           validation runs overview
GET  /projects/{name}/fuzz               fuzzing campaigns
GET  /projects/{name}/crash-analysis     crash analysis runs
GET  /projects/{name}/exploits           generated PoCs browser
GET  /projects/{name}/patches            generated patches browser
GET  /projects/{name}/reports            merged reports
GET  /projects/{name}/activity           JSONL audit tail
GET  /projects/{name}/settings           project overrides
GET  /settings                           global models + budget + personas
POST /settings                           update
```

### Findings view — raptor-literate

Finding row (collapsed):

```
[final_status]  [verdict × impact]  type   file:line                    [confidence]  ▶
exploitable     exploitable · RCE    cmd_injection   src/shell.py:42    high
```

Finding row (expanded):

- **Attack scenario** (one-paragraph prose)
- **Proof**: `source` · `sink` · `flow` (sequence)
- **Vulnerable code** (mono pre)
- **PoC payload + result** (mono pre)
- **Stage E feasibility** (if memory corruption): `binary_analysis.protections`, `exploitation_paths` (technique → target), `chain_breaks` tagged `[source]`/`[binary]`, `what_would_help`
- **Validation trail**: per-stage ruling (A/B/C/D/E/F) with pass/fail icon + reasoning quote

This is strictly richer than vulngraph's findings view — because raptor's data is strictly richer.

### Settings — raptor's actual knobs

Two sections:

1. **Models config (`~/.config/raptor/models.json`).** Four role cards (analysis / code / consensus / fallback); each holds provider + model + api_key_ref. We write the file and show which env vars are set as fallbacks. Budget input (`RAPTOR_MAX_COST`) lives here too.

2. **Project overrides.** Per-project overrides of the global defaults, written to a raptor-studio sidecar at `~/.raptor-studio/project-overrides/<name>.json` (raptor itself doesn't read this yet — these are studio-scoped until upstreamed).

We do not store API keys in plaintext on disk from the web UI unless the user explicitly chooses "store in file" — otherwise we write them to the system keyring or accept them only as env refs (`${ANTHROPIC_API_KEY}`).

## What shipped in this iteration

All of the below landed across two commits (`42ac26a`, `a follow-up`):

1. **IA reshape.** `project_base.html` shared shell with the three-lane sidebar, `project.html` rewritten as a lane-cards overview with next-action CTA, run-kind detection in `services/run_kind.py`, per-stage pages for every navigation item.
2. **Findings upgrade.** Raptor-literate findings template (`final_status` / `verdict` × `impact` / Stage E feasibility block with protections + exploitation_paths + chain_breaks + what_would_help), finding detail extracted to `_finding_detail.html` and shared between per-run and project-wide findings views.
3. **SARIF fallback.** `services/sarif_reader.py` parses Semgrep + CodeQL SARIF 2.1.0 into the same shape the rest of the UI expects. `RaptorRun.findings()` falls back to SARIF when no `findings.json` is present, so a plain `/scan` run renders its findings with zero extra config.
4. **Run-detail page.** `/projects/{name}/runs/{run}` shows kind + command + artifact summary (findings count, exploits, patches, scan metrics if present, fuzzing report if present, validation bundle counts). Deep-links down to findings / exploits / patches.
5. **Validation bundle reader.** `services/validation_reader.py` loads `findings.json`, `attack-tree.json`, `hypotheses.json`, `disproven.json`, `attack-paths.json`, `attack-surface.json`, `validation-report.md` in one call. `summarize_run()` feeds the run-detail page.
6. **Settings page.** `services/models_reader.py` reads + writes `~/.config/raptor/models.json` in raptor's exact schema. Four role cards (analysis / code / consensus / fallback), env-var status table, budget cap display. API-key env refs (`${ANTHROPIC_API_KEY}`) preserved; raw keys masked in display.
7. **Artifacts browsers.** Exploits, Patches, Reports, Activity pages walk the well-known subdirs of each run.
8. **Tests.** 23 → 78 (16 run_kind, 10 models_reader, 7 artifacts_reader, 6 sarif_reader, 6 validation_reader, 9 existing). All green.
9. **End-to-end.** 10/10 content-checks pass against a seeded project with a SARIF-only scan, a rich `/validate` run (full artifact bundle), and a `/fuzz` run (fuzzing_report + AFL crashes).

## What this iteration does not ship (punch-list for later)

- Run-diff view (needs identity model across runs)
- Coverage view (needs `gcov` reader and `checked_by` merge)
- OSS forensics lane detail (requires BigQuery/Wayback readers)
- Personas panel (context cards tied to finding type)

These are each an increment. The IA accommodates them.

## Shipped in the job-triggering pass

- **Job queue** (`services/jobs.py`) backed by SQLite at `$STUDIO_DATA_DIR/jobs.db`. Schema: `(id, project_name, kind, target, argv_json, status, created_at, started_at, finished_at, exit_code, pid, log_path, run_dir, error)`. Status machine: `queued → running → completed|failed|cancelled`.
- **Background worker** (`services/worker.py`) — daemon thread polling the queue, `subprocess.Popen` with `start_new_session=True` so we can cancel the whole process group, stdout+stderr redirected to `$STUDIO_DATA_DIR/job-logs/<id>.log`.
- **Run-spec translation** (`services/run_spec.py`) — four runnable kinds with typed form fields (`agentic`, `scan`, `codeql`, `fuzz`). Claude-only kinds (`understand`, `validate`, `oss-forensics`, `crash-analysis`) expose a CLI-hint fallback instead of a runnable form.
- **UI**:
  - `+ New run` button on every runnable stage page.
  - `/projects/{name}/{kind}/new` — typed form with live CLI preview.
  - `/projects/{name}/jobs` + `/jobs/{id}` — project + detail views.
  - `/jobs/{id}/cancel` — SIGTERM the process group, mark cancelled.
- **Live log tail via SSE** — `/api/jobs/{id}/stream` emits `event: log` and `event: status` frames; the job detail page consumes it with `EventSource`, auto-reloads on terminal status. Poll interval 0.4s; tails the log file by byte offset.
- **Sidebar** gains a "Jobs" entry under "Project".
- **Lifecycle** — worker `start()` on FastAPI startup, `stop()` on shutdown.

Tests: 78 → 103. New: `test_run_spec` (11), `test_jobs` (9), `test_worker_integration` (4 — actually spawns subprocesses).

End-to-end verified via TestClient: GET new-run form → POST → 303 redirect to `/jobs/{id}` → worker picks up → subprocess completes → log captured → detail page + project jobs list + API log endpoint all show the job correctly.

## Constraint: do not modify vulngraph

Vulngraph is referenced read-only at `~/Projects/vulngraph/vulngraph/web/`. We borrow layout grammar and CSS idioms. We do not import, link, or copy whole templates.
