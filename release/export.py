"""The export: MedOmni's public repository is `main` filtered to the release tree (R-163, R-169). Nobody develops on
it; this tool builds it, and brings outside pull requests merged there back into `main`.

    python release/export.py export [--branch main] [--config <private yaml>] [--report <md>]
    python release/export.py import <public ref> [--branch main]

`export` filters a fresh clone of the branch with `git filter-repo`:
- paths: the release tree at the branch's tip (`release/public.yaml`), plus the older names of those files
  (`release/history-paths.yaml`), renamed to today's. Every other path leaves every version; commits left empty go.
- authors: each commit keeps its author and dates, with addresses merged by the private mailmap.
- messages: subject and body stay; the patterns the private config names (R-row ids, session names) are stripped;
  AI co-author trailers stay. Each commit gets a `Private-Commit: <id>` trailer naming the commit it came from.
The result is the hidden ref `refs/export/main`. It is deterministic: the same branch gives the same commit ids, so a
later export appends only the new commits. When the public line holds commits that came from outside (imported),
the new commits are appended to it instead of replacing it.

`import` applies each outside commit of the public line (one with no `Private-Commit` trailer) to the branch as an
ordinary commit by its author, with a `Public-Commit: <id>` trailer; the next export appends after it rather than
exporting it again. It refuses unless the branch is exactly where the last export left it.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPORT_REF = "refs/export/main"
PRIVATE_TRAILER, PUBLIC_TRAILER = "Private-Commit", "Public-Commit"


class ExportError(RuntimeError):
    pass


def git(repo, *args, inp: bytes | None = None, env: dict | None = None) -> str:
    r = subprocess.run(["git", *args], cwd=repo, input=inp, capture_output=True, env={**os.environ, **(env or {})})
    if r.returncode:
        raise ExportError(f"git {' '.join(args[:3])}: {r.stderr.decode(errors='replace').strip()[-400:]}")
    return r.stdout.decode(errors="replace")


def _yaml(path: Path) -> dict:
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _at(repo, ref: str, path: str) -> dict:
    """A YAML file as the ref holds it; {} when the ref has none (no path map yet)."""
    import yaml

    r = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=repo, capture_output=True)
    if r.returncode:
        if path.endswith("public.yaml"):
            raise ExportError(f"{ref} has no {path}: nothing says what the release tree is")
        return {}
    return yaml.safe_load(r.stdout) or {}


def release_files(repo, ref: str, include: list[str]) -> list[str]:
    return [p for p in git(repo, "ls-tree", "-r", "--name-only", ref).splitlines() if p.split("/", 1)[0] in include]


def path_lines(files: list[str], renames: dict[str, str]) -> str:
    """`git filter-repo --paths-from-file`: each release file; each older name, kept and renamed to today's."""
    lines = [f"literal:{p}" for p in sorted(files)]
    for old, new in sorted(renames.items()):
        if new in files:
            lines += [f"literal:{old}", f"literal:{old}==>{new}"]
    return "\n".join(lines) + "\n"


