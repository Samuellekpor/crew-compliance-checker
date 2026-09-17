from __future__ import annotations

"""
Optional n8n webhook for lead enrichment / report delivery.

Set N8N_LEAD_WEBHOOK_URL in the environment or Streamlit secrets.
Absent or failing webhooks never block the user — Mailchimp (or local
dev mode) remains the primary capture path.

Only HTTPS URLs to public hosts are accepted to reduce accidental SSRF
from a misconfigured secret (localhost, link-local, metadata hosts).
"""

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse


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


def url_allowed(url: str) -> bool:
    """Return True only for https URLs that are not obvious local/metadata targets."""
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return False
    if parsed.scheme != "https":
        return False
    host = (parsed.hostname or "").lower()
    if not host:
        return False
    if host in {"localhost", "127.0.0.1", "::1", "0.0.0.0", "metadata.google.internal"}:
        return False
    if host.endswith(".local") or host.endswith(".internal"):
        return False
    if host.startswith("169.254.") or host.startswith("10.") or host.startswith("192.168."):
        return False
    # 172.16.0.0 – 172.31.255.255
    if host.startswith("172."):
        parts = host.split(".")
        if len(parts) == 4 and parts[1].isdigit() and 16 <= int(parts[1]) <= 31:
            return False
    return True


def post_lead(payload: dict, webhook_url: str | None = None, timeout: float = 5.0) -> WebhookResponse:
    """POST lead metadata to n8n. Fire-and-forget with a short timeout."""
    url = webhook_url or os.getenv("N8N_LEAD_WEBHOOK_URL") or _streamlit_secret("N8N_LEAD_WEBHOOK_URL")
    if not url:
        return WebhookResponse(WebhookResult.SKIPPED, "N8N_LEAD_WEBHOOK_URL not configured.")
    if not url_allowed(url):
        return WebhookResponse(
            WebhookResult.ERROR,
            "Webhook URL must be HTTPS and must not target localhost or private networks.",
        )

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
