from __future__ import annotations

"""
Optional n8n webhook for lead enrichment / report delivery.

Set N8N_LEAD_WEBHOOK_URL in the environment or Streamlit secrets.
Absent or failing webhooks never block the user — Mailchimp (or local
dev mode) remains the primary capture path.
"""

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from enum import Enum


class WebhookResult(str, Enum):
    OK = "ok"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass(frozen=True)
class WebhookResponse:
    result: WebhookResult
    detail: str = ""


def configured(webhook_url: str | None = None) -> bool:
    return bool(webhook_url or os.getenv("N8N_LEAD_WEBHOOK_URL") or _streamlit_secret("N8N_LEAD_WEBHOOK_URL"))


def post_lead(payload: dict, webhook_url: str | None = None, timeout: float = 5.0) -> WebhookResponse:
    """POST lead metadata to n8n. Fire-and-forget with a short timeout."""
    url = webhook_url or os.getenv("N8N_LEAD_WEBHOOK_URL") or _streamlit_secret("N8N_LEAD_WEBHOOK_URL")
    if not url:
        return WebhookResponse(WebhookResult.SKIPPED, "N8N_LEAD_WEBHOOK_URL not configured.")

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": "CrewComplianceChecker/2.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if 200 <= resp.status < 300:
                return WebhookResponse(WebhookResult.OK)
            return WebhookResponse(WebhookResult.ERROR, f"HTTP {resp.status}")
    except urllib.error.HTTPError as exc:
        return WebhookResponse(WebhookResult.ERROR, f"HTTP {exc.code}")
    except Exception as exc:
        return WebhookResponse(WebhookResult.ERROR, str(exc))


def _streamlit_secret(key: str) -> str | None:
    try:
        import streamlit as st  # noqa: PLC0415

        return st.secrets.get(key)
    except Exception:
        return None
