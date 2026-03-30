from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from .validator import FileValidationResult, RecordResult


def export_records(path: Path, records: list[str]) -> None:
    text = "\r\n".join(records)
    if records:
        text += "\r\n"
    path.write_text(text, encoding="utf-8", newline="")


def export_defects_csv(path: Path, result: FileValidationResult) -> None:
    export_defects_csv_records(path, result.records)


def export_defects_csv_records(path: Path, records: Iterable[RecordResult]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "source_file",
                "line_number",
                "field_name",
                "field_label",
                "code",
                "message",
                "start",
                "end",
                "value",
            ]
        )
        for record in records:
            for issue in record.issues:
                writer.writerow(
                    [
                        issue.source_path.name,
                        issue.line_number,
                        issue.field_name,
                        issue.field_label,
                        issue.code,
                        issue.message,
                        issue.start,
                        issue.end,
                        issue.value,
                    ]
                )
