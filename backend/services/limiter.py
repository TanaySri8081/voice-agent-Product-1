from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared rate limiter (in-memory). Imported by app.py (wiring) and by routes
# that apply per-endpoint limits via @limiter.limit(...).
limiter = Limiter(key_func=get_remote_address)
