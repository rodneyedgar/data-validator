from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cnds_validator.ccipr10h import (
    CCIPR10H_RECORD_LENGTH,
    ConversionConfig,
    build_binary_record,
    build_ccipr10h_record,
    validate_ccipr10h_binary_file,
    write_ccipr10h_text,
    write_ccipr10h_binary,
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


class Ccipr10hTests(unittest.TestCase):
    def test_logical_record_is_exactly_1000_characters(self) -> None:
        record = build_ccipr10h_record(
            _sample_record(),
            ConversionConfig(
                testing_comment="CCIUPDATE",
                last_changed_program_id="CCIBTH10",
                last_changed_user_id="TS54P06",
            ),
        )
        self.assertEqual(CCIPR10H_RECORD_LENGTH, len(record))
        self.assertEqual("0101DHRCCI", record[:10])
        self.assertEqual(" ", record[120])
        self.assertEqual("123456789", record[121:130])
        self.assertEqual(" ", record[130])
        self.assertEqual("A", record[131])
        self.assertEqual(" ", record[132])
        self.assertEqual("THOMAS".ljust(40), record[133:173])
        self.assertEqual("JAMES".ljust(12), record[174:186])
        self.assertEqual("000000000", record[193:202])
        self.assertEqual("19501128", record[203:211])
        self.assertEqual("M", record[212])
        self.assertEqual("N", record[214])
        self.assertEqual("EN", record[216:218])
        self.assertEqual("CCIBTH10", record[219:227])
        self.assertEqual("TS54P06 ".ljust(8), record[228:236])
        self.assertEqual("0001", record[236:240])
        self.assertEqual("  W", record[240:243])

    def test_binary_record_is_exactly_1000_bytes_without_crlf(self) -> None:
        record_bytes = build_binary_record(
            _sample_record(),
            ConversionConfig(
                testing_comment="CCIUPDATE",
                last_changed_program_id="CCIBTH10",
                last_changed_user_id="TS54P06",
            ),
        )
        self.assertEqual(CCIPR10H_RECORD_LENGTH, len(record_bytes))
        self.assertNotIn(b"\r", record_bytes)
        self.assertNotIn(b"\n", record_bytes)
        self.assertNotIn(b"\t", record_bytes)

    def test_binary_writer_creates_fixed_block_file(self) -> None:
        logical_records = [
            build_ccipr10h_record(
                _sample_record(),
                ConversionConfig(
                    testing_comment="CCIUPDATE",
                    last_changed_program_id="CCIBTH10",
                    last_changed_user_id="TS54P06",
                ),
            )
            for _ in range(2)
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "ccipr10h_upload.bin"
            write_ccipr10h_binary(target, logical_records)
            validate_ccipr10h_binary_file(target)
            self.assertEqual(CCIPR10H_RECORD_LENGTH * 2, target.stat().st_size)

    def test_text_writer_matches_ccipr60i_preview_style(self) -> None:
        logical_record = build_ccipr10h_record(
            _sample_record(),
            ConversionConfig(
                testing_comment="CCIUPDATE",
                last_changed_program_id="CCIBTH10",
                last_changed_user_id="TS54P06",
            ),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "ccipr10h_preview.txt"
            write_ccipr10h_text(target, [logical_record])
            written = target.read_text(encoding="utf-8").splitlines()[0]
            self.assertEqual(logical_record.rstrip(), written)


if __name__ == "__main__":
    unittest.main()
