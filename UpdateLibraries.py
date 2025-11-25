import subprocess
import sys
import json
import logging
import re
from datetime import datetime, timedelta
import site
import shutil
import argparse
from pathlib import Path
from typing import List, Dict, Optional
import time

MAX_UPGRADE_BATCH_SIZE = 5

class ConsoleFormatter(logging.Formatter):
    """A custom formatter that prints INFO messages cleanly but adds the levelname for others."""
    def format(self, record: logging.LogRecord) -> str:
        if record.levelno == logging.INFO:
            return super().format(record).strip()
        # For other levels (WARNING, ERROR, etc.), add the levelname prefix
        return f"{record.levelname}: {record.getMessage()}"

def setup_logging(log_dir: Path, verbose: bool = False) -> None:
    """Sets up logging to both the console and a file named with the current timestamp."""
    log_filename = datetime.now().strftime("update_libraries_%Y-%m-%d_%H-%M-%S.log")
    # Ensure the log directory exists before trying to write to it
    log_dir.mkdir(parents=True, exist_ok=True)
    log_filepath = log_dir / log_filename

    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG) # Set root logger to the lowest level
    
    # Clear existing handlers to avoid duplicate logs
    if logger.hasHandlers():
        logger.handlers.clear()

    # File handler - logs everything with a detailed format
    file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setLevel(logging.DEBUG) # File handler always logs everything
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console handler - logs messages cleanly for a better user experience
    console_handler = logging.StreamHandler(sys.stdout)
    # Show DEBUG (pip output) only if verbose is true, otherwise just INFO and above
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(ConsoleFormatter('%(message)s'))
    logger.addHandler(console_handler)
    
    logging.info(f"--- Log started. Output is being saved to {log_filepath} ---")

def cleanup_old_logs(log_dir: Path, retention_days: int) -> None:
    """Deletes log files in the specified directory older than the retention period."""
    if retention_days <= 0:
        logging.info("Log file cleanup is disabled (retention days is 0 or less).")
        return

    logging.info(f"\nCleaning up log files older than {retention_days} days...")
    now = datetime.now()  # Logs are timestamped using local time
    cutoff = now - timedelta(days=retention_days)
    cleaned_count = 0
    
    try:
        for log_file in log_dir.glob("update_libraries_*.log"):
            if log_file.is_file():
                try:
                    # Extract timestamp string from "update_libraries_YYYY-MM-DD_HH-MM-SS.log"
                    timestamp_str = log_file.name.removeprefix("update_libraries_").removesuffix(".log")
                    log_date = datetime.strptime(timestamp_str, "%Y-%m-%d_%H-%M-%S")
                    if log_date < cutoff:
                        log_file.unlink()
                        logging.info(f"Deleted old log file: {log_file.name}")
                        cleaned_count += 1
                except (ValueError, IndexError):
                    continue # Ignore files that don't match the expected name format
                except OSError as e:
                    logging.warning(f"Could not delete log file {log_file.name}: {e}")
    except FileNotFoundError:
        logging.warning(f"Log directory '{log_dir}' not found for cleanup. Skipping.")
    if cleaned_count == 0:
        logging.info("No old log files to clean up.")

def cleanup_invalid_distributions() -> None:
    """
    Scans for and removes invalid distribution folders (e.g., '~packagename')
    that can be left behind by interrupted pip installations.
    """
    logging.info("\nScanning for and cleaning up invalid package distributions...")
    cleaned_count = 0
    site_packages_paths: list[str] = []

    if hasattr(site, "getsitepackages"):
        try:
            site_packages_paths.extend(site.getsitepackages() or [])
        except Exception as e:  # pragma: no cover - environment specific
            logging.debug(f"Unable to read global site-packages directories: {e}")
    if hasattr(site, "getusersitepackages"):
        try:
            user_site = site.getusersitepackages()
            if user_site:
                site_packages_paths.append(user_site)
        except Exception as e:  # pragma: no cover - environment specific
            logging.debug(f"Unable to read user site-packages directory: {e}")

    for path_str in {str(Path(p)) for p in site_packages_paths if p}:
        site_path = Path(path_str)
        if not site_path.is_dir():
            continue
        try:
            entries = list(site_path.iterdir())
        except OSError as e:
            logging.debug(f"Unable to inspect '{site_path}': {e}")
            continue

        for item in entries:
            if item.is_dir() and item.name.startswith('~'):
                logging.warning(f"Found invalid distribution '{item.name}' in {site_path}. Removing it.")
                try:
                    shutil.rmtree(item)
                    cleaned_count += 1
                except OSError as e:
                    logging.warning(f"Could not remove '{item.name}': {e}")
    if cleaned_count == 0:
        logging.info("No invalid distributions found to clean up.")

