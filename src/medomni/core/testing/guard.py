"""The T1 guard: unit tests run with no data, no Docker and no network.

`install()` takes these away for a test session, so a test that reaches for one fails with the reason instead of
passing on a machine that happens to have it. Plug-in packages use the same guard in their own CI.
"""
from __future__ import annotations

import builtins
import io
import os
import socket
import sys
import tempfile
from pathlib import Path


class GuardError(RuntimeError):
    """A T1 test used something T1 tests must not use."""


FAKE_DOCKER = "#!/bin/sh\necho 'T1 test used Docker' >&2\nexit 97\n"


# Font folders in the home folder: matplotlib (which neurokit2 imports) lists them on first import. They hold fonts only.
FONT_DIRS = (".local/share/fonts", ".fonts")


def _allowed_roots(repo: Path, tmp: Path) -> tuple[str, ...]:
    roots = {repo, tmp, Path(tempfile.gettempdir()), Path(sys.prefix), Path(sys.base_prefix), Path(sys.exec_prefix)}
    roots |= {Path.home() / d for d in FONT_DIRS}
    return tuple(str(r.resolve()) for r in roots)


def install(monkeypatch, repo: Path, tmp: Path, blocked: tuple[str, ...] = ("/data",)) -> None:
    """Block the network, Docker and data paths for the rest of the session.

    `blocked` lists path prefixes that are always refused. The home folder is refused outside `repo`, `tmp` and the
    Python installation.
    """
    repo, tmp = Path(repo).resolve(), Path(tmp).resolve()
    allowed = _allowed_roots(repo, tmp)
    home = str(Path.home().resolve())

    def refuse(path) -> None:
        if isinstance(path, int):
            return  # an already open file descriptor
        p = os.path.abspath(os.fsdecode(path))
        if any(p == b or p.startswith(b.rstrip("/") + "/") for b in blocked):
            raise GuardError(f"T1 test read a data path: {p}")
        if (p == home or p.startswith(home + "/")) and not any(p == a or p.startswith(a + "/") for a in allowed):
            raise GuardError(f"T1 test read outside the repository: {p}")

    real_open, real_listdir, real_scandir = builtins.open, os.listdir, os.scandir

    def guarded_open(file, *a, **k):
        refuse(file)
        return real_open(file, *a, **k)

    def guarded_listdir(path="."):
        refuse(path)
        return real_listdir(path)

    def guarded_scandir(path="."):
        refuse(path)
        return real_scandir(path)

    monkeypatch.setattr(builtins, "open", guarded_open)
    monkeypatch.setattr(io, "open", guarded_open)
    monkeypatch.setattr(os, "listdir", guarded_listdir)
    monkeypatch.setattr(os, "scandir", guarded_scandir)

    def no_network(*a, **k):
        raise GuardError("T1 test used the network")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket.socket, "connect_ex", no_network)
    monkeypatch.setattr(socket, "getaddrinfo", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)

    bin_dir = tmp / "guard-bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    docker = bin_dir / "docker"
    docker.write_text(FAKE_DOCKER)
    docker.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("DOCKER_HOST", f"unix://{tmp}/no-docker.sock")

    workspace = tmp / "workspace"
    workspace.mkdir(exist_ok=True)
    monkeypatch.setenv("MEDOMNI_HOME", str(workspace))
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("HF_HOME", str(tmp / "hf"))
    monkeypatch.setenv("MPLCONFIGDIR", str(tmp / "matplotlib"))  # matplotlib's cache and config, not ~/.config
    monkeypatch.setenv("MPLBACKEND", "Agg")
