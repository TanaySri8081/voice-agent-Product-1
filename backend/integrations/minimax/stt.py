"""
Speech-to-Text for the inbound call pipeline.

Transcription is powered by Deepgram (MiniMax has no STT API). This buffers the
caller's PCM audio, detects an end-of-utterance via a simple RMS silence check,
then sends the utterance to Deepgram's pre-recorded /v1/listen endpoint.

(File lives under integrations/minimax for now for import stability; it is a
Deepgram client, not MiniMax.)
"""

import io
import wave
import audioop
import logging
import httpx
from backend.config.settings import settings

logger = logging.getLogger("deepgram-stt")


class SpeechToText:
    def __init__(self, sample_rate: int = 8000, channels: int = 1, silence_threshold: int = 400, silence_duration_seconds: float = 1.2, language: str = None):
        self.sample_rate = sample_rate
        self.channels = channels
        self.sample_width = 2  # 16-bit linear PCM (2 bytes per sample)
        self.silence_threshold = silence_threshold  # RMS below which audio is "silent"
        self.language = language or settings.DEEPGRAM_LANGUAGE

        # Audio buffer and state
        self.buffer = io.BytesIO()
        self.silence_duration_seconds = silence_duration_seconds
        self.silent_chunks_limit = int((sample_rate * silence_duration_seconds * self.sample_width) / 320)
        self.silent_chunk_count = 0
        self.has_spoken = False

    def reset(self):
        self.buffer = io.BytesIO()
        self.silent_chunk_count = 0
        self.has_spoken = False

    def is_silence(self, pcm_data: bytes) -> bool:
        """Root-mean-square check to decide if a chunk is silent."""
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
        Wrap the buffered PCM as WAV and transcribe it with Deepgram.
        """
        pcm_bytes = self.buffer.getvalue()
        if not pcm_bytes:
            return ""

        # Wrap raw PCM in a WAV container so Deepgram can detect the format.
        wav_io = io.BytesIO()
        with wave.open(wav_io, "wb") as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(self.sample_width)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(pcm_bytes)

        wav_data = wav_io.getvalue()
        self.reset()  # Reset buffer for the next utterance

        if not settings.DEEPGRAM_API_KEY:
            logger.info("[MOCK] DEEPGRAM_API_KEY is missing. Returning mock transcription.")
            return "I want to book an appointment for tomorrow at 10 AM."

        headers = {
            "Authorization": f"Token {settings.DEEPGRAM_API_KEY}",
            "Content-Type": "audio/wav",
        }
        params = {
            "model": settings.DEEPGRAM_MODEL,
            "language": self.language,
            "smart_format": "true",
            "punctuate": "true",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    settings.DEEPGRAM_URL, headers=headers, params=params, content=wav_data
                )
                if response.status_code == 200:
                    result = response.json()
                    try:
                        transcript = (
                            result["results"]["channels"][0]["alternatives"][0]["transcript"]
                        ).strip()
                    except (KeyError, IndexError, TypeError):
                        transcript = ""
                    logger.info(f"Deepgram transcript: {transcript}")
                    return transcript
                else:
                    logger.error(f"Deepgram ASR error: {response.status_code} - {response.text}")
                    return ""
        except Exception as e:
            logger.error(f"Failed to transcribe audio buffer with Deepgram: {e}")
            return ""
