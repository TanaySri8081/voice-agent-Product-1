import os
from celery import Celery
from backend.config.settings import settings

celery_app = Celery(
    "voxpilot_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Optional configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

@celery_app.task(name="tasks.send_outbound_reminder")
def send_outbound_reminder(phone: str, did: str):
    """
    Celery task wrapper to execute outbound calls asynchronously.
    """
    import asyncio
    from backend.integrations.vobiz.client import VobizClient
    
    vobiz = VobizClient()
    answer_url = f"{settings.SERVER_URL}/api/calls/twiml/outbound?to={phone}&From={did}"
    
    # Run the async initiate call inside the Celery synchronous runner
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(vobiz.initiate_call(to_number=phone, answer_url=answer_url))
    return result
