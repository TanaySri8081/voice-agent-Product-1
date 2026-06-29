import logging

from fastapi import APIRouter, Response, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.integrations.vobiz.client import VobizClient
from backend.config.settings import settings
from backend.services.db import get_db
from backend.routes.auth import get_current_user
from backend.models import Tenant, CallLog
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

    # Append routing params so websocket knows caller and DID mapping context
    ws_endpoint = f"{ws_url}/media-stream?destination={to}&phone={From}"
    xml_response = VobizClient.get_stream_xml(ws_endpoint)
    return Response(content=xml_response, media_type="application/xml")


@router.post("/twiml/outbound")
async def outbound_twiml(to: str = Query(None), From: str = Query(None)):
    """
    Webhook handler when Vobiz outbound call answers.
    """
    logger.info(f"Vobiz Outbound Webhook. To: {to}, From: {From}")
    ws_url = settings.SERVER_URL.replace("https://", "wss://").replace("http://", "ws://")

    # In outbound calls, "From" is the clinic DID and "To" is the patient
    ws_endpoint = f"{ws_url}/media-stream?destination={From}&phone={to}&outbound=true"
    xml_response = VobizClient.get_stream_xml(ws_endpoint)
    return Response(content=xml_response, media_type="application/xml")


@router.post("/twiml/transfer")
async def transfer_twiml(destination: str):
    """
    Webhook handler returns XML instructions to dial destination.
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


async def _get_clinic_did(db: AsyncSession, clinic_id):
    """Return the clinic's configured Vobiz DID, or None."""
    cid = to_uuid(clinic_id)
    if cid is None:
        return None
    result = await db.execute(select(Tenant).where(Tenant.id == cid))
    tenant = result.scalar_one_or_none()
    return tenant.did if tenant else None


@router.post("/outbound/trigger")
async def trigger_outbound(
    phone: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually dispatch an outbound call using Vobiz Client.
    """
    clinic_id = current_user.get("clinic_id")
    if not clinic_id:
        return api_response(success=False, message="No clinic associated with user", status_code=400)

    did = await _get_clinic_did(db, clinic_id)
    if not did:
        return api_response(success=False, message="Clinic does not have a configured Vobiz DID", status_code=400)

    vobiz = VobizClient()
    answer_url = f"{settings.SERVER_URL}/api/calls/twiml/outbound?to={phone}&From={did}"

    result = await vobiz.initiate_call(to_number=phone, answer_url=answer_url)
    if result["success"]:
        return api_response(success=True, message="Outbound call dispatched successfully", data=result["data"])
    else:
        return api_response(success=False, message="Failed to dispatch call", error=result["error"], status_code=500)


@router.post("/campaigns/trigger")
async def trigger_campaign(
    phones: list[str],
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Triggers outbound bulk calls (campaign) via Vobiz API.
    """
    clinic_id = current_user.get("clinic_id")
    if not clinic_id:
        return api_response(success=False, message="No clinic associated with user", status_code=400)

    did = await _get_clinic_did(db, clinic_id)
    if not did:
        return api_response(success=False, message="Clinic does not have a configured Vobiz DID", status_code=400)

    if not phones:
        return api_response(success=False, message="No phone numbers provided for the campaign", status_code=400)

    # Join numbers by '<' for Vobiz native bulk calling API
    bulk_to_string = "<".join(phones)
    vobiz = VobizClient()
    answer_url = f"{settings.SERVER_URL}/api/calls/twiml/outbound?From={did}"

    result = await vobiz.initiate_call(to_number=bulk_to_string, answer_url=answer_url)
    if result["success"]:
        return api_response(
            success=True,
            message=f"Campaign bulk call triggered successfully for {len(phones)} patients",
            data=result["data"],
        )
    else:
        return api_response(
            success=False,
            message="Failed to trigger bulk campaign calls",
            error=result["error"],
            status_code=500,
        )
