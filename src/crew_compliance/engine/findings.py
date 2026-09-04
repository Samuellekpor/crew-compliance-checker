from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from crew_compliance.domain.enums import FindingKind, Severity
from crew_compliance.domain.models import Finding, RuleMetadata
from crew_compliance.engine.severity import kind_severity


def make_finding_id(rule_id: str, crew_id: str, event_time: datetime | None, extra: str = "") -> str:
    stamp = event_time.isoformat() if event_time else ""
    raw = f"{rule_id}|{crew_id}|{stamp}|{extra}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def build_finding(
    metadata: RuleMetadata,
    *,
    kind: FindingKind,
    crew_id: str,
    crew_name: str,
    severity: Severity,
    explanation: str,
    actual: float | None = None,
    required: float | None = None,
    difference: float | None = None,
    units: str = "hours",
    duty_id: str | None = None,
    flight_id: str | None = None,
    event_time: datetime | None = None,
    evidence: dict[str, Any] | None = None,
    extra_limitations: tuple[str, ...] = (),
    extra: str = "",
) -> Finding:
    diff = difference
    if diff is None and actual is not None and required is not None:
        diff = round(actual - required, 4)
    return Finding(
        finding_id=make_finding_id(
            metadata.rule_id,
            crew_id,
            event_time,
            kind.value if not extra else f"{kind.value}|{extra}",
        ),
        kind=kind,
        rule_id=metadata.rule_id,
        rule_name=metadata.name,
        framework_id=metadata.framework_id,
        ruleset_version=metadata.ruleset_version,
        rule_version=metadata.rule_version,
        citation=metadata.citation,
        crew_id=crew_id,
        crew_name=crew_name,
        duty_id=duty_id,
        flight_id=flight_id,
        event_time=event_time,
        actual=actual,
        required=required,
        difference=diff,
        units=units,
        severity=kind_severity(kind, severity),
        evidence=evidence or {},
        explanation=explanation,
        assumptions=metadata.assumptions,
        limitations=metadata.limitations + extra_limitations,
    )