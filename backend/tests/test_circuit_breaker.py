"""Tests for the circuit breaker module."""

import asyncio

import pytest

from app.core.circuit_breaker import CircuitBreaker, CircuitBreakerOpen, CircuitState


@pytest.fixture
def breaker():
    return CircuitBreaker("test", failure_threshold=3, cooldown_seconds=1)


async def _succeed():
    return "ok"


async def _fail():
    raise RuntimeError("boom")


# -------------------------------------------------------------------
# State transitions
# -------------------------------------------------------------------


async def test_starts_closed(breaker: CircuitBreaker):
    assert breaker.state == CircuitState.CLOSED


async def test_stays_closed_on_success(breaker: CircuitBreaker):
    result = await breaker.call(_succeed())
    assert result == "ok"
    assert breaker.state == CircuitState.CLOSED


async def test_opens_after_threshold_failures(breaker: CircuitBreaker):
    for _ in range(3):
        with pytest.raises(RuntimeError):
            await breaker.call(_fail())

    assert breaker.state == CircuitState.OPEN


async def test_rejects_when_open(breaker: CircuitBreaker):
    # Force open
    for _ in range(3):
        with pytest.raises(RuntimeError):
            await breaker.call(_fail())

    with pytest.raises(CircuitBreakerOpen):
        await breaker.call(_succeed())


async def test_half_open_after_cooldown(breaker: CircuitBreaker):
    # Force open
    for _ in range(3):
        with pytest.raises(RuntimeError):
            await breaker.call(_fail())

    assert breaker.state == CircuitState.OPEN

    # Wait for cooldown (breaker has 1s cooldown)
    await asyncio.sleep(1.1)

    assert breaker.state == CircuitState.HALF_OPEN


async def test_half_open_success_closes(breaker: CircuitBreaker):
    # Force open
    for _ in range(3):
        with pytest.raises(RuntimeError):
            await breaker.call(_fail())

    await asyncio.sleep(1.1)
    assert breaker.state == CircuitState.HALF_OPEN

    # Probe succeeds → closed
    result = await breaker.call(_succeed())
    assert result == "ok"
    assert breaker.state == CircuitState.CLOSED


async def test_half_open_failure_reopens(breaker: CircuitBreaker):
    # Force open
    for _ in range(3):
        with pytest.raises(RuntimeError):
            await breaker.call(_fail())

    await asyncio.sleep(1.1)
    assert breaker.state == CircuitState.HALF_OPEN

    # Probe fails → back to open
    with pytest.raises(RuntimeError):
        await breaker.call(_fail())

    assert breaker.state == CircuitState.OPEN


async def test_reset(breaker: CircuitBreaker):
    for _ in range(3):
        with pytest.raises(RuntimeError):
            await breaker.call(_fail())

    assert breaker.state == CircuitState.OPEN
    breaker.reset()
    assert breaker.state == CircuitState.CLOSED


async def test_failures_below_threshold_stay_closed(breaker: CircuitBreaker):
    # 2 failures (below threshold of 3) → still closed
    for _ in range(2):
        with pytest.raises(RuntimeError):
            await breaker.call(_fail())

    assert breaker.state == CircuitState.CLOSED
