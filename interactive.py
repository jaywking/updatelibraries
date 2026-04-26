import sys
from pathlib import Path


def _ask_yes_no(prompt: str, default: bool = False) -> bool:
    suffix = "Y/n" if default else "y/N"
    try:
        answer = input(f"{prompt} ({suffix}): ").strip().lower()
    except EOFError:
        return default
    if not answer:
        return default
    return answer in {"y", "yes"}


def _find_local_venvs(root: Path = Path(r"C:\LocalVenvs")) -> list[tuple[str, Path]]:
    if not root.is_dir():
        return []

    venvs: list[tuple[str, Path]] = []
    for child in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        python_exe = child / "Scripts" / "python.exe"
        if python_exe.is_file():
            venvs.append((child.name, python_exe))
    return venvs


def _select_local_venvs() -> list[str]:
    venvs = _find_local_venvs()
    if not venvs:
        return []

    use_local_venv = _ask_yes_no("Update a C:\\LocalVenvs environment instead of the current Python?", default=False)
    if not use_local_venv:
        return []

    print("\nLocalVenvs found:")
    for index, (name, python_exe) in enumerate(venvs, start=1):
        print(f"  {index}. {name} ({python_exe})")
    print("  A. All LocalVenvs")
    print("  C. Current Python only")

    while True:
        try:
            choice = input("\nChoose a number, A for all, or C for current Python: ").strip().lower()
        except EOFError:
            return []
        if choice == "a":
            return [str(python_exe) for _, python_exe in venvs]
        if choice == "c" or choice == "":
            return []
        if choice.isdigit():
            index = int(choice)
            if 1 <= index <= len(venvs):
                return [str(venvs[index - 1][1])]
        print("Please choose a listed number, A, or C.")


def interactive_menu():
    print("\nPython Environment Maintenance & Package Updater")
    print(f"Python that will be inspected/modified: {sys.executable}")
    print("Choose your options below (press Enter for default):\n")

    local_venv_targets = _select_local_venvs()

    list_installed_only = _ask_yes_no("List installed packages and exit?", default=False)
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
        args.cancelled = False
        args.local_venv_targets = local_venv_targets
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
    skip_pip_update = _ask_yes_no("Skip pip update?", default=False)
    run_cleanup = _ask_yes_no("Move broken package leftovers to a backup folder if found?", default=True)
    dry_run = _ask_yes_no("Dry run only?", default=False)
    no_deps = _ask_yes_no("Skip upgrading dependencies?", default=False)
    verbose = _ask_yes_no("Verbose output?", default=False)

    proceed = True
    if not dry_run:
        print("\nReady to update packages in:")
        if local_venv_targets:
            for target in local_venv_targets:
                print(f"  {target}")
        else:
            print(f"  {sys.executable}")
        proceed = _ask_yes_no("Proceed with the update?", default=False)

    # Build a namespace-like object for compatibility
    class Args:
        pass

    args = Args()
    args.exclude = exclude
    args.exclude_from = exclude_from if exclude_from else None
    args.log_dir = log_dir
    args.log_retention_days = log_retention_days
    args.skip_pip_update = skip_pip_update
    args.skip_cleanup = not run_cleanup
    args.dry_run = dry_run
    args.no_deps = no_deps
    args.verbose = verbose
    args.list_installed = False
    args.cancelled = not proceed
    args.local_venv_targets = local_venv_targets
    return args
