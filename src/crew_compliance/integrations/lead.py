from __future__ import annotations

"""
Minimal lead capture for the compliance checker lead magnet.

Keep fields intentionally short: email required; role and future-product
interest optional. Never store roster contents — only lightweight context.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from crew_compliance.integrations.mailchimp import SubscribeResult, subscribe as mailchimp_subscribe
from crew_compliance.integrations import n8n as n8n_client

SOURCE = "crew-compliance-checker"

ROLE_OPTIONS = (
    "Crew Scheduler / Planner",
    "Crew Controller",
    "Flight Operations",
    "Operations Manager",
    "Aviation Consultant",
    "Airline Management",
    "Other",
)

INTEREST_OPTIONS = (
    "Crew scheduling",
    "Roster optimization",
    "Compliance",
    "Disruption management",
    "Other",
)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class LeadResult(str, Enum):
    OK = "ok"
    INVALID = "invalid"
    PARTIAL = "partial"  # stored somewhere, at least one backend failed
    SKIPPED = "skipped"  # no backends configured — still unlock report in UI


@dataclass(frozen=True)
class LeadPayload:
    email: str
    role: str | None = None
    interest: str | None = None
    framework_id: str | None = None
    sample_used: bool = False
    report_requested: bool = True
    source: str = SOURCE


@dataclass(frozen=True)
class LeadResponse:
    result: LeadResult
    detail: str = ""
    mailchimp: str = ""
    n8n: str = ""


def validate_email(email: str) -> bool:
    return bool(email and _EMAIL_RE.match(email.strip()))


def submit_lead(payload: LeadPayload) -> LeadResponse:
    """
    Persist a lead via Mailchimp and/or n8n.

    External failures must not prevent report delivery — callers unlock the
    report regardless of LeadResult except INVALID.
    """
    email = payload.email.strip().lower()
    if not validate_email(email):
        return LeadResponse(LeadResult.INVALID, "Please enter a valid email address.")

    merge_fields = {
        key: value
        for key, value in {
            "ROLE": (payload.role or "")[:100],
            "INTEREST": (payload.interest or "")[:100],
            "FRAMEWORK": (payload.framework_id or "")[:50],
            "SAMPLE": "yes" if payload.sample_used else "no",
            "REPORT": "yes" if payload.report_requested else "no",
            "SOURCE": payload.source,
        }.items()
        if value
    }

    mc = mailchimp_subscribe(email, merge_fields=merge_fields)
    webhook_body = {
        "email": email,
        "role": payload.role,
        "interest": payload.interest,
        "framework": payload.framework_id,
        "sample_used": payload.sample_used,
        "report_requested": payload.report_requested,
        "source": payload.source,
        "optimizer_interest": payload.interest in {"Crew scheduling", "Roster optimization"} if payload.interest else False,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    nw = n8n_client.post_lead(webhook_body)

    mc_status = mc.result.value
    n8n_status = nw.result.value

    if mc.result == SubscribeResult.SKIPPED and nw.result == n8n_client.WebhookResult.SKIPPED:
        return LeadResponse(
            LeadResult.SKIPPED,
            "Email list is not connected yet — your report is still unlocked for this session.",
            mailchimp=mc_status,
            n8n=n8n_status,
        )

    if mc.result == SubscribeResult.ERROR and nw.result == n8n_client.WebhookResult.ERROR:
        return LeadResponse(
            LeadResult.PARTIAL,
            "We could not save your email right now. Your report is still available.",
            mailchimp=mc_status,
            n8n=n8n_status,
        )

    if mc.result == SubscribeResult.ERROR or nw.result == n8n_client.WebhookResult.ERROR:
        return LeadResponse(
            LeadResult.PARTIAL,
            "Your email was saved, but one update step failed. Your report is still available.",
            mailchimp=mc_status,
            n8n=n8n_status,
        )

    return LeadResponse(LeadResult.OK, "Report unlocked for this session.", mailchimp=mc_status, n8n=n8n_status)
