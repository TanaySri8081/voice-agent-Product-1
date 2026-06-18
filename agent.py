import os
import certifi

# Fix for macOS SSL Certificate errors - MUST be before other imports
os.environ['SSL_CERT_FILE'] = certifi.where()

import json
import base64
import asyncio
import logging
import audioop
import httpx
from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv

# Load environment variables
load_dotenv(".env")

import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("twilio-agent")

app = FastAPI()

# Store chat histories per streamSid/callSid
chat_histories = {}

def lookup_user(phone: str):
    """Mock function to look up user details."""
    logger.info(f"Looking up user: {phone}")
    return "User found: Shreyas Raj. Status: Premium. Last order: Coffee setup (Delivered)."

async def transfer_call(call_sid: str, destination: str = None):
    """Transfer the Twilio call using the Twilio REST API to redirect it."""
    if not destination:
        destination = config.DEFAULT_TRANSFER_NUMBER
        if not destination:
            return "Error: No default transfer number configured."

    # Format destination
    destination = destination.replace("tel:", "")
    if "@" in destination:
        if not destination.startswith("sip:"):
            destination = f"sip:{destination}"

    logger.info(f"Initiating Twilio call transfer for {call_sid} to {destination}")

    try:
        from twilio.rest import Client
        client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
        
        # Redirect the call to our transfer TwiML endpoint
        transfer_url = f"{config.SERVER_URL}/twiml/transfer?destination={destination}"
        client.calls(call_sid).update(url=transfer_url)
        return f"Transfer to {destination} initiated successfully."
    except Exception as e:
        logger.error(f"Failed to transfer call: {e}")
        return f"Error executing transfer: {e}"

async def call_minimax_llm_with_tools(messages, call_sid):
    """Call MiniMax LLM and handle tool calling recursively if requested."""
    headers = {
        "Authorization": f"Bearer {config.MINIMAX_API_KEY}",
        "Content-Type": "application/json"
    }
    
    url = "https://api.minimax.chat/v1/text/chatcompletion_v2"
    if config.MINIMAX_GROUP_ID:
        url += f"?GroupId={config.MINIMAX_GROUP_ID}"
        
    tools = [
        {
            "type": "function",
            "function": {
                "name": "lookup_user",
                "description": "Look up user details by phone number.",
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
                "name": "transfer_call",
                "description": "Transfer the call to a human support agent or another phone number.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "destination": {
                            "type": "string",
                            "description": "The phone number or SIP URI to transfer the call to"
                        }
                    }
                }
            }
        }
    ]
    
    payload = {
        "model": config.DEFAULT_LLM_MODEL,
        "messages": messages,
        "temperature": config.MINIMAX_LLM_TEMPERATURE,
        "tools": tools
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                logger.error(f"MiniMax LLM API error: {response.status_code} - {response.text}")
                return "I'm sorry, I encountered an error checking my tools."
                
            result = response.json()
            if "choices" not in result or len(result["choices"]) == 0:
                return "I'm sorry, I didn't get a response."
                
            choice = result["choices"][0]
            message = choice["message"]
            
            # If the model wants to call tools
            if "tool_calls" in message and message["tool_calls"]:
                logger.info(f"Model requested tool calls: {message['tool_calls']}")
                messages.append(message)
                
                # Execute tool calls
                for tool_call in message["tool_calls"]:
                    tool_call_id = tool_call.get("id")
                    func_name = tool_call["function"]["name"]
                    arguments = json.loads(tool_call["function"]["arguments"])
                    
                    if func_name == "lookup_user":
                        func_result = lookup_user(arguments.get("phone"))
                    elif func_name == "transfer_call":
                        func_result = await transfer_call(call_sid, arguments.get("destination"))
                    else:
                        func_result = f"Error: Tool {func_name} not found."
                        
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": func_name,
                        "content": func_result
                    })
                
                # Recursively call LLM with the updated history
                return await call_minimax_llm_with_tools(messages, call_sid)
            else:
                return message["content"]
        except Exception as e:
            logger.error(f"Error calling MiniMax LLM: {e}")
            return "I'm sorry, I'm having trouble processing that request."

