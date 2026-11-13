"""release/export.py and release/datacheck.py on toy repositories (s4 part 6): the export is the allowlisted tree,
deterministic and append-only; outside commits import by their authors; the data check finds an id in an old version."""
import hashlib
import importlib.util
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(subprocess.run(["git", "filter-repo", "--version"], capture_output=True).returncode != 0,
                                reason="git filter-repo is not installed")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, REPO / "release" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ex, dc = _load("export"), _load("datacheck")
ID = "1" + "2" * 7  # shaped like a MIMIC subject id


def git(repo, *a, env=None):
    import os

    return subprocess.run(["git", *a], cwd=repo, capture_output=True, text=True, check=True,
                          env={**os.environ, **(env or {})}).stdout.strip()


def commit(repo, msg, files=(), remove=(), author=("Ada", "ada@example.org")):
    for rel, text in dict(files).items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(text)
    for rel in remove:
        git(repo, "rm", "-q", rel)
    git(repo, "add", "-A")
    env = {"GIT_AUTHOR_NAME": author[0], "GIT_AUTHOR_EMAIL": author[1], "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z",
           "GIT_COMMITTER_NAME": "Committer", "GIT_COMMITTER_EMAIL": "c@example.org", "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z"}
    git(repo, "commit", "-q", "-m", msg, env=env)
    return git(repo, "rev-parse", "HEAD")


@pytest.fixture
def private(tmp_path):
    repo = tmp_path / "private"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.name", "Importer")
    git(repo, "config", "user.email", "importer@example.org")
    public = yaml.safe_dump({"include": ["src", "release", "README.md"]})
    commit(repo, "start", {"release/public.yaml": public, "README.md": "hi\n", "old/a.py": "a = 1\n", "internal_docs/n.md": "private\n"})
    commit(repo, f"src: move a (R-12, S3)\n\nBody stays.\n\nCo-Authored-By: Claude <noreply@anthropic.com>",
           {"src/a.py": "a = 2\n"}, remove=["old/a.py"])  # a move that also edits
    commit(repo, "notes only", {"internal_docs/n.md": "more private\n"})
    commit(repo, "src: b", {"src/b.py": f"b = {ID}\n"}, author=("Bo", "bo@example.org"))
    commit(repo, "src: b without the id", {"src/b.py": "b = 0\n"}, author=("Bo", "bo@example.org"))
    commit(repo, "release: the path map", {"release/history-paths.yaml": yaml.safe_dump({"paths": {"old/a.py": "src/a.py"}})})
    return repo


def export(repo, cfg=None):
    p = repo.parent / "cfg.yaml"
    p.write_text(yaml.safe_dump({"strip_from_messages": [r"\bR-\d+[a-z]?\b", r"\bS[1-4]\b"], **(cfg or {})}))
    return ex.export(repo, "main", p)["tip"]


def test_the_export_is_the_release_tree_with_history(private):
    tip = export(private)
    files = git(private, "ls-tree", "-r", "--name-only", tip).splitlines()
    assert files == ["README.md", "release/history-paths.yaml", "release/public.yaml", "src/a.py", "src/b.py"]
    every = git(private, "log", "--format=", "--name-only", tip).split()
    assert not any(f.startswith(("internal_docs/", "old/")) for f in every)  # private and old paths are gone everywhere
    assert git(private, "log", "--format=%s", tip).splitlines() == [
        "release: the path map", "src: b without the id", "src: b", "src: move a", "start"]  # "notes only" was emptied
    assert git(private, "show", f"{tip}~4:src/a.py") == "a = 1"  # the moved file keeps its first version, under its new name


def test_messages_and_authors(private):
    tip = export(private)
    msg = git(private, "log", "-1", "--format=%B", f"{tip}~3")
    assert msg.splitlines()[0] == "src: move a"  # R-row id and session name stripped, empty parentheses gone
    assert "Body stays." in msg and "Co-Authored-By: Claude <noreply@anthropic.com>" in msg
    assert msg.strip().splitlines()[-1] == f"Private-Commit: {git(private, 'rev-parse', 'main~4')}"
    assert git(private, "log", "-1", "--format=%an", f"{tip}~2") == "Bo"


def test_a_range_of_ids_leaves_no_fragments(private):
    commit(private, "docs: redraft with decisions R-1 to R-8 (R-9/R-10; S2-S4 findings)", {"src/f.py": "f = 1\n"})
    tip = export(private, {"strip_from_messages": [r"\bR-\d+[a-z]?(?:\s*(?:to|and|/|-)\s*R-\d+[a-z]?)*\b", r"\bS[1-4](?:-S[1-4])?\b"]})
    assert git(private, "log", "-1", "--format=%s", tip) == "docs: redraft with decisions (findings)"


LIST = r"\bR-\d+[a-z]?(?:\s*(?:,|to|and|/|-)\s*R-\d+[a-z]?)*\b"


def test_a_list_of_ids_leaves_no_fragments(private):
    commit(private, "docs: cards (R-76, R-77, R-79; Bosong, 2026-11-06)\n\nversion 1.0; R-68, R-94).", {"src/g.py": "g = 1\n"})
    tip = export(private, {"strip_from_messages": [LIST]})
    assert git(private, "log", "-1", "--format=%B", tip).splitlines()[:3] == ["docs: cards (Bosong, 2026-11-06)", "", "version 1.0)."]


