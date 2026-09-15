from __future__ import annotations

from crew_compliance.integrations.mailchimp import (
    SubscribeResult,
    _basic_auth,
    _server_prefix,
    configured,
    subscribe,
)


def test_server_prefix_extracted_from_api_key():
    # No hex block — avoids triggering secret-scanning patterns.
    assert _server_prefix("test-key-server3") == "server3"


def test_basic_auth_format():
    token = _basic_auth("mykey")
    import base64
    decoded = base64.b64decode(token).decode()
    assert decoded == "user:mykey"


def test_subscribe_skipped_when_no_credentials():
    result = subscribe("pilot@example.com", api_key=None, list_id=None)
    assert result.result == SubscribeResult.SKIPPED


def test_configured_returns_false_when_missing(monkeypatch):
    monkeypatch.delenv("MAILCHIMP_API_KEY", raising=False)
    monkeypatch.delenv("MAILCHIMP_LIST_ID", raising=False)
    assert not configured()
