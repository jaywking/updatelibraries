def interactive_menu():
    print("\nPython Environment Maintenance & Package Updater")
    print("Choose your options below (press Enter for default):\n")

    list_installed_only = input("List installed packages and exit? (y/N): ").strip().lower() == "y"
    if list_installed_only:
        # No need to collect other options if we're just listing packages
        class Args:
            pass

        args = Args()
        args.exclude = []
        args.exclude_from = None
        args.log_dir = "logs"
        args.log_retention_days = 30
        args.skip_pip_update = True
        args.skip_cleanup = True
        args.dry_run = False
        args.no_deps = False
        args.verbose = False
        args.list_installed = True
        return args

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
    no_deps = input("Skip upgrading dependencies? (y/N): ").strip().lower() == "y"
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
    args.no_deps = no_deps
    args.verbose = verbose
    args.list_installed = False
    return args
