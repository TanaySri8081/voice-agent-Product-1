from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.db import get_db
from backend.routes.auth import get_current_user
from backend.models import Patient
from backend.schemas.patient import PatientCreate
from backend.utils.helpers import api_response, serialize_model, serialize_models, to_uuid

router = APIRouter(prefix="/patients", tags=["Patients CRM"])


@router.get("/")
async def list_patients(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    clinic_id = to_uuid(current_user.get("clinic_id"))
    if clinic_id is None:
        return api_response(success=False, message="No clinic associated with user", status_code=400)

    result = await db.execute(select(Patient).where(Patient.clinic_id == clinic_id))
    return api_response(
        success=True,
        message="Patients fetched successfully",
        data=serialize_models(result.scalars().all()),
    )


@router.post("/")
async def create_patient(
    payload: PatientCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    clinic_id = to_uuid(current_user.get("clinic_id"))
    if clinic_id is None:
        return api_response(success=False, message="No clinic associated with user", status_code=400)

    # Enforce unique phone per clinic (also guarded by a DB constraint)
    existing = await db.execute(
        select(Patient).where(Patient.phone == payload.phone, Patient.clinic_id == clinic_id)
    )
    if existing.scalar_one_or_none():
        return api_response(success=False, message="Patient with this phone number already exists", status_code=400)

    patient = Patient(clinic_id=clinic_id, **payload.dict())
    db.add(patient)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return api_response(success=False, message="Patient with this phone number already exists", status_code=400)

    return api_response(
        success=True,
        message="Patient created successfully",
        data=serialize_model(patient),
    )


@router.get("/{patient_id}")
async def get_patient(
    patient_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    clinic_id = to_uuid(current_user.get("clinic_id"))
    pid = to_uuid(patient_id)
    if pid is None:
        return api_response(success=False, message="Patient not found", status_code=404)

    result = await db.execute(
        select(Patient).where(Patient.id == pid, Patient.clinic_id == clinic_id)
    )
    patient = result.scalar_one_or_none()
    if not patient:
        return api_response(success=False, message="Patient not found", status_code=404)

    return api_response(
        success=True,
        message="Patient fetched successfully",
        data=serialize_model(patient),
    )


@router.put("/{patient_id}")
async def update_patient(
    patient_id: str,
    payload: PatientCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    clinic_id = to_uuid(current_user.get("clinic_id"))
    pid = to_uuid(patient_id)
    if pid is None:
        return api_response(success=False, message="Patient not found", status_code=404)

    result = await db.execute(
        select(Patient).where(Patient.id == pid, Patient.clinic_id == clinic_id)
    )
    patient = result.scalar_one_or_none()
    if not patient:
        return api_response(success=False, message="Patient not found", status_code=404)

    for key, value in payload.dict(exclude_unset=True).items():
        setattr(patient, key, value)
    await db.commit()

    return api_response(
        success=True,
        message="Patient updated successfully",
        data=serialize_model(patient),
    )


@router.delete("/{patient_id}")
async def delete_patient(
    patient_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    clinic_id = to_uuid(current_user.get("clinic_id"))
    pid = to_uuid(patient_id)
    if pid is None:
        return api_response(success=False, message="Patient not found", status_code=404)

    result = await db.execute(
        select(Patient).where(Patient.id == pid, Patient.clinic_id == clinic_id)
    )
    patient = result.scalar_one_or_none()
    if not patient:
        return api_response(success=False, message="Patient not found", status_code=404)

    await db.delete(patient)
    await db.commit()
    return api_response(success=True, message="Patient deleted successfully")
