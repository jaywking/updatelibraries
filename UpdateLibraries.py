import sys
import os
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
    restore_environment,
    run_pip_check,
    snapshot_environment,
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
    if getattr(args, "restore_snapshot", None):
        forwarded.extend(["--restore-snapshot", args.restore_snapshot])
    for constraint_file in args.constraint:
        forwarded.extend(["--constraint", constraint_file])
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
    if getattr(args, "confirm_preflight", False):
        forwarded.append("--confirm-preflight")
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


def _confirm_preflight_plan(installations: list[dict]) -> bool:
    print("\n" + "=" * 60, flush=True)
    print("RESOLVED UPDATE PLAN", flush=True)
    print("=" * 60, flush=True)
    if not installations:
        print("Pip found no distribution changes.", flush=True)
    else:
        print(f"{'Package':<32} {'Planned version':<20} Status", flush=True)
        print("-" * 60, flush=True)
        for installation in installations:
            metadata = installation.get("metadata", {})
            name = metadata.get("name", "unknown")
            version = metadata.get("version", "unknown")
            print(f"{name:<32} {version:<20} Upgrade", flush=True)
    while True:
        try:
            choice = input("\n[R] Run this plan  [C] Cancel: ").strip().lower()
        except EOFError:
            return False
        if choice == "r":
            return True
        if choice in {"c", ""}:
            return False
        print("Please choose R or C.")


def _log_completion_dashboard(
    update_outcome: dict,
    update_return_code: int,
    dependency_return_code: int,
    log_filepath: Path,
    snapshot_path: Path | None,
    restored_snapshot: Path | None = None,
) -> None:
    logging.info("\n" + "=" * 60)
    logging.info(" FINAL RESULTS")
    logging.info("=" * 60)
    if restored_snapshot:
        status = "[OK] completed" if update_return_code == 0 else "[ERROR] failed"
        logging.info(f"Restore: {status}")
        logging.info(f"Source snapshot: {restored_snapshot}")
    elif update_outcome.get("preflight") == "cancelled":
        logging.info("Update: [CANCELLED] after reviewing the resolved plan; no packages were changed.")
    elif update_return_code == 0:
        logging.info("Update: [OK] completed successfully.")
    else:
        logging.error("Update: [ERROR] completed with errors.")
    logging.info(
        "Packages: {attempted} selected, {managed} dependency-managed skipped, {excluded} user-excluded, {failed} failed.".format(
            attempted=update_outcome.get("attempted", 0),
            managed=len(update_outcome.get("managed_skipped", [])),
            excluded=update_outcome.get("excluded", 0),
            failed=len(update_outcome.get("failed", [])),
        )
    )
    validation_status = "[OK] passed" if dependency_return_code == 0 else "[ERROR] failed"
    logging.info(f"Dependency validation: {validation_status}.")
    logging.info(f"Log file: {log_filepath}")
    if snapshot_path:
        logging.info(f"Recovery snapshot: {snapshot_path}")


def _run_action(args) -> int:
    """Run one selected action and return its process-style exit code."""
    if getattr(args, "cancelled", False):
        print("Update cancelled. No changes were made.")
        return 0

    if getattr(args, "local_venv_targets", None):
        final_return_code = _run_for_local_venvs(args)
        return final_return_code

    log_dir_path = Path(args.log_dir)  # Ensure log_dir is a Path object

    log_filepath = setup_logging(log_dir=log_dir_path, verbose=args.verbose)
    log_python_environment()

    if getattr(args, "restore_snapshot", None):
        restore_path = Path(args.restore_snapshot)
        restore_return_code = restore_environment(restore_path)
        dependency_return_code = run_pip_check(snapshot_path=restore_path)
        _log_completion_dashboard(
            update_outcome={},
            update_return_code=restore_return_code,
            dependency_return_code=dependency_return_code,
            log_filepath=log_filepath,
            snapshot_path=None,
            restored_snapshot=restore_path,
        )
        if restore_return_code or dependency_return_code:
            return max(restore_return_code, dependency_return_code)
        return 0

    # Combine exclusions from command line and requirements file
    exclusions = list(args.exclude)
    if args.exclude_from:
        exclusions.extend(parse_requirements_file(args.exclude_from))

    if getattr(args, "list_installed", False):
        list_installed_packages()
        return 0

    final_return_code = 0
    snapshot_path = None
    update_outcome: dict = {}
    update_return_code = 0
    dependency_return_code = 0

    if args.dry_run:
        logging.info("\nDry run selected: skipping old log cleanup, package cleanup, and pip self-update.")
    else:
        logging.info("\nProgress: creating recovery snapshot...")
        snapshot_path = snapshot_environment(log_dir=log_dir_path)

        if args.log_retention_days > 0:
            cleanup_old_logs(log_dir=log_dir_path, retention_days=args.log_retention_days)

        if not args.skip_cleanup:
            cleanup_invalid_distributions(log_dir=log_dir_path)

        if not args.skip_pip_update:
            final_return_code = max(final_return_code, update_pip_itself())

    try:
        logging.info("\nProgress: resolving and upgrading packages...")
        update_return_code = update_all_outdated_libraries(
            exclude_packages=list(set(exclusions)),
            constraint_files=args.constraint,
            dry_run=args.dry_run,
            verbose=args.verbose,
            no_deps=args.no_deps,
            confirm_preflight=_confirm_preflight_plan if getattr(args, "confirm_preflight", False) else None,
            outcome=update_outcome,
        )
        final_return_code = max(final_return_code, update_return_code)
        if args.dry_run:
            logging.info("\nDependency check skipped due to dry run.")
        else:
            logging.info("\nProgress: package upgrades finished; validating dependencies...")
            dependency_return_code = run_pip_check(snapshot_path=snapshot_path)
            final_return_code = max(final_return_code, dependency_return_code)
    except KeyboardInterrupt:
        logging.error("Update interrupted by user (Ctrl+C).")
        final_return_code = 2

    if args.dry_run:
        dependency_return_code = 0
    _log_completion_dashboard(
        update_outcome=update_outcome,
        update_return_code=update_return_code,
        dependency_return_code=dependency_return_code,
        log_filepath=log_filepath,
        snapshot_path=snapshot_path,
    )

    return final_return_code


def _wait_for_main_menu() -> None:
    """Wait for a key press before showing the interactive menu again."""
    print("\nPress any key to return to the main menu...", end="", flush=True)
    try:
        import msvcrt

        msvcrt.getwch()
    except (ImportError, OSError):
        input()
    os.system("cls" if os.name == "nt" else "clear")


def main() -> None:
    """Run either the repeating interactive menu or one command-line action."""
    if len(sys.argv) != 1:
        exit_code = _run_action(parse_args())
        if exit_code:
            sys.exit(exit_code)
        return

    while True:
        args = interactive_menu()
        if getattr(args, "cancelled", False):
            print("Goodbye.")
            return

        exit_code = _run_action(args)
        if exit_code:
            print(f"\nAction completed with exit code {exit_code}.")
        else:
            print("\n[OK] Action complete.")
        _wait_for_main_menu()

if __name__ == "__main__":
    main()
