from __future__ import annotations

import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from cnds_validator.gui import ValidatorApp
from cnds_validator.profiles import DEFAULT_PROFILE
from cnds_validator.validator import InvalidRecordLengthError, validate_files


@contextmanager
def temp_input_file(*lengths: int):
    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "sample.txt"
        lines = ["X" * length for length in lengths]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        yield path


class RecordLengthValidationTests(unittest.TestCase):
    def test_rejects_file_when_record_is_too_short(self) -> None:
        with temp_input_file(130, 127) as path:
            with self.assertRaises(InvalidRecordLengthError) as exc_info:
                validate_files([path], DEFAULT_PROFILE)

        self.assertEqual(127, exc_info.exception.actual_length)
        self.assertEqual(130, exc_info.exception.expected_length)
        self.assertIn("File rejected", str(exc_info.exception))

    def test_rejects_file_when_record_is_too_long(self) -> None:
        with temp_input_file(133) as path:
            with self.assertRaises(InvalidRecordLengthError) as exc_info:
                validate_files([path], DEFAULT_PROFILE)

        self.assertEqual(133, exc_info.exception.actual_length)
        self.assertEqual(130, exc_info.exception.expected_length)

    def test_gui_shows_file_rejected_popup_for_invalid_record_length(self) -> None:
        with temp_input_file(130, 133) as path:
            app = ValidatorApp.__new__(ValidatorApp)
            app.selected_paths = [path]
            app.profile = DEFAULT_PROFILE
            app.selected_ignored_fields = set()
            app.selected_duplicate_mode = "name_dob"
            app.result = object()
            app.record_index = {"existing": object()}
            app.file_var = type("FileVar", (), {"value": "sample.txt", "set": lambda self, value: setattr(self, "value", value)})()
            app.status_var = type("StatusVar", (), {"value": "", "set": lambda self, value: setattr(self, "value", value)})()
            app.update_action_states = lambda: None
            app.records_tree = type(
                "TreeStub",
                (),
                {
                    "__init__": lambda self: setattr(self, "children", ["one"]),
                    "get_children": lambda self: tuple(self.children),
                    "delete": lambda self, item: self.children.remove(item),
                },
            )()
            app.preview_tree = type(
                "TreeStub",
                (),
                {
                    "__init__": lambda self: setattr(self, "children", ["one"]),
                    "get_children": lambda self: tuple(self.children),
                    "delete": lambda self, item: self.children.remove(item),
                },
            )()
            app.defects_tree = type(
                "TreeStub",
                (),
                {
                    "__init__": lambda self: setattr(self, "children", ["one"]),
                    "get_children": lambda self: tuple(self.children),
                    "delete": lambda self, item: self.children.remove(item),
                },
            )()

            with patch("cnds_validator.gui.messagebox.showerror") as showerror:
                app.validate_selected_files()

        self.assertIsNone(app.result)
        self.assertEqual([], app.selected_paths)
        self.assertEqual({}, app.record_index)
        self.assertEqual("", app.file_var.value)
        self.assertEqual((), app.records_tree.get_children())
        self.assertEqual((), app.preview_tree.get_children())
        self.assertEqual((), app.defects_tree.get_children())
        self.assertEqual("Select one or more CNDS fixed-width files to validate.", app.status_var.value)
        showerror.assert_called_once()
        title, message = showerror.call_args.args
        self.assertEqual("File Rejected", title)
        self.assertIn("A record length of 130 is required.", message)


if __name__ == "__main__":
    unittest.main()
