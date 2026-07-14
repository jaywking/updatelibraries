import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import updater


class UpdateAllOutdatedLibrariesTests(unittest.TestCase):
    @patch("updater._run_upgrade_command")
    @patch("updater.preflight_upgrade_plan", return_value=0)
    @patch("updater.run_with_retries")
    def test_skips_pydantic_core_but_upgrades_pydantic_and_other_packages(
        self, mock_run_with_retries, mock_preflight, mock_run_upgrade_command
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
        mock_preflight.assert_called_once_with(
            ["pydantic", "requests"], constraint_files=[], no_deps=False, confirm_plan=None
        )

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

    @patch("updater._run_upgrade_command")
    @patch("updater.preflight_upgrade_plan", return_value=1)
    @patch("updater.run_with_retries")
    def test_failed_preflight_blocks_all_upgrades(
        self, mock_run_with_retries, mock_preflight, mock_run_upgrade_command
    ):
        outdated = [{"name": "pydantic", "version": "2.13.4", "latest_version": "2.14.0"}]
        mock_run_with_retries.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps(outdated), stderr=""
        )

        with self.assertLogs(level="ERROR") as captured_logs:
            return_code = updater.update_all_outdated_libraries(
                exclude_packages=[], constraint_files=["constraints.txt"], verbose=True
            )

        self.assertEqual(return_code, 1)
        mock_preflight.assert_called_once_with(
            ["pydantic"], constraint_files=["constraints.txt"], no_deps=False, confirm_plan=None
        )
        mock_run_upgrade_command.assert_not_called()
        self.assertIn("No package upgrades were attempted because the preflight did not pass.", "\n".join(captured_logs.output))


class SafetyFlowTests(unittest.TestCase):
    @patch("updater.subprocess.run")
    def test_preflight_logs_plan_and_passes_constraints(self, mock_run):
        def write_report(command, **_kwargs):
            report_path = Path(command[command.index("--report") + 1])
            report_path.write_text(json.dumps({"install": [{"metadata": {"name": "pydantic", "version": "2.14.0"}}]}))
            return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

        mock_run.side_effect = write_report

        with self.assertLogs(level="INFO") as captured_logs:
            return_code = updater.preflight_upgrade_plan(["pydantic"], ["constraints.txt"], no_deps=False)

        self.assertEqual(return_code, 0)
        command = mock_run.call_args.args[0]
        self.assertIn("--dry-run", command)
        self.assertEqual(command[command.index("--constraint") + 1], "constraints.txt")
        self.assertIn("- pydantic==2.14.0", "\n".join(captured_logs.output))

    @patch("updater.subprocess.run")
    def test_preflight_can_be_cancelled_after_plan_review(self, mock_run):
        def write_report(command, **_kwargs):
            report_path = Path(command[command.index("--report") + 1])
            report_path.write_text(json.dumps({"install": [{"metadata": {"name": "pydantic", "version": "2.14.0"}}]}))
            return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

        mock_run.side_effect = write_report

        return_code = updater.preflight_upgrade_plan(
            ["pydantic"], [], no_deps=False, confirm_plan=lambda _installations: False
        )

        self.assertEqual(return_code, updater.PREFLIGHT_CANCELLED)

    @patch("updater.subprocess.run")
    def test_snapshot_is_saved_and_pip_check_logs_restore_command(self, mock_run):
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="pydantic==2.13.4\n", stderr=""),
            subprocess.CompletedProcess(args=[], returncode=1, stdout="pydantic has requirement pydantic-core==2.46.4\n", stderr=""),
        ]

        with tempfile.TemporaryDirectory() as temporary_directory:
            snapshot_path = updater.snapshot_environment(Path(temporary_directory))
            self.assertIsNotNone(snapshot_path)
            snapshot_contents = snapshot_path.read_text(encoding="utf-8")
            self.assertIn("# Python executable:", snapshot_contents)
            self.assertTrue(snapshot_contents.endswith("pydantic==2.13.4\n"))

            with self.assertLogs(level="ERROR") as captured_logs:
                return_code = updater.run_pip_check(snapshot_path=snapshot_path)

        self.assertEqual(return_code, 1)
        self.assertIn("--force-reinstall --requirement", "\n".join(captured_logs.output))


if __name__ == "__main__":
    unittest.main()
