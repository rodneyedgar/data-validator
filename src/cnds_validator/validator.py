from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from .profiles import FieldSpec, FileProfile

DUPLICATE_NAME_DOB = "name_dob"
DUPLICATE_NAME_DOB_SEX = "name_dob_sex"
DUPLICATE_CODES = {"DUPLICATE_MATCH_KEY"}


@dataclass(frozen=True)
class ValidationIssue:
    source_path: Path
    line_number: int
    field_name: str
    field_label: str
    code: str
    message: str
    start: int
    end: int
    value: str


@dataclass(frozen=True)
class RecordResult:
    source_path: Path
    line_number: int
    raw_record: str
    fields: dict[str, str]
    issues: tuple[ValidationIssue, ...]
    duplicate_group_size_value: int = 0

    @property
    def source_name(self) -> str:
        return self.source_path.stem

    @property
    def duplicate_issues(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.code in DUPLICATE_CODES)

    @property
    def non_duplicate_issues(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.code not in DUPLICATE_CODES)

    @property
    def is_duplicate(self) -> bool:
        return bool(self.duplicate_issues)

    @property
    def duplicate_group_size(self) -> int:
        return self.duplicate_group_size_value if self.is_duplicate else 0

    @property
    def is_valid(self) -> bool:
        return not self.issues

    @property
    def is_invalid_non_duplicate(self) -> bool:
        return (not self.is_duplicate) and bool(self.non_duplicate_issues)

    @property
    def status_label(self) -> str:
        if self.is_valid:
            return "Valid"
        if self.is_duplicate:
            return "Duplicate"
        return "Invalid"


@dataclass(frozen=True)
class FileValidationResult:
    source_paths: tuple[Path, ...]
    profile: FileProfile
    records: tuple[RecordResult, ...]
    duplicate_mode: str

    @property
    def total_files(self) -> int:
        return len(self.source_paths)

    @property
    def total_records(self) -> int:
        return len(self.records)

    @property
    def valid_records(self) -> tuple[RecordResult, ...]:
        return tuple(record for record in self.records if record.is_valid)

    @property
    def duplicate_records(self) -> tuple[RecordResult, ...]:
        return tuple(record for record in self.records if record.is_duplicate)

    @property
    def invalid_records(self) -> tuple[RecordResult, ...]:
        return tuple(record for record in self.records if not record.is_valid)

    @property
    def invalid_non_duplicate_records(self) -> tuple[RecordResult, ...]:
        return tuple(record for record in self.records if record.is_invalid_non_duplicate)

    @property
    def total_issues(self) -> int:
        return sum(len(record.issues) for record in self.records)

    @property
    def duplicate_percentage(self) -> float:
        if not self.total_records:
            return 0.0
        return (len(self.duplicate_records) / self.total_records) * 100.0


def build_duplicate_key(fields: dict[str, str], duplicate_mode: str) -> tuple[str, ...] | None:
    last_name = fields["last_name"].strip()
    first_name = fields["first_name"].strip()
    dob = fields["date_of_birth"].strip()
    sex = fields["sex"].strip()

    if duplicate_mode == DUPLICATE_NAME_DOB_SEX:
        if all((last_name, first_name, dob, sex)):
            return (last_name, first_name, dob, sex)
        return None

    if all((last_name, first_name, dob)):
        return (last_name, first_name, dob)
    return None


def duplicate_mode_label(duplicate_mode: str) -> str:
    if duplicate_mode == DUPLICATE_NAME_DOB_SEX:
        return "Last/First/DOB/Sex"
    return "Last/First/DOB"


def _slice_field(raw_record: str, field: FieldSpec) -> str:
    return raw_record[field.start - 1 : field.end]


def _build_issue(*, source_path: Path, line_number: int, field_name: str, field_label: str, code: str, message: str, start: int, end: int, value: str) -> ValidationIssue:
    return ValidationIssue(source_path=source_path, line_number=line_number, field_name=field_name, field_label=field_label, code=code, message=message, start=start, end=end, value=value)


def _field_issues(source_path: Path, line_number: int, raw_record: str, field: FieldSpec, ignored_fields: set[str]) -> list[ValidationIssue]:
    value = _slice_field(raw_record, field)
    trimmed = value.strip()
    issues: list[ValidationIssue] = []

    if field.name in ignored_fields:
        return issues

    if field.required and not trimmed:
        issues.append(_build_issue(source_path=source_path, line_number=line_number, field_name=field.name, field_label=field.label, code="REQUIRED", message="required field is blank", start=field.start, end=field.end, value=value))
        return issues

    for validator in field.validators:
        for message in validator(value):
            issues.append(_build_issue(source_path=source_path, line_number=line_number, field_name=field.name, field_label=field.label, code="INVALID_VALUE", message=message, start=field.start, end=field.end, value=value))

    return issues


