import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.db import get_db
from backend.routes.auth import get_current_user
from backend.models import CallLog, Appointment, Patient, User, PhoneNumber, Tenant
from backend.utils.helpers import api_response, to_uuid

logger = logging.getLogger("stats-router")
router = APIRouter(prefix="/stats", tags=["Stats"])


def _fmt_duration(seconds) -> str:
    seconds = int(seconds or 0)
    return f"{seconds // 60}m {seconds % 60}s"


@router.get("/overview")
async def overview(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    clinic_id = to_uuid(current_user.get("clinic_id"))
    if clinic_id is None:
        return api_response(success=False, message="No clinic associated with user", status_code=400)

    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    week_start = now - timedelta(days=7)

    async def scalar(stmt):
        return (await db.execute(stmt)).scalar() or 0

    total_calls = await scalar(select(func.count()).select_from(CallLog).where(CallLog.clinic_id == clinic_id))
    calls_today = await scalar(select(func.count()).select_from(CallLog).where(CallLog.clinic_id == clinic_id, CallLog.created_at >= today_start))
    calls_7d = await scalar(select(func.count()).select_from(CallLog).where(CallLog.clinic_id == clinic_id, CallLog.created_at >= week_start))
    active_calls = await scalar(select(func.count()).select_from(CallLog).where(CallLog.clinic_id == clinic_id, CallLog.status == "active"))
    avg_duration = await scalar(select(func.coalesce(func.avg(CallLog.duration), 0)).where(CallLog.clinic_id == clinic_id))
    total_seconds = await scalar(select(func.coalesce(func.sum(CallLog.duration), 0)).where(CallLog.clinic_id == clinic_id))

    total_appointments = await scalar(select(func.count()).select_from(Appointment).where(Appointment.clinic_id == clinic_id))
    scheduled_appointments = await scalar(select(func.count()).select_from(Appointment).where(Appointment.clinic_id == clinic_id, Appointment.status == "scheduled"))
    total_contacts = await scalar(select(func.count()).select_from(Patient).where(Patient.clinic_id == clinic_id))
    team_size = await scalar(select(func.count()).select_from(User).where(User.clinic_id == clinic_id))
    numbers_connected = await scalar(select(func.count()).select_from(PhoneNumber).where(PhoneNumber.clinic_id == clinic_id))

    tenant = (await db.execute(select(Tenant).where(Tenant.id == clinic_id))).scalar_one_or_none()
    plan = (tenant.subscription if tenant else "free") or "free"

    outcome_rows = (await db.execute(
        select(CallLog.status, func.count()).where(CallLog.clinic_id == clinic_id).group_by(CallLog.status)
    )).all()
    outcomes = [{"status": (s or "unknown"), "count": c} for s, c in outcome_rows]

    # Daily call volume for the last 7 calendar days (zero-filled).
    daily_rows = (await db.execute(
        select(func.date(CallLog.created_at), func.count())
        .where(CallLog.clinic_id == clinic_id, CallLog.created_at >= today_start - timedelta(days=6))
        .group_by(func.date(CallLog.created_at))
    )).all()
    daily_map = {}
    for d, c in daily_rows:
        key = d.isoformat() if hasattr(d, "isoformat") else str(d)
        daily_map[key] = c
    daily = []
    for i in range(6, -1, -1):
        day = (today_start - timedelta(days=i)).date().isoformat()
        daily.append({"date": day, "count": daily_map.get(day, 0)})

    recent_rows = (await db.execute(
        select(CallLog).where(CallLog.clinic_id == clinic_id).order_by(CallLog.created_at.desc()).limit(8)
    )).scalars().all()
    recent = [{
        "id": str(r.id),
        "customer": r.caller_name or r.phone or "Unknown",
        "phone": r.phone,
        "direction": r.direction or "inbound",
        "duration": _fmt_duration(r.duration),
        "status": r.status or "unknown",
        "date": r.created_at.isoformat() if r.created_at else None,
    } for r in recent_rows]

    data = {
        "totals": {
            "calls": total_calls,
            "appointments": total_appointments,
            "scheduledAppointments": scheduled_appointments,
            "contacts": total_contacts,
            "team": team_size,
            "numbers": numbers_connected,
        },
        "calls": {
            "today": calls_today,
            "last7Days": calls_7d,
            "active": active_calls,
            "avgDurationSec": int(avg_duration),
            "totalMinutes": round(total_seconds / 60, 1),
        },
        "outcomes": outcomes,
        "daily": daily,
        "recent": recent,
        "plan": plan,
    }
    return api_response(success=True, message="Overview fetched", data=data)


@router.get("/live")
async def live_calls(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    clinic_id = to_uuid(current_user.get("clinic_id"))
    if clinic_id is None:
        return api_response(success=False, message="No clinic associated with user", status_code=400)
    rows = (await db.execute(
        select(CallLog)
        .where(CallLog.clinic_id == clinic_id, CallLog.status == "active")
        .order_by(CallLog.created_at.desc())
    )).scalars().all()
    data = [{
        "id": str(r.id),
        "caller": r.caller_name or r.phone or "Unknown",
        "phone": r.phone,
        "direction": r.direction or "inbound",
        "startedAt": r.created_at.isoformat() if r.created_at else None,
        "turns": len(r.transcript or []),
    } for r in rows]
    return api_response(success=True, message="Live calls fetched", data=data)
