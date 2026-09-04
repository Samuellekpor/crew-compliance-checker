from __future__ import annotations

from datetime import date, datetime, timedelta

from crew_compliance.domain.credentials import Credential, CredentialBook
from crew_compliance.domain.enums import FindingKind, Severity
from crew_compliance.domain.models import Finding, Roster, RuleMetadata
from crew_compliance.engine.findings import build_finding
from crew_compliance.engine.protocol import EvaluationContext

ASSUMPTIONS = (
    "Expiry screening uses the earliest duty date in the uploaded roster as the look-ahead start.",
    "Only credentials present in the uploaded file are evaluated; missing people or types are not inferred.",
)
LIMITATIONS = (
    "This is not a determination under a licensing, medical, or immigration rule.",
    "A missing expiry date is never treated as valid or as a pass.",
)


def evaluate_credential_expiry(
    roster: Roster,
    ctx: EvaluationContext,
    book: CredentialBook,
    lookahead_days: int,
) -> list[Finding]:
    screening_start = min((d.duty_date for d in roster.duties), default=date.today())
    window_end = screening_start + timedelta(days=lookahead_days)
    duties_by_crew: dict[str, list[date]] = {}
    for duty in roster.duties:
        duties_by_crew.setdefault(duty.crew_id, []).append(duty.duty_date)
    names = {member.crew_id: member.name for member in roster.crew}
    metadata = _metadata(ctx, lookahead_days)
    findings: list[Finding] = []
    for cred in book.records:
        name = cred.crew_name or names.get(cred.crew_id) or cred.crew_id
        if cred.expiry_date is None:
            findings.append(
                build_finding(
                    metadata,
                    kind=FindingKind.INSUFFICIENT_DATA,
                    crew_id=cred.crew_id,
                    crew_name=name,
                    severity=Severity.INFORMATIONAL,
                    explanation=(
                        f"{name} has a {cred.credential_type} credential with no usable expiry date. "
                        "Validity cannot be assumed."
                    ),
                    evidence=_evidence(cred, screening_start, lookahead_days, scheduled=False, flying_after_expiry=False),
                    extra_limitations=("Missing expiry is never treated as valid.",),
                    extra=f"{cred.source_row}|missing-expiry",
                )
            )
            continue
        days_until = (cred.expiry_date - screening_start).days
        if days_until > lookahead_days:
            continue
        duty_dates = duties_by_crew.get(cred.crew_id, [])
        scheduled_in_window = any(screening_start <= d <= window_end for d in duty_dates)
        flying_after_expiry = any(d >= cred.expiry_date for d in duty_dates)
        severity = _severity(days_until, scheduled_in_window, flying_after_expiry)
        label = cred.credential_detail or cred.credential_type
        if days_until < 0:
            timing = f"expired on {cred.expiry_date.isoformat()} ({abs(days_until)} days before the roster start)"
        elif days_until == 0:
            timing = f"expires on the roster start date ({cred.expiry_date.isoformat()})"
        else:
            timing = f"expires on {cred.expiry_date.isoformat()} ({days_until} days after the roster start)"
        schedule_note = ""
        if flying_after_expiry:
            schedule_note = " The crew member is scheduled to operate on or after that expiry date."
        elif scheduled_in_window:
            schedule_note = " The crew member is scheduled to operate during the look-ahead window."
        findings.append(
            build_finding(
                metadata,
                kind=FindingKind.POTENTIAL_ISSUE,
                crew_id=cred.crew_id,
                crew_name=name,
                severity=severity,
                actual=float(days_until),
                required=float(lookahead_days),
                units="days",
                event_time=datetime.combine(cred.expiry_date, datetime.min.time()),
                explanation=(
                    f"{name}'s {label} {timing}.{schedule_note} This is a potential issue "
                    "and requires review; it is not a licensing determination."
                ),
                evidence=_evidence(
                    cred,
                    screening_start,
                    lookahead_days,
                    scheduled=scheduled_in_window,
                    flying_after_expiry=flying_after_expiry,
                    days_until=days_until,
                    window_end=window_end,
                ),
                extra=f"{cred.source_row}|{cred.credential_type}",
            )
        )
    return findings


def _severity(days_until: int, scheduled: bool, flying_after_expiry: bool) -> Severity:
    if flying_after_expiry or days_until < 0 and scheduled:
        return Severity.CRITICAL
    if scheduled or days_until < 0:
        return Severity.HIGH
    return Severity.MEDIUM


def _evidence(
    cred: Credential,
    screening_start: date,
    lookahead_days: int,
    *,
    scheduled: bool,
    flying_after_expiry: bool,
    days_until: int | None = None,
    window_end: date | None = None,
) -> dict:
    return {
        "credential_type": cred.credential_type,
        "credential_detail": cred.credential_detail,
        "expiry_date": cred.expiry_date.isoformat() if cred.expiry_date else None,
        "screening_start": screening_start.isoformat(),
        "lookahead_days": lookahead_days,
        "days_until_expiry": days_until,
        "look_ahead_end": window_end.isoformat() if window_end else None,
        "scheduled_in_window": scheduled,
        "scheduled_on_or_after_expiry": flying_after_expiry,
    }


def _metadata(ctx: EvaluationContext, lookahead_days: int) -> RuleMetadata:
    return RuleMetadata(
        rule_id="CRED-EXPIRY-1",
        name="License, qualification, or medical expiry",
        framework_id=ctx.framework_id,
        ruleset_id=ctx.ruleset_id,
        ruleset_version=ctx.ruleset_version,
        rule_version="1.0.0",
        effective_date=date(2026, 1, 1),
        citation="Credential expiry screening (operator-configured look-ahead; not a substitute for the applicable licensing rule)",
        description="Flags credentials that expire within a configured window, with higher severity when the crew member is rostered to fly in that window.",
        parameters={"lookahead_days": lookahead_days},
        assumptions=ASSUMPTIONS,
        limitations=LIMITATIONS,
        exceptions_not_modeled=LIMITATIONS,
        evaluation_mode="full",
        required_inputs=frozenset({"crew_id", "expiry_date"}),
    )
