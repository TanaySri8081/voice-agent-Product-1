from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.db import get_db
from backend.routes.auth import get_current_user
from backend.models import Tenant
from backend.utils.helpers import api_response, serialize_model, to_uuid

router = APIRouter(prefix="/clinics", tags=["Clinic Profile"])


class ClinicSettingsUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    # "time" (fixed slots) or "token" (daily queue number). The queue counters
    # themselves are managed only via the /appointments/queue endpoints.
    booking_mode: Optional[str] = None
    notify_email: Optional[str] = None
    did: Optional[str] = None
    system_prompt: Optional[str] = None
    initial_greeting: Optional[str] = None
    knowledge_base: Optional[str] = None
    voice: Optional[str] = None
    language: Optional[str] = None
    llm_model: Optional[str] = None
    whatsapp_phone_number_id: Optional[str] = None
    whatsapp_access_token: Optional[str] = None
    whatsapp_template_lang: Optional[str] = None
    whatsapp_confirm_template: Optional[str] = None
    whatsapp_reminder_template: Optional[str] = None


def _mask_secrets(data: dict) -> dict:
    """Never return the raw WhatsApp access token; expose only whether it's set."""
    if data is None:
        return data
    data["whatsapp_access_token_set"] = bool(data.get("whatsapp_access_token"))
    data["whatsapp_access_token"] = ""
    return data


@router.get("/settings")
async def get_settings(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    clinic_id = to_uuid(current_user.get("clinic_id"))
    if clinic_id is None:
        return api_response(success=False, message="No clinic associated with user", status_code=400)

    result = await db.execute(select(Tenant).where(Tenant.id == clinic_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        return api_response(success=False, message="Clinic settings not found", status_code=404)

    return api_response(
        success=True,
        message="Clinic settings fetched successfully",
        data=_mask_secrets(serialize_model(tenant)),
    )


@router.put("/settings")
async def update_settings(
    payload: ClinicSettingsUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    clinic_id = to_uuid(current_user.get("clinic_id"))
    if clinic_id is None:
        return api_response(success=False, message="No clinic associated with user", status_code=400)

    update_data = payload.dict(exclude_unset=True)
    if not update_data:
        return api_response(success=False, message="No settings data provided for update", status_code=400)

    result = await db.execute(select(Tenant).where(Tenant.id == clinic_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        return api_response(success=False, message="Clinic settings not found", status_code=404)

    for key, value in update_data.items():
        # Don't wipe the stored WhatsApp token when the field is left blank
        # (the dashboard sends blank to mean "keep the existing token").
        if key == "whatsapp_access_token" and not (value or "").strip():
            continue
        setattr(tenant, key, value)
    await db.commit()

    return api_response(
        success=True,
        message="Clinic settings updated successfully",
        data=_mask_secrets(serialize_model(tenant)),
    )
