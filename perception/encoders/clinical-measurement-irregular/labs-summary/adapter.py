"""Summarize named lab rows without mixing units or guessing clinical meaning."""
import json
import math
from datetime import datetime
from medomni.perception.runtime import Degraded, text

FAMILY = "clinical-measurement-irregular"


def encode(sample, options):
    groups = {}
    for row in sample["rows"]:
        if row.get("format") != "long":
            continue
        try:
            timestamp = datetime.fromisoformat(row["t"].replace("Z", "+00:00"))
        except (AttributeError, TypeError, ValueError):
            raise Degraded("lab summaries require an ISO timestamp for every measurement")
        key = (row["name"], row.get("itemid"), row["unit"])
        groups.setdefault(key, []).append((timestamp, row["value"]))
    if not groups:
        raise Degraded("no numeric long-format lab measurements")
    results = []
    for (name, itemid, unit), rows in sorted(groups.items(), key=lambda pair: str(pair[0])):
        try:
            rows.sort(key=lambda row: row[0])
        except TypeError:
            raise Degraded("lab timestamps mix timezone-aware and timezone-naive values")
        last_values = {value for timestamp, value in rows if timestamp == rows[-1][0]}
        latest = rows[-1][1] if len(last_values) == 1 else None
        if latest is None:
            sample["notes"].append(f"{name}: latest is ambiguous; conflicting values share the latest timestamp")
        values = [value for _, value in rows]
        mean = math.fsum(value / len(values) for value in values)
        results.append(dict(name=name, itemid=itemid, unit=unit, count=len(values),
                            min=min(values), max=max(values), mean=mean,
                            latest=latest, latest_time=rows[-1][0].isoformat()))
    ignored = sum(row.get("format") != "long" for row in sample["rows"])
    if ignored:
        sample["notes"].append(f"{ignored} wide-format vital measurements excluded from lab summaries")
    return [text(json.dumps(results, allow_nan=False, sort_keys=True))]
