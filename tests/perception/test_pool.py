"""The pool's state machine, against a fake runner. No docker."""
import asyncio
import threading
import unittest


from medomni.perception.gateway import config
from medomni.perception.gateway.pool import Pool, PoolError, READY, StartError, UpstreamError


class FakeHandle:
    def __init__(self, runner, encoder_id):
        self.runner, self.encoder_id = runner, encoder_id
        self.url, self.image_id, self.adopted = f"fake://{encoder_id}", "sha256:fake", False

    def encode(self, body):
        self.runner.entered.set()
        if self.runner.fail_encode:
            raise OSError("container went away")
        self.runner.release.wait(5)
        self.runner.finished.append(self.encoder_id)
        return 200, {"encoder_id": self.encoder_id, "family": "f",
                     "healthy": True, "outputs": [], "notes": []}


class FakeRunner:
    def __init__(self, start_delay=0.0, fail_encode=False):
        self.started, self.stopped, self.finished = [], [], []
        self.start_delay, self.fail_encode = start_delay, fail_encode
        self.release = threading.Event()
        self.release.set()
        self.entered = threading.Event()
        self.lock = threading.Lock()

    def start(self, encoder_id):
        if self.start_delay:
            threading.Event().wait(self.start_delay)
        with self.lock:
            self.started.append(encoder_id)
        return FakeHandle(self, encoder_id)

    def stop(self, handle):
        with self.lock:
            self.stopped.append(handle.encoder_id)

    def image_id(self, encoder_id):
        return "sha256:fake"


def deployment(**overrides):
    return config.load(None, dict({"max_live_containers": 2, "idle_timeout_s": 0,
                                   "acquire_timeout_s": 5.0}, **overrides))


class PoolTests(unittest.IsolatedAsyncioTestCase):
    async def test_a_live_container_is_reused(self):
        runner = FakeRunner()
        pool = Pool(runner, deployment())

        await pool.encode("a", {})
        await pool.encode("a", {})

        self.assertEqual(["a"], runner.started)

    async def test_a_cold_encoder_is_started_once(self):
        runner = FakeRunner(start_delay=0.2)
        pool = Pool(runner, deployment())

        await asyncio.gather(*(pool.encode("a", {}) for _ in range(5)))

        self.assertEqual(["a"], runner.started)

    async def test_eviction_takes_the_least_recently_used(self):
        runner = FakeRunner()
        pool = Pool(runner, deployment(max_live_containers=2))

        await pool.encode("a", {})
        await pool.encode("b", {})
        await pool.encode("a", {})        # 'b' is now the least recently used
        await pool.encode("c", {})

        self.assertEqual(["b"], runner.stopped)
        self.assertEqual({"a", "c"}, {s["encoder_id"] for s in pool.status()})

    async def test_a_busy_container_is_not_evicted(self):
        runner = FakeRunner()
        pool = Pool(runner, deployment(max_live_containers=1))
        runner.release.clear()

        busy = asyncio.ensure_future(pool.encode("a", {}))
        await asyncio.to_thread(runner.entered.wait, 5)
        waiting = asyncio.ensure_future(pool.encode("b", {}))
        await asyncio.sleep(0.1)

        self.assertFalse(waiting.done())
        self.assertEqual([], runner.stopped)      # 'a' is still running

        runner.release.set()
        await busy
        await waiting
        self.assertEqual(["a"], runner.stopped)   # evicted only once it was idle

    async def test_the_concurrency_limit_is_held(self):
        runner = FakeRunner()
        pool = Pool(runner, deployment(default_concurrency=1))
        runner.release.clear()

        first = asyncio.ensure_future(pool.encode("a", {}))
        await asyncio.to_thread(runner.entered.wait, 5)
        second = asyncio.ensure_future(pool.encode("a", {}))
        await asyncio.sleep(0.1)

        self.assertEqual(1, pool.status()[0]["inflight"])
        self.assertFalse(second.done())

        runner.release.set()
        await first
        await second

    async def test_cancelling_a_call_does_not_free_the_slot_early(self):
        """The thread is still in the container: the slot must stay busy."""
        runner = FakeRunner()
        pool = Pool(runner, deployment(max_live_containers=1, default_concurrency=1))
        runner.release.clear()

        call = asyncio.ensure_future(pool.encode("a", {}))
        await asyncio.to_thread(runner.entered.wait, 5)
        call.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await call
        await asyncio.sleep(0.1)

        self.assertEqual(1, pool.status()[0]["inflight"])   # still busy
        self.assertEqual([], runner.stopped)                # not evicted mid-call

        runner.release.set()
        await asyncio.sleep(0.2)
        self.assertEqual(0, pool.status()[0]["inflight"])
        self.assertEqual(["a"], runner.finished)            # the work did complete

    async def test_a_dead_container_is_invalidated(self):
        runner = FakeRunner(fail_encode=True)
        pool = Pool(runner, deployment())

        with self.assertRaises(UpstreamError):
            await pool.encode("a", {})

        self.assertEqual([], pool.status())     # not left ready for the next caller
        self.assertEqual(["a"], runner.stopped)

        runner.fail_encode = False
        await pool.encode("a", {})              # and a fresh one is started
        self.assertEqual(["a", "a"], runner.started)

    async def test_a_start_failure_frees_the_slot(self):
        runner = FakeRunner()
        runner.start = lambda encoder_id: (_ for _ in ()).throw(RuntimeError("no image"))
        pool = Pool(runner, deployment())

        with self.assertRaises(StartError):  # a PoolError the service reports as a start failure
            await pool.encode("a", {})
        self.assertEqual([], pool.status())

    async def test_waiting_for_a_full_busy_pool_times_out(self):
        runner = FakeRunner()
        pool = Pool(runner, deployment(max_live_containers=1, acquire_timeout_s=0.3))
        runner.release.clear()

        busy = asyncio.ensure_future(pool.encode("a", {}))
        await asyncio.to_thread(runner.entered.wait, 5)
        with self.assertRaises(PoolError):
            await pool.encode("b", {})

        runner.release.set()
        await busy

    async def test_reaping_stops_only_idle_containers(self):
        runner = FakeRunner()
        pool = Pool(runner, deployment(idle_timeout_s=0.05, max_live_containers=2))

        await pool.encode("a", {})
        await asyncio.sleep(0.1)
        self.assertEqual(["a"], await pool.reap())
        self.assertEqual([], pool.status())

    async def test_close_stops_everything(self):
        runner = FakeRunner()
        pool = Pool(runner, deployment())

        await pool.encode("a", {})
        await pool.encode("b", {})
        await pool.close()

        self.assertEqual({"a", "b"}, set(runner.stopped))
        self.assertEqual([], pool.status())

    async def test_status_reports_a_ready_slot(self):
        pool = Pool(FakeRunner(), deployment())
        await pool.encode("a", {})
        row = pool.status()[0]
        self.assertEqual(READY, row["state"])
        self.assertEqual("sha256:fake", row["image_id"])


if __name__ == "__main__":
    unittest.main()
