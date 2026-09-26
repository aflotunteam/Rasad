"""SI izohi: Claude hisoblangan strukturali natijani o'zbek tilidagi matnga aylantiradi.

Qoidalar (prompt §16):
- model xavf bahosini yaratmaydi, raqam, manba yoki fakt o'ylab topmaydi, ayb e'lon qilmaydi;
- javob JSON sxema bo'yicha olinadi va guard.check dan o'tadi;
- har qanday muammoda (kalit yo'q, xato, rad etish, tekshiruvdan o'tmadi) shablon izohi qaytariladi;
- natija ai_explanations jadvalida keshlanadi: bir xil natija uchun model qayta chaqirilmaydi.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.ai import client as ai_client
from app.ai import guard
from app.core.config import get_settings
from app.models import AiExplanation
from app.services import explain
from data_gen.reference import RISK_TYPES

PROMPT_VERSION = "v1"
RETRY_AFTER_FAILURE = timedelta(minutes=10)
LEVEL_UZ = {"high": "yuqori", "medium": "o‘rta", "low": "past"}
STATUS_UZ = {
    "pending": "ko‘rib chiqilmagan", "confirmed": "tasdiqlangan", "rejected": "rad etilgan",
    "need_info": "qo‘shimcha ma’lumot so‘ralgan", "sent_review": "tekshiruvga yuborilgan",
}
RISK_TYPE_NAMES = {c: n for c, n, _, _ in RISK_TYPES}

SYSTEM_PROMPT = """You write explanations for RASAD, an economic-risk decision-support platform used by government analysts in Uzbekistan.

You receive one subject's already-computed analytical results as JSON. Your only job is to explain those results in clear, professional academic Uzbek (Latin script) so an analyst understands why the case was prioritised.

Rules:
- Use only facts and numbers that appear in the JSON. Copy every number exactly as written there, using a decimal comma (81,7 not 81.7), and keep its unit. Do not round, add up, compare in percent, or derive new numbers.
- Do not add sources, statistics, company names, laws, or background knowledge that is not in the JSON.
- The score is an analytical signal, not a finding. Never state or imply guilt, fraud, a crime, or illegality. Say that the case needs further expert review.
- Keep the risk score, the confidence level and the data quality separate; do not present a high score as automatically reliable. If data quality is low, say the result should be interpreted with caution.
- End with the point that the final decision is made by an authorised expert.
- Write 3 or 4 short paragraphs, plain text, no markdown, no bullet points, no headings. Use the Uzbek apostrophes ‘ and ’ (o‘, g‘, ma’lumot).
"""

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "paragraphs": {
            "type": "array",
            "items": {"type": "string"},
            "description": "3-4 short paragraphs of Uzbek Latin text",
        }
    },
    "required": ["paragraphs"],
    "additionalProperties": False,
}


def build_payload(code: str, region: str, sector: str, risk: dict, factors: list[dict]) -> dict:
    """Modelga yuboriladigan strukturali natija: faqat hisoblangan qiymatlar, raqamlar o'zbekcha formatda."""
    fmt = explain.fmt
    top = [f for f in factors if f["impact"] > 0][:5]
    return {
        "subject_code": code,
        "region": region,
        "sector": sector,
        "risk_score": f"{fmt(risk['score'])} / 100",
        "risk_level": LEVEL_UZ.get(risk["level"], risk["level"]),
        "thresholds": f"o‘rta daraja {int(risk['thresholds']['low'])} dan, yuqori daraja {int(risk['thresholds']['high'])} dan boshlanadi (MVP uchun shartli qiymatlar)",
        "confidence_level": LEVEL_UZ.get(risk["confidence"], risk["confidence"]),
        "data_quality": f"{fmt(risk['dq_score'])} / 100",
        "primary_risk_type": f"{risk['primary_risk_type']} — {RISK_TYPE_NAMES.get(risk['primary_risk_type'], '')}",
        "observed_signals": [f"{t} — {RISK_TYPE_NAMES.get(t, '')}" for t in risk.get("risk_types") or []],
        "expert_status": STATUS_UZ.get(risk.get("expert_status", "pending"), "ko‘rib chiqilmagan"),
        "factors": [
            {
                "rank": i + 1,
                "factor": f["factor"],
                "current_value": explain.fmt_value(f["current_value"], f["unit"]),
                "expected_range": (
                    f"{explain.fmt_value(f['baseline_low'], f['unit'])} … {explain.fmt_value(f['baseline_high'], f['unit'])}"
                    if f["baseline_low"] is not None and f["baseline_high"] is not None else "ma’lumot mavjud emas"
                ),
                "deviation": explain.DEVIATION_TEXT.get(f["deviation"], f["deviation"]),
                "impact_points": fmt(f["impact"], 1, signed=True),
                "source": f["source"],
            }
            for i, f in enumerate(top)
        ],
        "impacts_sum_equals_score": True,
    }


def allowed_numbers(risk: dict, factors: list[dict]) -> set[float]:
    vals: list[float | None] = [risk["score"], risk["dq_score"], risk["confidence_value"] * 100,
                                risk["thresholds"]["low"], risk["thresholds"]["high"]]
    for f in factors[:5]:
        vals += [f["current_value"], f["baseline_low"], f["baseline_high"], f["impact"]]
    return guard.allowed_numbers(vals)


