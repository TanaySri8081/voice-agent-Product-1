import logging
import httpx
from typing import Optional
from backend.config.settings import settings

logger = logging.getLogger("vobiz-client")

class VobizClient:
    def __init__(self):
        self.auth_id = settings.VOBIZ_USERNAME
        self.auth_token = settings.VOBIZ_PASSWORD
        self.sip_domain = settings.VOBIZ_SIP_DOMAIN
        self.from_number = settings.VOBIZ_OUTBOUND_NUMBER
        self.base_url = f"https://api.vobiz.ai/api/v1/Account/{self.auth_id}/Call/"

    async def initiate_call(self, to_number: str, answer_url: str, hangup_url: Optional[str] = None) -> dict:
        """
        Triggers an outbound call via Vobiz Programmable Voice API.
        """
        headers = {
            "Content-Type": "application/json",
            "X-Auth-ID": self.auth_id,
            "X-Auth-Token": self.auth_token
        }
        
        payload = {
            "from": self.from_number,
            "to": to_number,
            "answer_url": answer_url,
            "answer_method": "POST"
        }
        if hangup_url:
            payload["hangup_url"] = hangup_url
            
        logger.info(f"Initiating Vobiz outbound call to {to_number} via API URL: {self.base_url}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(self.base_url, headers=headers, json=payload)
                if response.status_code in [200, 201]:
                    logger.info(f"Vobiz outbound call successful: {response.json()}")
                    return {"success": True, "data": response.json()}
                else:
                    logger.error(f"Vobiz API call failed: {response.status_code} - {response.text}")
                    return {"success": False, "error": response.text}
            except Exception as e:
                logger.error(f"Error calling Vobiz API: {e}")
                return {"success": False, "error": str(e)}

    async def transfer_active_call(self, call_uuid: str, destination: str) -> bool:
        """
        Redirects an active Vobiz call using Vobiz call transfer REST API.
        """
        transfer_url = f"https://api.vobiz.ai/api/v1/Account/{self.auth_id}/Call/{call_uuid}/Transfer"
        headers = {
            "Content-Type": "application/json",
            "X-Auth-ID": self.auth_id,
            "X-Auth-Token": self.auth_token
        }
        
        # Build redirect webhook instructions url
        redirect_url = f"{settings.SERVER_URL}/api/calls/twiml/transfer?destination={destination}"
        payload = {
            "legs": "aleg",
            "aleg_url": redirect_url,
            "aleg_method": "POST"
        }
        
        logger.info(f"Transferring Vobiz call {call_uuid} to URL {redirect_url}...")
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(transfer_url, headers=headers, json=payload)
                if response.status_code == 200:
                    logger.info(f"Vobiz transfer successful: {response.text}")
                    return True
                else:
                    logger.error(f"Vobiz transfer failed: {response.status_code} - {response.text}")
                    return False
            except Exception as e:
                logger.error(f"Error transferring Vobiz call: {e}")
                return False

    @staticmethod
    def get_stream_xml(ws_url: str) -> str:
        """
        Generate Vobiz XML to redirect call media to our WebSocket server.
        """
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Stream bidirectional="true" keepCallAlive="true" contentType="audio/x-l16;rate=8000">
        {ws_url}
    </Stream>
</Response>
"""

    @staticmethod
    def get_transfer_xml(destination: str) -> str:
        """
        Generate Vobiz XML to transfer the call (SIP REFER equivalent).
        """
        if "@" in destination:
            sip_uri = destination
            if not sip_uri.startswith("sip:"):
                sip_uri = f"sip:{sip_uri}"
            dial_element = f"<Sip>{sip_uri}</Sip>"
        else:
            dial_element = f"<Number>{destination}</Number>"
            
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Please hold while we transfer your call to a staff member.</Say>
    <Dial>
        {dial_element}
    </Dial>
</Response>
"""

    @staticmethod
    def get_hangup_xml() -> str:
        """
        Generate Vobiz XML to hang up the call.
        """
        return """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Goodbye and thank you.</Say>
    <Hangup />
</Response>
"""
