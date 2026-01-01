import sys
import logging
from pathlib import Path

from cli import parse_args
from interactive import interactive_menu
from updater import (
    cleanup_invalid_distributions,
    cleanup_old_logs,
    list_installed_packages,
    parse_requirements_file,
    run_pip_check,
    setup_logging,
    update_all_outdated_libraries,
    update_pip_itself,
)

def main() -> None:
    """Main function to parse arguments and run the update process."""
    if len(sys.argv) == 1:
        args = interactive_menu()
    else:
        args = parse_args()
    
    # Combine exclusions from command line and requirements file
    exclusions = args.exclude
    if args.exclude_from:
        exclusions.extend(parse_requirements_file(args.exclude_from))

    log_dir_path = Path(args.log_dir)  # Ensure log_dir is a Path object

    setup_logging(log_dir=log_dir_path, verbose=args.verbose)

    if getattr(args, "list_installed", False):
        list_installed_packages()
        return

    if args.log_retention_days > 0:
        cleanup_old_logs(log_dir=log_dir_path, retention_days=args.log_retention_days)

    if not args.skip_cleanup:
        cleanup_invalid_distributions()

    if not args.skip_pip_update:
        update_pip_itself()
    
    try:
        update_all_outdated_libraries(
            exclude_packages=list(set(exclusions)),
            dry_run=args.dry_run,
            verbose=args.verbose,
            no_deps=args.no_deps,
        )
        if args.dry_run:
            logging.info("\nDependency check skipped due to dry run.")
        else:
            run_pip_check()
    except KeyboardInterrupt:
        logging.error("Update interrupted by user (Ctrl+C).")

if __name__ == "__main__":
    main()