CALLBACK = r'''
import re as _re
_strip = [_re.compile(p.encode()) for p in {strip!r}]
_tidy = [(_re.compile(rb"\(\s*(?:[,;]\s*)*\)"), b""), (_re.compile(rb"\(\s*[,;]\s*"), b"("), (_re.compile(rb"\s*[,;]\s*\)"), b")"),
         (_re.compile(rb":\s*[,;]\s*"), b": "), (_re.compile(rb"\(\s+"), b"("), (_re.compile(rb"(?:,\s*){{2,}}"), b", "), (_re.compile(rb"[ \t]+([,.;:)])"), rb"\1"),
         (_re.compile(rb"[ \t]{{2,}}"), b" "), (_re.compile(rb"[ \t]+$", _re.M), b"")]
_trailer = _re.compile(rb"^[A-Za-z][A-Za-z-]*: ", _re.M)
_keep = _re.compile(rb"^(Co-Authored-By|Signed-off-by|{private}|{public}): ", _re.I)
msg = commit.message
lines = []
for line in msg.split(b"\n"):
    if not _keep.match(line):
        for rx in _strip:
            line = rx.sub(b"", line)
        for rx, rep in _tidy:
            line = rx.sub(rep, line)
    lines.append(line)
msg = b"\n".join(lines).rstrip(b"\n")
_subjects, _messages = {subjects!r}, {messages!r}
_new = _subjects.get(commit.original_id.decode())
if _new:
    msg = _new.encode() + (b"\n" + msg.split(b"\n", 1)[1] if b"\n" in msg else b"")
if commit.original_id.decode() in _messages:
    msg = _messages[commit.original_id.decode()].rstrip("\n").encode()
if b"\n{public}: " not in b"\n" + msg:
    paras = msg.split(b"\n\n")
    tail = paras[-1].split(b"\n")
    sep = b"\n" if len(paras) > 1 and all(_trailer.match(l) for l in tail if l) else b"\n\n"
    msg = msg + sep + b"{private}: " + commit.original_id
commit.message = msg + b"\n"
'''


def filtered(repo, branch: str, cfg: dict, work: Path) -> Path:
    """A fresh clone of the branch, filtered. Returns the clone; its `main` is the filtered history."""
    include = _at(repo, branch, "release/public.yaml")["include"]  # the allowlist and path map at the branch's tip
    renames = _at(repo, branch, "release/history-paths.yaml").get("paths", {})
    files = release_files(repo, branch, include)
    clone = work / "clone"
    git(work, "clone", "--quiet", "--no-local", "--no-tags", "--single-branch", "--branch", branch, str(Path(repo).resolve()), str(clone))
    if branch != "main":
        git(clone, "branch", "-m", branch, "main")
    (work / "paths").write_text(path_lines(files, renames), encoding="utf-8")
    args = ["filter-repo", "--force", "--quiet", "--paths-from-file", str(work / "paths"),
            "--commit-callback", CALLBACK.format(strip=list(cfg.get("strip_from_messages", [])), public=PUBLIC_TRAILER,
                                                 private=PRIVATE_TRAILER, subjects=_subjects(repo, cfg, "subjects"),
                                                 messages=_subjects(repo, cfg, "messages"))]
    if cfg.get("mailmap"):
        args += ["--mailmap", str(Path(repo, cfg["mailmap"]).resolve())]
    rules = replacements(clone, cfg, files + [o for o, n in renames.items() if n in files])
    if rules:
        (work / "replace").write_text("".join(f"{a}==>{b}\n" for a, b in rules), encoding="utf-8")
        args += ["--replace-text", str(work / "replace")]
    git(clone, *args)
    return clone


ID = re.compile(rb"(?<![0-9A-Za-z.])p?(1\d{7})(?![0-9A-Za-z.])")
# What cleaning a message must never leave behind (R-182): an emptied list or parenthesis, a dangling preposition
FRAGMENT = re.compile(r"\(,|\(\s|\(\s*;|,\s*\)|\(\)| for \(|after \(|\s(in|for|after|of|by)$")


def _subjects(repo, cfg: dict, key: str = "subjects") -> dict[str, str]:
    """The config's exact subjects (`subjects: {private commit: subject}`) or whole messages (`messages`), each id
    expanded to its full form."""
    out = {}
    for short, subject in (cfg.get(key) or {}).items():
        out[git(repo, "rev-parse", "--verify", f"{short}^{{commit}}").strip()] = str(subject)
    return out


def fragments(repo, clone: Path) -> list[str]:
    """Kept messages whose cleaning left a fragment: a line cleaning changed that now holds one, and the original
    line didn't. Returns `<private commit> | <line>`."""
    out = []
    for sha, t in trailers(clone, "main").items():
        pc = t.get(PRIVATE_TRAILER)
        if not pc:
            continue
        new = [l for l in git(clone, "log", "-1", "--format=%B", sha).splitlines() if not l.startswith(PRIVATE_TRAILER)]
        old = git(repo, "log", "-1", "--format=%B", pc).splitlines()
        for i, line in enumerate(new):
            was = old[i] if i < len(old) else ""
            if line != was and FRAGMENT.search(line) and not FRAGMENT.search(was):
                out.append(f"{pc[:12]} | {line[:120]}")
    return out


