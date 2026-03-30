from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Callable


ValidatorFunc = Callable[[str], list[str]]
VALID_COUNTY_CODES = {"000"} | {f"{value:03d}" for value in range(1, 102)}


@dataclass(frozen=True)
class FieldSpec:
    name: str
    label: str
    start: int
    end: int
    required: bool = False
    validators: tuple[ValidatorFunc, ...] = ()
    notes: str = ""

    @property
    def length(self) -> int:
        return self.end - self.start + 1


@dataclass(frozen=True)
class FileProfile:
    key: str
    name: str
    record_length: int
    fields: tuple[FieldSpec, ...] = field(default_factory=tuple)
    notes: str = ""


def validate_numeric(value: str) -> list[str]:
    if value and not value.isdigit():
        return ["must contain only digits"]
    return []


def validate_numeric_or_spaces(value: str) -> list[str]:
    if not value.strip():
        return []
    if not value.isdigit():
        return ["must contain only digits or spaces"]
    return []


def validate_county(value: str) -> list[str]:
    trimmed = value.strip()
    if not trimmed:
        return []
    if len(trimmed) != 3 or not trimmed.isdigit():
        return ["must be a 3-digit county code"]
    if trimmed not in VALID_COUNTY_CODES:
        return ["must match a valid North Carolina county code or 000 default"]
    return []


def validate_uppercase_alnum(value: str) -> list[str]:
    trimmed = value.strip()
    if not trimmed:
        return []
    errors: list[str] = []
    if trimmed != trimmed.upper():
        errors.append("contains lowercase characters")
    if not trimmed.isalnum():
        errors.append("must contain only letters and digits")
    return errors


def validate_alpha_field(value: str) -> list[str]:
    trimmed = value.strip()
    if not trimmed:
        return []
    errors: list[str] = []
    if any("a" <= char <= "z" for char in trimmed):
        errors.append("contains lowercase characters")
    if any(not ("A" <= char <= "Z") for char in trimmed):
        errors.append("must contain only alphabetic characters A-Z")
    return errors


def validate_middle_initial(value: str) -> list[str]:
    trimmed = value.strip()
    if not trimmed:
        return []
    errors: list[str] = []
    if len(trimmed) != 1 or not trimmed.isalpha():
        errors.append("must be a single alphabetic character")
    if any("a" <= char <= "z" for char in trimmed):
        errors.append("contains lowercase characters")
    return errors


def validate_suffix(value: str) -> list[str]:
    trimmed = value.strip()
    if not trimmed:
        return []
    errors: list[str] = []
    if any("a" <= char <= "z" for char in trimmed):
        errors.append("contains lowercase characters")
    if any(not char.isalnum() for char in trimmed):
        errors.append("must contain only letters and digits")
    return errors


def validate_ssn(value: str) -> list[str]:
    trimmed = value.strip()
    if not trimmed:
        return []
    if len(trimmed) != 9 or not trimmed.isdigit():
        return ["must be 9 digits"]
    if trimmed == "000000000":
        return []
    if trimmed[0] == "9":
        return ["cannot start with 9"]
    if trimmed[3:5] == "00" or trimmed[5:9] == "0000":
        return ["must be all zeroes or a valid SSN"]
    return []


def validate_date_yyyy_mm_dd(value: str) -> list[str]:
    trimmed = value.strip()
    if not trimmed:
        return []
    if len(trimmed) != 10 or trimmed[4] != "-" or trimmed[7] != "-":
        return ["must use CCYY-MM-DD format"]
    try:
        year = int(trimmed[0:4])
        month = int(trimmed[5:7])
        day = int(trimmed[8:10])
        parsed = date(year, month, day)
    except ValueError:
        return ["must be a valid calendar date"]
    if parsed > date.today():
        return ["cannot be in the future"]
    return []


def validate_allowed(*allowed_values: str) -> ValidatorFunc:
    allowed = set(allowed_values)

    def _validator(value: str) -> list[str]:
        trimmed = value.strip()
        if not trimmed:
            return []
        if trimmed not in allowed:
            return [f"must be one of: {', '.join(sorted(allowed))}"]
        return []

    return _validator


def validate_medicaid_id(value: str) -> list[str]:
    trimmed = value.strip()
    if not trimmed:
        return []
    if len(trimmed) != 10:
        return ["must be 10 characters"]
    if not trimmed[:9].isdigit():
        return ["first 9 characters must be digits"]
    if not trimmed[9].isalpha() or trimmed[9] != trimmed[9].upper():
        return ["10th character must be an uppercase alphabetic check digit"]
    return []


