#!/usr/bin/env python3
"""
csession — Claude Code Session Manager
=======================================
Saves, restores, and manages Claude Code session context between chats.

Think of it like a PILOT'S LOGBOOK:
  - Every flight (session), the pilot logs: what happened, current altitude,
    fuel level, next waypoint. The next pilot reads the logbook and
    continues the flight from exactly where it was.

Usage:
  csession init [name]         Create .claude-session/ workspace
  csession save [-m "note"]    Snapshot current session state
  csession resume [--copy]     Generate resume prompt for new chat
  csession status              Show project health dashboard
  csession task add <text>     Add a task
  csession task done <ID>      Mark task as done (e.g. T01)
  csession task wip  <ID>      Mark task as in-progress
  csession task block <ID>     Mark task as blocked
  csession log <text>          Log a decision to DECISIONS.md
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def _force_utf8_output():
    """
    Make stdout/stderr safe for box-drawing characters and emoji.

    Analogy: like fitting a UNIVERSAL PLUG ADAPTER before you travel —
    the wall socket (Windows cp1252 console) can't take our plug (UTF-8),
    so we adapt once at the door instead of failing at every appliance.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:          # Python < 3.7, or a non-text stream
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass                          # Redirected/closed stream — leave it alone


_force_utf8_output()

# ─────────────────────────────────────────────
#  Paths
# ─────────────────────────────────────────────
WORKSPACE    = Path(".claude-session")
CONFIG_FILE  = WORKSPACE / "config.json"
PROJECT_FILE = WORKSPACE / "PROJECT.md"
PROGRESS_FILE= WORKSPACE / "PROGRESS.md"
SNAPSHOT_FILE= WORKSPACE / "SNAPSHOT.md"
DECISIONS_FILE= WORKSPACE / "DECISIONS.md"
RESUME_FILE  = WORKSPACE / "RESUME_PROMPT.md"
HISTORY_DIR  = WORKSPACE / "history"


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────
def run(cmd, fallback: str = "") -> str:
    """
    Run a command given as an ARGUMENT LIST and return stdout, or fallback.

    Deliberately no shell: shell=True routes through cmd.exe on Windows, where
    POSIX-isms like `2>/dev/null` and 'single quotes' are not understood and
    silently blank out the result. capture_output already swallows stderr, so
    no redirection is needed on any platform.
    """
    if isinstance(cmd, str):
        cmd = cmd.split()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            return fallback
        return r.stdout.strip() or fallback
    except Exception:
        return fallback


def read_file(path) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except Exception:
        return ""


def write_file(path, content: str):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def load_config() -> dict:
    return json.loads(read_file(CONFIG_FILE) or "{}")


def save_config(config: dict):
    write_file(CONFIG_FILE, json.dumps(config, indent=2))


def get_git_info() -> dict:
    """
    Gather git context — branch, commits, changed files.
    Analogy: like checking your car's dashboard before a trip —
    current speed (branch), odometer (commits), warning lights (changes).
    """
    in_git = run(["git", "rev-parse", "--is-inside-work-tree"]) == "true"
    if not in_git:
        return {
            "branch": "N/A (not a git repo)",
            "last_commit": "none",
            "recent_commits": "  (no git history)",
            "changed_files": "  (not tracked)"
        }
    return {
        "branch":         run(["git", "branch", "--show-current"], "detached"),
        "last_commit":    run(["git", "log", "-1", "--format=%h  %s  (%ar)"], "no commits yet"),
        "recent_commits": run(["git", "log", "-5", "--format=  - %h %s"], "  none"),
        "changed_files":  run(["git", "diff", "--stat", "HEAD"])
                          or run(["git", "status", "--short"], "  no changes"),
    }


STATUS_EMOJI = {"todo": "⬜", "wip": "🔄", "done": "✅", "blocked": "❌", "skip": "⏭️"}


