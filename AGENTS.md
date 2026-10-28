# AGENTS.md

Guidance for coding agents working in this repository. Read these before changing anything:

- [Design principles](docs/learn/principles.md): data governance, task reproducibility and how the docs are written.
- [Concepts](docs/learn/concepts.md): one meaning per term. Use these names in code, docs and messages.
- [Architecture](docs/learn/architecture.md): the parts and where each lives.
- [Reference](docs/reference/tasks.md): the formats each part reads and writes. A format change and its doc change land in the same pull request.

Never commit patient data, labels or per-record outputs from credentialed datasets.
