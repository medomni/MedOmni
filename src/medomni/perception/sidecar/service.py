"""The perception service: the gateway app inside an atom's compose project, with the deltas container life needs.

Ported from v0.2's harness/perception-image/sidecar.py (FIX-1 D6, fix roadmap F3). The gateway is untouched; this
module owns what running beside an agent changes:

- encoder containers join the ATOM'S compose network (`--network <net>`) and inherit this container's mounts
  (`--volumes-from <self>`) with DATA_ROOT=/workspace/data, so the agent's relative path resolves verbatim end to end.
  No host port is published (unreachable from in here): the gateway dials <alias>:8080 by network DNS.
- budget and breaker: every /encode is counted (MAX_CALLS, default 300; BREAK_AFTER, default 10); a refusal is
  card-declared only if the file's inventory metadata violates encoder_limits.yaml (guard.py).
- scoped catalogue: GET /encoders lists only the encoders in /workspace/data/inventory.json.
- witness: inotify over the data root once bootstrap has touched /workspace/.staged.
- this service writes the call log itself, failures and refusals included; /usage returns it with status, scope,
  files opened, budget and breaker. admin_api is off; it serves 0.0.0.0:8899.
- on SIGTERM it removes every encoder container it started before shutting down.
"""
from __future__ import annotations

import dataclasses
import functools
import hashlib
import json
import os
import socket
import subprocess
import time
from pathlib import Path

import yaml

from .. import registry
from ..gateway import config, runner
from ..gateway import evidence as ev
from ..gateway.app import create_app
from ..gateway.catalog import Catalog
from ..gateway.pool import Pool
from ..gateway.service import Service, ServiceError
from . import record as deployed
from .guard import Guard, Witness, summarize_outputs

LIMITS = Path(__file__).resolve().parent / "encoder_limits.yaml"
SIDECAR_LABEL = f"{runner.LABEL_NS}.sidecar"
RECORD = "perception/deployed.yaml"          # the deployment record, under the repository root
DEPLOYMENT = "perception/deployment.yaml"    # the gateway's deployment defaults and encoder pins
CALLS = "perception/var/calls.jsonl"         # this service's call log


def self_inspect() -> tuple[str, str]:
    """(full container id, compose network name) of THIS container, via the mounted docker socket."""
    short = socket.gethostname()
    out = subprocess.run(["docker", "inspect", short], capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"cannot inspect self ({short}): {out.stderr.strip()}")
    info = json.loads(out.stdout)[0]
    nets = list(info["NetworkSettings"]["Networks"])
    if not nets:
        raise SystemExit("the perception service is on no docker network")
    return info["Id"], nets[0]


