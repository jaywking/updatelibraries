# Python Environment Maintenance & Package Updater

This Python script provides a comprehensive solution for maintaining a clean and up-to-date Python environment. It features both an easy-to-use interactive menu and a full suite of command-line arguments for automation. The script automatically finds and upgrades all outdated packages, cleans up broken installations, and manages its own log files.

This project includes a batch script (`run.bat`) that handles the setup and execution in a dedicated virtual environment, ensuring that the script and its dependencies do not interfere with your global Python installation.

## Features

- **Automated Environment Setup**: The `run.bat` script creates and manages a local virtual environment (`.venv`) for you.
- **Interactive Mode**: If run without arguments, an easy-to-use menu guides you through the update options.
- **Automatic Package Updates**: Finds and upgrades all outdated `pip` packages in a single, efficient command.
- **Self-Updating `pip`**: Ensures `pip` itself is the latest version before proceeding.
- **Environment Cleanup**: Scans for and removes temporary or broken package folders (e.g., `~packagename`).
- **Flexible Exclusions**: Exclude packages from updates via the menu, command-line arguments, or a `requirements.txt` file.
- **Dry Run Mode**: Preview which packages would be updated without making any changes.
- **Robust Logging**: Creates a timestamped log file for every run in a dedicated `logs/` directory and automatically cleans up old logs.

## Prerequisites

- Python 3.x installed and its `python` command accessible in the system's PATH.

## Usage Guide

### Recommended Method: `run.bat`

This is the simplest and safest way to run the updater. It handles all the setup steps for you.

1.  **Open a command prompt** in the project directory.
2.  **Execute the batch file**:

    ```bash
    run.bat
    ```

    The first time you run it, it will create a local Python virtual environment in a `.venv` folder. On subsequent runs, it will reuse this environment.

### Passing Arguments

You can pass any of the script's command-line arguments directly to `run.bat`. The arguments will be forwarded to the Python script.

**Example: Perform a dry run**

```bash
run.bat --dry-run
```

**Example: Exclude packages and run in verbose mode**

```bash
run.bat --exclude requests --exclude numpy -v
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
| `-v`, `--verbose`          | Show detailed `pip` output on the console instead of just in the log file.                                  | Disabled         |

## How It Works

The `run.bat` script performs the following steps:

1.  **Check for Virtual Environment**: Looks for a `.venv` directory. If it doesn't exist, it creates one using the `venv` module.
2.  **Activate Environment**: Activates the local virtual environment.
3.  **Install Dependencies**: Installs any dependencies listed in `requirements.txt` (currently none).
4.  **Execute Python Script**: Runs the `UpdateLibraries.py` script, passing along any command-line arguments.

The Python script then proceeds with its own logic as described in the features list.