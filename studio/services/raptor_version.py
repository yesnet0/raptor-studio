"""Read raptor's canonical version from its source checkout.

The truth is in ``$RAPTOR_HOME/core/config.py`` as a top-level constant::

    VERSION = "3.0.0"

We deliberately do not import raptor — its Python deps aren't guaranteed
to be installed in studio's venv, and this is the only thing we need
from it. A simple regex scrape is enough and cheap (cached once per
process).

Fallbacks in order:
  1. Regex-scrape ``VERSION = "..."`` from ``core/config.py``.
  2. ``git describe --tags --always`` inside ``$RAPTOR_HOME`` as a
     last-resort indicator if config.py is absent or malformed.
  3. Empty string — the template suppresses the pill when unknown.
"""

from __future__ import annotations

import re
import subprocess
from functools import lru_cache

from studio.config import RAPTOR_HOME

_VERSION_RE = re.compile(r'^\s*VERSION\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)


@lru_cache(maxsize=1)
def raptor_version() -> str:
    """Return raptor's version string, or ``""`` if it can't be read."""
    config = RAPTOR_HOME / "core" / "config.py"
    if config.is_file():
        try:
            match = _VERSION_RE.search(config.read_text())
            if match:
                return match.group(1).strip()
        except OSError:
            pass

    # Fallback: git describe on the raptor checkout
    if (RAPTOR_HOME / ".git").is_dir():
        try:
            out = subprocess.run(
                ["git", "describe", "--tags", "--always"],
                cwd=str(RAPTOR_HOME),
                capture_output=True, text=True, timeout=2,
            )
            if out.returncode == 0 and out.stdout.strip():
                tag = out.stdout.strip()
                # Strip leading "v" for consistency ("v3.0.0" → "3.0.0")
                return tag.lstrip("v")
        except (OSError, subprocess.TimeoutExpired):
            pass

    return ""
