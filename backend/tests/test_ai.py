"""SI xizmati testlari. Haqiqiy Anthropic API chaqirilmaydi: model javobi soxtalashtiriladi."""

import pytest

from app.ai import explainer, guard

API = "/api/v1"
GOLDEN = "SUB-000125"


# --- guard: raqam va mazmun tekshiruvi -------------------------------------

def test_guard_accepts_numbers_from_input():
    allowed = guard.allowed_numbers([81.7, 90.3, -65.8, -6.7, 15.9, 32.1])
    text = ["SUB-000125 uchun baho 81,7/100, sifat 90,3. Aylanma −65,8% (kutilgan −6,7% … 15,9%), ta’siri +32,1 ball. R01 va R05 signallari; 3 ta omil."]
    assert guard.check(text, allowed) is None


def test_guard_rejects_invented_number():
    allowed = guard.allowed_numbers([81.7])
    problem = guard.check(["Baho 81,7. Hududda 1 250 ta shunday holat bor."], allowed)
    assert problem and "250" in problem


def test_guard_rejects_rounded_number():
    assert guard.check(["Xavf bahosi 82 ball."], guard.allowed_numbers([81.7])) is not None


def test_guard_rejects_accusation_and_cyrillic():
    allowed = guard.allowed_numbers([81.7])
    assert "aybdor" in guard.check(["Subyekt aybdor deb topildi."], allowed)
    assert guard.check(["Хавф бахоси юқори."], allowed) == "Izohda kirill yozuvi bor"


def test_guard_ignores_identifiers():
    assert guard.check(["SUB-000125, R08, model rasad-risk-1.0.0, davr 2026-08."], set()) is None


# --- xizmat oqimi ----------------------------------------------------------

@pytest.fixture()
def ai_key():
    from app.core.config import get_settings

    s = get_settings()
    old = s.anthropic_api_key
    s.anthropic_api_key = "test-key-not-real"
    yield s
    s.anthropic_api_key = old


def _faithful_reply(payload: dict) -> tuple[list[str], dict]:
    """Faqat kiruvchi ma'lumotdagi qiymatlardan foydalanadigan "to‘g‘ri" javob."""
    f = payload["factors"][0]
    paragraphs = [
        f"{payload['subject_code']} subyekti uchun analitik xavf bahosi {payload['risk_score']}, ishonch darajasi {payload['confidence_level']}.",
        f"Asosiy omil — {f['factor'].lower()}: joriy qiymat {f['current_value']}, kutilgan oraliq {f['expected_range']}, ta’siri {f['impact_points']} ball.",
        "Holat qo‘shimcha ekspert tahlilini talab qiladi. Yakuniy qarorni vakolatli ekspert qabul qiladi.",
    ]
    return paragraphs, {"request_id": "req_test", "input_tokens": 900, "output_tokens": 250, "stop_reason": "end_turn"}


def test_without_key_uses_template(client, analyst_h):
    d = client.get(f"{API}/subjects/{GOLDEN}/explanation", headers=analyst_h).json()["data"]
    assert d["source"] == "template" and d["fallback_code"] == "not_configured"
    assert d["paragraphs"] and d["disclaimer"].startswith("Mazkur baho")


