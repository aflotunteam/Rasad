"""API, RBAC, audit va golden demo oqimi bo'yicha testlar."""

import io

API = "/api/v1"


def test_health_and_envelope(client):
    r = client.get(f"{API}/health")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True and body["error"] is None


def test_unknown_route_uses_error_envelope(client):
    r = client.get(f"{API}/no-such-route")
    assert r.status_code == 404
    assert r.json()["success"] is False and r.json()["error"]["code"] == "DATA_001"


def test_login_failure_is_audited(client, admin_h):
    r = client.post(f"{API}/auth/login", json={"username": "admin", "password": "xato"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "AUTH_001"
    audit = client.get(f"{API}/audit", params={"action": "auth.login_failed"}, headers=admin_h).json()["data"]
    assert audit["total"] >= 1


def test_requires_token(client):
    assert client.get(f"{API}/dashboard").status_code == 401


def test_dashboard_and_map_regions(client, admin_h):
    d = client.get(f"{API}/dashboard", headers=admin_h).json()["data"]
    assert len(d["regions"]) == 14  # AC-03
    assert d["kpis"]["analyzed"] == 5000
    ng = client.get(f"{API}/dashboard", params={"region": "NG"}, headers=admin_h).json()["data"]
    assert ng["filter"]["region"] == "NG"  # AC-04
    assert ng["kpis"]["analyzed"] < 5000
    assert ng["top_cases"][0]["code"] == "SUB-000125"


def test_rbac_matrix(client, auditor_h, manager_h, analyst_h):
    assert client.put(f"{API}/settings/thresholds", json={"low": 30, "high": 60}, headers=auditor_h).status_code == 403
    assert client.get(f"{API}/users", headers=analyst_h).status_code == 403
    assert client.get(f"{API}/settings", headers=manager_h).status_code == 403
    r = client.post(f"{API}/expert-decisions", headers=auditor_h,
                    json={"subject_code": "SUB-000125", "decision": "confirmed", "comment": "Auditor qaror qila olmaydi"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "AUTH_002"


def test_analyst_region_scope(client, analyst_h):
    subjects = client.get(f"{API}/subjects", params={"page_size": 100}, headers=analyst_h).json()["data"]
    assert {s["region_id"] for s in subjects["items"]} == {"NG"}
    # Boshqa hudud so'ralsa ham tahlilchi faqat o'z hududini ko'radi.
    other = client.get(f"{API}/subjects", params={"region": "TK"}, headers=analyst_h).json()["data"]["items"]
    assert {s["region_id"] for s in other} == {"NG"}
    d =client.get(f"{API}/dashboard", headers=analyst_h).json()["data"]
    assert all(r["restricted"] for r in d["regions"] if r["id"] != "NG")


def test_analyst_cannot_open_foreign_subject(client, admin_h, analyst_h):
    tk = client.get(f"{API}/subjects", params={"region": "TK", "page_size": 1}, headers=admin_h).json()["data"]
    code = tk["items"][0]["code"]
    r = client.get(f"{API}/subjects/{code}", headers=analyst_h)
    assert r.status_code == 403


def test_stir_masking(client, manager_h, analyst_h):
    m = client.get(f"{API}/subjects/SUB-000125", headers=manager_h).json()["data"]
    a = client.get(f"{API}/subjects/SUB-000125", headers=analyst_h).json()["data"]
    assert m["stir"].startswith("*** ***") and m["stir_masked"] is True
    assert a["stir"].isdigit() and a["stir_masked"] is False


def test_subject_filters_and_sorting(client, admin_h):
    d = client.get(f"{API}/subjects", params={"level": "high", "sort": "score", "order": "desc"},
                   headers=admin_h).json()["data"]
    scores = [i["score"] for i in d["items"]]
    assert scores == sorted(scores, reverse=True) and all(s >= 70 for s in scores)
    d = client.get(f"{API}/subjects", params={"dq": "low"}, headers=admin_h).json()["data"]
    assert all(i["dq_score"] < 60 for i in d["items"])
    d = client.get(f"{API}/subjects", params={"q": "125"}, headers=admin_h).json()["data"]
    assert d["items"][0]["code"] == "SUB-000125"


def test_golden_subject_endpoints(client, admin_h):
    base = f"{API}/subjects/SUB-000125"
    d = client.get(base, headers=admin_h).json()["data"]
    assert d["region"]["id"] == "NG" and 80 <= d["risk"]["score"] <= 84
    assert d["risk"]["confidence"] == "high" and d["risk"]["dq_score"] >= 80
    assert len(d["factors"]) >= 3
    ts = client.get(f"{base}/timeseries", headers=admin_h).json()["data"]
    assert len(ts["points"]) == 24 and any(p["outside"] for p in ts["points"][-3:])
    peers = client.get(f"{base}/peers", headers=admin_h).json()["data"]
    assert {g["group"] for g in peers["metrics"][0]["groups"]} == {"sector", "region", "size"}
    rel = client.get(f"{base}/relations", headers=admin_h).json()["data"]
    assert rel["summary"]["risky_direct"] >= 2 and any(e["risky_path"] for e in rel["edges"])
    exp = client.get(f"{base}/explanation", headers=admin_h).json()["data"]
    assert "81" in exp["paragraphs"][0] and exp["disclaimer"].startswith("Mazkur baho")


def test_expert_decision_flow(client, analyst_h, admin_h):
    bad = client.post(f"{API}/expert-decisions", headers=analyst_h,
                      json={"subject_code": "SUB-000125", "decision": "confirmed", "comment": "qisqa"})
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "DATA_002"
    r = client.post(f"{API}/expert-decisions", headers=analyst_h, json={
        "subject_code": "SUB-000125", "decision": "sent_review",
        "comment": "Aloqador subyektlar bo‘yicha qo‘shimcha tahlil talab etiladi."})
    assert r.status_code == 200  # AC-09
    timeline = client.get(f"{API}/subjects/SUB-000125/decisions", headers=analyst_h).json()["data"]
    assert timeline[0]["decision"] == "sent_review"
    audit = client.get(f"{API}/audit", params={"action": "decision.create"}, headers=admin_h).json()["data"]
    assert audit["items"][0]["object_id"] == "SUB-000125"  # AC-11
    detail = client.get(f"{API}/subjects/SUB-000125", headers=analyst_h).json()["data"]
    assert detail["risk"]["expert_status"] == "sent_review" and detail["alert"]["status"] == "in_review"


def test_alert_bulk_update(client, analyst_h):
    items = client.get(f"{API}/alerts", params={"status": "new"}, headers=analyst_h).json()["data"]["items"]
    assert items and all(a["region_id"] == "NG" for a in items)
    ids = [items[-1]["id"]]
    r = client.patch(f"{API}/alerts", json={"ids": ids, "status": "in_review"}, headers=analyst_h)
    assert r.status_code == 200 and r.json()["data"]["items"][0]["status"] == "in_review"


def test_reports_export(client, analyst_h):
    r = client.post(f"{API}/reports", json={"report_type": "subject", "params": {"code": "SUB-000125"}},
                    headers=analyst_h)
    assert r.status_code == 200
    rep = r.json()["data"]
    for key in ("number", "created_at", "period_start", "model_version", "data_version", "created_by"):
        assert rep["meta"][key]
    for fmt, magic in (("pdf", b"%PDF"), ("xlsx", b"PK"), ("csv", b"\xef\xbb\xbf")):
        f = client.get(f"{API}/reports/{rep['id']}/download", params={"format": fmt}, headers=analyst_h)
        assert f.status_code == 200 and f.content.startswith(magic)  # AC-10
    region = client.post(f"{API}/reports", json={"report_type": "region", "params": {"region": "NG"}},
                         headers=analyst_h)
    assert region.status_code == 200 and region.json()["data"]["content"]["summary"]["subjects"] > 0


def test_model_approval_rule(client, admin_h):
    models = client.get(f"{API}/models", headers=admin_h).json()["data"]
    testing = next(m for m in models if m["status"] == "TESTING")
    r = client.post(f"{API}/models/{testing['id']}/status", json={"status": "ACTIVE"}, headers=admin_h)
    assert r.status_code == 409 and r.json()["error"]["code"] == "MODEL_001"
    r = client.post(f"{API}/models/{testing['id']}/status", json={"status": "APPROVED"}, headers=admin_h)
    assert r.status_code == 200 and r.json()["data"]["approved_by"]
    r = client.post(f"{API}/models/{testing['id']}/status", json={"status": "ACTIVE"}, headers=admin_h)
    assert r.status_code == 409  # artefakt mavjud emas


def test_monitoring(client, admin_h):
    m = client.get(f"{API}/monitoring", headers=admin_h).json()["data"]
    assert len(m["series"]) == 6 and m["status_message"]


def test_thresholds_change_levels(client, admin_h):
    before = client.get(f"{API}/subjects", params={"level": "high"}, headers=admin_h).json()["data"]["total"]
    assert client.put(f"{API}/settings/thresholds", json={"low": 40, "high": 60}, headers=admin_h).status_code == 200
    after = client.get(f"{API}/subjects", params={"level": "high"}, headers=admin_h).json()["data"]["total"]
    assert after > before
    bad = client.put(f"{API}/settings/thresholds", json={"low": 70, "high": 60}, headers=admin_h)
    assert bad.status_code == 422
    client.put(f"{API}/settings/thresholds", json={"low": 40, "high": 70}, headers=admin_h)


def test_import_wizard(client, db, analyst_h):
    from sqlalchemy import select

    from app.models import Subject

    stir = db.scalar(select(Subject.stir).where(Subject.code == "SUB-000125"))
    csv = (
        "STIR;Davr;Aylanma;Operatsiyalar\n"
        f"{stir};2026-07-01;120,5;340\n"
        f"{stir};2026-07-01;120,5;340\n"
        "12345;2026-07-01;50;10\n"
        f"{stir};2030-01-01;-5;10\n"
    )
    up = client.post(f"{API}/imports", headers=analyst_h,
                     files={"file": ("namuna.csv", io.BytesIO(csv.encode()), "text/csv")})
    assert up.status_code == 200, up.text
    job = up.json()["data"]
    assert job["mapping"]["stir"] == "STIR" and job["mapping"]["turnover"] == "Aylanma"
    m = client.post(f"{API}/imports/{job['id']}/mapping", headers=analyst_h, json={"mapping": {
        "stir": "STIR", "period": "Davr", "turnover": "Aylanma", "tx_count": "Operatsiyalar"}})
    assert m.status_code == 200
    v = client.post(f"{API}/imports/{job['id']}/validate", headers=analyst_h).json()["data"]
    assert v["duplicates"] == 1 and v["rejected"] == 2 and v["accepted"] == 1
    c = client.post(f"{API}/imports/{job['id']}/confirm", headers=analyst_h)
    assert c.status_code == 200
    job_id = c.json()["data"]["job"]["id"]
    done = client.get(f"{API}/jobs/{job_id}", headers=analyst_h).json()["data"]
    assert done["status"] == "COMPLETED" and done["result"]["accepted"] == 1


def test_recompute_job_keeps_expert_status(client, admin_h):
    r = client.post(f"{API}/jobs/recompute", headers=admin_h)
    job = client.get(f"{API}/jobs/{r.json()['data']['id']}", headers=admin_h).json()["data"]
    assert job["status"] == "COMPLETED" and job["result"]["subjects"] == 5000
    d = client.get(f"{API}/subjects/SUB-000125", headers=admin_h).json()["data"]
    assert d["risk"]["expert_status"] == "sent_review"
