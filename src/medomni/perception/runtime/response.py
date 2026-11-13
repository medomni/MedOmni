"""Response blocks and the response every encoder returns (Container API)."""
import os


KINDS = ("labels", "events", "text", "embedding")
SCALES = ("probability", "logit", "score", "physical")


# ---------------- response ----------------

def labels(items, scale):
    if scale not in SCALES:
        raise ValueError(f"unknown scale '{scale}'")
    return {"kind": "labels", "scale": scale, "items": items}


def events(items):
    return {"kind": "events", "items": items}


def text(value):
    return {"kind": "text", "text": value}


def embedding(vector):
    vec = [float(v) for v in vector]
    return {"kind": "embedding", "dim": len(vec), "vector": vec}


def response(card, outputs, notes=(), healthy=True, duration_ms=None):
    return {
        "encoder_id": card["id"],
        "family": card["family"],
        "healthy": bool(healthy),
        "outputs": list(outputs),
        "notes": list(notes),
        "runtime": {"duration_ms": duration_ms,
                    "image_digest": os.environ.get("IMAGE_DIGEST")},
    }


def undeclared_labels(resp, card):
    """Labels the response emitted that the card does not declare.

    The card's outputs.labels is the complete vocabulary. A response can carry
    fewer labels than the card declares — an input that lacks a channel produces
    fewer. It can never carry one the card omits.
    """
    declared = set()
    for block in card.get("outputs") or []:
        declared |= set(block.get("labels") or [])
    emitted = set()
    for block in resp.get("outputs") or []:
        if block.get("kind") == "labels":
            emitted |= {item["label"] for item in block.get("items", [])}
        elif block.get("kind") == "events":
            emitted |= {item["label"] for item in block.get("items", [])}
    return sorted(emitted - declared)
