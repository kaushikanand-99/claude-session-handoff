# csession — Defect Report & Enhancement Plan

**Version audited:** 1.0.0 (commit `95a5b80`, branch `csession-v1`)
**Audited on:** 2026-07-26 · Windows 11, Python 3.14, cmd.exe shell
**Status:** all defects below were reproduced, not inferred.

Severity key — **S1** breaks a documented workflow outright · **S2** silently corrupts or loses
data · **S3** wrong output, recoverable · **S4** packaging/hygiene.

| # | Severity | Defect | Location |
|---|---|---|---|
| D1 | S1 | `status` crashes before the first `save` | `csession.py:437` |
| D2 | S2 | All git context silently lost on Windows | `csession.py:49-98` |
| D3 | S2 | `task done/wip/block` marks the **wrong** task | `csession.py:507-515` |
| D4 | S3 | `task add` splits the markdown table in two | `csession.py:479-483` |
| D5 | S3 | `count_tasks` counts the legend as real tasks | `csession.py:101-107` |
| D6 | S1 | Unicode crash on Windows consoles (cp1252) | `csession.py:434-449` |
| D7 | S4 | Invalid build backend — `pip install .` fails | `pyproject.toml:3` |
| D8 | S4 | Repo layout flattened; `testpaths` mismatch | repo root |
| D9 | S2 | Test suite cannot run on Windows — 6 of 21 fail | `test_csession.py` |
| D10 | S3 | Stop hook reports a bogus failure for a successful save | `.claude/hooks/auto_save.py:86` |
| D11 | S1 | Stop hook never fires on Windows — `python3` is a stub | `.claude/settings.json:9` |

D10 and D11 live in files that commit `95a5b80` had dropped entirely (see D8); they surfaced only
once the canonical layout was restored.

---

## D1 — `status` crashes before the first `save` (S1)

**Symptom.** `csession status` raises `TypeError` on any freshly initialized project.

```
TypeError: unsupported format string passed to NoneType.__format__
  File "csession.py", line 437, in cmd_status
    print(f"│  🕐  Last saved:      {config.get('last_saved', 'never'):<26}│")
```

**Reproduce.**
```bash
csession init demo && csession status     # crashes
```

**Root cause.** `cmd_init` writes `"last_saved": None` explicitly (`csession.py:221`). The read at
:437 uses `config.get('last_saved', 'never')` — a `dict.get` default only applies when the key is
**absent**, never when its value is `None`. The key is present and null, so `None` reaches the
`:<26` format spec and raises.

