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

    use_local_venv = _ask_yes_no("Choose a C:\\LocalVenvs environment instead of the current Python?", default=False)
    if not use_local_venv:
        return []

    print("\nAvailable LocalVenvs:")
    for index, (name, python_exe) in enumerate(venvs, start=1):
        print(f"  {index}. {name}\n     {python_exe}")
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


def _new_args():
    class Args:
        pass

    return Args()


def _choose_action() -> str:
    print("\nPython Environment Maintenance & Package Updater")
    print(f"Current Python: {sys.executable}")
    print("\n  1. Preview updates (recommended)")
    print("  2. Update packages now")
    print("  3. List installed packages")
    print("  4. Restore a package snapshot")
    print("  5. Exit")

    while True:
        try:
            choice = input("\nChoose an action [1-5]: ").strip()
        except EOFError:
            return "exit"
        if choice in {"1", "2", "3", "4", "5"}:
            return {"1": "preview", "2": "update", "3": "list", "4": "restore", "5": "exit"}[choice]
        print("Please choose 1, 2, 3, 4, or 5.")


def _snapshot_summary(snapshot_path: Path) -> tuple[str, int]:
    target = "Unknown (legacy snapshot)"
    package_count = 0
    try:
        for line in snapshot_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("# Python executable: "):
                target = line.removeprefix("# Python executable: ")
            elif line and not line.startswith("#"):
                package_count += 1
    except OSError:
        return "Unreadable snapshot", 0
    return target, package_count


