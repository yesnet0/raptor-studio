"""Tests for run_spec command-building."""

from __future__ import annotations

from pathlib import Path

import pytest

from studio.services.run_spec import (
    CLAUDE_ONLY_KINDS,
    RUNNABLE_KINDS,
    UnsupportedKind,
    build_command,
    claude_cli_hint,
    is_runnable,
)


def test_is_runnable_returns_true_for_pure_python_kinds():
    assert is_runnable("agentic")
    assert is_runnable("scan")
    assert is_runnable("codeql")
    assert is_runnable("fuzz")


def test_is_runnable_returns_false_for_claude_only_kinds():
    assert not is_runnable("understand")
    assert not is_runnable("validate")
    assert not is_runnable("oss-forensics")
    assert not is_runnable("crash-analysis")


def test_build_command_agentic_minimal(tmp_path: Path):
    argv = build_command("agentic", "/tmp/myapp", tmp_path, {})
    assert argv[0] == "python3"
    assert argv[1].endswith("raptor_agentic.py")
    assert "--repo" in argv
    assert "/tmp/myapp" in argv


def test_build_command_agentic_with_flags(tmp_path: Path):
    argv = build_command("agentic", "/tmp/app", tmp_path, {
        "policy_groups": "owasp,secrets",
        "max_findings": "5",
        "mode": "fast",
        "no_exploits": "on",
    })
    assert "--policy-groups" in argv
    assert "owasp,secrets" in argv
    assert "--max-findings" in argv
    assert "5" in argv
    assert "--mode" in argv
    assert "fast" in argv
    assert "--no-exploits" in argv


def test_build_command_scan_adds_fast_flags(tmp_path: Path):
    argv = build_command("scan", "/tmp/app", tmp_path, {})
    assert "--mode" in argv and "fast" in argv
    assert "--no-exploits" in argv
    assert "--no-patches" in argv


def test_build_command_codeql_language(tmp_path: Path):
    argv = build_command("codeql", "/tmp/app", tmp_path, {
        "language": "python",
        "validate_dataflow": "on",
        "visualize": "on",
    })
    assert argv[1].endswith("raptor_codeql.py")
    assert "--language" in argv and "python" in argv
    assert "--validate-dataflow" in argv
    assert "--visualize" in argv


def test_build_command_fuzz_requires_duration(tmp_path: Path):
    with pytest.raises(ValueError, match="Duration is required"):
        build_command("fuzz", "/tmp/bin", tmp_path, {})


def test_build_command_fuzz_with_options(tmp_path: Path):
    argv = build_command("fuzz", "/tmp/bin", tmp_path, {
        "duration": "600",
        "parallel": "4",
        "max_crashes": "10",
        "autonomous": "on",
        "goal": "find heap overflow",
    })
    assert argv[1].endswith("raptor_fuzzing.py")
    assert "--binary" in argv and "/tmp/bin" in argv
    assert "--duration" in argv and "600" in argv
    assert "--parallel" in argv and "4" in argv
    assert "--autonomous" in argv
    assert "--goal" in argv and "find heap overflow" in argv


def test_build_command_unsupported_kind_raises(tmp_path: Path):
    with pytest.raises(UnsupportedKind):
        build_command("validate", "/tmp/app", tmp_path, {})


def test_claude_cli_hint_returns_template_for_claude_only():
    hint = claude_cli_hint("validate", "/tmp/app", "myproj")
    assert "raptor project use myproj" in hint
    assert "/validate" in hint


def test_claude_cli_hint_returns_none_for_runnable():
    assert claude_cli_hint("agentic", "/tmp/app", "myproj") is None


def test_every_runnable_kind_has_target_arg_and_script():
    for kind, spec in RUNNABLE_KINDS.items():
        assert spec.script.endswith(".py")
        assert spec.target_arg in ("--repo", "--binary")
        assert spec.fields  # non-empty