def iter_task_rows(progress_text: str):
    """
    Yield (line_index, task_id, status_cell) for real task rows only.

    Analogy: like a TICKET INSPECTOR who only checks people holding tickets —
    the status legend and the HTML comments mention every emoji, but they are
    documentation, not passengers. Counting them inflates every statistic.

    A real row looks like:  | T04 | ⬜ | Some task | Notes |
    """
    in_comment = False
    for i, line in enumerate(progress_text.split("\n")):
        # Skip HTML comment blocks (the status legend lives inside one)
        if "<!--" in line:
            in_comment = "-->" not in line
            continue
        if in_comment:
            in_comment = "-->" not in line
            continue

        stripped = line.strip()
        if not stripped.startswith("|"):
            continue

        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) < 2:
            continue
        # Header row and the |---|---| separator are not tasks
        if not re.fullmatch(r"T\d+", cells[0], flags=re.IGNORECASE):
            continue

        yield i, cells[0].upper(), cells[1]


def count_tasks(progress_text: str) -> dict:
    """Count tasks by status, reading only the status column of real rows."""
    counts = {"done": 0, "wip": 0, "todo": 0, "blocked": 0}
    for _, _, status in iter_task_rows(progress_text):
        for key in counts:
            if STATUS_EMOJI[key] in status:
                counts[key] += 1
                break
    return counts


# ─────────────────────────────────────────────
#  Templates
# ─────────────────────────────────────────────
def project_template(name: str) -> str:
    return f"""# Project: {name}

## Goal
<!-- What are we building? What problem does it solve?
     Be specific — Claude reads this at the start of every new session. -->


## Tech Stack
<!-- Languages, frameworks, key libraries, versions -->


## Repository Structure
<!-- Briefly describe important dirs/files so Claude knows where things live -->
<!-- Example:
  src/          Main source code
  tests/        Unit and integration tests
  docs/         Documentation
  config/       Environment configs
-->


## Key Constraints
<!-- Non-negotiables: performance targets, deadlines, style guides, API limits -->


## Out of Scope
<!-- What are we explicitly NOT doing in this project? -->

"""


def progress_template() -> str:
    return """# Progress Tracker

## Current Phase
<!-- What phase are we in? e.g. "Phase 2: API integration" -->
Phase 1 — Setup

## Tasks
<!--
  Status legend:
    ⬜  TODO        — not started
    🔄  IN PROGRESS — actively being worked on
    ✅  DONE        — completed and verified
    ❌  BLOCKED     — waiting on something
    ⏭️  SKIPPED     — decided not to do
-->

| ID  | Status | Task                                | Notes                  |
|-----|--------|-------------------------------------|------------------------|
| T01 | ⬜     | Example: Set up project structure   |                        |
| T02 | ⬜     | Example: Write core module          |                        |
| T03 | ⬜     | Example: Add tests                  |                        |

## Blockers
<!-- What's currently in the way? -->
None

## Next Actions
<!-- Top 3 priorities for the next session — Claude reads this first -->
1. Start with T01
2.
3.
"""


def decisions_template() -> str:
    return """# Decision Log

<!--
  Log every significant decision made during the project.
  This is the project's MEMORY — why did we choose X over Y?
  Claude reads this to avoid re-questioning settled decisions.

  Format per entry:
    ### YYYY-MM-DD HH:MM — Short title
    **Decision:** What we decided
    **Reason:** Why
    **Alternatives considered:** What else was on the table
-->

"""


# ─────────────────────────────────────────────
#  Commands
# ─────────────────────────────────────────────
def cmd_init(args):
    """
    Initialize the .claude-session/ workspace.
    Like setting up a new PILOT'S LOGBOOK at the start of a mission —
    create all the pages, fill in the header info, ready to log.
    """
    if WORKSPACE.exists() and not getattr(args, "force", False):
        print("⚠️  .claude-session/ already exists.")
        print("    Use --force to reinitialize (this will reset templates, not history).")
        return

    WORKSPACE.mkdir(exist_ok=True)
    HISTORY_DIR.mkdir(exist_ok=True)

    name = getattr(args, "name", None) or Path.cwd().name

    config = {
        "project": name,
        "created": datetime.now().isoformat(),
        "session_count": 0,
        "last_saved": None
    }
    save_config(config)

    write_file(PROJECT_FILE, project_template(name))
    write_file(PROGRESS_FILE, progress_template())
    write_file(DECISIONS_FILE, decisions_template())

    print(f"\n✅  Initialized .claude-session/ for: {name}")
    print("\n📋  Your next steps:")
    print("   1️⃣   Edit  .claude-session/PROJECT.md    ← describe your project")
    print("   2️⃣   Edit  .claude-session/PROGRESS.md   ← add your tasks")
    print("   3️⃣   Run   csession save -m 'session note'  ← after each session")
    print("   4️⃣   Run   csession resume --copy           ← to start a new chat\n")


