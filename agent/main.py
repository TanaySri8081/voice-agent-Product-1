"""
VoxPilot LiveKit voice agent.

Runs the call pipeline: Deepgram STT -> MiniMax LLM (OpenAI-compatible) ->
MiniMax TTS (custom plugin). It joins the LiveKit room created for each inbound
SIP call (Vobiz trunk -> LiveKit SIP) and acts as a full receptionist in Hindi:
it recognises callers, registers new contacts, checks availability / queue, and
books appointments — all persisted to the dashboard's Supabase DB via secured
backend endpoints (POST /api/calls/agent-*). It also adapts per business (name,
booking mode, knowledge base) fetched at the start of each call.

The FastAPI backend is unchanged in behaviour; this is a separate worker process.
Config is read from the shared root .env (same file the backend uses).

Run:  python main.py dev      (dev mode, connects to LiveKit Cloud as a worker)
"""

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Load the shared root .env (one level up), so MINIMAX_*, DEEPGRAM_*, LIVEKIT_*,
# AGENT_* are all available to the agent.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from livekit import agents  # noqa: E402
from livekit.agents import (  # noqa: E402
    Agent,
    AgentSession,
    RoomInputOptions,
    RunContext,
    WorkerOptions,
    cli,
    function_tool,
    get_job_context,
)
from livekit.plugins import deepgram, noise_cancellation, openai, silero  # noqa: E402

from livekit.agents import llm as _lk_llm  # noqa: E402

from minimax_tts import MiniMaxTTS  # noqa: E402

logger = logging.getLogger("voxpilot-agent")

# --- Compatibility shim -----------------------------------------------------
# MiniMax's streaming chat responses can include a usage object whose token
# counts are null. LiveKit builds CompletionUsage(completion_tokens=int, ...)
# from it and crashes on None; that surfaces as a retryable "Connection error",
# so the agent retries for ~10-15s and then goes SILENT mid-call. Coerce those
# nulls to 0 so the turn completes normally. (Targets pinned livekit-agents 1.6.6;
# the parser calls `llm.CompletionUsage(...)`, so patching the module attr works.)
_OrigCompletionUsage = _lk_llm.CompletionUsage


def _lenient_completion_usage(*args, **kwargs):
    for _key in ("completion_tokens", "prompt_tokens", "total_tokens", "prompt_cached_tokens"):
        if kwargs.get(_key) is None:
            kwargs[_key] = 0
    return _OrigCompletionUsage(*args, **kwargs)


_lk_llm.CompletionUsage = _lenient_completion_usage

