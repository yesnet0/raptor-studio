"""Build raptor subprocess invocations for UI-triggered runs.

Only raptor commands that have a pure-Python entry point are supported here.
Claude-Code-only commands (``/understand``, ``/validate``, ``/oss-forensics``,
``/crash-analysis``) can't be kicked off without a Claude Code session, so
the UI falls back to showing the CLI command for those.

Schema reference: docs/PYTHON_CLI.md + docs/ARCHITECTURE.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


class UnsupportedKind(ValueError):
    """Raised for kinds that don't have a pure-Python entry point."""


@dataclass
class FormField:
    name: str
    label: str
    kind: str = "text"   # text | select | checkbox | number
    required: bool = False
    default: str = ""
    placeholder: str = ""
    help: str = ""
    options: list[str] = None  # for select


@dataclass
class RunnableKind:
    kind: str
    label: str
    description: str
    script: str           # path relative to RAPTOR_HOME
    target_arg: str       # --repo or --binary
    fields: list[FormField]


# Kinds that can be executed as pure Python (no Claude Code needed).
RUNNABLE_KINDS: dict[str, RunnableKind] = {
    "agentic": RunnableKind(
        kind="agentic",
        label="Agentic (full workflow)",
        description="Scan + validate + exploit + patch in one pass. Highest coverage, highest cost.",
        script="raptor_agentic.py",
        target_arg="--repo",
        fields=[
            FormField("policy_groups", "Policy groups", kind="text", default="all",
                      placeholder="all | secrets,owasp | secrets,crypto",
                      help="Comma-separated Semgrep packs; 'all' uses everything."),
            FormField("max_findings", "Max findings to process", kind="number", default="20"),
            FormField("mode", "Mode", kind="select", default="thorough",
                      options=["fast", "thorough"]),
            FormField("no_exploits", "Skip exploit generation", kind="checkbox"),
            FormField("no_patches", "Skip patch generation", kind="checkbox"),
        ],
    ),
    "scan": RunnableKind(
        kind="scan",
        label="Scan (Semgrep only)",
        description="Semgrep static analysis; no CodeQL, no LLM, no exploits. Fast.",
        script="raptor_agentic.py",
        target_arg="--repo",
        fields=[
            FormField("policy_groups", "Policy groups", kind="text", default="owasp,secrets",
                      placeholder="owasp,secrets",
                      help="Comma-separated Semgrep packs."),
        ],
    ),
    "codeql": RunnableKind(
        kind="codeql",
        label="CodeQL (deep dataflow)",
        description="CodeQL with SMT path pre-screening. Slow but catches what Semgrep misses.",
        script="raptor_codeql.py",
        target_arg="--repo",
        fields=[
            FormField("language", "Language", kind="select", default="",
                      options=["", "python", "java", "javascript", "cpp", "go", "ruby", "csharp"],
                      help="Leave blank to auto-detect."),
            FormField("validate_dataflow", "Validate dataflow paths", kind="checkbox", default="on"),
            FormField("visualize", "Emit Mermaid diagrams", kind="checkbox", default="on"),
            FormField("analyze", "Run LLM exploitability analysis", kind="checkbox"),
        ],
    ),
    "fuzz": RunnableKind(
        kind="fuzz",
        label="Fuzz (AFL++)",
        description="Coverage-guided fuzzing of a compiled binary with autonomous corpus.",
        script="raptor_fuzzing.py",
        target_arg="--binary",
        fields=[
            FormField("duration", "Duration (seconds)", kind="number", default="300", required=True),
            FormField("parallel", "Parallel AFL instances", kind="number", default="1"),
            FormField("max_crashes", "Max crashes to analyse", kind="number", default="10"),
            FormField("autonomous", "Autonomous corpus", kind="checkbox", default="on",
                      help="Let raptor generate intelligent seeds from the binary strings."),
            FormField("goal", "Goal", kind="text",
                      placeholder="find heap overflow | find parser bugs | find RCE",
                      help="Optional goal-directed seed generation."),
            FormField("corpus", "Corpus dir", kind="text",
                      placeholder="/path/to/seeds",
                      help="Optional — mutually exclusive with autonomous."),
        ],
    ),
}


# Kinds whose invocation we describe but cannot launch (Claude-only).
CLAUDE_ONLY_KINDS: dict[str, str] = {
    "understand":     "claude\n/understand --map",
    "validate":       "claude\n/validate",
    "oss-forensics":  "claude\n/oss-forensics <github-url>",
    "crash-analysis": "claude\n/crash-analysis <bug-url> <repo-url>",
}


def is_runnable(kind: str) -> bool:
    return kind in RUNNABLE_KINDS


def build_command(
    kind: str,
    target: str,
    raptor_home: Path,
    form_values: dict[str, str] | None = None,
) -> list[str]:
    """Translate (kind, target, form_values) into an argv for subprocess.Popen.

    Raises UnsupportedKind if the kind has no Python entry point.
    Raises ValueError on missing required fields.
    """
    if kind not in RUNNABLE_KINDS:
        raise UnsupportedKind(f"Kind '{kind}' is not runnable from the UI.")
    spec = RUNNABLE_KINDS[kind]
    values = form_values or {}

    argv = ["python3", str(raptor_home / spec.script), spec.target_arg, target]

    # Append kind-specific args, matching what raptor expects.
    if kind == "agentic":
        if values.get("policy_groups"):
            argv += ["--policy-groups", values["policy_groups"]]
        if values.get("max_findings"):
            argv += ["--max-findings", str(values["max_findings"])]
        if values.get("mode"):
            argv += ["--mode", values["mode"]]
        if values.get("no_exploits"):
            argv += ["--no-exploits"]
        if values.get("no_patches"):
            argv += ["--no-patches"]
    elif kind == "scan":
        if values.get("policy_groups"):
            argv += ["--policy-groups", values["policy_groups"]]
        argv += ["--mode", "fast", "--no-exploits", "--no-patches"]
    elif kind == "codeql":
        if values.get("language"):
            argv += ["--language", values["language"]]
        if values.get("validate_dataflow"):
            argv += ["--validate-dataflow"]
        if values.get("visualize"):
            argv += ["--visualize"]
        if values.get("analyze"):
            argv += ["--analyze"]
    elif kind == "fuzz":
        if not values.get("duration"):
            raise ValueError("Duration is required for fuzzing.")
        argv += ["--duration", str(values["duration"])]
        if values.get("parallel"):
            argv += ["--parallel", str(values["parallel"])]
        if values.get("max_crashes"):
            argv += ["--max-crashes", str(values["max_crashes"])]
        if values.get("autonomous"):
            argv += ["--autonomous"]
        if values.get("goal"):
            argv += ["--goal", values["goal"]]
        if values.get("corpus"):
            argv += ["--corpus", values["corpus"]]

    return argv


def claude_cli_hint(kind: str, target: str, project_name: str) -> Optional[str]:
    """Return the CLI command a user should run manually for a Claude-only kind."""
    if kind not in CLAUDE_ONLY_KINDS:
        return None
    template = CLAUDE_ONLY_KINDS[kind]
    return f"raptor project use {project_name}\n{template}".replace("<github-url>", target or "<github-url>")
