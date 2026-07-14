import logging

from fastapi import APIRouter, Response, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.integrations.vobiz.client import VobizClient
from backend.config.settings import settings
from backend.services.db import get_db
from backend.routes.auth import get_current_user
from backend.models import CallLog
from backend.utils.helpers import api_response, serialize_models, to_uuid

logger = logging.getLogger("calls-router")
router = APIRouter(prefix="/calls", tags=["Calls"])


@router.post("/twiml/inbound")
async def inbound_twiml(to: str = Query(None), From: str = Query(None)):
    """
    Webhook handler when Vobiz receives an inbound call.
    Resolves the destination DID and answers with Stream XML.
    """
    logger.info(f"Vobiz Inbound Webhook. To: {to}, From: {From}")
    ws_url = settings.SERVER_URL.replace("https://", "wss://").replace("http://", "ws://")

    # Append routing params so the websocket knows the caller and DID mapping
    ws_endpoint = f"{ws_url}/media-stream?destination={to}&phone={From}"
    xml_response = VobizClient.get_stream_xml(ws_endpoint)
    return Response(content=xml_response, media_type="application/xml")


@router.post("/twiml/transfer")
async def transfer_twiml(destination: str):
    """
    Webhook handler returns XML instructions to dial (transfer to) a human.
    Used when the AI receptionist hands an inbound call to a person.
    """
    logger.info(f"Vobiz Transfer Webhook. Destination: {destination}")
    xml_response = VobizClient.get_transfer_xml(destination)
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