# Where the FastAPI backend lives + the shared secret for the internal agent
# endpoints. Both read from the root .env. If the secret is empty, all DB actions
# are disabled (the backend returns 401), so set AGENT_INTERNAL_SECRET in .env.
BACKEND_URL = os.getenv("AGENT_BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
# Prefer a dedicated secret; fall back to the app's JWT secret so bookings work
# out of the box (the backend uses the same fallback and reads this same .env).
INTERNAL_SECRET = os.getenv("AGENT_INTERNAL_SECRET") or os.getenv("JWT_SECRET", "")

# STT language code -> MiniMax TTS language hint (mirrors the backend handler).
_LANG_BOOST = {
    "hi": "Hindi", "en": "English", "es": "Spanish", "fr": "French",
    "de": "German", "pt": "Portuguese", "it": "Italian", "nl": "Dutch",
    "ja": "Japanese", "ko": "Korean", "zh": "Chinese", "ru": "Russian",
}  

# Known-good MiniMax speech-02 human voices. A tenant's stored voice is honoured
# only if it's one of these (so a stale old voice id can't degrade the call).
_GOOD_VOICES = {
    "Wise_Woman", "Friendly_Person", "Inspirational_girl", "Deep_Voice_Man",
    "Calm_Woman", "Casual_Guy", "Lively_Girl", "Patient_Man", "Young_Knight",
    "Determined_Man", "Lovely_Girl", "Decent_Boy", "Imposing_Manner",
    "Elegant_Man", "Abbess", "Sweet_Girl_2", "Exuberant_Girl",
}

# Persona + hard tool-use rules. The LLM tends to NARRATE actions (invent a token
# number, say "booked") instead of calling tools, so the rules are stated firmly
# and injected FIRST (most salient) in _build_system_prompt().
TOOL_RULES = (
    "CRITICAL RULES — follow these exactly:\n"
    "- You do NOT know any token number, queue position, slot availability, or booking status on "
    "your own. These facts exist ONLY after you call the matching tool and read its result.\n"
    "- NEVER tell the caller an appointment is booked, NEVER say a token number, NEVER say which "
    "number is being served or how many people are ahead, and NEVER say a time is free — UNLESS a "
    "tool you called in this same conversation returned that exact value. Do not guess or make up "
    "numbers. If you have not called the tool yet, call it first.\n"
    "- To actually book, you MUST call book_appointment. Just saying 'booked' does nothing.\n"
    "- To hang up, you MUST call end_call. Just saying goodbye does NOT end the call.\n"
    "- NEVER speak or write code, function names, JSON, or tool-call syntax (for example never say "
    "'functions.book_appointment(...)'). To use a tool, just call it — the caller only ever hears "
    "plain Hindi.\n"
    "- Before booking, get the caller's REAL name and CONFIRM it. Never treat filler words like "
    "'ji boliye', 'haan', 'hello', 'bataiye', 'namaste' as a name. If you did not hear the name "
    "clearly, or it sounds garbled, or you are not fully sure, say you couldn't hear it properly and "
    "ask them to say it again slowly (ask them to spell it if it is still unclear). Then say the name "
    "back to confirm and wait for a yes before continuing.\n"
    "- Do NOT push, suggest, or bring up booking on your own. Begin collecting booking details (name, "
    "age, reason) and call book_appointment ONLY when the caller ASKS to book an appointment or to get "
    "a token/number. If the caller only has a question, answer it and do not ask for their details."
)

BASE_PERSONA = (
    "You are a warm, friendly, human female phone receptionist. Speak Hindi by default, naturally "
    "and in short spoken sentences (one at a time), like a real person on the phone — never robotic, "
    "no long lists. Ask only one thing at a time and keep each reply to ONE short sentence. If "
    "something isn't in your business information, say you'll have someone follow up rather than "
    "guessing. When the caller is done (bye, thanks, 'theek hai'), say one short goodbye and then "
    "call end_call. Reply with ONLY the words to speak, in Hindi — never your thoughts or any "
    "English explanation."
)

TOKEN_MODE_GUIDE = (
    "\n\nBOOKING — this business uses TOKEN NUMBERS (a daily queue, no fixed times). Do this ONLY when "
    "the caller asks to book or get a token/number:\n"
    "- First collect the patient details described below (a CONFIRMED name, age, and reason). Do NOT "
    "ask for a date or time. Once you have them, CALL book_appointment, then tell the caller the "
    "EXACT token number that book_appointment returned.\n"
    "- If the caller asks which number is being served or how long till their turn, CALL check_queue "
    "and say only what it returns."
)

TIME_MODE_GUIDE = (
    "\n\nBOOKING — this business uses fixed TIME SLOTS. Do this ONLY when the caller asks to book an "
    "appointment:\n"
    "- Collect the patient details described below (a CONFIRMED name, age, and reason), plus the day "
    "+ time they want. Convert the time to ISO-8601 (e.g. 2026-07-02T15:00) using the current date, "
    "CALL check_availability, and if it is free CALL book_appointment with that ISO time and the "
    "patient details. If taken, offer another time. Only confirm the booking after book_appointment returns."
)

TOOLS_GUIDE = (
    "\n\nOTHER TOOLS: use lookup_caller to recognise a returning caller by their number and greet "
    "them by name; use register_patient to save a new caller's name as a contact when they are not "
    "booking."
)

# Healthcare intake: collected step-by-step before a booking. Injected via
# _build_system_prompt so the model asks for the patient's name (confirmed),
# age, and reason one at a time — and passes them to book_appointment.
PATIENT_INTAKE_GUIDE = (
    "\n\nWHEN TO BOOK — begin the booking flow ONLY when the caller asks to book an appointment or to "
    "get a token/number (e.g. 'appointment chahiye', 'token laga do', 'dikhana hai', 'number laga do'). "
    "If they only have a question (timings, address, services, fees, etc.), just answer it from your "
    "business information and ask if there is anything else — do NOT ask their name, age, or reason "
    "then, and do NOT bring up booking yourself.\n"
    "\nPATIENT INTAKE — this is a healthcare centre, so ONCE the caller wants to book (and only then), "
    "collect the patient's details ONE at a time, each in one short Hindi sentence, in this order:\n"
    "1. NAME — ask the patient's full name. If you did not hear it clearly, it sounds garbled, or you "
    "are unsure, say you couldn't hear it properly and ask them to say it again slowly (ask them to "
    "spell it if it is still unclear). Then say it back to confirm, e.g. 'मैं कन्फ़र्म कर लूँ, आपका "
    "नाम ___ है ना?', and wait for a yes.\n"
    "2. AGE — ask the patient's age (umar) in years.\n"
    "3. REASON — ask briefly what problem or symptom they want to see the doctor for.\n"
    "Only after you have a CONFIRMED name AND the age, call book_appointment with patient_name, age, "
    "reason, and gender (ONLY if the caller mentions it). Never invent any of these details; if the "
    "caller refuses a detail, proceed without it rather than making one up."
)

# Always appended (even when the tenant has its own system_prompt) so pure Hindi
# is enforced regardless of the base persona.
LANGUAGE_RULE = (
    "\n\nLANGUAGE — VERY IMPORTANT: Reply ONLY in natural, everyday spoken Hindi written in "
    "DEVANAGARI script. Do NOT use Hinglish, do NOT romanize Hindi, and do NOT mix in English words "
    "— always use the common Hindi word instead. The ONLY exception is an unavoidable proper name "
    "such as the business name. For example, say 'आपकी बुकिंग हो गई है', not 'aapki booking ho gayi'."
)

DEFAULT_GREETING = "नमस्ते! मैं आपकी कैसे मदद कर सकती हूँ?"


# ---------------------------------------------------------------------------
# Text helpers (think-tag stripper)
# ---------------------------------------------------------------------------

_THINK_OPEN = "<think>"
_THINK_CLOSE = "</think>"


def _suffix_prefix_len(s: str, tag: str) -> int:
    """Longest k where the last k chars of s equal the first k chars of tag.

    Holds back a partial tag ("<thi") that the next streamed chunk may complete,
    so tag detection survives chunk boundaries.
    """
    for k in range(min(len(s), len(tag) - 1), 0, -1):
        if s[-k:] == tag[:k]:
            return k
    return 0


async def _strip_think_stream(text):
    """Remove <think>...</think> spans from a streamed text iterator.

    Safety net: some MiniMax reasoning models (M1/M2/M3) emit chain-of-thought
    inside the reply content, which must NOT be spoken. With the default
    non-reasoning model (MiniMax-Text-01) there are no tags and this is a no-op
    apart from a tiny end-buffer that flushes at stream end.
    """
    buf = ""
    in_think = False
    async for chunk in text:
        if not chunk:
            continue
        buf += chunk
        out = ""
        while buf:
            if not in_think:
                i = buf.find(_THINK_OPEN)
                if i == -1:
                    hold = _suffix_prefix_len(buf, _THINK_OPEN)
                    if hold:
                        out += buf[:-hold]
                        buf = buf[-hold:]
                    else:
                        out += buf
                        buf = ""
                    break
                out += buf[:i]
                buf = buf[i + len(_THINK_OPEN):]
                in_think = True
            else:
                j = buf.find(_THINK_CLOSE)
                if j == -1:
                    hold = _suffix_prefix_len(buf, _THINK_CLOSE)
                    buf = buf[-hold:] if hold else ""
                    break
                buf = buf[j + len(_THINK_CLOSE):]
                in_think = False
        if out:
            yield out
    if buf and not in_think:
        yield buf


async def _clean_tts_stream(text):
    """Drop <think>...</think> AND ```...``` (code / tool-call syntax) spans from the
    streamed TTS text, so the caller never hears reasoning or code. Some MiniMax
    models write a tool call as text (```functions.end_call({})```) instead of
    calling it — this stops that from being spoken. Robust to markers split across
    chunks."""
    buf = ""
    state = "normal"  # normal | think | code
    async for chunk in text:
        if not chunk:
            continue
        buf += chunk
        out = ""
        while buf:
            if state == "normal":
                i_think = buf.find(_THINK_OPEN)
                i_code = buf.find("```")
                cands = [i for i in (i_think, i_code) if i != -1]
                if not cands:
                    hold = max(_suffix_prefix_len(buf, _THINK_OPEN), _suffix_prefix_len(buf, "```"))
                    if hold:
                        out += buf[:-hold]
                        buf = buf[-hold:]
                    else:
                        out += buf
                        buf = ""
                    break
                i = min(cands)
                out += buf[:i]
                if i == i_think:
                    buf = buf[i + len(_THINK_OPEN):]
                    state = "think"
                else:
                    buf = buf[i + 3:]
                    state = "code"
            elif state == "think":
                j = buf.find(_THINK_CLOSE)
                if j == -1:
                    hold = _suffix_prefix_len(buf, _THINK_CLOSE)
                    buf = buf[-hold:] if hold else ""
                    break
                buf = buf[j + len(_THINK_CLOSE):]
                state = "normal"
            else:  # code
                j = buf.find("```")
                if j == -1:
                    hold = _suffix_prefix_len(buf, "```")
                    buf = buf[-hold:] if hold else ""
                    break
                buf = buf[j + 3:]
                state = "normal"
        if out:
            yield out
    if buf and state == "normal":
        yield buf


# ---------------------------------------------------------------------------
# Backend + SIP helpers
# ---------------------------------------------------------------------------

def _sip_numbers(room):
    """(dialed DID, caller number) from the SIP participant attributes.

    LiveKit sets sip.trunkPhoneNumber (the called number = our DID) and
    sip.phoneNumber (the caller) on the SIP participant. (None, None) if absent.
    """
    did = caller = None
    try:
        for p in room.remote_participants.values():
            attrs = getattr(p, "attributes", None) or {}
            did = did or attrs.get("sip.trunkPhoneNumber")
            caller = caller or attrs.get("sip.phoneNumber")
    except Exception:
        pass
    return did, caller


async def _resolve_sip_numbers(ctx):
    """Wait for the SIP caller to actually JOIN, then read the dialed DID + caller
    number from its attributes.

    Reading at entrypoint start (before the participant has joined) returns
    (None, None), which forces the single-clinic fallback (get_only_tenant) and
    breaks multi-clinic routing. We also log the full attribute/metadata set so we
    can see exactly which keys LiveKit's SIP trunk populates (the DID may live under
    a different key, or need to be added via the SIP dispatch rule)."""
    part = None
    try:
        part = await asyncio.wait_for(ctx.wait_for_participant(), timeout=8.0)
    except Exception as e:
        logger.warning(f"wait_for_participant timed out/failed: {e}")
    if part is None:
        return _sip_numbers(ctx.room)
    attrs = dict(getattr(part, "attributes", None) or {})
    logger.info(
        f"SIP participant joined: identity={getattr(part, 'identity', None)!r} "
        f"kind={getattr(part, 'kind', None)} name={getattr(part, 'name', None)!r} "
        f"attrs={attrs} metadata={getattr(part, 'metadata', None)!r}"
    )
    did = attrs.get("sip.trunkPhoneNumber") or attrs.get("sip.dnis")
    caller = attrs.get("sip.phoneNumber") or attrs.get("sip.from")
    return did, caller


def _try_parse_iso(s):
    """Return an ISO-8601 string if `s` parses as a datetime, else None."""
    s = (s or "").strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).isoformat()
    except Exception:
        return None