CNDS_SHARED_130 = FileProfile(
    key="cnds_shared_130",
    name="CCI804 / CCI805 Shared Layout",
    record_length=130,
    notes=(
        "Authoritative onboarding layout from the CNDS Match / Close Match / Create section. "
        "Both CCI804 and CCI805 use this shared 130-character fixed-width input schema. "
        "Business-focused validation is concentrated on positions 24 through 115, while the surrounding fields are still checked to keep downstream COBOL processing stable."
    ),
    fields=(
        FieldSpec(
            name="county",
            label="County",
            start=1,
            end=3,
            required=True,
            validators=(validate_county,),
            notes="Default 000. County table validated against the NCOSC county code list.",
        ),
        FieldSpec(
            name="case_number",
            label="Case Number",
            start=4,
            end=13,
            required=True,
            validators=(validate_numeric,),
            notes="Numeric only. Default 0000000000.",
        ),
        FieldSpec(
            name="medicaid_id",
            label="Medicaid ID / CNDS ID",
            start=14,
            end=23,
            validators=(validate_medicaid_id,),
            notes="CNDS ID / Medicaid ID, typically 9 digits plus 1 alphabetic check digit such as 123456789A. Default spaces.",
        ),
        FieldSpec(
            name="last_name",
            label="Last Name",
            start=24,
            end=53,
            required=True,
            validators=(validate_alpha_field,),
        ),
        FieldSpec(
            name="first_name",
            label="First Name",
            start=54,
            end=65,
            required=True,
            validators=(validate_alpha_field,),
        ),
        FieldSpec(
            name="first_name_filler",
            label="First Name Filler",
            start=66,
            end=77,
            validators=(validate_alpha_field,),
            notes="Continuation/filler area following first name.",
        ),
        FieldSpec(
            name="sis_number",
            label="SIS Number",
            start=78,
            end=83,
            validators=(validate_numeric_or_spaces,),
            notes="May contain digits or spaces.",
        ),
        FieldSpec(
            name="middle_initial",
            label="Middle Initial",
            start=84,
            end=84,
            validators=(validate_middle_initial,),
        ),
        FieldSpec(
            name="suffix",
            label="Suffix",
            start=85,
            end=87,
            validators=(validate_suffix,),
        ),
        FieldSpec(
            name="ssn",
            label="SSN",
            start=88,
            end=96,
            validators=(validate_ssn,),
            notes="Default 000000000.",
        ),
        FieldSpec(
            name="date_of_birth",
            label="Date of Birth",
            start=97,
            end=106,
            required=True,
            validators=(validate_date_yyyy_mm_dd,),
        ),
        FieldSpec(
            name="sex",
            label="Sex",
            start=107,
            end=107,
            required=True,
            validators=(validate_allowed("M", "F"),),
        ),
        FieldSpec(
            name="ethnicity",
            label="Ethnicity",
            start=108,
            end=108,
            validators=(validate_allowed("", "U", "N", "H", "C", "M", "P"),),
            notes="Blank defaults to space.",
        ),
        FieldSpec(
            name="language",
            label="Language",
            start=109,
            end=110,
            validators=(validate_allowed("", "EN", "SP", "AR", "CA", "CH", "FR", "FC", "GE", "GR", "GU", "HI", "HM", "HU", "IT", "JA", "KO", "LA", "MI", "MK", "PE", "PO", "PG", "PC", "RU", "SC", "TA", "TH", "UR", "VI", "OT"),),
            notes="Blank defaults to EN.",
        ),
        FieldSpec(
            name="race_1",
            label="Race 1",
            start=111,
            end=111,
            validators=(validate_allowed("", "U", "A", "B", "I", "P", "W"),),
        ),
        FieldSpec(
            name="race_2",
            label="Race 2",
            start=112,
            end=112,
            validators=(validate_allowed("", "U", "A", "B", "I", "P", "W"),),
        ),
        FieldSpec(
            name="race_3",
            label="Race 3",
            start=113,
            end=113,
            validators=(validate_allowed("", "U", "A", "B", "I", "P", "W"),),
        ),
        FieldSpec(
            name="race_4",
            label="Race 4",
            start=114,
            end=114,
            validators=(validate_allowed("", "U", "A", "B", "I", "P", "W"),),
        ),
        FieldSpec(
            name="race_5",
            label="Race 5",
            start=115,
            end=115,
            validators=(validate_allowed("", "U", "A", "B", "I", "P", "W"),),
        ),
        FieldSpec(
            name="application_person_id",
            label="Application Person ID",
            start=116,
            end=130,
            required=True,
            validators=(validate_uppercase_alnum,),
            notes="Validated for downstream COBOL processing support.",
        ),
    ),
)


DEFAULT_PROFILE = CNDS_SHARED_130