class SidecarContainer(runner.Container):
    """Same lifecycle, different `docker run`: no ports, the atom's network and this container's volumes."""

    def __init__(self, encoder_id, *, network, volumes_from, data_root, **kwargs):
        super().__init__(encoder_id, baked=True, **kwargs)  # baked: no host-path mount; --volumes-from carries the data
        self.network, self.volumes_from, self.data_root = network, volumes_from, data_root

    def start(self):
        runner._docker_or_explain()
        if not self._image_present():
            raise runner.ContainerError(f"no image {self.tag} on this machine")
        self.name = self.given_name
        if self._container_present():  # a crashed predecessor: ours by label, or refuse
            if not self._is_ours(runner.labels_of(self.name)):
                raise runner.ContainerError(f"container {self.name} exists and is not ours")
            subprocess.call(["docker", "rm", "-f", self.name],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # dial a SHORT network alias: full pool names can exceed the 63-character DNS label limit
        # (urllib then dies with an idna UnicodeError)
        alias = "enc-" + hashlib.sha256(self.name.encode()).hexdigest()[:12]
        run = ["docker", "run", "-d", "--rm", "--name", self.name,
               "--network", self.network, "--network-alias", alias,
               "--volumes-from", self.volumes_from,
               "-e", f"DATA_ROOT={self.data_root}"]
        for key, value in sorted(self.labels.items()):
            run += ["--label", f"{key}={value}"]
        result = subprocess.run(run + [self.tag], capture_output=True, text=True)
        if result.returncode != 0:
            raise runner.ContainerError(f"docker run failed: {result.stderr.strip()}")
        self.encoder = runner.Encoder(f"http://{alias}:8080")
        if not self.encoder.ready(self.ready_timeout):
            logs = subprocess.run(["docker", "logs", "--tail", "20", self.name],
                                  capture_output=True, text=True)
            self.stop()
            raise runner.ContainerError("encoder never became ready:\n" + (logs.stdout + logs.stderr).strip())
        return self.encoder


class SidecarRunner(runner.DockerRunner):
    def __init__(self, deployment, *, self_id, network, record=None, encoders_dir=None):
        super().__init__(deployment)
        self.self_id, self.network, self.record, self.encoders_dir = self_id, network, record, encoders_dir

    def labels_for(self, encoder_id):
        """The gateway's ownership labels plus this service's container id. The container NAME is a hash of these
        labels, so without it every concurrent trial wanted the same name for the same encoder (same data-root path
        and image), and each service adopted or removed the other's container mid-call (H5 finding, 2026-09-24)."""
        return {**super().labels_for(encoder_id), SIDECAR_LABEL: self.self_id}

    def tag_for(self, encoder_id):
        """The recorded image content id (sha256:...) when the record has the encoder: local only, no registry, so an
        unrecorded rebuild of the :dev tag can never serve. The :dev tag only when there is no record."""
        return deployed.ref(self.record, encoder_id) or super().tag_for(encoder_id)

    def container(self, encoder_id):
        return SidecarContainer(
            encoder_id,
            network=self.network,
            volumes_from=self.self_id,
            data_root=str(self.deployment.data_root),
            name=self.name_for(encoder_id),
            reuse=True,
            ready_timeout=self.deployment.start_timeout_s,
            labels=self.labels_for(encoder_id),
            tag=self.tag_for(encoder_id),
            encoders_dir=self.encoders_dir,
        )


def reap_own_encoders(self_id: str) -> None:
    """Remove every encoder container this service started (by its sidecar label), in one call. Runs on SIGTERM before
    the graceful shutdown, so compose down never finds a network still attached to our encoders: the leak that
    exhausted Docker's address pool (H5, 2026-09-24)."""
    ids = subprocess.run(["docker", "ps", "-aq", "--filter", f"label={SIDECAR_LABEL}={self_id}"],
                         capture_output=True, text=True).stdout.split()
    if ids:
        subprocess.run(["docker", "rm", "-f", *ids], capture_output=True, text=True)


class Calls:
    """The one complete call log, JSON lines. The gateway's own call log is switched off."""

    def __init__(self, path):
        self.path = Path(path)

    def write(self, rec: dict) -> None:
        rec.setdefault("t", time.time())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a") as f:
            f.write(json.dumps(rec, separators=(",", ":"), default=str) + "\n")

    def read(self) -> list[dict]:
        lines = self.path.read_text().splitlines() if self.path.exists() else []
        return [json.loads(line) for line in lines if line.strip()]


@dataclasses.dataclass
class GuardedService(Service):
    """The gateway's Service with the guard in front and a complete call log behind."""

    guard: Guard | None = None
    witness: Witness | None = None
    log: Calls | None = None

    async def encode(self, encoder_id, path, options):
        refused = self.guard.admit(encoder_id)
        if refused:
            self.log.write({"encoder_id": encoder_id, "path": path, "refused": refused[0], "status": refused[1]})
            raise ServiceError(refused[1], refused[2])
        # A WFDB signal file (.dat) is not a record: the record is its .hea header. Assurance audit 2026-09-24:
        # 12-lead ecgfounder was healthy on every .hea and unhealthy on every .dat of the same records, and those .dat
        # failures counted toward the breaker. Answer 400 with the fix, never a breaker count.
        hea = str(path)[:-4] + ".hea" if str(path).endswith(".dat") else None
        if hea and (Path(self.deployment.data_root) / hea).is_file():
            self.log.write({"encoder_id": encoder_id, "path": path,
                            **self.guard.record(encoder_id, path, "bad_request"), "status": 400,
                            "hint": "wfdb data file"})
            raise ServiceError(400, f"'{path}' is a WFDB signal file; pass the record header '{hea}'")
        try:  # a path the gateway will not read is the agent's bad request, never a breaker count
            ev.resolve_input(self.deployment.data_root, path)
        except ev.BadPath as exc:
            self.log.write({"encoder_id": encoder_id, "path": path,
                            **self.guard.record(encoder_id, path, "bad_request"), "status": 400})
            raise ServiceError(400, str(exc)) from None
        t0 = time.time()
        try:
            ans = await super().encode(encoder_id, path, options)
        except ServiceError as exc:
            self.witness.encode_window(path, t0, time.time())
            kind = "bad_request" if exc.status in (404, 409) else "error"
            self.log.write({"encoder_id": encoder_id, "path": path, "healthy": False, "status": exc.status,
                            **self.guard.record(encoder_id, path, kind)})
            raise
        self.witness.encode_window(path, t0, time.time())
        rt, prov = ans.get("runtime") or {}, ans.get("provenance") or {}
        self.log.write({"encoder_id": encoder_id, "path": path, "healthy": ans.get("healthy"), "status": 200,
                        "cached": rt.get("cached"), "fingerprint": ans.get("fingerprint"),
                        "image_id": prov.get("image_id"), "container_start_ms": rt.get("container_start_ms"),
                        "outputs": summarize_outputs(ans.get("outputs")),  # what the agent was shown (use levels L1/L2)
                        **self.guard.record(encoder_id, path, "healthy" if ans.get("healthy") else "unhealthy")})
        return ans


@dataclasses.dataclass(frozen=True)
class Scope:
    catalog: Catalog
    label: str
    unservable: dict
    pins: dict


def scope(catalog: Catalog, inventory: dict | None, record: dict | None, pins: dict) -> Scope:
    """GET /encoders == exactly this task's encoders (its emitted inventory); everything when there is no inventory.

    No runtime filtering (Bosong 2026-09-24: "rebuild the task, not a dynamic filter"): the task's own list is served
    as emitted. Which encoders a task lists is decided when it is built; an encoder the record cannot serve is only
    reported in /usage, never hidden. Encoder pins outside the scoped catalogue are dropped, since create_app refuses
    pins it has no card for.
    """
    if inventory is None:
        return Scope(catalog, "unscoped (no inventory.json: pre-fix atom)", {}, dict(pins))
    wanted = set(inventory.get("encoders") or [])
    unservable = {}
    if record is not None:
        for e in sorted(wanted):
            ok, why = deployed.servable(record, e)
            if not ok:
                unservable[e] = why
    scoped = Catalog([e for e in catalog.all() if e.id in wanted])
    return Scope(scoped, f"inventory ({len(scoped)} encoders)", unservable,
                 {k: v for k, v in pins.items() if k in wanted})


def deployment_for(doc: dict, base: Path, data_root: str, pins: dict, max_live: int):
    """The gateway's deployment: the file's settings, the scoped pins, and this service's fixed choices.

    The gateway's own call log is off (this service writes the one complete log), the operator routes are off, and
    every encoder it started stops on exit.
    """
    doc = dict(doc or {}, encoders=pins, call_log=None)
    return config.from_mapping(doc, base, {"data_root": data_root, "admin_api": False, "stop_on_exit": True,
                                           "max_live_containers": max_live})


def build_app(deployment, catalog, pool, guard, witness, log, scoped: Scope, record, staged: Path):
    """The gateway app with the guarded Service and the /usage route."""
    app = create_app(deployment, catalog=catalog, pool=pool,
                     service_type=functools.partial(GuardedService, guard=guard, witness=witness, log=log))

    @app.get("/usage")
    async def usage():  # this atom's calls only, by construction (one service per atom)
        return {"status": "ok", "encoders": "on", "scope": scoped.label,
                "witness": witness.error or ("started after staging" if staged.exists() else "started without sentinel"),
                "record": ("absent (pre-record era: mutable :dev tags)" if record is None
                           else {"schema": record.get("schema"), "unservable": scoped.unservable}),
                "calls": log.read(),
                "opened": witness.snapshot(), "submission_writes": list(witness.writes),
                **guard.state()}

    return app


def wait_for_data(data_root: Path, wait_s: int) -> Path:
    """Bootstrap populates the workspace volume after this service starts: wait for the data root, then for
    bootstrap's sentinel, so the witness never records the staging copy as agent reads. Returns the sentinel path."""
    deadline = time.time() + wait_s
    while not data_root.is_dir():
        if time.time() > deadline:
            raise SystemExit(f"data root never appeared: {data_root}")
        time.sleep(1)
    staged = data_root.parent / ".staged"
    while not staged.exists() and time.time() < deadline:
        time.sleep(1)
    return staged


def _yaml(path: Path) -> dict:
    return (yaml.safe_load(path.read_text()) or {}) if path.exists() else {}


def main() -> None:
    data_root = Path(os.environ.get("DATA_ROOT", "/workspace/data"))
    port = int(os.environ.get("PORT", "8899"))
    repo = registry.repo_root()
    self_id, network = self_inspect()
    staged = wait_for_data(data_root, int(os.environ.get("DATA_WAIT_S", "300")))

    inv_path = data_root / "inventory.json"
    inventory = json.loads(inv_path.read_text()) if inv_path.exists() else None
    guard = Guard(max_calls=int(os.environ.get("MAX_CALLS", "300")),
                  break_after=int(os.environ.get("BREAK_AFTER", "10")),
                  limits=_yaml(LIMITS), inventory=inventory)
    witness = Witness(str(data_root))
    witness.start()
    witness.watch_writes(str(data_root.parent / "submission"))  # exact final-write times

    # The deployment record, baked into the image at build time. Absent: today's mutable :dev tags, and /usage says so.
    record = deployed.load(repo / RECORD)
    encoders_dir = registry.encoders_root(repo)
    doc = _yaml(repo / DEPLOYMENT)
    scoped = scope(Catalog.load(encoders_dir), inventory, record, doc.get("encoders") or {})
    deployment = deployment_for(doc, (repo / DEPLOYMENT).parent, str(data_root), scoped.pins,
                                int(os.environ.get("MAX_LIVE", "5")))
    pool = Pool(SidecarRunner(deployment, self_id=self_id, network=network, record=record,
                              encoders_dir=encoders_dir), deployment)
    app = build_app(deployment, scoped.catalog, pool, guard, witness, Calls(repo / CALLS), scoped, record, staged)

    import uvicorn

    server = uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=port))
    graceful = server.handle_exit

    def handle_exit(sig, frame):  # reap our encoders first: fast (one docker rm -f), before compose's stop timeout
        try:
            reap_own_encoders(self_id)
        finally:
            graceful(sig, frame)

    server.handle_exit = handle_exit
    server.run()
