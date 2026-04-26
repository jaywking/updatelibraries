import subprocess
import sys
import json
import logging
import re
from datetime import datetime, timedelta, timezone
import site
import shutil
from pathlib import Path
from typing import List, Dict, Optional
import importlib.metadata
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
    log_filename = datetime.now().strftime("update_libraries_%Y-%m-%d_%H-%M-%S_%f.log")
    # Ensure the log directory exists before trying to write to it
    log_dir.mkdir(parents=True, exist_ok=True)
    log_filepath = log_dir / log_filename

    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Set root logger to the lowest level

    # Clear existing handlers to avoid duplicate logs
    if logger.hasHandlers():
        logger.handlers.clear()

    # File handler - logs everything with a detailed format
    file_handler = logging.FileHandler(log_filepath, encoding="utf-8")
    file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setLevel(logging.DEBUG)  # File handler always logs everything
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console handler - logs messages cleanly for a better user experience
    console_handler = logging.StreamHandler(sys.stdout)
    # Show DEBUG (pip output) only if verbose is true, otherwise just INFO and above
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(ConsoleFormatter("%(message)s"))
    logger.addHandler(console_handler)

    logging.info(f"--- Log started. Output is being saved to {log_filepath} ---")


def log_python_environment() -> None:
    """Logs the exact Python executable and pip version this run will use."""
    logging.info("\nPython environment selected for this run:")
    logging.info(f"- Python executable: {sys.executable}")
    logging.info(f"- Python prefix: {sys.prefix}")
    if sys.prefix != sys.base_prefix:
        logging.info(f"- Virtual environment detected; base Python: {sys.base_prefix}")
    else:
        logging.info("- Virtual environment: no")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            check=True,
            text=True,
            capture_output=True,
            encoding="utf-8",
        )
        logging.info(f"- Pip: {(result.stdout or '').strip()}")
    except Exception as e:  # pragma: no cover - environment specific
        logging.warning(f"Could not read pip version: {e}")


def canonical_package_name(name: str) -> str:
    """Normalize Python package names for comparisons."""
    package_name = name.strip()
    package_name = package_name.split("[", 1)[0]
    return re.sub(r"[-_.]+", "-", package_name).lower()


def _safe_backup_name(path: Path) -> str:
    """Turns a full path into a readable folder name that is safe on Windows."""
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", str(path).strip("\\/"))


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
                    try:
                        log_date = datetime.strptime(timestamp_str, "%Y-%m-%d_%H-%M-%S_%f")
                    except ValueError:
                        log_date = datetime.strptime(timestamp_str, "%Y-%m-%d_%H-%M-%S")
                    if log_date < cutoff:
                        log_file.unlink()
                        logging.info(f"Deleted old log file: {log_file.name}")
                        cleaned_count += 1
                except (ValueError, IndexError):
                    continue  # Ignore files that don't match the expected name format
                except OSError as e:
                    logging.warning(f"Could not delete log file {log_file.name}: {e}")
    except FileNotFoundError:
        logging.warning(f"Log directory '{log_dir}' not found for cleanup. Skipping.")
    if cleaned_count == 0:
        logging.info("No old log files to clean up.")


def cleanup_invalid_distributions(log_dir: Path) -> None:
    """
    Scans for and quarantines invalid distribution folders (e.g., '~packagename')
    that can be left behind by interrupted pip installations.
    """
    logging.info("\nScanning for invalid package distributions...")
    cleaned_count = 0
    site_packages_paths: list[str] = []
    backup_root = log_dir / "invalid_distributions_backup" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

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
            if item.is_dir() and item.name.startswith("~"):
                logging.warning(f"Found invalid distribution '{item.name}' in {site_path}. Moving it to backup.")
                try:
                    backup_dir = backup_root / _safe_backup_name(site_path)
                    backup_dir.mkdir(parents=True, exist_ok=True)
                    target = backup_dir / item.name
                    suffix = 1
                    while target.exists():
                        target = backup_dir / f"{item.name}_{suffix}"
                        suffix += 1
                    shutil.move(str(item), str(target))
                    logging.info(f"Moved '{item.name}' to '{target}'.")
                    cleaned_count += 1
                except OSError as e:
                    logging.warning(f"Could not move '{item.name}' to backup: {e}")
    if cleaned_count == 0:
        logging.info("No invalid distributions found.")


