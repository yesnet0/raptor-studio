"""Write-side operations against raptor's project directory.

Implements a subset of raptor.core.project.ProjectManager — just enough
to create new projects from raptor-studio. Writes JSON files matching
raptor's schema exactly, so projects created here are indistinguishable
from projects created via `raptor project create`.

Schema source: raptor/core/project/project.py (ProjectManager.create)
and raptor/core/project/schema.py (validate_project).
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from studio.config import RAPTOR_OUTPUT_BASE, RAPTOR_PROJECTS_DIR
from studio.services import project_extras as extras_service
from studio.services.raptor_reader import RaptorProject

_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")


class ProjectCreateError(Exception):
    """Raised when create_project cannot produce a valid raptor project."""


def _validate_name(name: str) -> None:
    if not name or not name.strip():
        raise ProjectCreateError("Project name is required.")
    if name.startswith(".") or name.startswith("_"):
        raise ProjectCreateError("Project name cannot start with '.' or '_'.")
    if not _NAME_RE.match(name):
        raise ProjectCreateError(
            "Project name may only contain letters, numbers, hyphens, dots, "
            "and underscores, and must start with a letter or number."
        )


def create_project(
    name: str,
    target: str,
    description: str = "",
    output_dir: Optional[str] = None,
    notes: str = "",
    project_type: Optional[str] = None,
    binary: str = "",
    focus: str = "",
    language: str = "",
    projects_dir: Path = RAPTOR_PROJECTS_DIR,
    output_base: Path = RAPTOR_OUTPUT_BASE,
    studio_dir: Optional[Path] = None,
) -> RaptorProject:
    """Create a new raptor project and return its RaptorProject record.

    Mirrors raptor.core.project.ProjectManager.create for the canonical
    raptor schema (version, name, target, output_dir, created, description,
    notes). Studio-side extras (type, binary, focus, language) are persisted
    to a sidecar at $STUDIO_DATA_DIR/project-extras/<name>.json — raptor's
    CLI ignores them, which is intentional.

    For ``project_type == 'forensics'``, ``target`` is treated as a URL and
    is NOT path-resolved — URLs mangle under ``Path.resolve()``.

    Raises ProjectCreateError on validation or duplicate errors.
    """
    _validate_name(name)

    projects_dir = Path(projects_dir)
    projects_dir.mkdir(parents=True, exist_ok=True)

    project_file = projects_dir / f"{name}.json"
    if project_file.exists():
        raise ProjectCreateError(f"Project '{name}' already exists.")

    if project_type and project_type not in extras_service.PROJECT_TYPES:
        raise ProjectCreateError(
            f"Invalid project type '{project_type}'. "
            f"Expected one of {extras_service.PROJECT_TYPES}."
        )

    if not target or not target.strip():
        raise ProjectCreateError("Target is required.")

    target_stripped = target.strip()

    # Forensics targets are URLs; path-resolve would mangle them.
    if project_type == "forensics":
        if not _looks_like_url(target_stripped):
            raise ProjectCreateError(
                "Forensics projects need a URL target (e.g. https://github.com/owner/repo)."
            )
        resolved_target = target_stripped
    else:
        resolved_target = str(Path(target_stripped).expanduser().resolve())

    if output_dir:
        resolved_output = str(Path(output_dir).expanduser().resolve())
    else:
        resolved_output = str((Path(output_base).expanduser() / name).resolve())

    Path(resolved_output).mkdir(parents=True, exist_ok=True)

    data = {
        "version": 1,
        "name": name,
        "target": resolved_target,
        "output_dir": resolved_output,
        "created": datetime.now(timezone.utc).isoformat(),
        "description": description or "",
        "notes": notes or "",
    }
    project_file.write_text(json.dumps(data, indent=2) + "\n")

    # Studio sidecar — optional extras that don't fit raptor's schema.
    extras = extras_service.ProjectExtras(
        type=project_type,
        binary=(str(Path(binary).expanduser().resolve()) if binary else ""),
        focus=focus or "",
        language=language or "",
        created_via="studio",
    )
    if not extras.is_empty:
        extras_service.save(
            name, extras,
            studio_dir=studio_dir if studio_dir is not None else None,
        ) if studio_dir is not None else extras_service.save(name, extras)

    return RaptorProject(
        name=name,
        target=resolved_target,
        output_dir=Path(resolved_output),
        description=description or "",
        notes=notes or "",
        created=data["created"],
    )


def _looks_like_url(s: str) -> bool:
    return s.startswith(("http://", "https://", "git@", "ssh://"))
