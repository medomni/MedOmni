"""Helpers several decoders share: input manifests, companion files, EDF signals."""
import json

from ..errors import BadRequest, Degraded




def _edf_signals(path):
    import edfio
    if path.suffix.lower() != '.edf':
        raise Degraded('this reader requires EDF')
    try:
        record = edfio.read_edf(path)
        if 'EDF+D' in record.reserved:
            raise Degraded('discontinuous EDF is not supported')
        return list(record.signals)
    except (ValueError, OSError) as exc:
        raise Degraded(f'cannot read EDF: {exc}') from exc


# ---------------- what an input is made of ----------------
#
# FAMILY BOUNDARY, as above. A request names one file, and for some families
# that file names others. Anything that has to identify an input — a
# fingerprint, a cache key — needs every file, not only the one named. That is
# family knowledge, so it lives here beside the readers and never in a caller.


def _manifest_one(path, root):
    return [path]


def _manifest_wfdb(path, root):
    """The header plus the signal files it names. None when it cannot be read.

    Parsed with the standard library: a caller that only needs to identify the
    input must not have to install a waveform library to do it. None means "this
    cannot be answered", and a caller must then treat the input as unidentified
    rather than assume the header is all of it.
    """
    if path.suffix != ".hea":
        return None
    try:
        lines = [line.strip() for line in path.read_text().splitlines()]
    except OSError:
        return None
    lines = [line for line in lines if line and not line.startswith("#")]
    if not lines:
        return None
    record = lines[0].split()
    if len(record) < 2 or "/" in record[0]:      # multi-segment: not handled here
        return None
    try:
        n_signals = int(record[1])
    except ValueError:
        return None
    if len(lines) - 1 < n_signals:
        return None

    files = []
    for spec in lines[1:1 + n_signals]:
        name = spec.split()[0]
        if name == "~":                          # a null signal has no file
            continue
        target = (path.parent / name).resolve()
        if target != root and root not in target.parents:
            raise BadRequest(f"the header names a file outside DATA_ROOT: '{name}'")
        files.append(target)
    return [path] + sorted(set(files) - {path})


def _read_json_manifest(path, root):
    if path.suffix.lower() != '.json':
        raise Degraded('this family requires a JSON manifest')
    try:
        manifest = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise Degraded(f'cannot read JSON manifest: {exc}') from exc
    if not isinstance(manifest, dict):
        raise Degraded('JSON manifest must contain an object')
    return manifest


def _confined_companion(path, root, name):
    if not isinstance(name, str) or not name:
        raise Degraded('manifest file name must be a non-empty string')
    target = (path.parent / name).resolve()
    if target != root and root not in target.parents:
        raise BadRequest(f"the manifest names a file outside DATA_ROOT: '{name}'")
    if not target.is_file():
        raise Degraded(f"the manifest file does not exist: '{name}'")
    return target


def _manifest_json_files(path, root):
    try:
        manifest = _read_json_manifest(path, root)
        names = manifest.get('files')
        if names is None and isinstance(manifest.get('file'), str):
            names = [manifest['file']]
        if not isinstance(names, list) or not names:
            return None
        return [path] + [_confined_companion(path, root, name) for name in names]
    except Degraded:
        return None