def test_ai_explanation_is_generated_validated_and_cached(client, analyst_h, admin_h, ai_key, monkeypatch):
    calls = []

    def fake(payload):
        calls.append(payload)
        return _faithful_reply(payload)

    monkeypatch.setattr(explainer, "_call_model", fake)
    d = client.get(f"{API}/subjects/{GOLDEN}/explanation", headers=analyst_h).json()["data"]
    assert d["source"] == "ai" and d["model"] == "claude-sonnet-5" and d["model_label"] == "Claude Sonnet 5"
    assert "81,7" in d["paragraphs"][0] and len(calls) == 1

    again = client.get(f"{API}/subjects/{GOLDEN}/explanation", headers=analyst_h).json()["data"]
    assert again["source"] == "ai" and len(calls) == 1  # keshdan

    forced = client.post(f"{API}/subjects/{GOLDEN}/explanation/regenerate", headers=analyst_h).json()["data"]
    assert forced["source"] == "ai" and len(calls) == 2

    audit = client.get(f"{API}/audit", params={"action": "ai.explanation"}, headers=admin_h).json()["data"]
    assert audit["total"] >= 2

    status = client.get(f"{API}/ai/status", headers=admin_h).json()["data"]
    assert status["configured"] and status["mode"] == "ai"
    assert status["totals"]["ok"] >= 2 and status["totals"]["input_tokens"] >= 1800


def test_report_reuses_cached_ai_text(client, analyst_h, ai_key, monkeypatch):
    monkeypatch.setattr(explainer, "_call_model", _faithful_reply)
    client.get(f"{API}/subjects/{GOLDEN}/explanation", headers=analyst_h)

    def must_not_call(payload):
        raise AssertionError("hisobot modelni chaqirmasligi kerak")

    monkeypatch.setattr(explainer, "_call_model", must_not_call)
    rep = client.post(f"{API}/reports", json={"report_type": "subject", "params": {"code": GOLDEN}}, headers=analyst_h)
    assert rep.json()["data"]["content"]["explanation"]["source"] == "ai"


def test_invented_number_falls_back_to_template(client, admin_h, ai_key, monkeypatch, db):
    from sqlalchemy import select

    from app.models import AiExplanation, Subject

    calls = []

    def lying(payload):
        calls.append(1)
        return [f"Baho {payload['risk_score']}. Bu hududdagi 4 812 ta subyektdan eng yuqori."], {
            "request_id": None, "input_tokens": 10, "output_tokens": 10, "stop_reason": "end_turn"}

    monkeypatch.setattr(explainer, "_call_model", lying)
    code = client.get(f"{API}/subjects", params={"region": "TK", "page_size": 1}, headers=admin_h).json()["data"]["items"][0]["code"]
    d = client.get(f"{API}/subjects/{code}/explanation", headers=admin_h).json()["data"]
    assert d["source"] == "template" and d["fallback_code"] == "rejected" and "812" in d["fallback_reason"]

    sid = db.scalar(select(Subject.id).where(Subject.code == code))
    row = db.scalar(select(AiExplanation).where(AiExplanation.subject_id == sid))
    assert row.status == "rejected"

    client.get(f"{API}/subjects/{code}/explanation", headers=admin_h)
    assert len(calls) == 1  # muvaffaqiyatsizlikdan keyin 10 daqiqa qayta chaqirilmaydi


def test_api_error_falls_back_to_template(client, admin_h, ai_key, monkeypatch):
    def broken(payload):
        raise RuntimeError("Model javob berish vaqti tugadi")

    monkeypatch.setattr(explainer, "_call_model", broken)
    code = client.get(f"{API}/subjects", params={"region": "SA", "page_size": 1}, headers=admin_h).json()["data"]["items"][0]["code"]
    d = client.get(f"{API}/subjects/{code}/explanation", headers=admin_h).json()["data"]
    assert d["source"] == "template" and d["fallback_code"] == "error"
    status = client.get(f"{API}/ai/status", headers=admin_h).json()["data"]
    assert status["session"]["last_error"] == "Model javob berish vaqti tugadi"


def test_ai_status_permissions(client, admin_h, analyst_h, auditor_h):
    assert client.get(f"{API}/ai/status", headers=analyst_h).status_code == 403
    assert client.get(f"{API}/ai/status", headers=auditor_h).status_code == 200
    assert client.post(f"{API}/ai/test", headers=auditor_h).status_code == 403
    r = client.post(f"{API}/ai/test", headers=admin_h).json()["data"]
    assert r["ok"] is False and "kaliti" in r["message"]