async def stream_minimax_tts(text, websocket, stream_sid):
    """Stream TTS from MiniMax, convert 16-bit PCM to 8-bit Mu-law, and send to Twilio."""
    headers = {
        "Authorization": f"Bearer {config.MINIMAX_API_KEY}",
        "Content-Type": "application/json"
    }
    
    url = "https://api.minimax.io/v1/t2a_v2"
    if config.MINIMAX_GROUP_ID:
        url += f"?GroupId={config.MINIMAX_GROUP_ID}"
    
    payload = {
        "model": config.MINIMAX_TTS_MODEL,
        "text": text,
        "stream": True,
        "voice_setting": {
            "voice_id": config.MINIMAX_TTS_VOICE,
            "speed": 1,
            "vol": 1,
            "pitch": 0
        },
        "audio_setting": {
            "sample_rate": 8000,
            "bitrate": 32000,
            "format": "pcm",
            "channel": 1
        },
        "stream_options": {
            "exclude_aggregated_audio": True
        }
    }
    
    logger.info(f"Starting MiniMax TTS synthesis: {text[:50]}...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    err_content = await response.aread()
                    logger.error(f"MiniMax TTS error: {response.status_code} - {err_content}")
                    return
                
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        try:
                            data_str = line[5:].strip()
                            data_json = json.loads(data_str)
                            
                            hex_data = data_json.get("data", "")
                            if hex_data:
                                pcm_bytes = bytes.fromhex(hex_data)
                                # Convert PCM to Mu-law
                                # 16-bit linear PCM has sample width of 2
                                mulaw_bytes = audioop.lin2ulaw(pcm_bytes, 2)
                                
                                # Send to Twilio
                                base64_audio = base64.b64encode(mulaw_bytes).decode("utf-8")
                                twilio_msg = {
                                    "event": "media",
                                    "streamSid": stream_sid,
                                    "media": {
                                        "payload": base64_audio
                                    }
                                }
                                await websocket.send_json(twilio_msg)
                        except Exception as e:
                            logger.error(f"Error parsing MiniMax TTS line: {e}")
        except Exception as e:
            logger.error(f"Error in TTS streaming connection: {e}")

@app.post("/twiml/outbound")
async def outbound_twiml():
    """Returns the TwiML response instructing Twilio to open a WebSocket connection."""
    ws_url = config.SERVER_URL.replace("https://", "wss://").replace("http://", "ws://")
    
    twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{ws_url}/media-stream" />
    </Connect>
</Response>
"""
    return Response(content=twiml_response, media_type="application/xml")

@app.post("/twiml/inbound")
async def inbound_twiml():
    """Returns TwiML for inbound calls routing to the Media Stream."""
    ws_url = config.SERVER_URL.replace("https://", "wss://").replace("http://", "ws://")
    
    twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Thank you for calling. Connecting to the school receptionist.</Say>
    <Connect>
        <Stream url="{ws_url}/media-stream" />
    </Connect>
</Response>
"""
    return Response(content=twiml_response, media_type="application/xml")

@app.post("/twiml/transfer")
async def transfer_twiml(destination: str):
    """Returns the TwiML response to transfer/redirect the call."""
    if destination.startswith("sip:"):
        dial_element = f"<Sip>{destination}</Sip>"
    else:
        dial_element = f"<Number>{destination}</Number>"
        
    twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Transferring your call now. Please hold.</Say>
    <Dial>
        {dial_element}
    </Dial>
</Response>
"""
    return Response(content=twiml_response, media_type="application/xml")

@app.websocket("/media-stream")
async def handle_media_stream(websocket: WebSocket):
    await websocket.accept()
    logger.info("Twilio media stream WebSocket connection accepted.")
    
    stream_sid = None
    call_sid = None
    
    # Establish connection with Deepgram STT
    try:
        dg_url = "wss://api.deepgram.com/v1/listen?encoding=mulaw&sample_rate=8000&channels=1"
        dg_headers = {"Authorization": f"Token {config.DEEPGRAM_API_KEY}"}
        
        import websockets as ws_lib
        async with ws_lib.connect(dg_url, extra_headers=dg_headers) as dg_socket:
            
            async def listen_deepgram():
                nonlocal stream_sid, call_sid
                try:
                    async for message in dg_socket:
                        data = json.loads(message)
                        channel = data.get("channel", {})
                        alternatives = channel.get("alternatives", [{}])
                        transcript = alternatives[0].get("transcript", "").strip()
                        
                        is_final = data.get("is_final", False)
                        
                        if transcript and is_final:
                            logger.info(f"User transcript (final): {transcript}")
                            
                            if stream_sid not in chat_histories:
                                chat_histories[stream_sid] = [
                                    {"role": "system", "content": config.SYSTEM_PROMPT}
                                ]
                            
                            chat_histories[stream_sid].append({"role": "user", "content": transcript})
                            
                            reply = await call_minimax_llm_with_tools(chat_histories[stream_sid], call_sid)
                            logger.info(f"AI response: {reply}")
                            
                            chat_histories[stream_sid].append({"role": "assistant", "content": reply})
                            await stream_minimax_tts(reply, websocket, stream_sid)
                except Exception as e:
                    logger.error(f"Error listening to Deepgram: {e}")
            
            dg_task = asyncio.create_task(listen_deepgram())
            
            async for message in websocket.iter_text():
                data = json.loads(message)
                event = data.get("event")
                
                if event == "start":
                    start_data = data["start"]
                    stream_sid = start_data["streamSid"]
                    call_sid = start_data["callSid"]
                    logger.info(f"Received Twilio start event. StreamSid: {stream_sid}, CallSid: {call_sid}")
                    
                    chat_histories[stream_sid] = [
                        {"role": "system", "content": config.SYSTEM_PROMPT}
                    ]
                    
                    # Generate and play initial greeting
                    greeting_reply = await call_minimax_llm_with_tools(
                        chat_histories[stream_sid] + [{"role": "user", "content": config.INITIAL_GREETING}],
                        call_sid
                    )
                    chat_histories[stream_sid].append({"role": "assistant", "content": greeting_reply})
                    await stream_minimax_tts(greeting_reply, websocket, stream_sid)
                    
                elif event == "media":
                    payload = data["media"]["payload"]
                    audio_chunk = base64.b64decode(payload)
                    await dg_socket.send(audio_chunk)
                    
                elif event == "stop":
                    logger.info(f"Received Twilio stop event for StreamSid: {stream_sid}")
                    break
                    
            dg_task.cancel()
            try:
                await dg_task
            except asyncio.CancelledError:
                pass
                
    except WebSocketDisconnect:
        logger.info(f"Twilio WebSocket disconnected for StreamSid: {stream_sid}")
    except Exception as e:
        logger.error(f"Error handling media stream WebSocket: {e}")
    finally:
        if stream_sid in chat_histories:
            del chat_histories[stream_sid]
        logger.info(f"Session cleaned up for StreamSid: {stream_sid}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
