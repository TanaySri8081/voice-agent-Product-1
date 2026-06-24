import json
import logging
import httpx
from datetime import datetime
from backend.config.settings import settings

logger = logging.getLogger("minimax-llm")

# Mock functions for tool calling, which will be integrated with database controllers later
async def mock_lookup_user(phone: str, db=None) -> str:
    logger.info(f"Looking up user: {phone}")
    if db is not None:
        patient = await db.patients.find_one({"phone": phone})
        if patient:
            return f"Patient found: {patient['name']}. Age: {patient.get('age')}. History: {', '.join(patient.get('history', []))}"
    return "Patient not found. Registered as a new patient."

async def mock_book_appointment(date: str, time: str, reason: str, clinic_id: str, phone: str, db=None) -> str:
    logger.info(f"Booking appointment on {date} at {time} for {reason}")
    if db is not None:
        # Find patient by phone
        patient = await db.patients.find_one({"phone": phone, "clinic_id": clinic_id})
        patient_name = patient["name"] if patient else "Unknown Patient"
        patient_id = str(patient["_id"]) if patient else "new"
        
        appointment_doc = {
            "clinic_id": clinic_id,
            "patient_id": patient_id,
            "patient_name": patient_name,
            "appointment_date": f"{date} {time}",
            "reason": reason,
            "status": "scheduled",
            "created_at": datetime.utcnow()
        }
        await db.appointments.insert_one(appointment_doc)
        return f"Appointment successfully scheduled for {patient_name} on {date} at {time}."
    return f"Appointment booked on {date} at {time}."

async def call_minimax_llm(messages: list, call_sid: str, clinic_id: str = None, db=None) -> str:
    # Check if we should use mock LLM response
    is_mock = not settings.MINIMAX_API_KEY or "your_minimax_api_key" in settings.MINIMAX_API_KEY
    clinic_name = "our clinic"
    
    if is_mock:
        logger.info("[MOCK] MiniMax API Key is a placeholder/missing. Using mock LLM response.")
        # Retrieve clinic name if db is available
        if db is not None and clinic_id:
            try:
                from bson import ObjectId
                tenant = await db.tenants.find_one({"_id": ObjectId(clinic_id)})
                if tenant:
                    clinic_name = tenant.get("name", clinic_name)
            except Exception:
                pass
                
        # Retrieve the last user message to determine intent
        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "").lower()
                break
        
        # Simple mock rule-based responder
        if not user_message or "hello" in user_message or "hi" in user_message or "greet" in user_message or "receptionist" in user_message or "start" in user_message:
            return f"Hello! Welcome to {clinic_name}. I am your AI receptionist. I can help you look up patient details, book an appointment, or transfer your call. How can I help you today?"
        elif "book" in user_message or "schedule" in user_message or "appointment" in user_message:
            logger.info("[MOCK] Simulating tool call execution for book_appointment.")
            res = await mock_book_appointment("2026-06-26", "10:00 AM", "General Consultation", clinic_id or "demo-clinic-123", "+919876543210", db)
            return res
        elif "lookup" in user_message or "patient" in user_message or "who am i" in user_message or "find" in user_message:
            logger.info("[MOCK] Simulating tool call execution for lookup_user.")
            res = await mock_lookup_user("+919876543210", db)
            return res
        elif "transfer" in user_message or "doctor" in user_message or "human" in user_message or "emergency" in user_message:
            logger.info("[MOCK] Simulating tool call execution for transfer_call.")
            dest = settings.DEFAULT_TRANSFER_NUMBER or "+918045671200"
            return f"__TRANSFER__:{dest}"
        else:
            return "I understand. I can help you book an appointment, look up your details, or transfer your call. What would you like to do?"

    headers = {
        "Authorization": f"Bearer {settings.MINIMAX_API_KEY}",
        "Content-Type": "application/json"
    }
    
    url = "https://api.minimax.chat/v1/text/chatcompletion_v2"
    if settings.MINIMAX_GROUP_ID:
        url += f"?GroupId={settings.MINIMAX_GROUP_ID}"
        
    tools = [
        {
            "type": "function",
            "function": {
                "name": "lookup_user",
                "description": "Look up patient details by phone number.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phone": {
                            "type": "string",
                            "description": "The phone number to look up"
                        }
                    },
                    "required": ["phone"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "book_appointment",
                "description": "Schedule a medical appointment for the patient.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "The appointment date (e.g., YYYY-MM-DD or tomorrow)"
                        },
                        "time": {
                            "type": "string",
                            "description": "The time of the appointment (e.g., 10:00 AM)"
                        },
                        "reason": {
                            "type": "string",
                            "description": "The symptom or reason for visit (e.g., dental cleaning, flu checkup)"
                        }
                    },
                    "required": ["date", "time"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "transfer_call",
                "description": "Transfer the call to a human doctor, receptionist, or emergency support.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "destination": {
                            "type": "string",
                            "description": "Optional specific phone number or SIP URI to transfer the call to"
                        }
                    }
                }
            }
        }
    ]
    
    payload = {
        "model": settings.MINIMAX_LLM_MODEL,
        "messages": messages,
        "temperature": 0.3,
        "tools": tools
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                logger.error(f"MiniMax LLM API error: {response.status_code} - {response.text}")
                return "I'm sorry, I'm having difficulty connecting to my database."
                
            result = response.json()
            if "choices" not in result or len(result["choices"]) == 0:
                return "I'm sorry, I didn't catch that."
                
            choice = result["choices"][0]
            message = choice["message"]
            
            # If the model requests tool calling
            if "tool_calls" in message and message["tool_calls"]:
                logger.info(f"Model requested tool calls: {message['tool_calls']}")
                messages.append(message)
                
                # Execute tool calls
                for tool_call in message["tool_calls"]:
                    tool_call_id = tool_call.get("id")
                    func_name = tool_call["function"]["name"]
                    arguments = json.loads(tool_call["function"]["arguments"])
                    
                    if func_name == "lookup_user":
                        func_result = await mock_lookup_user(arguments.get("phone"), db)
                    elif func_name == "book_appointment":
                        # Attempt to find Caller's phone from context
                        caller_phone = arguments.get("phone", "")
                        func_result = await mock_book_appointment(
                            arguments.get("date"),
                            arguments.get("time"),
                            arguments.get("reason", "Consultation"),
                            clinic_id,
                            caller_phone,
                            db
                        )
                    elif func_name == "transfer_call":
                        # We return a trigger string so the WebSocket handler knows to execute the transfer XML action
                        dest = arguments.get("destination") or settings.DEFAULT_TRANSFER_NUMBER
                        func_result = f"Initiating call transfer to {dest}..."
                        # Inject special marker to tell websocket to transfer
                        return f"__TRANSFER__:{dest}"
                    else:
                        func_result = f"Error: Tool {func_name} not found."
                        
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": func_name,
                        "content": func_result
                    })
                
                # Recursively call LLM with the updated history
                return await call_minimax_llm(messages, call_sid, clinic_id, db)
            else:
                return message["content"]
        except Exception as e:
            logger.error(f"Error calling MiniMax LLM: {e}")
            return "I'm sorry, I encountered an internal error. Please try again."
