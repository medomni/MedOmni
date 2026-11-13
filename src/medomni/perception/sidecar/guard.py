"""The perception service's guard: budget, breaker, declared-limit check, file-access witness (fix roadmap
harness-runtime §1). Pure python, no gateway or docker imports, so every rule is tested offline; service.py wires it
into the gateway.

Rules (each one has a test in tests/perception/test_sidecar.py):
  budget   EVERY /encode call counts, whatever its outcome; call MAX_CALLS+1 -> 429.
  breaker  per encoder, more than BREAK_AFTER consecutive UNDECLARED failures -> 503 disabled.
           A healthy answer resets the run. A card-declared refusal neither counts nor resets.
           Bad requests (bad path, unknown encoder, card-only) never count: they are the agent's.
           A container that would not start (start_failure) neither counts nor resets: the encoder never ran.
  declared a refusal is card-declared ONLY if the FILE's own inventory metadata violates a bound
           in encoder_limits.yaml. The encoder's word is not taken: a "too long" refusal on an
           in-limit file is an undeclared failure. No metadata (meta: null) -> never declared.
  witness  paths opened under the data root after staging, aggregated {path: {n, first_t}}.
"""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path


MAX_ITEMS = 50      # label items kept per output block
MAX_EVENTS = 20     # event items kept verbatim per block (all are counted)
MAX_TEXT = 400      # characters of a text output kept


def summarize_outputs(outputs: list | None) -> list[dict]:
    """What an answer SHOWED the agent, compact, for the encoder-use levels (assurance 2026-09-24:
    L1 surfaced / L2 cited are matched against these values): labels with values, event counts and
    the first events, the start of any text. Embeddings keep only their size — never the vector,
    since nothing in an embedding can be cited."""
    out = []
    for b in outputs or []:
        kind = b.get("kind")
        items = b.get("items") or []
        if kind == "labels":
            out.append({"kind": kind, "scale": b.get("scale"),
                        "items": [{"label": i.get("label"), "value": i.get("value")} for i in items[:MAX_ITEMS]],
                        "n": len(items)})
        elif kind == "events":
            counts: dict = {}
            for i in items:
                counts[i.get("label")] = counts.get(i.get("label"), 0) + 1
            out.append({"kind": kind, "n": len(items), "label_counts": counts, "first": items[:MAX_EVENTS]})
        elif kind == "text":
            txt = b.get("text") if isinstance(b.get("text"), str) else " ".join(str(i) for i in items)
            out.append({"kind": kind, "text": (txt or "")[:MAX_TEXT]})
        elif kind == "embedding":
            vec = b.get("vector") or b.get("values") or (items[0] if items and isinstance(items[0], list) else [])
            out.append({"kind": kind, "dim": b.get("dim") or len(vec)})
        else:
            out.append({"kind": kind})
    return out


class Guard:
    def __init__(self, max_calls: int = 300, break_after: int = 10,
                 limits: dict | None = None, inventory: dict | None = None):
        self.max_calls = max_calls
        self.break_after = break_after
        self.limits = limits or {}
        self.meta = {}
        for fam in ((inventory or {}).get("families") or {}).values():
            m = fam.get("meta") or {}
            for p in fam.get("paths") or []:
                if isinstance(p, dict):          # tolerate paths-as-objects
                    self.meta[p.get("path")] = p.get("meta")
                else:
                    self.meta[p] = m.get(p)
        self.used = 0
        self.run: dict[str, int] = {}
        self.disabled: dict[str, str] = {}
        self.lock = threading.Lock()

    # -- before the call -------------------------------------------------------------------
    def admit(self, encoder_id: str) -> tuple[str, int, str] | None:
        """Count the call, then refuse it if over budget or the encoder is disabled."""
        with self.lock:
            self.used += 1
            if self.used > self.max_calls:
                return ("budget", 429, f"call budget used up for this task ({self.max_calls} calls)")
            if encoder_id in self.disabled:
                return ("breaker", 503, self.disabled[encoder_id])
        return None

    # -- after the call ----------------------------------------------------------------------
    def declared(self, encoder_id: str, path: str) -> str | None:
        """The card bound this file's metadata violates, or None."""
        lim = self.limits.get(encoder_id) or {}
        meta = self.meta.get(path)
        if not lim or lim.get("limits") == "none" or not meta:
            return None
        dur = meta.get("duration_s")
        if dur is not None:
            if lim.get("max_duration_s") is not None and dur > lim["max_duration_s"]:
                return f"duration {dur:.0f} s > {lim['max_duration_s']} s"
            if lim.get("min_duration_s") is not None and dur < lim["min_duration_s"]:
                return f"duration {dur:.0f} s < {lim['min_duration_s']} s"
        for key, mkey in (("sample_rate_hz", "sample_rate"), ("n_channels", "n_channels"),
                          ("width", "width"), ("height", "height"), ("frames", "frames")):
            b, v = lim.get(key), meta.get(mkey)
            if b is None or v is None:
                continue
            vals = v if isinstance(v, list) else [v]   # EDF sample rates are per channel
            if isinstance(b, dict):                    # {min, max}: every value must fit
                bad = [x for x in vals if (b.get("min") is not None and x < b["min"])
                       or (b.get("max") is not None and x > b["max"])]
                if bad and len(bad) == len(vals) if key == "sample_rate_hz" else bad:
                    return f"{mkey} {v} outside {b}"
            else:                                      # number or list of accepted values
                ok = set(b if isinstance(b, list) else [b])
                if not (set(vals) & ok if key == "sample_rate_hz" else set(vals) <= ok):
                    return f"{mkey} {v} not in {sorted(ok)}"
        return None

    def record(self, encoder_id: str, path: str, outcome: str) -> dict:
        """outcome: healthy | unhealthy | error | bad_request | start_failure. Returns the fields to log."""
        with self.lock:
            if outcome in ("bad_request", "start_failure"):
                return {"outcome": outcome}
            if outcome == "healthy":
                self.run[encoder_id] = 0
                return {"outcome": outcome}
            why = self.declared(encoder_id, path)
            if why:  # its own outcome value (assurance audit 2026-09-24), so no consumer re-derives it
                return {"outcome": "declared", "not_applicable": why}
            self.run[encoder_id] = self.run.get(encoder_id, 0) + 1
            out = {"outcome": outcome, "undeclared_run": self.run[encoder_id]}
            if self.run[encoder_id] > self.break_after and encoder_id not in self.disabled:
                self.disabled[encoder_id] = (f"encoder disabled for this task after {self.run[encoder_id]} "
                                             "consecutive failures")
                out["breaker"] = "opened"
            return out

    def state(self) -> dict:
        return {"budget": {"used": self.used, "max": self.max_calls},
                "breaker": dict(self.disabled)}


