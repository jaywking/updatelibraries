import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import interactive


class InteractiveMenuTests(unittest.TestCase):
    @patch("interactive._select_local_venvs", return_value=[])
    @patch("builtins.input")
    def test_update_plan_requires_explicit_run_confirmation(self, mock_input, _mock_select_local_venvs):
        mock_input.side_effect = [
            "2",  # Update packages now
            "",  # No package exclusions
            "",  # No exclusion file
            "",  # No constraints file
            "",  # Default log directory
            "",  # Default retention
            "",  # Do not skip pip update
            "",  # Run cleanup
            "",  # Do not skip dependencies
            "",  # Do not enable verbose mode
            "r",  # Run update from review screen
        ]

        args = interactive.interactive_menu()

        self.assertFalse(args.cancelled)
        self.assertFalse(args.dry_run)
        self.assertFalse(args.skip_pip_update)
        self.assertFalse(args.skip_cleanup)
        self.assertEqual(args.constraint, [])

    @patch("builtins.input", side_effect=["5"])
    def test_exit_cancels_without_selecting_an_environment(self, _mock_input):
        args = interactive.interactive_menu()

        self.assertTrue(args.cancelled)
        self.assertEqual(args.local_venv_targets, [])

    @patch("interactive._select_local_venvs", return_value=[])
    @patch("builtins.input")
    def test_restore_requires_typed_confirmation_and_returns_snapshot(self, mock_input, _mock_select_local_venvs):
        with tempfile.TemporaryDirectory() as temporary_directory:
            snapshot_dir = Path(temporary_directory) / "environment_snapshots"
            snapshot_dir.mkdir()
            snapshot = snapshot_dir / "pip_freeze_2026-07-14_12-00-00.txt"
            snapshot.write_text("# Python executable: C:\\Python\\python.exe\nrequests==2.32.0\n", encoding="utf-8")
            mock_input.side_effect = ["4", temporary_directory, "1", "RESTORE"]

            args = interactive.interactive_menu()

        self.assertFalse(args.cancelled)
        self.assertEqual(args.restore_snapshot, str(snapshot.resolve()))
