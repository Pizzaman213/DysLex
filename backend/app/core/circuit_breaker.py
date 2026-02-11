"""Circuit breaker for external API calls.

Three states:
  CLOSED   — normal operation, requests pass through
  OPEN     — too many failures, requests are rejected immediately
  HALF_OPEN — cooldown elapsed, one probe request is allowed through

Thread-safe via asyncio.Lock.
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Coroutine

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpen(Exception):
    """Raised when the circuit is open and calls are being rejected."""

    def __init__(self, name: str):
        super().__init__(f"Circuit breaker '{name}' is OPEN — call rejected")
        self.breaker_name = name


class CircuitBreaker:
    """Async-safe circuit breaker for protecting external service calls."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        cooldown_seconds: int = 60,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Current circuit state (may transition to HALF_OPEN on read)."""
        if (
            self._state == CircuitState.OPEN
            and time.monotonic() - self._last_failure_time >= self.cooldown_seconds
        ):
            return CircuitState.HALF_OPEN
        return self._state

    async def call(self, coro: Coroutine[Any, Any, Any]) -> Any:
        """Execute *coro* through the circuit breaker.

        Raises CircuitBreakerOpen when the circuit is OPEN.
        """
        async with self._lock:
            current = self.state

            if current == CircuitState.OPEN:
                raise CircuitBreakerOpen(self.name)

            # HALF_OPEN: allow a single probe
            if current == CircuitState.HALF_OPEN:
                logger.info("Circuit '%s' HALF_OPEN — allowing probe request", self.name)

        try:
            result = await coro
        except Exception:
            await self._on_failure()
            raise

        await self._on_success()
        return result

    async def _on_success(self) -> None:
        async with self._lock:
            if self._state in (CircuitState.HALF_OPEN, CircuitState.OPEN):
                logger.info("Circuit '%s' recovered — CLOSED", self.name)
            self._state = CircuitState.CLOSED
            self._failure_count = 0

    async def _on_failure(self) -> None:
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()

            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                logger.warning(
                    "Circuit '%s' probe failed — back to OPEN (cooldown %ds)",
                    self.name, self.cooldown_seconds,
                )
            elif self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(
                    "Circuit '%s' OPEN after %d failures (cooldown %ds)",
                    self.name, self._failure_count, self.cooldown_seconds,
                )

    def reset(self) -> None:
        """Manually reset the circuit to CLOSED (useful in tests)."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0
