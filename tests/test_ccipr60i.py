from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cnds_validator.ccipr60i import (
    CCIPR60I_RECORD_LENGTH,
    ComparisonResult,
    ConversionConfig,
    build_binary_record,
    build_ccipr60i_record,
    compare_binary_files,
    debug_dump_records,
    validate_binary_file,
    write_ccipr60i_binary,
)
from cnds_validator.validator import RecordResult


def _sample_record() -> RecordResult:
    fields = {
        "county": "021",
        "case_number": "0001000001",
        "medicaid_id": "123456789A",
        "last_name": "THOMAS                        ",
        "first_name": "JAMES       ",
        "first_name_filler": "            ",
        "sis_number": "      ",
        "middle_initial": " ",
        "suffix": "   ",
        "ssn": "000000000",
        "date_of_birth": "1950-11-28",
        "sex": "M",
        "ethnicity": "N",
        "language": "EN",
        "race_1": "W",
        "race_2": " ",
        "race_3": " ",
        "race_4": " ",
        "race_5": " ",
        "application_person_id": "000000000000001",
    }
    return RecordResult(
        source_path=Path("sample.txt"),
        line_number=1,
        raw_record=" " * 130,
        fields=fields,
        issues=(),
    )


class Ccipr60iTests(unittest.TestCase):
    def test_logical_record_is_exactly_1000_characters(self) -> None:
        record = build_ccipr60i_record(_sample_record(), ConversionConfig(last_changed_user_id="TS54P06"))
        self.assertEqual(CCIPR60I_RECORD_LENGTH, len(record))
        self.assertEqual("0101DHRCCI", record[:10])
        self.assertEqual("0001", record[247:251])

    def test_binary_record_is_exactly_1000_bytes_without_crlf(self) -> None:
        record_bytes = build_binary_record(_sample_record(), ConversionConfig(last_changed_user_id="TS54P06"))
        self.assertEqual(CCIPR60I_RECORD_LENGTH, len(record_bytes))
        self.assertNotIn(b"\r", record_bytes)
        self.assertNotIn(b"\n", record_bytes)
        self.assertNotIn(b"\t", record_bytes)

    def test_binary_writer_creates_fixed_block_file(self) -> None:
        logical_records = [
            build_ccipr60i_record(_sample_record(), ConversionConfig(last_changed_user_id="TS54P06"))
            for _ in range(2)
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "ccipr60i_upload.bin"
            write_ccipr60i_binary(target, logical_records)
            validate_binary_file(target)
            self.assertEqual(CCIPR60I_RECORD_LENGTH * 2, target.stat().st_size)

    def test_compare_binary_files_reports_first_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            expected = Path(temp_dir) / "expected.bin"
            actual = Path(temp_dir) / "actual.bin"
            expected.write_bytes(b"A" * CCIPR60I_RECORD_LENGTH)
            actual.write_bytes(b"B" + (b"A" * (CCIPR60I_RECORD_LENGTH - 1)))
            result = compare_binary_files(expected, actual)
            self.assertFalse(result.matches)
            self.assertEqual(0, result.first_mismatch_offset)
            self.assertIsNotNone(result.field_name)

    def test_debug_dump_contains_record_metadata(self) -> None:
        dump_text = debug_dump_records([_sample_record()], ConversionConfig(last_changed_user_id="TS54P06"))
        self.assertIn("Record 1", dump_text)
        self.assertIn("Byte offset: 0", dump_text)
        self.assertIn("last_name", dump_text)


if __name__ == "__main__":
    unittest.main()
