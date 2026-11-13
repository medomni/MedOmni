#!/bin/sh
# The local CI script (s4 part 7): the data check and the release check on the checkout's committed tree, as the
# GitHub workflow will run them. On the private line it adds the private patterns. Exit 0 when both pass.
set -eu
top=$(git rev-parse --show-toplevel)
cd "$top"
py=${MEDOMNI_PYTHON:-"$top/.venv/bin/python"}
[ -x "$py" ] || py=python3
"$py" release/datacheck.py tree HEAD --release --private-config internal_docs/release/export.yaml
"$py" -c 'import sys; from medomni.core.cli import main; sys.exit(main(["studio", "release-check", "--no-images"]))'
