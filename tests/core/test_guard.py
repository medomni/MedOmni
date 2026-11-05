"""The T1 guard itself: each thing it takes away really is gone."""
import os
import socket
import subprocess
from pathlib import Path

import pytest

from medomni.core.testing.guard import GuardError


def test_data_path_is_refused():
    with pytest.raises(GuardError, match="data path"):
        open("/data/anything")
    with pytest.raises(GuardError, match="data path"):
        os.listdir("/data")
    with pytest.raises(GuardError, match="data path"):
        Path("/data/x").read_text()


def test_home_outside_repository_is_refused(repo):
    outside = Path.home() / ".medomni-guard-test"
    if str(outside).startswith(str(repo)):
        pytest.skip("repository is the home folder")
    with pytest.raises(GuardError, match="outside the repository"):
        open(outside)


def test_repository_and_tmp_are_readable(repo, tmp_path):
    assert (repo / "pyproject.toml").read_text().startswith("[project]")
    (tmp_path / "f").write_text("ok")
    assert (tmp_path / "f").read_text() == "ok"


def test_network_is_refused():
    with pytest.raises(GuardError, match="network"):
        socket.create_connection(("127.0.0.1", 9))
    with pytest.raises(GuardError, match="network"):
        socket.getaddrinfo("example.org", 443)
    s = socket.socket()
    try:
        with pytest.raises(GuardError, match="network"):
            s.connect(("127.0.0.1", 9))
    finally:
        s.close()


def test_docker_is_refused():
    r = subprocess.run(["docker", "ps"], capture_output=True, text=True)
    assert r.returncode == 97 and "T1 test used Docker" in r.stderr


def test_workspace_and_hf_are_temporary(t1_guard):
    assert os.environ["MEDOMNI_WORKSPACE"].startswith(str(t1_guard))
    assert os.environ["HF_HUB_OFFLINE"] == "1"
    assert os.environ["HF_HOME"].startswith(str(t1_guard))
