"""`medomni perception check <encoder-folder>` (R-122): one command that can refuse an encoder.

1. The card passes the registry's card check, which is Core's model card contract (as `medomni contracts check`).
2. The Dockerfile passes a static rule, before anything is built: every `torch==` install names the build index in
   `torch.yaml` (the CPU build) and pins a version on its list. A plug-in folder's `perception/torch.yaml` replaces it.
3. The image builds, from a context staged with what its `Dockerfile.dockerignore` allows (`build.py`). The torch
   inside it, if any, is the build and a version `torch.yaml` names: a dependency can bring in torch on its own.
4. Every `testdata/input*` sample runs through one container, and each response matches `testdata/expected.json`:
   numbers within a tolerance, everything else exactly. A neural network is reproducible to a tolerance and not to a
   bit: the BLAS library and the processor differ between machines. `--freeze` writes expected.json instead.
5. The family's pinned real samples (`--samples <dir>`, else the family's published sample set) run offline, with
   Docker networking off, and each response must be healthy and say only what the card declares.

`run_case(..., docker=False)` runs the same samples in this process, with no Docker, through the same run_encode.
"""
import hashlib
import json
import math
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import yaml

from . import RegistryError, encoder_id, tag
from .cards import load_card

TOL = 1e-3          # how far a number can move between two machines


class CheckFailed(RuntimeError):
    """The encoder failed a step; the message names it."""


# ---------------- the Dockerfile ----------------

TORCH = Path(__file__).resolve().parent / "torch.yaml"
PLUGIN_TORCH = "perception/torch.yaml"  # where a plug-in content folder ships its own list
_PIN = re.compile(r"(?<![\w.\-\[])torch==([0-9][0-9A-Za-z.+]*)")
_INDEX = re.compile(r"(?<!\S)(?:--index-url|-i)(?:=|\s+)(\S+)")


def torch_builds():
    """{index, versions}: the shipped torch.yaml, or the one plug-in folder that ships perception/torch.yaml."""
    from medomni.core import plugins

    found = [f.path / PLUGIN_TORCH for f in plugins.folders() if f.path and (f.path / PLUGIN_TORCH).is_file()]
    if len(found) > 1:
        raise RegistryError(f"{len(found)} plug-in folders ship {PLUGIN_TORCH}; at most one may")
    path = found[0] if found else TORCH
    try:
        builds = yaml.safe_load(path.read_text(encoding="utf-8"))
        index, versions = builds["index"], [str(v) for v in builds["versions"]]
    except (OSError, yaml.YAMLError, KeyError, TypeError) as exc:
        raise RegistryError(f"cannot read the torch build list {path}: {exc}") from exc
    return {"index": str(index).rstrip("/"), "build": str(builds.get("build", "")), "versions": versions}


def _run_commands(text):
    """The shell commands of a Dockerfile's RUN instructions: comment lines dropped, continuations joined."""
    lines = [line for line in text.splitlines() if not line.lstrip().startswith("#")]
    for instruction in re.sub(r"\\[ \t]*\n", " ", "\n".join(lines)).splitlines():
        head, _, body = instruction.strip().partition(" ")
        if head.upper() == "RUN":
            yield from re.split(r"&&|\|\||;", body)


def dockerfile_problems(dockerfile, builds):
    """What the torch rule refuses in one Dockerfile: a `torch==` install without the build index, or off the list."""
    problems = []
    for command in _run_commands(Path(dockerfile).read_text(encoding="utf-8")):
        pins = _PIN.findall(command)
        if not pins or "install" not in command:
            continue
        indexes = [u.strip("\"'").rstrip("/") for u in _INDEX.findall(command)]
        if builds["index"] not in indexes:
            problems.append(f"torch=={pins[0]} installs without --index-url {builds['index']}")
        problems += [f"torch=={v} is not on the torch build list ({', '.join(builds['versions'])})"
                     for v in pins if v not in builds["versions"]]
    return problems


