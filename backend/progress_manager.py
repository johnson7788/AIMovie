"""
In-memory progress event manager for SSE streaming.

Each background task emits events as it progresses through pipeline stages.
The SSE endpoint subscribes to these events and streams them to the frontend.
"""

import asyncio
import time
from typing import Optional


class ProgressManager:
    """Singleton pub/sub for per-task progress events."""

    _instance: Optional["ProgressManager"] = None

    def __init__(self):
        # task_id -> list of accumulated event dicts
        self._events: dict[str, list[dict]] = {}
        # task_id -> list of asyncio.Event (waiters for new events)
        self._waiters: dict[str, list[asyncio.Event]] = {}
        # task_id -> bool (terminal event sent)
        self._completed: dict[str, bool] = {}
        # task_id -> str (working_dir for file serving)
        self._working_dirs: dict[str, str] = {}

    @classmethod
    def get_instance(cls) -> "ProgressManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_working_dir(self, task_id: str, working_dir: str):
        self._working_dirs[task_id] = working_dir

    def get_working_dir(self, task_id: str) -> Optional[str]:
        return self._working_dirs.get(task_id)

    def emit(self, task_id: str, event: dict):
        """Emit a progress event for a task."""
        # Add timestamp if not present
        if "timestamp" not in event:
            event["timestamp"] = time.time()

        if task_id not in self._events:
            self._events[task_id] = []
        self._events[task_id].append(event)

        # Notify all waiters
        waiters = self._waiters.get(task_id, [])
        for waiter in waiters:
            waiter.set()
        waiters.clear()

        # Mark terminal
        if event.get("type") in ("complete", "error"):
            self._completed[task_id] = True
            # Notify any remaining waiters
            for waiter in self._waiters.get(task_id, []):
                waiter.set()
            self._waiters[task_id] = []

    def is_completed(self, task_id: str) -> bool:
        return self._completed.get(task_id, False)

    def mark_completed(self, task_id: str):
        self._completed[task_id] = True
        # Wake up any remaining waiters
        for waiter in self._waiters.get(task_id, []):
            waiter.set()
        self._waiters[task_id] = []

    async def subscribe(self, task_id: str, from_index: int = 0, timeout: Optional[float] = None) -> list[dict]:
        """Get all existing events from from_index, then wait for new ones.

        Returns the full list of events. Blocks until at least one new event
        arrives, the task completes, or the optional timeout elapses.

        When timeout is reached, returns whatever events are available.
        """
        events = self._events.get(task_id, [])

        # If there are new events already, or task is complete, return immediately
        if len(events) > from_index:
            return events

        if self._completed.get(task_id, False):
            return events

        # Wait for new events
        waiter = asyncio.Event()
        if task_id not in self._waiters:
            self._waiters[task_id] = []
        self._waiters[task_id].append(waiter)

        try:
            if timeout is not None:
                await asyncio.wait_for(waiter.wait(), timeout=timeout)
            else:
                await waiter.wait()
        except asyncio.TimeoutError:
            pass  # Timeout is expected — caller will retry
        except asyncio.CancelledError:
            # Remove this waiter on cancellation
            waiters = self._waiters.get(task_id, [])
            if waiter in waiters:
                waiters.remove(waiter)
            raise
        else:
            # Normal completion — remove waiter
            waiters = self._waiters.get(task_id, [])
            if waiter in waiters:
                waiters.remove(waiter)

        return self._events.get(task_id, events)

    def get_events(self, task_id: str) -> list[dict]:
        """Get all events for a task so far (non-blocking)."""
        return self._events.get(task_id, [])
