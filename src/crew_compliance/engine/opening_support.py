from __future__ import annotations

from crew_compliance.domain.enums import FindingKind
from crew_compliance.domain.opening import OpeningBalance
from crew_compliance.engine.findings import build_finding
from crew_compliance.engine.protocol import EvaluationContext
from crew_compliance.engine.severity import hour_exceedance_severity
from crew_compliance.domain.models import Finding, RuleMetadata


def apply_opening_hours(
    in_period: float,
    incomplete: bool,
    ctx: EvaluationContext,
    crew_id: str,
    window_type: str,
    metric: str | None,
) -> tuple[float | None, bool, dict]:
    """Combine roster-window hours with optional carry-over.

    When no opening-balance file was uploaded, V1 incomplete-lookback behaviour is unchanged.
    When a file was uploaded, a missing row is never treated as zero.
    Carry-over is added only if the roster does not fully cover the window.
    """
    book = ctx.opening_balances
    if book is None:
        return in_period, incomplete, {"opening_balance_status": "not_provided"}
    balance = book.get(crew_id, window_type, metric)
    if balance is None:
        return None, True, {
            "opening_balance_status": "missing",
            "opening_balance_window": window_type,
            "opening_balance_metric": metric,
        }
    extra = balance.hours if incomplete else 0.0
    status = "applied" if incomplete else "not_applied_window_complete_in_roster"
    return in_period + extra, False if incomplete else incomplete, _balance_evidence(balance, status)


def _balance_evidence(balance: OpeningBalance, status: str) -> dict:
    return {
        "opening_balance_status": status,
        "opening_balance_hours": balance.hours,
        "opening_balance_as_of": balance.as_of_date.isoformat(),
        "opening_balance_window": balance.window_type,
        "opening_balance_metric": balance.metric,
    }


def missing_opening_finding(
    metadata: RuleMetadata,
    *,
    crew_id: str,
    crew_name: str,
    window_type: str,
    limit: float,
) -> Finding:
    return build_finding(
        metadata,
        kind=FindingKind.INSUFFICIENT_DATA,
        crew_id=crew_id,
        crew_name=crew_name,
        severity=hour_exceedance_severity(0, limit),
        required=limit,
        explanation=(
            f"An opening-balances file was uploaded, but {crew_name} has no carry-over row "
            f"for window type '{window_type}'. Hours before the roster file cannot be assumed "
            "to be zero, so this rolling-window check cannot be evaluated."
        ),
        evidence={
            "opening_balance_status": "missing",
            "opening_balance_window": window_type,
        },
        extra_limitations=("Missing opening balance is never treated as zero.",),
    )
