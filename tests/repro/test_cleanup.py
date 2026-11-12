"""Stage 3 part 8 and s4 part 1: v0.2's folders are gone, and no copy of Core's hash helpers is left in `src/` (probe p10).

v0.2.1 stays whole in git history (tag v0.2.1, commit aa45b68); the equivalence tests read it from there (`v02_root`).
"""
import ast
import re
import subprocess

V02_FOLDERS = ("assurance", "data_manifest", "data_task", "harness", "release", "tools", "runs", "perception")
KEPT = re.compile(r"^(perception/encoders/|perception/deployed\.yaml$|perception/deployment\.yaml$)")  # v0.3 content
CORE_HELPERS = {"sha256", "sha256_file", "sha256_dir", "quick_sha", "dir_hash"}  # medomni.core.hashing's, and v0.2's names


def _tracked(repo, *paths):
    out = subprocess.run(["git", "-C", str(repo), "ls-files", "--", *paths], capture_output=True, text=True, check=True)
    return out.stdout.split()


def test_v02_folders_hold_only_v03_content(repo):
    assert [f for f in _tracked(repo, *V02_FOLDERS) if not KEPT.match(f)] == []


def test_no_encoder_folder_reaches_into_the_repository(repo):
    """v0.2's demo.py put the repository on sys.path to import perception/container.py; the image copies what it needs."""
    reach = re.compile(r"sys\.path\.insert\(0, str\(Path\(__file__\)\.resolve\(\)\.parents\[")
    files = [f for f in _tracked(repo, "perception/encoders") if f.endswith(".py")]
    assert [f for f in files if reach.search((repo / f).read_text(encoding="utf-8"))] == []
    assert not [f for f in files if f.endswith("/demo.py")]


def test_core_hash_helpers_are_defined_once(repo):
    found = {}
    for p in sorted((repo / "src/medomni").rglob("*.py")):
        for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.lstrip("_") in CORE_HELPERS:
                found.setdefault(node.name.lstrip("_"), []).append(p.relative_to(repo).as_posix())
    assert found == {"sha256_file": ["src/medomni/core/hashing.py"], "quick_sha": ["src/medomni/core/hashing.py"],
                     "dir_hash": ["src/medomni/core/hashing.py"]}
