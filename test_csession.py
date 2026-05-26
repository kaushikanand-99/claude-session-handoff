"""
Unit tests for csession.py

Run with:  pytest tests/ -v
"""
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Add parent directory to path so we can import csession
sys.path.insert(0, str(Path(__file__).parent.parent))
import csession


# ─────────────────────────────────────────────
#  Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def tmp_project(tmp_path, monkeypatch):
    """Create a temporary project directory and chdir into it."""
    monkeypatch.chdir(tmp_path)
    # Override workspace paths to point into tmp_path
    monkeypatch.setattr(csession, "WORKSPACE",      tmp_path / ".claude-session")
    monkeypatch.setattr(csession, "CONFIG_FILE",    tmp_path / ".claude-session" / "config.json")
    monkeypatch.setattr(csession, "PROJECT_FILE",   tmp_path / ".claude-session" / "PROJECT.md")
    monkeypatch.setattr(csession, "PROGRESS_FILE",  tmp_path / ".claude-session" / "PROGRESS.md")
    monkeypatch.setattr(csession, "DECISIONS_FILE", tmp_path / ".claude-session" / "DECISIONS.md")
    monkeypatch.setattr(csession, "SNAPSHOT_FILE",  tmp_path / ".claude-session" / "SNAPSHOT.md")
    monkeypatch.setattr(csession, "RESUME_FILE",    tmp_path / ".claude-session" / "RESUME_PROMPT.md")
    monkeypatch.setattr(csession, "HISTORY_DIR",    tmp_path / ".claude-session" / "history")
    return tmp_path


@pytest.fixture
def initialized_project(tmp_project):
    """A project with csession already initialized."""
    class Args:
        name = "test-project"
        force = False
    csession.cmd_init(Args())
    return tmp_project


# ─────────────────────────────────────────────
#  Test: init
# ─────────────────────────────────────────────

class TestInit:
    def test_creates_workspace(self, tmp_project):
        class Args:
            name = "my-project"
            force = False
        csession.cmd_init(Args())
        assert (tmp_project / ".claude-session").is_dir()

    def test_creates_all_template_files(self, tmp_project):
        class Args:
            name = "my-project"
            force = False
        csession.cmd_init(Args())
        ws = tmp_project / ".claude-session"
        assert (ws / "config.json").exists()
        assert (ws / "PROJECT.md").exists()
        assert (ws / "PROGRESS.md").exists()
        assert (ws / "DECISIONS.md").exists()
        assert (ws / "history").is_dir()

    def test_config_contains_project_name(self, tmp_project):
        class Args:
            name = "payment-service"
            force = False
        csession.cmd_init(Args())
        config = json.loads((tmp_project / ".claude-session" / "config.json").read_text())
        assert config["project"] == "payment-service"
        assert config["session_count"] == 0

    def test_skips_reinit_without_force(self, initialized_project, capsys):
        class Args:
            name = "other"
            force = False
        csession.cmd_init(Args())
        out = capsys.readouterr().out
        assert "already exists" in out

    def test_force_reinitializes(self, initialized_project):
        class Args:
            name = "new-name"
            force = True
        csession.cmd_init(Args())
        config = json.loads((initialized_project / ".claude-session" / "config.json").read_text())
        assert config["project"] == "new-name"


# ─────────────────────────────────────────────
#  Test: save
# ─────────────────────────────────────────────

class TestSave:
    def test_creates_snapshot_file(self, initialized_project):
        class Args:
            message = "test save"
        csession.cmd_save(Args())
        assert (initialized_project / ".claude-session" / "SNAPSHOT.md").exists()

    def test_creates_resume_file(self, initialized_project):
        class Args:
            message = "test save"
        csession.cmd_save(Args())
        assert (initialized_project / ".claude-session" / "RESUME_PROMPT.md").exists()

    def test_increments_session_count(self, initialized_project):
        class Args:
            message = "first"
        csession.cmd_save(Args())
        csession.cmd_save(Args())
        config = json.loads((initialized_project / ".claude-session" / "config.json").read_text())
        assert config["session_count"] == 2

    def test_archives_to_history(self, initialized_project):
        class Args:
            message = "test"
        csession.cmd_save(Args())
        history_files = list((initialized_project / ".claude-session" / "history").glob("*.md"))
        assert len(history_files) == 1

    def test_snapshot_contains_session_note(self, initialized_project):
        class Args:
            message = "JWT refresh tokens are broken"
        csession.cmd_save(Args())
        snapshot = (initialized_project / ".claude-session" / "SNAPSHOT.md").read_text()
        assert "JWT refresh tokens are broken" in snapshot

    def test_resume_prompt_contains_instructions(self, initialized_project):
        class Args:
            message = "test"
        csession.cmd_save(Args())
        resume = (initialized_project / ".claude-session" / "RESUME_PROMPT.md").read_text()
        assert "Instructions for Claude" in resume
        assert "Session Resume" in resume


