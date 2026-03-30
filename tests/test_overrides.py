from __future__ import annotations

import unittest
from pathlib import Path

from cnds_validator.overrides import OverrideConfig, apply_overrides_to_fields
from cnds_validator.profiles import DEFAULT_PROFILE
from cnds_validator.validator import RecordResult


def _sample_fields() -> dict[str, str]:
    field_lengths = {field.name: field.length for field in DEFAULT_PROFILE.fields}
    fields = {field.name: " " * field.length for field in DEFAULT_PROFILE.fields}
    fields.update(
        {
            "county": "021",
            "case_number": "0001000001",
            "medicaid_id": "123456789a".ljust(field_lengths["medicaid_id"]),
            "last_name": "ashby-miller-haas".ljust(field_lengths["last_name"]),
            "first_name": "ise".ljust(field_lengths["first_name"]),
            "first_name_filler": "ann".ljust(field_lengths["first_name_filler"]),
            "middle_initial": "q",
            "suffix": "jr ".ljust(field_lengths["suffix"]),
            "ssn": "abc123xyz".ljust(field_lengths["ssn"]),
            "date_of_birth": "19991231",
            "sex": "m",
            "ethnicity": "n",
            "language": "en",
            "race_1": "w",
            "application_person_id": "abc000000000001",
        }
    )
    return fields


def _sample_record(fields: dict[str, str]) -> RecordResult:
    return RecordResult(
        source_path=Path("sample.txt"),
        line_number=1,
        raw_record=" " * DEFAULT_PROFILE.record_length,
        fields=fields,
        issues=(),
    )


class OverrideTests(unittest.TestCase):
    def test_uppercase_override_converts_all_field_data(self) -> None:
        fields = _sample_fields()
        field_lengths = {field.name: field.length for field in DEFAULT_PROFILE.fields}
        updated = apply_overrides_to_fields(
            fields,
            DEFAULT_PROFILE,
            OverrideConfig(uppercase_all_data=True),
            record=_sample_record(fields),
        )

        self.assertEqual("ASHBY-MILLER-HAAS".ljust(field_lengths["last_name"]), updated["last_name"])
        self.assertEqual("ISE".ljust(field_lengths["first_name"]), updated["first_name"])
        self.assertEqual("ANN".ljust(field_lengths["first_name_filler"]), updated["first_name_filler"])
        self.assertEqual("Q", updated["middle_initial"].strip())
        self.assertEqual("JR", updated["suffix"].strip())
        self.assertEqual("ABC123XYZ", updated["ssn"])
        self.assertEqual("M", updated["sex"].strip())
        self.assertEqual("N", updated["ethnicity"].strip())
        self.assertEqual("EN", updated["language"].strip())
        self.assertEqual("W", updated["race_1"].strip())
        self.assertEqual("123456789A", updated["medicaid_id"].strip())
        self.assertEqual("ABC000000000001", updated["application_person_id"].strip())

    def test_apostrophe_cleanup_works_without_hyphen_cleanup(self) -> None:
        fields = _sample_fields()
        field_lengths = {field.name: field.length for field in DEFAULT_PROFILE.fields}
        fields["last_name"] = "o'brien".ljust(field_lengths["last_name"])
        fields["first_name"] = "d'arcy".ljust(field_lengths["first_name"])
        fields["first_name_filler"] = "l'".ljust(field_lengths["first_name_filler"])

        updated = apply_overrides_to_fields(
            fields,
            DEFAULT_PROFILE,
            OverrideConfig(cleanup_name_apostrophes=True),
            record=_sample_record(fields),
        )

        self.assertEqual("obrien".ljust(field_lengths["last_name"]), updated["last_name"])
        self.assertEqual("darcy".ljust(field_lengths["first_name"]), updated["first_name"])
        self.assertEqual("l".ljust(field_lengths["first_name_filler"]), updated["first_name_filler"])


if __name__ == "__main__":
    unittest.main()
