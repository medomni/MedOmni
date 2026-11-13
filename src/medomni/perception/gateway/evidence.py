"""What an input is, how a run is identified, and the Evidence that wraps it."""
import asyncio
import hashlib
import json
from pathlib import Path

from .. import runtime

CHUNK = 1 << 20


class BadPath(ValueError):
    """The request names a file the gateway will not read."""


class IdentityMismatch(RuntimeError):
    """The container answered for a different encoder than the card selected."""


def resolve_input(data_root, rel):
    """Resolve rel under data_root and confine it there, as the container does."""
    if not rel or rel.startswith("/"):
        raise BadPath(f"path must be relative to the data root: '{rel}'")
    root = Path(data_root).resolve()
    target = (root / rel).resolve()
    if target != root and root not in target.parents:
        raise BadPath(f"path escapes the data root: '{rel}'")
    if not target.is_file():
        raise BadPath(f"no such file: '{rel}'")
    return target


def _digest_files(paths, root):
    """sha256 over each file's name under root and its bytes, in a fixed order.

    Both sides are resolved before they are compared: a data root reached
    through a symbolic link (/var on macOS) is the same directory as its target,
    and the digest must not depend on which spelling the caller used.
    """
    root = Path(root).resolve()
    sha = hashlib.sha256()
    for path in paths:
        resolved = Path(path).resolve()
        name = resolved.relative_to(root) if resolved.is_relative_to(root) else resolved.name
        sha.update(str(name).encode())
        sha.update(b"\0")
        with open(resolved, "rb") as handle:
            for chunk in iter(lambda: handle.read(CHUNK), b""):
                sha.update(chunk)
        sha.update(b"\0")
    return sha.hexdigest()


def _identity(family, path, data_root):
    """Digest every file the input is made of. Return None if the family cannot say.

    The family reader can fail to open an input. A header can name a missing .dat
    file. A header can fail to decode. This function turns those failures into
    BadPath, because the caller named the file. The service then has one
    exception to catch.

    PermissionError stays out of that list. A file we cannot read under our own
    data root is a broken deployment. A 400 would blame the caller and hide it.
    """
    try:
        manifest = runtime.input_manifest(family, path, data_root)
        if not manifest:
            return None        # the family cannot say what this input is made of
        return _digest_files(manifest, Path(data_root).resolve())
    except runtime.BadRequest as exc:
        raise BadPath(str(exc)) from None
    except (FileNotFoundError, IsADirectoryError, NotADirectoryError,
            UnicodeDecodeError) as exc:
        raise BadPath(f"the input '{path}' cannot be read: {exc}") from None


async def input_identity(family, path, data_root):
    """sha256 over every file the input is made of, or None when it cannot be known.

    A WFDB record is a header plus the signal files it names. Hashing the header
    alone would leave a changed .dat invisible, and a cache keyed on it would
    return the wrong Evidence — so the whole manifest is hashed, and a family
    that cannot produce one yields None.
    """
    return await asyncio.to_thread(_identity, family, path, data_root)


def fingerprint(card, input_sha256, path, image_id, options):
    """sha256 over the encoder, its weights and source, the image, and the input.

    `image_id` is what docker actually resolved, not the digest written in a
    card: card digests are null until the images are published, and an image
    rebuilt under the same tag has to change this value.
    """
    material = {
        "encoder_id": card.get("id"),
        "family": card.get("family"),
        "weights_sha256": (card.get("weights") or {}).get("sha256"),
        "source_rev": (card.get("source") or {}).get("rev"),
        "image_id": image_id,
        "input_sha256": input_sha256,
        # Falls back to the name only when the content could not be identified.
        # provenance.input_complete says which of the two happened.
        "input_path": None if input_sha256 else path,
        "options": options or {},
    }
    blob = json.dumps(material, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(blob.encode()).hexdigest()


def verify(card, response):
    """The container must answer for the encoder the card selected."""
    got, want = response.get("encoder_id"), card.get("id")
    if got != want:
        raise IdentityMismatch(f"container answered for '{got}', the card selects '{want}'")
    got, want = response.get("family"), card.get("family")
    if got != want:
        raise IdentityMismatch(f"container answered family '{got}', the card declares '{want}'")


def compose(card, response, fingerprint_, input_sha256, image_id,
            start_ms=0.0, cached=False):
    """Container response + card verbatim + provenance + fingerprint.

    Nothing here recomputes a card field or reinterprets an output block.
    """
    verify(card, response)
    runtime = dict(response.get("runtime") or {})
    runtime["container_start_ms"] = start_ms
    runtime["cached"] = cached
    return {
        "encoder_id": card["id"],
        "family": card["family"],
        "healthy": response.get("healthy"),
        "outputs": response.get("outputs") or [],
        "notes": response.get("notes") or [],
        "reliability": card.get("reliability"),
        "card": card,
        "provenance": {
            "weights_sha256": (card.get("weights") or {}).get("sha256"),
            "source_rev": (card.get("source") or {}).get("rev"),
            "image": (card.get("runtime") or {}).get("image"),
            "image_id": image_id,
            "input_sha256": input_sha256,
            # false: the input could not be content-addressed, so this Evidence
            # is not pinned to the bytes that produced it, and is never cached.
            "input_complete": input_sha256 is not None,
        },
        "fingerprint": fingerprint_,
        "runtime": runtime,
    }