def image_torch(image):
    """The torch version installed in a built image ('2.6.0+cpu'), or None when it has no torch."""
    probe = ("import importlib.metadata as m\ntry: print(m.version('torch'))\n"
             "except m.PackageNotFoundError: print('-')")
    result = subprocess.run(["docker", "run", "--rm", "--network", "none", "--entrypoint", "python", image, "-c", probe],
                            capture_output=True, text=True)
    if result.returncode:
        raise RegistryError(f"cannot read the torch version in {image}: {result.stderr.strip()[-200:]}")
    version = result.stdout.strip()
    return None if version == "-" else version


def image_torch_problems(version, builds):
    """What the torch rule refuses in a built image's installed torch version."""
    if version is None:
        return []
    base, _, label = version.partition("+")
    problems = []
    if label != builds["build"]:
        problems.append(f"the image has torch {version}, not a +{builds['build']} build (a dependency may pull it in)")
    if base not in builds["versions"]:
        problems.append(f"the image has torch {version}, not on the torch build list ({', '.join(builds['versions'])})")
    return problems


# ---------------- testdata ----------------

def family_options(edir, sample_name):
    """Non-secret request options for one sample, from the folder's family-test.json."""
    path = Path(edir) / "family-test.json"
    if not path.exists():
        return {}
    try:
        config = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise RegistryError(f"cannot read {path.name}: {exc}") from exc
    if not isinstance(config, dict):
        raise RegistryError("family-test.json must contain an object")
    default, samples = config.get("default", {}), config.get("samples", {})
    if not isinstance(default, dict) or not isinstance(samples, dict):
        raise RegistryError("family-test.json default and samples must be objects")
    override = samples.get(sample_name, {})
    if not isinstance(override, dict):
        raise RegistryError(f"family-test.json entry for {sample_name} must be an object")
    options = dict(default.get("options", default))
    options.update(override.get("options", override))
    return options


def _in_process(edir, card, bodies):
    """Every sample through one loaded model, in this process. Weights are read once."""
    from medomni.perception.runtime import load_adapter
    from medomni.perception.runtime.serve import run_encode

    adapter = load_adapter(Path(edir) / "adapter.py")
    model = adapter.load() if hasattr(adapter, "load") else None
    return [run_encode(card, adapter, body, data_root=str(Path(edir) / "testdata"), model=model) for body in bodies]


def _via_docker(edir, card, bodies, image_tag="dev"):
    """Every sample through one container (the one Docker runner). Weights are read once."""
    from medomni.perception.gateway.runner import Container

    with Container(encoder_id(edir), data=str(Path(edir) / "testdata"), tag=tag(encoder_id(edir), image_tag),
                   encoders_dir=Path(edir).parent.parent) as encoder:
        out = []
        for body in bodies:
            status, response = encoder.call("/encode", body)
            if status != 200:  # the in-process path raises on a caller error, so this one must too
                raise CheckFailed(f"HTTP {status} from /encode: {response.get('error', response)}")
            out.append(response)
        return out


def run_case(edir, docker=True, image_tag="dev"):
    """Run every testdata/input* sample. Returns the card and {file name: response}."""
    edir = Path(edir)
    card = load_card(edir)
    inputs = sorted(p.name for p in (edir / "testdata").glob("input*") if p.is_file())
    if not inputs:
        raise CheckFailed("no testdata/input* file")
    bodies = [{"family": card["family"], "path": name, "options": family_options(edir, name)} for name in inputs]
    responses = _via_docker(edir, card, bodies, image_tag) if docker else _in_process(edir, card, bodies)
    for resp in responses:
        resp.pop("runtime", None)          # duration and digest are not comparable
    return card, dict(zip(inputs, responses))


