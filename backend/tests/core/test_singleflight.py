from __future__ import annotations

import asyncio

import pytest

from app.core.singleflight import AsyncSingleFlight


@pytest.mark.anyio
async def test_singleflight_shares_only_overlapping_work() -> None:
    singleflight = AsyncSingleFlight()
    calls = 0
    entered = asyncio.Event()
    release = asyncio.Event()

    async def factory() -> dict[str, int]:
        nonlocal calls
        calls += 1
        entered.set()
        await release.wait()
        return {"value": calls}

    first = asyncio.create_task(singleflight.run(("projection", 1), factory))
    await entered.wait()
    second = asyncio.create_task(singleflight.run(("projection", 1), factory))
    release.set()
    assert await asyncio.gather(first, second) == [{"value": 1}, {"value": 1}]
    assert calls == 1

    release.clear()
    entered.clear()
    third = asyncio.create_task(singleflight.run(("projection", 1), factory))
    await entered.wait()
    release.set()
    assert await third == {"value": 2}
    assert calls == 2


@pytest.mark.anyio
async def test_singleflight_discards_completed_work_after_waiter_cancellation() -> None:
    singleflight = AsyncSingleFlight()
    calls = 0
    entered = asyncio.Event()
    release = asyncio.Event()
    finished = asyncio.Event()

    async def factory() -> int:
        nonlocal calls
        calls += 1
        entered.set()
        await release.wait()
        finished.set()
        return calls

    cancelled_waiter = asyncio.create_task(singleflight.run("cancelled", factory))
    await entered.wait()
    cancelled_waiter.cancel()
    with pytest.raises(asyncio.CancelledError):
        await cancelled_waiter

    release.set()
    await finished.wait()
    await asyncio.sleep(0)

    assert await singleflight.run("cancelled", factory) == 2
    assert calls == 2
