"""
In-process pub/sub for real-time dashboard notifications.

Single process, in-memory: each connected dashboard (scoped to a clinic) gets an
asyncio.Queue; publish() fans an event out to that clinic's queues. publish() is
non-blocking and safe to call from anywhere (sync or async). Events are NOT
durable — they're only delivered to clients connected at that moment (the bell
also seeds recent history over REST, so a brief disconnect isn't a big deal).
"""

import asyncio
import logging
from collections import defaultdict

logger = logging.getLogger("events")

# clinic_id (str) -> set[asyncio.Queue]
_subscribers = defaultdict(set)


def subscribe(clinic_id) -> asyncio.Queue:
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers[str(clinic_id)].add(queue)
    return queue


def unsubscribe(clinic_id, queue) -> None:
    subs = _subscribers.get(str(clinic_id))
    if subs:
        subs.discard(queue)
        if not subs:
            _subscribers.pop(str(clinic_id), None)


def publish(clinic_id, event: dict) -> None:
    """Fan an event out to every dashboard connected for this clinic.

    No-ops when clinic_id is None or nobody is listening. Drops the event for any
    client whose queue is full (a stuck/slow tab) rather than blocking.
    """
    if clinic_id is None:
        return
    for queue in list(_subscribers.get(str(clinic_id), ())):
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            pass
