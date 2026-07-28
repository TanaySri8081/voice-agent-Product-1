"""
Readiness diagnostics: checks each integration and reports ok / warn / fail so
an operator can see at a glance what's blocking a live call. The MiniMax check
is ACTIVE (a tiny request) so it surfaces the real state — e.g. the "1008
insufficient balance" error — not just whether a key is present.

Checks run sequentially because they share the request's DB session (an async
session isn't safe to use concurrently).
"""

import logging

import httpx
from sqlalchemy import select, func, text

from backend.config.settings import settings
from backend.models import Tenant

logger = logging.getLogger("diagnostics")


async def _check_db(db):
    try:
        await db.execute(text("SELECT 1"))
        return {"name": "Database (Supabase)", "status": "ok", "detail": "Connected"}
    except Exception as e:
        return {"name": "Database (Supabase)", "status": "fail", "detail": str(e)[:180]}


def _check_deepgram():
    if settings.DEEPGRAM_API_KEY:
        return {"name": "Deepgram (Speech-to-Text)", "status": "ok",
                "detail": f"Configured — model {settings.DEEPGRAM_MODEL}, lang {settings.DEEPGRAM_LANGUAGE}"}
    return {"name": "Deepgram (Speech-to-Text)", "status": "fail", "detail": "DEEPGRAM_API_KEY not set (mock mode)"}


async def _check_minimax():
    key = settings.MINIMAX_API_KEY
    if not key or "your_minimax" in key:
        return {"name": "MiniMax (LLM + Voice)", "status": "fail", "detail": "MINIMAX_API_KEY not set (mock mode)"}
    url = f"{settings.MINIMAX_API_BASE}/text/chatcompletion_v2"
    if settings.MINIMAX_GROUP_ID:
        url += f"?GroupId={settings.MINIMAX_GROUP_ID}"
    payload = {"model": settings.MINIMAX_LLM_MODEL, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1}
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(url, headers=headers, json=payload)
        try:
            data = r.json()
        except Exception:
            data = {}
        base = (data or {}).get("base_resp") or {}
        code = base.get("status_code")
        if r.status_code == 200 and code in (0, None):
            return {"name": "MiniMax (LLM + Voice)", "status": "ok", "detail": f"Reachable — model {settings.MINIMAX_LLM_MODEL}"}
        msg = base.get("status_msg") or (r.text[:160] if r.text else f"HTTP {r.status_code}")
        return {"name": "MiniMax (LLM + Voice)", "status": "fail", "detail": f"code {code}: {msg}"}
    except Exception as e:
        return {"name": "MiniMax (LLM + Voice)", "status": "fail", "detail": str(e)[:180]}


def _check_vobiz():
    if settings.VOBIZ_SIP_DOMAIN and settings.VOBIZ_USERNAME and settings.VOBIZ_PASSWORD:
        return {"name": "Vobiz (Telephony)", "status": "ok", "detail": "Configured"}
    return {"name": "Vobiz (Telephony)", "status": "warn", "detail": "Not fully configured — inbound calls won't route"}


async def _check_whatsapp(db):
    cnt = (await db.execute(
        select(func.count()).select_from(Tenant).where(
            Tenant.whatsapp_phone_number_id.isnot(None),
            Tenant.whatsapp_access_token.isnot(None),
        )
    )).scalar() or 0
    platform = settings.whatsapp_enabled
    if platform or cnt > 0:
        return {"name": "WhatsApp (Meta Cloud API)", "status": "ok",
                "detail": f"Platform {'on' if platform else 'off'} · {cnt} tenant(s) with own number"}
    return {"name": "WhatsApp (Meta Cloud API)", "status": "warn", "detail": "Not configured — confirmations/reminders won't send"}


def _check_smtp():
    if settings.SMTP_HOST:
        return {"name": "Email (SMTP)", "status": "ok", "detail": "Configured"}
    return {"name": "Email (SMTP)", "status": "warn", "detail": "Not set — reset/alert links are logged, not emailed"}


async def run_all(db) -> list:
    return [
        await _check_db(db),
        _check_deepgram(),
        await _check_minimax(),
        _check_vobiz(),
        await _check_whatsapp(db),
        _check_smtp(),
    ]
