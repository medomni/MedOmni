"""One alias resolver (part 3): the same result as v0.2's generated file; never a silent empty result."""
import shutil

import pytest
import yaml

from medomni.core import families
from medomni.core.families import aliases

GENERATED = "perception/runtime/family_alias.generated.yaml"


@pytest.fixture(scope="module")
def v02(repo):
    return yaml.safe_load((repo / GENERATED).read_text(encoding="utf-8"))["families"]


def test_resolver_equals_v02_generated(repo, v02):
    assert len(v02) == 13
    for fid, want in v02.items():
        got = aliases.resolve(fid, repo)
        assert got.labels == want["labels"], fid
        assert got.components == want["components"], fid
        assert list(got.rates) == [float(r) for r in want["rates"]], fid
        assert list(got.prefixes) == want["prefixes"], fid
        assert list(got.colors) == want["colors"], fid


def test_families_without_aliases_resolve_empty(repo, v02):
    rest = sorted(set(families.load_registry(repo)) - set(v02))
    assert len(rest) == 29
    for fid in rest:
        assert aliases.resolve(fid, repo) == aliases.ResolvedAliases()


def test_accepts_keep_v02_order_and_spelling(repo):
    """U2.2: the order and spelling of each accepts list are part of the bridge's cache key."""
    new = yaml.safe_load((repo / "core/families/aliases.yaml").read_text(encoding="utf-8"))
    old = yaml.safe_load((repo / "data_task/family_alias.yaml").read_text(encoding="utf-8"))
    assert new == old


def _copy_registry(repo, tmp_path):
    shutil.copytree(repo / "core/families", tmp_path / "core/families")
    return tmp_path


def test_missing_alias_file_raises(repo, tmp_path):
    root = _copy_registry(repo, tmp_path)
    (root / "core/families/aliases.yaml").unlink()
    with pytest.raises(FileNotFoundError, match="alias file missing"):
        aliases.resolve("ecg-1lead-200hz-uv", root)


def test_alias_to_an_undeclared_label_raises(repo, tmp_path):
    root = _copy_registry(repo, tmp_path)
    p = root / "core/families/aliases.yaml"
    p.write_text(p.read_text(encoding="utf-8").replace("{ekg: ecg,", "{ekg: nope,"), encoding="utf-8")
    with pytest.raises(families.FamilyError, match="undeclared label 'nope'"):
        aliases.resolve("ecg-1lead-200hz-uv", root)


def test_aliases_for_an_unknown_family_raise(repo, tmp_path):
    root = _copy_registry(repo, tmp_path)
    p = root / "core/families/aliases.yaml"
    p.write_text(p.read_text(encoding="utf-8") + "  no-such-family:\n    accepts: []\n", encoding="utf-8")
    with pytest.raises(families.FamilyError, match="unknown families"):
        aliases.resolve("ecg-1lead-200hz-uv", root)


def test_prefix_keeps_its_trailing_space(repo):
    assert aliases.resolve("eeg-sleep-6ch-200hz-uv", repo).prefixes == ("eeg ",)
