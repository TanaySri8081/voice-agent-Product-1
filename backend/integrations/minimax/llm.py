import json
import logging
import httpx
from backend.config.settings import settings
from backend.services import repository

logger = logging.getLogger("minimax-llm")


async def _lookup_caller(caller_phone: str, clinic_id: str) -> str:
    """Recognise the current caller by their phone number (from call context)."""
    logger.info(f"Looking up caller: {caller_phone}")
    if not caller_phone:
        return "No caller ID is available. Please ask the caller for their name."
    patient = await repository.lookup_patient_by_phone(caller_phone, clinic_id)
    if patient:
        history = patient.get("history") or []
        extra = f" Past visits: {', '.join(history)}." if history else ""
        return f"Returning patient: {patient['name']}.{extra}"
    return "This is a new caller with no existing record yet."


async def _book_appointment(date: str, time: str, reason: str, name: str, caller_phone: str, clinic_id: str) -> str:
    """Capture the caller as a lead (if new) and book an appointment for them."""
    logger.info(f"Booking appointment on {date} at {time} ({reason}) for {name or caller_phone}")
    if not clinic_id:
        return "I'm unable to reach the booking system right now."

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
        reason=reason or "Consultation",
        status="scheduled",
    )
    if booked:
        return f"Appointment confirmed for {patient_name} on {date} at {time}."
    return "I couldn't complete the booking. Please try again or I can transfer you."


def _build_tools():
    return [
        {
            "type": "function",
            "function": {
                "name": "lookup_caller",
                "description": "Look up the current caller's existing record (recognised by their phone number). Use to greet returning patients by name.",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "book_appointment",
                "description": "Book an appointment for the caller once you have a date and time. Captures the caller as a contact automatically.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "The caller's full name, if provided"},
                        "date": {"type": "string", "description": "Appointment date (e.g. 2026-07-01 or 'tomorrow')"},
                        "time": {"type": "string", "description": "Appointment time (e.g. 10:00 AM)"},
                        "reason": {"type": "string", "description": "Reason for the visit (e.g. dental cleaning)"},
                    },
                    "required": ["date", "time"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "transfer_call",
                "description": "Transfer the call to a human (reception/doctor) or for emergencies.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "destination": {"type": "string", "description": "Optional phone number or SIP URI to transfer to"}
                    },
                },
            },
        },
    ]


async def call_minimax_llm(messages: list, call_sid: str, clinic_id: str = None, caller_phone: str = None, model: str = None) -> str:
    is_mock = not settings.MINIMAX_API_KEY or "your_minimax_api_key" in settings.MINIMAX_API_KEY
    clinic_name = "our clinic"

    if is_mock:
        logger.info("[MOCK] MiniMax API key missing/placeholder. Using mock responder.")
        if clinic_id:
            try:
                tenant = await repository.get_tenant_by_id(clinic_id)
                if tenant:
                    clinic_name = tenant.get("name", clinic_name)
            except Exception:
                pass

        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "").lower()
                break

        if not user_message or any(k in user_message for k in ("hello", "hi", "greet", "receptionist", "start")):
            return f"Hello! Thank you for calling {clinic_name}. I'm the AI receptionist and I can help you book an appointment. May I have your name?"
        elif any(k in user_message for k in ("book", "schedule", "appointment", "slot")):
            logger.info("[MOCK] book_appointment")
            return await _book_appointment("2026-07-01", "10:00 AM", "General consultation", None, caller_phone, clinic_id)
        elif any(k in user_message for k in ("who am i", "my details", "my record", "lookup", "recognise", "recognize")):
            return await _lookup_caller(caller_phone, clinic_id)
        elif any(k in user_message for k in ("transfer", "human", "agent", "emergency", "reception", "doctor")):
            dest = settings.DEFAULT_TRANSFER_NUMBER or "+918045671200"
            return f"__TRANSFER__:{dest}"
        else:
            return "I can help you book an appointment or answer a quick question. Would you like to schedule a visit?"

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
        "tools": _build_tools(),
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
                            arguments.get("reason", "Consultation"),
                            arguments.get("name"),
                            caller_phone,
                            clinic_id,
                        )
                    elif func_name == "transfer_call":
                        dest = arguments.get("destination") or settings.DEFAULT_TRANSFER_NUMBER
                        # Special marker tells the websocket handler to execute the transfer.
                        return f"__TRANSFER__:{dest}"
                    else:
                        func_result = f"Error: Tool {func_name} not found."

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": func_name,
                        "content": func_result,
                    })

                # Recurse so the model can speak a natural confirmation.
                return await call_minimax_llm(messages, call_sid, clinic_id, caller_phone, model)

            return message["content"]
        except Exception as e:
            logger.error(f"Error calling MiniMax LLM: {e}")
            return "I'm sorry, I ran into an internal error. Please try again."
