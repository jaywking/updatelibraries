import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import interactive
import UpdateLibraries


class InteractiveMenuTests(unittest.TestCase):
    @patch("interactive._ask_yes_no", return_value=True)
    @patch("interactive._find_local_venvs")
    @patch("builtins.input", return_value="1")
    def test_local_venv_picker_lists_names_without_redundant_paths(self, _mock_input, mock_find_venvs, _mock_yes_no):
        python_exe = Path(r"C:\LocalVenvs\Example\Scripts\python.exe")
        mock_find_venvs.return_value = [("Example", python_exe)]
        output = io.StringIO()

        with redirect_stdout(output):
            selected = interactive._select_local_venvs()

        self.assertEqual(selected, [str(python_exe)])
        self.assertIn("1. Example", output.getvalue())
        self.assertNotIn(str(python_exe), output.getvalue())

    @patch("interactive._ask_yes_no", return_value=True)
    @patch("interactive._find_local_venvs")
    @patch("builtins.input", side_effect=["s", "pdf", "2"])
    def test_local_venv_picker_searches_and_keeps_original_selection_numbers(
        self, _mock_input, mock_find_venvs, _mock_yes_no
    ):
        pdf_python = Path(r"C:\LocalVenvs\pdfconvert\Scripts\python.exe")
        mock_find_venvs.return_value = [
            ("ATLSApp", Path(r"C:\LocalVenvs\ATLSApp\Scripts\python.exe")),
            ("pdfconvert", pdf_python),
            ("pdfconvertOCR", Path(r"C:\LocalVenvs\pdfconvertOCR\Scripts\python.exe")),
        ]

        selected = interactive._select_local_venvs()

        self.assertEqual(selected, [str(pdf_python)])

    @patch.object(UpdateLibraries.sys, "argv", ["UpdateLibraries.py"])
    @patch("UpdateLibraries.os.system")
    @patch("UpdateLibraries._wait_for_main_menu")
    @patch("UpdateLibraries._run_action", return_value=0)
    @patch("UpdateLibraries.interactive_menu")
    def test_completed_action_returns_to_main_menu(self, mock_menu, mock_run_action, mock_wait, mock_clear):
        mock_menu.side_effect = [
            SimpleNamespace(cancelled=False),
            SimpleNamespace(cancelled=True),
        ]

        UpdateLibraries.main()

        self.assertEqual(mock_menu.call_count, 2)
        mock_run_action.assert_called_once()
        mock_wait.assert_called_once()
        mock_clear.assert_not_called()

    @patch("UpdateLibraries.os.system")
    @patch("msvcrt.getwch")
    def test_keypress_clears_screen_before_returning_to_menu(self, mock_getwch, mock_system):
        UpdateLibraries._wait_for_main_menu()

        mock_getwch.assert_called_once()
        mock_system.assert_called_once_with("cls")

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
