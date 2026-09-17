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


def test_subscribe_skipped_when_no_credentials(monkeypatch):
    # Ignore local .streamlit/secrets.toml so the SKIPPED path stays testable.
    monkeypatch.delenv("MAILCHIMP_API_KEY", raising=False)
    monkeypatch.delenv("MAILCHIMP_LIST_ID", raising=False)
    monkeypatch.setattr(
        "crew_compliance.integrations.mailchimp._streamlit_secret",
        lambda _key: None,
    )
    result = subscribe("pilot@example.com", api_key=None, list_id=None)
    assert result.result == SubscribeResult.SKIPPED


def test_configured_returns_false_when_missing(monkeypatch):
    monkeypatch.delenv("MAILCHIMP_API_KEY", raising=False)
    monkeypatch.delenv("MAILCHIMP_LIST_ID", raising=False)
    monkeypatch.setattr(
        "crew_compliance.integrations.mailchimp._streamlit_secret",
        lambda _key: None,
    )
    assert not configured()


def test_subscribe_includes_merge_fields_in_payload(monkeypatch):
    import json

    captured = {}

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"status":"subscribed"}'

    def fake_urlopen(req, timeout=6):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode())
        return _Resp()

    monkeypatch.setattr(
        "crew_compliance.integrations.mailchimp.urllib.request.urlopen",
        fake_urlopen,
    )
    result = subscribe(
        "ops@example.com",
        api_key="test-key-server3",
        list_id="list123",
        merge_fields={"ROLE": "Crew Controller", "FRAMEWORK": "easa", "SAMPLE": "yes", "EMPTY": ""},
    )
    assert result.result == SubscribeResult.OK
    assert captured["body"]["merge_fields"]["ROLE"] == "Crew Controller"
    assert captured["body"]["merge_fields"]["FRAMEWORK"] == "easa"
    assert "EMPTY" not in captured["body"]["merge_fields"]
