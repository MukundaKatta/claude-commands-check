"""Tests for the claude-commands-check command-line interface."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from claude_commands_check import __version__
from claude_commands_check.cli import _collect_paths, _format_human, main
from claude_commands_check.validator import validate_command_source

VALID_CMD = textwrap.dedent(
    """\
    ---
    description: A valid long enough description for this slash command.
    ---
    Please do the thing.
    """
)

BAD_NAME_CMD = "body\n"  # filename drives the E001 error


def test_collect_paths_expands_directory(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text(VALID_CMD)
    (tmp_path / "b.md").write_text(VALID_CMD)
    (tmp_path / "notes.txt").write_text("ignored")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.md").write_text(VALID_CMD)

    collected = _collect_paths([str(tmp_path)])
    names = sorted(p.name for p in collected)
    # Only .md files, recursively; .txt is skipped.
    assert names == ["a.md", "b.md", "c.md"]


def test_collect_paths_keeps_explicit_file(tmp_path: Path) -> None:
    f = tmp_path / "explicit.md"
    f.write_text(VALID_CMD)
    collected = _collect_paths([str(f)])
    assert collected == [f]


def test_main_returns_zero_on_clean_file(tmp_path: Path, capsys) -> None:
    f = tmp_path / "good.md"
    f.write_text(VALID_CMD)
    rc = main([str(f)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "OK" in out
    assert "0 error(s)" in out


def test_main_returns_one_on_error(tmp_path: Path, capsys) -> None:
    f = tmp_path / "BadName.md"  # uppercase -> E001
    f.write_text(BAD_NAME_CMD)
    rc = main([str(f)])
    assert rc == 1
    out = capsys.readouterr().out
    assert "E001" in out


def test_main_no_files_found_returns_two(tmp_path: Path, capsys) -> None:
    # Empty directory: nothing to lint.
    rc = main([str(tmp_path)])
    assert rc == 2
    assert "no command files found" in capsys.readouterr().out


def test_main_quiet_hides_clean_and_warnings(tmp_path: Path, capsys) -> None:
    good = tmp_path / "good.md"
    good.write_text(VALID_CMD)
    rc = main([str(good), "--quiet"])
    assert rc == 0
    # Nothing is printed when quiet and there are no errors.
    assert capsys.readouterr().out == ""


def test_main_quiet_still_reports_errors(tmp_path: Path, capsys) -> None:
    good = tmp_path / "good.md"
    good.write_text(VALID_CMD)
    bad = tmp_path / "BadName.md"
    bad.write_text(BAD_NAME_CMD)
    rc = main([str(tmp_path), "--quiet"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "E001" in out
    # The clean file is suppressed in quiet mode.
    assert "good.md" not in out


def test_main_version_flag(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_format_human_counts_errors_and_warnings() -> None:
    # One file with a warning, one with an error.
    warn_result = validate_command_source(
        "---\ndescription: short\n---\nbody\n", path="warn.md"
    )
    err_result = validate_command_source("body\n", path="BadName.md")
    rendered = _format_human([warn_result, err_result])
    assert "2 file(s)" in rendered
    assert "1 error(s)" in rendered
    assert "1 warning(s)" in rendered
