from __future__ import annotations

from pathlib import Path

from .ccipr60i import (
    CONVERSION_FORMAT_BINARY,
    CONVERSION_FORMAT_BOTH,
    CONVERSION_FORMAT_TEXT,
    BinaryValidationSummary,
    ConversionConfig,
    EBCDIC_CODEC,
    FieldDefinition,
)
from .validator import RecordResult

CCIPR10H_RECORD_LENGTH = 1000
CCIPR10H_TEXT_FILE_NAME = "ccipr10h_preview.txt"
CCIPR10H_BINARY_FILE_NAME = "ccipr10h_upload.bin"


class Ccipr10hBuildError(ValueError):
    pass


# CCIPR10H uses the same header, person-field order, and trailing fields as
# CCIPR60I, with Medicaid identifier/check-digit inserted ahead of last name.
CCIPR10H_FIELD_DEFINITIONS: tuple[FieldDefinition, ...] = (
    FieldDefinition("svc_version", 1, 2, "char", "left", required=True),
    FieldDefinition("svc_release", 3, 4, "char", "left", required=True),
    FieldDefinition("accounting_info", 5, 10, "char", "left", required=True),
    FieldDefinition("accounting_info_2", 11, 34, "char", "left"),
    FieldDefinition("testing_comment", 35, 90, "char", "left", required=True),
    FieldDefinition("comp_code", 91, 95, "char", "right", required=True),
    FieldDefinition("reason_code", 96, 100, "char", "right", required=True),
    FieldDefinition("cnds_header_type", 101, 101, "char", "left", required=True),
    FieldDefinition("cnds_service", 102, 109, "char", "left", required=True),
    FieldDefinition("cnds_version", 110, 111, "char", "left"),
    FieldDefinition("cnds_application", 112, 115, "char", "left", required=True),
    FieldDefinition("cnds_filler", 116, 120, "char", "left"),
    FieldDefinition("person_segment_filler_1", 121, 121, "char", "left"),
    FieldDefinition("identifier", 122, 130, "numeric_display", "right", required=True),
    FieldDefinition("person_segment_filler_2", 131, 131, "char", "left"),
    FieldDefinition("check_digit", 132, 132, "char", "left", required=True),
    FieldDefinition("person_segment_filler_3", 133, 133, "char", "left"),
    FieldDefinition("last_name", 134, 173, "char", "left", required=True),
    FieldDefinition("person_segment_filler_4", 174, 174, "char", "left"),
    FieldDefinition("first_name", 175, 186, "char", "left", required=True),
    FieldDefinition("person_segment_filler_5", 187, 187, "char", "left"),
    FieldDefinition("middle_initial", 188, 188, "char", "left"),
    FieldDefinition("person_segment_filler_6", 189, 189, "char", "left"),
    FieldDefinition("suffix", 190, 192, "char", "left"),
    FieldDefinition("person_segment_filler_7", 193, 193, "char", "left"),
    FieldDefinition("primary_ssn", 194, 202, "numeric_display", "right", required=True),
    FieldDefinition("person_segment_filler_8", 203, 203, "char", "left"),
    FieldDefinition("date_of_birth", 204, 211, "numeric_display", "right", required=True),
    FieldDefinition("person_segment_filler_9", 212, 212, "char", "left"),
    FieldDefinition("sex_code", 213, 213, "char", "left", required=True),
    FieldDefinition("person_segment_filler_10", 214, 214, "char", "left"),
    FieldDefinition("ethnicity", 215, 215, "char", "left"),
    FieldDefinition("person_segment_filler_11", 216, 216, "char", "left"),
    FieldDefinition("language_preference", 217, 218, "char", "left"),
    FieldDefinition("person_segment_filler_12", 219, 219, "char", "left"),
    FieldDefinition("last_changed_program_id", 220, 227, "char", "left", required=True),
    FieldDefinition("person_segment_filler_13", 228, 228, "char", "left"),
    FieldDefinition("last_changed_user_id", 229, 236, "char", "left"),
    FieldDefinition("race_count", 237, 240, "numeric_display", "right", required=True),
    FieldDefinition("race_occurs_1_filler_1", 241, 241, "char", "left"),
    FieldDefinition("race_occurs_1_filler_2", 242, 242, "char", "left"),
    FieldDefinition("race_1", 243, 243, "char", "left"),
    FieldDefinition("race_occurs_2_filler_1", 244, 244, "char", "left"),
    FieldDefinition("race_occurs_2_filler_2", 245, 245, "char", "left"),
    FieldDefinition("race_2", 246, 246, "char", "left"),
    FieldDefinition("race_occurs_3_filler_1", 247, 247, "char", "left"),
    FieldDefinition("race_occurs_3_filler_2", 248, 248, "char", "left"),
    FieldDefinition("race_3", 249, 249, "char", "left"),
    FieldDefinition("race_occurs_4_filler_1", 250, 250, "char", "left"),
    FieldDefinition("race_occurs_4_filler_2", 251, 251, "char", "left"),
    FieldDefinition("race_4", 252, 252, "char", "left"),
    FieldDefinition("race_occurs_5_filler_1", 253, 253, "char", "left"),
    FieldDefinition("race_occurs_5_filler_2", 254, 254, "char", "left"),
    FieldDefinition("race_5", 255, 255, "char", "left"),
    FieldDefinition("record_filler", 256, 1000, "char", "left"),
)
FIELD_BY_NAME = {field.field_name: field for field in CCIPR10H_FIELD_DEFINITIONS}


