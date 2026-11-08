"""Serialize each session without skipping a running predecessor."""

import threading
import time
from collections import Counter
from contextlib import contextmanager
from collections.abc import Iterator


class OrderingGate:
    def __init__(self, header: dict, wait_seconds: float = 8.0):
        self.header = header
        self.wait_seconds = wait_seconds
        self.condition = threading.Condition(threading.RLock())
        self.waiting = Counter()
        self.busy = False

    @contextmanager
    def release(self, seq: int | None, finish=None) -> Iterator[bool]:
        """Yield whether an event missed its sequence position and advance on exit."""
        with self.condition:
            if seq is not None:
                self.waiting[seq] += 1
            missing_since = None
            previous = self.header["last_seq"]
            while True:
                last = self.header["last_seq"]
                stale = seq is not None and seq <= last
                if not self.busy and (seq is None or stale or seq == last + 1):
                    break
                due_present = self.waiting[last + 1] > 0
                if self.busy or due_present:
                    missing_since = None
                elif previous != last or missing_since is None:
                    missing_since = time.monotonic()
                if missing_since is not None:
                    remaining = self.wait_seconds - (time.monotonic() - missing_since)
                    if remaining <= 0:
                        future = [s for s, count in self.waiting.items() if count and s > last]
                        self.header["last_seq"] = min(future) - 1
                        missing_since = None
                        self.condition.notify_all()
                        continue
                    timeout = remaining
                else:
                    timeout = None
                previous = last
                self.condition.wait(timeout)
            if seq is not None:
                self.waiting[seq] -= 1
                if not self.waiting[seq]:
                    del self.waiting[seq]
            self.busy = True
        try:
            yield stale
        finally:
            with self.condition:
                try:
                    if seq is not None:
                        self.header["last_seq"] = max(self.header["last_seq"], seq)
                    if finish is not None:
                        finish()
                finally:
                    self.busy = False
                    self.condition.notify_all()