# ─────────────────────────────────────────────
#  Test: task
# ─────────────────────────────────────────────

class TestTask:
    def test_add_task(self, initialized_project):
        class Args:
            action = "add"
            text = ["Implement", "auth", "module"]
        csession.cmd_task(Args())
        progress = (initialized_project / ".claude-session" / "PROGRESS.md").read_text()
        assert "Implement auth module" in progress
        assert "⬜" in progress

    def test_add_auto_increments_id(self, initialized_project):
        class Args:
            action = "add"
            text = ["First task"]
        csession.cmd_task(Args())
        class Args2:
            action = "add"
            text = ["Second task"]
        csession.cmd_task(Args2())
        progress = (initialized_project / ".claude-session" / "PROGRESS.md").read_text()
        assert "T04" in progress  # T01–T03 exist in template
        assert "T05" in progress

    def test_mark_task_done(self, initialized_project):
        class AddArgs:
            action = "add"
            text = ["Test task"]
        csession.cmd_task(AddArgs())

        class DoneArgs:
            action = "done"
            text = ["T04"]
        csession.cmd_task(DoneArgs())

        progress = (initialized_project / ".claude-session" / "PROGRESS.md").read_text()
        lines = [l for l in progress.split("\n") if "T04" in l]
        assert any("✅" in l for l in lines)

    def test_mark_task_wip(self, initialized_project):
        class AddArgs:
            action = "add"
            text = ["WIP task"]
        csession.cmd_task(AddArgs())

        class WipArgs:
            action = "wip"
            text = ["T04"]
        csession.cmd_task(WipArgs())

        progress = (initialized_project / ".claude-session" / "PROGRESS.md").read_text()
        lines = [l for l in progress.split("\n") if "T04" in l]
        assert any("🔄" in l for l in lines)

    def test_unknown_task_id_doesnt_crash(self, initialized_project, capsys):
        class Args:
            action = "done"
            text = ["T99"]
        csession.cmd_task(Args())
        out = capsys.readouterr().out
        assert "not found" in out


# ─────────────────────────────────────────────
#  Test: log
# ─────────────────────────────────────────────

class TestLog:
    def test_appends_to_decisions(self, initialized_project):
        class Args:
            text = ["Chose", "JWT", "over", "sessions"]
        csession.cmd_log(Args())
        decisions = (initialized_project / ".claude-session" / "DECISIONS.md").read_text()
        assert "Chose JWT over sessions" in decisions

    def test_multiple_logs_accumulate(self, initialized_project):
        class Args1:
            text = ["First decision"]
        class Args2:
            text = ["Second decision"]
        csession.cmd_log(Args1())
        csession.cmd_log(Args2())
        decisions = (initialized_project / ".claude-session" / "DECISIONS.md").read_text()
        assert "First decision" in decisions
        assert "Second decision" in decisions


# ─────────────────────────────────────────────
#  Test: helpers
# ─────────────────────────────────────────────

class TestHelpers:
    def test_count_tasks_correct(self):
        progress = """
        | T01 | ✅ | done task |
        | T02 | 🔄 | wip task  |
        | T03 | ⬜ | todo task |
        | T04 | ⬜ | todo task |
        | T05 | ❌ | blocked   |
        """
        result = csession.count_tasks(progress)
        assert result["done"]    == 1
        assert result["wip"]     == 1
        assert result["todo"]    == 2
        assert result["blocked"] == 1

    def test_read_file_missing_returns_empty(self):
        assert csession.read_file("/nonexistent/path.md") == ""

    def test_write_then_read_roundtrip(self, tmp_path):
        path = tmp_path / "test.md"
        csession.write_file(path, "hello world")
        assert csession.read_file(path) == "hello world"