def _fixed_width(value: str, definition: FieldDefinition) -> str:
    if "\t" in value:
        raise Ccipr10hBuildError(f"tab character is not allowed in field {definition.field_name}")
    if "\r" in value or "\n" in value:
        raise Ccipr10hBuildError(f"CR/LF is not allowed in field {definition.field_name}")
    if len(value) > definition.length:
        raise Ccipr10hBuildError(
            f"field {definition.field_name} exceeds width {definition.length}: {value!r}"
        )
    if definition.required and not value:
        raise Ccipr10hBuildError(f"required field {definition.field_name} is missing")
    if definition.justification == "right":
        return value.rjust(definition.length, definition.pad_character)
    return value.ljust(definition.length, definition.pad_character)


def _race_values(record: RecordResult) -> tuple[str, ...]:
    race_names = ("race_1", "race_2", "race_3", "race_4", "race_5")
    return tuple(record.fields[name].strip().upper() for name in race_names)


def _race_count_text(record: RecordResult) -> str:
    return f"{sum(1 for race_value in _race_values(record) if race_value):04d}"


def _medicaid_identifier_parts(record: RecordResult) -> tuple[str, str]:
    medicaid_id = record.fields["medicaid_id"].strip().upper()
    if len(medicaid_id) != 10:
        raise Ccipr10hBuildError("medicaid_id must be 10 characters for CCIPR10H conversion")
    identifier = medicaid_id[:9]
    check_digit = medicaid_id[9]
    if not identifier.isdigit():
        raise Ccipr10hBuildError("medicaid_id positions 1-9 must be numeric for CCIPR10H conversion")
    if not check_digit.isalpha():
        raise Ccipr10hBuildError("medicaid_id position 10 must be an alphabetic check digit for CCIPR10H conversion")
    return identifier, check_digit


def build_field_value_map(record: RecordResult, config: ConversionConfig) -> dict[str, str]:
    fields = record.fields
    identifier, check_digit = _medicaid_identifier_parts(record)
    values = {
        "svc_version": "01",
        "svc_release": "01",
        "accounting_info": config.accounting_info.strip().upper(),
        "accounting_info_2": "",
        "testing_comment": f"={config.testing_comment.strip().upper():<13}|  CCIPR10H    |                         |",
        "comp_code": "0000{",
        "reason_code": "0000{",
        "cnds_header_type": "O",
        "cnds_service": "CCIPR10H",
        "cnds_version": "",
        "cnds_application": "CCI",
        "cnds_filler": "",
        "person_segment_filler_1": "",
        "identifier": identifier,
        "person_segment_filler_2": "",
        "check_digit": check_digit,
        "person_segment_filler_3": "",
        "last_name": fields["last_name"].strip().upper(),
        "person_segment_filler_4": "",
        "first_name": fields["first_name"].strip().upper(),
        "person_segment_filler_5": "",
        "middle_initial": fields["middle_initial"].strip().upper(),
        "person_segment_filler_6": "",
        "suffix": fields["suffix"].strip().upper(),
        "person_segment_filler_7": "",
        "primary_ssn": fields["ssn"].strip(),
        "person_segment_filler_8": "",
        "date_of_birth": fields["date_of_birth"].strip().replace("-", ""),
        "person_segment_filler_9": "",
        "sex_code": fields["sex"].strip().upper(),
        "person_segment_filler_10": "",
        "ethnicity": fields["ethnicity"].strip().upper(),
        "person_segment_filler_11": "",
        "language_preference": fields["language"].strip().upper(),
        "person_segment_filler_12": "",
        "last_changed_program_id": config.last_changed_program_id.strip().upper(),
        "person_segment_filler_13": "",
        "last_changed_user_id": config.last_changed_user_id.strip().upper(),
        "race_count": _race_count_text(record),
        "record_filler": "",
    }
    for index, race_value in enumerate(_race_values(record), start=1):
        values[f"race_occurs_{index}_filler_1"] = ""
        values[f"race_occurs_{index}_filler_2"] = ""
        values[f"race_{index}"] = race_value
    return values


