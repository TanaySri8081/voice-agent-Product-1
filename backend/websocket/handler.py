import base64
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.services.db import get_database
from backend.integrations.minimax.stt import MiniMaxSTT
from backend.integrations.minimax.llm import call_minimax_llm
from backend.integrations.minimax.tts import stream_minimax_tts_pcm
from backend.integrations.vobiz.client import VobizClient
from backend.config.settings import settings

logger = logging.getLogger("vobiz-websocket")
router = APIRouter(tags=["Websocket"])

@router.websocket("/media-stream")
async def handle_media_stream(websocket: WebSocket):
    await websocket.accept()
    logger.info("Accepted incoming Vobiz media stream connection.")
    
    db = get_database()
    vobiz_client = VobizClient()
    stt = MiniMaxSTT()
    
    # Extract query params from WebSocket URL connection for tenant mapping
    query_params = websocket.query_params
    destination = query_params.get("destination", "")
    caller_phone = query_params.get("phone", "")
    
    logger.info(f"Connection metadata: DID={destination}, Caller={caller_phone}")
    
    # 1. Resolve Tenant Context
    clinic_id = None
    system_prompt = settings.SYSTEM_PROMPT
    clinic_name = "Rapid X High School"  # default fallback
    
    if db is not None and destination:
        tenant = await db.tenants.find_one({"did": destination})
        if tenant:
            clinic_id = str(tenant["_id"])
            clinic_name = tenant.get("name", "Clinic")
            system_prompt = tenant.get("system_prompt", settings.SYSTEM_PROMPT)
            logger.info(f"Resolved call to clinic: {clinic_name} (ID: {clinic_id})")
        else:
            logger.warning(f"No tenant mapping found for DID: {destination}. Using default configuration.")
            
    chat_history = [
        {"role": "system", "content": system_prompt}
    ]
    
    call_id = None
    stream_id = None
    
    try:
        async for message in websocket.iter_text():
            data = json.loads(message)
            event = data.get("event")
            
            if event == "start":
                start_data = data.get("start", {})
                call_id = start_data.get("callId")
                stream_id = start_data.get("streamId")
                logger.info(f"Vobiz stream started. Call ID: {call_id}, Stream ID: {stream_id}")
                
                # Update call status in database if connected
                if db is not None and call_id:
                    await db.call_logs.update_one(
                        {"call_id": call_id},
                        {
                            "$set": {
                                "status": "active",
                                "clinic_id": clinic_id,
                                "caller_name": caller_phone,
                                "phone": caller_phone,
                                "direction": "inbound" if not query_params.get("outbound") else "outbound"
                            }
                        },
                        upsert=True
                    )
                
                # Generate and stream initial greeting
                greeting_prompt = settings.INITIAL_GREETING
                greeting_reply = await call_minimax_llm(
                    chat_history + [{"role": "user", "content": greeting_prompt}],
                    call_sid=call_id,
                    clinic_id=clinic_id,
                    db=db
                )
                
                logger.info(f"Initial Greeting: {greeting_reply}")
                chat_history.append({"role": "assistant", "content": greeting_reply})
                
                # Synthesize greeting and send to Vobiz
                async for pcm_chunk in stream_minimax_tts_pcm(greeting_reply):
                    play_msg = {
                        "event": "playAudio",
                        "media": {
                            "contentType": "audio/x-l16",
                            "sampleRate": 8000,
                            "payload": base64.b64encode(pcm_chunk).decode("utf-8")
                        }
                    }
                    await websocket.send_json(play_msg)
                    
            elif event == "media":
                media_data = data.get("media", {})
                payload = media_data.get("payload")
                if payload:
                    chunk = base64.b64decode(payload)
                    
                    # Accumulate chunk and check if speech has ended
                    is_complete = stt.add_chunk(chunk)
                    if is_complete:
                        transcript = await stt.transcribe_buffer()
                        if transcript:
                            chat_history.append({"role": "user", "content": transcript})
                            
                            # Log transcript fragment in DB if database is connected
                            if db is not None and call_id:
                                await db.call_logs.update_one(
                                    {"call_id": call_id},
                                    {"$push": {"transcript": {"role": "user", "content": transcript}}}
                                )
                            
                            # Get AI Reply
                            reply = await call_minimax_llm(
                                chat_history,
                                call_sid=call_id,
                                clinic_id=clinic_id,
                                db=db
                            )
                            logger.info(f"AI response: {reply}")
                            
                            # Check if the AI response triggers a transfer
                            if reply.startswith("__TRANSFER__:"):
                                dest = reply.split(":")[1]
                                logger.info(f"Tool execution requested call transfer to: {dest}")
                                # Execute transfer
                                await vobiz_client.transfer_active_call(call_uuid=call_id, destination=dest)
                                if db is not None and call_id:
                                    await db.call_logs.update_one(
                                        {"call_id": call_id},
                                        {"$set": {"status": "transferred"}}
                                    )
                                break
                            
                            chat_history.append({"role": "assistant", "content": reply})
                            
                            # Log assistant response to DB
                            if db is not None and call_id:
                                await db.call_logs.update_one(
                                    {"call_id": call_id},
                                    {"$push": {"transcript": {"role": "assistant", "content": reply}}}
                                )
                            
                            # Stream TTS generated reply
                            async for pcm_chunk in stream_minimax_tts_pcm(reply):
                                play_msg = {
                                    "event": "playAudio",
                                    "media": {
                                        "contentType": "audio/x-l16",
                                        "sampleRate": 8000,
                                        "payload": base64.b64encode(pcm_chunk).decode("utf-8")
                                    }
                                }
                                await websocket.send_json(play_msg)
                                
    except WebSocketDisconnect:
        logger.info(f"Vobiz stream WebSocket disconnected for Call ID: {call_id}")
        if db is not None and call_id:
            await db.call_logs.update_one(
                {"call_id": call_id},
                {"$set": {"status": "completed"}}
            )
    except Exception as e:
        logger.error(f"Error handling media stream WebSocket: {e}")
        if db is not None and call_id:
            await db.call_logs.update_one(
                {"call_id": call_id},
                {"$set": {"status": "failed"}}
            )
    finally:
        logger.info(f"Session finished for Call ID: {call_id}")
