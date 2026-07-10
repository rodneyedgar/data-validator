from __future__ import annotations

import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from cnds_validator.gui import ValidatorApp
from cnds_validator.profiles import DEFAULT_PROFILE, validate_name_field
from cnds_validator.validator import InvalidRecordLengthError, ValidationIssue, RecordResult, validate_files


@contextmanager
def temp_input_file(*lengths: int):
    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "sample.txt"
        lines = ["X" * length for length in lengths]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        yield path


class RecordLengthValidationTests(unittest.TestCase):
    @staticmethod
    def _blank_fields() -> dict[str, str]:
        return {field.name: " " * field.length for field in DEFAULT_PROFILE.fields}

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

    def test_duplicate_and_invalid_record_is_marked_as_both(self) -> None:
        record = RecordResult(
            source_path=Path("sample.txt"),
            line_number=1,
            raw_record=" " * DEFAULT_PROFILE.record_length,
            fields={field.name: " " * field.length for field in DEFAULT_PROFILE.fields},
            issues=(
                ValidationIssue(
                    source_path=Path("sample.txt"),
                    line_number=1,
                    field_name="application_person_id",
                    field_label="Application Person ID",
                    code="INVALID_VALUE",
                    message="must contain only letters and digits",
                    start=116,
                    end=130,
                    value="11111111111111@",
                ),
                ValidationIssue(
                    source_path=Path("sample.txt"),
                    line_number=1,
                    field_name="person_identity",
                    field_label="Last/First/DOB",
                    code="DUPLICATE_MATCH_KEY",
                    message="duplicate group records sample:1, sample:2",
                    start=24,
                    end=106,
                    value="A | B | C",
                ),
            ),
            duplicate_group_size_value=2,
        )

        self.assertTrue(record.is_duplicate)
        self.assertTrue(record.is_invalid)
        self.assertTrue(record.has_validation_issues)
        self.assertFalse(record.is_invalid_non_duplicate)
        self.assertEqual("Duplicate + Invalid", record.status_label)

    def test_name_fields_allow_internal_space_and_hyphen(self) -> None:
        self.assertEqual([], validate_name_field("ANNE MARIE".ljust(12)))
        self.assertEqual([], validate_name_field("SMITH-JONES".ljust(30)))

    def test_name_fields_reject_leading_space_or_hyphen(self) -> None:
        self.assertIn("cannot start with a space or hyphen", validate_name_field(" SMITH".ljust(30)))
        self.assertIn("cannot start with a space or hyphen", validate_name_field("-SMITH".ljust(30)))

    def test_name_fields_reject_other_symbols(self) -> None:
        self.assertIn(
            "must contain only alphabetic characters A-Z, spaces, or hyphens",
            validate_name_field("SMITH@".ljust(30)),
        )

    def test_export_buckets_split_duplicate_invalid_records(self) -> None:
        valid_record = RecordResult(
            source_path=Path("sample.txt"),
            line_number=1,
            raw_record="V" * DEFAULT_PROFILE.record_length,
            fields=self._blank_fields(),
            issues=(),
        )
        invalid_record = RecordResult(
            source_path=Path("sample.txt"),
            line_number=2,
            raw_record="I" * DEFAULT_PROFILE.record_length,
            fields=self._blank_fields(),
            issues=(
                ValidationIssue(
                    source_path=Path("sample.txt"),
                    line_number=2,
                    field_name="application_person_id",
                    field_label="Application Person ID",
                    code="INVALID_VALUE",
                    message="must contain only letters and digits",
                    start=116,
                    end=130,
                    value="BADVALUE@@@@@@@",
                ),
            ),
        )
        duplicate_record = RecordResult(
            source_path=Path("sample.txt"),
            line_number=3,
            raw_record="D" * DEFAULT_PROFILE.record_length,
            fields=self._blank_fields(),
            issues=(
                ValidationIssue(
                    source_path=Path("sample.txt"),
                    line_number=3,
                    field_name="person_identity",
                    field_label="Last/First/DOB",
                    code="DUPLICATE_MATCH_KEY",
                    message="duplicate group records sample:3, sample:4",
                    start=24,
                    end=106,
                    value="A | B | C",
                ),
            ),
            duplicate_group_size_value=2,
        )
        duplicate_invalid_record = RecordResult(
            source_path=Path("sample.txt"),
            line_number=4,
            raw_record="X" * DEFAULT_PROFILE.record_length,
            fields=self._blank_fields(),
            issues=(
                ValidationIssue(
                    source_path=Path("sample.txt"),
                    line_number=4,
                    field_name="application_person_id",
                    field_label="Application Person ID",
                    code="INVALID_VALUE",
                    message="must contain only letters and digits",
                    start=116,
                    end=130,
                    value="11111111111111@",
                ),
                ValidationIssue(
                    source_path=Path("sample.txt"),
                    line_number=4,
                    field_name="person_identity",
                    field_label="Last/First/DOB",
                    code="DUPLICATE_MATCH_KEY",
                    message="duplicate group records sample:4, sample:5",
                    start=24,
                    end=106,
                    value="A | B | C",
                ),
            ),
            duplicate_group_size_value=2,
        )

        app = ValidatorApp.__new__(ValidatorApp)
        app.result = type("Result", (), {"records": (valid_record, invalid_record, duplicate_record, duplicate_invalid_record)})()
        app._review_records = lambda config=None: (valid_record, invalid_record, duplicate_record, duplicate_invalid_record)
        app._sort_key = lambda record: record.line_number

        valid_records, invalid_records, duplicate_records, duplicate_invalid_records = app._build_export_buckets()

        self.assertEqual([valid_record.raw_record], valid_records)
        self.assertEqual([invalid_record.raw_record], invalid_records)
        self.assertEqual([duplicate_record.raw_record], duplicate_records)
        self.assertEqual([duplicate_invalid_record.raw_record], duplicate_invalid_records)


if __name__ == "__main__":
    unittest.main()
