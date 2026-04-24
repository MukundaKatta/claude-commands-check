"""claude-commands-check: linter for Claude Code slash-command files."""

from claude_commands_check.validator import (
    Issue,
    Severity,
    ValidationResult,
    validate_command_file,
    validate_command_source,
)

__all__ = [
    "Issue",
    "Severity",
    "ValidationResult",
    "validate_command_file",
    "validate_command_source",
]

__version__ = "0.1.0"
