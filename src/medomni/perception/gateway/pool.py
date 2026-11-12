"""The container pool: at most N live, least-recently-used evicted, never a busy one.

Pure asyncio. The docker calls are blocking, so they go through to_thread; the
state machine below is what makes concurrent requests safe.

    absent -> starting -> ready -> stopping -> absent

Two rules are worth stating because they are easy to get wrong:

Every thread hand-off is shielded. Cancelling `await to_thread(...)` does not
stop the thread, so an unshielded cancel would release the slot while inference
is still running — and the pool would then evict a container mid-call, or admit
past the concurrency limit. The awaiting task may be cancelled; the slot is not
freed until the work actually finishes.

A container that stops answering is not ready. A transport failure invalidates
that exact slot and removes the container, so the next request starts a fresh
one instead of being routed at a corpse.
"""
import asyncio
import dataclasses
import time

STARTING, READY, STOPPING = "starting", "ready", "stopping"


class PoolError(RuntimeError):
    """No slot could be had, or the container would not start. Worth retrying."""


class StartError(PoolError):
    """The container would not start (e.g. its image is not on this machine): the machine's fault, not the encoder's."""


class UpstreamError(RuntimeError):
    """The container failed or vanished mid-call."""


@dataclasses.dataclass
class Slot:
    encoder_id: str
    state: str = STARTING
    handle: object = None
    inflight: int = 0
    started_at: float = 0.0
    last_used: float = 0.0
    generation: int = 0        # tells a stale slot from its replacement


