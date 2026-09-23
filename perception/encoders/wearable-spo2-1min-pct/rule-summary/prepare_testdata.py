"""Hand-checkable synthetic OMH fixture; Apache-2.0."""
import json
from pathlib import Path
root = Path(__file__).parent / "testdata"
records = [{"header": {"schema_id": {"namespace": "omh", "name": "oxygen-saturation"}},
            "body": {"oxygen_saturation": {"value": value, "unit": "%"},
                     "effective_time_frame": {"date_time": f"2024-01-01T00:0{i}:00Z"}}}
           for i, value in enumerate([90, 95, 100, 101])]
(root / "input.json").write_text(json.dumps(records, indent=2) + "\n")
(root / "input-empty.json").write_text("[]\n")
