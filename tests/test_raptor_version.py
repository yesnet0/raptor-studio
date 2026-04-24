"""Tests for the raptor-version scrape."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


def _reload_version_with_home(home: Path):
    """Point RAPTOR_HOME at `home`, reload modules, return the fresh scraper."""
    import os
    os.environ["RAPTOR_HOME"] = str(home)
    from studio import config
    importlib.reload(config)
    if "studio.services.raptor_version" in sys.modules:
        importlib.reload(sys.modules["studio.services.raptor_version"])
    from studio.services import raptor_version as mod
    mod.raptor_version.cache_clear()
    return mod.raptor_version


def test_reads_version_from_core_config(tmp_path: Path):
    core = tmp_path / "core"
    core.mkdir()
    (core / "config.py").write_text('''
class RaptorConfig:
    VERSION = "3.4.5"
    OTHER = "noise"
''')
    fn = _reload_version_with_home(tmp_path)
    assert fn() == "3.4.5"


def test_returns_empty_when_no_raptor(tmp_path: Path):
    fn = _reload_version_with_home(tmp_path)
    assert fn() == ""


def test_falls_back_to_git_describe(tmp_path: Path, monkeypatch):
    # No core/config.py but a .git dir so the fallback path runs.
    (tmp_path / ".git").mkdir()

    class _Result:
        returncode = 0
        stdout = "v9.9.9-1-gabc1234\n"
        stderr = ""

    def fake_run(argv, **kw):
        assert argv[0] == "git"
        return _Result()

    monkeypatch.setattr("subprocess.run", fake_run)
    fn = _reload_version_with_home(tmp_path)
    # Leading 'v' stripped for consistency.
    assert fn() == "9.9.9-1-gabc1234"


def test_malformed_config_returns_empty(tmp_path: Path):
    core = tmp_path / "core"
    core.mkdir()
    (core / "config.py").write_text("x = 1\n")  # no VERSION constant
    fn = _reload_version_with_home(tmp_path)
    assert fn() == ""