def _record_level_issues(source_path: Path, line_number: int, fields: dict[str, str]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    race_names = ["race_1", "race_2", "race_3", "race_4", "race_5"]
    race_values = [fields[name].strip() for name in race_names if fields[name].strip()]
    if race_values:
        if len(set(race_values)) != len(race_values):
            issues.append(_build_issue(source_path=source_path, line_number=line_number, field_name="race_group", field_label="Race Codes", code="DUPLICATE_RACE", message="race codes must be unique", start=111, end=115, value="".join(fields[name] for name in race_names)))
        if "U" in race_values and len(race_values) > 1:
            issues.append(_build_issue(source_path=source_path, line_number=line_number, field_name="race_group", field_label="Race Codes", code="INVALID_RACE_COMBINATION", message="race U cannot appear with any other race code", start=111, end=115, value="".join(fields[name] for name in race_names)))
    else:
        issues.append(_build_issue(source_path=source_path, line_number=line_number, field_name="race_group", field_label="Race Codes", code="MISSING_RACE", message="at least one race code should be provided; use U if unknown", start=111, end=115, value="".join(fields[name] for name in race_names)))
    return issues


def validate_record(source_path: Path, line_number: int, raw_record: str, profile: FileProfile, ignored_fields: set[str] | None = None) -> RecordResult:
    ignored_fields = ignored_fields or set()
    issues: list[ValidationIssue] = []
    fields: dict[str, str] = {}

    if len(raw_record) != profile.record_length:
        issues.append(_build_issue(source_path=source_path, line_number=line_number, field_name="record", field_label="Record", code="INVALID_LENGTH", message=f"record length is {len(raw_record)} but expected {profile.record_length}", start=1, end=max(len(raw_record), 1), value=raw_record))

    padded_record = raw_record if len(raw_record) >= profile.record_length else raw_record.ljust(profile.record_length)
    for field in profile.fields:
        fields[field.name] = _slice_field(padded_record, field)
        issues.extend(_field_issues(source_path, line_number, padded_record, field, ignored_fields))

    issues.extend(_record_level_issues(source_path, line_number, fields))
    return RecordResult(source_path=source_path, line_number=line_number, raw_record=raw_record, fields=fields, issues=tuple(issues))


def _append_duplicate_issues(records: list[RecordResult], groups: dict[tuple[str, ...], list[int]], duplicate_mode: str) -> list[RecordResult]:
    updated = list(records)
    field_label = duplicate_mode_label(duplicate_mode)
    end = 107 if duplicate_mode == DUPLICATE_NAME_DOB_SEX else 106
    for indexes in groups.values():
        if len(indexes) < 2:
            continue
        members_text = ", ".join(f"{records[index].source_name}:{records[index].line_number}" for index in indexes)
        for index in indexes:
            record = updated[index]
            key = build_duplicate_key(record.fields, duplicate_mode)
            issue_list = list(record.issues)
            issue_list.append(
                _build_issue(
                    source_path=record.source_path,
                    line_number=record.line_number,
                    field_name="person_identity",
                    field_label=field_label,
                    code="DUPLICATE_MATCH_KEY",
                    message=f"duplicate group records {members_text}",
                    start=24,
                    end=end,
                    value=" | ".join(key or ()),
                )
            )
            updated[index] = replace(record, issues=tuple(issue_list), duplicate_group_size_value=len(indexes))
    return updated


def validate_files(paths: list[Path], profile: FileProfile, ignored_fields: set[str] | None = None, duplicate_mode: str = DUPLICATE_NAME_DOB) -> FileValidationResult:
    ignored_fields = ignored_fields or set()
    records: list[RecordResult] = []

    for path in paths:
        text = path.read_text(encoding="utf-8-sig")
        normalized = text.splitlines()
        for line_number, raw_record in enumerate(normalized, start=1):
            records.append(validate_record(path, line_number, raw_record, profile, ignored_fields))

    duplicate_groups: dict[tuple[str, ...], list[int]] = {}
    for index, record in enumerate(records):
        key = build_duplicate_key(record.fields, duplicate_mode)
        if key is not None:
            duplicate_groups.setdefault(key, []).append(index)

    records = _append_duplicate_issues(records, duplicate_groups, duplicate_mode)
    return FileValidationResult(source_paths=tuple(paths), profile=profile, records=tuple(records), duplicate_mode=duplicate_mode)


def validate_file(path: Path, profile: FileProfile, ignored_fields: set[str] | None = None, duplicate_mode: str = DUPLICATE_NAME_DOB) -> FileValidationResult:
    return validate_files([path], profile, ignored_fields=ignored_fields, duplicate_mode=duplicate_mode)
