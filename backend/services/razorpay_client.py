"""
Minimal Razorpay integration (no SDK dependency — httpx + stdlib hmac).

Flow:
  1. create_order()  -> creates a Razorpay Order server-side (amount computed
     from the plan price, never from the client).
  2. Browser opens Razorpay Checkout with the order id + public key id.
  3. On success the browser posts razorpay_order_id / _payment_id / _signature
     back; verify_payment_signature() confirms authenticity before we upgrade.
  4. Optionally a signed webhook (verify_webhook_signature) is the source of
     truth for payment.captured.

Only KEY_ID is ever sent to the browser. KEY_SECRET / WEBHOOK_SECRET stay here.
"""

import hashlib
import hmac
import logging

import httpx

from backend.config.settings import settings

logger = logging.getLogger("razorpay")

_ORDERS_URL = "https://api.razorpay.com/v1/orders"


async def create_order(amount_inr: int, receipt: str, notes: dict | None = None) -> dict:
    """Create a Razorpay order. `amount_inr` is in rupees; Razorpay wants paise."""
    if not settings.payments_enabled:
        raise RuntimeError("Payments are not configured")
    payload = {
        "amount": int(amount_inr) * 100,  # paise
        "currency": "INR",
        "receipt": receipt,
        "payment_capture": 1,
        "notes": notes or {},
    }
    async with httpx.AsyncClient(
        timeout=20.0,
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
    ) as client:
        resp = await client.post(_ORDERS_URL, json=payload)
        if resp.status_code >= 400:
            logger.error(f"Razorpay order creation failed: {resp.status_code} {resp.text}")
        resp.raise_for_status()
        return resp.json()


def verify_payment_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """Verify the checkout callback signature: HMAC_SHA256(order_id|payment_id)."""
    if not settings.RAZORPAY_KEY_SECRET or not (order_id and payment_id and signature):
        return False
    message = f"{order_id}|{payment_id}".encode("utf-8")
    expected = hmac.new(settings.RAZORPAY_KEY_SECRET.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    """Verify a Razorpay webhook using the configured webhook secret."""
    secret = settings.RAZORPAY_WEBHOOK_SECRET
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