def compare(expected, actual, tol=TOL, path="response"):
    """Differences between a frozen response and a fresh one. Numbers match within tol; everything else exactly."""
    if isinstance(expected, bool) or isinstance(actual, bool):
        return [] if expected is actual else [f"{path}: expected {expected}, got {actual}"]
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        if not math.isfinite(expected) or not math.isfinite(actual):
            return [f"{path}: expected and actual values must be finite numbers, got {expected!r} and {actual!r}"]
        if abs(expected - actual) > tol:
            return [f"{path}: expected {expected}, got {actual} (tolerance {tol})"]
        return []
    if isinstance(expected, dict) and isinstance(actual, dict):
        diffs = []
        for key in sorted(set(expected) | set(actual)):
            if key not in actual:
                diffs.append(f"{path}.{key}: missing from the response")
            elif key not in expected:
                diffs.append(f"{path}.{key}: not in expected.json")
            else:
                diffs += compare(expected[key], actual[key], tol, f"{path}.{key}")
        return diffs
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            return [f"{path}: expected {len(expected)} item(s), got {len(actual)}"]
        return [d for i, (e, a) in enumerate(zip(expected, actual)) for d in compare(e, a, tol, f"{path}[{i}]")]
    return [] if expected == actual else [f"{path}: expected {expected!r}, got {actual!r}"]


def load_expected(path, result_names):
    """Load a named response map. Return (mapping or None, errors)."""
    path = Path(path)
    if not path.exists():
        return None, ["no testdata/expected.json: run `medomni perception check --freeze`"]
    try:
        expected = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        return None, [f"could not read testdata/expected.json: {exc}"]
    if not isinstance(expected, dict):
        return None, ["expected.json must contain an object of sample names"]
    if "encoder_id" in expected:       # the one-sample shape, before samples were named
        return None, ["expected.json holds a single response: run `medomni perception check --freeze`"]
    if not expected:
        return None, ["expected.json has no frozen responses: run `medomni perception check --freeze`"]
    return expected, [f"{name}: in expected.json, but no such testdata file" for name in expected
                      if name not in result_names]


def testdata_problems(card, results, expected_path, tol=TOL):
    """Everything wrong with a set of fresh testdata responses, against the card and expected.json."""
    from medomni.perception.runtime import undeclared_labels

    errs = [f"card declares a '{b['kind']}' block with no vocabulary" for b in card.get("outputs") or []
            if b.get("kind") in ("labels", "events") and not b.get("labels")]
    expected, expected_errors = load_expected(expected_path, results)
    errs += expected_errors
    for name, resp in results.items():
        undeclared = undeclared_labels(resp, card)
        if undeclared:
            errs.append(f"{name}: labels not declared in the card: {', '.join(undeclared)}")
        if expected is not None and name not in expected:
            errs.append(f"{name}: not in expected.json: run `medomni perception check --freeze`")
        elif expected is not None:
            errs += compare(expected[name], resp, tol, path=name)[:8]
    return errs


def freeze(edir, results):
    path = Path(edir) / "testdata" / "expected.json"
    path.write_text(json.dumps(results, indent=1, allow_nan=False) + "\n")
    return path


# ---------------- real family samples ----------------

