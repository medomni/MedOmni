"""The gateway's deployment: what this machine does. Environment config, never task content.

It is the `deployment` mapping of the workspace config (R-60), read by `from_workspace`; `load` reads the same keys
from a YAML file, for tests and one-off runs. `encoders` is the encoder set: a list of ids, or a mapping of id to
its policy (`concurrency`). Relative paths (`call_log`) are taken from the workspace folder.
"""
import dataclasses
import math
import re
from pathlib import Path

import yaml

DEFAULTS = {
    "data_root": None,              # host directory mounted read-only at /data
    "max_live_containers": 5,
    "default_concurrency": 4,       # simultaneous calls one container accepts
    "start_timeout_s": 180.0,       # ecgfounder reads 353 MiB of weights at start
    "acquire_timeout_s": 300.0,     # how long a request waits for a free slot
    "encode_timeout_s": 600.0,      # how long one /encode call may take before it counts as failed
    "idle_timeout_s": 900.0,        # 0 disables the reaper
    "reap_interval_s": 30.0,
    "cache_bytes": 256 << 20,       # 0 disables the cache
    "call_log": "var/calls.jsonl",  # relative to the workspace folder. null disables
    "log_paths": True,              # false: hash request paths in the call log
    "stop_on_exit": True,
    "admin_api": True,              # false removes the operator pool routes
    "container_prefix": "medomni-gw",
    "image_tag": "dev",
    "bind_host": "127.0.0.1",       # where a container publishes its port
}
ENCODER_KEYS = {"concurrency"}
NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")


class ConfigError(Exception):
    """The deployment config is wrong."""


@dataclasses.dataclass(frozen=True)
class Deployment:
    data_root: object
    max_live_containers: int
    default_concurrency: int
    start_timeout_s: float
    acquire_timeout_s: float
    idle_timeout_s: float
    reap_interval_s: float
    cache_bytes: int
    call_log: object
    log_paths: bool
    stop_on_exit: bool
    admin_api: bool
    container_prefix: str
    image_tag: str
    bind_host: str
    encoders: dict
    encode_timeout_s: float = 600.0

    def concurrency(self, encoder_id):
        return (self.encoders.get(encoder_id) or {}).get(
            "concurrency", self.default_concurrency)


def _integer(name, value, minimum):
    """A whole number. 0.5 is not a pool size, and int(0.5) would silently be 0."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"{name} must be a whole number, got {value!r}")
    if value < minimum:
        raise ConfigError(f"{name} must be at least {minimum}, got {value!r}")
    return value


def _seconds(name, value, allow_zero=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{name} must be a number of seconds, got {value!r}")
    if not math.isfinite(value) or value < 0 or (value == 0 and not allow_zero):
        raise ConfigError(f"{name} must be a finite positive number, got {value!r}")
    return float(value)


def _boolean(name, value):
    """A real boolean. The YAML string 'false' is a mistake, not a false."""
    if not isinstance(value, bool):
        raise ConfigError(f"{name} must be true or false, got {value!r}")
    return value


def _name(name, value):
    if not isinstance(value, str) or not NAME_RE.match(value):
        raise ConfigError(f"{name} must be a docker-safe name, got {value!r}")
    return value


def load(path=None, overrides=None):
    """Read a deployment file. Command-line overrides win over the file."""
    raw, base = {}, Path.cwd()
    if path is not None:
        path = Path(path)
        if not path.exists():
            raise ConfigError(f"no such deployment file: {path}")
        raw = yaml.safe_load(path.read_text()) or {}
        if not isinstance(raw, dict):
            raise ConfigError(f"{path} must hold a mapping")
        base = path.resolve().parent
    return from_mapping(raw, base, overrides)


def from_workspace(config=None, overrides=None):
    """The deployment of the workspace config (default: the current one, `medomni.core.workspace.load()`)."""
    from medomni.core import workspace

    config = config if config is not None else workspace.load()
    return from_mapping(config.deployment, workspace.home(), overrides)


def from_mapping(raw, base, overrides=None):
    """Check a deployment mapping; relative paths are taken from `base`."""
    if not isinstance(raw, dict):
        raise ConfigError("the deployment must be a mapping")
    raw = dict(raw)
    encoders = raw.pop("encoders", None) or {}
    if isinstance(encoders, (list, tuple)):  # the encoder set as a list of ids (R-60)
        if not all(isinstance(e, str) for e in encoders) or len(set(encoders)) != len(encoders):
            raise ConfigError("'encoders' as a list must hold distinct encoder ids")
        encoders = {e: {} for e in encoders}
    unknown = set(raw) - set(DEFAULTS)
    if unknown:
        raise ConfigError(f"unknown key(s): {', '.join(sorted(unknown))}")

    values = dict(DEFAULTS, **raw)
    values.update({k: v for k, v in (overrides or {}).items() if v is not None})

    if not isinstance(encoders, dict):
        raise ConfigError("'encoders' must map an encoder id to its policy")
    for encoder_id, policy in encoders.items():
        if not isinstance(policy, dict):
            raise ConfigError(f"encoders.{encoder_id} must be a mapping")
        extra = set(policy) - ENCODER_KEYS
        if extra:
            raise ConfigError(f"encoders.{encoder_id}: unknown key(s) {', '.join(sorted(extra))}")
        if "concurrency" in policy:
            _integer(f"encoders.{encoder_id}.concurrency", policy["concurrency"], 1)

    _integer("max_live_containers", values["max_live_containers"], 1)
    _integer("default_concurrency", values["default_concurrency"], 1)
    _integer("cache_bytes", values["cache_bytes"], 0)
    for key in ("start_timeout_s", "acquire_timeout_s", "encode_timeout_s", "reap_interval_s"):
        _seconds(key, values[key])
    _seconds("idle_timeout_s", values["idle_timeout_s"], allow_zero=True)
    for key in ("stop_on_exit", "log_paths", "admin_api"):
        _boolean(key, values[key])
    _name("container_prefix", values["container_prefix"])
    _name("image_tag", values["image_tag"])
    if not isinstance(values["bind_host"], str) or not values["bind_host"]:
        raise ConfigError(f"bind_host must be an address, got {values['bind_host']!r}")

    data_root = None
    if values["data_root"]:
        data_root = Path(values["data_root"]).expanduser().resolve()
        if not data_root.is_dir():
            raise ConfigError(f"data_root is not a directory: {data_root}")

    return Deployment(
        data_root=data_root,
        max_live_containers=values["max_live_containers"],
        default_concurrency=values["default_concurrency"],
        start_timeout_s=float(values["start_timeout_s"]),
        acquire_timeout_s=float(values["acquire_timeout_s"]),
        encode_timeout_s=float(values["encode_timeout_s"]),
        idle_timeout_s=float(values["idle_timeout_s"]),
        reap_interval_s=float(values["reap_interval_s"]),
        cache_bytes=values["cache_bytes"],
        call_log=(base / values["call_log"]) if values["call_log"] else None,
        log_paths=values["log_paths"],
        stop_on_exit=values["stop_on_exit"],
        admin_api=values["admin_api"],
        container_prefix=values["container_prefix"],
        image_tag=values["image_tag"],
        bind_host=values["bind_host"],
        encoders=encoders,
    )
