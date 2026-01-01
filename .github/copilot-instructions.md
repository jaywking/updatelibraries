# Copilot instructions for `UpdateLibraries` repository

This file gives concise, actionable guidance for an AI coding agent working on this repository.

1. Big picture
- Purpose: `UpdateLibraries.py` is a single-file CLI utility to list, clean, and upgrade Python packages in the current system environment. The canonical entrypoint is [UpdateLibraries.py](UpdateLibraries.py#L1).
- Architecture: single-script tool with small helpers: logging setup, cleanup, pip self-update, listing installed packages, and batched upgrades (batch size controlled by `MAX_UPGRADE_BATCH_SIZE`). The UI is either interactive (no args) or fully scripted via CLI flags.

2. Key files and where to look
- Entrypoint: [UpdateLibraries.py](UpdateLibraries.py#L1)
- Shortcut: [run.bat](run.bat#L1) (for Windows) forwards args to the script.
- Dangerous helper: [remove_azure_python_sdks.bat](remove_azure_python_sdks.bat#L1) uninstalls many azure packages — do not run or modify lightly.
- Documentation: [README.md](README.md#L1) contains usage, flags, and behavior summaries.
- Logs: `logs/` directory; log filenames start with `update_libraries_`.

3. Developer workflows and commands (explicit)
- Run interactive: `run.bat` or `python UpdateLibraries.py` (runs interactive menu).
- Scripted examples:
  - Dry run: `run.bat --dry-run` or `python UpdateLibraries.py --dry-run`
  - Verbose (shows pip output): `python UpdateLibraries.py --dry-run --verbose`
  - Exclude packages: `python UpdateLibraries.py --exclude azure-cli --exclude-from requirements.txt`
  - List installed only: `python UpdateLibraries.py --list-installed`

4. Project-specific conventions & patterns
- Logging: `setup_logging()` creates a timestamped file in `logs/` (file handler = DEBUG, console = INFO unless `--verbose`). Use `logging` module for new output so logs go to file.
- Pip invocation: always uses `sys.executable -m pip ...` to ensure the same Python interpreter is used. Prefer this pattern when adding subprocess calls.
- Robustness: `run_with_retries()` wraps pip commands; follow this pattern for flaky subprocesses.
- Output parsing: `UpgradeStatusManager` parses pip stdout for progress. When changing pip output handling, update that parser and tests manually.
- Batch upgrades: packages upgraded in batches (see `MAX_UPGRADE_BATCH_SIZE`); keep that limit in mind when adding parallelization or progress features.

5. Integration & external dependencies
- External tool: `pip` must be available for runtime actions; script assumes `pip` is callable via `sys.executable -m pip`.
- No third-party Python dependencies are required for the script itself (see `requirements.txt`).

6. Editing guidance for AI agents
- Small, targeted changes: modify `UpdateLibraries.py` in-place; keep CLI compatibility and respect both interactive and scripted modes.
- Tests / safety: prefer adding a `--dry-run` branch to new behaviors and preserve existing dry-run behavior.
- Logs & diagnostics: add `logging.debug(...)` for internal diagnostic messages; avoid printing directly to stdout except for interactive prompts.
- Avoid touching `remove_azure_python_sdks.bat` unless the task explicitly concerns Azure removal — it's destructive by design.

7. Examples of actionable tasks to accept
- Add a new CLI flag that filters packages by regex: follow `_parse_args()`, add arg, and apply filter in `update_all_outdated_libraries()`.
- Improve parsing robustness in `UpgradeStatusManager.update_status()` when pip output format changes — include unit-like assertion comments and fallback heuristics.
- Add unit-style smoke checks for `list_installed_packages()` by extracting small functions that can be run without modifying system packages.

8. What *not* to do
- Do not run or modify destructive batch uninstallers (`remove_azure_python_sdks.bat`) without explicit user permission.
- Do not assume a virtualenv — the script targets the active interpreter and its site-packages.

If anything here is unclear or you'd like deeper guidance (examples, tests, or a proposed refactor), tell me which area to expand.
