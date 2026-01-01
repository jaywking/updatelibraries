# Python Environment Maintenance & Package Updater

This Python script provides a comprehensive solution for maintaining a clean and up-to-date Python environment. It features both an easy-to-use interactive menu and a full suite of command-line arguments for automation. The script automatically finds and upgrades all outdated packages, cleans up broken installations, and manages its own log files.

The canonical entry point is `UpdateLibraries.py` (or `run.bat`, which forwards to it). There are no secondary copies of the script in this repo.

## Features

- **Interactive Mode**: If run without arguments, an easy-to-use menu guides you through the update options.
- **Automatic Package Updates**: Finds and upgrades all outdated `pip` packages, running them in small batches for better resiliency.
- **Self-Updating `pip`**: Ensures `pip` itself is the latest version before proceeding.
- **Environment Cleanup**: Scans for and removes temporary or broken package folders (e.g., `~packagename`).
- **Flexible Exclusions**: Exclude packages from updates via the menu, command-line arguments, or a `requirements.txt` file.
- **Dry Run Mode**: Preview which packages would be updated without making any changes.
- **Robust Logging**: Creates a timestamped log file for every run, records the version changes for each package, captures detailed `pip` output on failures, and automatically cleans up old logs.

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
| `--log-dir <DIR>`          | Directory to save log files.                                                                                | `./logs`         |
| `--log-retention-days <N>` | Automatically delete log files older than `N` days. Set to `0` to disable.                                  | 30               |
| `--skip-pip-update`        | Skip the initial step of updating `pip` itself.                                                             | Disabled         |
| `--skip-cleanup`           | Skip the cleanup of invalid package distributions.                                                          | Disabled         |
| `--dry-run`                | Show which packages would be updated without actually updating them.                                        | Disabled         |
| `--no-deps`                | Do not install package dependencies when upgrading.                                                         | Disabled         |
| `-v`, `--verbose`          | Show detailed `pip` output on the console instead of just in the log file.                                  | Disabled         |
| `--list-installed`         | List all installed packages with version and install date, then exit.                                       | Disabled         |

## How It Works

The script performs the following steps in order:

1.  **Parse Inputs**: Checks if command-line arguments were provided. If not, it launches the **interactive menu**.
2.  **Setup Logging**: Initializes logging to both the console and a timestamped file.
3.  **Run Cleanup (Optional)**: Cleans up old logs and broken package installations.
4.  **Update Pip (Optional)**: Checks if `pip` is outdated and upgrades it if necessary.
5.  **Update Libraries**: Fetches the list of all outdated packages, filters exclusions, and upgrades them in small batches while streaming live progress.
6.  **Summary Report**: Prints the before/after version of every attempted upgrade and surfaces any `pip` errors so you can act immediately.
