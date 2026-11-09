"""The agent-facing Service API. Routes only; the work is in service and catalog."""
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query

# Changes on assurance/matrix (2026-09-17), for review by Perception:
#   B3  operator.py is now admin.py: a module named `operator` beside main.py shadows the stdlib one, and
#       `uv run gateway/main.py` died on `import argparse` in a clean venv (repro in ISSUES-v0 B3).
from . import admin
from .cache import Cache
from .calllog import CallLog
from .catalog import Catalog
from .pool import Pool
from .runner import DockerRunner
from medomni.core.contracts import EncodeRequest

from .schemas import EncoderSummary, FamilyRow
from .service import Service, ServiceError

DESCRIPTION = """
Find an encoder, then run one.

Discovery is served from the cards on disk and starts nothing. Whether a
container is running, and which ones, is not part of this API: name an encoder
and the gateway sees to it.

`path` is relative to the gateway's data root, which is mounted read-only into
the container. The API does not accept uploaded bytes: the agent and the gateway
must see the same filesystem, and a file must not change while it is being read.
"""


def create_app(deployment, catalog=None, pool=None, encoders_dir=None):
    catalog = catalog or Catalog.load(encoders_dir, ids=tuple(deployment.encoders))
    pool = pool or Pool(DockerRunner(deployment), deployment)
    unknown = set(deployment.encoders) - {e.id for e in catalog.all()}
    if unknown:
        raise ValueError("the workspace deployment names encoders that do not exist: "
                         + ", ".join(sorted(unknown)))

    service = Service(deployment=deployment, catalog=catalog, pool=pool,
                      cache=Cache(deployment.cache_bytes),
                      calls=CallLog(deployment.call_log, deployment.log_paths))

    @asynccontextmanager
    async def lifespan(_app):
        pool.start_reaper()
        try:
            yield
        finally:
            await pool.stop_reaper()
            if deployment.stop_on_exit:
                await pool.close()

    app = FastAPI(title="MedOmni Perception Service", description=DESCRIPTION,
                  version="0.1.0", lifespan=lifespan)
    app.state.deployment = deployment
    app.state.catalog = catalog
    app.state.pool = pool
    app.state.service = service

    @app.get("/encoders", response_model=list[EncoderSummary])
    async def list_encoders(
        q: Optional[str] = Query(None, description="Free text, fuzzy. 'ecg', 'chest xray'."),
        family: Optional[str] = None,
        modality: Optional[str] = None,
        kind: Optional[str] = Query(None, pattern="^(labels|events|text|embedding)$"),
        label: Optional[str] = Query(None, description="An encoder that can emit this label."),
        runnable: str = Query("true", pattern="^(true|false|any)$"),
        limit: Optional[int] = Query(None, ge=1,
                                     description="Most rows to return. Unset: every match."),
    ):
        """Every encoder that matches, best first.

        Previous default cap left out the missing encoders without flagging
        to the agent. Ask for less with `limit`.
        """
        wanted = {"true": True, "false": False, "any": None}[runnable]
        found = catalog.search(q=q, family=family, modality=modality, kind=kind,
                               label=label, runnable=wanted, limit=limit)
        return [entry.summary(score) for entry, score in found]

    @app.get("/encoders/{encoder_id}", response_model=EncoderSummary)
    async def get_encoder(encoder_id: str):
        return _answer(lambda: service.entry(encoder_id).summary())

    @app.get("/cards/{encoder_id}")
    async def get_card(encoder_id: str):
        """The card, verbatim. The gateway never computes or fills a field."""
        return _answer(lambda: service.entry(encoder_id).card)

    @app.get("/families", response_model=list[FamilyRow])
    async def list_families():
        return catalog.families()

    @app.post("/encode")
    async def encode(request: EncodeRequest):
        try:
            return await service.encode(request.encoder_id, request.path, request.options)
        except ServiceError as exc:
            raise HTTPException(exc.status, exc.detail) from None

    def _answer(call):
        try:
            return call()
        except ServiceError as exc:
            raise HTTPException(exc.status, exc.detail) from None

    app.include_router(admin.router(deployment, catalog, pool, service))
    return app


def serve(deployment, host="127.0.0.1", port=8000, encoders_dir=None):
    """Run the gateway in the foreground (`medomni perception up`)."""
    import sys

    import uvicorn

    app = create_app(deployment, encoders_dir=encoders_dir)
    print(f"encoders   {len(app.state.catalog)} from the repository", file=sys.stderr)
    print(f"data root  {deployment.data_root or 'none: containers read their baked samples'}", file=sys.stderr)
    print(f"pool       up to {deployment.max_live_containers} live container(s)", file=sys.stderr)
    uvicorn.run(app, host=host, port=port)
