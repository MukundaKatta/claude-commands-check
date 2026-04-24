"""Tests for claude-commands-check."""

from __future__ import annotations

import textwrap
from pathlib import Path

from claude_commands_check.validator import (
    Severity,
    validate_command_file,
    validate_command_source,
)


def _codes(issues) -> list[str]:
    return [i.code for i in issues]


def test_valid_minimal_with_frontmatter() -> None:
    source = textwrap.dedent(
        """\
        ---
        description: A valid slash command used for smoke testing this linter.
        ---

        Please do the thing.
        """
    )
    result = validate_command_source(source, path="my-cmd.md")
    assert result.ok


def test_valid_body_only() -> None:
    source = "Please do the thing.\n"
    result = validate_command_source(source, path="body-only.md")
    assert result.ok  # frontmatter optional


def test_empty_file() -> None:
    result = validate_command_source("", path="empty.md")
    assert "E000" in _codes(result.errors)


def test_empty_body() -> None:
    source = "---\ndescription: A long enough description for this test file.\n---\n\n"
    result = validate_command_source(source, path="empty-body.md")
    assert "E200" in _codes(result.errors)


def test_broken_yaml() -> None:
    source = "---\nallowed-tools: [unclosed\n---\nbody"
    result = validate_command_source(source, path="bad.md")
    assert "E010" in _codes(result.errors)


def test_frontmatter_must_be_mapping() -> None:
    source = "---\n- 1\n- 2\n---\nbody"
    result = validate_command_source(source, path="list-fm.md")
    assert "E012" in _codes(result.errors)


def test_description_too_short_warns() -> None:
    source = textwrap.dedent(
        """\
        ---
        description: short
        ---
        body
        """
    )
    result = validate_command_source(source, path="short.md")
    assert result.ok
    assert "W101" in _codes(result.warnings)


def test_allowed_tools_list_items_must_be_strings() -> None:
    source = textwrap.dedent(
        """\
        ---
        description: A valid long enough description for this slash command.
        allowed-tools:
          - Read
          - 42
        ---
        body
        """
    )
    result = validate_command_source(source, path="tools.md")
    assert "E111" in _codes(result.errors)


def test_allowed_tools_string_ok() -> None:
    source = textwrap.dedent(
        """\
        ---
        description: A valid long enough description for this slash command.
        allowed-tools: Read, Edit, Bash(ls:*)
        ---
        body
        """
    )
    result = validate_command_source(source, path="tools-str.md")
    assert result.ok


def test_argument_hint_must_be_string() -> None:
    source = textwrap.dedent(
        """\
        ---
        description: A valid long enough description for this slash command.
        argument-hint: 42
        ---
        body
        """
    )
    result = validate_command_source(source, path="argh.md")
    assert "E120" in _codes(result.errors)


def test_model_unknown_warns() -> None:
    source = textwrap.dedent(
        """\
        ---
        description: A valid long enough description for this slash command.
        model: gpt-5
        ---
        body
        """
    )
    result = validate_command_source(source, path="model.md")
    assert "W131" in _codes(result.warnings)


def test_model_inherit_ok() -> None:
    source = textwrap.dedent(
        """\
        ---
        description: A valid long enough description for this slash command.
        model: inherit
        ---
        body
        """
    )
    result = validate_command_source(source, path="model-ok.md")
    assert result.ok


def test_disable_model_invocation_must_be_bool() -> None:
    source = textwrap.dedent(
        """\
        ---
        description: A valid long enough description for this slash command.
        disable-model-invocation: "yes"
        ---
        body
        """
    )
    result = validate_command_source(source, path="dmi.md")
    assert "E140" in _codes(result.errors)


def test_unknown_field_warns() -> None:
    source = textwrap.dedent(
        """\
        ---
        description: A valid long enough description for this slash command.
        nonsense_field: whatever
        ---
        body
        """
    )
    result = validate_command_source(source, path="extra.md")
    assert result.ok
    assert "W900" in _codes(result.warnings)


def test_secret_leak_detected() -> None:
    source = textwrap.dedent(
        """\
        ---
        description: A valid long enough description for this slash command.
        ---

        My key is ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890 for testing.
        """
    )
    result = validate_command_source(source, path="leaky.md")
    assert "E300" in _codes(result.errors)


def test_bad_command_name_in_filename() -> None:
    source = "body\n"
    result = validate_command_source(source, path="BadName.md")
    assert "E001" in _codes(result.errors)


def test_validate_command_file_missing(tmp_path: Path) -> None:
    result = validate_command_file(tmp_path / "nope.md")
    assert "E000" in _codes(result.errors)


def test_validate_command_file_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "my-cmd.md"
    p.write_text(
        textwrap.dedent(
            """\
            ---
            description: A valid long enough description for this slash command.
            ---
            body
            """
        )
    )
    result = validate_command_file(p)
    assert result.ok


def test_severity_split() -> None:
    source = "---\n---\n"
    result = validate_command_source(source, path="bare.md")
    assert all(i.severity is Severity.ERROR for i in result.errors)
