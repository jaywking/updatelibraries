import subprocess
import sys
import json
import logging
from datetime import datetime
import site
import os
import shutil
import argparse

def setup_logging(log_dir: str):
    """Sets up logging to both the console and a file named with the current timestamp."""
    log_filename = datetime.now().strftime("update_libraries_%Y-%m-%d_%H-%M-%S.log")
    log_filepath = os.path.join(log_dir, log_filename)
    
    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Clear existing handlers to avoid duplicate logs
    if logger.hasHandlers():
        logger.handlers.clear()

    # File handler - logs everything with a detailed format
    file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console handler - logs messages cleanly for a better user experience
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    logging.info(f"--- Log started. Output is being saved to {log_filepath} ---")

def cleanup_invalid_distributions():
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
        if os.path.isdir(path):
            for item in os.listdir(path):
                if item.startswith('~') and os.path.isdir(os.path.join(path, item)):
                    logging.warning(f"Found invalid distribution '{item}' in {path}. Removing it.")
                    shutil.rmtree(os.path.join(path, item))
                    cleaned_count += 1
    if cleaned_count == 0:
        logging.info("No invalid distributions found to clean up.")

def update_pip_itself():
    """
    Upgrades pip to its latest version, showing output only if an actual upgrade occurs.
    """
    logging.info("Checking and upgrading pip...")
    try:
        # Command to upgrade pip, capturing output to check for an actual upgrade
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'], check=True, text=True, capture_output=True, encoding='utf-8')
        # Check if the output indicates a new version was installed or uninstalled
        if "Successfully installed" in result.stdout or "Successfully uninstalled" in result.stdout:
            logging.info(result.stdout)
            logging.info("Successfully upgraded pip.")
        else:
            logging.info("Pip is already up to date.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error upgrading pip. The process returned with exit code {e.returncode}.")
        logging.error(f"Pip's error output: {e.stderr}")
        logging.info("Attempting to continue with package updates...")
    except Exception as e:
        logging.error(f"An unexpected error occurred while upgrading pip: {e}")

def update_all_outdated_libraries(exclude_packages: list):
    """
    Checks for all outdated Python libraries and upgrades them, showing live progress.
    This script relies on the 'pip' command being in your system's PATH.
    """
    logging.info("\nScanning for outdated Python libraries...")
    try:
        # Run pip list --outdated and capture the output
        # Use the JSON format for stable, machine-readable output
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'list', '--outdated', '--format', 'json'],
            capture_output=True, text=True, check=True, encoding='utf-8'
        )
        package_names = [pkg['name'] for pkg in json.loads(result.stdout)]
        if not package_names:
            logging.info("No outdated packages found.")
            return

        # Filter out packages from the exclusion list
        if exclude_packages:
            original_count = len(package_names)
            package_names = [pkg for pkg in package_names if pkg not in exclude_packages]
            excluded_count = original_count - len(package_names)
            if excluded_count > 0:
                logging.info(f"Skipping {excluded_count} package(s) based on the exclusion list: {', '.join(exclude_packages)}")

        if not package_names:
            logging.info("All outdated packages are in the exclusion list. Nothing to do.")
            return

        logging.info(f"Found {len(package_names)} outdated package(s). Starting upgrades...")
        packages_to_upgrade = list(package_names) # Keep a copy for the summary

        # Upgrade all packages in a single command for better dependency resolution and speed
        upgrade_command = [sys.executable, '-m', 'pip', 'install', '--upgrade'] + package_names
        # Use Popen to stream output live to the logger
        process = subprocess.Popen(upgrade_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')

        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                logging.info(line.strip())
        
        return_code = process.wait()
        
        # --- Final Summary ---
        logging.info("\n" + "="*50)
        logging.info("UPDATE SUMMARY")
        logging.info("="*50)
        logging.info(f"The script attempted to upgrade the following {len(packages_to_upgrade)} package(s):")
        for pkg in packages_to_upgrade:
            logging.info(f"- {pkg}")

        if return_code == 0:
            logging.info("\nResult: All upgrades completed successfully.")
        else:
            logging.error(f"\nResult: An error occurred. The process finished with exit code {return_code}. Please review the log for details.")

    except FileNotFoundError:
        logging.error("Error: The 'pip' command was not found. Please ensure Python and pip are correctly installed and added to your system's PATH.")
    except subprocess.CalledProcessError as e:
        logging.error(f"An error occurred while running pip: {e.stderr}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")

def main():
    """Main function to parse arguments and run the update process."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    parser = argparse.ArgumentParser(
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
        '--log-dir',
        default=script_dir,
        help=f"Directory to save log files.\n(default: script's directory, {script_dir})"
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
    
    args = parser.parse_args()
    
    # Set up logging first
    setup_logging(log_dir=args.log_dir)

    # Clean up any broken package folders first
    if not args.skip_cleanup:
        cleanup_invalid_distributions()

    # First, update pip itself
    if not args.skip_pip_update:
        update_pip_itself()
    
    # Then, update all other outdated libraries
    update_all_outdated_libraries(exclude_packages=args.exclude)

if __name__ == "__main__":
    main()
