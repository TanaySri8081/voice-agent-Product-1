"""
Background reminder worker.

Periodically finds scheduled appointments whose start is within the reminder
lead window and hasn't been reminded yet, sends a WhatsApp reminder, and marks
it sent. Runs as an asyncio task started in the app lifespan (no external
scheduler/Celery). No-op while WhatsApp is unconfigured.

Note: `appointment_at` is naive local wall-time, so we compare against
datetime.now() (server local). If you run multiple app workers, a rare duplicate
reminder is possible; a single worker (typical for the WebSocket app) is safe.
"""

import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import select

from backend.services.db import get_sessionmaker
from backend.services.whatsapp import send_appointment_reminder, resolve_config
from backend.services import repository
from backend.config.settings import settings
from backend.models import Appointment, Tenant
from backend.utils.helpers import serialize_model

logger = logging.getLogger("reminder-worker")


async def _run_once():
    Session = get_sessionmaker()
    if Session is None:
        return
    now = datetime.now()  # naive local, matching the appointment_at convention
    horizon = now + timedelta(minutes=settings.WHATSAPP_REMINDER_LEAD_MIN)
    async with Session() as session:
        rows = (await session.execute(
            select(Appointment, Tenant)
            .join(Tenant, Tenant.id == Appointment.clinic_id)
            .where(
                Appointment.status == "scheduled",
                Appointment.reminder_sent.is_(False),
                Appointment.appointment_at.isnot(None),
                Appointment.phone.isnot(None),
                Appointment.appointment_at > now,
                Appointment.appointment_at <= horizon,
            )
        )).all()
        for appt, tenant in rows:
            config = resolve_config(serialize_model(tenant))
            if not config:
                continue  # this tenant has no WhatsApp configured
            when = appt.appointment_at.strftime("%d %b %Y, %I:%M %p")
            try:
                ok = await send_appointment_reminder(config, appt.phone, appt.patient_name, tenant.name or "", when)
            except Exception as e:
                logger.warning(f"Reminder send failed for {appt.id}: {e}")
                ok = False
            preview = f"Reminder to {appt.patient_name or 'customer'} — {tenant.name or ''} on {when}".strip()
            await repository.log_whatsapp_message(
                appt.clinic_id, appt.phone, "reminder", config.get("reminder_template"),
                preview, "sent" if ok else "failed",
            )
            if ok:
                appt.reminder_sent = True
        await session.commit()


async def reminder_loop():
    """Run reminder checks on an interval until cancelled (app shutdown)."""
    interval = max(int(settings.WHATSAPP_REMINDER_INTERVAL_SEC or 300), 30)
    logger.info(
        f"Reminder worker started (interval={interval}s, lead={settings.WHATSAPP_REMINDER_LEAD_MIN}min)."
    )
    while True:
        try:
            await _run_once()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Reminder loop iteration error: {e}")
        await asyncio.sleep(interval)
