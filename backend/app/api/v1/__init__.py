from fastapi import APIRouter

from app.api.v1 import ai, alerts, auth, dashboard, data, decisions, governance, health, meta, reports, subjects

router = APIRouter()
for module in (health, auth, meta, ai, dashboard, subjects, decisions, alerts, reports, data, governance):
    router.include_router(module.router)
