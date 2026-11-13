"""Atom-level format check (slipway): submission exists, parses, names exactly
the asked targets, values are numeric. Emits {"format_ok": 0|1, "why": ...} on
stdout — a named dimension so `harbor view` reads honestly; NEVER a score."""
import csv
import json
import sys


def main() -> None:
    sub_path, expected_path = sys.argv[1], sys.argv[2]
    expected = set(json.load(open(expected_path))["targets"])
    try:
        rows = list(csv.DictReader(open(sub_path)))
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"format_ok": 0, "why": f"unreadable: {e}"}))
        return
    if not rows or set(rows[0].keys()) != {"target", "prediction"}:
        print(json.dumps({"format_ok": 0, "why": "header must be target,prediction"}))
        return
    got = {}
    for r in rows:
        try:
            got[r["target"]] = float(r["prediction"])
        except (ValueError, TypeError):
            print(json.dumps({"format_ok": 0, "why": f"non-numeric prediction for {r['target']!r}"}))
            return
    if set(got) != expected:
        print(json.dumps({"format_ok": 0, "why": f"targets mismatch: missing {sorted(expected - set(got))}, extra {sorted(set(got) - expected)}"}))
        return
    print(json.dumps({"format_ok": 1}))


if __name__ == "__main__":
    main()
