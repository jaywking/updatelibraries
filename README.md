# Python Environment Maintenance & Package Updater

This Python script provides a comprehensive solution for maintaining a clean and up-to-date Python environment. It automatically finds and upgrades all outdated packages, cleans up broken installations, and manages its own log files.

## Features

- **Automatic Package Updates**: Finds and upgrades all outdated `pip` packages in a single, efficient operation.
- **Self-Updating `pip`**: Ensures `pip` itself is the latest version before proceeding with other packages.
- **Environment Cleanup**: Scans for and removes temporary or broken package folders (e.g., `~packagename`) left by interrupted installations.
- **Flexible Exclusions**: Exclude specific packages from being updated via command-line arguments or by providing a `requirements.txt` file.
- **Dry Run Mode**: Preview which packages would be updated without making any actual changes to your environment.
- **Robust Logging**: Creates a timestamped log file for every run and automatically cleans up old logs based on a configurable retention period.
- **User-Friendly Progress**: Displays a clean, single-line progress indicator during updates, with a verbose option for detailed `pip` output.

## Prerequisites

- Python 3.x
- `pip` installed and accessible in the system's PATH.

## Usage

To run the script, navigate to its directory in your terminal and use the `python` command.

```bash
python UpdateLibraries.py [OPTIONS]
```

### Command-Line Arguments

| Argument                  | Description                                                                                                 | Default                               |
| ------------------------- | ----------------------------------------------------------------------------------------------------------- | ------------------------------------- |
| `--exclude <PKG>`         | Package to exclude from updates. Can be specified multiple times.                                           | None                                  |
| `--exclude-from <FILE>`   | Path to a `requirements.txt`-style file. Packages listed in this file will be excluded.                     | None                                  |
| `--log-dir <DIR>`         | Directory to save log files.                                                                                | The script's directory                |
| `--log-retention-days <N>`| Automatically delete log files older than `N` days. Set to `0` to disable.                                  | 30                                    |
| `--skip-pip-update`       | Skip the initial step of updating `pip` itself.                                                             | Disabled                              |
| `--skip-cleanup`          | Skip the cleanup of invalid package distributions and old logs.                                             | Disabled                              |
| `--dry-run`               | Show which packages would be updated without actually updating them.                                        | Disabled                              |
| `-v`, `--verbose`         | Show detailed `pip` output on the console instead of just in the log file.                                  | Disabled                              |

---

### Examples

**1. Basic Run**

Run the script with default settings. It will clean the environment, update pip, and then update all outdated packages.

```bash
python UpdateLibraries.py
```

**2. Dry Run**

See which packages are outdated and would be upgraded, without making any changes.

```bash
python UpdateLibraries.py --dry-run
```

**3. Exclude Specific Packages**

Run the update but prevent `requests` and `numpy` from being upgraded.

```bash
python UpdateLibraries.py --exclude requests --exclude numpy
```

**4. Exclude Packages from a File**

Exclude all packages listed in a `pinned-requirements.txt` file. This is useful for packages you need to keep at a specific version.

```bash
python UpdateLibraries.py --exclude-from pinned-requirements.txt
```

**5. Verbose Output**

Run the update and see all the real-time output from `pip` directly in your console.

```bash
python UpdateLibraries.py --verbose
```

**6. Custom Log Settings**

Store logs in a different directory and keep them for only one week.

```bash
python UpdateLibraries.py --log-dir /var/logs/python-updates --log-retention-days 7
```

## How It Works

The script performs the following steps in order:

1.  **Setup Logging**: Initializes logging to both the console and a timestamped file in the specified log directory.
2.  **Cleanup Old Logs**: Deletes log files from previous runs that are older than the configured retention period.
3.  **Cleanup Invalid Distributions**: Scans `site-packages` for directories starting with `~` and removes them to fix a common `pip` issue.
4.  **Update Pip**: Checks if `pip` is outdated and upgrades it if necessary.
5.  **Update Libraries**:
    a. Runs `pip list --outdated` to get a list of all outdated packages.
    b. Filters out any packages specified in the exclusion arguments.
    c. If not a dry run, it runs `pip install --upgrade` on the final list of packages.
6.  **Summary Report**: Prints a final summary of the actions taken and the result of the process.

