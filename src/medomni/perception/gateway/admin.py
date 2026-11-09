"""Operator routes: the pool, and whether this process can run anything.

Kept out of the OpenAPI schema. `/docs` is how an agent learns what it may call,
and an agent has no business starting or stopping containers — it names an
encoder, and the pool is the gateway's problem. Set `admin_api: false` to remove
these entirely.
"""
from pathlib import Path

from fastapi import APIRouter, HTTPException

from .schemas import Health, PoolStatus, Ready
from .service import ServiceError

PREFIX = "/admin"


def router(deployment, catalog, pool, service):
    api = APIRouter(include_in_schema=False)

    @api.get("/healthz", response_model=Health)
    async def healthz():
        """The process answers. It says nothing about docker — see /readyz."""
        return Health(ok=True, encoders=len(catalog), live=len(pool.status()),
                      data_root=str(deployment.data_root) if deployment.data_root else None)

    @api.get("/readyz", response_model=Ready)
    async def readyz():
        """Whether this gateway can actually run an encoder."""
        docker = await pool.docker_available()
        root = deployment.data_root
        root_ok = root is None or Path(root).is_dir()
        reasons = ([] if docker else ["docker does not answer"]) + \
                  ([] if root_ok else [f"data_root is not a directory: {root}"])
        return Ready(ready=not reasons, docker=docker, data_root_ok=root_ok,
                     reasons=reasons)

    if not deployment.admin_api:
        return api

    @api.get(f"{PREFIX}/pool", response_model=PoolStatus)
    async def pool_status():
        return PoolStatus(max_live_containers=deployment.max_live_containers,
                          idle_timeout_s=deployment.idle_timeout_s,
                          live=pool.status(), cache=service.cache.stats(),
                          call_log_failures=service.calls.failed)

    @api.post(PREFIX + "/pool/{encoder_id}/warm")
    async def warm(encoder_id: str):
        try:
            return await service.warm(encoder_id)
        except ServiceError as exc:
            raise HTTPException(exc.status, exc.detail) from None

    @api.delete(PREFIX + "/pool/{encoder_id}")
    async def evict(encoder_id: str):
        try:
            return await service.evict(encoder_id)
        except ServiceError as exc:
            raise HTTPException(exc.status, exc.detail) from None

    return api