def update_pip_itself() -> int:
    """
    Upgrades pip to its latest version, showing output only if an actual upgrade occurs.
    """
    logging.info("Checking and upgrading pip...")
    try:
        # Command to upgrade pip, capturing output to check for an actual upgrade
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
            check=True,
            text=True,
            capture_output=True,
            encoding="utf-8",
        )
        # If pip was already up to date, the output is minimal. If it was upgraded, log the details.
        if "Requirement already satisfied" not in result.stdout:
            logging.info(result.stdout)
            logging.info("Pip was successfully upgraded.")
        else:
            logging.info("Pip is already up to date.")
        return 0
    except subprocess.CalledProcessError as e:
        logging.error(f"Error upgrading pip. The process returned with exit code {e.returncode}.")
        logging.error(f"Pip's error output: {e.stderr}")
        logging.info("Attempting to continue with package updates...")
        return e.returncode or 1
    except Exception as e:
        logging.error(f"An unexpected error occurred while upgrading pip: {e}")
        return 1


class UpgradeStatusManager:
    """A helper class to track and display the status of package upgrades."""

    def __init__(self, packages: List[str], verbose: bool):
        self.status: Dict[str, str] = {pkg: "Pending" for pkg in packages}
        self.verbose = verbose
        self.total = len(packages)
        self.done_count = 0

    def update_status(self, line: str) -> None:
        """Parses a line from pip's output and updates the status of a package."""
        # Match lines like "Collecting <package>" or "Installing collected <package>"
        match = re.search(
            r"(?:Collecting|Installing collected package(?:s)?|Attempting uninstall):\s*([a-zA-Z0-9-_]+)",
            line,
            re.IGNORECASE,
        )
        if match:
            pkg_name = canonical_package_name(match.group(1))
            # Normalize names (e.g., pyyaml -> pyYAML)
            for k_orig in self.status.keys():
                if canonical_package_name(k_orig) == pkg_name and self.status[k_orig] == "Pending":
                    self.status[k_orig] = "In Progress"
                    self.display()
                    return

    def display(self) -> None:
        """Displays the current progress on a single line, if not in verbose mode."""
        if not self.verbose:
            in_progress_pkgs = [pkg for pkg, status in self.status.items() if status == "In Progress"]
            if in_progress_pkgs:
                # Show the first package that is "In Progress"
                status_msg = f"({self.done_count + 1}/{self.total}) Upgrading {in_progress_pkgs[0]}..."
                sys.stdout.write("\r" + " " * 60 + "\r")  # Clear line
                sys.stdout.write(status_msg)
                sys.stdout.flush()

    def mark_done(self, pkg_name: str) -> None:
        """Marks a package as done and updates the progress count."""
        normalized_pkg_name = canonical_package_name(pkg_name)
        for k_orig in self.status.keys():
            if canonical_package_name(k_orig) == normalized_pkg_name and self.status[k_orig] != "Done":
                self.status[k_orig] = "Done"
                self.done_count += 1
                self.display()  # Refresh display to show next package
                return


def run_with_retries(cmd: list, retries: int = 3, delay: int = 3) -> subprocess.CompletedProcess:
    """Run a subprocess command with retries on failure."""
    last_exception: Optional[subprocess.CalledProcessError] = None
    for attempt in range(retries):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, check=True, encoding="utf-8")
        except subprocess.CalledProcessError as e:
            last_exception = e
            logging.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay} seconds...")
            time.sleep(delay)
    logging.error(f"All {retries} attempts failed for command: {' '.join(cmd)}")
    if last_exception:
        raise last_exception
    raise RuntimeError("Command failed without raising CalledProcessError")


