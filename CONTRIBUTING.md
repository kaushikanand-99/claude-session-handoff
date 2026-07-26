# Contributing to csession

Thanks for your interest in contributing! `csession` is a small, focused tool — contributions that keep it that way are most welcome.

---

## Philosophy

`csession` follows three principles:

1. **Zero required dependencies** — stdlib only. The tool must work with a bare Python 3.8+ install, no internet, no pip. (`pyperclip` is the only optional exception.)
2. **Single-file CLI** — `csession.py` stays one file. It's easy to audit, copy into a project, and understand.
3. **Every function needs an analogy** — this project explains itself through real-world analogies (surgical handoff, relay baton, pilot's logbook). New features should include one.

---

## Getting Started

```bash
git clone https://github.com/kaushikanand-99/Claude-Session-Management-System.git
cd Claude-Session-Management-System

# Verify it works
python3 csession.py --help

# Run tests
python3 -m pytest tests/ -v
```

---

## How to Contribute

### Reporting a Bug

1. Search [existing issues](https://github.com/kaushikanand-99/Claude-Session-Management-System/issues) first.
2. Open a new issue using the **Bug Report** template.
3. Include: Python version, OS, command you ran, expected vs actual output.

### Suggesting a Feature

1. Open a new issue using the **Feature Request** template.
2. Describe the use case — *why* would this help, not just *what* it does.

### Submitting a Pull Request

1. Fork the repo and create a branch from `main`:
   ```bash
   git checkout -b feature/my-feature
   ```
2. Make your changes in `csession.py` (and tests in `tests/`).
3. Test manually:
   ```bash
   cd /tmp && mkdir test-project && cd test-project && git init
   python3 /path/to/csession.py init test
   python3 /path/to/csession.py task add "test task"
   python3 /path/to/csession.py save -m "test save"
   python3 /path/to/csession.py status
   ```
4. Run the test suite:
   ```bash
   python3 -m pytest tests/ -v
   ```
5. Open a PR with a clear description of what changed and why.

---

## What's Welcome

| Type | Welcome? | Notes |
|------|----------|-------|
| Bug fixes | ✅ Yes | Always |
| New commands (`history`, `diff`, etc.) | ✅ Yes | Open an issue to discuss first |
| Shell completions | ✅ Yes | bash, zsh, fish |
| Better git integration | ✅ Yes | Richer snapshot data |
| Tests | ✅ Yes | More coverage = more confidence |
| Refactor to multi-file | ❌ No | Single-file is a feature |
| External dependencies | ❌ No | Stdlib only |
| Cloud/API features | ❌ No | Local-first is a feature |

---

## Code Style

- Python 3.8+ compatible (no walrus operator, no `match` statements)
- Type hints where they add clarity
- Docstrings on every public function — include a one-sentence analogy
- Keep functions small and named after what they do, not how

---

## Questions?

Open a [Discussion](https://github.com/kaushikanand-99/Claude-Session-Management-System/discussions) — happy to help.
