# Status: [planned]

import time
from dataclasses import dataclass


@dataclass
class TokenBucket:
    capacity: int
    refill_per_second: float
    tokens: float | None = None
    updated_at: float | None = None

    def __post_init__(self) -> None:
        self.tokens = float(self.capacity) if self.tokens is None else self.tokens
        self.updated_at = time.monotonic() if self.updated_at is None else self.updated_at

    def allow(self, cost: int = 1) -> bool:
        now = time.monotonic()
        assert self.updated_at is not None
        assert self.tokens is not None
        elapsed = now - self.updated_at
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_per_second)
        self.updated_at = now
        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False
