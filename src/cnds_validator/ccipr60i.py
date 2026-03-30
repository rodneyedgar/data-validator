from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .validator import RecordResult

CONVERSION_SCOPE_VALID_ONLY = "valid_only"
CONVERSION_SCOPE_VALID_AND_CORRECTED = "valid_and_corrected"
CONVERSION_SCOPE_LABELS = {
    "Valid records only": CONVERSION_SCOPE_VALID_ONLY,
    "Valid + Corrected records": CONVERSION_SCOPE_VALID_AND_CORRECTED,
}
CONVERSION_SCOPE_REVERSE = {value: key for key, value in CONVERSION_SCOPE_LABELS.items()}

CONVERSION_FORMAT_TEXT = "text"
CONVERSION_FORMAT_BINARY = "binary"
CONVERSION_FORMAT_BOTH = "both"
CONVERSION_FORMAT_LABELS = {
    "Text only": CONVERSION_FORMAT_TEXT,
    "Binary only": CONVERSION_FORMAT_BINARY,
    "Text + Binary": CONVERSION_FORMAT_BOTH,
}
CONVERSION_FORMAT_REVERSE = {value: key for key, value in CONVERSION_FORMAT_LABELS.items()}

CCIPR60I_RECORD_LENGTH = 1000
CCIPR60I_TEXT_FILE_NAME = "ccipr60i_preview.txt"
CCIPR60I_BINARY_FILE_NAME = "ccipr60i_upload.bin"
EBCDIC_CODEC = "cp037"


@dataclass(frozen=True)
class ConversionConfig:
    scope: str = CONVERSION_SCOPE_VALID_ONLY
    output_format: str = CONVERSION_FORMAT_BOTH
    accounting_info: str = "DHRCCI"
    testing_comment: str = "CCICREATE"
    last_changed_program_id: str = "CCIBTH60"
    last_changed_user_id: str = ""


@dataclass(frozen=True)
class FieldDefinition:
    field_name: str
    start_position: int
    end_position: int
    field_type: str
    justification: str
    pad_character: str = " "
    required: bool = False
    allowed_values: tuple[str, ...] = ()

    @property
    def length(self) -> int:
        return self.end_position - self.start_position + 1


@dataclass(frozen=True)
class ComparisonResult:
    matches: bool
    first_mismatch_offset: int | None = None
    expected_byte: int | None = None
    actual_byte: int | None = None
    field_name: str | None = None
    message: str = ""


@dataclass(frozen=True)
class BinaryValidationSummary:
    record_count: int
    file_size: int
    record_length: int
    filler_start: int
    filler_end: int


