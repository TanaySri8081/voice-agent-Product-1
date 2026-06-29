import io
import wave
import audioop
import logging
import httpx
from backend.config.settings import settings

logger = logging.getLogger("minimax-stt")

class MiniMaxSTT:
    def __init__(self, sample_rate: int = 8000, channels: int = 1, silence_threshold: int = 400, silence_duration_seconds: float = 1.2):
        self.sample_rate = sample_rate
        self.channels = channels
        self.sample_width = 2  # 16-bit linear PCM (2 bytes per sample)
        self.silence_threshold = silence_threshold  # RMS value below which audio is considered silent
        
        # Audio buffer and state
        self.buffer = io.BytesIO()
        self.silence_duration_seconds = silence_duration_seconds
        self.silent_chunks_limit = int((sample_rate * silence_duration_seconds * self.sample_width) / 320) # Approx chunks
        self.silent_chunk_count = 0
        self.has_spoken = False

    def reset(self):
        self.buffer = io.BytesIO()
        self.silent_chunk_count = 0
        self.has_spoken = False

    def is_silence(self, pcm_data: bytes) -> bool:
        """Calculate Root Mean Square (RMS) of PCM data to determine if it is silent."""
        if not pcm_data:
            return True
        try:
            rms = audioop.rms(pcm_data, self.sample_width)
            return rms < self.silence_threshold
        except Exception as e:
            logger.error(f"Error calculating audio RMS: {e}")
            return True

    def add_chunk(self, chunk: bytes) -> bool:
        """
        Adds a PCM chunk to the buffer.
        Returns True if an utterance is complete (silence detected after speech).
        """
        self.buffer.write(chunk)
        
        is_silent = self.is_silence(chunk)
        if not is_silent:
            self.has_spoken = True
            self.silent_chunk_count = 0
        else:
            if self.has_spoken:
                self.silent_chunk_count += 1
                if self.silent_chunk_count >= self.silent_chunks_limit:
                    logger.info("Speech pause detected. Processing utterance.")
                    return True
        return False

    async def transcribe_buffer(self) -> str:
        """
        Convert raw PCM in buffer to WAV file in-memory and send to ASR / transcription API.
        """
        pcm_bytes = self.buffer.getvalue()
        if not pcm_bytes:
            return ""

        # Create in-memory WAV container
        wav_io = io.BytesIO()
        with wave.open(wav_io, 'wb') as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(self.sample_width)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(pcm_bytes)
        
        wav_data = wav_io.getvalue()
        self.reset()  # Reset buffer for next utterance

        is_mock = not settings.STT_API_KEY
        if is_mock:
            logger.info("[MOCK] STT_API_KEY is missing. Returning mock transcription.")
            return "I want to book an appointment for tomorrow at 10 AM."

        # OpenAI-compatible transcription endpoint (MiniMax provides no STT).
        headers = {
            "Authorization": f"Bearer {settings.STT_API_KEY}"
        }

        url = f"{settings.STT_API_BASE}/audio/transcriptions"

        files = {
            "file": ("audio.wav", wav_data, "audio/wav")
        }
        data = {
            "model": settings.STT_MODEL
        }
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, headers=headers, files=files, data=data)
                if response.status_code == 200:
                    result = response.json()
                    transcript = result.get("text", "").strip()
                    logger.info(f"ASR Transcript: {transcript}")
                    return transcript
                else:
                    logger.error(f"ASR API error: {response.status_code} - {response.text}")
                    # Standard fallback / demo mock for development if API keys are not active
                    return ""
        except Exception as e:
            logger.error(f"Failed to transcribe audio buffer: {e}")
            return ""
