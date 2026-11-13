"""The push guard and the local CI script (s4 part 7), against a local stand-in remote only: no network, no real push."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tests.release.test_export import ID, commit, ex, git

REPO = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(subprocess.run(["git", "filter-repo", "--version"], capture_output=True).returncode != 0,
                                reason="git filter-repo is not installed")
RELEASE = ("datacheck.py", "datacheck-allow.yaml", "export.py", "guard.py", "hooks/pre-push")


def push(repo, remote, *refspecs):
    env = {**os.environ, "MEDOMNI_GUARD_PYTHON": sys.executable}
    return subprocess.run(["git", "push", "--quiet", remote, *refspecs], cwd=repo, capture_output=True, text=True, env=env)


@pytest.fixture
def guarded(tmp_path):
    """A private toy repository with the real guard, an export, and two stand-in remotes: `public` and `origin`."""
    repo = tmp_path / "private"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.name", "Releaser")
    git(repo, "config", "user.email", "releaser@example.org")
    files = {f"release/{f}": (REPO / "release" / f).read_text() for f in RELEASE}
    files["release/public.yaml"] = yaml.safe_dump({"include": ["src", "release", "README.md"]})
    commit(repo, "start", {**files, "README.md": "hi\n", "src/a.py": "a = 1\n", "internal_docs/n.md": "private\n"})
    os.chmod(repo / "release/hooks/pre-push", 0o755)
    git(repo, "config", "core.hooksPath", "release/hooks")
    for name in ("public", "origin"):
        git(tmp_path, "init", "-q", "--bare", f"{name}.git")
        git(repo, "remote", "add", name, str(tmp_path / f"{name}.git"))
    ex.export(repo, "main")
    return repo


def _plant(repo, path, text):
    """Point refs/export/main at a hand-made commit on top of the export that adds one file."""
    tip = git(repo, "rev-parse", ex.EXPORT_REF)
    idx = repo / ".git" / "plant-index"
    env = {**os.environ, "GIT_INDEX_FILE": str(idx)}
    subprocess.run(["git", "read-tree", tip], cwd=repo, env=env, check=True)
    blob = subprocess.run(["git", "hash-object", "-w", "--stdin"], cwd=repo, input=text, capture_output=True, text=True, check=True).stdout.strip()
    subprocess.run(["git", "update-index", "--add", "--cacheinfo", f"100644,{blob},{path}"], cwd=repo, env=env, check=True)
    tree = subprocess.run(["git", "write-tree"], cwd=repo, env=env, capture_output=True, text=True, check=True).stdout.strip()
    c = git(repo, "commit-tree", tree, "-p", tip, "-m", "planted")
    git(repo, "update-ref", ex.EXPORT_REF, c)


def test_the_export_and_its_tag_go_public(guarded):
    tip = git(guarded, "rev-parse", ex.EXPORT_REF)
    git(guarded, "tag", "-a", "-m", "v0.1", "tmp-v0.1", tip)
    git(guarded, "update-ref", "refs/export/tags/v0.1", git(guarded, "rev-parse", "refs/tags/tmp-v0.1"))
    git(guarded, "tag", "-d", "tmp-v0.1")
    r = push(guarded, "public", f"{ex.EXPORT_REF}:refs/heads/main", "refs/export/tags/v0.1:refs/tags/v0.1")
    assert r.returncode == 0, r.stderr
    assert git(guarded.parent / "public.git", "rev-parse", "main") == tip


def test_a_hand_made_branch_is_refused(guarded):
    r = push(guarded, "public", "main:refs/heads/main")
    assert r.returncode != 0 and "only the export goes public" in r.stderr


def test_a_planted_id_is_refused(guarded):
    _plant(guarded, "src/ids.txt", f"subject {ID}\n")
    r = push(guarded, "public", f"{ex.EXPORT_REF}:refs/heads/main")
    assert r.returncode != 0 and "mimic-id in src/ids.txt" in r.stderr


def test_an_unlisted_file_is_refused(guarded):
    _plant(guarded, "notes/plan.md", "a private plan\n")
    r = push(guarded, "public", f"{ex.EXPORT_REF}:refs/heads/main")
    assert r.returncode != 0 and "doesn't list: notes" in r.stderr


def test_the_public_refs_are_never_deleted(guarded):
    assert push(guarded, "public", f"{ex.EXPORT_REF}:refs/heads/main").returncode == 0
    r = push(guarded, "public", ":refs/heads/main")
    assert r.returncode != 0 and "never deleted" in r.stderr


def test_a_private_push_with_patient_data_is_refused(guarded):
    assert push(guarded, "origin", "main").returncode == 0  # the private line, clean
    commit(guarded, "notes", {"internal_docs/cohort.md": f"subject {ID}\n"})
    r = push(guarded, "origin", "main")
    assert r.returncode != 0 and "mimic-id in internal_docs/cohort.md" in r.stderr


@pytest.fixture(scope="module")
def checkout(tmp_path_factory):
    """A clean clone of this repository's HEAD, with the release folder as it is in the worktree."""
    d = tmp_path_factory.mktemp("ci") / "clone"
    subprocess.run(["git", "clone", "--quiet", "--shared", str(REPO), str(d)], check=True)
    subprocess.run(["git", "checkout", "--quiet", git(REPO, "rev-parse", "HEAD")], cwd=d, check=True)
    for f in ("ci.sh", "datacheck.py", "datacheck-allow.yaml", "public.yaml"):  # until they are committed
        shutil.copy(REPO / "release" / f, d / "release" / f)
    subprocess.run(["git", "add", "release"], cwd=d, check=True)
    if subprocess.run(["git", "status", "--porcelain"], cwd=d, capture_output=True, text=True).stdout.strip():
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.org", "commit", "-qm", "release/ as in the worktree"],
                       cwd=d, check=True)
    return d


def ci(d):
    return subprocess.run(["sh", "release/ci.sh"], cwd=d, capture_output=True, text=True,
                          env={**os.environ, "MEDOMNI_PYTHON": sys.executable})


def test_the_ci_script_passes_on_a_clean_checkout(checkout):
    r = ci(checkout)
    assert r.returncode == 0, r.stdout[-800:] + r.stderr[-800:]
    assert "0 unresolved" in r.stdout and "release-check: ok" in r.stdout


def test_the_ci_script_fails_on_a_planted_record_id(checkout, tmp_path):
    d = tmp_path / "planted"
    subprocess.run(["git", "clone", "--quiet", "--shared", str(checkout), str(d)], check=True)
    (d / "src/medomni/planted.txt").write_text(f"files/p12/p{ID}/s1/record.hea\n")
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.org", "add", "-A"], cwd=d, check=True)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.org", "commit", "-qm", "plant"], cwd=d, check=True)
    r = ci(d)
    assert r.returncode != 0 and "1 unresolved" in r.stdout
