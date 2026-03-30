from __future__ import annotations

from dataclasses import dataclass, field

from .profiles import FileProfile
from .validator import RecordResult

OVERRIDE_SCOPE_VALID = "valid"
OVERRIDE_SCOPE_INVALID = "invalid"
OVERRIDE_SCOPE_BOTH = "both"
OVERRIDE_SCOPE_LABELS = {
    "Valid records": OVERRIDE_SCOPE_VALID,
    "Invalid records": OVERRIDE_SCOPE_INVALID,
    "Valid + Invalid records": OVERRIDE_SCOPE_BOTH,
}
OVERRIDE_SCOPE_REVERSE = {value: key for key, value in OVERRIDE_SCOPE_LABELS.items()}
OVERRIDE_EXPORT_SPLIT_ONLY = "split_only"
OVERRIDE_EXPORT_FULL_ONLY = "full_only"
OVERRIDE_EXPORT_FULL_AND_SPLIT = "full_and_split"
OVERRIDE_EXPORT_MODE_LABELS = {
    "Split files only": OVERRIDE_EXPORT_SPLIT_ONLY,
    "Corrected full file only": OVERRIDE_EXPORT_FULL_ONLY,
    "Corrected full file + split files": OVERRIDE_EXPORT_FULL_AND_SPLIT,
}
OVERRIDE_EXPORT_MODE_REVERSE = {value: key for key, value in OVERRIDE_EXPORT_MODE_LABELS.items()}
OVERRIDE_FIELD_NAMES = (
    "ssn",
    "ethnicity",
    "language",
    "race_1",
    "race_2",
    "race_3",
    "race_4",
    "race_5",
)
RACE_OVERRIDE_FIELD_NAMES = {"race_1", "race_2", "race_3", "race_4", "race_5"}


@dataclass(frozen=True)
class OverrideConfig:
    target_scope: str = OVERRIDE_SCOPE_BOTH
    export_mode: str = OVERRIDE_EXPORT_FULL_AND_SPLIT
    field_values: dict[str, str] = field(default_factory=dict)
    normalize_application_person_id: bool = False
    cleanup_name_spaces: bool = False
    cleanup_name_hyphens: bool = False
    cleanup_name_apostrophes: bool = False

    @property
    def has_overrides(self) -> bool:
        return (
            bool(self.field_values)
            or self.normalize_application_person_id
            or self.cleanup_name_spaces
            or self.cleanup_name_hyphens
            or self.cleanup_name_apostrophes
        )


def should_apply_overrides(record: RecordResult, config: OverrideConfig) -> bool:
    if not config.has_overrides or record.is_duplicate:
        return False
    if config.target_scope == OVERRIDE_SCOPE_VALID:
        return record.is_valid
    if config.target_scope == OVERRIDE_SCOPE_INVALID:
        return record.is_invalid_non_duplicate
    return not record.is_duplicate


def _fixed_width(value: str, length: int) -> str:
    return value[:length].ljust(length)


def serialize_fields(fields: dict[str, str], profile: FileProfile) -> str:
    raw_record = [" "] * profile.record_length
    for field in profile.fields:
        value = _fixed_width(fields.get(field.name, ""), field.length)
        start = field.start - 1
        raw_record[start:field.end] = list(value)
    return "".join(raw_record)


def _record_has_race_issue(record: RecordResult | None) -> bool:
    if record is None:
        return True
    return any(issue.field_name == "race_group" or issue.field_name.startswith("race_") for issue in record.issues)


def apply_overrides_to_fields(fields: dict[str, str], profile: FileProfile, config: OverrideConfig, record: RecordResult | None = None) -> dict[str, str]:
    updated_fields = dict(fields)
    field_specs = {field.name: field for field in profile.fields}
    apply_race_overrides = _record_has_race_issue(record)

    for field_name, replacement_value in config.field_values.items():
        if field_name in RACE_OVERRIDE_FIELD_NAMES and not apply_race_overrides:
            continue
        field = field_specs[field_name]
        updated_fields[field_name] = _fixed_width(replacement_value, field.length)

    if config.normalize_application_person_id:
        field = field_specs["application_person_id"]
        current_value = updated_fields["application_person_id"].strip()
        if not current_value:
            normalized_value = "0" * field.length
        elif current_value.isdigit() and len(current_value) <= field.length:
            normalized_value = current_value.zfill(field.length)
        else:
            normalized_value = current_value
        updated_fields["application_person_id"] = _fixed_width(normalized_value, field.length)

    remove_characters = ""
    if config.cleanup_name_spaces:
        remove_characters += " "
    if config.cleanup_name_hyphens:
        remove_characters += "-"
    if config.cleanup_name_apostrophes:
        remove_characters += "'"

    if remove_characters:
        remove_chars = str.maketrans("", "", remove_characters)
        for field_name in ("last_name", "first_name", "first_name_filler"):
            field = field_specs[field_name]
            cleaned_value = updated_fields[field_name].translate(remove_chars).strip()
            updated_fields[field_name] = _fixed_width(cleaned_value, field.length)

    return updated_fields


