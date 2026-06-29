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
    did: Optional[str] = None
    system_prompt: Optional[str] = None
    initial_greeting: Optional[str] = None
    transfer_number: Optional[str] = None


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
        data=serialize_model(tenant),
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
        setattr(tenant, key, value)
    await db.commit()

    return api_response(
        success=True,
        message="Clinic settings updated successfully",
        data=serialize_model(tenant),
    )
