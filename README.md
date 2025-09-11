# Python Environment Maintenance & Package Updater

This Python script provides a comprehensive solution for maintaining a clean and up-to-date Python environment. It features both an easy-to-use interactive menu and a full suite of command-line arguments for automation. The script automatically finds and upgrades all outdated packages, cleans up broken installations, and manages its own log files.

## Features

- **Interactive Mode**: If run without arguments, an easy-to-use menu guides you through the update options.
- **Automatic Package Updates**: Finds and upgrades all outdated `pip` packages in a single, efficient command for better dependency resolution.
- **Self-Updating `pip`**: Ensures `pip` itself is the latest version before proceeding with other packages.
- **Environment Cleanup**: Scans for and removes temporary or broken package folders (e.g., `~packagename`) left by interrupted installations.
- **Flexible Exclusions**: Exclude specific packages from being updated via the interactive menu, command-line arguments, or by providing a `requirements.txt` file.
- **Dry Run Mode**: Preview which packages would be updated without making any actual changes to your environment.
- **Robust Logging**: Creates a timestamped log file for every run in a dedicated `logs/` directory and automatically cleans up old logs.
- **User-Friendly Progress**: Displays a clean, single-line progress indicator during updates, with a verbose option for detailed `pip` output.
- **Resilient Operations**: Automatically retries network-dependent commands to handle transient connection issues.

## Prerequisites

- Python 3.x
- `pip` installed and accessible in the system's PATH.

## Usage Guide

There are two ways to run the script: Interactive Mode (recommended for manual runs) and Command-Line Mode (ideal for automation).

### 1. Interactive Mode (Default)

Simply run the script without any arguments to launch the interactive menu. It will prompt you for all common options.

```bash
python UpdateLibraries.py
```

----
You will see prompts like this:

```text
Python Environment Maintenance & Package Updater
Choose your options below (press Enter for default):

Exclude a package from updates (type name, Enter to finish): requests
Exclude a package from updates (type name, Enter to finish): 
Exclude packages from a requirements.txt file (path, Enter to skip): 
Log directory (default: ./logs): 
Log retention days (default: 30): 
Skip pip update? (y/N): 
Skip cleanup? (y/N): 
Dry run only? (y/N): y
Verbose output? (y/N): 
```

### 2. Command-Line Mode

For scripting, automation, or power users, you can provide arguments directly on the command line.

#### Command-Line Arguments

| Argument                   | Description                                                                                                 | Default          |
| -------------------------- | ----------------------------------------------------------------------------------------------------------- | ---------------- |
| `--exclude <PKG>`          | Package to exclude from updates. Can be specified multiple times.                                           | None             |
| `--exclude-from <FILE>`    | Path to a `requirements.txt`-style file. Packages listed in this file will be excluded.                     | None             |
| `--log-dir <DIR>`          | Directory to save log files.                                                                                | `./logs`         |
| `--log-retention-days <N>` | Automatically delete log files older than `N` days. Set to `0` to disable.                                  | 30               |
| `--skip-pip-update`        | Skip the initial step of updating `pip` itself.                                                             | Disabled         |
| `--skip-cleanup`           | Skip the cleanup of invalid package distributions and old logs.                                             | Disabled         |
| `--dry-run`                | Show which packages would be updated without actually updating them.                                        | Disabled         |
| `-v`, `--verbose`          | Show detailed `pip` output on the console instead of just in the log file.                                  | Disabled         |

#### Examples

**1. Dry Run**

See which packages are outdated and would be upgraded, without making any changes.

```bash
python UpdateLibraries.py --dry-run
```

**2. Exclude Specific Packages**

Run the update but prevent `requests` and `numpy` from being upgraded.

```bash
python UpdateLibraries.py --exclude requests --exclude numpy
```

**3. Exclude Packages from a File**

Exclude all packages listed in a `pinned-requirements.txt` file. This is useful for packages you need to keep at a specific version.

```bash
python UpdateLibraries.py --exclude-from pinned-requirements.txt
```

**4. Verbose Output**

Run the update and see all the real-time output from `pip` directly in your console.

```bash
python UpdateLibraries.py --verbose
```

**5. Custom Log Settings**

Store logs in a different directory and keep them for only one week.

```bash
python UpdateLibraries.py --log-dir /var/logs/python-updates --log-retention-days 7
```

## How It Works

The script performs the following steps in order:

1.  **Parse Inputs**: Checks if command-line arguments were provided. If not, it launches the **interactive menu** to gather settings.
2.  **Setup Logging**: Initializes logging to both the console and a timestamped file inside the log directory (e.g., `logs/update_libraries_2023-10-27_10-30-00.log`).
3.  **Run Cleanup (Optional)**:
    *   Deletes log files from previous runs that are older than the configured retention period.
    *   Scans `site-packages` for broken distribution folders (e.g., `~requests`) and removes them.
4.  **Update Pip (Optional)**: Checks if `pip` is outdated and upgrades it if necessary.
5.  **Update Libraries**:
    a. Fetches the list of all outdated packages from `pip`.
    b. Filters out any packages specified for exclusion.
    c. If it's a **dry run**, it prints the list of packages that would be upgraded and exits.
    d. Otherwise, it runs a single `pip install --upgrade` command on the final list of packages.
6.  **Summary Report**: Prints a final summary of the actions taken, including a list of packages that were upgraded or failed, and the final result of the process.

