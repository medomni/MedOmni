# AGENTS.md

Guidance for coding agents working in this repository. Read these before changing anything:

- [Concepts](docs/learn/concepts.md): one meaning per term. Use these names in code, docs and messages.
- [Constitution](docs/learn/constitution.md): the rules that always hold. When a change conflicts with one, the rule wins; amend the constitution first, then change the code.
- [Architecture](docs/learn/architecture.md): the parts, who may change them, and the four extension points.
- [Contracts](docs/learn/contracts/index.md): the versioned interfaces between parts. A contract change and its doc change land in the same pull request.

Never commit patient data, labels or per-record outputs from credentialed datasets.
