from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.db import get_db
from backend.routes.auth import get_current_user
from backend.models import Appointment
from backend.schemas.patient import AppointmentCreate
from backend.utils.helpers import api_response, serialize_model, serialize_models, to_uuid

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.get("/")
async def list_appointments(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    clinic_id = to_uuid(current_user.get("clinic_id"))
    if clinic_id is None:
        return api_response(success=False, message="No clinic associated with user", status_code=400)

    result = await db.execute(
        select(Appointment)
        .where(Appointment.clinic_id == clinic_id)
        .order_by(Appointment.appointment_date.asc())
    )
    return api_response(
        success=True,
        message="Appointments fetched successfully",
        data=serialize_models(result.scalars().all()),
    )


@router.post("/")
async def create_appointment(
    payload: AppointmentCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    clinic_id = to_uuid(current_user.get("clinic_id"))
    if clinic_id is None:
        return api_response(success=False, message="No clinic associated with user", status_code=400)

    appointment = Appointment(clinic_id=clinic_id, **payload.dict())
    db.add(appointment)
    await db.commit()

    return api_response(
        success=True,
        message="Appointment created successfully",
        data=serialize_model(appointment),
    )


@router.put("/{appointment_id}")
async def update_appointment(
    appointment_id: str,
    payload: AppointmentCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    clinic_id = to_uuid(current_user.get("clinic_id"))
    aid = to_uuid(appointment_id)
    if aid is None:
        return api_response(success=False, message="Appointment not found", status_code=404)

    result = await db.execute(
        select(Appointment).where(Appointment.id == aid, Appointment.clinic_id == clinic_id)
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        return api_response(success=False, message="Appointment not found", status_code=404)

    for key, value in payload.dict(exclude_unset=True).items():
        setattr(appointment, key, value)
    await db.commit()

    return api_response(
        success=True,
        message="Appointment updated successfully",
        data=serialize_model(appointment),
    )


@router.delete("/{appointment_id}")
async def cancel_appointment(
    appointment_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    clinic_id = to_uuid(current_user.get("clinic_id"))
    aid = to_uuid(appointment_id)
    if aid is None:
        return api_response(success=False, message="Appointment not found", status_code=404)

    result = await db.execute(
        select(Appointment).where(Appointment.id == aid, Appointment.clinic_id == clinic_id)
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        return api_response(success=False, message="Appointment not found", status_code=404)

    appointment.status = "cancelled"
    await db.commit()
    return api_response(success=True, message="Appointment cancelled successfully")