GRACE_S = 2.0      # an open this soon after an encode call ends still belongs to that call
MAX_TIMES = 2000   # per-path open timestamps kept for attribution


def companion(opened: str, call_path: str) -> bool:
    """The call's own input or a file the encoder reads with it: same directory, and the opened
    file's name starts with the call file's stem (WFDB: x.hea -> x.dat, x_0001e.dat, x_0001.hea)."""
    o, c = Path(opened), Path(call_path)
    return o.parent == c.parent and o.name.startswith(c.stem)


class Witness:
    """inotify IN_OPEN over every directory AND every file under the data root. Files are watched
    individually because per-file ro bind mounts (refs/…) report opens against the bind source's
    inode, not against the volume directory they appear in.

    inotify cannot tell which process opened a file, and encoder containers read the same volume
    (--volumes-from). Opens are therefore ATTRIBUTED by time (assurance audit 2026-09-24: 403 of 706
    recorded signal reads were the encoder's, not the agent's): an open inside an encode call's
    window [start, end + GRACE_S] on that call's input or a companion file is the encoder's; every
    other open is the agent's. Known limit: an agent reading the very file an encoder is reading at
    that moment is credited to the encoder."""

    def __init__(self, root: str):
        self.root = Path(root)
        self.opened: dict[str, dict] = {}
        self.times: dict[str, list[float]] = {}
        self.windows: list[tuple[str, float, float]] = []
        self.lock = threading.Lock()
        self.error: str | None = None
        self.writes: list[dict] = []
        self._wd: dict[int, Path] = {}

    def start(self) -> None:
        try:
            from inotify_simple import INotify, flags
        except Exception as exc:  # noqa: BLE001
            self.error = f"inotify unavailable: {exc}"
            return
        self._ino, self._flags = INotify(), flags
        for dirpath, dirnames, filenames in os.walk(self.root):
            for p in [Path(dirpath)] + [Path(dirpath) / f for f in filenames]:
                try:
                    self._wd[self._ino.add_watch(str(p), flags.OPEN)] = p
                except OSError:
                    pass
        threading.Thread(target=self._loop, daemon=True).start()

    def watch_writes(self, dirpath: str) -> None:
        """Exact write times of the submission (close-write / moved-to on the submission directory),
        so the encoder-use scorer never has to guess the final write from keystrokes."""
        try:
            from inotify_simple import INotify, flags
        except Exception:  # noqa: BLE001
            return
        ino = INotify()
        try:
            ino.add_watch(dirpath, flags.CLOSE_WRITE | flags.MOVED_TO)
        except OSError:
            return

        def loop():
            while True:
                for ev in ino.read():
                    if ev.name:
                        with self.lock:
                            if len(self.writes) < MAX_TIMES:
                                self.writes.append({"path": ev.name, "t": time.time()})
        threading.Thread(target=loop, daemon=True).start()

    def _loop(self) -> None:
        while True:
            for ev in self._ino.read():
                base = self._wd.get(ev.wd)
                if base is None:
                    continue
                target = base / ev.name if ev.name else base
                if target.is_dir():
                    continue
                self.note(str(target.relative_to(self.root)))

    def note(self, rel: str, t: float | None = None) -> None:
        t = time.time() if t is None else t
        with self.lock:
            rec = self.opened.setdefault(rel, {"path": rel, "n": 0, "first_t": t})
            rec["n"] += 1
            ts = self.times.setdefault(rel, [])
            if len(ts) < MAX_TIMES:
                ts.append(t)

    def encode_window(self, call_path: str, start: float, end: float) -> None:
        with self.lock:
            self.windows.append((str(call_path), start, end))

    def _is_encoder(self, rel: str, t: float) -> bool:
        return any(s <= t <= e + GRACE_S and companion(rel, p) for p, s, e in self.windows)

    def snapshot(self) -> list[dict]:
        with self.lock:
            out = []
            for rel, rec in self.opened.items():
                enc = sum(self._is_encoder(rel, t) for t in self.times.get(rel, []))
                out.append({**rec, "n_encoder": enc, "n_agent": len(self.times.get(rel, [])) - enc})
            return sorted(out, key=lambda r: r["first_t"])
