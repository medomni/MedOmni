"""Bench's content kinds (R-145): agent configs, and benchmarks with their task sets."""
from medomni.core.contracts import AgentConfig, BenchmarkCard, TaskSet
from medomni.core.plugins import Files, Kind

CONTENT = (
    Kind("agents", "bench/agents/*.yaml", 0),
    Kind("benchmarks", "bench/benchmarks/*/benchmark.yaml", 1),  # a card and its task sets in sets/ (R-83)
    Files("agent config", "agents", "bench/agents/*.yaml", AgentConfig),
    Files("benchmark", "benchmarks", "bench/benchmarks/*/benchmark.yaml", BenchmarkCard),
    Files("task set", "sets", "bench/benchmarks/*/sets/*.yaml", TaskSet),
)
