from __future__ import annotations

"""
Mailchimp subscriber utility — no Streamlit dependency.

Required environment / Streamlit secrets:
    MAILCHIMP_API_KEY   e.g. "abc123...us14"  (the server prefix is the suffix after the last dash)
    MAILCHIMP_LIST_ID   e.g. "a1b2c3d4e5"     (Audience ID from Mailchimp → Audience → Settings)

If either value is absent the helper returns SubscribeResult.SKIPPED so the app
can continue without blocking the user.
"""

import hashlib
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from enum import Enum


class SubscribeResult(str, Enum):
    OK = "ok"                   # newly subscribed
    ALREADY = "already"         # already a member — treated as success
    SKIPPED = "skipped"         # credentials not configured — gate stays open
    ERROR = "error"             # API error — do not hard-block the user


@dataclass(frozen=True)
class SubscribeResponse:
    result: SubscribeResult
    detail: str = ""


def subscribe(email: str, api_key: str | None = None, list_id: str | None = None) -> SubscribeResponse:
    """
    Add *email* to the Mailchimp audience identified by *list_id*.

    Falls back to MAILCHIMP_API_KEY / MAILCHIMP_LIST_ID environment variables.
    Returns SubscribeResult.SKIPPED when credentials are absent so callers can
    decide whether to gate or pass through.
    """
    api_key = api_key or os.getenv("MAILCHIMP_API_KEY") or _streamlit_secret("MAILCHIMP_API_KEY")
    list_id = list_id or os.getenv("MAILCHIMP_LIST_ID") or _streamlit_secret("MAILCHIMP_LIST_ID")

    if not api_key or not list_id:
        return SubscribeResponse(SubscribeResult.SKIPPED, "Mailchimp credentials not configured.")

    server = _server_prefix(api_key)
    member_hash = hashlib.md5(email.strip().lower().encode()).hexdigest()
    url = f"https://{server}.api.mailchimp.com/3.0/lists/{list_id}/members/{member_hash}"

    payload = json.dumps(
        {"email_address": email.strip().lower(), "status_if_new": "subscribed", "status": "subscribed"}
    ).encode()

    req = urllib.request.Request(
        url,
        data=payload,
        method="PUT",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {_basic_auth(api_key)}",
            "User-Agent": "CrewComplianceChecker/2.0",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            body = json.loads(resp.read())
            if body.get("status") in ("subscribed", "pending"):
                return SubscribeResponse(SubscribeResult.OK)
            return SubscribeResponse(SubscribeResult.ALREADY)
    except urllib.error.HTTPError as exc:
        body = {}
        try:
            body = json.loads(exc.read())
        except Exception:
            pass
        title = body.get("title", "")
        if "Member Exists" in title or exc.code == 400 and "already a list member" in body.get("detail", "").lower():
            return SubscribeResponse(SubscribeResult.ALREADY)
        return SubscribeResponse(SubscribeResult.ERROR, f"Mailchimp {exc.code}: {title}")
    except Exception as exc:  # network timeout, DNS, etc.
        return SubscribeResponse(SubscribeResult.ERROR, str(exc))


def configured() -> bool:
    """Return True if both credentials are present in env or Streamlit secrets."""
    key = os.getenv("MAILCHIMP_API_KEY") or _streamlit_secret("MAILCHIMP_API_KEY")
    lid = os.getenv("MAILCHIMP_LIST_ID") or _streamlit_secret("MAILCHIMP_LIST_ID")
    return bool(key and lid)


# ── helpers ──────────────────────────────────────────────────────────────────

def _server_prefix(api_key: str) -> str:
    """Extract the server prefix from an API key like 'abc123abc-us14'."""
    return api_key.split("-")[-1]


def _basic_auth(api_key: str) -> str:
    import base64
    return base64.b64encode(f"user:{api_key}".encode()).decode()


def _streamlit_secret(key: str) -> str | None:
    """Read from st.secrets without hard-importing Streamlit (optional dep)."""
    try:
        import streamlit as st  # noqa: PLC0415
        return st.secrets.get(key)
    except Exception:
        return None