def list_installed_packages() -> None:
    """
    Lists installed packages with version and install date (based on dist-info mtime)
    in a console-friendly table.
    """
    logging.info("\nCollecting installed package information...")
    rows: list[tuple[str, str, str]] = []
    for dist in importlib.metadata.distributions():
        name = dist.metadata.get("Name") or dist.metadata.get("Summary") or dist.name or "unknown"
        version = dist.version or "unknown"
        install_time_display = "unknown"

        dist_path = getattr(dist, "_path", None)
        if dist_path:
            try:
                # Use the dist-info directory's mtime as an install/update proxy
                mtime = Path(dist_path).stat().st_mtime
                dt = datetime.fromtimestamp(mtime, tz=timezone.utc).astimezone()
                install_time_display = dt.strftime("%Y-%m-%d %H:%M:%S %Z")
            except OSError:
                pass

        rows.append((name, version, install_time_display))

    if not rows:
        logging.info("No installed packages found.")
        return

    # Sort rows by package name for consistency
    rows.sort(key=lambda r: r[0].lower())

    name_width = max(len("Package"), max(len(r[0]) for r in rows))
    version_width = max(len("Version"), max(len(r[1]) for r in rows))
    installed_width = max(len("Installed"), max(len(r[2]) for r in rows))

    header = f"{'Package':<{name_width}}  {'Version':<{version_width}}  {'Installed':<{installed_width}}"
    separator = "-" * len(header)

    logging.info("\nInstalled packages:")
    logging.info(header)
    logging.info(separator)
    for name, version, installed in rows:
        logging.info(f"{name:<{name_width}}  {version:<{version_width}}  {installed:<{installed_width}}")
    logging.info(f"\nTotal packages: {len(rows)}")


