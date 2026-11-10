"""R-147: Bench finds the perception service through `medomni.services` and refuses an encoder-arm run without its image.

The installed metadata may predate the entry point, so `plugins.resolve` is patched with a stand-in service, the way
test_any_builder.py adds a builder. Bench never imports Perception; nothing here does either.
"""
import pytest

from medomni.bench import arms
from medomni.bench.runs import RunError, harbor
from medomni.core import plugins


class FakeService:
    image = "medomni-perception"

    def __init__(self, present):
        self._present = present

    def present(self):
        return self._present

    def build_command(self, repo):
        return ["docker", "build", "-f", f"{repo}/Dockerfile", "-t", self.image, str(repo)]


@pytest.fixture
def services(monkeypatch):
    """Register `perception` in medomni.services as the given service (None: register nothing)."""
    real = plugins.resolve

    def install(service):
        def resolve(group):
            out = real(group)
            if group != plugins.SERVICES:
                return out
            found = {k: v for k, v in out.pieces.items() if k != harbor.PERCEPTION}
            if service is not None:
                found[harbor.PERCEPTION] = type("P", (), {"load": staticmethod(lambda: service)})()
            return type(out)(**{**out.__dict__, "pieces": found})

        monkeypatch.setattr(plugins, "resolve", resolve)

    return install


def test_the_service_is_found_by_name(services):
    svc = FakeService(True)
    services(svc)
    assert harbor.perception_service() is svc


def test_an_encoder_arm_without_the_image_is_refused(services):
    services(FakeService(False))
    for arm in (arms.encoders, arms.encoders_required, arms.modality_ladder):
        with pytest.raises(RunError, match="image medomni-perception is not on this machine.*docker build"):
            harbor.require_services(arm)


def test_an_encoder_arm_with_the_image_runs(services):
    services(FakeService(True))
    harbor.require_services(arms.encoders)


def test_an_arm_without_the_service_never_looks(services):
    services(None)  # even with no service registered
    harbor.require_services(arms.no_perception)


def test_no_registered_service_is_refused(services):
    services(None)
    with pytest.raises(RunError, match="no service 'perception'"):
        harbor.require_services(arms.encoders)


def test_harbor_is_not_launched_when_the_image_is_absent(services, monkeypatch, tmp_path):
    services(FakeService(False))
    launched = []
    monkeypatch.setattr(harbor.shutil, "which", lambda name: "/usr/bin/harbor")
    monkeypatch.setattr(harbor.subprocess, "run", lambda *a, **k: launched.append(a))
    job = type("Job", (), {"arm": arms.encoders, "folder": tmp_path})()
    with pytest.raises(RunError):
        harbor.harness.run(job)
    assert launched == []
