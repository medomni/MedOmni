"""`medomni perception check --record` writes the entry the perception service reads (sidecar/record.py)."""
import pytest
import yaml

from medomni.perception.registry import RegistryError
from medomni.perception.registry import record
from medomni.perception.sidecar import record as served

KEY = "sha256:" + "a" * 64
IMAGE_ID = "sha256:" + "b" * 64


@pytest.fixture
def repo(tmp_path, monkeypatch):
    edir = tmp_path / "perception/encoders/fam-x/enc"
    edir.mkdir(parents=True)
    (tmp_path / "perception/deployed.yaml").write_text(yaml.safe_dump({"schema": record.SCHEMA, "encoders": {
        "other__keep": {"image_id": "sha256:" + "c" * 64}, "fam-x__enc": {"image_id": "sha256:" + "d" * 64}}}))
    monkeypatch.setattr(record, "build_key", lambda e, r: KEY)
    monkeypatch.setattr(record, "git_rev", lambda paths, r: "f" * 40)
    monkeypatch.setattr(record, "image_labels", lambda image: ({"org.medomni.build_key": KEY}, IMAGE_ID))
    return tmp_path, edir


def test_a_passing_check_is_servable_and_other_entries_stay(repo):
    root, edir = repo
    record.write(edir, "2 sample(s)", "PASS", "5 sample(s), offline", repo=root, at="2026-11-11T00:00:00Z")
    doc = served.load(root / record.RECORD)
    assert served.servable(doc, "fam-x__enc") == (True, "ok")
    assert served.ref(doc, "fam-x__enc") == IMAGE_ID
    assert doc["encoders"]["other__keep"] == {"image_id": "sha256:" + "c" * 64}
    assert (root / record.RECORD).read_text().startswith("# Deployed encoder images")


def test_no_samples_is_recorded_but_not_served(repo):
    root, edir = repo
    record.write(edir, "1 sample(s)", "UNVERIFIED-no-supply", "the family publishes no samples", repo=root)
    assert served.servable(served.load(root / record.RECORD), "fam-x__enc") == (False, "L3 UNVERIFIED-no-supply")


def test_refused_for_uncommitted_source_or_a_stale_image(repo, monkeypatch):
    root, edir = repo
    before = (root / record.RECORD).read_text()
    monkeypatch.setattr(record, "git_rev", lambda paths, r: "dev-dirty")
    with pytest.raises(RegistryError, match="uncommitted"):
        record.write(edir, "1", "PASS", repo=root)
    monkeypatch.setattr(record, "git_rev", lambda paths, r: "f" * 40)
    monkeypatch.setattr(record, "image_labels", lambda image: ({"org.medomni.build_key": "sha256:old"}, IMAGE_ID))
    with pytest.raises(RegistryError, match="not built from the current source"):
        record.write(edir, "1", "PASS", repo=root)
    assert (root / record.RECORD).read_text() == before


def test_access_controlled_samples_let_test_data_stand_in(repo):
    root, edir = repo
    record.write(edir, "4 sample(s)", served.ACCESS_CONTROLLED, "the family's sample set is access-controlled", repo=root)
    assert served.servable(served.load(root / record.RECORD), "fam-x__enc") == (True, "ok")


def test_access_controlled_families_are_marked_in_core():
    from medomni.core import families

    controlled = {f for f in ("ppg-waveform-uncal", "ecg-12lead-500hz-mv", "cxr-radiograph-2d", "clinical-measurement-irregular",
                              "eeg-sleep-6ch-200hz-uv") if families.get(f).samples_access == "controlled"}
    assert len(controlled) == 5
    assert families.get("capnography-mmhg").samples_access is None  # no sample set at all: still not servable
