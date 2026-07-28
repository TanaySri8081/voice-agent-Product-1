"""
Meta WhatsApp Cloud API sender (official, no BSP).

Proactive appointment messages are business-initiated, so they must use
pre-approved template messages. Each template here expects 3 body parameters in
order: {{1}} customer name, {{2}} business name, {{3}} when (date/time string).

Everything is best-effort: sends never raise, and the whole feature is a no-op
until WHATSAPP_ACCESS_TOKEN + WHATSAPP_PHONE_NUMBER_ID are configured.
Only the access token is used server-side; nothing WhatsApp-related reaches the
browser.
"""

import logging
import re

import httpx

from backend.config.settings import settings

logger = logging.getLogger("whatsapp")


def _normalize(phone: str):
    """Return digits-only international number (E.164 without '+'), or None."""
    digits = re.sub(r"\D", "", phone or "")
    if not digits:
        return None
    # A bare 10-digit number is treated as local and gets the default country code.
    if len(digits) == 10:
        digits = f"{settings.WHATSAPP_DEFAULT_COUNTRY_CODE}{digits}"
    return digits


def resolve_config(tenant):
    """Effective WhatsApp config for a tenant (dict), or None if not sendable.

    Per-tenant values (their own WhatsApp number) override the platform .env
    defaults. Returns None when neither the tenant nor the platform has both an
    access token and a phone number id configured.
    """
    t = tenant or {}
    token = (t.get("whatsapp_access_token") or "").strip() or settings.WHATSAPP_ACCESS_TOKEN
    phone_id = (t.get("whatsapp_phone_number_id") or "").strip() or settings.WHATSAPP_PHONE_NUMBER_ID
    if not (token and phone_id):
        return None
    return {
        "access_token": token,
        "phone_number_id": phone_id,
        "api_version": settings.WHATSAPP_API_VERSION,
        "lang": (t.get("whatsapp_template_lang") or "").strip() or settings.WHATSAPP_TEMPLATE_LANG,
        "confirm_template": (t.get("whatsapp_confirm_template") or "").strip() or settings.WHATSAPP_CONFIRM_TEMPLATE,
        "reminder_template": (t.get("whatsapp_reminder_template") or "").strip() or settings.WHATSAPP_REMINDER_TEMPLATE,
    }


async def send_template(config: dict, to_phone: str, template_name: str, params) -> bool:
    if not config or not config.get("access_token") or not config.get("phone_number_id"):
        return False
    to = _normalize(to_phone)
    if not to or not template_name:
        return False

    url = f"https://graph.facebook.com/{config['api_version']}/{config['phone_number_id']}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": config.get("lang") or settings.WHATSAPP_TEMPLATE_LANG},
            "components": [
                {"type": "body", "parameters": [{"type": "text", "text": str(p)} for p in params]}
            ],
        },
    }
    headers = {
        "Authorization": f"Bearer {config['access_token']}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code >= 400:
                logger.warning(f"WhatsApp send failed {resp.status_code}: {resp.text}")
                return False
            return True
    except Exception as e:
        logger.warning(f"WhatsApp send error: {e}")
        return False


async def send_appointment_confirmation(config: dict, to_phone: str, name: str, business: str, when: str) -> bool:
    return await send_template(
        config, to_phone, (config or {}).get("confirm_template"),
        [name or "there", business or "us", when or ""],
    )


async def send_appointment_reminder(config: dict, to_phone: str, name: str, business: str, when: str) -> bool:
    return await send_template(
        config, to_phone, (config or {}).get("reminder_template"),
        [name or "there", business or "us", when or ""],
    )
