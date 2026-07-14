import json
import subprocess
import unittest
from unittest.mock import patch

import updater


class UpdateAllOutdatedLibrariesTests(unittest.TestCase):
    @patch("updater._run_upgrade_command")
    @patch("updater.run_with_retries")
    def test_skips_pydantic_core_but_upgrades_pydantic_and_other_packages(
        self, mock_run_with_retries, mock_run_upgrade_command
    ):
        outdated = [
            {"name": "pydantic_core", "version": "2.46.4", "latest_version": "2.47.0"},
            {"name": "pydantic", "version": "2.13.4", "latest_version": "2.14.0"},
            {"name": "requests", "version": "2.31.0", "latest_version": "2.32.0"},
        ]
        mock_run_with_retries.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps(outdated), stderr=""
        )
        mock_run_upgrade_command.return_value = (0, [])

        with self.assertLogs(level="INFO") as captured_logs:
            return_code = updater.update_all_outdated_libraries(exclude_packages=[], verbose=True)

        self.assertEqual(return_code, 0)
        upgraded_packages = mock_run_upgrade_command.call_args.args[0]
        self.assertEqual(upgraded_packages, ["pydantic", "requests"])

        log_output = "\n".join(captured_logs.output)
        self.assertIn(
            "Skipping pydantic_core: it is dependency-managed by pydantic and must not be upgraded independently.",
            log_output,
        )
        self.assertIn("Found 2 outdated package(s). Starting upgrades...", log_output)
        self.assertIn("Upgrade process attempted for the following 2 package(s):", log_output)
        self.assertNotIn("- pydantic_core:", log_output)

    @patch("updater.run_with_retries")
    def test_dry_run_omits_dependency_managed_package(self, mock_run_with_retries):
        outdated = [
            {"name": "pydantic-core", "version": "2.46.4", "latest_version": "2.47.0"},
        ]
        mock_run_with_retries.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps(outdated), stderr=""
        )

        with self.assertLogs(level="INFO") as captured_logs:
            return_code = updater.update_all_outdated_libraries(exclude_packages=[], dry_run=True, verbose=True)

        self.assertEqual(return_code, 0)
        log_output = "\n".join(captured_logs.output)
        self.assertIn("Skipping pydantic-core: it is dependency-managed by pydantic", log_output)
        self.assertIn("All outdated packages were skipped. Nothing to do.", log_output)
        self.assertNotIn("- pydantic-core (2.46.4 -> 2.47.0)", log_output)


if __name__ == "__main__":
    unittest.main()
