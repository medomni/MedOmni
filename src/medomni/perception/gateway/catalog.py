"""The cards, read from disk once. Discovery never starts a container."""
import dataclasses
import difflib
import re

from .. import registry  # the card check's rules, not a second set of them

# Field -> how much a query token matching it is worth.
WEIGHTS = (("id", 3.0), ("family", 3.0), ("modality", 3.0),
           ("labels", 1.6), ("summary", 1.5), ("intended_use", 1.0),
           ("limits", 0.5))
TOP_WEIGHT = max(weight for _, weight in WEIGHTS)
MIN_SCORE = 0.2
FUZZY_RATIO = 0.84      # below this, two words are different words

# The words people use for a signal, mapped onto the words the cards use.
ALIASES = {
    "xray": "cxr radiograph chest", "x": "cxr", "ray": "radiograph",
    "radiograph": "cxr chest", "radiography": "cxr", "chest": "cxr",
    "cxr": "chest radiograph", "lung": "cxr chest", "thorax": "cxr chest",
    "ekg": "ecg", "electrocardiogram": "ecg", "cardiac": "ecg heart",
    "heart": "ecg cardiac", "rhythm": "ecg",
    "eeg": "sleep electroencephalogram", "electroencephalogram": "eeg",
    "vitals": "clinical measurement vital", "vital": "clinical measurement",
    "signs": "measurement", "waveform": "ecg eeg",
    "embedding": "embedding vector", "image": "cxr radiograph",
}


def tokens(text):
    return [t for t in re.split(r"[^a-z0-9]+", str(text).lower()) if t]


@dataclasses.dataclass(frozen=True)
class Entry:
    id: str
    family: str
    modality: str
    runnable: bool
    card: dict
    haystack: dict

    @property
    def kinds(self):
        return [b.get("kind") for b in self.card.get("outputs") or []]

    @property
    def labels(self):
        return {label for b in self.card.get("outputs") or []
                for label in (b.get("labels") or [])}

    def summary(self, score=None):
        """The entry an agent lists. The full card is a separate call."""
        out = {
            "id": self.id,
            "family": self.family,
            "modality": self.modality,
            "summary": " ".join(str(self.card.get("summary", "")).split()),
            "outputs": [{"kind": b.get("kind"), "scale": b.get("scale"),
                         "dim": b.get("dim"), "n_labels": len(b.get("labels") or []) or None}
                        for b in self.card.get("outputs") or []],
            "runnable": self.runnable,
            "reliability": (self.card.get("reliability") or {}).get("status"),
            "acceptance": self.card.get("acceptance"),
            "license": self.card.get("license"),
        }
        if score is not None:
            out["score"] = round(score, 3)
        return out


def _haystack(card):
    return {
        "id": tokens(card.get("id")),
        "family": tokens(card.get("family")),
        "modality": tokens(card.get("modality")),
        "summary": tokens(card.get("summary")),
        "intended_use": tokens(card.get("intended_use")),
        "limits": tokens(" ".join(card.get("limits") or [])),
        "labels": tokens(" ".join(label for b in card.get("outputs") or []
                                  for label in (b.get("labels") or []))),
    }


class CatalogError(Exception):
    """A card the gateway will not serve."""


class Catalog:
    def __init__(self, entries):
        self._entries = {entry.id: entry for entry in entries}

    @classmethod
    def load(cls, encoders_dir=None, ids=()):
        """Every card (only `ids` when given), checked by the registry's card check (Core's model card contract).

        A card the check would reject is not served: an agent choosing on a
        malformed card is worse than an agent seeing one encoder fewer. Loading
        fails rather than skipping, so a bad card is fixed and not ignored.
        """
        from medomni.core import families as core_families

        known, entries, problems = set(core_families.load_registry()), [], []
        for directory in registry.encoder_dirs(ids, encoders_dir):
            card = registry.cards.load_card(directory)
            if not isinstance(card, dict):
                problems.append(f"{directory.name}: card.yaml is not a mapping")
                continue
            errors, _ = registry.cards.check(directory, known)
            if errors:
                problems += [f"{directory.name}: {e}" for e in errors]
                continue
            runnable = (directory / "adapter.py").is_file()
            if runnable and not (directory / "Dockerfile").is_file():
                problems.append(f"{directory.name}: runnable but has no Dockerfile")
                continue
            entries.append(Entry(id=card["id"], family=card.get("family"),
                                 modality=card.get("modality"), runnable=runnable,
                                 card=card, haystack=_haystack(card)))

        seen = {}
        for entry in entries:
            if entry.id in seen:
                problems.append(f"{entry.id}: declared by two directories")
            seen[entry.id] = entry
        if problems:
            raise CatalogError("the encoder catalog is not valid:\n  - "
                               + "\n  - ".join(problems))
        return cls(entries)

    def __len__(self):
        return len(self._entries)

    def get(self, encoder_id):
        return self._entries.get(encoder_id)

    def all(self):
        return list(self._entries.values())

    def families(self):
        counts = {}
        for entry in self._entries.values():
            row = counts.setdefault(entry.family, {"family": entry.family,
                                                   "encoders": 0, "runnable": 0})
            row["encoders"] += 1
            row["runnable"] += int(entry.runnable)
        return sorted(counts.values(), key=lambda row: row["family"])

    def search(self, q=None, family=None, modality=None, kind=None, label=None,
               runnable=True, limit=20, min_score=MIN_SCORE):
        """Filter, then rank by q. Returns [(entry, score)], best first."""
        found = []
        for entry in self._entries.values():
            if runnable is not None and entry.runnable != runnable:
                continue
            if family and entry.family != family:
                continue
            if modality and entry.modality != modality:
                continue
            if kind and kind not in entry.kinds:
                continue
            if label and label not in entry.labels:
                continue
            found.append(entry)

        if not q or not q.strip():
            return [(entry, None) for entry in sorted(found, key=lambda e: e.id)][:limit]

        wanted = _expand(tokens(q))
        scored = [(entry, _score(entry, wanted)) for entry in found]
        scored = [pair for pair in scored if pair[1] >= min_score]
        scored.sort(key=lambda pair: (-pair[1], pair[0].id))
        return scored[:limit]


def _expand(query_tokens):
    out = list(query_tokens)
    for token in query_tokens:
        out.extend(tokens(ALIASES.get(token, "")))
    return out


def _match(token, words):
    """0..1 for one query token against one field's words."""
    if token in words:
        return 1.0
    best = 0.0
    for word in words:
        if len(token) >= 3 and word.startswith(token):
            best = max(best, 0.8)
        else:
            ratio = difflib.SequenceMatcher(None, token, word).ratio()
            if ratio >= FUZZY_RATIO:
                best = max(best, ratio * 0.7)
    return best


def _score(entry, query_tokens):
    total = sum(max(weight * _match(token, entry.haystack[field])
                    for field, weight in WEIGHTS)
                for token in query_tokens)
    return total / (len(query_tokens) * TOP_WEIGHT)