class Pool:
    def __init__(self, runner, deployment):
        self.runner = runner
        self.deployment = deployment
        self._slots = {}
        self._cond = asyncio.Condition()
        self._reaper = None
        self._generation = 0

    # -- the call an endpoint makes --

    async def encode(self, encoder_id, body):
        """Returns (status, response, start_ms, image_id). start_ms is 0 when warm."""
        slot, start_ms = await self.acquire(encoder_id)
        task = asyncio.ensure_future(asyncio.to_thread(slot.handle.encode, body))
        try:
            status, response = await asyncio.shield(task)
        except asyncio.CancelledError:
            # The thread is still in the container. The slot stays busy until it
            # is really done — releasing here is what would let the pool evict a
            # container mid-inference, or admit past the concurrency limit.
            asyncio.ensure_future(self._release_when_done(slot, task))
            raise
        except Exception as exc:
            # The container is gone or wedged. Take it out rather than route the
            # next request at it.
            await self._invalidate(slot)
            await self.release(slot)
            raise UpstreamError(f"{encoder_id}: {exc}") from exc
        await self.release(slot)
        return status, response, start_ms, slot.handle.image_id

    async def _release_when_done(self, slot, task):
        """Hold the slot for a call whose caller disconnected, until it finishes."""
        try:
            await task
        except Exception:
            await self._invalidate(slot)
        finally:
            await self.release(slot)

    async def docker_available(self):
        return await asyncio.to_thread(self.runner.docker_available)

    async def image_id(self, encoder_id):
        """What the encoder's tag resolves to right now, without starting anything."""
        return await asyncio.to_thread(self.runner.image_id, encoder_id)

    async def warm(self, encoder_id):
        slot, start_ms = await self.acquire(encoder_id)
        await self.release(slot)
        return start_ms

    # -- slots --

    async def acquire(self, encoder_id):
        deadline = time.monotonic() + self.deployment.acquire_timeout_s
        limit = self.deployment.concurrency(encoder_id)
        while True:
            async with self._cond:
                slot = self._slots.get(encoder_id)
                if slot is not None and slot.state == READY and slot.inflight < limit:
                    slot.inflight += 1
                    slot.last_used = time.monotonic()
                    return slot, 0.0
                if slot is not None:
                    # Starting, stopping, or at its concurrency limit. Waiting is
                    # also what stops two requests from starting one encoder twice.
                    await self._wait(deadline, f"timed out waiting for {encoder_id}")
                    continue
                if len(self._slots) < self.deployment.max_live_containers:
                    self._generation += 1
                    slot = Slot(encoder_id, generation=self._generation)
                    self._slots[encoder_id] = slot
                    break
                victim = self._lru_idle()
                if victim is None:
                    await self._wait(
                        deadline,
                        f"the pool is full and every container is busy "
                        f"({self.deployment.max_live_containers} live)")
                    continue
                victim.state = STOPPING
                self._slots.pop(victim.encoder_id, None)
            await self._stop(victim)
        return await self._start(slot)

    async def release(self, slot):
        async with self._cond:
            slot.inflight = max(0, slot.inflight - 1)
            slot.last_used = time.monotonic()
            self._cond.notify_all()

    async def _start(self, slot):
        began = time.monotonic()
        # Shielded: a cancelled start would otherwise leave the container the
        # thread is still creating with nothing tracking it.
        task = asyncio.ensure_future(asyncio.to_thread(self.runner.start, slot.encoder_id))
        try:
            handle = await asyncio.shield(task)
        except asyncio.CancelledError:
            asyncio.ensure_future(self._abandon(slot, task))
            raise
        except BaseException as exc:
            async with self._cond:
                self._slots.pop(slot.encoder_id, None)
                self._cond.notify_all()
            raise StartError(f"could not start {slot.encoder_id}: {exc}") from exc
        async with self._cond:
            slot.handle, slot.state = handle, READY
            slot.inflight, slot.started_at = 1, time.time()
            slot.last_used = time.monotonic()
            self._cond.notify_all()
        return slot, round((time.monotonic() - began) * 1000, 1)

    async def _abandon(self, slot, task):
        """The caller went away while the container was still being created.

        The container is finished and kept — the next request finds it warm —
        unless the slot was replaced meanwhile, in which case it is stopped so
        nothing is left untracked.
        """
        try:
            handle = await task
        except BaseException:
            handle = None
        orphan = None
        async with self._cond:
            mine = self._slots.get(slot.encoder_id) is slot
            if not mine:
                orphan = handle         # a replacement took over
            elif handle is None:
                self._slots.pop(slot.encoder_id, None)
            else:
                slot.handle, slot.state = handle, READY
                slot.inflight, slot.started_at = 0, time.time()
                slot.last_used = time.monotonic()
            self._cond.notify_all()
        if orphan is not None:
            await asyncio.to_thread(self.runner.stop, orphan)

    async def _invalidate(self, slot):
        """Drop a slot whose container failed, and remove the container."""
        async with self._cond:
            if self._slots.get(slot.encoder_id) is slot:
                self._slots.pop(slot.encoder_id, None)
            slot.state = STOPPING
            self._cond.notify_all()
        if slot.handle is not None:
            try:
                await asyncio.shield(
                    asyncio.ensure_future(asyncio.to_thread(self.runner.stop, slot.handle)))
            except Exception:
                pass                    # it is already unreachable; nothing more to do
        async with self._cond:
            self._cond.notify_all()

    async def _stop(self, slot):
        try:
            if slot.handle is not None:
                await asyncio.shield(
                    asyncio.ensure_future(asyncio.to_thread(self.runner.stop, slot.handle)))
        finally:
            async with self._cond:
                self._cond.notify_all()

    async def _wait(self, deadline, message):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise PoolError(message)
        try:
            await asyncio.wait_for(self._cond.wait(), remaining)
        except asyncio.TimeoutError:
            raise PoolError(message) from None

    def _lru_idle(self):
        idle = [s for s in self._slots.values() if s.state == READY and not s.inflight]
        return min(idle, key=lambda s: s.last_used, default=None)

    # -- operator --

    def status(self):
        now = time.monotonic()
        return [{
            "encoder_id": slot.encoder_id,
            "state": slot.state,
            "inflight": slot.inflight,
            "concurrency": self.deployment.concurrency(slot.encoder_id),
            "idle_s": round(now - slot.last_used, 1) if slot.last_used else None,
            "started_at": slot.started_at or None,
            "url": getattr(slot.handle, "url", None),
            "image_id": getattr(slot.handle, "image_id", None),
            "adopted": getattr(slot.handle, "adopted", None),
        } for slot in sorted(self._slots.values(), key=lambda s: s.encoder_id)]

    async def evict(self, encoder_id, wait_s=30.0):
        """Stop one container. Waits for it to fall idle rather than cutting a call."""
        deadline = time.monotonic() + wait_s
        while True:
            async with self._cond:
                slot = self._slots.get(encoder_id)
                if slot is None:
                    return False
                if slot.state == READY and not slot.inflight:
                    slot.state = STOPPING
                    self._slots.pop(encoder_id, None)
                else:
                    await self._wait(deadline, f"{encoder_id} is still busy")
                    continue
            await self._stop(slot)
            return True

    async def reap(self):
        """Stop containers idle longer than idle_timeout_s."""
        if not self.deployment.idle_timeout_s:
            return []
        cutoff = time.monotonic() - self.deployment.idle_timeout_s
        stopped = []
        while True:
            async with self._cond:
                victim = next((s for s in self._slots.values()
                               if s.state == READY and not s.inflight
                               and s.last_used < cutoff), None)
                if victim is None:
                    return stopped
                victim.state = STOPPING
                self._slots.pop(victim.encoder_id, None)
            await self._stop(victim)
            stopped.append(victim.encoder_id)

    async def close(self):
        for slot in list(self._slots.values()):
            self._slots.pop(slot.encoder_id, None)
            slot.state = STOPPING
            await self._stop(slot)

    # -- the reaper task --

    def start_reaper(self):
        if self.deployment.idle_timeout_s and self._reaper is None:
            self._reaper = asyncio.create_task(self._reap_loop())

    async def stop_reaper(self):
        if self._reaper is not None:
            self._reaper.cancel()
            try:
                await self._reaper
            except asyncio.CancelledError:
                pass
            self._reaper = None

    async def _reap_loop(self):
        while True:
            await asyncio.sleep(self.deployment.reap_interval_s)
            try:
                await self.reap()
            except Exception:
                pass                      # a reaper that dies leaks containers