CCIPR60I_FIELD_DEFINITIONS: tuple[FieldDefinition, ...] = (
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
    FieldDefinition("last_name", 122, 161, "char", "left", required=True),
    FieldDefinition("person_segment_filler_2", 162, 162, "char", "left"),
    FieldDefinition("first_name", 163, 174, "char", "left", required=True),
    FieldDefinition("person_segment_filler_3", 175, 175, "char", "left"),
    FieldDefinition("middle_initial", 176, 176, "char", "left"),
    FieldDefinition("person_segment_filler_4", 177, 177, "char", "left"),
    FieldDefinition("suffix", 178, 180, "char", "left"),
    FieldDefinition("person_segment_filler_5", 181, 181, "char", "left"),
    FieldDefinition("primary_ssn", 182, 190, "numeric_display", "right", required=True),
    FieldDefinition("person_segment_filler_6", 191, 191, "char", "left"),
    FieldDefinition("date_of_birth", 192, 199, "numeric_display", "right", required=True),
    FieldDefinition("person_segment_filler_7", 200, 200, "char", "left"),
    FieldDefinition("sex_code", 201, 201, "char", "left", required=True),
    FieldDefinition("person_segment_filler_8", 202, 202, "char", "left"),
    FieldDefinition("ethnicity", 203, 203, "char", "left"),
    FieldDefinition("person_segment_filler_9", 204, 204, "char", "left"),
    FieldDefinition("language_preference", 205, 206, "char", "left"),
    FieldDefinition("person_segment_filler_10", 207, 207, "char", "left"),
    FieldDefinition("biometrics_code", 208, 208, "char", "left"),
    FieldDefinition("person_segment_filler_11", 209, 209, "char", "left"),
    FieldDefinition("ssi_indicator", 210, 210, "char", "left", required=True),
    FieldDefinition("person_segment_filler_12", 211, 211, "char", "left"),
    FieldDefinition("acts_mpi_number", 212, 221, "char", "left"),
    FieldDefinition("person_segment_filler_13", 222, 222, "char", "left"),
    FieldDefinition("last_applied_eis_county", 223, 225, "char", "left"),
    FieldDefinition("person_segment_filler_14", 226, 226, "char", "left"),
    FieldDefinition("last_applied_fsis_county", 227, 229, "char", "left"),
    FieldDefinition("person_segment_filler_15", 230, 230, "char", "left"),
    FieldDefinition("last_changed_program_id", 231, 238, "char", "left", required=True),
    FieldDefinition("person_segment_filler_16", 239, 239, "char", "left"),
    FieldDefinition("last_changed_user_id", 240, 247, "char", "left"),
    FieldDefinition("race_count", 248, 251, "numeric_display", "right", required=True),
    FieldDefinition("race_occurs_1_filler_1", 252, 252, "char", "left"),
    FieldDefinition("race_occurs_1_filler_2", 253, 253, "char", "left"),
    FieldDefinition("race_1", 254, 254, "char", "left"),
    FieldDefinition("race_occurs_2_filler_1", 255, 255, "char", "left"),
    FieldDefinition("race_occurs_2_filler_2", 256, 256, "char", "left"),
    FieldDefinition("race_2", 257, 257, "char", "left"),
    FieldDefinition("race_occurs_3_filler_1", 258, 258, "char", "left"),
    FieldDefinition("race_occurs_3_filler_2", 259, 259, "char", "left"),
    FieldDefinition("race_3", 260, 260, "char", "left"),
    FieldDefinition("race_occurs_4_filler_1", 261, 261, "char", "left"),
    FieldDefinition("race_occurs_4_filler_2", 262, 262, "char", "left"),
    FieldDefinition("race_4", 263, 263, "char", "left"),
    FieldDefinition("race_occurs_5_filler_1", 264, 264, "char", "left"),
    FieldDefinition("race_occurs_5_filler_2", 265, 265, "char", "left"),
    FieldDefinition("race_5", 266, 266, "char", "left"),
    FieldDefinition("record_filler", 267, 1000, "char", "left"),
)
FIELD_BY_NAME = {field.field_name: field for field in CCIPR60I_FIELD_DEFINITIONS}


class Ccipr60iBuildError(ValueError):
    pass


def _fixed_width(value: str, definition: FieldDefinition) -> str:
    if "\t" in value:
        raise Ccipr60iBuildError(f"tab character is not allowed in field {definition.field_name}")
    if "\r" in value or "\n" in value:
        raise Ccipr60iBuildError(f"CR/LF is not allowed in field {definition.field_name}")
    if len(value) > definition.length:
        raise Ccipr60iBuildError(
            f"field {definition.field_name} exceeds width {definition.length}: {value!r}"
        )
    if definition.required and not value:
        raise Ccipr60iBuildError(f"required field {definition.field_name} is missing")
    if definition.allowed_values and value and value not in definition.allowed_values:
        allowed = ", ".join(definition.allowed_values)
        raise Ccipr60iBuildError(f"field {definition.field_name} must be one of: {allowed}")
    if definition.justification == "right":
        return value.rjust(definition.length, definition.pad_character)
    return value.ljust(definition.length, definition.pad_character)


def _race_values(record: RecordResult) -> tuple[str, ...]:
    race_names = ("race_1", "race_2", "race_3", "race_4", "race_5")
    return tuple(record.fields[name].strip().upper() for name in race_names)


def _race_count_text(record: RecordResult) -> str:
    return f"{sum(1 for race_value in _race_values(record) if race_value):04d}"