def _run_upgrade_command(
    package_names: list[str],
    status_manager: UpgradeStatusManager,
    no_deps: bool,
) -> tuple[int, list[str]]:
    upgrade_command = [sys.executable, "-m", "pip", "install", "--upgrade"]
    if no_deps:
        upgrade_command.append("--no-deps")
    upgrade_command += package_names

    process = subprocess.Popen(
        upgrade_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    captured_output: list[str] = []

    if process.stdout is None:
        return process.wait(), captured_output

    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            stripped_line = line.strip()
            captured_output.append(stripped_line)
            logging.debug(stripped_line)
            status_manager.update_status(stripped_line)
            if "Successfully installed" in stripped_line:
                installed_pkgs = stripped_line.split("Successfully installed", 1)[1].strip().split()
                for pkg_with_version in installed_pkgs:
                    pkg_name = pkg_with_version.rsplit("-", 1)[0]
                    status_manager.mark_done(pkg_name)

    return process.wait(), captured_output


def update_all_outdated_libraries(
    exclude_packages: list[str],
    dry_run: bool = False,
    verbose: bool = False,
    no_deps: bool = False,
) -> int:
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
    final_return_code = 0
    failed_packages: set[str] = set()
    try:
        result = run_with_retries([sys.executable, "-m", "pip", "list", "--outdated", "--format", "json"])
        outdated_packages_raw = json.loads(result.stdout or "[]")
        if not isinstance(outdated_packages_raw, list):
            raise ValueError("Unexpected response from 'pip list --outdated'")

        exclusion_set = {canonical_package_name(pkg) for pkg in exclude_packages if pkg.strip()}
        if exclusion_set:
            original_count = len(outdated_packages_raw)
            packages_to_upgrade_info = [
                pkg for pkg in outdated_packages_raw if canonical_package_name(pkg.get("name", "")) not in exclusion_set
            ]
            excluded_count = original_count - len(packages_to_upgrade_info)
            if excluded_count > 0:
                logging.info(
                    "Skipping {count} package(s) based on the exclusion list: {names}".format(
                        count=excluded_count, names=", ".join(sorted(exclusion_set))
                    )
                )
        else:
            packages_to_upgrade_info = outdated_packages_raw

        packages_to_upgrade_names = [pkg.get("name") for pkg in packages_to_upgrade_info if pkg.get("name")]

        if not outdated_packages_raw:
            logging.info("No outdated packages found.")
        elif not packages_to_upgrade_names:
            logging.info("All outdated packages are in the exclusion list. Nothing to do.")
        elif dry_run:
            logging.info("\n[DRY RUN] The following packages would be upgraded:")
            for pkg in packages_to_upgrade_info:
                current_version = pkg.get("version", "unknown")
                latest_version = pkg.get("latest_version", "unknown")
                logging.info(f"- {pkg.get('name', 'unknown')} ({current_version} -> {latest_version})")
        elif packages_to_upgrade_names:
            logging.info(f"Found {len(packages_to_upgrade_names)} outdated package(s). Starting upgrades...")

            status_manager = UpgradeStatusManager(packages_to_upgrade_names, verbose)

            for batch_start in range(0, len(packages_to_upgrade_names), MAX_UPGRADE_BATCH_SIZE):
                batch_names = packages_to_upgrade_names[batch_start : batch_start + MAX_UPGRADE_BATCH_SIZE]
                proc_return_code, captured_output = _run_upgrade_command(
                    batch_names,
                    status_manager,
                    no_deps=no_deps,
                )
                if proc_return_code == 0:
                    continue

                if len(batch_names) > 1:
                    logging.warning(
                        "'pip install' failed while upgrading this batch; retrying one package at a time: {names}".format(
                            names=", ".join(batch_names)
                        )
                    )
                    logging.debug("\n".join(captured_output))
                    for package_name in batch_names:
                        single_code, single_output = _run_upgrade_command(
                            [package_name],
                            status_manager,
                            no_deps=no_deps,
                        )
                        if single_code != 0:
                            final_return_code = single_code or 1
                            failed_packages.add(package_name)
                            logging.error(
                                "'pip install' exited with code {code} while upgrading: {name}".format(
                                    code=single_code, name=package_name
                                )
                            )
                            for output_line in single_output:
                                logging.error(output_line)
                    continue

                final_return_code = proc_return_code or 1
                failed_packages.update(batch_names)
                logging.error(
                    "'pip install' exited with code {code} while upgrading: {names}".format(
                        code=proc_return_code, names=", ".join(batch_names)
                    )
                )
                for output_line in captured_output:
                    logging.error(output_line)

    except FileNotFoundError:
        logging.error(
            "Error: The 'pip' command was not found. Please ensure Python and pip are correctly installed and added to your system's PATH."
        )
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

    if not verbose and packages_to_upgrade_names:
        sys.stdout.write("\r" + " " * 60 + "\r")

    logging.info("\n" + "=" * 50)
    logging.info("UPDATE SUMMARY")
    logging.info("=" * 50)

    if dry_run:
        logging.info("Dry run complete. No changes were made.")
        return final_return_code

    if packages_to_upgrade_info:
        logging.info(f"Upgrade process attempted for the following {len(packages_to_upgrade_info)} package(s):")
        for pkg in packages_to_upgrade_info:
            current_version = pkg.get("version", "unknown")
            latest_version = pkg.get("latest_version", "unknown")
            logging.info(f"- {pkg.get('name', 'unknown')}: {current_version} -> {latest_version}")
    elif final_return_code == 0:
        logging.info("No packages required an upgrade.")

    if failed_packages:
        logging.error(f"\nThe following packages failed to upgrade: {', '.join(sorted(failed_packages))}")

    if final_return_code == 0:
        logging.info("\nResult: The upgrade process completed successfully.")
    else:
        logging.error(
            f"\nResult: The upgrade process failed with exit code {final_return_code}. Please review the log for details."
        )
    return final_return_code


def run_pip_check() -> int:
    """Runs `pip check` and logs dependency conflicts distinctly."""
    logging.info("\nRunning dependency check (pip check)...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "check"],
            text=True,
            capture_output=True,
            encoding="utf-8",
        )
        output = (result.stdout or "").strip()
        if result.returncode == 0:
            logging.info("Dependency check passed: no conflicts found.")
            return 0

        if output:
            for line in output.splitlines():
                line = line.strip()
                if line:
                    logging.error(f"Dependency conflict: {line}")
        else:
            logging.error("Dependency check failed with no output.")
        return result.returncode or 1
    except FileNotFoundError:
        logging.error("Error: The 'pip' command was not found for dependency check.")
        return 1
    except Exception as e:
        logging.error(f"An unexpected error occurred during dependency check: {e}")
        return 1


def parse_requirements_file(filepath: str) -> list[str]:
    """Parses a requirements.txt file to extract package names."""
    packages = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.split("#", 1)[0].strip()
                if not line or line.startswith("-") or "://" in line:
                    continue
                match = re.match(r"^[a-zA-Z0-9-_.\[\]]+", line)
                if match:
                    packages.append(canonical_package_name(match.group(0)))
        logging.info(f"Successfully parsed {len(packages)} packages from '{filepath}'.")
    except FileNotFoundError:  # pragma: no cover
        logging.error(f"Requirements file not found at '{filepath}'.")
    except Exception as e:
        logging.error(f"Failed to parse requirements file '{filepath}': {e}")
    return packages
