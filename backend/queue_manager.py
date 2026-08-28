"""Asynchronous background event queue and simulated webhook/SMS broadcaster."""

import asyncio
from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, Optional
from backend.database import get_db_connection

logger = logging.getLogger("reflex.queue_manager")

event_queue: asyncio.Queue = asyncio.Queue()
_worker_task: Optional[asyncio.Task] = None
_shutdown_event: asyncio.Event = asyncio.Event()


async def enqueue_notification_event(event: Dict[str, Any]) -> None:
    """Enqueue an event to be processed out-of-band by the background worker."""
    await event_queue.put(event)


async def _process_single_event(event: Dict[str, Any]) -> None:
    """Simulate out-of-band SMS or Webhook delivery and update database event status."""
    order_id = event.get("order_id")
    event_type = event.get("event_type", "STATUS_CHANGED")
    payload = event.get("payload", {})

    # Simulate network dispatch latency (20ms)
    await asyncio.sleep(0.02)

    logger.info(
        "[REFLEX EVENT HUB] Dispatched %s for Order #%s: %s",
        event_type,
        order_id,
        json.dumps(payload),
    )

    # Update database record status to SENT
    try:
        conn = get_db_connection()
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE notification_events
            SET delivery_status = 'SENT', processed_at = ?
            WHERE order_id = ? AND delivery_status = 'PENDING';
            """,
            (now_iso, order_id),
        )
        conn.commit()
        conn.close()
    except Exception as err:
        logger.error("[REFLEX EVENT HUB] Failed to mark event as SENT: %s", err)


async def background_worker() -> None:
    """Continuous consumer loop taking notification items from the in-memory queue."""
    logger.info("[REFLEX EVENT HUB] Background notification worker started.")
    while not _shutdown_event.is_set():
        try:
            event = await asyncio.wait_for(event_queue.get(), timeout=1.0)
            await _process_single_event(event)
            event_queue.task_done()
        except asyncio.TimeoutError:
            continue
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.exception("[REFLEX EVENT HUB] Worker error: %s", exc)


def start_queue_worker() -> None:
    """Start background queue consumer task."""
    global _worker_task
    _shutdown_event.clear()
    _worker_task = asyncio.create_task(background_worker())


async def stop_queue_worker() -> None:
    """Gracefully drain and shut down the background worker."""
    global _worker_task
    _shutdown_event.set()
    if _worker_task:
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
        _worker_task = None
    logger.info("[REFLEX EVENT HUB] Background notification worker stopped cleanly.")
