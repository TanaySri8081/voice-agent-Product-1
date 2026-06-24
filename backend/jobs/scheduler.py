import logging
from datetime import datetime, timedelta
from bson import ObjectId
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from backend.services.db import get_database
from backend.integrations.vobiz.client import VobizClient
from backend.config.settings import settings

logger = logging.getLogger("scheduler-jobs")
scheduler = AsyncIOScheduler()

async def dispatch_appointment_reminders():
    """
    Looks up upcoming appointments within the next 24 hours, and initiates Vobiz outbound reminders.
    """
    logger.info("Running scheduled appointment reminder checks...")
    db = get_database()
    if db is None:
        return
        
    now = datetime.utcnow()
    limit = now + timedelta(hours=24)
    
    # Query scheduled appointments that haven't been completed/cancelled
    appointments = await db.appointments.find({
        "status": "scheduled",
        "appointment_date": {"$gte": now.isoformat(), "$lte": limit.isoformat()}
    }).to_list(100)
    
    if not appointments:
        logger.info("No upcoming appointments found for reminder dispatch.")
        return
        
    vobiz = VobizClient()
    for appt in appointments:
        patient_id = appt.get("patient_id")
        clinic_id = appt.get("clinic_id")
        
        # Get patient details
        patient = await db.patients.find_one({"_id": ObjectId(patient_id)})
        tenant = await db.tenants.find_one({"_id": ObjectId(clinic_id)})
        
        if not patient or not tenant:
            continue
            
        phone = patient.get("phone")
        did = tenant.get("did")
        if not phone or not did:
            continue
            
        logger.info(f"Dispatching reminder call to {patient['name']} ({phone}) for appointment on {appt['appointment_date']}")
        
        # answer_url instructs Vobiz to connect the call to the media stream
        answer_url = f"{settings.SERVER_URL}/api/calls/twiml/outbound?to={phone}&From={did}"
        
        # Update appointment so we don't spam them with multiple reminder calls
        await db.appointments.update_one(
            {"_id": appt["_id"]},
            {"$set": {"status": "reminder_dispatched"}}
        )
        
        await vobiz.initiate_call(to_number=phone, answer_url=answer_url)

def setup_scheduler():
    """
    Registers periodic cron jobs and starts the scheduler.
    """
    # Run reminder check every hour
    scheduler.add_job(dispatch_appointment_reminders, 'interval', hours=1, id='reminder_dispatch')
    scheduler.start()
    logger.info("Background job scheduler started successfully.")
