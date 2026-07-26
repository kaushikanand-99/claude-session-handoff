# Changelog

All notable changes to `csession` will be documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- `csession history` — browse and restore past session snapshots
- `csession diff` — compare two session snapshots
- Shell completions (bash / zsh / fish)
- `csession sync` — push `.claude-session/` to a remote gist for team sharing

---

## [1.0.0] — 2026-05-27

### Added
- `csession init [name] [--force]` — initialize `.claude-session/` workspace
- `csession save [-m note]` — snapshot session state with git context
- `csession resume [--copy]` — generate resume prompt for a new chat
- `csession status` — project health dashboard with progress bar
- `csession task add|done|wip|block|skip|list` — full task lifecycle management
- `csession log <text>` — append decision entries to `DECISIONS.md`
- Claude Code Stop hook (`auto_save.py`) for automatic saving
- `install.sh` — one-command interactive installer
- Git integration: branch, last commit, recent history, changed files in every snapshot
- Session history archive (`history/` directory) with timestamped snapshots
- `pyproject.toml` for proper Python packaging
- Zero external dependencies (stdlib only, `pyperclip` optional)

---

[Unreleased]: https://github.com/kaushikanand-99/Claude-Session-Management-System/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/kaushikanand-99/Claude-Session-Management-System/releases/tag/v1.0.0
