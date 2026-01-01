import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    default_log_dir = script_dir / "logs"
    parser = argparse.ArgumentParser(
        description="A script to clean the Python environment and update all outdated packages.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Package to exclude from updates. Can be specified multiple times.\n(e.g., --exclude azure-cli --exclude esphome)",
    )
    parser.add_argument(
        "--exclude-from",
        metavar="FILE",
        help="Path to a requirements.txt file. Packages listed in this file will be excluded from updates.",
    )
    parser.add_argument(
        "--log-dir",
        default=default_log_dir,
        help=f"Directory to save log files.\n(default: {default_log_dir})",
    )
    parser.add_argument(
        "--log-retention-days",
        type=int,
        default=30,
        help="Automatically delete log files older than this many days. Set to 0 to disable.\n(default: 30)",
    )
    parser.add_argument(
        "--skip-pip-update",
        action="store_true",
        help="Skip the initial step of updating pip itself.",
    )
    parser.add_argument(
        "--skip-cleanup",
        action="store_true",
        help="Skip the cleanup of invalid package distributions.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show which packages would be updated without actually updating them.",
    )
    parser.add_argument(
        "--no-deps",
        action="store_true",
        help="Do not install package dependencies when upgrading.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show detailed pip output on the console instead of just in the log file.",
    )
    parser.add_argument(
        "--list-installed",
        action="store_true",
        help="List installed packages (name, version, install date) in a table and exit.",
    )
    return parser.parse_args()
