"""Core's hash functions (part 4): same values as v0.2 where stored values depend on them; the cfg1: config hash (R-111).

v0.2's helpers are imported from their old files (code, not data). These imports go when the code moves in Stage 3.
"""
import hashlib
import importlib.util
import os

import pytest

from medomni.core import hashing

MIB = 1 << 20
SIZES = [0, 10, MIB - 1, MIB, MIB + 1, 3 * MIB // 2, 2 * MIB, 2 * MIB + 1, 5 * MIB]
IN_BAND = {MIB + 1, 3 * MIB // 2, 2 * MIB}  # where the bridge's copy reads a tail and the others don't


def _v02(repo, rel, name):
    spec = importlib.util.spec_from_file_location(name, repo / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def v02(repo):
    return (_v02(repo, "data_task/manifestbuilder/__init__.py", "v02_manifestbuilder"),
            _v02(repo, "data_task/familybridge/bridge.py", "v02_bridge"))


def _bytes(n: int) -> bytes:
    return hashlib.shake_256(str(n).encode()).digest(n) if n else b""  # head and tail differ, as in a recording


@pytest.fixture(scope="module")
def sized(tmp_path_factory):
    d = tmp_path_factory.mktemp("sized")
    for n in SIZES:
        (d / f"f{n}").write_bytes(_bytes(n))
    return d


@pytest.mark.parametrize("n", SIZES)
def test_quick_sha_equals_the_stored_recipe(v02, sized, n):
    manifestbuilder, bridge = v02
    p = sized / f"f{n}"
    assert hashing.quick_sha(p) == manifestbuilder.quick_sha(p)
    assert len(hashing.quick_sha(p)) == 16
    if n not in IN_BAND:
        assert hashing.quick_sha(p) == bridge.quick_sha(p)
    else:
        assert hashing.quick_sha(p) != bridge.quick_sha(p)  # the one known difference (U2.3)


@pytest.mark.parametrize("n", [0, 5 * MIB])
def test_sha256_file(sized, n):
    p = sized / f"f{n}"
    assert hashing.sha256_file(p) == hashlib.sha256(p.read_bytes()).hexdigest()
    assert hashing.sha256_file(p, chunk=7) == hashing.sha256_file(p)


def _tree(root, files: dict[str, bytes]):
    root.mkdir(parents=True, exist_ok=True)
    for rel, data in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(data)
    return root


def test_dir_hash_entries_are_length_prefixed(tmp_path):
    a = _tree(tmp_path / "a", {"ab": b"c"})
    b = _tree(tmp_path / "b", {"a": b"bc"})
    assert hashing.dir_hash(a) != hashing.dir_hash(b)
    # v0.2's emit.sha256_dir adds path then bytes with nothing between, so it can't tell the two apart
    # (re-stated here: emit.py imports the whole task builder)
    def v02_sha256_dir(d):
        h = hashlib.sha256()
        for p in sorted(p for p in d.rglob("*") if p.is_file()):
            h.update(str(p.relative_to(d)).encode()); h.update(p.read_bytes())
        return h.hexdigest()
    assert v02_sha256_dir(a) == v02_sha256_dir(b)


def test_dir_hash_ignores_creation_order_and_times(tmp_path):
    files = {"x/1.txt": b"one", "y/2.txt": b"two", "z.txt": b""}
    a = _tree(tmp_path / "a", files)
    b = _tree(tmp_path / "b", dict(reversed(list(files.items()))))
    os.utime(b / "z.txt", (0, 0))
    os.chmod(b / "x/1.txt", 0o600)
    assert hashing.dir_hash(a) == hashing.dir_hash(b)


def test_dir_hash_changes_with_names_and_bytes(tmp_path):
    a = _tree(tmp_path / "a", {"x/1.txt": b"one"})
    base = hashing.dir_hash(a)
    (a / "x/1.txt").rename(a / "x/2.txt")
    assert hashing.dir_hash(a) != base
    (a / "x/2.txt").rename(a / "x/1.txt")
    assert hashing.dir_hash(a) == base
    (a / "x/1.txt").write_bytes(b"onf")
    assert hashing.dir_hash(a) != base
    (a / "x/1.txt").write_bytes(b"one")
    (a / "empty").mkdir()
    assert hashing.dir_hash(a) == base  # folders count only through their files


def test_dir_hash_value_is_pinned(tmp_path):
    """Caches and the stage tests compare folders with this recipe, so its value stays fixed."""
    a = _tree(tmp_path / "a", {"b.txt": b"b", "a/c.txt": b"cc"})
    stream = b"a/c.txt\x002\x00cc" + b"b.txt\x001\x00b"
    assert hashing.dir_hash(a) == hashlib.sha256(stream).hexdigest()
    assert hashing.dir_hash(a) == "3df5fd228371fd4b4f66cf52a299453a7f639a0f6ef0dc32540ffe4e8ec6259a"


@pytest.mark.parametrize("kind", ["file", "folder"])
def test_links_are_refused(tmp_path, kind):
    a = _tree(tmp_path / "a", {"data/x.bin": b"x"})
    outside = _tree(tmp_path / "outside", {"y.bin": b"y"})
    (a / "data/link").symlink_to(outside / "y.bin" if kind == "file" else outside)
    with pytest.raises(hashing.HashError, match="a link"):
        hashing.dir_hash(a)


def test_config_hash_value_is_pinned():
    """Config hashes are published (R-111, R-112): this value may never change under cfg1:."""
    stream = b"a.yaml\x002\x00aa" + b"b/c.yaml\x001\x00c" + b"dataset\x001.0\x00" + b"medomni\x000.3.0\x00"
    h = hashing.config_hash({"b/c.yaml": b"c", "a.yaml": b"aa"}, dataset_release="1.0", medomni_release="0.3.0")
    assert h == "cfg1:" + hashlib.sha256(stream).hexdigest()
    assert h == "cfg1:53457f2fa1238049a88c18c9baa56cd755b42b6d39799a3ace5fb4050fc2efbb"


def test_config_hash_covers_configs_and_releases_only(tmp_path):
    cfg = _tree(tmp_path / "pkg", {"template.yaml": b"t", "cohorts/n20.yaml": b"c"})
    files = {"template.yaml": cfg / "template.yaml", "cohorts/n20.yaml": cfg / "cohorts/n20.yaml"}
    h = hashing.config_hash(files, dataset_release="1.0", medomni_release="0.3.0")
    assert h == hashing.config_hash({k: v.read_bytes() for k, v in files.items()}, dataset_release="1.0",
                                    medomni_release="0.3.0")  # paths or bytes: the same value
    assert h != hashing.config_hash(files, dataset_release="1.1", medomni_release="0.3.0")
    assert h != hashing.config_hash(files, dataset_release="1.0", medomni_release="0.3.1")
    (cfg / "cohorts/n20.yaml").write_bytes(b"c2")
    assert h != hashing.config_hash(files, dataset_release="1.0", medomni_release="0.3.0")  # one config byte
    with pytest.raises(hashing.HashError):
        hashing.config_hash(files, dataset_release="", medomni_release="0.3.0")


def test_no_fingerprint_left():
    assert not hasattr(hashing, "fingerprint") and not hasattr(hashing, "FP_PREFIX")  # R-111
