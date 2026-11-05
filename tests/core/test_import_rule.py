"""The import rule: core -> core; bench -> core, bench; perception -> core, perception; studio -> core, bench, studio."""
import time
from pathlib import Path

from medomni.core.testing.import_rule import check_tree


def plant(root: Path, files: dict[str, str]) -> Path:
    pkg = root / "medomni"
    for rel, src in files.items():
        p = pkg / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(src)
    return pkg


def found(violations):
    return {(v.path, v.line) for v in violations}


def test_src_passes(repo):
    assert [str(v) for v in check_tree(repo / "src" / "medomni")] == []


def test_planted_violations_are_found(tmp_path):
    pkg = plant(tmp_path, {
        "__init__.py": "",
        "core/__init__.py": "",
        "core/a.py": "import os\nimport medomni.bench.x\n",
        "core/b.py": "from ..bench import y\n",
        "core/c.py": "from ... import z\n",
        "bench/__init__.py": "",
        "bench/a.py": "from medomni.core import plugins\nfrom medomni.perception.gateway import g\n",
        "perception/__init__.py": "",
        "perception/a.py": "from medomni import bench\n",
        "studio/__init__.py": "",
        "studio/a.py": "import medomni.bench\nimport medomni.perception\n",
        "studio/b.py": "import sys\nsys.path.insert(0, '/x')\n",
        "studio/c.py": "import sys\nsys.path = []\n",
    })
    v = check_tree(pkg)
    assert found(v) == {
        ("medomni/core/a.py", 2),          # core -> bench
        ("medomni/core/b.py", 1),          # core -> bench, relative
        ("medomni/core/c.py", 1),          # climbs out of the package
        ("medomni/bench/a.py", 2),         # bench -> perception
        ("medomni/perception/a.py", 1),    # perception -> bench
        ("medomni/studio/a.py", 2),        # studio -> perception
        ("medomni/studio/b.py", 2),        # sys.path edit
        ("medomni/studio/c.py", 2),        # sys.path assignment
    }, [str(x) for x in v]


def test_allowed_imports_pass(tmp_path):
    pkg = plant(tmp_path, {
        "__init__.py": "",
        "core/__init__.py": "from . import plugins\nfrom .plugins import x\nimport medomni\nfrom medomni import __version__\n",
        "bench/__init__.py": "import medomni.core\nfrom medomni.core.plugins import Piece\nfrom .build import b\n",
        "perception/__init__.py": "from medomni.core import families\nimport numpy\n",
        "studio/__init__.py": "from medomni.bench import x\nfrom medomni.core import y\nfrom ..bench import z\n",
    })
    assert [str(x) for x in check_tree(pkg)] == []


def test_file_outside_projects(tmp_path):
    pkg = plant(tmp_path, {"__init__.py": "", "extra/a.py": ""})
    assert [v.path for v in check_tree(pkg)] == ["medomni/extra/a.py"]


def test_fast(repo):
    t = time.perf_counter()
    check_tree(repo / "src" / "medomni")
    assert time.perf_counter() - t < 2.0
