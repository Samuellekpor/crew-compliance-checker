from __future__ import annotations

from crew_compliance.domain.enums import FindingKind, Severity


def hour_exceedance_severity(actual: float, limit: float) -> Severity:
    if actual <= limit:
        return Severity.INFORMATIONAL
    pct = (actual - limit) / limit if limit else 1.0
    if pct > 0.15:
        return Severity.CRITICAL
    if pct > 0.05:
        return Severity.HIGH
    return Severity.MEDIUM


def rest_shortfall_severity(actual: float, required: float) -> Severity:
    if actual >= required or required <= 0:
        return Severity.INFORMATIONAL
    if actual < 0.5 * required:
        return Severity.CRITICAL
    return Severity.HIGH


def kind_severity(kind: FindingKind, issue_severity: Severity) -> Severity:
    if kind in (FindingKind.INSUFFICIENT_DATA, FindingKind.INFORMATIONAL):
        return Severity.INFORMATIONAL
    return issue_severity