# Changelog

## [0.1.0] - 2026-04-23

### Added
- Initial release.
- CLI `claude-commands-check` for linting Claude Code slash-command files in `.claude/commands/`.
- Library API: `validate_command_file`, `validate_command_source`, `ValidationResult`, `Issue`, `Severity`.
- Checks: filename format, optional YAML frontmatter validity, `description` quality, `allowed-tools` / `disallowed-tools` shape, `argument-hint` / `model` / `disable-model-invocation` types, non-empty body, and hardcoded secret detection.
- GitHub Actions CI on Python 3.9-3.13, and a release workflow publishing to PyPI via OIDC trusted publishing.
