import asyncio
import json
import logging
import httpx
from backend.config.settings import settings
from backend.services import repository
from backend.services.notifications import notify_new_appointment, send_customer_confirmation

logger = logging.getLogger("minimax-llm")


async def _lookup_caller(caller_phone: str, clinic_id: str) -> str:
    """Recognise the current caller by their phone number (from call context)."""
    logger.info(f"Looking up caller: {caller_phone}")
    if not caller_phone:
        return "No caller ID is available. Please ask the caller for their name."
    patient = await repository.lookup_patient_by_phone(caller_phone, clinic_id)
    if patient:
        history = patient.get("history") or []
        extra = f" Previous notes: {', '.join(history)}." if history else ""
        return f"Returning caller: {patient['name']}.{extra}"
    return "This is a new caller with no existing record yet."


def _parse_iso(dt_str):
    """Best-effort parse of an ISO 8601 datetime string to a naive datetime."""
    if not dt_str:
        return None
    from datetime import datetime as _dt
    try:
        return _dt.fromisoformat(str(dt_str).strip().replace("Z", ""))
    except (ValueError, TypeError):
        return None


async def _check_availability(appointment_at: str, clinic_id: str, duration_min: int = 30) -> str:
    """Tool: report whether a specific time is free, so the AI can offer open slots."""
    if not clinic_id:
        return "I can't check the calendar right now."
    start_dt = _parse_iso(appointment_at)
    if start_dt is None:
        return "Please give a specific date and time to check."
    available = await repository.is_slot_available(clinic_id, start_dt, duration_min)
    return "That time is available." if available else "That time is already booked; please suggest another."


async def _check_queue(caller_phone: str, clinic_id: str) -> str:
    """Tool: report the token currently being served + the caller's own token/position.

    Answers questions like "number kya chal raha hai" / "mera number kab aayega".
    Returns factual English; the model speaks it back in the caller's language.
    """
    if not clinic_id:
        return "I can't check the queue right now."
    today = repository.queue_today_str()
    status = await repository.get_queue_status(clinic_id, today, caller_phone)
    current = int(status.get("current_number") or 0)
    total = int(status.get("total_issued") or 0)
    caller_token = status.get("caller_token")
    ahead = status.get("ahead")

    if current > 0:
        base = f"Currently serving token number {current}."
    elif total > 0:
        base = "The queue hasn't started yet today; no token has been called."
    else:
        base = "No tokens have been issued yet today."

    if caller_token is not None:
        if ahead and ahead > 0:
            return f"{base} The caller's token is {caller_token}; about {ahead} people are ahead of them."
        return f"{base} The caller's token is {caller_token}; it is their turn now."
    return f"{base} I don't have this caller's token on record; ask for their token number if they have one."


