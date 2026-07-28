import asyncio
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Response, Depends, Request, Header
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.integrations.vobiz.client import VobizClient
from backend.config.settings import settings
from backend.services.db import get_db
from backend.services import repository, notifications, events
from backend.routes.auth import get_current_user
from backend.models import CallLog, Tenant, Appointment
from backend.utils.helpers import api_response, serialize_models, to_uuid

logger = logging.getLogger("calls-router")
router = APIRouter(prefix="/calls", tags=["Calls"])


def _pick(params: dict, *keys):
    """Case-insensitive lookup across a set of possible parameter names."""
    lowered = {str(k).lower(): v for k, v in params.items()}
    for key in keys:
        val = lowered.get(key.lower())
        if val:
            return val
    return None


@router.post("/twiml/inbound")
async def inbound_twiml(request: Request):
    """
    Webhook handler when Vobiz receives an inbound call.
    Resolves the destination DID and answers with Stream XML.

    Vobiz (Plivo-style) posts the call details as form fields, not query params,
    so we gather from query + form (+ JSON) and match common field-name variants.
    The full payload is logged so we can see exactly what the provider sends.
    """
    params = dict(request.query_params)
    content_type = request.headers.get("content-type", "")
    try:
        if "application/json" in content_type:
            body = await request.json()
            if isinstance(body, dict):
                params.update({k: str(v) for k, v in body.items()})
        else:
            form = await request.form()
            params.update({k: str(v) for k, v in form.items()})
    except Exception as e:
        logger.warning(f"Inbound webhook parse error: {e}")

    logger.info(f"Vobiz Inbound Webhook raw params: {params}")

    to = _pick(params, "to", "To", "called", "CalledNumber", "destination", "did", "DID", "dnis", "dialed_number")
    frm = _pick(params, "From", "from", "caller", "CallerNumber", "src", "source", "ani", "from_number")
    logger.info(f"Vobiz Inbound resolved -> To: {to}, From: {frm}")

    ws_url = settings.SERVER_URL.replace("https://", "wss://").replace("http://", "ws://")
    ws_endpoint = f"{ws_url}/media-stream?destination={to or ''}&phone={frm or ''}"
    xml_response = VobizClient.get_stream_xml(ws_endpoint)
    return Response(content=xml_response, media_type="application/xml")