async def _agent_post(path: str, body: dict, timeout: float = 15.0):
    """POST to a backend internal agent endpoint with the shared secret.

    Returns (status_code, data_dict). Raises on transport errors (callers handle).
    """
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{BACKEND_URL}{path}",
            headers={"X-Internal-Secret": INTERNAL_SECRET},
            json=body,
        )
    try:
        data = resp.json()
    except Exception:
        data = {}
    return resp.status_code, data


async def _fetch_context(did):
    """Load per-call business config from the backend. {} on any failure."""
    if not INTERNAL_SECRET:
        return {}
    try:
        status, data = await _agent_post("/api/calls/agent-context", {"did": did})
        if status == 200 and data.get("success"):
            return data.get("data") or {}
        logger.warning(f"agent-context -> {status} {data.get('message')}")
    except Exception as e:
        logger.warning(f"agent-context failed: {e}")
    return {}


async def _warm_llm(agent_llm) -> None:
    """Open the LLM's HTTP/TLS connection early with a tiny throwaway completion, so
    the FIRST real user turn doesn't pay a cold ~2-3s handshake (logs showed the
    first turn's TTFT ~3.9s cold vs ~1.5s warm). Since the worker is recycled after
    each call on Windows, every call otherwise starts cold. Best-effort."""
    try:
        cctx = _lk_llm.ChatContext.empty()
        cctx.add_message(role="user", content="hi")
        stream = agent_llm.chat(chat_ctx=cctx)
        try:
            async for _ in stream:
                break  # first token proves the connection is up; discard the rest
        finally:
            await stream.aclose()
    except Exception as e:
        logger.debug(f"LLM warm-up skipped: {e}")


