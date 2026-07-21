# Python Environment Maintenance & Package Updater

This Python script provides a comprehensive solution for maintaining a clean and up-to-date Python environment. It features both an easy-to-use interactive menu and a full suite of command-line arguments for automation. The script automatically finds and upgrades all outdated packages, cleans up broken installations, and manages its own log files.

The canonical entry point is `UpdateLibraries.py` (or `run.bat`, which forwards to it). There are no secondary copies of the script in this repo.

## Features

- **Preview-First Interactive Mode**: If run without arguments, a menu starts with a no-change preview option, then presents one reviewable update plan before a real update can begin. After each completed action, press any key to clear the screen and return to the main menu; choose Exit when you are finished.
- **LocalVenvs Picker**: From the menu, choose the current Python, one `C:\LocalVenvs` environment, or all detected LocalVenvs. The picker uses a compact two-column name list with search; the exact Python executable is shown in the review plan before a real update.
- **Automatic Package Updates**: Finds and upgrades all outdated `pip` packages, running them in small batches for better resiliency.
- **Self-Updating `pip`**: Ensures `pip` itself is the latest version before proceeding.
- **Environment Visibility**: Shows the exact Python executable and `pip` version that will be inspected or modified.
- **Safer Environment Cleanup**: Scans for temporary or broken package folders (e.g., `~packagename`) and moves them to a backup folder instead of deleting them.
- **Flexible Exclusions**: Exclude packages from updates via the menu, command-line arguments, or a `requirements.txt` file.
- **Constraints Support**: Apply one or more pip constraints files to keep compatible versions together.
- **Upgrade Preflight**: Resolves and logs pip's complete proposed package plan before changing the environment.
- **Recovery Snapshot**: Saves `pip freeze` before real updates and provides a restore command if the final dependency check fails.
- **Guided Snapshot Restore**: The interactive menu can preview a saved snapshot's recorded Python target and package count, then requires typed confirmation before restoring it.
- **Dry Run Mode**: Preview which packages would be updated without changing packages, updating `pip`, or moving cleanup folders.
- **Robust Logging**: Creates a timestamped log file for every run, records the version changes for each package, captures detailed `pip` output on failures, and automatically cleans up old logs.
- **Failure Signaling**: Returns a non-zero exit code when package upgrades or dependency checks fail.

## Prerequisites

- Python 3.x installed and its `python` command accessible in the system's PATH.

## Usage Guide

### Using `run.bat`

The included `run.bat` file is a convenient shortcut for running the script.

1.  **Open a command prompt** in the project directory.
2.  **Execute the batch file**:

    ```bash
    run.bat
    ```

### Passing Arguments

You can pass any of the script's command-line arguments directly to `run.bat`. The arguments will be forwarded to the Python script.

**Example: Perform a dry run**

```bash
run.bat --dry-run
```

### Command-Line Arguments Reference

| Argument                   | Description                                                                                                 | Default          |
| -------------------------- | ----------------------------------------------------------------------------------------------------------- | ---------------- |
| `--exclude <PKG>`          | Package to exclude from updates. Can be specified multiple times.                                           | None             |
| `--exclude-from <FILE>`    | Path to a `requirements.txt`-style file. Packages listed in this file will be excluded.                     | None             |
| `--constraint <FILE>`      | Pip constraints file that pins or limits allowed package versions. Can be specified multiple times.          | None             |
| `--log-dir <DIR>`          | Directory to save log files.                                                                                | `./logs`         |
| `--log-retention-days <N>` | Automatically delete log files older than `N` days. Set to `0` to disable.                                  | 30               |
| `--skip-pip-update`        | Skip the initial step of updating `pip` itself.                                                             | Disabled         |
| `--skip-cleanup`           | Skip moving invalid package distributions to a backup folder.                                               | Disabled         |
| `--dry-run`                | Show which packages would be updated without actually updating them.                                        | Disabled         |
| `--no-deps`                | Do not install package dependencies when upgrading.                                                         | Disabled         |
| `-v`, `--verbose`          | Show detailed `pip` output on the console instead of just in the log file.                                  | Disabled         |
| `--list-installed`         | List all installed packages with version and install date, then exit.                                       | Disabled         |

## How It Works

The script performs the following steps in order:

1.  **Choose an Action**: The interactive menu offers preview, update, list-installed, and exit actions; preview is listed first.
2.  **Choose Environment**: Lets you use the current Python, one `C:\LocalVenvs` environment, or every detected LocalVenv.
3.  **Confirm Environment**: Shows which Python executable(s) will be changed and asks for confirmation before a real interactive update.
4.  **Setup Logging**: Initializes logging to both the console and a timestamped file.
5.  **Run Cleanup (Optional)**: Cleans up old logs and moves broken package leftovers to a timestamped backup folder.
6.  **Snapshot Environment**: Saves the current `pip freeze` output before any package changes.
7.  **Update Pip (Optional)**: Checks if `pip` is outdated and upgrades it if necessary.
8.  **Preflight and Update Libraries**: Fetches outdated packages, filters exclusions, resolves the full plan without modifying the environment, then upgrades in small batches while streaming progress.
9.  **Validate and Summarize**: Runs `pip check`; if it finds conflicts, the log includes the exact command to restore the pre-update snapshot.

If a batch upgrade fails, the script retries each package in that batch one at a time so the failure report names the specific package.