def input_hash(payload: dict, model: str) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False) + PROMPT_VERSION + model
    return hashlib.sha256(raw.encode()).hexdigest()


def _template(code: str, risk: dict, factors: list[dict], reason: str | None, reason_code: str) -> dict:
    out = explain.build(code, risk, factors)
    out.update({"source": "template", "model": None, "model_label": None, "validated": True,
                "fallback_reason": reason, "fallback_code": reason_code, "created_at": None})
    return out


def _from_row(row: AiExplanation, code: str, risk: dict, factors: list[dict]) -> dict:
    base = explain.build(code, risk, factors)
    return {
        "paragraphs": row.paragraphs,
        "basis_note": base["basis_note"] + " Matn Claude modeli tomonidan yozilgan va raqamlar tekshiruvidan o‘tgan.",
        "disclaimer": base["disclaimer"],
        "generator": f"{ai_client.model_label(row.model)} ({row.model})",
        "inputs": base["inputs"],
        "source": "ai",
        "model": row.model,
        "model_label": ai_client.model_label(row.model),
        "validated": True,
        "fallback_reason": None,
        "fallback_code": None,
        "created_at": row.created_at.isoformat(),
    }


def _call_model(payload: dict) -> tuple[list[str], dict]:
    s = get_settings()
    client = ai_client.get_client()
    response = client.messages.create(
        model=s.ai_model,
        max_tokens=s.ai_max_tokens,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": "Analitik natijalar (JSON):\n" + json.dumps(payload, ensure_ascii=False, indent=1),
        }],
        output_config={"effort": s.ai_effort, "format": {"type": "json_schema", "schema": OUTPUT_SCHEMA}},
    )
    meta = {
        "request_id": getattr(response, "_request_id", None),
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "stop_reason": response.stop_reason,
    }
    if response.stop_reason == "refusal":
        raise RuntimeError("Model so‘rovni rad etdi")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("Javob token chegarasida kesilib qoldi")
    text = next((b.text for b in response.content if b.type == "text"), "")
    data = json.loads(text)
    return [p.strip() for p in data.get("paragraphs", []) if isinstance(p, str)], meta


def cached_or_template(db: Session, subject_id: int, code: str, region: str, sector: str, risk: dict,
                       factors: list[dict]) -> dict:
    """Modelni chaqirmaydi: hisobotlar uchun keshdagi tasdiqlangan SI izohi, bo'lmasa shablon."""
    s = get_settings()
    h = input_hash(build_payload(code, region, sector, risk, factors), s.ai_model)
    row = db.scalar(select(AiExplanation).where(AiExplanation.subject_id == subject_id, AiExplanation.input_hash == h,
                                                AiExplanation.status == "ok").order_by(desc(AiExplanation.created_at)))
    if row:
        return _from_row(row, code, risk, factors)
    return _template(code, risk, factors, None, "template")


def explain_subject(db: Session, subject_id: int, code: str, region: str, sector: str, risk: dict,
                    factors: list[dict], user_id: int | None = None, force: bool = False) -> dict:
    s = get_settings()
    if not s.ai_enabled:
        return _template(code, risk, factors, "SI xizmati sozlamalarda o‘chirilgan", "disabled")
    if not ai_client.is_configured():
        return _template(code, risk, factors, "API kaliti o‘rnatilmagan: shablon izohi ko‘rsatilmoqda", "not_configured")

    payload = build_payload(code, region, sector, risk, factors)
    h = input_hash(payload, s.ai_model)
    last = db.scalar(select(AiExplanation).where(AiExplanation.subject_id == subject_id, AiExplanation.input_hash == h)
                     .order_by(desc(AiExplanation.created_at)))
    if last and not force:
        if last.status == "ok":
            return _from_row(last, code, risk, factors)
        created = last.created_at if last.created_at.tzinfo else last.created_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - created < RETRY_AFTER_FAILURE:
            return _template(code, risk, factors, last.rejection_reason, last.status)

    started = time.perf_counter()
    ai_client.state.calls += 1
    row = AiExplanation(subject_id=subject_id, input_hash=h, model=s.ai_model, status="error", created_by=user_id)
    try:
        paragraphs, meta = _call_model(payload)
        row.input_tokens, row.output_tokens = meta["input_tokens"], meta["output_tokens"]
        row.request_id = meta["request_id"]
        ai_client.state.input_tokens += row.input_tokens
        ai_client.state.output_tokens += row.output_tokens
        problem = guard.check(paragraphs, allowed_numbers(risk, factors))
        row.paragraphs = paragraphs
        if problem:
            row.status, row.rejection_reason = "rejected", problem
            ai_client.state.rejected += 1
        else:
            row.status = "ok"
            ai_client.state.ok += 1
            ai_client.state.last_ok_at = datetime.now(timezone.utc)
    except Exception as exc:  # noqa: BLE001 - har qanday xatoda shablonga qaytiladi
        message = str(exc) if isinstance(exc, (RuntimeError, json.JSONDecodeError)) else ai_client.describe_error(exc)
        row.rejection_reason = message
        ai_client.record_error(message)
    row.latency_ms = int((time.perf_counter() - started) * 1000)
    ai_client.state.note_latency(row.latency_ms)
    db.add(row)
    db.commit()

    if row.status == "ok":
        return _from_row(row, code, risk, factors)
    return _template(code, risk, factors, row.rejection_reason, row.status)