def build_logical_record(record: RecordResult, config: ConversionConfig) -> str:
    buffer = [" "] * CCIPR10H_RECORD_LENGTH
    values = build_field_value_map(record, config)
    for definition in CCIPR10H_FIELD_DEFINITIONS:
        value = values.get(definition.field_name, "")
        formatted = _fixed_width(value, definition)
        start = definition.start_position - 1
        end = definition.end_position
        if len(formatted) != definition.length:
            raise Ccipr10hBuildError(
                f"field {definition.field_name} formatted to {len(formatted)} but expected {definition.length}"
            )
        buffer[start:end] = list(formatted)
    logical_record = "".join(buffer)
    if len(logical_record) != CCIPR10H_RECORD_LENGTH:
        raise Ccipr10hBuildError(
            f"logical record length is {len(logical_record)} but expected {CCIPR10H_RECORD_LENGTH}"
        )
    if "\t" in logical_record:
        raise Ccipr10hBuildError("tab character found in logical record")
    if "\r" in logical_record or "\n" in logical_record:
        raise Ccipr10hBuildError("CR/LF found in logical record")
    return logical_record


def encode_logical_record(logical_record: str) -> bytes:
    encoded = logical_record.encode(EBCDIC_CODEC)
    if len(encoded) != CCIPR10H_RECORD_LENGTH:
        raise Ccipr10hBuildError(
            f"encoded record length is {len(encoded)} but expected {CCIPR10H_RECORD_LENGTH}"
        )
    if b"\t" in encoded:
        raise Ccipr10hBuildError("tab byte found in encoded output")
    if b"\r" in encoded or b"\n" in encoded:
        raise Ccipr10hBuildError("CR/LF byte found in encoded output")
    return encoded


def build_binary_record(record: RecordResult, config: ConversionConfig) -> bytes:
    logical_record = build_logical_record(record, config)
    return encode_logical_record(logical_record)


def build_ccipr10h_record(record: RecordResult, config: ConversionConfig) -> str:
    return build_logical_record(record, config)


def write_ccipr10h_text(path: Path, records: list[str]) -> None:
    preview_records = [record.rstrip() for record in records]
    text = "\r\n".join(preview_records)
    if records:
        text += "\r\n"
    path.write_text(text, encoding="utf-8", newline="")


def write_ccipr10h_binary(path: Path, records: list[str]) -> None:
    with path.open("wb") as handle:
        for logical_record in records:
            encoded = encode_logical_record(logical_record)
            handle.write(encoded)


def validate_ccipr10h_binary_file(path: Path) -> BinaryValidationSummary:
    data = path.read_bytes()
    if len(data) % CCIPR10H_RECORD_LENGTH != 0:
        raise Ccipr10hBuildError(
            f"file size {len(data)} is not divisible by {CCIPR10H_RECORD_LENGTH}"
        )
    if b"\r" in data or b"\n" in data:
        raise Ccipr10hBuildError("CR/LF byte found in binary output")
    if b"\t" in data:
        raise Ccipr10hBuildError("tab byte found in binary output")
    ebcdic_space = " ".encode(EBCDIC_CODEC)[0]
    filler = FIELD_BY_NAME["record_filler"]
    record_count = len(data) // CCIPR10H_RECORD_LENGTH
    for record_index in range(record_count):
        start = record_index * CCIPR10H_RECORD_LENGTH
        record_bytes = data[start : start + CCIPR10H_RECORD_LENGTH]
        filler_bytes = record_bytes[filler.start_position - 1 : filler.end_position]
        if any(byte != ebcdic_space for byte in filler_bytes):
            raise Ccipr10hBuildError(
                f"record {record_index + 1} filler bytes {filler.start_position}-{filler.end_position} are not space-padded"
            )
    return BinaryValidationSummary(
        record_count=record_count,
        file_size=len(data),
        record_length=CCIPR10H_RECORD_LENGTH,
        filler_start=filler.start_position,
        filler_end=filler.end_position,
    )


def output_format_includes_text(config: ConversionConfig) -> bool:
    return config.output_format in (CONVERSION_FORMAT_BOTH, CONVERSION_FORMAT_TEXT)


def output_format_includes_binary(config: ConversionConfig) -> bool:
    return config.output_format in (CONVERSION_FORMAT_BOTH, CONVERSION_FORMAT_BINARY)
