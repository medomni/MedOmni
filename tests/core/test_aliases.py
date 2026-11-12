"""One alias resolver (part 3): never a silent empty result. Its equality with v0.2 is in tests/repro."""
import shutil

import pytest

from medomni.core import families
from medomni.core.families import aliases


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