def cmd_save(args):
    """
    Snapshot the current session state.
    Like a SURGEON ending their shift — they write a transfer note:
    what was done, current patient status, what the next surgeon needs to do.
    """
    if not WORKSPACE.exists():
        print("❌  Workspace not found. Run: csession init [project-name]")
        sys.exit(1)

    git = get_git_info()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    config = load_config()
    config["session_count"] = config.get("session_count", 0) + 1
    config["last_saved"] = now
    save_config(config)

    note = getattr(args, "message", None) or "No session note provided."
    progress   = read_file(PROGRESS_FILE)
    decisions  = read_file(DECISIONS_FILE)
    tasks      = count_tasks(progress)

    snapshot = f"""# Session Snapshot
> Saved: {now}  |  Session #{config['session_count']}  |  Project: {config.get('project', 'unknown')}

## 📝 Session Note
{note}

## 🌿 Git Context
- **Branch:** `{git['branch']}`
- **Last Commit:** {git['last_commit']}

### Recent Commits
{git['recent_commits']}

### Changed / Staged Files
```
{git['changed_files']}
```

## 📊 Task Summary
| ✅ Done | 🔄 In Progress | ⬜ Todo | ❌ Blocked |
|---------|----------------|---------|-----------|
| {tasks['done']:^7} | {tasks['wip']:^14} | {tasks['todo']:^7} | {tasks['blocked']:^9} |

## 📋 Full Progress
{progress}

## 🗂️ Decisions Made
{decisions}
"""

    write_file(SNAPSHOT_FILE, snapshot)

    # Archive a timestamped copy
    archive_name = datetime.now().strftime("%Y%m%d_%H%M%S") + f"_session{config['session_count']}.md"
    write_file(HISTORY_DIR / archive_name, snapshot)

    # Also regenerate the resume prompt
    _write_resume_prompt(config, git, note, progress, decisions, tasks, now)

    print(f"\n✅  Session #{config['session_count']} saved.")
    print(f"📸  Snapshot  →  .claude-session/SNAPSHOT.md")
    print(f"📋  Resume    →  .claude-session/RESUME_PROMPT.md")
    print(f"🗄️   Archived  →  .claude-session/history/{archive_name}\n")


def _write_resume_prompt(config, git, last_note, progress, decisions, tasks, saved_at):
    """
    Build the RESUME_PROMPT.md — the single file you paste into a new chat.
    Analogy: like a RELAY RUNNER'S BATON — it carries all the momentum
    from the previous runner so the next one starts at full speed.
    """
    project = read_file(PROJECT_FILE)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    resume = f"""# ⚡ Claude Code Session Resume
> **Paste this entire file into a new Claude chat to continue your session.**
> Generated: {now} | Session #{config['session_count']} | Project: {config.get('project')}

---

## 🎯 Project Context

{project}

---

## 🌿 Git State

| Field         | Value                          |
|---------------|--------------------------------|
| Branch        | `{git['branch']}`              |
| Last Commit   | {git['last_commit']}           |

**Recent commits:**
{git['recent_commits']}

---

## 📋 Current Progress & Tasks

{progress}

---

## 🗂️ Key Decisions (Do Not Re-debate)

{decisions}

---

## 📝 Last Session Note

> {last_note}

---

## 📊 Quick Stats at Handoff

| ✅ Done | 🔄 In Progress | ⬜ Todo | ❌ Blocked |
|---------|----------------|---------|-----------|
| {tasks['done']:^7} | {tasks['wip']:^14} | {tasks['todo']:^7} | {tasks['blocked']:^9} |

---

## 🤖 Instructions for Claude

You are **resuming** a Claude Code session. Here is exactly what to do:

1. **Understand the state** — read the Project Context and Progress above carefully.
2. **Find the next task** — look for the first `🔄 IN PROGRESS` task, then the first `⬜ TODO`.
3. **Do not redo completed work** — `✅ DONE` tasks are finished and verified.
4. **Respect decisions** — the Decision Log captures settled choices; do not re-open them unless asked.
5. **Update as you go:**
   - Mark tasks `🔄` when you start them, `✅` when done.
   - Append significant new decisions to `.claude-session/DECISIONS.md`.
6. **Ask before large changes** — if something major isn't in the plan, confirm first.

**Begin by stating:**
- What you understand about the current project state
- Which task you're picking up next
- Any questions or blockers you see before starting

Go.
"""

    write_file(RESUME_FILE, resume)