def replacements(clone: Path, cfg: dict, paths: list[str]) -> list[tuple[str, str]]:
    """The `--replace-text` rules, longest first: the config's literal rewrites (`replace_text`, such as private
    paths), and the ids it names by sha256 (`replace_ids_sha256`), found in the kept files' history so that no id is
    written in the config. A rule may only touch older versions: the tip must hold none of them."""
    import hashlib

    rules = [(str(a), str(b)) for a, b in (cfg.get("replace_text") or [])]
    wanted = set(cfg.get("replace_ids_sha256") or [])
    if wanted:
        found = set()
        keep = set(paths)
        blobs = {line.split()[2] for line in git(clone, "log", "--all", "--no-renames", "--raw", "--no-abbrev", "--format=").splitlines()
                 if line.startswith(":") and line.split("\t", 1)[1] in keep}
        blobs.discard("0" * 40)
        out = subprocess.run(["git", "cat-file", "--batch"], cwd=clone, input=("\n".join(sorted(blobs)) + "\n").encode(),
                             capture_output=True, check=True).stdout
        found = {m.decode() for m in ID.findall(out) if hashlib.sha256(m).hexdigest() in wanted}
        rules += [(f"p{v}", "p<subject>") for v in sorted(found)] + [(v, "<subject>") for v in sorted(found)]
    tip = subprocess.run(["git", "grep", "-l", "-F", *[x for a, _ in rules for x in ("-e", a)], "HEAD", "--", *paths],
                         cwd=clone, capture_output=True, text=True).stdout if rules else ""
    if tip.strip():
        raise ExportError(f"a replace rule would change today's tree: {len(tip.splitlines())} file(s) at the tip hold its text")
    return sorted(rules, key=lambda r: -len(r[0]))


def trailers(repo, ref: str) -> dict[str, dict[str, str]]:
    """{commit: {trailer: value}} for the Private- and Public-Commit trailers along a history."""
    out = {}
    for block in git(repo, "log", "--format=%H%x00%B%x01", ref).split("\x01"):
        if "\x00" not in block:
            continue
        sha, body = block.strip("\n").split("\x00", 1)
        t = {k: v for k, v in re.findall(rf"^({PRIVATE_TRAILER}|{PUBLIC_TRAILER}): (\S+)$", body, re.M)}
        out[sha] = t
    return out


def _meta(repo, sha: str) -> tuple[dict, bytes]:
    f = git(repo, "show", "-s", "--format=%an%x00%ae%x00%ad%x00%cn%x00%ce%x00%cd", "--date=raw", sha).rstrip("\n").split("\x00")
    env = dict(zip(("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_AUTHOR_DATE", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL",
                    "GIT_COMMITTER_DATE"), f))
    return env, subprocess.run(["git", "cat-file", "commit", sha], cwd=repo, capture_output=True, check=True).stdout.split(b"\n\n", 1)[1]