def build_field_value_map(record: RecordResult, config: ConversionConfig) -> dict[str, str]:
    fields = record.fields
    values = {
        "svc_version": "01",
        "svc_release": "01",
        "accounting_info": config.accounting_info.strip().upper(),
        "accounting_info_2": "",
        "testing_comment": f"={config.testing_comment.strip().upper()}",
        "comp_code": "0000{",
        "reason_code": "0000{",
        "cnds_header_type": "O",
        "cnds_service": "CCIPR60I",
        "cnds_version": "",
        "cnds_application": "CCI",
        "cnds_filler": "",
        "person_segment_filler_1": "",
        "last_name": fields["last_name"].strip().upper(),
        "person_segment_filler_2": "",
        "first_name": fields["first_name"].strip().upper(),
        "person_segment_filler_3": "",
        "middle_initial": fields["middle_initial"].strip().upper(),
        "person_segment_filler_4": "",
        "suffix": fields["suffix"].strip().upper(),
        "person_segment_filler_5": "",
        "primary_ssn": fields["ssn"].strip(),
        "person_segment_filler_6": "",
        "date_of_birth": fields["date_of_birth"].strip().replace("-", ""),
        "person_segment_filler_7": "",
        "sex_code": fields["sex"].strip().upper(),
        "person_segment_filler_8": "",
        "ethnicity": fields["ethnicity"].strip().upper(),
        "person_segment_filler_9": "",
        "language_preference": fields["language"].strip().upper(),
        "person_segment_filler_10": "",
        "biometrics_code": "",
        "person_segment_filler_11": "",
        "ssi_indicator": "N",
        "person_segment_filler_12": "",
        "acts_mpi_number": "",
        "person_segment_filler_13": "",
        "last_applied_eis_county": "",
        "person_segment_filler_14": "",
        "last_applied_fsis_county": "",
        "person_segment_filler_15": "",
        "last_changed_program_id": config.last_changed_program_id.strip().upper(),
        "person_segment_filler_16": "",
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
    buffer = [" "] * CCIPR60I_RECORD_LENGTH
    values = build_field_value_map(record, config)
    for definition in CCIPR60I_FIELD_DEFINITIONS:
        value = values.get(definition.field_name, "")
        formatted = _fixed_width(value, definition)
        start = definition.start_position - 1
        end = definition.end_position
        if len(formatted) != definition.length:
            raise Ccipr60iBuildError(
                f"field {definition.field_name} formatted to {len(formatted)} but expected {definition.length}"
            )
        buffer[start:end] = list(formatted)
    logical_record = "".join(buffer)
    if len(logical_record) != CCIPR60I_RECORD_LENGTH:
        raise Ccipr60iBuildError(
            f"logical record length is {len(logical_record)} but expected {CCIPR60I_RECORD_LENGTH}"
        )
    if "\t" in logical_record:
        raise Ccipr60iBuildError("tab character found in logical record")
    if "\r" in logical_record or "\n" in logical_record:
        raise Ccipr60iBuildError("CR/LF found in logical record")
    return logical_record


def encode_logical_record(logical_record: str) -> bytes:
    encoded = logical_record.encode(EBCDIC_CODEC)
    if len(encoded) != CCIPR60I_RECORD_LENGTH:
        raise Ccipr60iBuildError(
            f"encoded record length is {len(encoded)} but expected {CCIPR60I_RECORD_LENGTH}"
        )
    if b"\t" in encoded:
        raise Ccipr60iBuildError("tab byte found in encoded output")
    if b"\r" in encoded or b"\n" in encoded:
        raise Ccipr60iBuildError("CR/LF byte found in encoded output")
    return encoded


def build_binary_record(record: RecordResult, config: ConversionConfig) -> bytes:
    logical_record = build_logical_record(record, config)
    return encode_logical_record(logical_record)


def build_ccipr60i_record(record: RecordResult, config: ConversionConfig) -> str:
    return build_logical_record(record, config)


def write_ccipr60i_text(path: Path, records: list[str]) -> None:
    preview_records = [record.rstrip() for record in records]
    text = "\r\n".join(preview_records)
    if records:
        text += "\r\n"
    path.write_text(text, encoding="utf-8", newline="")


def write_ccipr60i_binary(path: Path, records: list[str]) -> None:
    with path.open("wb") as handle:
        for logical_record in records:
            encoded = encode_logical_record(logical_record)
            handle.write(encoded)


def validate_binary_file(path: Path) -> BinaryValidationSummary:
    data = path.read_bytes()
    if len(data) % CCIPR60I_RECORD_LENGTH != 0:
        raise Ccipr60iBuildError(
            f"file size {len(data)} is not divisible by {CCIPR60I_RECORD_LENGTH}"
        )
    if b"\r" in data or b"\n" in data:
        raise Ccipr60iBuildError("CR/LF byte found in binary output")
    if b"\t" in data:
        raise Ccipr60iBuildError("tab byte found in binary output")
    ebcdic_space = " ".encode(EBCDIC_CODEC)[0]
    filler = FIELD_BY_NAME["record_filler"]
    record_count = len(data) // CCIPR60I_RECORD_LENGTH
    for record_index in range(record_count):
        start = record_index * CCIPR60I_RECORD_LENGTH
        record_bytes = data[start : start + CCIPR60I_RECORD_LENGTH]
        filler_bytes = record_bytes[filler.start_position - 1 : filler.end_position]
        if any(byte != ebcdic_space for byte in filler_bytes):
            raise Ccipr60iBuildError(
                f"record {record_index + 1} filler bytes {filler.start_position}-{filler.end_position} are not space-padded"
            )
    return BinaryValidationSummary(
        record_count=record_count,
        file_size=len(data),
        record_length=CCIPR60I_RECORD_LENGTH,
        filler_start=filler.start_position,
        filler_end=filler.end_position,
    )


def _field_for_byte_offset(byte_offset: int) -> str | None:
    position = byte_offset + 1
    for definition in CCIPR60I_FIELD_DEFINITIONS:
        if definition.start_position <= position <= definition.end_position:
            return definition.field_name
    return None


def compare_binary_files(expected_path: Path, actual_path: Path) -> ComparisonResult:
    expected = expected_path.read_bytes()
    actual = actual_path.read_bytes()
    if len(expected) != len(actual):
        return ComparisonResult(
            matches=False,
            message=f"file size mismatch: expected {len(expected)} bytes, actual {len(actual)} bytes",
        )
    for offset, (expected_byte, actual_byte) in enumerate(zip(expected, actual, strict=True)):
        if expected_byte != actual_byte:
            field_name = _field_for_byte_offset(offset % CCIPR60I_RECORD_LENGTH)
            return ComparisonResult(
                matches=False,
                first_mismatch_offset=offset,
                expected_byte=expected_byte,
                actual_byte=actual_byte,
                field_name=field_name,
                message=(
                    f"first mismatch at byte offset {offset}: expected 0x{expected_byte:02X}, "
                    f"actual 0x{actual_byte:02X}"
                ),
            )
    return ComparisonResult(matches=True, message="files match byte-for-byte")


def _column_ruler(length: int = CCIPR60I_RECORD_LENGTH) -> str:
    digits = "1234567890"
    return "".join(digits[index % 10] for index in range(length))


def _hex_dump(data: bytes, width: int = 32) -> str:
    lines: list[str] = []
    for offset in range(0, len(data), width):
        chunk = data[offset : offset + width]
        hex_values = " ".join(f"{byte:02X}" for byte in chunk)
        lines.append(f"{offset:04d}: {hex_values}")
    return "\n".join(lines)


def debug_dump_records(records: Iterable[RecordResult], config: ConversionConfig, limit: int = 3) -> str:
    lines: list[str] = []
    for record_number, record in enumerate(records, start=1):
        if record_number > limit:
            break
        logical_record = build_logical_record(record, config)
        encoded = encode_logical_record(logical_record)
        byte_offset = (record_number - 1) * CCIPR60I_RECORD_LENGTH
        lines.append(f"Record {record_number}")
        lines.append(f"Byte offset: {byte_offset}")
        lines.append(f"Column ruler: {_column_ruler(120)}...")
        lines.append(f"Logical record: {logical_record}")
        lines.append("Hex dump:")
        lines.append(_hex_dump(encoded[:256]))
        lines.append(f"CP037 preview: {encoded.decode(EBCDIC_CODEC)}")
        lines.append("Fields:")
        values = build_field_value_map(record, config)
        for definition in CCIPR60I_FIELD_DEFINITIONS:
            value = values.get(definition.field_name, "")
            lines.append(
                f"  {definition.field_name}: {definition.start_position}-{definition.end_position} "
                f"len={definition.length} value={value!r}"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