def cmd_resume(args):
    """
    Display or copy the resume prompt.
    This is the BATON — the thing you hand to the next runner (chat session).
    """
    if not RESUME_FILE.exists():
        print("❌  No resume prompt found. Run: csession save -m 'your note'")
        sys.exit(1)

    content = read_file(RESUME_FILE)

    copy = getattr(args, "copy", False)
    if copy:
        try:
            import pyperclip
            pyperclip.copy(content)
            print("📋  Resume prompt copied to clipboard!")
            print("    Paste it into a new Claude chat and you're off. 🚀")
        except ImportError:
            print("⚠️   pyperclip not installed. To enable clipboard copy:")
            print("     pip install pyperclip")
            print("\n─── RESUME PROMPT ──────────────────────────────\n")
            print(content)
    else:
        print(content)


def cmd_status(args):
    """
    Show a quick dashboard of the project's current health.
    Like a MISSION CONTROL SCREEN — one glance tells you everything.
    """
    if not WORKSPACE.exists():
        print("❌  Workspace not found. Run: csession init")
        return

    config  = load_config()
    progress= read_file(PROGRESS_FILE)
    tasks   = count_tasks(progress)
    total   = sum(tasks.values())
    pct     = int((tasks["done"] / total * 100) if total > 0 else 0)

    # `init` writes last_saved as null, and dict.get()'s default only fires on a
    # MISSING key — never on a present-but-None one. `or` covers both.
    project    = config.get("project") or "unknown"
    sessions   = config.get("session_count") or 0
    last_saved = config.get("last_saved") or "never"

    bar_len = 30
    filled  = int(bar_len * pct / 100)
    bar     = "█" * filled + "░" * (bar_len - filled)

    print(f"\n┌─────────────────────────────────────────────────┐")
    print(f"│  📦  {project:<43}│")
    print(f"│  🔢  Sessions logged: {sessions:<26}│")
    print(f"│  🕐  Last saved:      {last_saved:<26}│")
    print(f"├─────────────────────────────────────────────────┤")
    print(f"│  Progress  [{bar}] {pct:>3}%  │")
    print(f"│                                                 │")
    print(f"│  ✅  Done:         {tasks['done']:<3}  ❌  Blocked:   {tasks['blocked']:<3}      │")
    print(f"│  🔄  In Progress:  {tasks['wip']:<3}  ⬜  Todo:      {tasks['todo']:<3}      │")
    print(f"└─────────────────────────────────────────────────┘\n")

    if tasks["blocked"] > 0:
        print("⚠️   You have blocked tasks — check PROGRESS.md")
    if tasks["wip"] > 1:
        print("💡  Tip: More than one task in progress. Consider focusing.")
    print()


