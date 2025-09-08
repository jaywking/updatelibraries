import subprocess
import sys
import json
import logging
import re
from datetime import datetime
from datetime import timedelta, timezone
import site
import shutil
import argparse
from pathlib import Path

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
    now = datetime.now(timezone.utc).astimezone() # Make 'now' timezone-aware
    cutoff = now - timedelta(days=retention_days)
    cleaned_count = 0
    
    try:
        for log_file in log_dir.glob("update_libraries_*.log"):
            if log_file.is_file():
                try:
                    # Extract timestamp string from "update_libraries_YYYY-MM-DD_HH-MM-SS.log"
                    timestamp_str = log_file.name.removeprefix("update_libraries_").removesuffix(".log")
                    log_date = datetime.strptime(timestamp_str, "%Y-%m-%d_%H-%M-%S")
                    # Make log_date timezone-aware for correct comparison
                    if log_date.astimezone() < cutoff:
                        log_file.unlink()
                        logging.info(f"Deleted old log file: {log_file.name}")
                        cleaned_count += 1
                except (ValueError, IndexError):
                    continue # Ignore files that don't match the expected name format
                except OSError as e:
                    logging.warning(f"Could not delete log file {filename}: {e}")
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
    # Get all site-packages directories, including the user-specific one
    site_packages_paths = site.getsitepackages()
    if site.getusersitepackages():
        site_packages_paths.append(site.getusersitepackages())

    for path in set(site_packages_paths): # Use set to avoid duplicates
        site_path = Path(path)
        if site_path.is_dir():
            for item in site_path.iterdir():
                if item.is_dir() and item.name.startswith('~'):
                    logging.warning(f"Found invalid distribution '{item.name}' in {site_path}. Removing it.")
                    shutil.rmtree(item)
                    cleaned_count += 1
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

def update_all_outdated_libraries(exclude_packages: list[str], dry_run: bool = False) -> None:
    """
    Checks for all outdated Python libraries and upgrades them, showing live progress.
    This script relies on the 'pip' command being in your system's PATH.
    """
    if dry_run:
        logging.info("\n--- DRY RUN MODE: Scanning for outdated libraries without making changes ---")
    else:
        logging.info("\nScanning for outdated Python libraries...")

    packages_to_upgrade = []
    final_return_code = 0 # Default to success, will be updated on error
    try:
        # Run pip list --outdated and capture the output
        # Use the JSON format for stable, machine-readable output
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'list', '--outdated', '--format', 'json'],
            capture_output=True, text=True, check=True, encoding='utf-8'
        )
        outdated_packages = [pkg['name'] for pkg in json.loads(result.stdout)]
        if not outdated_packages:
            logging.info("No outdated packages found.")
            return # Exit cleanly, finally block will still execute

        # Filter out packages from the exclusion list
        if exclude_packages:
            original_count = len(outdated_packages)
            packages_to_upgrade = [pkg for pkg in outdated_packages if pkg not in exclude_packages]
            excluded_count = original_count - len(packages_to_upgrade)
            if excluded_count > 0:
                logging.info(f"Skipping {excluded_count} package(s) based on the exclusion list: {', '.join(exclude_packages)}")
        else:
            packages_to_upgrade = outdated_packages

        if not packages_to_upgrade:
            logging.info("All outdated packages are in the exclusion list. Nothing to do.")
            return # Exit cleanly, finally block will still execute

        if dry_run:
            logging.info("\n[DRY RUN] The following packages would be upgraded:")
            for pkg in packages_to_upgrade:
                logging.info(f"- {pkg}")
            # Set packages_to_upgrade to empty so the summary reports correctly for the finally block
            packages_to_upgrade = []
            return

        logging.info(f"Found {len(packages_to_upgrade)} outdated package(s). Starting upgrades...")
        # Upgrade all packages in a single command for better dependency resolution and speed
        upgrade_command = [sys.executable, '-m', 'pip', 'install', '--upgrade'] + packages_to_upgrade
        # Use Popen to stream output live to the logger
        process = subprocess.Popen(upgrade_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')

        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                logging.debug(line.strip()) # Log pip output as DEBUG
        
        proc_return_code = process.wait()
        if proc_return_code != 0:
            final_return_code = proc_return_code

    except FileNotFoundError:
        logging.error("Error: The 'pip' command was not found. Please ensure Python and pip are correctly installed and added to your system's PATH.")
        final_return_code = 1
    except subprocess.CalledProcessError as e:
        logging.error(f"An error occurred while checking for outdated packages: {e.stderr}")
        final_return_code = e.returncode
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        final_return_code = 1
    finally:
        # --- Final Summary ---
        logging.info("\n" + "="*50)
        logging.info("UPDATE SUMMARY")
        logging.info("="*50)

        if dry_run:
            # This message is shown after the list of packages that *would* have been upgraded.
            logging.info("Dry run complete. No changes were made.")
            return # Skip the success/error message for dry runs

        if packages_to_upgrade:
            logging.info(f"Upgrade process initiated for the following {len(packages_to_upgrade)} package(s):")
            for pkg in packages_to_upgrade:
                logging.info(f"- {pkg}")
        elif final_return_code == 0:
            logging.info("No packages required an upgrade.")

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
    script_dir = os.path.dirname(os.path.abspath(__file__))
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
        default=Path(script_dir),
        help=f"Directory to save log files.\n(default: script's directory, {script_dir})"
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

def main() -> None:
    """Main function to parse arguments and run the update process."""
    args = _parse_args()
    
    # Combine exclusions from command line and requirements file
    exclusions = args.exclude
    if args.exclude_from:
        # Use a helper function to parse the file
        exclusions.extend(_parse_requirements_file(args.exclude_from))

    # Set up logging first
    setup_logging(log_dir=Path(args.log_dir), verbose=args.verbose)

    # Clean up old logs based on retention policy
    if not args.skip_cleanup and args.log_retention_days > 0:
        cleanup_old_logs(log_dir=args.log_dir, retention_days=args.log_retention_days)

    # Clean up any broken package folders first
    if not args.skip_cleanup:
        cleanup_invalid_distributions()

    # First, update pip itself
    if not args.skip_pip_update:
        update_pip_itself()
    
    # Then, update all other outdated libraries
    update_all_outdated_libraries(exclude_packages=list(set(exclusions)), dry_run=args.dry_run)

if __name__ == "__main__":
    main()


## comment at the end of the file to test automatic updates