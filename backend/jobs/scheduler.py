import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from backend.services import repository
from backend.integrations.vobiz.client import VobizClient
from backend.config.settings import settings

logger = logging.getLogger("scheduler-jobs")
scheduler = AsyncIOScheduler()

async def dispatch_appointment_reminders():
    """
    Looks up upcoming appointments within the next 24 hours, and initiates Vobiz outbound reminders.
    """
    logger.info("Running scheduled appointment reminder checks...")

    now = datetime.utcnow()
    limit = now + timedelta(hours=24)

    # Query scheduled appointments that haven't been completed/cancelled
    appointments = await repository.get_due_appointments(now.isoformat(), limit.isoformat())

    if not appointments:
        logger.info("No upcoming appointments found for reminder dispatch.")
        return

    vobiz = VobizClient()
    for appt in appointments:
        patient_id = appt.get("patient_id")
        clinic_id = appt.get("clinic_id")

        # Get patient and clinic details
        patient = await repository.get_patient_by_id(patient_id)
        tenant = await repository.get_tenant_by_id(clinic_id)

        if not patient or not tenant:
            continue

        phone = patient.get("phone")
        did = tenant.get("did")
        if not phone or not did:
            continue

        logger.info(
            f"Dispatching reminder call to {patient['name']} ({phone}) "
            f"for appointment on {appt['appointment_date']}"
        )

        # answer_url instructs Vobiz to connect the call to the media stream
        answer_url = f"{settings.SERVER_URL}/api/calls/twiml/outbound?to={phone}&From={did}"

        # Update appointment so we don't spam them with multiple reminder calls
        await repository.mark_appointment_status(appt["id"], "reminder_dispatched")

        await vobiz.initiate_call(to_number=phone, answer_url=answer_url)

def setup_scheduler():
    """
    Registers periodic cron jobs and starts the scheduler.
    """
    # Run reminder check every hour
    scheduler.add_job(dispatch_appointment_reminders, 'interval', hours=1, id='reminder_dispatch')
    scheduler.start()
    logger.info("Background job scheduler started successfully.")
