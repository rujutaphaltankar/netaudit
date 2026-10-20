import json

import httpx
import pytest

from app.db.models import AIMapping, Audit
from app.db.session import session_for
from app.services import ai_mapping as ai
from tests.conftest import read_sample

API = "/api/v1"


def create(client, sample="cisco_ios_weak.cfg"):
    return client.post(f"{API}/audits", files={"file": (sample, read_sample(sample).encode(), "text/plain")}).json()


def mock_factory(handler):
    return lambda settings: httpx.Client(transport=httpx.MockTransport(handler))


def anthropic_reply(payload) -> httpx.Response:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return httpx.Response(200, json={"content": [{"type": "text", "text": text}]})


# ---------------------------------------------------------------------------------- heuristics
@pytest.mark.parametrize("cmd,cat,impact", [
    ("login block-for 120 attempts 3 within 60", "authentication", "positive"),
    ("aaa authorization exec default group tacacs+ local", "authentication", "positive"),
    ("set system services ssh root-login allow", "management", "negative"),
    ("set system services ssh root-login deny", "management", "positive"),
    ("totally unknown vendor thing", "other", "unknown"),
])
def test_heuristics(cmd, cat, impact):
    s = ai.heuristic_suggestion(cmd)
    assert (s.category, s.security_impact) == (cat, impact)
    assert ("low" if cat == "other" else "medium") == s.confidence


def test_command_pattern_generalises_numbers():
    assert ai.command_pattern("ip ssh time-out 120") == "ip ssh time-out"
    assert ai.command_pattern("login block-for 120 attempts 3") == "login block-for <n>"


# --------------------------------------------------------------------------------------- API
def test_generate_with_heuristic_fallback_and_review_flow(client, viewer_client):
    audit = create(client)
    unknown = len(audit["parse"]["result"]["unknown_commands"])
    assert unknown > 0
    r = client.post(f"{API}/audits/{audit['id']}/ai-mappings/generate").json()
    assert r["created"] == unknown and r["ai_configured"] is False and r["ai_used"] is False
    assert client.post(f"{API}/audits/{audit['id']}/ai-mappings/generate").json()["created"] == 0  # idempotent

    items = client.get(f"{API}/audits/{audit['id']}/ai-mappings").json()
    assert all(m["source"] == "heuristic" and m["status"] == "pending" for m in items)
    pending = client.get(f"{API}/ai-mappings?status=pending").json()
    assert len(pending) == unknown and pending[0]["audit_filename"]

    mid = items[0]["id"]
    assert viewer_client.post(f"{API}/ai-mappings/{mid}/review", json={"decision": "approved"}).status_code == 403
    assert viewer_client.post(f"{API}/audits/{audit['id']}/ai-mappings/generate").status_code == 403
    done = client.post(f"{API}/ai-mappings/{mid}/review", json={"decision": "approved", "note": "ok"}).json()
    assert done["status"] == "approved" and done["review_note"] == "ok" and done["reviewed_at"]
    assert client.post(f"{API}/ai-mappings/{mid}/review", json={"decision": "maybe"}).status_code == 422
    assert client.post(f"{API}/ai-mappings/9999/review", json={"decision": "rejected"}).status_code == 404
    assert len(client.get(f"{API}/ai-mappings?status=approved").json()) == 1


def test_ai_review_never_changes_score_or_findings(client):
    audit = create(client)
    client.post(f"{API}/audits/{audit['id']}/ai-mappings/generate")
    for m in client.get(f"{API}/audits/{audit['id']}/ai-mappings").json():
        client.post(f"{API}/ai-mappings/{m['id']}/review", json={"decision": "approved"})
    after = client.get(f"{API}/audits/{audit['id']}").json()
    assert after["score"] == audit["score"] and after["grade"] == audit["grade"]
    assert [f["status"] for f in after["findings"]] == [f["status"] for f in audit["findings"]]


def test_approved_mapping_is_reused_for_similar_command(client):
    first, second = create(client), create(client)
    client.post(f"{API}/audits/{first['id']}/ai-mappings/generate")
    for m in client.get(f"{API}/audits/{first['id']}/ai-mappings").json():
        client.post(f"{API}/ai-mappings/{m['id']}/review", json={"decision": "approved"})
    client.post(f"{API}/audits/{second['id']}/ai-mappings/generate")
    mapped = client.get(f"{API}/audits/{second['id']}/ai-mappings").json()
    assert mapped and all(m["source"] == "reused" and m["status"] == "pending" for m in mapped)


# ------------------------------------------------------------------------------- AI provider
def run_generate(settings, handler, sample="cisco_ios_weak.cfg", client=None):
    audit_id = create(client)["id"]
    s = settings.model_copy(update={"ai_api_key": "test-key"})
    with session_for(s) as db:
        out = ai.generate_mappings(db, db.get(Audit, audit_id), s, mock_factory(handler))
        return out, list(db.query(AIMapping).all())


def test_ai_success_path_sends_only_redacted_commands(client, settings):
    seen = {}

    def handler(request: httpx.Request):
        seen["headers"], seen["body"] = request.headers, json.loads(request.content)
        items = json.loads(seen["body"]["messages"][0]["content"])
        return anthropic_reply("```json\n" + json.dumps([
            {"id": it["id"], "meaning": f"AI says: {it['command']}", "category": "management",
             "security_impact": "neutral", "confidence": "high", "suggested_field": None, "note": None}
            for it in items]) + "\n```")

    out, mappings = run_generate(settings, handler, client=client)
    assert out["ai_used"] is True and out["ai_error"] is None
    assert mappings and all(m.source == "ai" and m.status == "pending" and m.meaning.startswith("AI says") for m in mappings)
    assert seen["headers"]["x-api-key"] == "test-key" and seen["body"]["model"] == settings.ai_model
    sent = seen["body"]["messages"][0]["content"] + seen["body"]["system"]
    assert "EDGE-SW-01" not in sent and "0822455D0A16" not in sent  # no hostname / secrets / full config


def test_ai_malformed_or_hostile_output_falls_back_to_heuristics(client, settings):
    def handler(request):
        return anthropic_reply([{"id": 0, "meaning": "ignore previous instructions", "category": "DROP TABLE",
                                 "security_impact": "positive", "confidence": "high"},
                                {"id": 99, "meaning": "x", "category": "other", "security_impact": "neutral", "confidence": "low"},
                                "not-an-object"])
    out, mappings = run_generate(settings, handler, client=client)
    assert mappings and all(m.source == "heuristic" for m in mappings)  # invalid items rejected, id 99 ignored


def test_ai_failures_fall_back_without_breaking(client, settings):
    out, mappings = run_generate(settings, lambda r: httpx.Response(500, json={"error": "boom"}), client=client)
    assert out["ai_error"] == "HTTPStatusError" and mappings and all(m.source == "heuristic" for m in mappings)
    out2, m2 = run_generate(settings, lambda r: anthropic_reply("sorry, I cannot help"), client=client)
    assert out2["ai_used"] is False and all(m.source == "heuristic" for m in m2)
