from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

from crew_compliance.domain.models import Roster
from crew_compliance.ingestion.common import IngestError
from crew_compliance.ingestion.loader import load_table
from crew_compliance.ingestion.mapping import auto_map_columns
from crew_compliance.ingestion.normalize import normalize_roster


def ingest_roster(
    source: str | Path | BinaryIO | bytes,
    *,
    filename: str | None = None,
    mapping: dict[str, str | None] | None = None,
    dayfirst: bool = False,
) -> Roster:
    table = load_table(source, filename=filename)
    if table.empty:
        raise IngestError("The uploaded roster has no data rows.")
    headers = [str(c) for c in table.columns]
    resolved = mapping or auto_map_columns(headers)
    if not resolved.get("duty_date"):
        raise IngestError("A date column is required. Map the roster date column before analyzing.")
    if not resolved.get("crew_id") and not resolved.get("captain") and not resolved.get("crew_name"):
        raise IngestError(
            "A crew column is required. Map either a crew identifier column or Captain / First Officer columns."
        )
    rows = table.to_dict(orient="records")
    name = filename or (getattr(source, "name", None) if hasattr(source, "name") else str(source))
    return normalize_roster(rows, resolved, source_name=str(name), dayfirst=dayfirst)