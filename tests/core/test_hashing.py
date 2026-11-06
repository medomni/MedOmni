"""Core's hash functions (part 4): same values as v0.2 where stored values depend on them; fp1 as the Tasks page says.

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
    """Published fingerprints must stay checkable: this value may never change for fp1."""
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


def _atom(root, data=b"\x00\x01signal"):
    return _tree(root, {"task.toml": b'template = "dummy_aki"\ncohort = "n20"\n',
                        "instruction.md": b"Predict aki.\n",
                        "environment/Dockerfile": b"FROM scratch\n",
                        "tests/check.py": b"print('ok')\n",
                        "data/files/DUMMY-1.edf": data})


def test_fingerprint(tmp_path):
    a = _atom(tmp_path / "build-1")
    fp = hashing.fingerprint(a)
    assert fp.startswith("fp1:") and len(fp) == 4 + 64
    (a / "FINGERPRINT").write_text(fp + "\n")
    assert hashing.fingerprint(a) == fp  # the FINGERPRINT file is left out
    assert hashing.fingerprint(_atom(tmp_path / "build-2")) == fp  # a second build in another place: same value
    assert hashing.fingerprint(_atom(tmp_path / "build-3", data=b"\x00\x01signam")) != fp  # one changed byte
    (a / "data/FINGERPRINT").write_text("x")
    assert hashing.fingerprint(a) != fp  # only the top-level FINGERPRINT is left out