async def _book_appointment(date: str, time: str, reason: str, name: str, caller_phone: str, clinic_id: str, appointment_at: str = None, duration_min: int = 30, booking_mode: str = "time") -> str:
    """Capture the caller as a lead (if new) and book for them.

    "time" mode books a specific slot (with a double-booking check); "token" mode
    assigns the caller today's next daily queue number (no specific time).
    """
    logger.info(f"Booking ({booking_mode}) for {name or caller_phone}: {date} {time} ({reason})")
    if not clinic_id:
        return "I'm unable to reach the booking system right now."

    mode = (booking_mode or "time").strip().lower()

    # ----- token / queue mode: assign a daily number, no specific time -----
    if mode == "token":
        patient = await repository.get_or_create_patient(clinic_id, caller_phone, name)
        patient_name = (patient or {}).get("name") or (name or "").strip() or "Caller"
        patient_id = (patient or {}).get("id")

        today = repository.queue_today_str()
        token_num = await repository.next_token(clinic_id, today)
        display = f"Token {token_num}"
        booked = await repository.create_appointment_record(
            clinic_id=clinic_id,
            patient_id=patient_id,
            patient_name=patient_name,
            appointment_date=display,
            reason=reason or "General enquiry",
            status="scheduled",
            appointment_at=None,
            duration_min=duration_min,
            phone=caller_phone,
            token_number=token_num,
            token_date=today,
        )
        if booked:
            try:
                asyncio.create_task(
                    notify_new_appointment(clinic_id, patient_name, display, reason or "General enquiry")
                )
                asyncio.create_task(
                    send_customer_confirmation(clinic_id, caller_phone, patient_name, display)
                )
            except RuntimeError:
                pass
            return f"Booked. {patient_name}'s token number for today is {token_num}. Tell the caller their number is {token_num}."
        return "I couldn't complete the booking. Please try again or I can transfer you."

    # ----- time mode (default): specific slot with a conflict check -----
    # Reject if the requested slot overlaps an existing scheduled appointment.
    start_dt = _parse_iso(appointment_at)
    if start_dt is not None:
        available = await repository.is_slot_available(clinic_id, start_dt, duration_min)
        if not available:
            return f"I'm sorry, {date} at {time} is already booked. Could we pick another time?"

    # Find or create the lead by the real caller phone, filling in the name if given.
    patient = await repository.get_or_create_patient(clinic_id, caller_phone, name)
    patient_name = (patient or {}).get("name") or (name or "").strip() or "Caller"
    patient_id = (patient or {}).get("id")

    when = f"{date} {time}".strip()
    booked = await repository.create_appointment_record(
        clinic_id=clinic_id,
        patient_id=patient_id,
        patient_name=patient_name,
        appointment_date=when,
        reason=reason or "General enquiry",
        status="scheduled",
        appointment_at=start_dt,
        duration_min=duration_min,
        phone=caller_phone,
    )
    if booked:
        # Fire-and-forget alerts; must not delay the spoken reply.
        try:
            asyncio.create_task(
                notify_new_appointment(clinic_id, patient_name, when, reason or "General enquiry")
            )
            asyncio.create_task(
                send_customer_confirmation(clinic_id, caller_phone, patient_name, when)
            )
        except RuntimeError:
            pass  # no running loop (e.g. unit test) — skip the alerts
        return f"Appointment confirmed for {patient_name} on {date} at {time}."
    return "I couldn't complete the booking. Please try again or I can transfer you."


def _build_tools(booking_mode="time"):
    """Tools exposed to the model. In token mode, booking assigns a daily queue
    number (no time) and a check_queue tool is added; in time mode, booking is
    slot-based and paired with check_availability."""
    token_mode = (booking_mode or "time").strip().lower() == "token"

    tools = [
        {
            "type": "function",
            "function": {
                "name": "lookup_caller",
                "description": "Look up the current caller's existing record (recognised by their phone number). Use to greet returning callers by name.",
                "parameters": {"type": "object", "properties": {}},
            },
        },
    ]

    if token_mode:
        tools.append({
            "type": "function",
            "function": {
                "name": "book_appointment",
                "description": "Book the caller into today's queue by assigning them the next token (a daily number). For businesses that serve by token number, not a fixed time. No date or time is needed. Captures the caller as a contact automatically, then tell the caller their token number.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "The caller's full name, if provided"},
                        "reason": {"type": "string", "description": "What the visit is for (optional)"},
                    },
                },
            },
        })
        tools.append({
            "type": "function",
            "function": {
                "name": "check_queue",
                "description": "Report the live queue status: which token number is being served now, and (recognised by the caller's phone) the caller's own token and how many people are ahead. Use when the caller asks things like 'number kya chal raha hai' or when their turn will come.",
                "parameters": {"type": "object", "properties": {}},
            },
        })
    else:
        tools.append({
            "type": "function",
            "function": {
                "name": "book_appointment",
                "description": "Book an appointment, reservation, site visit, or callback once you have a date and time. Call check_availability first; do not book a time that is already taken. Captures the caller as a contact automatically.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "The caller's full name, if provided"},
                        "date": {"type": "string", "description": "Preferred date (e.g. 2026-07-01 or 'tomorrow')"},
                        "time": {"type": "string", "description": "Preferred time (e.g. 10:00 AM)"},
                        "appointment_at": {"type": "string", "description": "The start time as ISO 8601 (e.g. 2026-07-02T15:00), computed from the caller's date/time and today's date. Required for scheduling."},
                        "reason": {"type": "string", "description": "What the booking is for (e.g. consultation, site visit, table for 4)"},
                    },
                    "required": ["date", "time", "appointment_at"],
                },
            },
        })
        tools.append({
            "type": "function",
            "function": {
                "name": "check_availability",
                "description": "Check whether a specific time is free before offering or confirming it to the caller.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "appointment_at": {"type": "string", "description": "The time to check as ISO 8601 (e.g. 2026-07-02T15:00)."},
                    },
                    "required": ["appointment_at"],
                },
            },
        })

    return tools


