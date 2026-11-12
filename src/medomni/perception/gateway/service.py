"""The encode pipeline: identify the input, run it, compose Evidence.

Everything between an HTTP request and the pool lives here, so app.py stays
routes and this stays testable without a web framework.
"""
# When the container that answered runs a different image than the tag resolved to before the call, the Evidence
# fingerprint is recomputed over the image that actually ran. An input the family reader cannot open (missing .dat,
# undecodable header) is a 400, not a 500; evidence._identity makes that translation.
import dataclasses
import time

from . import evidence as ev
from .pool import PoolError, StartError, UpstreamError


class ServiceError(Exception):
    """Something a caller must be told about, with the status to tell it with."""

    def __init__(self, status, detail, reason=None):
        super().__init__(detail)
        self.status = status
        self.detail = detail
        self.reason = reason  # "start_failure": the container would not start, so the encoder never ran


@dataclasses.dataclass
class Service:
    deployment: object
    catalog: object
    pool: object
    cache: object
    calls: object

    def entry(self, encoder_id):
        found = self.catalog.get(encoder_id)
        if found is None:
            raise ServiceError(404, f"no such encoder: {encoder_id}")
        return found

    def runnable(self, encoder_id):
        found = self.entry(encoder_id)
        if not found.runnable:
            raise ServiceError(409, f"{found.id} is a card only; it has no container yet")
        return found

    async def encode(self, encoder_id, path, options):
        entry = self.runnable(encoder_id)
        began = time.monotonic()

        input_sha = None
        if self.deployment.data_root:
            try:
                resolved = ev.resolve_input(self.deployment.data_root, path)
                input_sha = await ev.input_identity(entry.family, resolved,
                                                    self.deployment.data_root)
            except ev.BadPath as exc:
                raise ServiceError(400, str(exc)) from None

        image_id = await self.pool.image_id(entry.id)
        fingerprint = ev.fingerprint(entry.card, input_sha, path, image_id, options)

        # An input the family cannot fully identify is never cached: the key
        # would not cover the bytes, so a later call could be answered with
        # Evidence produced from different ones.
        cacheable = input_sha is not None
        if cacheable:
            hit = self.cache.get(fingerprint)
            if hit is not None:
                await self.calls.write(encoder_id=entry.id, path=path, cached=True,
                                       fingerprint=fingerprint,
                                       healthy=hit.get("healthy"), duration_ms=0.0)
                return dict(hit, runtime=dict(hit["runtime"], cached=True,
                                              container_start_ms=0.0))

        # Translate to the Container API: the family comes from the card.
        body = {"family": entry.family, "path": path, "options": options}
        try:
            status, response, start_ms, ran_on = await self.pool.encode(entry.id, body)
        except StartError as exc:
            raise ServiceError(503, str(exc), reason="start_failure") from None
        except PoolError as exc:
            raise ServiceError(503, str(exc)) from None
        except UpstreamError as exc:
            raise ServiceError(502, str(exc)) from None

        if status != 200:
            detail = response.get("error", response)
            # 400 is the caller's bug and passes through. Anything else is the
            # container failing, which is the gateway's upstream.
            raise ServiceError(400 if status == 400 else 502, detail)

        if ran_on != image_id:      # the tag was rebuilt after this container started (m10)
            fingerprint = ev.fingerprint(entry.card, input_sha, path, ran_on, options)
        try:
            answer = ev.compose(entry.card, response, fingerprint, input_sha,
                                ran_on, start_ms)
        except ev.IdentityMismatch as exc:
            raise ServiceError(502, str(exc)) from None

        # Only cache when the image that ran is the one the key was built from.
        if cacheable and ran_on == image_id:
            self.cache.put(fingerprint, answer)
        await self.calls.write(encoder_id=entry.id, path=path, cached=False,
                               fingerprint=fingerprint, healthy=answer.get("healthy"),
                               container_start_ms=start_ms, image_id=ran_on,
                               duration_ms=round((time.monotonic() - began) * 1000, 1))
        return answer

    async def warm(self, encoder_id):
        entry = self.runnable(encoder_id)
        try:
            return {"encoder_id": entry.id,
                    "container_start_ms": await self.pool.warm(entry.id)}
        except PoolError as exc:
            raise ServiceError(503, str(exc)) from None

    async def evict(self, encoder_id):
        try:
            return {"encoder_id": encoder_id,
                    "stopped": await self.pool.evict(encoder_id)}
        except PoolError as exc:
            raise ServiceError(409, str(exc)) from None
