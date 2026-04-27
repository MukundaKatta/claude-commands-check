# claude-commands-check

[![CI](https://github.com/MukundaKatta/claude-commands-check/actions/workflows/ci.yml/badge.svg)](https://github.com/MukundaKatta/claude-commands-check/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/claude-commands-check.svg)](https://pypi.org/project/claude-commands-check/)
[![Python](https://img.shields.io/pypi/pyversions/claude-commands-check.svg)](https://pypi.org/project/claude-commands-check/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A small Python linter for [Claude Code](https://claude.ai/code) **slash-command files** (`.claude/commands/*.md`).

It checks:

- filename is a valid command name (lowercase kebab-case)
- YAML frontmatter parses cleanly (when present — frontmatter is optional)
- `description` is present, reasonably long, and a string
- `allowed-tools` / `disallowed-tools` are a string or list of strings
- `argument-hint` is a string
- `model` is a recognized value (`opus`, `sonnet`, `haiku`, `inherit`, `default`, or a full model id)
- `disable-model-invocation` is a boolean
- command body is not empty (otherwise there's no prompt for Claude to run)
- no hardcoded API keys slipped into the body or frontmatter

## Install

```bash
pip install claude-commands-check
```

## Usage

Lint a single file:

```bash
claude-commands-check .claude/commands/my-cmd.md
```

Lint an entire commands directory:

```bash
claude-commands-check .claude/commands/
claude-commands-check ~/.claude/commands/
```

Exit status: `0` on no errors, `1` on any errors, `2` when no command files were found.

## Library API

```python
from claude_commands_check import validate_command_file

result = validate_command_file(".claude/commands/my-cmd.md")
for issue in result.errors:
    print(issue.code, issue.message)
```

## Issue codes

| Code | Severity | Meaning |
|------|----------|---------|
| E000 | error | file-level problem (missing, empty, not UTF-8) |
| E001 | error | filename is not a valid command name |
| E010 | error | frontmatter is not valid YAML |
| E012 | error | frontmatter is not a mapping |
| E100 | error | `description` is not a string |
| E102 | error | `description` is too long |
| E110 | error | `allowed-tools` / `disallowed-tools` is not a string or list |
| E111 | error | list item in tools field is not a string |
| E120 | error | `argument-hint` is not a string |
| E130 | error | `model` is not a string |
| E140 | error | `disable-model-invocation` is not a boolean |
| E200 | error | command body is empty |
| E300 | error | possible secret detected |
| W001 | warning | file does not end in `.md` |
| W011 | warning | frontmatter block is empty |
| W100 | warning | missing `description` |
| W101 | warning | `description` is too short |
| W131 | warning | unusual `model` value |
| W900 | warning | unknown frontmatter field |

## Use as a GitHub Action

Add this step to any workflow:

```yaml
- uses: actions/checkout@v5
- uses: MukundaKatta/claude-commands-check@v1
  with:
    paths: .claude/commands
```

The action runs the same checks as the CLI and fails the workflow on any errors. Inputs: `paths` (default `.claude/commands`), `quiet` (default `false`), `python-version` (default `3.12`).

## License

MIT