async def call_minimax_llm(messages: list, call_sid: str, clinic_id: str = None, caller_phone: str = None, model: str = None, booking_mode: str = "time") -> str:
    is_mock = not settings.MINIMAX_API_KEY or "your_minimax_api_key" in settings.MINIMAX_API_KEY
    business_name = "our business"
    booking_mode = (booking_mode or "time").strip().lower()

    if is_mock:
        logger.info("[MOCK] MiniMax API key missing/placeholder. Using mock responder.")
        if clinic_id:
            try:
                tenant = await repository.get_tenant_by_id(clinic_id)
                if tenant:
                    business_name = tenant.get("name", business_name)
            except Exception:
                pass

        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "").lower()
                break

        if not user_message or any(k in user_message for k in ("hello", "hi", "greet", "receptionist", "start")):
            return f"Hello! Thank you for calling {business_name}. I'm the AI assistant and I can help you. May I have your name?"
        elif booking_mode == "token" and any(k in user_message for k in ("number", "token", "queue", "kitna", "kitne", "aage", "chal raha", "turn")):
            logger.info("[MOCK] check_queue")
            return await _check_queue(caller_phone, clinic_id)
        elif any(k in user_message for k in ("book", "schedule", "appointment", "slot", "reservation", "visit")):
            logger.info("[MOCK] book_appointment")
            return await _book_appointment("2026-07-01", "10:00 AM", "General enquiry", None, caller_phone, clinic_id, booking_mode=booking_mode)
        elif any(k in user_message for k in ("who am i", "my details", "my record", "lookup", "recognise", "recognize")):
            return await _lookup_caller(caller_phone, clinic_id)
        else:
            return "I can help you book an appointment or answer a quick question. How can I help you today?"

    headers = {
        "Authorization": f"Bearer {settings.MINIMAX_API_KEY}",
        "Content-Type": "application/json",
    }

    url = f"{settings.MINIMAX_API_BASE}/text/chatcompletion_v2"
    if settings.MINIMAX_GROUP_ID:
        url += f"?GroupId={settings.MINIMAX_GROUP_ID}"

    payload = {
        "model": model or settings.MINIMAX_LLM_MODEL,
        "messages": messages,
        "temperature": 0.3,
        "tools": _build_tools(booking_mode),
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                logger.error(f"MiniMax LLM API error: {response.status_code} - {response.text}")
                return "I'm sorry, I'm having trouble with the system right now."

            result = response.json()
            if "choices" not in result or len(result["choices"]) == 0:
                return "I'm sorry, I didn't catch that."

            message = result["choices"][0]["message"]

            # Handle tool calling
            if message.get("tool_calls"):
                logger.info(f"Model requested tool calls: {message['tool_calls']}")
                messages.append(message)

                for tool_call in message["tool_calls"]:
                    tool_call_id = tool_call.get("id")
                    func_name = tool_call["function"]["name"]
                    try:
                        arguments = json.loads(tool_call["function"].get("arguments") or "{}")
                    except (ValueError, TypeError):
                        arguments = {}

                    if func_name == "lookup_caller":
                        func_result = await _lookup_caller(caller_phone, clinic_id)
                    elif func_name == "book_appointment":
                        func_result = await _book_appointment(
                            arguments.get("date"),
                            arguments.get("time"),
                            arguments.get("reason", "General enquiry"),
                            arguments.get("name"),
                            caller_phone,
                            clinic_id,
                            arguments.get("appointment_at"),
                            booking_mode=booking_mode,
                        )
                    elif func_name == "check_availability":
                        func_result = await _check_availability(arguments.get("appointment_at"), clinic_id)
                    elif func_name == "check_queue":
                        func_result = await _check_queue(caller_phone, clinic_id)
                    else:
                        func_result = f"Error: Tool {func_name} not found."

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": func_name,
                        "content": func_result,
                    })

                # Recurse so the model can speak a natural confirmation.
                return await call_minimax_llm(messages, call_sid, clinic_id, caller_phone, model, booking_mode)

            return message["content"]
        except Exception as e:
            logger.error(f"Error calling MiniMax LLM: {e}")
            return "I'm sorry, I ran into an internal error. Please try again."
