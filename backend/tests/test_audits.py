import json

from sqlalchemy import func, select

from app.db.models import Audit, Finding
from app.db.session import session_for
from tests.conftest import read_sample

API = "/api/v1"


def create(client, sample="cisco_ios_weak.cfg", name=None, **form):
    files = {"file": (name or sample, read_sample(sample).encode(), "text/plain")}
    return client.post(f"{API}/audits", files=files, data=form)


def test_create_and_fetch_audit(client):
    r = create(client)
    assert r.status_code == 201
    a = r.json()
    assert a["vendor"] == "cisco_ios" and a["hostname"] == "EDGE-SW-01" and a["grade"] == "F"
    assert a["passed"] + a["failed"] + a["unknown"] + a["not_applicable"] == 19 == len(a["findings"])
    assert a["findings"][0]["status"] == "fail" and a["findings"][0]["severity"] == "critical"  # worst first
    assert a["created_by"] == "admin" and a["parse"]["result"]["config"]["hostname"]["value"] == "EDGE-SW-01"
    again = client.get(f"{API}/audits/{a['id']}").json()
    assert again["score"] == a["score"] and len(again["findings"]) == 19


def test_stored_audit_contains_no_secrets(client, settings):
    create(client)
    with session_for(settings) as db:
        blob = json.dumps(db.scalars(select(Audit)).one().parse_response) + json.dumps(
            [f.evidence for f in db.scalars(select(Finding))])
    for secret in ("0822455D0A16", "070C285F4D06", "hx5rVt7rPNoS4wqbXKX7m0", "shouldNotBeParsed"):
        assert secret not in blob


def test_unsupported_and_invalid_uploads_are_rejected(client):
    assert create(client, "arista_eos_unsupported.cfg").status_code == 422
    r = client.post(f"{API}/audits", files={"file": ("x.exe", b"hostname R1", "text/plain")})
    assert r.status_code == 415
    assert client.get(f"{API}/audits").json()["total"] == 0


def test_list_filter_search_paginate(client):
    create(client, "cisco_ios_weak.cfg", name="edge.cfg")
    create(client, "juniper_junos_weak.set")
    create(client, "cisco_ios_hardened.cfg", name="core.cfg")
    assert client.get(f"{API}/audits").json()["total"] == 3
    assert [i["filename"] for i in client.get(f"{API}/audits").json()["items"]][0] == "core.cfg"  # newest first
    assert client.get(f"{API}/audits?vendor=juniper_junos").json()["total"] == 1
    assert client.get(f"{API}/audits?q=EDGE-SW").json()["total"] == 1  # hostname search
    page = client.get(f"{API}/audits?page=2&page_size=2").json()
    assert len(page["items"]) == 1 and page["total"] == 3
    assert client.get(f"{API}/audits?page=0").status_code == 422


def test_get_missing_audit_and_delete_cascades(client, viewer_client, settings):
    assert client.get(f"{API}/audits/999").json()["error"]["code"] == "audit_not_found"
    aid = create(client).json()["id"]
    assert viewer_client.delete(f"{API}/audits/{aid}").status_code == 403
    assert client.delete(f"{API}/audits/{aid}").status_code == 204
    with session_for(settings) as db:
        assert db.scalar(select(func.count()).select_from(Finding)) == 0
    assert client.get(f"{API}/audits/{aid}").status_code == 404


def test_dashboard_stats(client):
    assert client.get(f"{API}/audits/stats").json()["total_audits"] == 0
    create(client, "cisco_ios_weak.cfg")
    create(client, "cisco_ios_hardened.cfg")
    s = client.get(f"{API}/audits/stats").json()
    assert s["total_audits"] == 2 and s["by_vendor"] == {"cisco_ios": 2}
    assert set(s["by_grade"]) == {"F", "A"} and 10 < s["average_score"] < 90
    assert s["top_failing_rules"][0]["count"] >= 1 and len(s["score_trend"]) == 2 and len(s["recent"]) == 2


def test_compare_audits(client):
    weak = create(client, "cisco_ios_weak.cfg").json()
    hard = create(client, "cisco_ios_hardened.cfg").json()
    c = client.get(f"{API}/audits/compare?base={weak['id']}&target={hard['id']}").json()
    assert c["score_delta"] > 50
    by_rule = {x["rule_id"]: x for x in c["changes"]}
    assert by_rule["NA-MGMT-001"]["change"] == "improved"
    assert client.get(f"{API}/audits/compare?base={hard['id']}&target={weak['id']}").json()["changes"][0]["change"] == "regressed"
    assert client.get(f"{API}/audits/compare?base=1&target=999").status_code == 404


def test_rules_endpoint(viewer_client):
    body = viewer_client.get(f"{API}/rules").json()
    assert len(body["rules"]) >= 15 and "does NOT demonstrate compliance" in body["disclaimer"]


def test_pdf_report(client, viewer_client):
    aid = create(client).json()["id"]
    r = viewer_client.get(f"{API}/audits/{aid}/report.pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF") and len(r.content) > 4000
    assert f"netaudit-report-{aid}.pdf" in r.headers["content-disposition"]
    assert client.get(f"{API}/audits/999/report.pdf").status_code == 404


def test_pdf_text_content(client):
    import io
    import pytest
    pypdf = pytest.importorskip("pypdf")
    aid = create(client).json()["id"]
    text = "".join(p.extract_text() for p in pypdf.PdfReader(io.BytesIO(client.get(f"{API}/audits/{aid}/report.pdf").content)).pages)
    for needle in ("Network Security Compliance Report", "EDGE-SW-01", "NA-MGMT-001", "Recommended fix", "Limitations and disclaimer"):
        assert needle in text
    assert "0822455D0A16" not in text


def test_pdf_survives_hostile_characters(client, settings):
    """Evidence containing markup / non-latin text must not break report generation."""
    from app.services.report_pdf import build_report
    aid = create(client).json()["id"]
    with session_for(settings) as db:
        audit = db.get(Audit, aid)
        audit.findings[0].message = "<b>bad & <unclosed> \u4e2d\u6587"
        audit.filename = "x<y>&z.cfg"
        assert build_report(audit).startswith(b"%PDF")
