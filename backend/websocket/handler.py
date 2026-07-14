import base64
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.services import repository
from backend.integrations.minimax.stt import SpeechToText
from backend.integrations.minimax.llm import call_minimax_llm
from backend.integrations.minimax.tts import stream_minimax_tts_pcm
from backend.integrations.vobiz.client import VobizClient
from backend.config.settings import settings

logger = logging.getLogger("vobiz-websocket")
router = APIRouter(tags=["Websocket"])

# Maps a clinic's STT language code to MiniMax's TTS language hint.
_LANG_BOOST = {
    "hi": "Hindi", "en": "English", "es": "Spanish", "fr": "French",
    "de": "German", "pt": "Portuguese", "it": "Italian", "nl": "Dutch",
    "ja": "Japanese", "ko": "Korean", "zh": "Chinese", "ru": "Russian",
}

@router.websocket("/media-stream")
async def handle_media_stream(websocket: WebSocket):
    await websocket.accept()
    logger.info("Accepted incoming Vobiz media stream connection.")
    
    vobiz_client = VobizClient()

    # Extract query params from WebSocket URL connection for tenant mapping
    query_params = websocket.query_params
    destination = query_params.get("destination", "")
    caller_phone = query_params.get("phone", "")
    direction = "inbound" if not query_params.get("outbound") else "outbound"

    logger.info(f"Connection metadata: DID={destination}, Caller={caller_phone}")

    # 1. Resolve Tenant Context + per-clinic agent config (env values are defaults)
    clinic_id = None
    system_prompt = settings.SYSTEM_PROMPT
    clinic_name = "the clinic"  # default fallback
    agent_voice = settings.MINIMAX_TTS_VOICE
    agent_language = settings.DEEPGRAM_LANGUAGE
    agent_model = settings.MINIMAX_LLM_MODEL

    if destination:
        tenant = await repository.get_tenant_by_did(destination)
        if tenant:
            clinic_id = tenant["id"]
            clinic_name = tenant.get("name", "Clinic")
            system_prompt = tenant.get("system_prompt") or settings.SYSTEM_PROMPT
            knowledge_base = tenant.get("knowledge_base")
            if knowledge_base:
                system_prompt += (
                    "\n\nBusiness information you can use to answer the caller. "
                    "Rely on these facts; if a question isn't covered here, say you'll have "
                    "someone follow up rather than guessing.\n"
                    f"{knowledge_base}"
                )
            agent_voice = tenant.get("voice") or settings.MINIMAX_TTS_VOICE
            agent_language = tenant.get("language") or settings.DEEPGRAM_LANGUAGE
            agent_model = tenant.get("llm_model") or settings.MINIMAX_LLM_MODEL
            logger.info(f"Resolved call to clinic: {clinic_name} (ID: {clinic_id})")
        else:
            logger.warning(f"No tenant mapping found for DID: {destination}. Using default configuration.")

    agent_boost = _LANG_BOOST.get((agent_language or "").lower(), "auto")
    stt = SpeechToText(language=agent_language)
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
                
                # Create/update the call log row
                if call_id:
                    await repository.upsert_call_start(call_id, clinic_id, caller_phone, direction)
                
                # Generate and stream initial greeting
                greeting_prompt = settings.INITIAL_GREETING
                greeting_reply = await call_minimax_llm(
                    chat_history + [{"role": "user", "content": greeting_prompt}],
                    call_sid=call_id,
                    clinic_id=clinic_id,
                    caller_phone=caller_phone,
                    model=agent_model,
                )
                
                logger.info(f"Initial Greeting: {greeting_reply}")
                chat_history.append({"role": "assistant", "content": greeting_reply})
                
                # Synthesize greeting and send to Vobiz
                async for pcm_chunk in stream_minimax_tts_pcm(greeting_reply, voice=agent_voice, language_boost=agent_boost):
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
                            
                            # Log the user's utterance
                            if call_id:
                                await repository.append_transcript(call_id, "user", transcript)
                            
                            # Get AI Reply
                            reply = await call_minimax_llm(
                                chat_history,
                                call_sid=call_id,
                                clinic_id=clinic_id,
                                caller_phone=caller_phone,
                                model=agent_model,
                            )
                            logger.info(f"AI response: {reply}")
                            
                            # Check if the AI response triggers a transfer
                            if reply.startswith("__TRANSFER__:"):
                                dest = reply.split(":")[1]
                                logger.info(f"Tool execution requested call transfer to: {dest}")
                                # Execute transfer
                                await vobiz_client.transfer_active_call(call_uuid=call_id, destination=dest)
                                if call_id:
                                    await repository.set_call_status(call_id, "transferred")
                                break
                            
                            chat_history.append({"role": "assistant", "content": reply})
                            
                            # Log assistant response
                            if call_id:
                                await repository.append_transcript(call_id, "assistant", reply)
                            
                            # Stream TTS generated reply
                            async for pcm_chunk in stream_minimax_tts_pcm(reply, voice=agent_voice, language_boost=agent_boost):
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
        if call_id:
            await repository.set_call_status(call_id, "completed")
    except Exception as e:
        logger.error(f"Error handling media stream WebSocket: {e}")
        if call_id:
            await repository.set_call_status(call_id, "failed")
    finally:
        logger.info(f"Session finished for Call ID: {call_id}")
