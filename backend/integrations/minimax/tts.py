import json
import logging
import httpx
from typing import AsyncGenerator
from backend.config.settings import settings

logger = logging.getLogger("minimax-tts")

async def stream_minimax_tts_pcm(text: str, voice: str = None, language_boost: str = None) -> AsyncGenerator[bytes, None]:
    """
    Synthesize text into raw linear 16-bit PCM bytes at 8kHz sample rate.
    Yields chunks of PCM bytes as they arrive from MiniMax.
    """
    is_mock = not settings.MINIMAX_API_KEY or "your_minimax_api_key" in settings.MINIMAX_API_KEY
    if is_mock:
        logger.info(f"[MOCK] Streaming dummy 8kHz 16-bit PCM audio for text: '{text[:40]}...'")
        import asyncio
        # Yield 20 chunks of 320 bytes (total 6400 bytes, which is 0.4 seconds of 8kHz 16-bit mono audio)
        # Each chunk is 160 samples of 16-bit audio (20ms).
        for i in range(20):
            dummy_pcm = bytearray()
            for j in range(160):
                # Alternating wave pattern to prevent flat silence
                val = 1000 if (j // 20) % 2 == 0 else -1000
                dummy_pcm.extend(val.to_bytes(2, byteorder='little', signed=True))
            yield bytes(dummy_pcm)
            await asyncio.sleep(0.01)
        return

    headers = {
        "Authorization": f"Bearer {settings.MINIMAX_API_KEY}",
        "Content-Type": "application/json"
    }
    
    url = f"{settings.MINIMAX_API_BASE}/t2a_v2"
    if settings.MINIMAX_GROUP_ID:
        url += f"?GroupId={settings.MINIMAX_GROUP_ID}"
        
    payload = {
        "model": settings.MINIMAX_TTS_MODEL,
        "text": text,
        "stream": True,
        "language_boost": language_boost or settings.MINIMAX_LANGUAGE_BOOST,
        "voice_setting": {
            "voice_id": voice or settings.MINIMAX_TTS_VOICE,
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
    
    logger.info(f"Synthesizing speech via MiniMax TTS: {text[:60]}...")
    
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

                            # In the t2a_v2 stream the audio hex lives at
                            # data.audio (a nested object), not data itself.
                            chunk = data_json.get("data")
                            hex_data = ""
                            if isinstance(chunk, dict):
                                hex_data = chunk.get("audio", "") or ""
                            elif isinstance(chunk, str):
                                hex_data = chunk
                            if hex_data:
                                pcm_bytes = bytes.fromhex(hex_data)
                                yield pcm_bytes
                        except Exception as e:
                            logger.error(f"Error parsing MiniMax TTS payload line: {e}")
        except Exception as e:
            logger.error(f"Error in MiniMax TTS streaming: {e}")
