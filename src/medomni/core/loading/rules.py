"""The `rules` step of a dataset config: timing and visit rules (Datasets reference page; S1's U1.19 packages).

- `visit: unit`: the subject is the visit (one case, one visit).
- `one_visit: <code>`: each subject has exactly one `<code>` event, and every event belongs to its visit.
- `untimed: true`: an event with no time takes the time of the subject's `one_visit` event (cross-sectional data).
"""
from __future__ import annotations

from .readers import LoadError

KNOWN = ("visit", "one_visit", "untimed")


def apply(rules: dict, events: list[dict]) -> list[dict]:
    unknown = sorted(set(rules) - set(KNOWN))
    if unknown:
        raise LoadError(f"rules: unknown rule {', '.join(unknown)} (known: {', '.join(KNOWN)})")
    if rules.get("visit") not in (None, "unit"):
        raise LoadError(f"rules: visit must be 'unit', not {rules['visit']!r}")
    if rules.get("untimed") and not rules.get("one_visit"):
        raise LoadError("rules: untimed needs one_visit, whose event gives the time")
    if rules.get("visit") == "unit":
        for e in events:
            e["visit_id"] = e["subject_id"]
    code = rules.get("one_visit")
    if code:
        anchor: dict[str, dict] = {}
        for e in events:
            if e["code"] == code:
                if e["subject_id"] in anchor:
                    raise LoadError(f"rules: subject {e['subject_id']} has more than one {code} event (one_visit)")
                anchor[e["subject_id"]] = e
        missing = sorted({e["subject_id"] for e in events} - set(anchor))
        if missing:
            raise LoadError(f"rules: {len(missing)} subjects have no {code} event (one_visit), such as {missing[0]}")
        for e in events:
            a = anchor[e["subject_id"]]
            e["visit_id"] = a["visit_id"] or e["visit_id"]
            if rules.get("untimed") and e["time"] is None:
                e["time"] = a["time"]
    return events
