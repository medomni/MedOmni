"""Bench's content kinds (R-145): agent configs, and benchmarks with their task sets."""
from pydantic import model_validator

from medomni.core.contracts import AgentConfig, BenchmarkCard, TaskSet
from medomni.core.plugins import Files, Kind


class AgentFile(AgentConfig):
    """An agent config as a file in `bench/agents/`: its `settings` are checked by its runner's own model."""

    @model_validator(mode="after")
    def _runner_settings(self):
        from medomni.core import plugins
        from medomni.core.contracts import load_data

        piece = plugins.resolve(plugins.RUNNERS).pieces.get(self.runner or self.kind)
        model = getattr(piece.load(), "settings", None) if piece is not None else None
        if model is not None:
            load_data({**self.settings, "route": self.route}, model, "settings")
        return self

CONTENT = (
    Kind("agents", "bench/agents/*.yaml", 0),
    Kind("benchmarks", "bench/benchmarks/*/benchmark.yaml", 1),  # a card and its task sets in sets/ (R-83)
    Files("agent config", "agents", "bench/agents/*.yaml", AgentFile),
    Files("benchmark", "benchmarks", "bench/benchmarks/*/benchmark.yaml", BenchmarkCard),
    Files("task set", "sets", "bench/benchmarks/*/sets/*.yaml", TaskSet),
)
