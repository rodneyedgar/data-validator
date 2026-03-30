from __future__ import annotations

import unittest
from pathlib import Path

from cnds_validator.ccipr60i import CONVERSION_SCOPE_VALID_AND_CORRECTED, ConversionConfig
from cnds_validator.gui import ValidatorApp
from cnds_validator.overrides import OverrideConfig
from cnds_validator.profiles import DEFAULT_PROFILE
from cnds_validator.validator import validate_files


class ConversionScopeRegressionTests(unittest.TestCase):
    def test_valid_and_corrected_scope_uses_same_reviewed_records_for_both_conversions(self) -> None:
        input_path = Path("docs/CNDS/oas/EDITS/APSR.edit.txt")
        result = validate_files([input_path], DEFAULT_PROFILE, ignored_fields={"medicaid_id"})

        app = ValidatorApp.__new__(ValidatorApp)
        app.profile = DEFAULT_PROFILE
        app.result = result
        app.selected_ignored_fields = {"medicaid_id"}
        app.override_config = OverrideConfig(
            target_scope="both",
            normalize_application_person_id=True,
            uppercase_all_data=True,
            cleanup_name_spaces=True,
            cleanup_name_hyphens=True,
            cleanup_name_apostrophes=True,
            field_values={
                "race_1": "U",
                "race_2": "",
                "race_3": "",
                "race_4": "",
                "race_5": "",
            },
        )
        app.conversion_config = ConversionConfig(
            scope=CONVERSION_SCOPE_VALID_AND_CORRECTED,
            last_changed_user_id="TS54P06",
        )
        app.conversion_10h_config = ConversionConfig(
            scope=CONVERSION_SCOPE_VALID_AND_CORRECTED,
            testing_comment="CCIUPDATE",
            last_changed_program_id="CCIBTH10",
            last_changed_user_id="",
        )

        ccipr60i_records = app._conversion_source_records(app.conversion_config, app.override_config)
        ccipr10h_records = app._conversion_source_records(app.conversion_10h_config, app.override_config)

        self.assertEqual(12, len(ccipr60i_records))
        self.assertEqual(12, len(ccipr10h_records))
        self.assertEqual(
            [(record.source_name, record.line_number) for record in ccipr60i_records],
            [(record.source_name, record.line_number) for record in ccipr10h_records],
        )


if __name__ == "__main__":
    unittest.main()