def _build_system_prompt(ctx_data: dict) -> str:
    """Tailor the system prompt to the business + its booking mode + knowledge."""
    business = ctx_data.get("business_name") or "our business"
    mode = (ctx_data.get("booking_mode") or "time").strip().lower()
    custom = (ctx_data.get("system_prompt") or "").strip()
    kb = (ctx_data.get("knowledge_base") or "").strip()
    now_str = datetime.now().strftime("%A, %d %B %Y, %I:%M %p")

    parts = [TOOL_RULES, "\n\n", custom or BASE_PERSONA]
    parts.append(
        f"\n\nYou are the receptionist for {business}. The current date and time is {now_str}."
    )
    parts.append(LANGUAGE_RULE)
    parts.append(TOKEN_MODE_GUIDE if mode == "token" else TIME_MODE_GUIDE)
    parts.append(PATIENT_INTAKE_GUIDE)
    parts.append(TOOLS_GUIDE)
    if kb:
        parts.append(
            "\n\nBusiness information you can use to answer the caller (rely on these facts; if a "
            "question isn't covered, say you'll have someone follow up):\n" + kb
        )
    return "".join(parts)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class VoxAgent(Agent):
    """Inbound receptionist: recognises callers, registers contacts, checks
    availability/queue, books appointments, and ends the call — all via secured
    backend calls so everything lands in the dashboard's Supabase DB."""

    def __init__(self, instructions: str, clinic_id=None, did=None, booking_mode=None) -> None:
        super().__init__(instructions=instructions)
        self._clinic_id = clinic_id
        self._did = did
        self._booking_mode = booking_mode

    # --- helpers -----------------------------------------------------------

    def _call_body(self) -> dict:
        """Common identity for backend calls: clinic + DID + live caller number."""
        live_did, caller = _sip_numbers(get_job_context().room)
        return {
            "clinic_id": self._clinic_id,
            "did": self._did or live_did,
            "caller_phone": caller,
            "booking_mode": self._booking_mode,
        }

    # Strip <think>...</think> and ```code``` before it is spoken, so the caller
    # never hears reasoning or a tool call written as text. tts_node text is plain str.
    def tts_node(self, text, model_settings):
        return Agent.default.tts_node(self, _clean_tts_stream(text), model_settings)

    # --- tools -------------------------------------------------------------

    @function_tool
    async def lookup_caller(self, ctx: RunContext):
        """Recognise the current caller by their phone number: whether they're a
        known contact, their name, any notes, and their nearest upcoming
        appointment. Use to greet returning callers by name."""
        if not INTERNAL_SECRET:
            return "Record abhi check nahi kar pa rahi."
        try:
            status, data = await _agent_post("/api/calls/agent-lookup", self._call_body())
        except Exception as e:
            logger.error(f"lookup_caller failed: {e}")
            return "Record abhi check nahi kar pa rahi."
        if status == 200 and data.get("success"):
            d = data.get("data") or {}
            if d.get("known"):
                name = d.get("name") or "caller"
                up = d.get("upcoming") or {}
                if up.get("when"):
                    return f"Returning caller: {name}. Unki ek appointment hai: {up.get('when')}."
                return f"Returning caller: {name}."
            return "Naya caller hai, koi record nahi. Naam poochho."
        return "Record abhi check nahi kar pa rahi."

    @function_tool
    async def register_patient(
        self,
        ctx: RunContext,
        patient_name: str,
        age: int = 0,
        gender: str = "",
        note: str = "",
    ):
        """Register the caller as a new patient/contact (or update their details) so
        they appear in the dashboard. Call this when you learn a new caller's name
        (and, for a healthcare centre, their age), or when they want to be
        registered without booking.

        Args:
            patient_name: the caller's full, confirmed name.
            age: the patient's age in years, if given (0 if unknown).
            gender: the patient's gender, only if the caller mentions it.
            note: an optional short note about the caller (e.g. their query).
        """
        if not INTERNAL_SECRET:
            return "Details abhi save nahi kar pa rahi. Team unhe call karegi."
        body = self._call_body()
        body.update({
            "patient_name": patient_name,
            "age": age if age and age > 0 else None,
            "gender": (gender or "").strip() or None,
            "note": note or None,
        })
        try:
            status, data = await _agent_post("/api/calls/agent-patient", body)
        except Exception as e:
            logger.error(f"register_patient failed: {e}")
            return "Details abhi save nahi kar pa rahi."
        if status == 200 and data.get("success"):
            return f"{patient_name} ji ka record save ho gaya."
        return "Details abhi save nahi kar pa rahi."

    @function_tool
    async def check_availability(self, ctx: RunContext, preferred_time: str):
        """Check whether a specific date/time is free before offering or confirming
        it (time-slot businesses). preferred_time must be an ISO-8601 datetime such
        as 2026-07-02T15:00, computed from the caller's requested day/time."""
        if not INTERNAL_SECRET:
            return "Abhi calendar check nahi kar pa rahi."
        appt_at = _try_parse_iso(preferred_time)
        if not appt_at:
            return "Kripya ek specific din aur samay batayein."
        body = {"clinic_id": self._clinic_id, "did": self._did, "appointment_at": appt_at}
        try:
            status, data = await _agent_post("/api/calls/agent-availability", body)
        except Exception as e:
            logger.error(f"check_availability failed: {e}")
            return "Abhi calendar check nahi kar pa rahi."
        if status == 200 and data.get("success"):
            if (data.get("data") or {}).get("available"):
                return "Yeh samay available hai."
            return "Yeh samay pehle se booked hai; koi doosra samay suggest karein."
        return "Abhi calendar check nahi kar pa rahi."

    @function_tool
    async def check_queue(self, ctx: RunContext):
        """Report the live token/queue status: which token is being served now and,
        if known, the caller's own token and how many people are ahead. Use for
        questions like 'number kya chal raha hai' (token businesses)."""
        if not INTERNAL_SECRET:
            return "Abhi queue check nahi kar pa rahi."
        try:
            status, data = await _agent_post("/api/calls/agent-queue", self._call_body())
        except Exception as e:
            logger.error(f"check_queue failed: {e}")
            return "Abhi queue check nahi kar pa rahi."
        if status == 200 and data.get("success"):
            s = data.get("data") or {}
            cur = int(s.get("current_number") or 0)
            total = int(s.get("total_issued") or 0)
            ct = s.get("caller_token")
            ahead = s.get("ahead")
            if cur > 0:
                base = f"Abhi token number {cur} chal raha hai."
            elif total > 0:
                base = "Aaj queue abhi shuru nahi hui hai."
            else:
                base = "Aaj abhi tak koi token issue nahi hua."
            if ct is not None:
                if ahead and ahead > 0:
                    return f"{base} Aapka token {ct} hai; aapse aage lagbhag {ahead} log hain."
                return f"{base} Aapka token {ct} hai; abhi aapki baari hai."
            return base
        return "Abhi queue check nahi kar pa rahi."

    @function_tool
    async def book_appointment(
        self,
        ctx: RunContext,
        patient_name: str,
        age: int = 0,
        reason: str = "",
        gender: str = "",
        preferred_time: str = "",
    ):
        """Save the caller's appointment into the system. Call this ONCE you have
        the caller's CONFIRMED name and age (for time-slot businesses, also the
        preferred time).

        Args:
            patient_name: the caller's full, confirmed name (confirm it first).
            age: the patient's age in years (use 0 only if the caller refused to give it).
            reason: short reason / symptom for the visit, if given.
            gender: the patient's gender, only if the caller mentions it.
            preferred_time: for time-slot businesses, the desired time as ISO-8601
                (e.g. 2026-07-02T15:00). Leave empty for token/queue businesses.
        """
        if not INTERNAL_SECRET:
            logger.warning("book_appointment: AGENT_INTERNAL_SECRET not set — cannot save booking")
            return ("Abhi booking system se connect nahi ho pa raha. Caller ko boliye ki humari "
                    "team unhe thodi der mein call karegi.")
        body = self._call_body()
        body.update({
            "patient_name": patient_name,
            "age": age if age and age > 0 else None,
            "gender": (gender or "").strip() or None,
            "reason": reason or None,
            "appointment_date": preferred_time or None,
        })
        appt_at = _try_parse_iso(preferred_time)
        if appt_at:
            body["appointment_at"] = appt_at
        logger.info(f"book_appointment: clinic={self._clinic_id} name={patient_name!r} when={preferred_time!r}")
        try:
            status, data = await _agent_post("/api/calls/agent-book", body)
        except Exception as e:
            logger.error(f"book_appointment failed: {e}")
            return "Booking save karne mein dikkat aa rahi hai. Caller ko boliye koi unhe call karega."
        if status == 200 and data.get("success"):
            d = data.get("data") or {}
            if d.get("booking_mode") == "token" and d.get("token_number"):
                return f"Appointment book ho gayi. Caller ka token number {d['token_number']} hai."
            display = d.get("display")
            if display and display != "Unspecified":
                return f"Appointment book ho gayi — {display}."
            return "Appointment book ho gayi."
        if status == 409:
            return "Yeh samay pehle se booked hai. Caller se koi doosra samay poochhiye."
        logger.warning(f"book_appointment: backend said {status} {data}")
        return "Booking save nahi ho payi. Caller ko boliye ki koi unhe jaldi call karega."

    @function_tool
    async def end_call(self, ctx: RunContext):
        """End and hang up the phone call. You MUST call this to end a call — just
        saying goodbye does NOT hang up. Call it as soon as the caller signals they
        are done (bye, thanks, 'theek hai', 'bas itna hi') or their request is fully
        handled. Say one short goodbye line first, then call this immediately."""
        # Let the current spoken line (the goodbye) finish before hanging up.
        await ctx.wait_for_playout()
        await get_job_context().delete_room()