def cmd_task(args):
    """
    Manage tasks in PROGRESS.md.
    Each task is like a KANBAN CARD — it moves from Todo → In Progress → Done.
    """
    if not PROGRESS_FILE.exists():
        print("❌  PROGRESS.md not found. Run: csession init")
        return

    progress = read_file(PROGRESS_FILE)
    action   = args.action
    text     = args.text or []

    if action == "list":
        print(progress)
        return

    if action == "add":
        if not text:
            print("❌  Provide task description. Example: csession task add 'Write unit tests'")
            return
        task_text = " ".join(text)
        lines     = progress.split("\n")

        # Derive the next ID from real rows only — scanning the whole file would
        # also pick up IDs mentioned in prose ("1. Start with T01") or in notes.
        rows      = list(iter_task_rows(progress))
        next_num  = max((int(tid[1:]) for _, tid, _ in rows), default=0) + 1
        next_id   = f"T{next_num:02d}"
        new_row   = f"| {next_id} | ⬜     | {task_text:<35} |                        |"

        # Insert immediately after the last table row. Anchoring on "## Blockers"
        # instead lands the row after the template's blank line, and a blank line
        # terminates a markdown table — splitting it into two.
        if rows:
            insert_at = rows[-1][0] + 1
        elif "## Blockers" in progress:
            insert_at = lines.index("## Blockers")
        else:
            insert_at = len(lines)

        lines.insert(insert_at, new_row)
        write_file(PROGRESS_FILE, "\n".join(lines))
        print(f"✅  Added {next_id}: {task_text}")
        return

    # Status-change actions
    status_map = {
        "done":  "✅",
        "wip":   "🔄",
        "block": "❌",
        "skip":  "⏭️",
    }
    all_statuses = ["⬜", "🔄", "✅", "❌", "⏭️"]

    if not text:
        print(f"❌  Provide a task ID. Example: csession task {action} T01")
        return

    task_id    = text[0].upper()
    new_status = status_map[action]
    lines      = progress.split("\n")

    # Match the ID *cell* exactly. A substring test against the whole line would
    # claim any row whose task text happens to mention another task's ID.
    target = next((i for i, tid, _ in iter_task_rows(progress) if tid == task_id), None)

    if target is None:
        print(f"❌  Task ID '{task_id}' not found in PROGRESS.md")
        return

    line = lines[target]
    for s in all_statuses:
        if s in line:
            lines[target] = line.replace(s, new_status, 1)
            break
    else:
        print(f"❌  {task_id} has no status cell to update.")
        return

    write_file(PROGRESS_FILE, "\n".join(lines))
    print(f"✅  {task_id} marked as {action} ({new_status})")


def cmd_log(args):
    """
    Append a decision to DECISIONS.md.
    Like writing in a ship's CAPTAIN'S LOG — every significant call gets recorded.
    """
    if not DECISIONS_FILE.exists():
        print("❌  Not initialized. Run: csession init")
        return

    decision = " ".join(args.text)
    now      = datetime.now().strftime("%Y-%m-%d %H:%M")

    entry = f"""
### {now}
**Decision:** {decision}
**Reason:** *(add why below)*
**Alternatives considered:** *(add what else was on the table)*

"""

    current = read_file(DECISIONS_FILE)
    write_file(DECISIONS_FILE, current + entry)
    print(f"✅  Decision logged to .claude-session/DECISIONS.md")
    print(f"    Edit the file to add 'Reason' and 'Alternatives considered'.")


# ─────────────────────────────────────────────
#  CLI Entry Point
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        prog="csession",
        description="Claude Code Session Manager — save and restore AI session context",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  csession init my-api-project
  csession save -m "Finished auth module, starting on user routes"
  csession resume --copy
  csession task add "Add rate limiting middleware"
  csession task done T03
  csession task wip  T04
  csession log "Chose JWT over sessions because the API is stateless"
  csession status
        """
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    # init
    p = sub.add_parser("init", help="Initialize session workspace in current directory")
    p.add_argument("name",    nargs="?", help="Project name (defaults to directory name)")
    p.add_argument("--force", action="store_true", help="Reinitialize existing workspace")
    p.set_defaults(func=cmd_init)

    # save
    p = sub.add_parser("save", help="Save a session snapshot (run after each Claude Code session)")
    p.add_argument("-m", "--message", metavar="NOTE", help="Brief description of what happened this session")
    p.set_defaults(func=cmd_save)

    # resume
    p = sub.add_parser("resume", help="Show the resume prompt to paste into a new Claude chat")
    p.add_argument("--copy", action="store_true", help="Copy to clipboard (requires: pip install pyperclip)")
    p.set_defaults(func=cmd_resume)

    # status
    p = sub.add_parser("status", help="Show project health dashboard")
    p.set_defaults(func=cmd_status)

    # task
    p = sub.add_parser("task", help="Manage tasks in PROGRESS.md")
    p.add_argument("action", choices=["add","done","wip","block","skip","list"])
    p.add_argument("text",   nargs="*", help="Task description (for add) or Task ID (for others, e.g. T03)")
    p.set_defaults(func=cmd_task)

    # log
    p = sub.add_parser("log", help="Log a decision to DECISIONS.md")
    p.add_argument("text", nargs="+", help="Decision text")
    p.set_defaults(func=cmd_log)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
