"""One alias resolver (part 3): the same result as v0.2's generated file; never a silent empty result."""
import shutil

import pytest
import yaml

from medomni.core import families
from medomni.core.families import aliases

GENERATED = "perception/runtime/family_alias.generated.yaml"
# Rates Stage 3 part 1 added (R-87, p13): the only change to v0.2's aliases. Rates are not in the bridge key (R-86).
STAGE3_RATES = {"resp-flow": [10, 50, 100, 200], "capnography-mmhg": [2, 10], "snore-acoustic": [500]}


@pytest.fixture(scope="module")
def v02(v02_root):
    return yaml.safe_load((v02_root / GENERATED).read_text(encoding="utf-8"))["families"]


def test_resolver_equals_v02_generated(repo, v02):
    assert len(v02) == 13
    for fid, want in v02.items():
        got = aliases.resolve(fid, repo)
        assert got.labels == want["labels"], fid
        assert got.components == want["components"], fid
        assert list(got.rates) == sorted(float(r) for r in want["rates"] + STAGE3_RATES.get(fid, [])), fid
        assert list(got.prefixes) == want["prefixes"], fid
        assert list(got.colors) == want["colors"], fid


def test_families_without_aliases_resolve_empty(repo, v02):
    rest = sorted(set(families.load_registry(repo)) - set(v02))
    assert len(rest) == 29
    for fid in rest:
        rates = tuple(sorted(float(r) for r in STAGE3_RATES.get(fid, [])))
        assert aliases.resolve(fid, repo) == aliases.ResolvedAliases(rates=rates)


def test_accepts_keep_v02_order_and_spelling(repo, v02_root):
    """U2.2: v0.2's accepts lists, in order and spelling, plus only the rates Stage 3 added (R-87)."""
    new = yaml.safe_load((repo / "core/families/aliases.yaml").read_text(encoding="utf-8"))
    old = yaml.safe_load((v02_root / "data_task/family_alias.yaml").read_text(encoding="utf-8"))
    assert new["families"]["resp-flow"]["accepts"][0].pop("rates") == STAGE3_RATES["resp-flow"]
    for fid in ("capnography-mmhg", "snore-acoustic"):
        assert new["families"].pop(fid) == {"accepts": [{"rates": STAGE3_RATES[fid]}]}
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
