"""
Custom LiveKit TTS plugin for MiniMax (speech-02-turbo).

LiveKit has no built-in MiniMax TTS plugin, so we wrap MiniMax's streaming
t2a_v2 endpoint. It streams raw 16-bit PCM which we push straight into LiveKit's
AudioEmitter. This mirrors the backend's stream_minimax_tts_pcm parsing (audio
hex lives at data.audio).
"""

import json
import logging
import uuid

try:  # stdlib on Python < 3.13; hard-clip fallback amplifier for raw PCM.
    import audioop
except Exception:  # pragma: no cover - audioop removed in 3.13
    audioop = None

try:  # numpy gives a smooth tanh limiter so loud audio stays clean (no clipping).
    import numpy as _np
except Exception:  # pragma: no cover
    _np = None

import httpx
from livekit.agents import (
    DEFAULT_API_CONNECT_OPTIONS,
    APIConnectOptions,
    tts,
)

logger = logging.getLogger("minimax-tts")


def _amplify_pcm(pcm: bytes, gain: float) -> bytes:
    """Loudness boost for 16-bit mono PCM using a soft-KNEE limiter.

    Samples below the knee (80% of full scale) are amplified purely linearly and
    left untouched — so the body of the speech stays natural (no "computerized"
    coloration) — while only the loud peaks above the knee are rounded off smoothly
    (no harsh clipping / "cutting"). Falls back to audioop.mul if numpy is missing,
    and returns the input unchanged when gain == 1.0.
    """
    if not gain or gain == 1.0 or not pcm:
        return pcm
    if _np is not None:
        try:
            s = _np.frombuffer(pcm, dtype=_np.int16).astype(_np.float32) * gain
            ceil = 32767.0
            knee = 0.8 * ceil
            a = _np.abs(s)
            over = a > knee
            if bool(over.any()):
                head = ceil - knee
                s = _np.where(
                    over,
                    _np.sign(s) * (knee + head * _np.tanh((a - knee) / head)),
                    s,
                )
            _np.clip(s, -ceil, ceil, out=s)
            return s.astype(_np.int16).tobytes()
        except Exception:
            pass
    if audioop is not None:
        try:
            return audioop.mul(pcm, 2, gain)
        except Exception:
            pass
    return pcm


