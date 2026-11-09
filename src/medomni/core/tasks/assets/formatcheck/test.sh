#!/bin/bash
# FORMAT CHECK ONLY — never a score (slipway §Atom verifier). Stamped from
# harness/formatcheck/ by build.py emit; expected.json sits beside this file.
# Copies the submission into /logs/verifier/ so post-run scoring can read it.
D="$(cd "$(dirname "$0")" && pwd)"
mkdir -p /logs/verifier
cp /workspace/submission/predictions.csv /logs/verifier/submission.csv 2>/dev/null || true
python3 "$D/format_check.py" /workspace/submission/predictions.csv "$D/expected.json" \
  > /logs/verifier/reward.json 2> /logs/verifier/format_check.err || echo '{"format_ok": 0}' > /logs/verifier/reward.json
python3 -c "import json; print(json.load(open('/logs/verifier/reward.json')).get('format_ok', 0))" > /logs/verifier/reward.txt
# choosing-behavior record (FIX-1): pull this atom's gateway usage into the trial dir; absent gateway = fine
# status is never ambiguous (fix roadmap D8): ok (from the sidecar) | unreachable | no-gateway (noenc arm)
python3 - <<'PY' || true
import json, os, urllib.request
out = "/logs/verifier/gateway_usage.json"
if not os.environ.get("PERCEPTION_URL"):
    open(out, "w").write(json.dumps({"status": "no-gateway", "calls": []}))
else:
    try:
        with urllib.request.urlopen(os.environ["PERCEPTION_URL"].rstrip("/") + "/usage", timeout=10) as r:
            open(out, "w").write(r.read().decode())
    except Exception as e:
        open(out, "w").write(json.dumps({"status": "unreachable", "calls": [], "error": str(e)[:200]}))
PY