def append(clone: Path) -> str:
    """The filtered history's new commits appended to the public line `previous`; returns the new tip.

    Commits already exported (their Private-Commit trailer names a private commit `previous` holds) and commits that
    came from the public line (Public-Commit) aren't written again. The first new commit's parent is `previous`'s tip,
    whose tree must match the filtered history at the point the new commits start."""
    done = {t[PRIVATE_TRAILER] for t in trailers(clone, "refs/previous").values() if PRIVATE_TRAILER in t}
    seen = trailers(clone, "main")
    order = git(clone, "rev-list", "--reverse", "--topo-order", "main").split()
    exported = {s for s in order if seen[s].get(PRIVATE_TRAILER) in done or PUBLIC_TRAILER in seen[s]}
    new = [s for s in order if s not in exported]
    tip = git(clone, "rev-parse", "refs/previous").strip()
    if not new:
        return tip
    first_parents = git(clone, "rev-list", "--parents", "-n1", new[0]).split()[1:]
    if not first_parents or git(clone, "rev-parse", f"{first_parents[0]}^{{tree}}").strip() != git(clone, "rev-parse", f"{tip}^{{tree}}").strip():
        raise ExportError("the public line and the private branch disagree where the new commits start: "
                          "import the public line's outside commits first (`export.py import`)")
    mapped: dict[str, str] = {}
    for s in new:
        parents = []
        for p in git(clone, "rev-list", "--parents", "-n1", s).split()[1:]:
            parents.append(mapped.get(p, tip if p in exported else p))
        env, message = _meta(clone, s)
        tree = git(clone, "rev-parse", f"{s}^{{tree}}").strip()
        args = ["commit-tree", tree] + [x for p in dict.fromkeys(parents) for x in ("-p", p)]
        mapped[s] = git(clone, *args, inp=message, env=env).strip()
    return mapped[new[-1]]


