import logging
from bson import ObjectId
from fastapi import APIRouter, Response, Depends, Query
from backend.integrations.vobiz.client import VobizClient
from backend.config.settings import settings
from backend.services.db import get_database
from backend.routes.auth import get_current_user
from backend.utils.helpers import api_response, serialize_docs

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
async def get_call_logs(current_user: dict = Depends(get_current_user)):
    """
    Retrieve call logs for the logged-in doctor's clinic.
    """
    db = get_database()
    clinic_id = current_user.get("clinic_id")
    if not clinic_id:
        return api_response(success=False, message="No clinic associated with user", status_code=400)
        
    logs = await db.call_logs.find({"clinic_id": clinic_id}).sort("created_at", -1).to_list(100)
    return api_response(
        success=True,
        message="Call logs retrieved successfully",
        data=serialize_docs(logs)
    )

@router.post("/outbound/trigger")
async def trigger_outbound(phone: str, current_user: dict = Depends(get_current_user)):
    """
    Manually dispatch an outbound call using Vobiz Client.
    """
    clinic_id = current_user.get("clinic_id")
    db = get_database()
    if not clinic_id:
        return api_response(success=False, message="No clinic associated with user", status_code=400)
        
    tenant = await db.tenants.find_one({"_id": ObjectId(clinic_id)})
    if not tenant or not tenant.get("did"):
        return api_response(success=False, message="Clinic does not have a configured Vobiz DID", status_code=400)
        
    vobiz = VobizClient()
    answer_url = f"{settings.SERVER_URL}/api/calls/twiml/outbound?to={phone}&From={tenant['did']}"
    
    result = await vobiz.initiate_call(to_number=phone, answer_url=answer_url)
    if result["success"]:
        return api_response(success=True, message="Outbound call dispatched successfully", data=result["data"])
    else:
        return api_response(success=False, message="Failed to dispatch call", error=result["error"], status_code=500)

@router.post("/campaigns/trigger")
async def trigger_campaign(phones: list[str], current_user: dict = Depends(get_current_user)):
    """
    Triggers outbound bulk calls (campaign) via Vobiz API.
    """
    clinic_id = current_user.get("clinic_id")
    db = get_database()
    if not clinic_id:
        return api_response(success=False, message="No clinic associated with user", status_code=400)
        
    tenant = await db.tenants.find_one({"_id": ObjectId(clinic_id)})
    if not tenant or not tenant.get("did"):
        return api_response(success=False, message="Clinic does not have a configured Vobiz DID", status_code=400)
        
    if not phones:
        return api_response(success=False, message="No phone numbers provided for the campaign", status_code=400)
        
    # Join numbers by '<' for Vobiz native bulk calling API
    bulk_to_string = "<".join(phones)
    vobiz = VobizClient()
    answer_url = f"{settings.SERVER_URL}/api/calls/twiml/outbound?From={tenant['did']}"
    
    result = await vobiz.initiate_call(to_number=bulk_to_string, answer_url=answer_url)
    if result["success"]:
        return api_response(
            success=True,
            message=f"Campaign bulk call triggered successfully for {len(phones)} patients",
            data=result["data"]
        )
    else:
        return api_response(
            success=False,
            message="Failed to trigger bulk campaign calls",
            error=result["error"],
            status_code=500
        )

