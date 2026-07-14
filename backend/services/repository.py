"""
Data-access helpers for non-request code paths (websocket handler, scheduler,
and the LLM tool functions). Each helper manages its own AsyncSession so callers
don't need FastAPI's request-scoped dependency.

All functions are safe to call before the DB is connected: they no-op (return
None/[] or do nothing) when the sessionmaker isn't available yet, mirroring the
previous `if db is not None` guards.
"""

import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.postgresql import insert as pg_insert

from backend.services.db import get_sessionmaker
from backend.models import Tenant, Patient, Appointment, CallLog, PhoneNumber
from backend.utils.helpers import serialize_model, to_uuid

logger = logging.getLogger("repository")


# ----- Tenant lookups -------------------------------------------------------

async def get_tenant_by_did(did: str):
    Session = get_sessionmaker()
    if Session is None or not did:
        return None
    async with Session() as session:
        # Prefer the managed phone_numbers table (active connected numbers).
        pn = (await session.execute(
            select(PhoneNumber).where(PhoneNumber.number == did, PhoneNumber.status == "active")
        )).scalar_one_or_none()
        if pn is not None:
            tenant = (await session.execute(
                select(Tenant).where(Tenant.id == pn.clinic_id)
            )).scalar_one_or_none()
            if tenant is not None:
                return serialize_model(tenant)
        # Fallback: the legacy single DID stored directly on the tenant.
        result = await session.execute(select(Tenant).where(Tenant.did == did))
        return serialize_model(result.scalar_one_or_none())


async def get_tenant_by_id(clinic_id):
    Session = get_sessionmaker()
    cid = to_uuid(clinic_id)
    if Session is None or cid is None:
        return None
    async with Session() as session:
        result = await session.execute(select(Tenant).where(Tenant.id == cid))
        return serialize_model(result.scalar_one_or_none())


# ----- Patient / appointment helpers (used by LLM tools) --------------------

async def lookup_patient_by_phone(phone: str, clinic_id=None):
    Session = get_sessionmaker()
    if Session is None or not phone:
        return None
    async with Session() as session:
        stmt = select(Patient).where(Patient.phone == phone)
        cid = to_uuid(clinic_id) if clinic_id else None
        if cid is not None:
            stmt = stmt.where(Patient.clinic_id == cid)
        result = await session.execute(stmt)
        return serialize_model(result.scalars().first())


async def get_or_create_patient(clinic_id, phone, name=None):
    """Find a patient by (clinic_id, phone), or create a new lead if missing.

    Used during inbound calls so an unknown caller who books is captured as a
    contact. If we learn a real name for an existing "Caller" record, fill it in.
    Returns the serialized patient dict (with id), or None if unconfigured.
    """
    Session = get_sessionmaker()
    cid = to_uuid(clinic_id)
    if Session is None or cid is None or not phone:
        return None
    clean_name = (name or "").strip()
    async with Session() as session:
        result = await session.execute(
            select(Patient).where(Patient.clinic_id == cid, Patient.phone == phone)
        )
        patient = result.scalar_one_or_none()

        if patient is None:
            patient = Patient(
                clinic_id=cid,
                name=clean_name or "Caller",
                phone=phone,
                history=[],
            )
            session.add(patient)
            try:
                await session.commit()
            except IntegrityError:
                # Created concurrently (unique clinic_id+phone) -> fetch the winner.
                await session.rollback()
                result = await session.execute(
                    select(Patient).where(Patient.clinic_id == cid, Patient.phone == phone)
                )
                patient = result.scalar_one_or_none()
        elif clean_name and (not patient.name or patient.name == "Caller"):
            patient.name = clean_name
            await session.commit()

        return serialize_model(patient)


async def create_appointment_record(
    clinic_id, patient_id, patient_name, appointment_date, reason, status="scheduled"
) -> bool:
    Session = get_sessionmaker()
    cid = to_uuid(clinic_id)
    if Session is None or cid is None:
        return False
    async with Session() as session:
        session.add(
            Appointment(
                clinic_id=cid,
                patient_id=str(patient_id) if patient_id is not None else None,
                patient_name=patient_name,
                appointment_date=appointment_date,
                reason=reason,
                status=status,
            )
        )
        await session.commit()
        return True


async def get_patient_by_id(patient_id):
    Session = get_sessionmaker()
    pid = to_uuid(patient_id)
    if Session is None or pid is None:
        return None
    async with Session() as session:
        result = await session.execute(select(Patient).where(Patient.id == pid))
        return serialize_model(result.scalar_one_or_none())


# ----- Call log helpers (used by the websocket handler) ---------------------

async def upsert_call_start(call_id: str, clinic_id, caller_phone: str, direction: str):
    """Create or update the call_logs row when a media stream starts."""
    Session = get_sessionmaker()
    if Session is None or not call_id:
        return
    cid = to_uuid(clinic_id) if clinic_id else None
    async with Session() as session:
        values = {
            "call_id": call_id,
            "status": "active",
            "clinic_id": cid,
            "caller_name": caller_phone,
            "phone": caller_phone,
            "direction": direction,
        }
        stmt = pg_insert(CallLog).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["call_id"],
            set_={
                "status": "active",
                "clinic_id": cid,
                "caller_name": caller_phone,
                "phone": caller_phone,
                "direction": direction,
            },
        )
        await session.execute(stmt)
        await session.commit()


async def append_transcript(call_id: str, role: str, content: str):
    """Append one {role, content} message to a call's JSONB transcript."""
    Session = get_sessionmaker()
    if Session is None or not call_id:
        return
    async with Session() as session:
        result = await session.execute(select(CallLog).where(CallLog.call_id == call_id))
        call_log = result.scalar_one_or_none()
        message = {"role": role, "content": content}
        if call_log is None:
            session.add(CallLog(call_id=call_id, transcript=[message]))
        else:
            # Reassign (not in-place append) so SQLAlchemy detects the change.
            call_log.transcript = (call_log.transcript or []) + [message]
        await session.commit()


async def set_call_status(call_id: str, status: str):
    Session = get_sessionmaker()
    if Session is None or not call_id:
        return
    async with Session() as session:
        result = await session.execute(select(CallLog).where(CallLog.call_id == call_id))
        call_log = result.scalar_one_or_none()
        if call_log is not None:
            call_log.status = status
            if status in ("completed", "failed", "transferred") and call_log.created_at:
                from datetime import datetime
                delta = datetime.utcnow() - call_log.created_at
                call_log.duration = int(delta.total_seconds())
            await session.commit()


# ----- Scheduler helpers ----------------------------------------------------

async def get_due_appointments(now_iso: str, limit_iso: str):
    Session = get_sessionmaker()
    if Session is None:
        return []
    async with Session() as session:
        stmt = select(Appointment).where(
            Appointment.status == "scheduled",
            Appointment.appointment_date >= now_iso,
            Appointment.appointment_date <= limit_iso,
        )
        result = await session.execute(stmt)
        return [serialize_model(row) for row in result.scalars().all()]


async def mark_appointment_status(appointment_id, status: str):
    Session = get_sessionmaker()
    aid = to_uuid(appointment_id)
    if Session is None or aid is None:
        return
    async with Session() as session:
        result = await session.execute(select(Appointment).where(Appointment.id == aid))
        appt = result.scalar_one_or_none()
        if appt is not None:
            appt.status = status
            await session.commit()