def update_pip_itself() -> None:
    """
    Upgrades pip to its latest version, showing output only if an actual upgrade occurs.
    """
    logging.info("Checking and upgrading pip...")
    try:
        # Command to upgrade pip, capturing output to check for an actual upgrade
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'], check=True, text=True, capture_output=True, encoding='utf-8')
        # If pip was already up to date, the output is minimal. If it was upgraded, log the details.
        if "Requirement already satisfied" not in result.stdout:
            logging.info(result.stdout)
            logging.info("Pip was successfully upgraded.")
        else:
            logging.info("Pip is already up to date.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error upgrading pip. The process returned with exit code {e.returncode}.")
        logging.error(f"Pip's error output: {e.stderr}")
        logging.info("Attempting to continue with package updates...")
    except Exception as e:
        logging.error(f"An unexpected error occurred while upgrading pip: {e}")

class UpgradeStatusManager:
    """A helper class to track and display the status of package upgrades."""
    def __init__(self, packages: List[str], verbose: bool):
        self.status: Dict[str, str] = {pkg: "Pending" for pkg in packages}
        self.verbose = verbose
        self.total = len(packages)
        self.done_count = 0

    def update_status(self, line: str):
        """Parses a line from pip's output and updates the status of a package."""
        # Match lines like "Collecting <package>" or "Installing collected <package>"
        match = re.search(r"(?:Collecting|Installing collected package(?:s)?|Attempting uninstall):\s*([a-zA-Z0-9-_]+)", line, re.IGNORECASE)
        if match:
            pkg_name = match.group(1).lower()
            # Normalize names (e.g., pyyaml -> pyYAML)
            for k_orig in self.status.keys():
                if k_orig.lower() == pkg_name and self.status[k_orig] == "Pending":
                    self.status[k_orig] = "In Progress"
                    self.display()
                    return

    def display(self):
        """Displays the current progress on a single line, if not in verbose mode."""
        if not self.verbose:
            in_progress_pkgs = [pkg for pkg, status in self.status.items() if status == "In Progress"]
            if in_progress_pkgs:
                # Show the first package that is "In Progress"
                status_msg = f"({self.done_count + 1}/{self.total}) Upgrading {in_progress_pkgs[0]}..."
                sys.stdout.write("\r" + " " * 60 + "\r") # Clear line
                sys.stdout.write(status_msg)
                sys.stdout.flush()

    def mark_done(self, pkg_name: str):
        """Marks a package as done and updates the progress count."""
        for k_orig in self.status.keys():
            if k_orig.lower() == pkg_name.lower() and self.status[k_orig] != "Done":
                self.status[k_orig] = "Done"
                self.done_count += 1
                self.display() # Refresh display to show next package
                return

def run_with_retries(cmd: list, retries: int = 3, delay: int = 3) -> subprocess.CompletedProcess:
    """Run a subprocess command with retries on failure."""
    last_exception: Optional[subprocess.CalledProcessError] = None
    for attempt in range(retries):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8')
        except subprocess.CalledProcessError as e:
            last_exception = e
            logging.warning(f"Attempt {attempt+1} failed: {e}. Retrying in {delay} seconds...")
            time.sleep(delay)
    logging.error(f"All {retries} attempts failed for command: {' '.join(cmd)}")
    if last_exception:
        raise last_exception
    raise RuntimeError("Command failed without raising CalledProcessError")

