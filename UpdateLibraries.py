import sys
import logging
import subprocess
from pathlib import Path

from cli import parse_args
from interactive import interactive_menu
from updater import (
    cleanup_invalid_distributions,
    cleanup_old_logs,
    list_installed_packages,
    log_python_environment,
    parse_requirements_file,
    run_pip_check,
    setup_logging,
    update_all_outdated_libraries,
    update_pip_itself,
)


def _build_forwarded_args(args) -> list[str]:
    forwarded: list[str] = []
    for package in args.exclude:
        forwarded.extend(["--exclude", package])
    if args.exclude_from:
        forwarded.extend(["--exclude-from", args.exclude_from])
    forwarded.extend(["--log-dir", str(args.log_dir)])
    forwarded.extend(["--log-retention-days", str(args.log_retention_days)])
    if args.skip_pip_update:
        forwarded.append("--skip-pip-update")
    if args.skip_cleanup:
        forwarded.append("--skip-cleanup")
    if args.dry_run:
        forwarded.append("--dry-run")
    if args.no_deps:
        forwarded.append("--no-deps")
    if args.verbose:
        forwarded.append("--verbose")
    if getattr(args, "list_installed", False):
        forwarded.append("--list-installed")
    return forwarded


def _run_for_local_venvs(args) -> int:
    script_path = Path(__file__).resolve()
    forwarded_args = _build_forwarded_args(args)
    final_return_code = 0

    for target in args.local_venv_targets:
        python_exe = Path(target)
        if not python_exe.is_file():
            print(f"Skipping missing LocalVenv Python: {python_exe}")
            final_return_code = max(final_return_code, 1)
            continue

        print("\n" + "=" * 70, flush=True)
        print(f"Running updater with LocalVenv Python: {python_exe}", flush=True)
        print("=" * 70, flush=True)
        result = subprocess.run(
            [str(python_exe), str(script_path), *forwarded_args],
            cwd=str(script_path.parent),
        )
        final_return_code = max(final_return_code, result.returncode)

    return final_return_code


def main() -> None:
    """Main function to parse arguments and run the update process."""
    if len(sys.argv) == 1:
        args = interactive_menu()
    else:
        args = parse_args()

    if getattr(args, "cancelled", False):
        print("Update cancelled. No changes were made.")
        return

    if getattr(args, "local_venv_targets", None):
        final_return_code = _run_for_local_venvs(args)
        if final_return_code:
            sys.exit(final_return_code)
        return

    log_dir_path = Path(args.log_dir)  # Ensure log_dir is a Path object

    setup_logging(log_dir=log_dir_path, verbose=args.verbose)
    log_python_environment()

    # Combine exclusions from command line and requirements file
    exclusions = list(args.exclude)
    if args.exclude_from:
        exclusions.extend(parse_requirements_file(args.exclude_from))

    if getattr(args, "list_installed", False):
        list_installed_packages()
        return

    final_return_code = 0

    if args.dry_run:
        logging.info("\nDry run selected: skipping old log cleanup, package cleanup, and pip self-update.")
    else:
        if args.log_retention_days > 0:
            cleanup_old_logs(log_dir=log_dir_path, retention_days=args.log_retention_days)

        if not args.skip_cleanup:
            cleanup_invalid_distributions(log_dir=log_dir_path)

        if not args.skip_pip_update:
            final_return_code = max(final_return_code, update_pip_itself())

    try:
        update_return_code = update_all_outdated_libraries(
            exclude_packages=list(set(exclusions)),
            dry_run=args.dry_run,
            verbose=args.verbose,
            no_deps=args.no_deps,
        )
        final_return_code = max(final_return_code, update_return_code)
        if args.dry_run:
            logging.info("\nDependency check skipped due to dry run.")
        else:
            final_return_code = max(final_return_code, run_pip_check())
    except KeyboardInterrupt:
        logging.error("Update interrupted by user (Ctrl+C).")
        final_return_code = 2

    if final_return_code:
        sys.exit(final_return_code)

if __name__ == "__main__":
    main()
