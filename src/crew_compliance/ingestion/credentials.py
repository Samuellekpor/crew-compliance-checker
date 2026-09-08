from __future__ import annotations

from crew_compliance.domain.credentials import Credential, CredentialBook, normalize_credential_type
from crew_compliance.domain.models import ValidationIssue
from crew_compliance.ingestion.common import _str, mapped_value
from crew_compliance.ingestion.parse import parse_date


def normalize_credentials(
    rows: list[dict],
    mapping: dict[str, str | None],
    source_name: str,
    dayfirst: bool = False,
) -> CredentialBook:
    records: list[Credential] = []
    issues: list[ValidationIssue] = []
    dropped = 0

    for index, row in enumerate(rows, start=2):
        crew_id = _str(mapped_value(row, mapping, "crew_id")) or _str(mapped_value(row, mapping, "crew_name"))
        if not crew_id:
            issues.append(ValidationIssue("This row is missing a crew identifier.", source_row=index, field="crew_id"))
            dropped += 1
            continue
        cred_type = normalize_credential_type(_str(mapped_value(row, mapping, "credential_type")))
        if not cred_type:
            issues.append(
                ValidationIssue(
                    "This row is missing a credential type (for example license, medical, or type_rating).",
                    source_row=index,
                    field="credential_type",
                )
            )
            dropped += 1
            continue
        expiry = parse_date(mapped_value(row, mapping, "expiry_date"), dayfirst=dayfirst)
        if expiry is None:
            issues.append(
                ValidationIssue(
                    "This row has a missing or invalid expiry date. The credential cannot be assumed valid.",
                    source_row=index,
                    field="expiry_date",
                )
            )
        records.append(
            Credential(
                crew_id=crew_id,
                crew_name=_str(mapped_value(row, mapping, "crew_name")),
                role=_str(mapped_value(row, mapping, "role")),
                credential_type=cred_type,
                credential_detail=_str(mapped_value(row, mapping, "credential_detail")),
                expiry_date=expiry,
                source_row=index,
            )
        )

    return CredentialBook(
        source_name=source_name,
        records=tuple(records),
        validation_issues=tuple(issues),
        dropped_row_count=dropped,
    )