class MiniMaxTTS(tts.TTS):
    def __init__(
        self,
        *,
        api_key: str,
        group_id: str | None = None,
        base_url: str = "https://api.minimax.io/v1",
        model: str = "speech-02-turbo",
        voice: str = "male-qn-qingse",
        language_boost: str = "Hindi",
        sample_rate: int = 24000,
        volume: float = 1.0,
        speed: float = 1.0,
        gain: float = 1.0,
    ) -> None:
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=sample_rate,
            num_channels=1,
        )
        if not api_key:
            raise ValueError("MiniMaxTTS requires a MiniMax API key")
        self._api_key = api_key
        self._group_id = group_id
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._voice = voice
        self._language_boost = language_boost
        # MiniMax voice_setting: vol (0,10] louder>1.0; speed 1.0 = normal.
        self._volume = volume
        self._speed = speed
        # Extra digital gain applied to the decoded PCM AFTER synthesis, so the
        # line is loud enough on telephony even when MiniMax's own vol tops out.
        self._gain = gain
        # One keep-alive HTTP connection reused across sentences — see _client().
        self._http: "httpx.AsyncClient | None" = None

    def _client(self) -> httpx.AsyncClient:
        # Reuse one keep-alive connection across sentences. A fresh TLS handshake
        # to MiniMax per sentence costs ~1.4s; reusing it drops first-audio from
        # ~1.9s to ~0.5s on later sentences of the same call.
        if self._http is None or self._http.is_closed:
            # Keep the TLS connection warm for the whole call. httpx's default
            # keepalive_expiry is only 5s, so a caller pause longer than that lets
            # the connection go cold and re-adds the ~1.4s handshake on the next
            # turn. A long expiry keeps first-audio ~0.5s on every turn after the first.
            self._http = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                limits=httpx.Limits(max_keepalive_connections=1, keepalive_expiry=300.0),
            )
        return self._http

    async def aclose(self) -> None:
        if self._http is not None and not self._http.is_closed:
            await self._http.aclose()
        self._http = None
        await super().aclose()

    async def warm_up(self) -> None:
        """Open the HTTP/TLS connection to MiniMax ahead of time so the FIRST real
        synthesis (the call's greeting) doesn't pay the ~1.4s cold handshake. Sends
        a tiny throwaway synth and stops as soon as the first byte arrives; the
        connection stays in the keep-alive pool for the greeting. Best-effort.

        NOTE: named warm_up (not prewarm) on purpose — livekit's TTS base class has
        its own synchronous prewarm() that the framework calls un-awaited; overriding
        it with an async def breaks that call ("coroutine was never awaited")."""
        url = f"{self._base_url}/t2a_v2"
        if self._group_id:
            url += f"?GroupId={self._group_id}"
        payload = {
            "model": self._model,
            "text": "नमस्ते",
            "stream": True,
            "language_boost": self._language_boost,
            "voice_setting": {"voice_id": self._voice, "speed": self._speed, "vol": self._volume, "pitch": 0},
            "audio_setting": {"sample_rate": self.sample_rate, "bitrate": 128000, "format": "pcm", "channel": 1},
            "stream_options": {"exclude_aggregated_audio": True},
        }
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        try:
            client = self._client()
            async with client.stream("POST", url, headers=headers, json=payload) as resp:
                # Fully drain the (tiny) response so httpx returns the connection to
                # its keep-alive pool. Breaking early leaves a half-read response,
                # which makes httpx CLOSE the connection — then the greeting would
                # still pay a cold handshake, defeating the warm-up.
                async for _line in resp.aiter_lines():
                    pass
        except Exception:
            pass

    def synthesize(
        self, text: str, *, conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS
    ) -> "tts.ChunkedStream":
        return _MiniMaxChunkedStream(tts=self, input_text=text, conn_options=conn_options)


class _MiniMaxChunkedStream(tts.ChunkedStream):
    async def _run(self, output_emitter: "tts.AudioEmitter") -> None:
        t: MiniMaxTTS = self._tts  # set by tts.ChunkedStream.__init__

        url = f"{t._base_url}/t2a_v2"
        if t._group_id:
            url += f"?GroupId={t._group_id}"

        payload = {
            "model": t._model,
            "text": self.input_text,
            "stream": True,
            "language_boost": t._language_boost,
            "voice_setting": {"voice_id": t._voice, "speed": t._speed, "vol": t._volume, "pitch": 0},
            "audio_setting": {
                "sample_rate": t.sample_rate,
                "bitrate": 128000,
                "format": "pcm",
                "channel": 1,
            },
            "stream_options": {"exclude_aggregated_audio": True},
        }
        headers = {"Authorization": f"Bearer {t._api_key}", "Content-Type": "application/json"}

        output_emitter.initialize(
            request_id=uuid.uuid4().hex,
            sample_rate=t.sample_rate,
            num_channels=1,
            mime_type="audio/pcm",
        )

        client = t._client()
        async with client.stream("POST", url, headers=headers, json=payload) as resp:
            if resp.status_code != 200:
                body = await resp.aread()
                raise RuntimeError(f"MiniMax TTS HTTP {resp.status_code}: {body[:200]!r}")
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                try:
                    data_json = json.loads(line[5:].strip())
                except (ValueError, TypeError):
                    continue
                # In t2a_v2 the audio hex is nested at data.audio.
                chunk = data_json.get("data")
                hex_audio = ""
                if isinstance(chunk, dict):
                    hex_audio = chunk.get("audio", "") or ""
                elif isinstance(chunk, str):
                    hex_audio = chunk
                if hex_audio:
                    pcm = _amplify_pcm(bytes.fromhex(hex_audio), float(t._gain or 1.0))
                    output_emitter.push(pcm)

        output_emitter.flush()