@router.get("/logs")
async def get_call_logs(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve call logs for the logged-in doctor's clinic.
    """
    clinic_id = to_uuid(current_user.get("clinic_id"))
    if clinic_id is None:
        return api_response(success=False, message="No clinic associated with user", status_code=400)

    result = await db.execute(
        select(CallLog)
        .where(CallLog.clinic_id == clinic_id)
        .order_by(CallLog.created_at.desc())
        .limit(100)
    )
    return api_response(
        success=True,
        message="Call logs retrieved successfully",
        data=serialize_models(result.scalars().all()),
    )


# ----- Internal: booking made by the LiveKit voice agent --------------------

class AgentBookRequest(BaseModel):
    # Dialed DID (to resolve the clinic) + caller's number, both from the SIP
    # participant attributes. clinic_id may be sent to bypass DID resolution.
    did: Optional[str] = None
    clinic_id: Optional[str] = None
    # Booking mode from the call context, so the endpoint can skip a tenant read.
    booking_mode: Optional[str] = None
    caller_phone: Optional[str] = None
    patient_name: str
    reason: Optional[str] = None
    # Healthcare intake collected on the call, saved to the patient record.
    age: Optional[int] = None
    gender: Optional[str] = None
    # Time mode: ISO-8601 datetime. Token mode ignores it.
    appointment_at: Optional[datetime] = None
    # Human display fallback (e.g. "kal shaam 5 baje") when no ISO time is parsed.
    appointment_date: Optional[str] = None
    duration_min: int = 30


def _did_variants(did: str):
    """Common phone-format variants so DID matching survives +/country-code
    differences between what Vobiz sends over SIP and what's stored in the DB."""
    d = (did or "").strip()
    if not d:
        return []
    digits = "".join(ch for ch in d if ch.isdigit())
    variants = [d]
    if digits:
        variants += [digits, "+" + digits]
        if len(digits) > 10:
            last10 = digits[-10:]
            variants += ["+91" + last10, "91" + last10, last10]
    seen, out = set(), []
    for v in variants:
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


def _publish_appt_event(clinic_id, appt_id, name, display):
    """In-memory real-time dashboard notification (bell + lists). Fast, non-blocking."""
    try:
        events.publish(clinic_id, {
            "id": f"appt-{appt_id}",
            "type": "appointment",
            "name": name,
            "meta": display,
            "ts": datetime.utcnow().isoformat(),
            "to": "/appointments",
        })
    except Exception:
        pass


async def _post_book_side_effects(clinic_id, caller_phone, name, display, age=None, gender=None):
    """Non-critical work done AFTER the booking response: capture the caller as a
    contact (with any intake details) and send the WhatsApp confirmation. Kept off
    the critical path so the agent gets its token back fast."""
    if not caller_phone:
        return
    try:
        await repository.get_or_create_patient(clinic_id, caller_phone, name, age=age, gender=gender)
    except Exception as e:
        logger.warning(f"agent-book: contact upsert failed: {e}")
    try:
        await notifications.send_customer_confirmation(clinic_id, caller_phone, name, display)
    except Exception:
        pass


@router.post("/agent-book")
async def agent_book_appointment(
    payload: AgentBookRequest,
    x_internal_secret: str = Header(default="", alias="X-Internal-Secret"),
    db: AsyncSession = Depends(get_db),
):
    """Persist a booking made by the LiveKit voice agent during a live call.

    Optimised for low latency: the critical path (assign the daily token / check
    the slot + insert the appointment) runs in ONE DB session; capturing the
    caller as a contact and sending the WhatsApp confirmation are deferred to a
    background task so the agent gets its token back fast. Auth is a shared secret.
    """
    if not _agent_secret_ok(x_internal_secret):
        return api_response(success=False, message="Unauthorized", status_code=401)

    # Resolve clinic + booking_mode with as few round-trips as possible. Fast path:
    # the agent sends clinic_id + booking_mode from the call context => ZERO tenant
    # reads. Fall back to a DID / sole-clinic lookup only when clinic_id is missing.
    clinic_id = to_uuid(payload.clinic_id) if payload.clinic_id else None
    booking_mode = (payload.booking_mode or "").strip().lower()
    if clinic_id is None:
        tenant = None
        for cand in _did_variants(payload.did):
            tenant = await repository.get_tenant_by_did(cand)
            if tenant:
                break
        if tenant is None:
            tenant = await repository.get_only_tenant()
        if tenant is None:
            return api_response(success=False, message="Could not resolve a clinic for this call.", status_code=404)
        clinic_id = to_uuid(tenant.get("id"))
        booking_mode = (tenant.get("booking_mode") or "time").strip().lower()
    elif booking_mode not in ("time", "token"):
        booking_mode = ((await db.execute(
            select(Tenant.booking_mode).where(Tenant.id == clinic_id)
        )).scalar_one_or_none() or "time").strip().lower()

    caller_phone = (payload.caller_phone or "").strip() or None
    name = (payload.patient_name or "").strip() or "Caller"
    patient_ref = caller_phone or "agent"
    duration_min = int(payload.duration_min or 30)

    if booking_mode == "token":
        today = repository.queue_today_str()
        current_max = (await db.execute(
            select(func.max(Appointment.token_number)).where(
                Appointment.clinic_id == clinic_id,
                Appointment.token_date == today,
            )
        )).scalar()
        token_num = int(current_max or 0) + 1
        display = payload.appointment_date or f"Token {token_num}"
        appt = Appointment(
            clinic_id=clinic_id, patient_id=patient_ref, patient_name=name,
            appointment_date=display, appointment_at=None, duration_min=duration_min,
            token_number=token_num, token_date=today, phone=caller_phone,
            reason=payload.reason, status="scheduled",
        )
        db.add(appt)
        await db.commit()
        _publish_appt_event(clinic_id, appt.id, name, display)
        asyncio.create_task(_post_book_side_effects(clinic_id, caller_phone, name, display, age=payload.age, gender=payload.gender))
        return api_response(
            success=True, message=f"Token {token_num} booked",
            data={"booking_mode": "token", "token_number": token_num, "display": display},
        )

    # ----- time mode -----
    appt_at = payload.appointment_at
    if appt_at is not None and not await repository.is_slot_available(clinic_id, appt_at, duration_min):
        return api_response(success=False, message="slot_unavailable", data={"available": False}, status_code=409)
    display = payload.appointment_date or (
        appt_at.strftime("%d %b %Y, %I:%M %p") if appt_at else "Unspecified"
    )
    appt = Appointment(
        clinic_id=clinic_id, patient_id=patient_ref, patient_name=name,
        appointment_date=display, appointment_at=appt_at, duration_min=duration_min,
        phone=caller_phone, reason=payload.reason, status="scheduled",
    )
    db.add(appt)
    await db.commit()
    _publish_appt_event(clinic_id, appt.id, name, display)
    asyncio.create_task(_post_book_side_effects(clinic_id, caller_phone, name, display))
    return api_response(
        success=True, message="Appointment booked",
        data={"booking_mode": "time", "display": display},
    )


# ----- Internal: additional agent actions (context / availability / queue /
#       caller lookup / register contact). All share the same shared-secret auth
#       and clinic-resolution as agent-book. -------------------------------------

def _agent_secret_ok(secret_header: str) -> bool:
    # Prefer a dedicated secret; fall back to the app's JWT secret so the agent
    # works out of the box (backend + agent read the same root .env, so both
    # compute the same value). Set AGENT_INTERNAL_SECRET to override.
    secret = settings.AGENT_INTERNAL_SECRET or settings.JWT_SECRET
    return bool(secret) and secret_header == secret


async def _agent_resolve_tenant(clinic_id, did):
    """clinic_id -> DID (with format variants) -> sole clinic. Mirrors agent-book."""
    tenant = None
    if clinic_id:
        tenant = await repository.get_tenant_by_id(clinic_id)
    if tenant is None and did:
        for cand in _did_variants(did):
            tenant = await repository.get_tenant_by_did(cand)
            if tenant:
                break
    if tenant is None:
        tenant = await repository.get_only_tenant()
    return tenant


class AgentContextRequest(BaseModel):
    did: Optional[str] = None
    clinic_id: Optional[str] = None


class AgentAvailabilityRequest(BaseModel):
    did: Optional[str] = None
    clinic_id: Optional[str] = None
    appointment_at: datetime
    duration_min: int = 30


class AgentPhoneRequest(BaseModel):
    did: Optional[str] = None
    clinic_id: Optional[str] = None
    caller_phone: Optional[str] = None


class AgentPatientRequest(BaseModel):
    did: Optional[str] = None
    clinic_id: Optional[str] = None
    caller_phone: Optional[str] = None
    patient_name: str
    note: Optional[str] = None
    # Healthcare intake collected on the call, saved to the patient record.
    age: Optional[int] = None
    gender: Optional[str] = None


@router.post("/agent-context")
async def agent_context(
    payload: AgentContextRequest,
    x_internal_secret: str = Header(default="", alias="X-Internal-Secret"),
):
    """Per-call config for the voice agent: business name, booking mode, custom
    prompt + knowledge base, voice/language. Lets one agent serve many clinics."""
    if not _agent_secret_ok(x_internal_secret):
        return api_response(success=False, message="Unauthorized", status_code=401)
    tenant = await _agent_resolve_tenant(payload.clinic_id, payload.did)
    if tenant is None:
        return api_response(success=False, message="Could not resolve a clinic.", status_code=404)
    return api_response(success=True, message="ok", data={
        "clinic_id": tenant.get("id"),
        "business_name": tenant.get("name") or "our business",
        "booking_mode": (tenant.get("booking_mode") or "time").strip().lower(),
        "system_prompt": tenant.get("system_prompt") or "",
        "knowledge_base": tenant.get("knowledge_base") or "",
        "voice": tenant.get("voice") or "",
        "language": tenant.get("language") or "",
    })


@router.post("/agent-availability")
async def agent_availability(
    payload: AgentAvailabilityRequest,
    x_internal_secret: str = Header(default="", alias="X-Internal-Secret"),
):
    """Is a specific time free? (time-slot clinics)."""
    if not _agent_secret_ok(x_internal_secret):
        return api_response(success=False, message="Unauthorized", status_code=401)
    tenant = await _agent_resolve_tenant(payload.clinic_id, payload.did)
    if tenant is None:
        return api_response(success=False, message="Could not resolve a clinic.", status_code=404)
    available = await repository.is_slot_available(
        tenant.get("id"), payload.appointment_at, payload.duration_min
    )
    return api_response(success=True, message="ok", data={"available": bool(available)})


@router.post("/agent-queue")
async def agent_queue(
    payload: AgentPhoneRequest,
    x_internal_secret: str = Header(default="", alias="X-Internal-Secret"),
):
    """Live token/queue status (token clinics)."""
    if not _agent_secret_ok(x_internal_secret):
        return api_response(success=False, message="Unauthorized", status_code=401)
    tenant = await _agent_resolve_tenant(payload.clinic_id, payload.did)
    if tenant is None:
        return api_response(success=False, message="Could not resolve a clinic.", status_code=404)
    today = repository.queue_today_str()
    caller_phone = (payload.caller_phone or "").strip() or None
    status = await repository.get_queue_status(tenant.get("id"), today, caller_phone)
    return api_response(success=True, message="ok", data=status)


@router.post("/agent-lookup")
async def agent_lookup(
    payload: AgentPhoneRequest,
    x_internal_secret: str = Header(default="", alias="X-Internal-Secret"),
):
    """Recognise the caller by phone: known?/name/history + nearest upcoming appt."""
    if not _agent_secret_ok(x_internal_secret):
        return api_response(success=False, message="Unauthorized", status_code=401)
    tenant = await _agent_resolve_tenant(payload.clinic_id, payload.did)
    if tenant is None:
        return api_response(success=False, message="Could not resolve a clinic.", status_code=404)
    clinic_id = tenant.get("id")
    phone = (payload.caller_phone or "").strip() or None
    patient = await repository.lookup_patient_by_phone(phone, clinic_id) if phone else None
    upcoming = await repository.get_upcoming_appointment(clinic_id, phone) if phone else None
    return api_response(success=True, message="ok", data={
        "known": bool(patient),
        "name": (patient or {}).get("name"),
        "history": (patient or {}).get("history") or [],
        "upcoming": (
            {"when": upcoming.get("appointment_date"), "reason": upcoming.get("reason")}
            if upcoming else None
        ),
    })


@router.post("/agent-patient")
async def agent_patient(
    payload: AgentPatientRequest,
    x_internal_secret: str = Header(default="", alias="X-Internal-Secret"),
):
    """Register the caller as a patient/contact (or update name), optional note."""
    if not _agent_secret_ok(x_internal_secret):
        return api_response(success=False, message="Unauthorized", status_code=401)
    tenant = await _agent_resolve_tenant(payload.clinic_id, payload.did)
    if tenant is None:
        return api_response(success=False, message="Could not resolve a clinic.", status_code=404)
    phone = (payload.caller_phone or "").strip() or None
    patient = await repository.register_or_update_patient(
        tenant.get("id"), phone, payload.patient_name, payload.note,
        age=payload.age, gender=payload.gender,
    )
    if patient is None:
        return api_response(success=False, message="Could not save the contact.", status_code=500)
    return api_response(success=True, message="Contact saved", data={
        "patient_id": patient.get("id"),
        "name": patient.get("name"),
    })
