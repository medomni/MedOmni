"""Generate a hand-checkable synthetic OMH fixture (Apache-2.0)."""
import json
from pathlib import Path

root = Path(__file__).parent / "testdata"
records = []
for minute, value in enumerate([60, 80, 100, 0]):
    records.append({
        "header": {"schema_id": {"namespace": "omh", "name": "heart-rate"}},
        "body": {"heart_rate": {"value": value, "unit": "beats/min"},
                 "effective_time_frame": {"date_time": f"2024-01-01T00:0{minute}:00Z"}},
    })
(root / "input.json").write_text(json.dumps(records, indent=2) + "\n")
(root / "input-empty.json").write_text("[]\n")
