# AGENTS.md

Guidance for coding agents working in this repository. Read these before changing anything:

- [Design principles](docs/learn/principles.md): data governance, task reproducibility, structure and how the docs are written.
- [Concepts](docs/learn/concepts.md): one meaning per term. Use these names in code, docs and messages.
- [Architecture](docs/learn/architecture.md): the projects (Core, Bench, Perception), the repository layout and where each part lives.
- [Reference](docs/reference/tasks.md): the contracts each project reads and writes. A contract change and its doc change land in the same pull request.

Core developers in the private repository also read `internal_docs/developing.md`: one `main` branch, what the allowlist publishes, the export, imported pull requests and the push guard. That folder isn't in the public repository.

Never commit patient data, labels or per-record outputs from credentialed datasets.
