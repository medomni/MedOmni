"""The torch rule in `medomni perception check` (R-171): CPU builds at listed versions, in the Dockerfile and the image."""
from pathlib import Path

import pytest

from medomni.core import plugins
from medomni.perception.registry import RegistryError, check

REPO = Path(__file__).resolve().parents[2]
DOCKERFILES = sorted((REPO / "perception/encoders").glob("*/*/Dockerfile"))
CPU = "https://download.pytorch.org/whl/cpu"
FROM = "FROM python:3.11-slim\n"


@pytest.fixture
def builds():
    return check.torch_builds()


def problems(tmp_path, text, builds):
    (tmp_path / "Dockerfile").write_text(FROM + text)
    return check.dockerfile_problems(tmp_path / "Dockerfile", builds)


def test_the_shipped_list():
    assert check.torch_builds() == {"index": CPU, "build": "cpu", "versions": ["2.6.0", "2.7.1", "2.13.0", "2.15.0"]}


@pytest.mark.parametrize("dockerfile", DOCKERFILES, ids=lambda p: f"{p.parent.parent.name}__{p.parent.name}")
def test_every_encoder_passes(dockerfile, builds):
    assert check.dockerfile_problems(dockerfile, builds) == []


def test_a_gpu_torch_install_is_refused(tmp_path, builds):
    """biomedclip's line before R-171: torch from PyPI, the GPU build."""
    got = problems(tmp_path, "RUN pip install --no-cache-dir pyyaml==6.0.2 torch==2.6.0 torchvision==0.21.0\n", builds)
    assert got == [f"torch==2.6.0 installs without --index-url {CPU}"]


@pytest.mark.parametrize("line", [f"RUN pip install --index-url {CPU} torch==2.6.0",
                                  f"RUN pip install --index-url={CPU}/ torch==2.6.0",
                                  f"RUN pip install -i {CPU} \\\n    # a comment line inside the instruction\n    torch==2.6.0",
                                  "RUN pip install open_clip_torch==2.32.0 pytorch-lightning==2.4.0"])
def test_what_passes(tmp_path, builds, line):
    assert problems(tmp_path, line + "\n", builds) == []


def test_another_index_is_refused(tmp_path, builds):
    """--extra-index-url leaves PyPI in play, and PyPI's torch is the GPU build."""
    got = problems(tmp_path, f"RUN pip install --extra-index-url {CPU} torch==2.6.0\n", builds)
    assert got == [f"torch==2.6.0 installs without --index-url {CPU}"]


def test_a_pin_off_the_list_is_refused(tmp_path, builds):
    got = problems(tmp_path, f"RUN pip install --index-url {CPU} torch==2.5.1 && pip install numpy==2.2.6\n", builds)
    assert got == ["torch==2.5.1 is not on the torch build list (2.6.0, 2.7.1, 2.13.0, 2.15.0)"]


def test_the_index_belongs_to_the_same_pip_command(tmp_path, builds):
    got = problems(tmp_path, f"RUN pip install --index-url {CPU} numpy==2.2.6 && pip install torch==2.6.0\n", builds)
    assert got == [f"torch==2.6.0 installs without --index-url {CPU}"]


@pytest.mark.parametrize("version,refused", [(None, 0), ("2.6.0+cpu", 0), ("2.15.0+cpu", 0),
                                             ("2.15.0", 1), ("2.6.0+cu124", 1), ("2.5.1+cpu", 1), ("2.5.1", 2)])
def test_the_torch_in_a_built_image(builds, version, refused):
    """retinograd and dr-grade pinned torch 2.6.0 from the CPU index, and timm's torchvision brought 2.15.0 from PyPI."""
    assert len(check.image_torch_problems(version, builds)) == refused


def _plugin(tmp_path, name, text):
    root = tmp_path / name
    (root / "perception").mkdir(parents=True)
    (root / check.PLUGIN_TORCH).write_text(text)
    return plugins.Folder(name, name, f"{name}:content", root)


def test_a_plugin_folder_replaces_the_list(tmp_path, monkeypatch):
    """A GPU host ships its own list."""
    gpu = _plugin(tmp_path, "gpuhost", "index: https://download.pytorch.org/whl/cu124\nbuild: cu124\nversions: [2.6.0]\n")
    monkeypatch.setattr(plugins, "folders", lambda: [gpu])
    assert check.torch_builds() == {"index": "https://download.pytorch.org/whl/cu124", "build": "cu124",
                                    "versions": ["2.6.0"]}


def test_two_plugin_lists_are_refused(tmp_path, monkeypatch):
    text = f"index: {CPU}\nbuild: cpu\nversions: [2.6.0]\n"
    monkeypatch.setattr(plugins, "folders", lambda: [_plugin(tmp_path, "a", text), _plugin(tmp_path, "b", text)])
    with pytest.raises(RegistryError, match="at most one"):
        check.torch_builds()
