import asyncio
import json
import websockets
import base64

async def test_call():
    # Local FastAPI WebSocket address
    # We pass query parameters destination (DID) and phone (caller) to map the tenant context
    url = "ws://localhost:8000/media-stream?destination=+918045671200&phone=+919876543210"
    
    print(f"Connecting to local voice receptionist at {url}...")
    try:
        async with websockets.connect(url) as ws:
            print("Connected!")
            
            # 1. Send Vobiz "start" event
            start_event = {
                "event": "start",
                "start": {
                    "callId": "local-test-call-1234",
                    "streamId": "local-test-stream-5678"
                }
            }
            print("Sending 'start' event...")
            await ws.send(json.dumps(start_event))
            
            # 2. Listen for generated greeting (TTS playAudio events)
            print("Waiting for AI greeting responses...")
            greeting_audio_count = 0
            while True:
                response = await ws.recv()
                data = json.loads(response)
                event = data.get("event")
                
                if event == "playAudio":
                    greeting_audio_count += 1
                    # Stop printing after receiving the first few chunks to avoid flooding output
                    if greeting_audio_count == 1:
                        print("[SUCCESS] Received synthesized voice greeting audio packets from MiniMax!")
                        print(f"Sample response: {str(data)[:120]}...")
                
                # Check for silence or pause to send simulated user reply
                if greeting_audio_count >= 10:
                    break
                    
            print(f"Received total of {greeting_audio_count} audio packets for initial greeting.")
            
            # 3. Stream mock speech followed by silence
            print("\nSimulating patient speech followed by silence to trigger conversation...")
            
            # Send 15 chunks of simulated speech (RMS ~10000 > 400)
            speech_data = b'\x10\x27' * 160  # 320 bytes
            speech_payload = base64.b64encode(speech_data).decode("utf-8")
            for _ in range(15):
                speech_chunk = {
                    "event": "media",
                    "media": {
                        "payload": speech_payload
                    }
                }
                await ws.send(json.dumps(speech_chunk))
                await asyncio.sleep(0.02)
                
            # Send 80 chunks of simulated silence (exceeds the 60-chunk threshold for 1.2s silence)
            silent_payload = base64.b64encode(b'\x00' * 320).decode("utf-8")
            for _ in range(80):
                silent_chunk = {
                    "event": "media",
                    "media": {
                        "payload": silent_payload
                    }
                }
                await ws.send(json.dumps(silent_chunk))
                await asyncio.sleep(0.02)
                
            print("Speech and silence sequence sent. Waiting for AI response to utterance...")
            
            # Listen for reply audio packets
            reply_audio_count = 0
            while True:
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    data = json.loads(response)
                    event = data.get("event")
                    if event == "playAudio":
                        reply_audio_count += 1
                        if reply_audio_count == 1:
                            print("[SUCCESS] Received reply audio packets from MiniMax LLM + TTS!")
                            print(f"Sample reply packet: {str(data)[:120]}...")
                    if reply_audio_count >= 10:
                        break
                except asyncio.TimeoutError:
                    print("Timeout waiting for AI reply.")
                    break
                    
            print(f"Received total of {reply_audio_count} audio packets for the reply.")
            
    except Exception as e:
        print(f"Connection failed: {e}")
        print("Make sure your FastAPI server is running locally on port 8000 (run: python backend/app.py)")

if __name__ == "__main__":
    asyncio.run(test_call())