def scan(repo, ref: str, cfg: dict) -> dict:
    """Every version of every file in a history: the data check (with the config's private patterns) and the release
    check's provenance rule for data files (a PROVENANCE stating a licence beside the file, then or at the tip)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("datacheck", HERE / "datacheck.py")
    dc = importlib.util.module_from_spec(spec); spec.loader.exec_module(dc)
    extra = None
    if cfg.get("private_patterns"):
        extra = Path(tempfile.mkstemp(prefix="medomni-patterns-")[1])
        extra.write_text("\n".join(cfg["private_patterns"]) + "\n", encoding="utf-8")
    try:
        r = dc.check(repo, ref, True, extra)
    finally:
        if extra:
            extra.unlink()
    licensed = re.compile(r"(?i)\blicen[cs](e|ed|es)\b")
    data_ext = {".edf", ".bdf", ".dat", ".hea", ".atr", ".dcm", ".h5", ".hdf5", ".npz", ".npy", ".parquet", ".vital", ".mat",
                ".pt", ".pth", ".pkl", ".bin", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".nii", ".gz", ".zst"}
    tip = set(git(repo, "ls-tree", "-r", "--name-only", ref).splitlines())
    provenance = {}
    unprovenanced = set()
    for sha in git(repo, "rev-list", ref).split():
        names = set(git(repo, "ls-tree", "-r", "--name-only", sha).splitlines())
        for path in names:
            pp = Path(path)
            if pp.suffix.lower() not in data_ext or path.startswith("docs/") or pp.name.startswith("PROVENANCE"):
                continue
            ok = False
            for folder in (pp.parent, pp.parent.parent):
                for n in ("PROVENANCE.md", "PROVENANCE.json"):
                    f = (folder / n).as_posix()
                    for where in ([sha] if f in names else []) + (["HEAD"] if f in tip else []):
                        key = (where if where != "HEAD" else ref, f)
                        if key not in provenance:
                            provenance[key] = bool(licensed.search(git(repo, "show", f"{key[0]}:{f}")))
                        ok = ok or provenance[key]
            if not ok:
                unprovenanced.add(pp.parent.as_posix())
    return {"versions": r["versions"], "hits": r["hits"], "data_without_provenance": sorted(unprovenanced)}


def export(repo=".", branch="main", config: Path | None = None, report: Path | None = None, fresh: bool = False) -> dict:
    """Filter the branch into EXPORT_REF. Once an export exists it is only appended to; `fresh` builds it anew, which
    is right only before anything has been pushed (a changed message rule or mailmap then reaches every commit)."""
    repo = Path(repo).resolve()
    cfg = _yaml(config) if config else {}
    previous = "" if fresh else subprocess.run(["git", "rev-parse", "--verify", "-q", EXPORT_REF], cwd=repo,
                                                capture_output=True, text=True).stdout.strip()
    with tempfile.TemporaryDirectory(prefix="medomni-export-") as tmp:
        clone = filtered(repo, branch, cfg, Path(tmp))
        left = fragments(repo, clone)
        if left:
            raise ExportError("cleaning left fragments in these messages; add exact subjects or a rule "
                              "(internal_docs/release/export.yaml):\n  " + "\n  ".join(left))
        tip = git(clone, "rev-parse", "main").strip()
        if previous:
            git(clone, "fetch", "--quiet", str(repo), f"+{EXPORT_REF}:refs/previous")
            if subprocess.run(["git", "merge-base", "--is-ancestor", "refs/previous", tip], cwd=clone).returncode != 0:
                tip = append(clone)
        git(clone, "update-ref", "refs/heads/export-tip", tip)
        git(repo, "fetch", "--quiet", str(clone), f"+refs/heads/export-tip:{EXPORT_REF}")
    out = {"tip": tip, "previous": previous or None}
    if report:
        report.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    return out


def import_public(public_ref: str, repo=".", branch="main") -> list[str]:
    """Apply the public line's outside commits (no Private-Commit trailer) after the last exported one to the branch,
    each as an ordinary commit by its author with a Public-Commit trailer. Returns the new private commits."""
    repo = Path(repo).resolve()
    seen = trailers(repo, public_ref)
    order = git(repo, "rev-list", "--reverse", "--topo-order", "--no-merges", public_ref).split()
    last = next((s for s in reversed(order) if PRIVATE_TRAILER in seen[s]), None)
    if last is None:
        raise ExportError("the public line holds no exported commit")
    checked = [l.split(" ", 1)[1] for l in git(repo, "worktree", "list", "--porcelain").splitlines()
               if l == f"branch refs/heads/{branch}"]
    if checked:
        raise ExportError(f"{branch} is checked out in a worktree; import moves the branch, which would leave that "
                          "checkout behind (its next commit would undo the import): switch it to another branch first")
    branch_tip = git(repo, "rev-parse", branch).strip()
    if seen[last][PRIVATE_TRAILER] != branch_tip:
        raise ExportError(f"{branch} has moved since the last export; export first, then import")
    outside = [s for s in order[order.index(last) + 1:] if PRIVATE_TRAILER not in seen[s]]
    made = []
    with tempfile.TemporaryDirectory(prefix="medomni-import-") as tmp:
        wt = Path(tmp) / "wt"
        git(repo, "worktree", "add", "--quiet", "--detach", str(wt), branch)
        try:
            for s in outside:
                patch = subprocess.run(["git", "diff", "--binary", f"{s}^", s], cwd=repo, capture_output=True, check=True).stdout
                git(wt, "apply", "--index", "--whitespace=nowarn", inp=patch)
                env, message = _meta(repo, s)
                env = {k: v for k, v in env.items() if k.startswith("GIT_AUTHOR")}  # the importer commits it
                body = message.rstrip(b"\n") + f"\n\n{PUBLIC_TRAILER}: {s}\n".encode()
                git(wt, "commit", "--quiet", "--no-verify", "-F", "-", inp=body, env=env)
                made.append(git(wt, "rev-parse", "HEAD").strip())
            if made:
                git(repo, "update-ref", f"refs/heads/{branch}", made[-1], branch_tip)
        finally:
            git(repo, "worktree", "remove", "--force", str(wt))
    return made


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="export", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export", help=f"filter the branch into {EXPORT_REF}")
    e.add_argument("--branch", default="main")
    e.add_argument("--config", type=Path, help="the private config (mailmap, message patterns, replace_text)")
    e.add_argument("--report", type=Path)
    e.add_argument("--fresh", action="store_true", help="build the export anew; only before anything has been pushed")
    i = sub.add_parser("import", help="bring the public line's outside commits into the branch")
    i.add_argument("public_ref")
    i.add_argument("--branch", default="main")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "export":
            r = export(".", a.branch, a.config, a.report, a.fresh)
            print(f"{EXPORT_REF} -> {r['tip'][:12]}" + (f" (after {r['previous'][:12]})" if r["previous"] else ""))
        else:
            made = import_public(a.public_ref, ".", a.branch)
            print(f"imported {len(made)} commit(s) into {a.branch}")
    except ExportError as err:
        print(f"export: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
