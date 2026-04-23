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
    projects_dir: Path = RAPTOR_PROJECTS_DIR,
    output_base: Path = RAPTOR_OUTPUT_BASE,
) -> RaptorProject:
    """Create a new raptor project and return its RaptorProject record.

    Mirrors raptor.core.project.ProjectManager.create: validates the name,
    rejects duplicates, resolves the target path, ensures the output dir
    exists, writes JSON with raptor's schema (version=1).

    Raises ProjectCreateError on validation or duplicate errors.
    """
    _validate_name(name)

    projects_dir = Path(projects_dir)
    projects_dir.mkdir(parents=True, exist_ok=True)

    project_file = projects_dir / f"{name}.json"
    if project_file.exists():
        raise ProjectCreateError(f"Project '{name}' already exists.")

    if not target or not target.strip():
        raise ProjectCreateError("Target path is required.")

    resolved_target = str(Path(target).expanduser().resolve())

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
        "notes": "",
    }
    project_file.write_text(json.dumps(data, indent=2) + "\n")

    return RaptorProject(
        name=name,
        target=resolved_target,
        output_dir=Path(resolved_output),
        description=description or "",
        notes="",
        created=data["created"],
    )