def update_all_outdated_libraries(exclude_packages: list[str], dry_run: bool = False, verbose: bool = False) -> None:
    """
    Checks for all outdated Python libraries and upgrades them, showing live progress.
    This script relies on the 'pip' command being in your system's PATH.
    """
    if dry_run:
        # No need for a spinner in dry run, it's fast.
        logging.info("\n--- DRY RUN MODE: Scanning for outdated libraries without making changes ---")
    else:
        logging.info("\nScanning for outdated Python libraries...")

    packages_to_upgrade_info: list[dict] = []
    packages_to_upgrade_names: list[str] = []
    final_return_code = 0 # Default to success, will be updated on error
    failed_packages: set[str] = set()
    try:
        # Use run_with_retries for pip list
        result = run_with_retries(
            [sys.executable, '-m', 'pip', 'list', '--outdated', '--format', 'json']
        )
        outdated_packages_raw = json.loads(result.stdout or "[]")
        if not isinstance(outdated_packages_raw, list):
            raise ValueError("Unexpected response from 'pip list --outdated'")
        if not outdated_packages_raw:
            logging.info("No outdated packages found.")
            return # Exit cleanly, finally block will still execute

        # Filter out packages from the exclusion list
        exclusion_set = {pkg.lower() for pkg in exclude_packages}
        if exclusion_set:
            original_count = len(outdated_packages_raw)
            packages_to_upgrade_info = [
                pkg for pkg in outdated_packages_raw
                if pkg.get('name', '').lower() not in exclusion_set
            ]
            excluded_count = original_count - len(packages_to_upgrade_info)
            if excluded_count > 0:
                logging.info(
                    f"Skipping {excluded_count} package(s) based on the exclusion list: "
                    f"{', '.join(sorted(exclusion_set))}"
                )
        else:
            packages_to_upgrade_info = outdated_packages_raw

        packages_to_upgrade_names = [pkg.get('name') for pkg in packages_to_upgrade_info if pkg.get('name')]

        if not packages_to_upgrade_names:
            logging.info("All outdated packages are in the exclusion list. Nothing to do.")
            return # Exit cleanly, finally block will still execute

        if dry_run:
            logging.info("\n[DRY RUN] The following packages would be upgraded:")
            for pkg in packages_to_upgrade_info:
                current_version = pkg.get('version', 'unknown')
                latest_version = pkg.get('latest_version', 'unknown')
                logging.info(f"- {pkg.get('name', 'unknown')} ({current_version} -> {latest_version})")
            # Clear lists so the summary reports correctly for the finally block
            packages_to_upgrade_info = []
            packages_to_upgrade_names = []
            return

        logging.info(f"Found {len(packages_to_upgrade_names)} outdated package(s). Starting upgrades...")

        status_manager = UpgradeStatusManager(packages_to_upgrade_names, verbose)

        for batch_start in range(0, len(packages_to_upgrade_names), MAX_UPGRADE_BATCH_SIZE):
            batch_names = packages_to_upgrade_names[batch_start:batch_start + MAX_UPGRADE_BATCH_SIZE]
            upgrade_command = [sys.executable, '-m', 'pip', 'install', '--upgrade'] + batch_names
            process = subprocess.Popen(
                upgrade_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            captured_output: list[str] = []

            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    stripped_line = line.strip()
                    captured_output.append(stripped_line)
                    logging.debug(stripped_line) # Log pip output as DEBUG
                    status_manager.update_status(stripped_line)
                    # Check for successfully installed packages to mark them as "Done"
                    if "Successfully installed" in stripped_line:
                        installed_pkgs = stripped_line.split("Successfully installed")[1].strip().split()
                        for pkg_with_version in installed_pkgs:
                            pkg_name = pkg_with_version.split('-')[0]
                            status_manager.mark_done(pkg_name)
                    if "ERROR:" in stripped_line or "Failed" in stripped_line:
                        # Try to extract package name from error line
                        match = re.search(r"ERROR: Could not install packages: ([a-zA-Z0-9-_]+)", stripped_line)
                        if match:
                            failed_packages.add(match.group(1))

            proc_return_code = process.wait()
            if proc_return_code != 0:
                final_return_code = proc_return_code
                logging.error(
                    f"'pip install' exited with code {proc_return_code} while upgrading: {', '.join(batch_names)}"
                )
                for output_line in captured_output:
                    logging.error(output_line)
                failed_packages.update(batch_names)

    except FileNotFoundError:
        logging.error("Error: The 'pip' command was not found. Please ensure Python and pip are correctly installed and added to your system's PATH.")
        final_return_code = 1
    except subprocess.CalledProcessError as e:
        logging.error(f"An error occurred while checking for outdated packages: {e.stderr}")
        final_return_code = e.returncode
    except KeyboardInterrupt:
        logging.error("Update interrupted by user (Ctrl+C).")
        final_return_code = 2
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        final_return_code = 1
    finally:
        # Clear the spinner line before printing the summary
        if not verbose and packages_to_upgrade_names:
            sys.stdout.write("\r" + " " * 60 + "\r") # Clear the status line

        # --- Final Summary ---
        logging.info("\n" + "="*50)
        logging.info("UPDATE SUMMARY")
        logging.info("="*50)

        if dry_run:
            # This message is shown after the list of packages that *would* have been upgraded.
            logging.info("Dry run complete. No changes were made.")
            return # Skip the success/error message for dry runs

        if packages_to_upgrade_info:
            logging.info(f"Upgrade process initiated for the following {len(packages_to_upgrade_info)} package(s):")
            for pkg in packages_to_upgrade_info:
                current_version = pkg.get('version', 'unknown')
                latest_version = pkg.get('latest_version', 'unknown')
                logging.info(f"- {pkg.get('name', 'unknown')}: {current_version} -> {latest_version}")
        elif final_return_code == 0:
            logging.info("No packages required an upgrade.")

        if failed_packages:
            logging.error(f"\nThe following packages failed to upgrade: {', '.join(sorted(failed_packages))}")

        if final_return_code == 0:
            logging.info("\nResult: The upgrade process completed successfully.")
        else:
            logging.error(f"\nResult: The upgrade process failed with exit code {final_return_code}. Please review the log for details.")

def _parse_requirements_file(filepath: str) -> list[str]:
    """Parses a requirements.txt file to extract package names."""
    packages = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                # Strip comments and whitespace
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                # Match the package name (e.g., 'requests' from 'requests==2.31.0')
                match = re.match(r'^[a-zA-Z0-9-_.\[\]]+', line)
                if match:
                    packages.append(match.group(0))
        logging.info(f"Successfully parsed {len(packages)} packages from '{filepath}'.")
    except FileNotFoundError: # pragma: no cover
        logging.error(f"Requirements file not found at '{filepath}'.")
    except Exception as e:
        logging.error(f"Failed to parse requirements file '{filepath}': {e}")
    return packages

def _parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    default_log_dir = script_dir / 'logs'
    parser = argparse.ArgumentParser( # pragma: no cover
        description="A script to clean the Python environment and update all outdated packages.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        '--exclude', 
        action='append',
        default=[],
        help="Package to exclude from updates. Can be specified multiple times.\n(e.g., --exclude azure-cli --exclude esphome)"
    )
    parser.add_argument(
        '--exclude-from',
        metavar='FILE',
        help="Path to a requirements.txt file. Packages listed in this file will be excluded from updates."
    )
    parser.add_argument(
        '--log-dir',
        default=default_log_dir,
        help=f"Directory to save log files.\n(default: {default_log_dir})"
    )
    parser.add_argument(
        '--log-retention-days',
        type=int,
        default=30,
        help="Automatically delete log files older than this many days. Set to 0 to disable.\n(default: 30)"
    )
    parser.add_argument(
        '--skip-pip-update',
        action='store_true',
        help="Skip the initial step of updating pip itself."
    )
    parser.add_argument(
        '--skip-cleanup',
        action='store_true',
        help="Skip the cleanup of invalid package distributions."
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Show which packages would be updated without actually updating them."
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help="Show detailed pip output on the console instead of just in the log file."
    )
    return parser.parse_args()

def interactive_menu():
    print("\nPython Environment Maintenance & Package Updater")
    print("Choose your options below (press Enter for default):\n")

    exclude = []
    while True:
        pkg = input("Exclude a package from updates (type name, Enter to finish): ").strip()
        if not pkg:
            break
        exclude.append(pkg)

    exclude_from = input("Exclude packages from a requirements.txt file (path, Enter to skip): ").strip()
    log_dir = input("Log directory (default: ./logs): ").strip() or "logs"
    try:
        log_retention_days = int(input("Log retention days (default: 30): ").strip() or "30")
    except ValueError:
        log_retention_days = 30
    skip_pip_update = input("Skip pip update? (y/N): ").strip().lower() == "y"
    skip_cleanup = input("Skip cleanup? (y/N): ").strip().lower() == "y"
    dry_run = input("Dry run only? (y/N): ").strip().lower() == "y"
    verbose = input("Verbose output? (y/N): ").strip().lower() == "y"

    # Build a namespace-like object for compatibility
    class Args:
        pass
    args = Args()
    args.exclude = exclude
    args.exclude_from = exclude_from if exclude_from else None
    args.log_dir = log_dir
    args.log_retention_days = log_retention_days
    args.skip_pip_update = skip_pip_update
    args.skip_cleanup = skip_cleanup
    args.dry_run = dry_run
    args.verbose = verbose
    return args

def main() -> None:
    """Main function to parse arguments and run the update process."""
    if len(sys.argv) == 1:
        args = interactive_menu()
    else:
        args = _parse_args()
    
    # Combine exclusions from command line and requirements file
    exclusions = args.exclude
    if args.exclude_from:
        exclusions.extend(_parse_requirements_file(args.exclude_from))

    log_dir_path = Path(args.log_dir)  # Ensure log_dir is a Path object

    setup_logging(log_dir=log_dir_path, verbose=args.verbose)

    if args.log_retention_days > 0:
        cleanup_old_logs(log_dir=log_dir_path, retention_days=args.log_retention_days)

    if not args.skip_cleanup:
        cleanup_invalid_distributions()

    if not args.skip_pip_update:
        update_pip_itself()
    
    try:
        update_all_outdated_libraries(exclude_packages=list(set(exclusions)), dry_run=args.dry_run, verbose=args.verbose)
    except KeyboardInterrupt:
        logging.error("Update interrupted by user (Ctrl+C).")

if __name__ == "__main__":
    main()
