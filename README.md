<div align="center">

```
 ██████╗███████╗███████╗███████╗██╗ ██████╗ ███╗   ██╗
██╔════╝██╔════╝██╔════╝██╔════╝██║██╔═══██╗████╗  ██║
██║     ███████╗█████╗  ███████╗██║██║   ██║██╔██╗ ██║
██║     ╚════██║██╔══╝  ╚════██║██║██║   ██║██║╚██╗██║
╚██████╗███████║███████╗███████║██║╚██████╔╝██║ ╚████║
 ╚═════╝╚══════╝╚══════╝╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝
```

**Claude Code Session Manager**

*Your AI coding assistant — but it never forgets.*

[![Python](https://img.shields.io/badge/python-3.8%2B-blue?style=flat-square&logo=python)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey?style=flat-square)]()
[![Claude Code](https://img.shields.io/badge/Claude%20Code-hooks%20supported-orange?style=flat-square)](https://docs.anthropic.com/en/docs/claude-code/hooks)

[Installation](#installation) · [Quick Start](#quick-start) · [Commands](#commands) · [How It Works](#how-it-works) · [Contributing](#contributing)

</div>

---

## The Problem

Every new Claude Code chat starts with **complete amnesia**.

You end up spending the first 10 minutes of every session re-explaining:
- What the project is
- What's already been done
- What's still broken
- Which architectural choices were made and why

`csession` fixes this in one paste.

---

## Demo

```
$ csession init payment-service
✅  Initialized .claude-session/ for: payment-service

$ csession task add "Set up Stripe integration"
✅  Added T01: Set up Stripe integration

$ csession task add "Implement webhook handler"
✅  Added T02: Implement webhook handler

# ... Claude Code session runs ...

$ csession save -m "Stripe keys wired up. Webhook handler failing on signature verification."
✅  Session #1 saved.
📸  Snapshot  →  .claude-session/SNAPSHOT.md
📋  Resume    →  .claude-session/RESUME_PROMPT.md
🗄️   Archived  →  .claude-session/history/20260526_143022_session1.md

$ csession resume --copy
📋  Resume prompt copied to clipboard!
    Paste it into a new Claude chat and you're off. 🚀

$ csession status

┌─────────────────────────────────────────────────┐
│  📦  payment-service                            │
│  🔢  Sessions logged: 1                         │
│  🕐  Last saved:      2026-05-26 14:30          │
├─────────────────────────────────────────────────┤
│  Progress  [████████░░░░░░░░░░░░░░░░░░░░░] 25%  │
│                                                 │
│  ✅  Done:         1    ❌  Blocked:   0        │
│  🔄  In Progress:  1    ⬜  Todo:      2        │
└─────────────────────────────────────────────────┘
```

---

## Table of Contents

- [How It Works](#how-it-works)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Commands](#commands)
- [Workspace Layout](#workspace-layout)
- [The 5 Files](#the-5-files)
- [Claude Code Hook](#claude-code-hook-phase-3)
- [Tips & Tricks](#tips--tricks)
- [Contributing](#contributing)
- [License](#license)

---

## How It Works

Think of it as a **surgical handoff between hospital shifts.**

When a surgeon ends their shift, they don't just say "good luck" — they write a structured transfer note:

> *"Patient stable. BP 120/80. Appendix removed at 14:30. Currently on amoxicillin. Monitor for infection. Next: review bloods at 08:00."*

The incoming surgeon reads it and continues care without re-examining everything.

`csession` does the same for Claude Code:

```
┌────────────────────────────────────────────────────────────────┐
│                        SESSION LOOP                            │
│                                                                │
│  ┌──────────────┐    csession save     ┌──────────────────┐   │
│  │  Claude Code │  ──────────────────► │  SNAPSHOT.md +   │   │
│  │  Session N   │                      │  RESUME_PROMPT   │   │
│  └──────────────┘                      └────────┬─────────┘   │
│                                                 │             │
│                                     csession resume --copy    │
│                                                 │             │
│  ┌──────────────┐                      ┌────────▼─────────┐   │
│  │  Claude Code │  ◄──────────────────  │  New Chat        │   │
│  │  Session N+1 │    paste prompt       │  (fresh window)  │   │
│  └──────────────┘                      └──────────────────┘   │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**With the Stop hook (Phase 3), saving is automatic.** The moment Claude Code finishes, the snapshot is written — you never need to remember.

---

## Installation

### One-line install (recommended)

```bash
bash install.sh
```

The script will:
1. Verify Python 3.8+
2. Optionally install `pyperclip` for clipboard support
3. Ask where to install (`/usr/local/bin`, `~/.local/bin`, or local)
4. Configure Claude Code hooks in `.claude/`
5. Initialize your `.claude-session/` workspace

### Manual install

```bash
# 1. Make csession.py executable and available on PATH
cp csession.py ~/.local/bin/csession
chmod +x ~/.local/bin/csession

# 2. Set up Claude Code Stop hook
mkdir -p .claude/hooks
cp .claude/hooks/auto_save.py .claude/hooks/auto_save.py
cp .claude/settings.json      .claude/settings.json

# 3. Initialize workspace
csession init my-project
```

### Requirements

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.8+ | Required |
| Git | Any | Optional — enriches snapshots with commit history |
| pyperclip | Any | Optional — enables `--copy` clipboard flag |

---

## Quick Start

```bash
# 1. Initialize in your project root
csession init my-project-name

# 2. Describe your project (the most important step)
#    Edit .claude-session/PROJECT.md

# 3. Add your tasks
csession task add "Set up database schema"
csession task add "Implement auth endpoints"
csession task add "Write integration tests"

# 4. Run Claude Code on your project as normal...

# 5. After the session, save with a note
csession save -m "DB schema done. Auth endpoints 70% complete — refresh token logic broken."

# 6. Start a new Claude chat
csession resume --copy   # ← copies RESUME_PROMPT.md to clipboard
#    Paste → Claude reads it → continues from exactly where you left off
```

---

## Commands

| Command | Description |
|---------|-------------|
| `csession init [name] [--force]` | Initialize `.claude-session/` workspace in current directory |
| `csession save [-m "note"]` | Snapshot current session state and regenerate resume prompt |
| `csession resume [--copy]` | Print (or copy) the resume prompt for a new chat |
| `csession status` | Show project health dashboard |
| `csession task add <text>` | Add a new task to `PROGRESS.md` |
| `csession task done <ID>` | Mark a task as ✅ done (e.g. `T03`) |
| `csession task wip <ID>` | Mark a task as 🔄 in progress |
| `csession task block <ID>` | Mark a task as ❌ blocked |
| `csession task skip <ID>` | Mark a task as ⏭️ skipped |
| `csession task list` | Print full `PROGRESS.md` |
| `csession log <text>` | Append a decision entry to `DECISIONS.md` |

### Task status legend

| Emoji | Status | Meaning |
|-------|--------|---------|
| ⬜ | TODO | Not started |
| 🔄 | IN PROGRESS | Actively being worked on |
| ✅ | DONE | Completed and verified |
| ❌ | BLOCKED | Waiting on something external |
| ⏭️ | SKIPPED | Decided not to do |

---

## Workspace Layout

```
your-project/
├── .claude-session/            ← The "memory bank" (commit this to git)
│   ├── config.json             ← Project metadata and session counter
│   ├── PROJECT.md              ← What are we building? (fill once)
│   ├── PROGRESS.md             ← Living task board with status emojis
│   ├── DECISIONS.md            ← Architectural decisions log
│   ├── SNAPSHOT.md             ← Auto-generated last-session summary
│   ├── RESUME_PROMPT.md        ← ← ← PASTE THIS into new Claude chats
│   └── history/                ← Every session archived with timestamp
│       ├── 20260526_143022_session1.md
│       └── 20260527_091144_session2.md
│
├── .claude/
│   ├── settings.json           ← Registers the Stop hook
│   └── hooks/
│       └── auto_save.py        ← Runs csession save automatically
│
├── csession.py                 ← The CLI (or installed system-wide)
└── install.sh                  ← One-command setup
```

---

## The 5 Files

### `PROJECT.md` — Fill once, update rarely

The project brief Claude reads at the start of every session. Like a **new employee's onboarding doc** — the more specific it is, the less Claude hallucinates context.

```markdown
# Project: payment-service

## Goal
REST API for processing Stripe payments, including subscriptions and webhooks.

## Tech Stack
Python 3.11 · FastAPI · PostgreSQL · Stripe SDK · Docker

## Key Constraints
- PCI-DSS: never log raw card data
- All endpoints must be idempotent
- Response time < 200ms on payment endpoints
```

### `PROGRESS.md` — The living task board

A markdown table Claude reads and updates as it works.

```
| ID  | Status | Task                               | Notes                    |
|-----|--------|------------------------------------|--------------------------|
| T01 | ✅     | Set up FastAPI project structure   |                          |
| T02 | ✅     | Configure Stripe SDK               | Using stripe-python 7.x  |
| T03 | 🔄     | Implement webhook handler          | Signature verify failing |
| T04 | ⬜     | Add subscription endpoints         |                          |
| T05 | ❌     | Load testing                       | Waiting on staging env   |
```

### `DECISIONS.md` — The "why" behind every choice

Prevents Claude from re-debating settled questions in future sessions.

> Without it: every session Claude might suggest *"maybe we should use Sessions instead of JWT?"*
> With it: Claude sees *"JWT chosen — API is stateless, needs mobile support"* and moves on.

### `SNAPSHOT.md` — Auto-generated by `csession save`

Rich snapshot including git branch, recent commits, changed files, task summary, and your session note. You never edit this directly.

### `RESUME_PROMPT.md` — The baton you hand to the next session

Compiled from all of the above. Contains everything Claude needs to resume. **This is the only file you paste into a new chat.**

---

## Claude Code Hook (Phase 3)

The Stop hook makes saving **completely automatic**. You never need to remember to run `csession save`.

```
Claude Code finishes or stops
           ↓
.claude/hooks/auto_save.py fires
           ↓
Calls: csession save -m "Auto-saved at HH:MM"
           ↓
.claude-session/SNAPSHOT.md       ← updated
.claude-session/RESUME_PROMPT.md  ← updated
.claude-session/history/[ts].md   ← archived
```

### Adding the hook to an existing `.claude/settings.json`

If you already have a settings file, merge in the Stop hook:

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/auto_save.py"
          }
        ]
      }
    ]
  }
}
```

> **Docs:** [Claude Code Hooks →](https://docs.anthropic.com/en/docs/claude-code/hooks)

---

## Tips & Tricks

**Keep `PROJECT.md` tight.** One precise sentence beats three vague paragraphs. Claude infers context from specificity.

**Use `csession log` immediately after decisions.** Don't wait. As soon as Claude suggests and you accept an approach, run:
```bash
csession log "Chose FastAPI over Flask for async support and Pydantic validation"
```

**Check `csession status` before every session.** 30 seconds of orientation saves 10 minutes of re-ramping.

**Commit `.claude-session/` to git.** The full session history becomes version-controlled, diffable, and shareable with teammates.

**The `history/` folder is your undo button.** Every `csession save` archives a timestamped snapshot. If you want to see what the project looked like two sessions ago, it's there.

**Multi-task warning:** If `csession status` shows 2+ tasks in progress, that's a signal to focus. Claude (like humans) context-switches poorly.

---

## Contributing

Contributions are welcome! Here's how to get started:

```bash
git clone https://github.com/yourusername/csession.git
cd csession
python3 csession.py --help   # verify it works
```

### What to contribute

- **Bug fixes** — open an issue first if it's non-trivial
- **New commands** — `csession history`, `csession diff`, etc.
- **Shell completions** — bash/zsh/fish support
- **Better git integration** — smarter changed-file summaries
- **Tests** — unit tests for commands

### Guidelines

- Keep it single-file (`csession.py`) — zero dependencies outside stdlib
- Every new feature needs a docstring with an analogy
- Test on macOS and Linux before PRing

See [CONTRIBUTING.md](CONTRIBUTING.md) for full details.

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

<div align="center">

Built for developers who want their AI to pick up where it left off.

**[⭐ Star this repo](https://github.com/yourusername/csession)** if `csession` saves you time.

</div>