**Impact.** This is the first command the README tells you to run ("Check `csession status` before
every session"), and it fails 100% of the time until a save has happened.

**Fix.** `config.get('last_saved') or 'never'`. Same defensive treatment for `project` and
`session_count`.

---

## D2 — All git context silently lost on Windows (S2)

**Symptom.** Snapshots record `branch: N/A (not a git repo)` while sitting inside a valid git repo.
No error is shown. `SNAPSHOT.md` and `RESUME_PROMPT.md` are written with empty git sections.

**Reproduce.**
```python
>>> import csession; csession.get_git_info()
{'branch': 'N/A (not a git repo)', 'last_commit': 'none', ...}   # inside a real repo
```

**Root cause — two independent POSIX assumptions in `run()` (`csession.py:49`), which uses
`shell=True`.** On Windows `shell=True` invokes `cmd.exe`, not a POSIX shell.

1. **`2>/dev/null` is not valid cmd.exe syntax.** `cmd.exe` treats `/dev/null` as a file path and
   aborts:
   ```
   rc=1  stderr='The system cannot find the path specified.'
   ```
   `run()` then returns its fallback, so `in_git` is `False` and the function short-circuits to the
   "not a git repo" branch — even though git is present and working.

   | command | result on Windows |
   |---|---|
   | `git rev-parse --is-inside-work-tree 2>/dev/null` | `''` ← breaks detection |
   | `git rev-parse --is-inside-work-tree` | `'true'` |
   | `['git','rev-parse','--is-inside-work-tree']` | `'true'` |

2. **Single-quoted format strings are not de-quoted by cmd.exe.** `--format='%h %s (%ar)'` is passed
   through with the literal quotes attached and yields `''`, where the argument-list form correctly
   returns `95a5b80  feat: initial release v1.0.0  (9 weeks ago)`.

**Impact.** The single most valuable part of a handoff — what branch you were on and what you last
committed — is silently blank for every Windows user. Silent, so nobody notices until they read a
stale snapshot. Note the CI matrix includes `windows-latest`, so this was reachable by the existing
test plan.

**Fix.** Drop `shell=True`. Pass argument lists, let `capture_output` swallow stderr instead of
shell redirection, and check `returncode` rather than truthiness of stdout.

---

## D3 — `task done/wip/block` marks the wrong task (S2)

**Symptom.** Marking one task silently changes a different one. The intended task stays untouched
and the command still reports success.

**Reproduce.**
```bash
csession init demo
csession task add "Prep work for T09"    # becomes T05
csession task add ... # filler up to T09
csession task done T09
```
```
✅  T09 marked as done (✅)
| T05 | ✅  | Prep work for T09  |     ← T05 was modified; T09 was not
```

**Root cause.** `cmd_task` matches with `if task_id in line` (`csession.py:508`) — an unanchored
substring test against the **entire line**, including the Task and Notes columns. Any row whose free
text mentions another task's ID will be claimed first if it appears earlier in the file. The loop
then `break`s, so the real row is never reached.

**Impact.** Silent data corruption in the file that is the tool's whole reason for existing. The
success message actively misleads.

**Fix.** Parse the row as a markdown table and compare the **ID cell** exactly:
split on `|`, strip, require `cells[0] == task_id`. Skip lines that aren't table rows.

---

## D4 — `task add` splits the markdown table in two (S3)

**Symptom.** After the first `task add`, `PROGRESS.md` no longer renders as one table.

**Reproduce.** `csession init demo && csession task add "New task alpha"` →

```
| T03 | ⬜ | Example: Add tests |    |
                                        ← blank line injected here
| T04 | ⬜ | New task alpha     |    |
```

**Root cause.** `cmd_task` inserts via `progress.replace("## Blockers", new_row + "\n## Blockers")`
(`csession.py:481`). The template already has a blank line before `## Blockers`, so the new row lands
*after* that blank line rather than adjacent to the last table row. In markdown a blank line
terminates a table, so every added task forms a second, headerless table.

**Impact.** Cosmetic in raw text, but `RESUME_PROMPT.md` is consumed by an LLM — a fragmented table
degrades the parse and undercuts the tool's core purpose. It also compounds D5.

**Fix.** Locate the last contiguous table row and insert directly after it, rather than anchoring on
the `## Blockers` heading.

---

## D5 — `count_tasks` counts its own legend (S3)

**Symptom.** A brand-new project with zero work done reports **14% complete, 1 done, 1 blocked**, and
prints the warning `⚠️ You have blocked tasks`.

**Reproduce.**
```bash
csession init demo && csession save -m x && csession status
```
```
Progress [████░░░░░░░░░░░░░░░░░░░░░░]  14%
✅ Done: 1    ❌ Blocked: 1
🔄 In Progress: 1    ⬜ Todo: 4
```
Expected on a fresh init: `done=0, wip=0, todo=3, blocked=0`.
Actual `count_tasks()` return: `{'done': 1, 'wip': 1, 'todo': 4, 'blocked': 1}`.

**Root cause.** `count_tasks` (`csession.py:101`) runs `str.count()` over the **entire file**. The
status legend embedded in `progress_template()` (`csession.py:154-159`) contains one of every emoji,
so each status is inflated by exactly one. Any emoji in prose, notes, or the HTML comments is counted
too.

**Impact.** Every progress percentage, every dashboard, and the "Quick Stats at Handoff" table in
`RESUME_PROMPT.md` are wrong. The spurious blocked-task warning trains users to ignore a real signal.

**Fix.** Count only status cells of well-formed table rows: skip HTML comment blocks, require a line
starting with `|`, and read the status column specifically.

---

## D6 — Unicode crash on Windows consoles (S1 on Windows)

**Symptom.**
```
UnicodeEncodeError: 'charmap' codec can't encode characters in position 2-52
  File "csession.py", line 434, in cmd_status
```

**Reproduce.** Run `csession status` in any console where stdout is cp1252 (the Windows default) —
i.e. without `PYTHONIOENCODING=utf-8`.

**Root cause.** `cmd_status` prints box-drawing characters (`┌ ─ │ └`) and emoji. Python resolves
stdout's encoding from the console code page; on cp1252 these characters have no mapping and the
write raises. The same exposure exists anywhere the CLI prints emoji, which is nearly every command.

**Impact.** The dashboard is unusable on stock Windows terminals. Combined with D1, `status` fails
two different ways before it can ever succeed.

**Fix.** Reconfigure stdout/stderr to UTF-8 with a replacement error handler at startup
(`io.TextIOWrapper.reconfigure(encoding='utf-8', errors='replace')`), guarded for Python < 3.7 and
for redirected streams.

---

## D7 — Invalid build backend; `pip install .` fails (S4)

**Symptom.** The package cannot be built or installed.

**Root cause.** `pyproject.toml:3` declares:
```toml
build-backend = "setuptools.backends.legacy:build"
```
No such module exists.
```
setuptools.backends.legacy  -> ModuleNotFoundError: No module named 'setuptools.backends'
setuptools.build_meta       -> OK
```

**Impact.** `[project.scripts] csession = "csession:main"` — the documented console-script entry
point — can never be installed. Users are silently forced onto `install.sh`'s file-copy path.

**Fix.** `build-backend = "setuptools.build_meta"`.

---

## D8 — Repo layout flattened; `testpaths` mismatch (S4)

Commit `95a5b80` is a **flattened, partial snapshot** of the real project:

| Correct (per `csession-repo.zip`) | As committed |
|---|---|
| `.github/workflows/ci.yml` | `ci.yml` at root — never runs |
| `tests/test_csession.py` | `test_csession.py` at root |
| `install.sh` | missing |
| `.claude/hooks/auto_save.py`, `.claude/settings.json` | missing |
| `.gitignore` | missing |

`csession.py` and `test_csession.py` are byte-identical between the commit and the zip, so this is a
packaging artifact rather than divergent code. Consequences: `pyproject.toml:55` sets
`testpaths = ["tests"]` and `ci.yml:33` runs `pytest tests/`, but no `tests/` directory exists in the
checkout — the suite collects nothing. CI would also never trigger from the root `ci.yml`.

**Fix.** Restore the zip's layout; keep `testpaths`/CI as-is once `tests/` exists again.

---

## D9 — Test suite cannot run on Windows (S2)

**Symptom.** 6 of the 21 tests fail on Windows before any source change:

```
FAILED TestSave::test_snapshot_contains_session_note      - UnicodeDecodeError
FAILED TestSave::test_resume_prompt_contains_instructions - UnicodeDecodeError
FAILED TestTask::test_add_task                            - UnicodeDecodeError
FAILED TestTask::test_add_auto_increments_id              - UnicodeDecodeError
FAILED TestTask::test_mark_task_done                      - UnicodeDecodeError
FAILED TestTask::test_mark_task_wip                       - UnicodeDecodeError
6 failed, 15 passed
```

**Root cause.** The tests read fixture files with a bare `Path.read_text()` (11 call sites).
`read_text()` with no `encoding` uses the platform's locale encoding — cp1252 on Windows — and every
one of these files contains status emoji. `csession.py` itself is correct here: `read_file`/
`write_file` both pin `encoding="utf-8"`. The defect is confined to the test suite.

**Verification that this is pre-existing.** The identical 6 failures occur on the unmodified v1.0.0
`csession.py`, so this is not a regression introduced by the fixes below.

**Impact.** Two-thirds of the CI matrix is Windows (`windows-latest` × 3 Python versions). Those legs
would have failed from day one, which is consistent with D8 — the workflow was never in
`.github/workflows/`, so CI has almost certainly never run.

**Fix.** Pass `encoding="utf-8"` at every `read_text()` call site.

---

## D10 — Stop hook reports a bogus failure for a successful save (S3)

**Symptom.** On a Claude Code Stop event the hook emits a thread traceback and an error, even though
the snapshot was written correctly:

```
Exception in thread Thread-1 (_readerthread):
  UnicodeDecodeError: 'charmap' codec can't decode byte 0x8f in position 137
[csession] ⚠️  Unexpected error: 'NoneType' object has no attribute 'strip'
```

**Reproduce.** `echo '{}' | python .claude/hooks/auto_save.py` in an initialized project on Windows.

**Root cause.** `auto_save.py:86` calls `subprocess.run(..., text=True)` without an `encoding`. The
child (`csession save`) emits UTF-8; the parent decodes with the locale codec — cp1252 — so the
reader thread dies, `result.stdout` comes back `None`, and `.strip()` raises. The mirror image of D2:
D2 was the child misconfigured, this is the parent.

**Impact.** The save genuinely succeeds, so this is a lying error message rather than data loss — but
it trains users to distrust a working autosave, which is the feature's whole value.

**Fix.** Pin `encoding="utf-8", errors="replace"` on the call and guard `stdout`/`stderr` against
`None`. Also reconfigure the hook's own stderr to UTF-8, so its status line renders as `✅` rather
than `✅` under `backslashreplace`.

---

## D11 — Stop hook never fires on Windows (S1)

**Symptom.** The autosave hook silently does nothing on Windows.

**Root cause.** `.claude/settings.json:9` invokes `python3`. On Windows that name resolves to the
Microsoft Store alias stub at `%LOCALAPPDATA%\Microsoft\WindowsApps\python3.exe`, which runs nothing:

```
$ python3 --version
Python was not found; run without arguments to install from the Microsoft Store...
$ echo $?
49
```

A real interpreter is present as `python`. The stub shadows it for the `python3` name regardless.

**Impact.** Phase 3 — billed in the README as the feature that makes saving "completely automatic" —
is inert on Windows. It fails silently, so the first symptom is an empty `history/` after a session
the user believed was captured.

**Fix.** `python3 … || python …`. The stub exits **49**, not 0, so the fallback triggers reliably; and
`auto_save.py` ends in an unconditional `sys.exit(0)`, so a non-zero status can only mean the
interpreter never launched — never that the save itself failed. Applied to `settings.json`, the
setup snippet in the hook's own docstring, and the README.

---

## Observation — four hardening tests exist in no commit

`.pytest_cache/v/cache/nodeids` records **25** test IDs. Every committed and zipped copy of the suite
contains **21**. The four extras are:

- `test_get_git_info_uses_argument_list_commands` → D2
- `test_count_tasks_ignores_legend_and_comments` → D5
- `test_mark_task_id_matches_exact_table_cell` → D3
- `test_add_task_preserves_task_table` → D4

They map one-to-one onto four of the defects above, which indicates a later hardened revision was
written and run locally. It does not appear in any commit, branch, stash, or reflog entry. Treat the
fixes below as a reimplementation, not a recovery.

---

## Remediation plan

Ordered by severity, each landing with the regression test named above.

| Step | Change | Test | Status |
|---|---|---|---|
| 1 | D1 — null-safe config reads in `cmd_status` | `test_status_before_first_save` | ✅ done |
| 2 | D2 — argument-list subprocess, no `shell=True` | `test_get_git_info_uses_argument_list_commands` | ✅ done |
| 3 | D3 — exact table-cell ID matching | `test_mark_task_id_matches_exact_table_cell` | ✅ done |
| 4 | D4 — insert after last table row | `test_add_task_preserves_task_table` | ✅ done |
| 5 | D5 — legend/comment-aware counting | `test_count_tasks_ignores_legend_and_comments` | ✅ done |
| 6 | D6 — UTF-8 stdout reconfiguration | `test_unicode_output_does_not_crash` | ✅ done |
| 7 | D7 — correct build backend | backend import check | ✅ done |
| 8 | D9 — `encoding="utf-8"` at all `read_text()` sites | existing suite green on Windows | ✅ done |
| 9 | D8 — restore `tests/`, `.github/workflows/`, `install.sh`, `.claude/` | CI green | ✅ done |
| 10 | D10 — pin UTF-8 decode in the hook's subprocess call | manual Stop-event run | ✅ done |
| 11 | D11 — `python3 … || python …` interpreter fallback | manual Stop-event run | ✅ done |

Constraint carried from `README.md`: keep `csession.py` single-file and stdlib-only. Honoured — the
fixes add no imports beyond the stdlib modules already in use.

### Implementation notes

A shared helper, `iter_task_rows()`, now yields `(line_index, task_id, status_cell)` for genuine
table rows only — skipping HTML comment blocks, the header, and the `|---|` separator. D3, D4, and D5
were three symptoms of one absent abstraction: nothing in v1.0.0 knew what a task row actually *was*,
so each site improvised with `str.count()` or `in`. Task-ID allocation in `task add` now derives from
the same helper, so IDs mentioned in prose or notes no longer inflate the next number.

### Verification

| Suite | Original v1.0.0 | Patched |
|---|---|---|
| 21 original tests | 6 failed, 15 passed | 21 passed |
| 6 new regression tests | 6 failed | 6 passed |
| **Total** | **12 failed, 15 passed** | **27 passed** |

Every regression test was confirmed to fail against unmodified v1.0.0 before being accepted — a test
that passes on broken code proves nothing. The D6 test runs `csession status` as a subprocess under
`PYTHONIOENCODING=cp1252`; an in-process check cannot reproduce the defect because pytest's `capsys`
replaces stdout with a UTF-8 capture object.

D10 and D11 are verified by running the hook directly against a Stop-event payload rather than by
unit test: both are integration failures in how the hook is *launched* and how it *decodes a child
process*, neither of which an in-process test can exercise honestly.

**All 11 defects are now fixed.** Landed across three commits: the CLI fixes, the layout restore, and
the hook fixes that the restore made visible.

### Residual notes (not defects, not addressed)

- `csession-repo.zip` is still committed at the project root. Now that the layout it encoded has been
  restored, it is redundant and will drift. Worth deleting in a future commit.
- `install.sh` is bash-only, so on Windows the documented one-line install works only under Git Bash
  or WSL. The manual install path in the README covers it; a `.ps1` equivalent would not.
- `pyproject.toml` still carries placeholder metadata — `Your Name`, `you@example.com`, and
  `github.com/yourusername/csession` in four URLs.
