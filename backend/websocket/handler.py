import asyncio
import base64
import json
import logging
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.services import repository, events
from backend.services.auth_service import decode_access_token
from backend.integrations.minimax.stt import SpeechToText
from backend.integrations.minimax.llm import call_minimax_llm
from backend.integrations.minimax.tts import stream_minimax_tts_pcm
from backend.services.plans import effective_call_limit
from backend.config.settings import settings

logger = logging.getLogger("vobiz-websocket")
router = APIRouter(tags=["Websocket"])

# Maps a clinic's STT language code to MiniMax's TTS language hint.
_LANG_BOOST = {
    "hi": "Hindi", "en": "English", "es": "Spanish", "fr": "French",
    "de": "German", "pt": "Portuguese", "it": "Italian", "nl": "Dutch",
    "ja": "Japanese", "ko": "Korean", "zh": "Chinese", "ru": "Russian",
}

@router.websocket("/ws/notifications")
async def notifications_ws(websocket: WebSocket):
    """Real-time dashboard notifications for a clinic.

    Auth is via a ?token= query param (browsers can't set Authorization headers
    on a WebSocket). The clinic id is read straight from the JWT payload, so no
    DB round-trip is needed. Events are pushed as JSON; a periodic ping keeps the
    connection alive through proxies and lets us detect dead sockets.
    """
    token = websocket.query_params.get("token", "")
    payload = decode_access_token(token) if token else None
    clinic_id = (payload or {}).get("clinic_id")
    if not payload or not clinic_id:
        await websocket.close(code=4401)  # unauthorized
        return

    await websocket.accept()
    queue = events.subscribe(clinic_id)
    try:
        await websocket.send_json({"type": "connected"})
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                await websocket.send_json(event)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.info(f"Notifications websocket closed: {e}")
    finally:
        events.unsubscribe(clinic_id, queue)


@router.websocket("/media-stream")
async def handle_media_stream(websocket: WebSocket):
    await websocket.accept()
    logger.info("Accepted incoming Vobiz media stream connection.")
    
    # Extract query params from WebSocket URL connection for tenant mapping
    query_params = websocket.query_params
    destination = query_params.get("destination", "")
    caller_phone = query_params.get("phone", "")
    direction = "inbound" if not query_params.get("outbound") else "outbound"

    logger.info(f"Connection metadata: DID={destination}, Caller={caller_phone}")

    # 1. Resolve Tenant Context + per-clinic agent config (env values are defaults)
    clinic_id = None
    system_prompt = settings.SYSTEM_PROMPT
    business_name = "the business"  # default fallback
    agent_voice = settings.MINIMAX_TTS_VOICE
    agent_language = settings.DEEPGRAM_LANGUAGE
    agent_model = settings.MINIMAX_LLM_MODEL
    agent_call_limit = None  # tenant's monthly call allowance (for quota enforcement)
    agent_booking_mode = "time"  # "time" (slots) | "token" (daily queue number)

    if destination:
        tenant = await repository.get_tenant_by_did(destination)
        if tenant:
            clinic_id = tenant["id"]
            business_name = tenant.get("name", "Business")
            agent_call_limit = effective_call_limit(tenant.get("subscription"), tenant.get("monthly_call_limit"))
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
            agent_booking_mode = tenant.get("booking_mode") or "time"
            logger.info(f"Resolved call to business: {business_name} (ID: {clinic_id})")
        else:
            logger.warning(f"No tenant mapping found for DID: {destination}. Using default configuration.")

    # Give the model the current date/time, and booking guidance tailored to how
    # this business books (fixed time slots vs a daily token/queue number).
    now_str = datetime.now().strftime('%A, %d %B %Y, %I:%M %p')
    if (agent_booking_mode or "time").strip().lower() == "token":
        system_prompt += (
            f"\n\nThe current date and time is {now_str}. "
            "This business books by TOKEN NUMBER (a daily queue), not fixed time slots. "
            "To book, call book_appointment with just the caller's name and reason — it assigns "
            "the next token number for today, and you should tell the caller their token number. "
            "Do not ask for or confirm a specific appointment time. "
            "If the caller asks which number is currently being served or when their turn will come "
            "(for example 'number kya chal raha hai'), call check_queue and tell them the number "
            "currently being served, their own token number, and how many people are ahead."
        )
    else:
        system_prompt += (
            f"\n\nThe current date and time is {now_str}. "
            "When a caller requests an appointment, convert their date and time into an ISO 8601 "
            "datetime (e.g. 2026-07-02T15:00) and pass it as appointment_at. Call check_availability "
            "before confirming a time; if it is already booked, offer a different time."
        )

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

                # Quota enforcement (opt-in via ENFORCE_CALL_QUOTA, fail-open):
                # block inbound calls once a tenant is at/over its monthly allowance.
                if settings.ENFORCE_CALL_QUOTA and clinic_id and agent_call_limit:
                    try:
                        over_quota = await repository.is_over_monthly_quota(clinic_id, agent_call_limit)
                    except Exception as e:
                        logger.error(f"Quota check failed, allowing call: {e}")
                        over_quota = False
                    if over_quota:
                        logger.warning(
                            f"Clinic {clinic_id} at/over monthly quota ({agent_call_limit}); "
                            f"blocking call {call_id}"
                        )
                        if call_id:
                            await repository.upsert_call_start(call_id, clinic_id, caller_phone, direction)
                            await repository.set_call_status(call_id, "blocked")
                        async for pcm_chunk in stream_minimax_tts_pcm(
                            settings.QUOTA_EXCEEDED_MESSAGE, voice=agent_voice, language_boost=agent_boost
                        ):
                            await websocket.send_json({
                                "event": "playAudio",
                                "media": {
                                    "contentType": "audio/x-l16",
                                    "sampleRate": 8000,
                                    "payload": base64.b64encode(pcm_chunk).decode("utf-8"),
                                },
                            })
                        break

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
                    booking_mode=agent_booking_mode,
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
                                booking_mode=agent_booking_mode,
                            )
                            logger.info(f"AI response: {reply}")
                            
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
