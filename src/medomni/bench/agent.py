"""`medomni bench agent new`: an agent config to fill in."""
from __future__ import annotations

import re
import sys

AGENT = """\
# An agent config (Run your agent guide). Keys are named as ${{VARNAME}}: export them in your shell.
# `settings` belong to the runner: for the agent runner (Harbor), its agent block.
kind: agent
name: {name}
model: <provider>/<model>
route: cloud
settings:
  scaffold: terminus-2
  model_served: <what the provider reports back>
  env: {{OPENAI_API_KEY: '${{OPENAI_API_KEY}}'}}
"""


def new_agent(name: str, stream=None) -> int:
    from medomni.core import plugins

    stream = stream or sys.stdout
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
        print(f"'{name}' is not an agent name (lower case, digits, hyphens)", file=stream)
        return 1
    path = plugins.find_repo() / "bench/agents" / f"{name}.yaml"
    if path.exists():
        print(f"{path} already exists", file=stream)
        return 1
    path.write_text(AGENT.format(name=name), encoding="utf-8")
    print(f"wrote {path}", file=stream)
    return 0
