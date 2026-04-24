"""Core validation logic for Claude Code slash-command files.

A slash-command file lives in ``.claude/commands/<name>.md`` (project-scoped)
or ``~/.claude/commands/<name>.md`` (user-scoped) and looks like::

    ---
    description: Brief description of what this command does.
    argument-hint: [optional arg pattern shown in completion]
    allowed-tools: Read, Edit, Bash(ls:*)
    model: sonnet
    ---

    The prompt body that Claude executes when the user invokes /<name>.

The frontmatter is optional (a body-only command works), but if present it
must parse cleanly and use recognized keys.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import yaml

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", re.DOTALL)

KNOWN_FIELDS = frozenset(
    {
        "description",
        "argument-hint",
        "allowed-tools",
        "disallowed-tools",
        "model",
        "disable-model-invocation",
    }
)

COMMAND_NAME_RE = re.compile(r"^[a-z][a-z0-9\-]{0,62}[a-z0-9]$|^[a-z]$")

MIN_DESCRIPTION_LEN = 10
MAX_DESCRIPTION_LEN = 500

SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("Anthropic API key", re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}")),
    ("OpenAI API key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("AWS access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("GitHub token", re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}")),
    ("Stripe live key", re.compile(r"sk_live_[A-Za-z0-9]{24,}")),
    ("Google API key", re.compile(r"AIza[0-9A-Za-z_\-]{35}")),
    ("generic PEM block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
)

KNOWN_MODELS = frozenset({"opus", "sonnet", "haiku", "inherit", "default"})


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class Issue:
    severity: Severity
    code: str
    message: str


@dataclass
class ValidationResult:
    path: str
    issues: list[Issue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(i.severity is Severity.ERROR for i in self.issues)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity is Severity.ERROR]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity is Severity.WARNING]


def _err(code: str, msg: str) -> Issue:
    return Issue(Severity.ERROR, code, msg)


def _warn(code: str, msg: str) -> Issue:
    return Issue(Severity.WARNING, code, msg)


def _check_filename(path_str: str) -> list[Issue]:
    """Command name comes from the filename without .md."""
    p = Path(path_str)
    if p.suffix not in ("", ".md"):
        # Only warn — users occasionally use .markdown or similar
        return [_warn("W001", f"command file should end in .md (got '{p.suffix}')")]
    name = p.stem
    if name and not COMMAND_NAME_RE.match(name):
        return [
            _err(
                "E001",
                f"command name '{name}' must be lowercase kebab-case, 1-64 chars, starting with a letter",
            )
        ]
    return []


def _check_frontmatter(data: dict) -> list[Issue]:
    issues: list[Issue] = []

    desc = data.get("description")
    if desc is None:
        issues.append(_warn("W100", "missing 'description' in frontmatter"))
    elif not isinstance(desc, str):
        issues.append(_err("E100", "'description' must be a string"))
    else:
        n = len(desc.strip())
        if n < MIN_DESCRIPTION_LEN:
            issues.append(
                _warn("W101", f"'description' is too short ({n} chars); aim for at least {MIN_DESCRIPTION_LEN}")
            )
        elif n > MAX_DESCRIPTION_LEN:
            issues.append(
                _err("E102", f"'description' is too long ({n} chars); keep under {MAX_DESCRIPTION_LEN}")
            )

    for tools_key in ("allowed-tools", "disallowed-tools"):
        if tools_key in data:
            v = data[tools_key]
            if not isinstance(v, (str, list)):
                issues.append(_err("E110", f"'{tools_key}' must be a string or list of strings"))
            elif isinstance(v, list):
                for i, item in enumerate(v):
                    if not isinstance(item, str):
                        issues.append(
                            _err("E111", f"'{tools_key}[{i}]' must be a string")
                        )

    if "argument-hint" in data:
        hint = data["argument-hint"]
        if not isinstance(hint, str):
            issues.append(_err("E120", "'argument-hint' must be a string"))

    if "model" in data:
        model = data["model"]
        if not isinstance(model, str):
            issues.append(_err("E130", "'model' must be a string"))
        elif model not in KNOWN_MODELS and not model.startswith(("claude-", "opus-", "sonnet-", "haiku-")):
            issues.append(
                _warn(
                    "W131",
                    f"'model' value '{model}' is unusual; expected one of {sorted(KNOWN_MODELS)} or a full model id",
                )
            )

    if "disable-model-invocation" in data:
        dmi = data["disable-model-invocation"]
        if not isinstance(dmi, bool):
            issues.append(_err("E140", "'disable-model-invocation' must be a boolean"))

    for key in data.keys():
        if key not in KNOWN_FIELDS:
            issues.append(_warn("W900", f"unknown frontmatter field '{key}'"))

    return issues


def validate_command_source(source: str, path: str = "<string>") -> ValidationResult:
    """Validate a slash-command file given its raw text."""
    result = ValidationResult(path=path)
    result.issues.extend(_check_filename(path))

    if not source.strip():
        result.issues.append(_err("E000", "file is empty"))
        return result

    frontmatter_match = FRONTMATTER_RE.match(source)
    body = source
    if frontmatter_match:
        fm_text = frontmatter_match.group(1)
        body = source[frontmatter_match.end():]
        try:
            data = yaml.safe_load(fm_text)
        except yaml.YAMLError as exc:
            result.issues.append(_err("E010", f"frontmatter is not valid YAML: {exc}"))
            return result

        if data is None:
            result.issues.append(_warn("W011", "frontmatter block is empty"))
        elif not isinstance(data, dict):
            result.issues.append(
                _err("E012", f"frontmatter must be a mapping, got {type(data).__name__}")
            )
        else:
            result.issues.extend(_check_frontmatter(data))

    # Body checks
    body_stripped = body.strip()
    if not body_stripped:
        result.issues.append(_err("E200", "command body is empty; no prompt for Claude to execute"))
    else:
        for label, pat in SECRET_PATTERNS:
            if pat.search(source):
                result.issues.append(_err("E300", f"possible {label} leaked in command file"))

    return result


def validate_command_file(path: str | Path) -> ValidationResult:
    p = Path(path)
    if not p.exists():
        r = ValidationResult(path=str(p))
        r.issues.append(_err("E000", f"file not found: {p}"))
        return r
    if not p.is_file():
        r = ValidationResult(path=str(p))
        r.issues.append(_err("E000", f"not a regular file: {p}"))
        return r
    try:
        source = p.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        r = ValidationResult(path=str(p))
        r.issues.append(_err("E000", f"file is not valid UTF-8: {exc}"))
        return r
    return validate_command_source(source, path=str(p))