def _select_snapshot(log_dir: Path) -> Path | None:
    snapshot_dir = log_dir / "environment_snapshots"
    snapshots = sorted(snapshot_dir.glob("pip_freeze_*.txt"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not snapshots:
        print(f"\nNo snapshots found in {snapshot_dir}.")
        return None

    print(f"\nSnapshots in {snapshot_dir}:")
    for index, snapshot_path in enumerate(snapshots, start=1):
        target, package_count = _snapshot_summary(snapshot_path)
        print(f"  {index}. {snapshot_path.name} — {package_count} packages")
        print(f"     Target: {target}")

    while True:
        try:
            choice = input("\nChoose a snapshot number or B to go back: ").strip().lower()
        except EOFError:
            return None
        if choice in {"b", ""}:
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(snapshots):
            return snapshots[int(choice) - 1]
        print("Please choose a listed snapshot number or B.")


def _collect_options(dry_run: bool, local_venv_targets: list[str]):
    args = _new_args()
    args.exclude = []
    print("\nOptional update settings (press Enter to keep the recommended default):")
    while True:
        pkg = input("Exclude a package from updates (type name, Enter to finish): ").strip()
        if not pkg:
            break
        args.exclude.append(pkg)

    exclude_from = input("Exclude packages from a requirements.txt file (path, Enter to skip): ").strip()
    args.exclude_from = exclude_from or None
    args.constraint = []
    while True:
        constraint_file = input("Constraints file for version limits (path, Enter to finish): ").strip()
        if not constraint_file:
            break
        args.constraint.append(constraint_file)

    args.log_dir = input("Log directory (default: ./logs): ").strip() or "logs"
    try:
        args.log_retention_days = int(input("Log retention days (default: 30): ").strip() or "30")
    except ValueError:
        args.log_retention_days = 30

    args.dry_run = dry_run
    args.skip_pip_update = dry_run or _ask_yes_no("Skip pip update?", default=False)
    args.skip_cleanup = dry_run or not _ask_yes_no("Move broken package leftovers to a backup folder if found?", default=True)
    args.no_deps = _ask_yes_no("Skip dependency upgrades? This can cause conflicts", default=False)
    args.verbose = _ask_yes_no("Show detailed pip output?", default=False)
    args.list_installed = False
    args.restore_snapshot = None
    args.confirm_preflight = not dry_run
    args.cancelled = False
    args.local_venv_targets = local_venv_targets
    return args


def _review_plan(args) -> str:
    print("\n" + "=" * 60)
    print("UPDATE PLAN")
    print("=" * 60)
    print(f"Mode: {'Preview only (no changes)' if args.dry_run else 'Update packages'}")
    print("Target environment(s):")
    targets = args.local_venv_targets or [sys.executable]
    for target in targets:
        print(f"- {target}")
    print(f"Excluded packages: {', '.join(args.exclude) if args.exclude else 'None'}")
    print(f"Exclusion file: {args.exclude_from or 'None'}")
    print(f"Constraints: {', '.join(args.constraint) if args.constraint else 'None'}")
    print(f"Log directory: {args.log_dir}")
    print(f"Dependencies: {'Do not upgrade dependencies (risk of conflicts)' if args.no_deps else 'Resolve dependencies normally'}")
    if not args.dry_run:
        print(f"Pip self-update: {'Skip' if args.skip_pip_update else 'Run'}")
        print(f"Cleanup invalid package folders: {'Skip' if args.skip_cleanup else 'Run'}")

    if args.dry_run:
        print("\nSafety: no packages, pip, cleanup folders, or dependency state will be changed.")
        proceed_key = "P"
        proceed_label = "Preview"
    else:
        print("\nSafety: a package snapshot will be saved before changes.")
        print("Safety: pip will resolve and display the full upgrade plan before installation.")
        print("Safety: dependency-managed packages are updated only through their parent package.")
        print("Safety: pip check will validate dependencies after installation.")
        proceed_key = "R"
        proceed_label = "Run update"

    while True:
        try:
            choice = input(f"\n[{proceed_key}] {proceed_label}  [B] Back  [Q] Cancel: ").strip().lower()
        except EOFError:
            return "cancel"
        if choice == proceed_key.lower():
            return "proceed"
        if choice == "b":
            return "back"
        if choice in {"q", ""}:
            return "cancel"
        print(f"Please choose {proceed_key}, B, or Q.")


def _review_restore(snapshot_path: Path, local_venv_targets: list[str]) -> bool:
    snapshot_target, package_count = _snapshot_summary(snapshot_path)
    target = local_venv_targets[0] if local_venv_targets else sys.executable
    print("\n" + "=" * 60)
    print("RESTORE SNAPSHOT")
    print("=" * 60)
    print(f"Snapshot: {snapshot_path}")
    print(f"Snapshot target: {snapshot_target}")
    print(f"Packages recorded: {package_count}")
    print(f"Restore target: {target}")
    if snapshot_target != "Unknown (legacy snapshot)" and Path(snapshot_target) != Path(target):
        print("WARNING: the snapshot was created for a different Python executable.")
    print("\nThis reinstalls the recorded versions but does not remove packages added later.")
    try:
        return input("Type RESTORE to continue, or press Enter to cancel: ").strip() == "RESTORE"
    except EOFError:
        return False


def interactive_menu():
    while True:
        action = _choose_action()
        if action == "exit":
            args = _new_args()
            args.cancelled = True
            args.local_venv_targets = []
            return args

        local_venv_targets = _select_local_venvs()
        if action == "list":
            args = _new_args()
            args.exclude = []
            args.exclude_from = None
            args.constraint = []
            args.log_dir = "logs"
            args.log_retention_days = 30
            args.skip_pip_update = True
            args.skip_cleanup = True
            args.dry_run = False
            args.no_deps = False
            args.verbose = False
            args.list_installed = True
            args.restore_snapshot = None
            args.confirm_preflight = False
            args.cancelled = False
            args.local_venv_targets = local_venv_targets
            return args

        if action == "restore":
            if len(local_venv_targets) > 1:
                print("Snapshot restore supports one environment at a time. Please select one environment.")
                continue
            log_dir = Path(input("Snapshot log directory (default: ./logs): ").strip() or "logs")
            snapshot_path = _select_snapshot(log_dir)
            if not snapshot_path:
                continue
            if not _review_restore(snapshot_path, local_venv_targets):
                print("Snapshot restore cancelled. No changes were made.")
                continue

            args = _new_args()
            args.cancelled = False
            args.local_venv_targets = local_venv_targets
            args.restore_snapshot = str(snapshot_path.resolve())
            args.confirm_preflight = False
            args.exclude = []
            args.exclude_from = None
            args.constraint = []
            args.log_dir = str(log_dir)
            args.log_retention_days = 30
            args.skip_pip_update = True
            args.skip_cleanup = True
            args.dry_run = False
            args.no_deps = False
            args.verbose = False
            args.list_installed = False
            return args

        args = _collect_options(dry_run=action == "preview", local_venv_targets=local_venv_targets)
        decision = _review_plan(args)
        if decision == "proceed":
            return args
        if decision == "cancel":
            args.cancelled = True
            return args
