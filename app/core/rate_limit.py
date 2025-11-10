import time
from collections import defaultdict, deque
from threading import Lock
from typing import Deque, Dict, Tuple


class RateLimiter:
    """Simple in-memory rate limiter keyed by a string identifier."""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._attempts: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> Tuple[bool, float]:
        """Record an attempt and return whether it is allowed along with retry-after seconds."""
        now = time.time()
        with self._lock:
            dq = self._attempts[key]
            cutoff = now - self.window_seconds
            while dq and dq[0] <= cutoff:
                dq.popleft()

            if len(dq) >= self.max_requests:
                retry_after = self.window_seconds - (now - dq[0])
                return False, max(retry_after, 0.0)

            dq.append(now)
        return True, 0.0
