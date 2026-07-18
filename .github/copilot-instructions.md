# Copilot instructions for the `UpdateLibraries` repository

This file gives concise, actionable guidance for an AI coding agent working on
this repository.

## Big picture

- Purpose: the project previews, cleans, snapshots, restores, and upgrades
  packages in the selected Python environment.
- Architecture: [UpdateLibraries.py](../UpdateLibraries.py) coordinates the
  workflow, [cli.py](../cli.py) owns command-line parsing,
  [interactive.py](../interactive.py) owns the terminal menu and review screens,
  and [updater.py](../updater.py) owns pip operations, logging, preflight,
  snapshots, restore, batching, and dependency validation.
- The UI is interactive when launched without arguments and scriptable through
  CLI flags. `run.bat` forwards arguments to the canonical Python entrypoint.

## Key files

- Entrypoint and orchestration: [UpdateLibraries.py](../UpdateLibraries.py)
- CLI arguments: [cli.py](../cli.py)
- Interactive workflow: [interactive.py](../interactive.py)
- Package-management implementation: [updater.py](../updater.py)
- Tests: [tests](../tests)
- Windows shortcut: [run.bat](../run.bat)
- Destructive Azure removal helper:
  [remove_azure_python_sdks.bat](../remove_azure_python_sdks.bat)
- User documentation: [README.md](../README.md)
- Deferred work: [PARKINGLOT.md](../PARKINGLOT.md)
- Generated logs: `logs/`; log filenames start with `update_libraries_`.

## Developer workflows

- Run tests:
  `python -m unittest discover -s tests -v`
- Compile-check the Python modules:
  `python -m compileall -q UpdateLibraries.py cli.py interactive.py updater.py`
- Run interactively:
  `run.bat` or `python UpdateLibraries.py`
- Preview without changing an environment:
  `run.bat --dry-run`
- Show verbose preview output:
  `python UpdateLibraries.py --dry-run --verbose`
- Exclude packages:
  `python UpdateLibraries.py --exclude azure-cli --exclude-from requirements.txt`
- List installed packages:
  `python UpdateLibraries.py --list-installed`

Use the project virtual environment at
`C:\LocalVenvs\updatelibraries\Scripts\python.exe` when it exists.

## Project conventions

- Use `logging` for operational output so messages reach both the console and
  log file. Reserve direct `print()` calls for interactive prompts and screens.
- Invoke pip through the selected Python executable with
  `sys.executable -m pip` so the intended environment is modified.
- Keep `run_with_retries()` around pip operations that need retry behavior.
- `UpgradeStatusManager` parses pip output for progress. Update its tests when
  changing output parsing.
- `MAX_UPGRADE_BATCH_SIZE` controls upgrade batching.
- Normalize package names with `canonical_package_name()` before comparing
  exclusions or dependency-managed package rules.
- Preserve the resolver-backed preflight, pre-update snapshot, final
  `pip check`, and restore guidance when changing the mutation path.
- Forward relevant options consistently through CLI, interactive, and
  LocalVenv subprocess paths.

## Dependencies and integrations

- Runtime package management requires pip in the selected Python environment.
- The application itself currently has no third-party Python dependencies; see
  [requirements.txt](../requirements.txt).
- This is a local maintenance utility, not a deployed web or cloud service.
  Do not introduce frontend, analytics, browser, or cloud-deploy tooling without
  a project requirement.

## Editing and safety guidance

- Make small changes in the module that owns the behavior instead of routing
  every change through `UpdateLibraries.py`.
- Preserve compatibility between interactive and scripted modes.
- Add or update unit tests for behavior changes and keep dry-run paths
  non-mutating.
- Do not run a real package update or snapshot restore merely to test code.
  Mock subprocess operations in unit tests.
- Do not run or modify `remove_azure_python_sdks.bat` unless the task explicitly
  concerns Azure removal; it uninstalls packages.
- Do not assume the active interpreter is a virtual environment. The tool may
  target the current Python or one or more environments under `C:\LocalVenvs`.

## Examples

- For a new CLI flag, add parsing in `cli.parse_args()`, forward it through the
  entrypoint and LocalVenv path, add interactive support when applicable, and
  apply it in `updater.py`.
- For pip-output parsing changes, update `UpgradeStatusManager` and add focused
  tests for the new and fallback formats.
- For package-selection changes, apply filters before downstream counts,
  batching, preflight, and summary generation so reporting remains consistent.
