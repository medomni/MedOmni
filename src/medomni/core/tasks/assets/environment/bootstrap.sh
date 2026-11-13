#!/bin/bash
# Stage task data into the shared workspace volume, then exit 0.
# LOCAL-ONLY (Constitution Art. 2, generation bundle-1): data comes from the task folder's own
# data/, mounted read-only at /task_data by docker-compose — never from any remote.
# Gold under tests/ is never mounted, so it can never reach the workspace.
set -euo pipefail
cp /task_instruction.md /workspace/instruction.md
mkdir -p /workspace/submission /workspace/data
cp -rL /task_data/. /workspace/data/
echo "bootstrap: staged $(find /workspace/data -type f | wc -l) files"
# The perception sidecar's access witness starts only once this marker exists, so the copy above
# is never logged as agent reads (harness-runtime §1). Written last, in both arms.
touch /workspace/.staged