def test_an_exact_subject_replaces_a_badly_cleaned_one(private):
    sha = commit(private, "docs: redraft for R-19 to R-43 (Build, Recipes)", {"src/h.py": "h = 1\n"})
    with pytest.raises(ex.ExportError, match="left fragments"):  # "redraft for (Build" would be published
        export(private, {"strip_from_messages": [LIST]})
    tip = export(private, {"strip_from_messages": [LIST], "subjects": {sha[:10]: "docs: redraft (Build, Recipes)"}})
    assert git(private, "log", "-1", "--format=%s", tip) == "docs: redraft (Build, Recipes)"


def test_a_whole_message_can_be_given(private):
    sha = commit(private, "src: i (R-1)\n\nquotes '(,' on purpose", {"src/i.py": "i = 1\n"})
    tip = export(private, {"messages": {sha[:10]: "src: i\n\nsays it in words"}})
    assert git(private, "log", "-1", "--format=%B", tip).splitlines()[:3] == ["src: i", "", "says it in words"]
    assert git(private, "log", "-1", "--format=%B", tip).strip().endswith(f"Private-Commit: {sha}")


def test_fresh_rebuilds_an_export_that_exists(private):
    first = export(private)
    p = private.parent / "cfg.yaml"
    p.write_text(yaml.safe_dump({"strip_from_messages": [r"\bsrc\b"]}))
    assert ex.export(private, "main", p)["tip"] == first  # appended to: nothing new, so unchanged
    assert ex.export(private, "main", p, fresh=True)["tip"] != first  # rebuilt with the new rule


def test_a_second_run_gives_the_same_commits(private):
    first = export(private)
    git(private, "update-ref", "-d", ex.EXPORT_REF)
    assert export(private) == first


def test_an_incremental_export_appends_exactly_the_new_commit(private):
    first = export(private)
    new = commit(private, "src: c", {"src/c.py": "c = 1\n"})
    second = export(private)
    assert git(private, "rev-parse", f"{second}~1") == first
    assert git(private, "log", "-1", "--format=%B", second).strip().endswith(f"Private-Commit: {new}")


def test_an_outside_commit_imports_by_its_author_and_isnt_exported_twice(private, tmp_path):
    first = export(private)
    public = tmp_path / "public"
    git(tmp_path, "clone", "-q", str(private), str(public), "--no-checkout")
    git(public, "checkout", "-q", "-B", "main", first)
    commit(public, "src: a fix from outside", {"src/b.py": "b = 2\n"}, author=("Out", "out@example.org"))
    outside = git(public, "rev-parse", "HEAD")
    git(private, "fetch", "-q", str(public), f"main:refs/public/main")
    with pytest.raises(ex.ExportError, match="checked out"):  # moving a checked-out branch would strand its checkout
        ex.import_public("refs/public/main", private, "main")
    git(private, "checkout", "-q", "-b", "work")
    made = ex.import_public("refs/public/main", private, "main")
    assert len(made) == 1 and git(private, "log", "-1", "--format=%an|%B", "main").startswith("Out|src: a fix from outside")
    assert f"Public-Commit: {outside}" in git(private, "log", "-1", "--format=%B", "main")
    # the public line is now the export to build on; the next export appends a later private commit after it
    git(private, "update-ref", ex.EXPORT_REF, outside)
    git(private, "checkout", "-q", "main")
    commit(private, "src: d", {"src/d.py": "d = 1\n"})
    tip = export(private)
    assert git(private, "rev-parse", f"{tip}~1") == outside  # appended after the outside commit, not duplicated
    subjects = git(private, "log", "--format=%s", tip).splitlines()
    assert subjects.count("src: a fix from outside") == 1 and subjects[0] == "src: d"
    assert git(private, "show", f"{tip}:src/b.py") == "b = 2"


def test_import_refuses_when_main_moved_since_the_export(private, tmp_path):
    export(private)
    git(private, "fetch", "-q", str(private), f"{ex.EXPORT_REF}:refs/public/main")
    commit(private, "src: e", {"src/e.py": "e = 1\n"})
    git(private, "checkout", "-q", "-b", "work")
    with pytest.raises(ex.ExportError, match="moved since the last export"):
        ex.import_public("refs/public/main", private, "main")


def test_an_id_planted_in_an_old_version_is_caught_and_can_be_rewritten(private):
    tip = export(private)
    found = dc.check(private, tip, history=True, allow=[])
    assert ("src/b.py", "mimic-id", None) in found["hits"]  # in an old version only: today's src/b.py has none
    assert not [h for h in dc.check(private, tip, history=False, allow=[])["hits"] if h[1] == "mimic-id"]
    git(private, "update-ref", "-d", ex.EXPORT_REF)
    tip = export(private, {"replace_ids_sha256": [hashlib.sha256(ID.encode()).hexdigest()]})
    assert not [h for h in dc.check(private, tip, history=True, allow=[])["hits"] if h[1] == "mimic-id"]
    assert git(private, "show", f"{tip}~2:src/b.py") == "b = <subject>"


def test_a_replace_rule_that_would_change_the_tip_is_refused(private):
    with pytest.raises(ex.ExportError, match="would change today's tree"):
        export(private, {"replace_text": [["b = 0", "b = x"]]})


def test_the_release_tree_passes_the_data_check():
    r = dc.check(REPO, "HEAD", include=dc.include_list(REPO))
    assert [h for h in r["hits"] if h[2] is None] == []