def prewarm(proc: agents.JobProcess) -> None:
    # Load the VAD once per worker process (not per call). A shorter
    # min_silence_duration detects end-of-turn faster => snappier replies. Raise
    # AGENT_VAD_MIN_SILENCE if the agent starts replying before the caller finishes.
    proc.userdata["vad"] = silero.VAD.load(
        min_silence_duration=float(os.getenv("AGENT_VAD_MIN_SILENCE", "0.4") or "0.4"),
    )


async def entrypoint(ctx: agents.JobContext) -> None:
    await ctx.connect()
    logger.info(f"Agent joined room: {ctx.room.name}")

    # Windows stability workaround: LiveKit's native (Rust) layer can panic during
    # room teardown at call-end ("malformed serialized RtcError"), leaving the
    # worker process alive but unable to accept the NEXT call. Force a clean process
    # exit once the job ends so the run-agent wrapper immediately launches a fresh
    # worker. Disable with AGENT_RECYCLE_AFTER_CALL=0 (e.g. on Linux, where this
    # native panic does not occur and one worker can serve many calls).
    if os.getenv("AGENT_RECYCLE_AFTER_CALL", "1").strip() != "0":
        async def _recycle_worker():
            logger.info("Call ended — recycling worker process (Windows teardown workaround).")
            os._exit(0)
        ctx.add_shutdown_callback(_recycle_worker)

    # Resolve who was called (DID) + fetch this business's config so the agent
    # greets, behaves, and books correctly for that specific clinic. We WAIT for the
    # SIP participant so the DID is actually available (reading too early gave
    # None -> single-clinic fallback, which can't work for multiple clinics).
    did, caller = await _resolve_sip_numbers(ctx)
    ctx_data = await _fetch_context(did)
    clinic_id = ctx_data.get("clinic_id")
    business_name = ctx_data.get("business_name") or "our business"
    logger.info(f"Call context: did={did} caller={caller} clinic={clinic_id} business={business_name!r}")

    system_prompt = os.getenv("AGENT_SYSTEM_PROMPT") or _build_system_prompt(ctx_data)

    greeting = os.getenv("AGENT_GREETING")
    if not greeting:
        greeting = (
            f"नमस्ते! {business_name} में आपका स्वागत है। मैं आपकी कैसे मदद कर सकती हूँ?"
            if business_name and business_name != "our business"
            else DEFAULT_GREETING
        )

    # Per-tenant language + voice (voice only if a known-good speech-02 id), else
    # the good defaults. .env can force these via DEEPGRAM_LANGUAGE / MINIMAX_TTS_VOICE.
    language = os.getenv("DEEPGRAM_LANGUAGE") or ctx_data.get("language") or "hi"
    # Honor ANY voice the dashboard set (a built-in voice id OR a MiniMax cloned
    # voice id). Env override wins; falls back to a good default when unset.
    tenant_voice = (ctx_data.get("voice") or "").strip()
    voice = os.getenv("MINIMAX_TTS_VOICE") or tenant_voice or "Calm_Woman"
    lang_boost = os.getenv("MINIMAX_LANGUAGE_BOOST") or _LANG_BOOST.get(language.lower(), "Hindi")

    # LLM: prefer Groq (reliable tool-calling + very low latency) when GROQ_API_KEY
    # is set; otherwise fall back to MiniMax. Both use the OpenAI-compatible client.
    # TTS stays MiniMax below, so the cloned voice is unchanged.
    _gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    _groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if _gemini_key:
        # Google Gemini via its OpenAI-compatible endpoint. The free tier allows
        # ~250k tokens/min (vs Groq free's ~12k), so this agent's larger prompt +
        # tools + knowledge base does NOT exhaust the quota and go silent mid-call.
        # Default to gemini-flash-latest: reliable + fast (~1.3s) tool-calling.
        # (gemini-flash-lite-latest was intermittently HANGING server-side —
        # requests timed out — which made the agent go silent mid-call.) Override
        # via GEMINI_LLM_MODEL if you want a different model.
        _gemini_model = os.getenv("GEMINI_LLM_MODEL", "gemini-flash-latest")
        agent_llm = openai.LLM(
            model=_gemini_model,
            api_key=_gemini_key,
            base_url=os.getenv(
                "GEMINI_API_BASE",
                "https://generativelanguage.googleapis.com/v1beta/openai/",
            ),
            temperature=0.3,
        )
        logger.info(f"LLM = Gemini ({_gemini_model})")
    elif _groq_key:
        _groq_model = os.getenv("GROQ_LLM_MODEL", "llama-3.3-70b-versatile")
        agent_llm = openai.LLM(
            model=_groq_model,
            api_key=_groq_key,
            base_url=os.getenv("GROQ_API_BASE", "https://api.groq.com/openai/v1"),
            temperature=0.3,
        )
        logger.info(f"LLM = Groq ({_groq_model})")
    else:
        agent_llm = openai.LLM(
            model=os.getenv("MINIMAX_LLM_MODEL", "MiniMax-Text-01"),
            api_key=os.getenv("MINIMAX_API_KEY"),
            base_url=os.getenv("MINIMAX_API_BASE", "https://api.minimax.io/v1"),
            temperature=0.3,
        )
        logger.info("LLM = MiniMax-Text-01 (set GEMINI_API_KEY or GROQ_API_KEY in .env)")

    # Build the TTS engine up front so its HTTP/TLS connection to MiniMax can be
    # warmed in the background (task below) WHILE the session starts. The greeting
    # is the first synth of a fresh (recycled) process, so without this warm-up it
    # pays a ~1.4s cold handshake before the caller hears anything.
    tts_engine = MiniMaxTTS(
        api_key=os.getenv("MINIMAX_API_KEY", ""),
        group_id=os.getenv("MINIMAX_GROUP_ID"),
        base_url=os.getenv("MINIMAX_API_BASE", "https://api.minimax.io/v1"),
        model=os.getenv("MINIMAX_TTS_MODEL", "speech-2.6-turbo"),
        voice=voice,
        language_boost=lang_boost,
        # Clean, unclipped MiniMax volume (1.0); loudness comes from the downstream
        # tanh limiter (gain) so audio is loud but CLEAR.
        volume=float(os.getenv("MINIMAX_TTS_VOL", "1.0") or "1.0"),
        speed=float(os.getenv("MINIMAX_TTS_SPEED", "1.0") or "1.0"),
        gain=float(os.getenv("MINIMAX_TTS_GAIN", "2.0") or "2.0"),
    )
    # Kick off the connection warm-ups now (TTS + LLM), in parallel with the
    # session start below, so the greeting and the first user turn don't pay cold
    # handshakes. TTS is awaited before the greeting; the LLM warm finishes during
    # greeting playback, before the caller's first turn.
    _tts_warm = asyncio.create_task(tts_engine.warm_up())
    _llm_warm = asyncio.create_task(_warm_llm(agent_llm))

    session = AgentSession(
        vad=ctx.proc.userdata["vad"],
        stt=deepgram.STT(
            model=os.getenv("DEEPGRAM_MODEL", "nova-2"),
            language=language,
            api_key=os.getenv("DEEPGRAM_API_KEY"),
        ),
        # LLM chosen above (Gemini / Groq / MiniMax). TTS built + warmed above.
        llm=agent_llm,
        tts=tts_engine,
        # Respond faster: start generating early, don't wait long after the caller
        # stops speaking. max_endpointing_delay was 2.0s — the biggest source of a
        # "late" reply; 1.0s feels snappy on the phone. Raise AGENT_MAX_ENDPOINTING
        # if the AI starts cutting callers off mid-sentence.
        # preemptive_generation lowers latency but can fire a 2nd LLM request per
        # turn (doubling token use) — set AGENT_PREEMPTIVE=0 to conserve Groq's
        # tight free-tier quota. Leave on for Gemini (huge free quota).
        preemptive_generation=(os.getenv("AGENT_PREEMPTIVE", "1").strip() != "0"),
        min_endpointing_delay=float(os.getenv("AGENT_MIN_ENDPOINTING", "0.4") or "0.4"),
        max_endpointing_delay=float(os.getenv("AGENT_MAX_ENDPOINTING", "1.0") or "1.0"),
        # Mark the caller "away" after this many seconds of silence; we hang up on
        # that (the LLM doesn't reliably call end_call when the caller just goes
        # quiet). Tunable via .env without code changes.
        user_away_timeout=float(os.getenv("AGENT_SILENCE_HANGUP_SEC", "10") or "10"),
    )

    # Per-turn latency metrics -> logs, so we can see exactly where time goes
    # (EOU end_of_utterance_delay = how long we waited after the caller stopped;
    # LLM ttft = time to first token; TTS ttfb = time to first audio byte).
    # Grep the agent output for "[latency]" after a test call.
    def _on_metrics(ev):
        m = ev.metrics
        parts = [type(m).__name__]
        for attr in ("end_of_utterance_delay", "transcription_delay", "ttft", "ttfb", "duration"):
            v = getattr(m, attr, None)
            if isinstance(v, (int, float)):
                parts.append(f"{attr}={v:.3f}")
        logger.info("[latency] " + " ".join(parts))

    session.on("metrics_collected", _on_metrics)

    await session.start(
        VoxAgent(instructions=system_prompt, clinic_id=clinic_id, did=did,
                 booking_mode=(ctx_data.get("booking_mode") or "time")),
        room=ctx.room,
        room_input_options=RoomInputOptions(
            # Telephony-tuned echo + noise cancellation so the agent doesn't
            # transcribe its own voice.
            noise_cancellation=noise_cancellation.BVCTelephony(),
        ),
    )

    # If the caller goes silent for user_away_timeout seconds, the session marks
    # them "away". The LLM doesn't reliably call end_call on silence, so we say a
    # short closing line and hang up.
    async def _hangup_after_silence():
        try:
            await session.say(
                "लगता है आप अभी व्यस्त हैं। मैं फ़ोन रख रही हूँ, धन्यवाद!",
                allow_interruptions=False,
            )
        except Exception:
            pass
        try:
            await get_job_context().delete_room()
        except Exception:
            pass

    def _on_user_state_changed(ev):
        if getattr(ev, "new_state", None) == "away":
            asyncio.create_task(_hangup_after_silence())

    session.on("user_state_changed", _on_user_state_changed)

    # Ensure the TTS connection warm-up (started above) has finished so the
    # greeting plays right away instead of paying a cold handshake.
    try:
        await asyncio.wait_for(_tts_warm, timeout=3.0)
    except Exception:
        pass

    # Speak the opening greeting once connected.
    await session.say(greeting, allow_interruptions=True)


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            # Explicit agent name so a LiveKit SIP dispatch rule can target it.
            agent_name="voxpilot-inbound",
            # Keep a job process pre-warmed so an incoming call doesn't wait for a
            # fresh one to spin up (the "no warmed process available" gap before the
            # greeting). Tune via AGENT_IDLE_PROCESSES.
            num_idle_processes=int(os.getenv("AGENT_IDLE_PROCESSES", "1") or "1"),
        )
    )