def manifest_entries(samples_dir):
    """The request names of one family-samples folder, after its manifest's hashes are verified."""
    samples_dir = Path(samples_dir)
    manifest = samples_dir / "manifest.jsonl"
    if not manifest.is_file():
        raise RegistryError(f"no family sample manifest: {manifest}")
    entries = []
    for line_number, line in enumerate(manifest.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except ValueError as exc:
            raise RegistryError(f"{manifest}:{line_number}: invalid JSON: {exc}") from exc
        name, declared = entry.get("file"), entry.get("sha256")
        if not isinstance(name, str) or not name or declared is None:
            raise RegistryError(f"{manifest}:{line_number}: file and sha256 are required")
        paths = ({name: declared} if isinstance(declared, str)
                 else {name + suffix: digest for suffix, digest in declared.items()})
        for relative, digest in paths.items():
            relative_path = Path(relative)
            if relative_path.is_absolute() or ".." in relative_path.parts:
                raise RegistryError(f"family sample escapes its directory: {relative}")
            path = samples_dir / relative_path
            if not path.is_file():
                raise RegistryError(f"family sample is missing: {relative}")
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != digest:
                raise RegistryError(f"family sample hash mismatch for {relative}: {actual} != {digest}")
        entries.append(name + ".hea" if isinstance(declared, dict) else name)
    # Per-file manifests list a WFDB record's .dat beside its .hea; the header is the request.
    headers = {Path(e).with_suffix("") for e in entries if e.endswith(".hea")}
    entries = [e for e in entries if not (e.endswith(".dat") and Path(e).with_suffix("") in headers)]
    if not entries:
        raise RegistryError(f"family sample manifest is empty: {manifest}")
    return entries


def _finite(value, path="response"):
    errors = []
    if isinstance(value, float) and not math.isfinite(value):
        errors.append(f"{path}: value must be finite")
    elif isinstance(value, dict):
        for key, child in value.items():
            errors += _finite(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors += _finite(child, f"{path}[{index}]")
    return errors


def family_response_problems(card, response):
    """The output facts a card promises for every real sample."""
    errors = []
    if not isinstance(response, dict):
        return ["response is not an object"]
    if response.get("encoder_id") != card["id"]:
        errors.append("response encoder_id does not match the card")
    if response.get("family") != card["family"]:
        errors.append("response family does not match the card")
    if response.get("healthy") is not True:
        errors.append("real family sample did not produce healthy output")
    outputs = response.get("outputs")
    if not isinstance(outputs, list):
        return errors + ["response outputs is not a list"]
    declarations = card.get("outputs") or []
    if len(outputs) != len(declarations):
        errors.append(f"card declares {len(declarations)} output block(s), got {len(outputs)}")
    for index, block in enumerate(outputs):
        if not isinstance(block, dict):
            errors.append(f"output {index} is not an object")
            continue
        declaration = declarations[index] if index < len(declarations) else {}
        if block.get("kind") != declaration.get("kind"):
            errors.append(f"output {index} kind does not match the card")
        if block.get("kind") == "embedding" and block.get("dim") != declaration.get("dim"):
            errors.append(f"output {index} embedding dimension does not match the card")
        if block.get("kind") in ("labels", "events"):
            declared = set(declaration.get("labels") or [])
            emitted = {item.get("label") for item in block.get("items") or [] if isinstance(item, dict)}
            unknown = sorted(emitted - declared)
            if unknown:
                errors.append(f"output {index} has undeclared labels: {', '.join(unknown)}")
    return errors + _finite(response)


def download_family_samples(family_id):
    """The family's published sample set (core/families/<id>.yaml `samples`), from Hugging Face."""
    from medomni.core import families

    samples = families.get(family_id).samples
    if samples is None:
        raise RegistryError(f"family '{family_id}' publishes no samples")
    from huggingface_hub import snapshot_download

    snapshot = Path(snapshot_download(samples.hf_repo, repo_type="dataset", revision=samples.revision,
                                      allow_patterns=[samples.dir.rstrip("/") + "/**"]))
    return snapshot / samples.dir


def offline_encode(edir, samples_dir, sample_name, options, image_tag="dev"):
    """One sample through the image's one-shot entry point, with Docker networking off."""
    body = json.dumps(options, separators=(",", ":"), allow_nan=False)
    command = ["docker", "run", "--rm", "--network", "none", "-v", f"{Path(samples_dir).resolve()}:/data:ro",
               tag(encoder_id(edir), image_tag), "python", "-m", "medomni.perception.runtime.serve", "encode",
               "--family", load_card(edir)["family"], "--path", sample_name, "--options-json", body]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip()
                           or f"offline Docker inference exited {result.returncode}")
    try:
        return json.loads(result.stdout)
    except ValueError as exc:
        raise RuntimeError(f"offline Docker inference did not return JSON: {result.stdout}") from exc


def family_samples(edir, samples_root=None, image_tag="dev"):
    """Run the family's real samples offline; returns (number of samples, failures)."""
    edir = Path(edir)
    card = load_card(edir)
    root = Path(samples_root).resolve() / card["family"] if samples_root else download_family_samples(card["family"])
    with tempfile.TemporaryDirectory(prefix=".family-test-") as directory:
        materialized = Path(directory) / card["family"]
        shutil.copytree(root, materialized)
        names = manifest_entries(materialized)
        failures = []
        for name in names:
            try:
                response = offline_encode(edir, materialized, name, family_options(edir, name), image_tag)
            except RuntimeError as exc:  # the container crashed: a failure, never "not run"
                failures.append(f"{name}: container crashed: {str(exc).splitlines()[-1][:200]}")
                continue
            failures += [f"{name}: {error}" for error in family_response_problems(card, response)]
    return len(names), failures


# ---------------- the command ----------------

def check(edir, samples_root=None, do_freeze=False, tol=TOL, out=print, build=True, record=False):
    """Every step of `medomni perception check`; returns 0 when the encoder passes, 1 when a step fails. With `record`,
    a passing encoder is written into the deployment record (`registry/record.py`)."""
    from . import build as image_build, cards

    edir = Path(edir).resolve()
    eid = encoder_id(edir)
    errs, warns = cards.check(edir)
    for w in warns:
        out(f"  ~ {w}")
    if errs:
        out(f"[{eid}] card REJECTED:")
        for e in errs[:8]:
            out(f"   - {e}")
        return 1
    out(f"[{eid}] card ok")
    if not (edir / "adapter.py").is_file():
        out(f"[{eid}] card only, no adapter: nothing to build")
        return 0
    if (edir / "Dockerfile").is_file():
        try:
            problems = dockerfile_problems(edir / "Dockerfile", torch_builds())
        except RegistryError as exc:
            out(f"[{eid}] REJECTED: {exc}")
            return 1
        if problems:
            out(f"[{eid}] Dockerfile REJECTED:")
            for e in problems[:8]:
                out(f"   - {e}")
            return 1
        out(f"[{eid}] Dockerfile ok")
    try:
        if build:
            image, image_id = image_build.build(edir)
            out(f"[{eid}] built {image} ({image_id[:19]})")
        problems = image_torch_problems(image_torch(tag(eid, "dev")), torch_builds())
        if problems:
            out(f"[{eid}] image REJECTED:")
            for e in problems:
                out(f"   - {e}")
            return 1
        card, results = run_case(edir, docker=True)
    except Exception as exc:  # a failed build or a crashed container is a failure, never "not run"
        out(f"[{eid}] REJECTED: {type(exc).__name__}: {exc}")
        return 1
    if do_freeze:
        out(f"[{eid}] froze {len(results)} sample(s) in {freeze(edir, results)}")
        return 0
    problems = testdata_problems(card, results, edir / "testdata" / "expected.json", tol)
    if problems:
        out(f"[{eid}] testdata REJECTED:")
        for e in problems[:12]:
            out(f"   - {e}")
        return 1
    out(f"[{eid}] testdata ok: {len(results)} sample(s)")
    from medomni.core import families

    def recorded(l3_status, l3_detail=None):
        if not record:
            return 0
        from . import record as deployed

        try:
            entry = deployed.write(edir, f"{len(results)} sample(s)", l3_status, l3_detail)
        except RegistryError as exc:
            out(f"[{eid}] not recorded: {exc}")
            return 1
        out(f"[{eid}] recorded {entry['image_id'][:19]} in {deployed.RECORD}")
        return 0

    fam = families.get(card["family"])
    if samples_root is None and fam.samples is None:
        if fam.samples_access == "controlled":
            out(f"[{eid}] real samples: access-controlled, not distributed; the test data stands in")
            return recorded("UNVERIFIED-access-controlled", "the family's sample set is access-controlled")
        out(f"[{eid}] real samples: the family publishes none")
        return recorded("UNVERIFIED-no-supply", "the family publishes no samples")
    try:
        n, failures = family_samples(edir, samples_root)
    except (RegistryError, ImportError, OSError) as exc:
        out(f"[{eid}] real samples REJECTED: {exc}")
        return 1
    if failures:
        out(f"[{eid}] real samples REJECTED:")
        for e in failures[:8]:
            out(f"   - {e}")
        return 1
    out(f"[{eid}] real samples ok: {n}, offline")
    return recorded("PASS", f"{n} sample(s), offline")
