#!/usr/bin/env python3
"""
Claude Code — Stop Hook: auto_save.py
======================================
Automatically saves a session snapshot whenever Claude Code stops.

How it works:
  Claude Code calls this script on its Stop event.
  It receives a JSON payload on stdin describing why Claude stopped.
  We call `csession save` to snapshot the current state.

Analogy: Like a DASHCAM that auto-saves footage when the car turns off.
  You don't have to remember to save — it just happens.

Setup (in your project's .claude/settings.json):
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

Docs: https://docs.anthropic.com/en/docs/claude-code/hooks
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def main():
    # ── 1. Read the hook payload Claude Code sends on stdin ──────────────────
    payload = {}
    try:
        raw = sys.stdin.read()
        if raw.strip():
            payload = json.loads(raw)
    except (json.JSONDecodeError, Exception):
        pass  # Payload is optional; we continue regardless

    # ── 2. Only act if .claude-session/ workspace exists ─────────────────────
    workspace = Path(".claude-session")
    if not workspace.exists():
        # Workspace not initialized — skip silently
        sys.exit(0)

    # ── 3. Build an auto-save message from the hook context ──────────────────
    #   The Stop hook payload can include a "reason" or other metadata.
    #   We use it to make the snapshot note descriptive.
    reason   = payload.get("reason", "")
    hook_active = payload.get("stop_hook_active", False)
    timestamp = datetime.now().strftime("%H:%M")

    if reason:
        note = f"Auto-saved by Claude Code stop hook at {timestamp}. Reason: {reason}"
    else:
        note = f"Auto-saved by Claude Code stop hook at {timestamp}"

    # ── 4. Find csession.py relative to this hook's location ─────────────────
    #   Hooks live at .claude/hooks/auto_save.py
    #   csession.py lives at the project root
    hook_dir      = Path(__file__).parent          # .claude/hooks/
    project_root  = hook_dir.parent.parent         # project root
    csession_path = project_root / "csession.py"

    if not csession_path.exists():
        # Try PATH-installed csession command
        csession_cmd = ["csession", "save", "-m", note]
    else:
        csession_cmd = [sys.executable, str(csession_path), "save", "-m", note]

    # ── 5. Run csession save ──────────────────────────────────────────────────
    try:
        result = subprocess.run(
            csession_cmd,
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=30
        )

        if result.returncode == 0:
            # Print to stderr so it shows in Claude Code's output without
            # interfering with the normal stop flow
            print(f"[csession] ✅  {result.stdout.strip()}", file=sys.stderr)
        else:
            print(f"[csession] ⚠️  Save failed: {result.stderr.strip()}", file=sys.stderr)

    except subprocess.TimeoutExpired:
        print("[csession] ⚠️  Save timed out (>30s)", file=sys.stderr)
    except FileNotFoundError:
        print("[csession] ⚠️  csession.py not found. Check installation.", file=sys.stderr)
    except Exception as e:
        print(f"[csession] ⚠️  Unexpected error: {e}", file=sys.stderr)

    # ── 6. Exit 0 = let Claude stop normally ─────────────────────────────────
    #   Exit non-zero only if you want to BLOCK Claude from stopping
    #   (we never do that here — just save and get out of the way)
    sys.exit(0)


if __name__ == "__main__":
    main()
