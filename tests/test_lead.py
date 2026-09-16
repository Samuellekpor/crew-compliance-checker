from __future__ import annotations

from crew_compliance.integrations.lead import (
    LeadPayload,
    LeadResult,
    submit_lead,
    validate_email,
)
from crew_compliance.integrations.mailchimp import SubscribeResponse, SubscribeResult
from crew_compliance.integrations.n8n import WebhookResponse, WebhookResult, post_lead


def test_validate_email_accepts_and_rejects():
    assert validate_email("ops@airline.com")
    assert validate_email("  a.b+c@carrier.co.uk ")
    assert not validate_email("")
    assert not validate_email("not-an-email")
    assert not validate_email("@missing.local")


def test_submit_lead_invalid_email():
    response = submit_lead(LeadPayload(email="bad"))
    assert response.result == LeadResult.INVALID


def test_submit_lead_skipped_when_no_backends(monkeypatch):
    monkeypatch.setattr(
        "crew_compliance.integrations.lead.mailchimp_subscribe",
        lambda *a, **k: SubscribeResponse(SubscribeResult.SKIPPED),
    )
    monkeypatch.setattr(
        "crew_compliance.integrations.lead.n8n_client.post_lead",
        lambda *a, **k: WebhookResponse(WebhookResult.SKIPPED),
    )
    response = submit_lead(
        LeadPayload(email="planner@example.com", role="Crew Scheduler / Planner", framework_id="easa")
    )
    assert response.result == LeadResult.SKIPPED


def test_submit_lead_ok_path(monkeypatch):
    captured = {}

    def fake_mc(email, merge_fields=None, **_):
        captured["email"] = email
        captured["merge"] = merge_fields
        return SubscribeResponse(SubscribeResult.OK)

    def fake_n8n(payload, **_):
        captured["n8n"] = payload
        return WebhookResponse(WebhookResult.OK)

    monkeypatch.setattr("crew_compliance.integrations.lead.mailchimp_subscribe", fake_mc)
    monkeypatch.setattr("crew_compliance.integrations.lead.n8n_client.post_lead", fake_n8n)

    response = submit_lead(
        LeadPayload(
            email="Ops@Airline.COM",
            role="Flight Operations",
            interest="Roster optimization",
            framework_id="faa_part_117",
            sample_used=True,
        )
    )
    assert response.result == LeadResult.OK
    assert captured["email"] == "ops@airline.com"
    assert captured["merge"]["FRAMEWORK"] == "faa_part_117"
    assert captured["merge"]["SAMPLE"] == "yes"
    assert captured["merge"]["INTEREST"] == "Roster optimization"
    assert captured["n8n"]["optimizer_interest"] is True
    assert captured["n8n"]["source"] == "crew-compliance-checker"


def test_submit_lead_partial_when_mailchimp_fails(monkeypatch):
    monkeypatch.setattr(
        "crew_compliance.integrations.lead.mailchimp_subscribe",
        lambda *a, **k: SubscribeResponse(SubscribeResult.ERROR, "down"),
    )
    monkeypatch.setattr(
        "crew_compliance.integrations.lead.n8n_client.post_lead",
        lambda *a, **k: WebhookResponse(WebhookResult.OK),
    )
    response = submit_lead(LeadPayload(email="ok@example.com"))
    assert response.result == LeadResult.PARTIAL


def test_submit_lead_optional_role_and_interest_blank(monkeypatch):
    captured = {}

    def fake_mc(email, merge_fields=None, **_):
        captured["merge"] = merge_fields
        return SubscribeResponse(SubscribeResult.OK)

    monkeypatch.setattr("crew_compliance.integrations.lead.mailchimp_subscribe", fake_mc)
    monkeypatch.setattr(
        "crew_compliance.integrations.lead.n8n_client.post_lead",
        lambda *a, **k: WebhookResponse(WebhookResult.SKIPPED),
    )
    response = submit_lead(LeadPayload(email="ok@example.com", role=None, interest=None))
    assert response.result == LeadResult.OK
    assert "ROLE" not in captured["merge"]
    assert "INTEREST" not in captured["merge"]
    assert captured["merge"]["REPORT"] == "yes"
    assert captured["merge"]["SAMPLE"] == "no"

def test_n8n_post_skipped_without_url(monkeypatch):
    monkeypatch.delenv("N8N_LEAD_WEBHOOK_URL", raising=False)
    result = post_lead({"email": "a@b.com"}, webhook_url=None)
    assert result.result == WebhookResult.SKIPPED


def test_n8n_post_ok(monkeypatch):
    class _Resp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b"{}"

    monkeypatch.setattr(
        "crew_compliance.integrations.n8n.urllib.request.urlopen",
        lambda *a, **k: _Resp(),
    )
    result = post_lead({"email": "a@b.com"}, webhook_url="https://example.com/hook")
    assert result.result == WebhookResult.OK


def test_n8n_post_error_is_graceful(monkeypatch):
    def boom(*a, **k):
        raise TimeoutError("timeout")

    monkeypatch.setattr("crew_compliance.integrations.n8n.urllib.request.urlopen", boom)
    result = post_lead({"email": "a@b.com"}, webhook_url="https://example.com/hook")
    assert result.result == WebhookResult.ERROR
