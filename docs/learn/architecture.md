# Architecture

MedOmni is shown here in three C4 views, from the outside in: who uses it, which containers it has, and which components make up the package.

!!! note "Draft"
    These views show v1.0.0. The figures are the single source; the lines under each figure name its elements.

## Context (C1)

![C1: three stakeholders, one entrance](../assets/c1-context.drawio.svg)

- **Model tester and practitioner** (primary): brings an agent, runs it with the `medomni` command, reads the scores.
- **Perception service user**: calls the encoders over HTTP.
- **Task adder**: adds tasks on open data, dataset adapters and encoders by pull request, checked by `medomni` check commands.
- **MedOmni**: one package, `pip install medomni`. Runs agents on medical tasks, scores them, serves perception encoders.
- **medomni.ai**: these docs, one path per stakeholder.
- **PyPI**: versioned `medomni` releases.
- **Datasets**: dummy data and VitalDB built in; MIMIC-IV, AI-READI and BDSP from the user's own access, read from local disk.
- **Model behind the agent**: local open model by default; cloud routes opt-in, checked against each dataset's policy.
- **Container registry** (ghcr.io): encoder images, built by the encoder repository.
- **Hugging Face Hub**: public task samples and encoder model cards.

## Containers (C2)

![C2: two repositories, one package, one contract layer](../assets/c2-containers.drawio.svg)

Main repository `MedOmni`, installed as `medomni`:

- **medomni CLI**: the one entrance: `run`, `score`, `task new`, `task check`, `encoder check`.
- **datasets**: one adapter and one policy per dataset, plus the dummy-data generator.
- **tasks**: task specs, the task builder, and verification against published fingerprints.
- **harness**: the Harbor environment, agent routes, the scorer and metrics.
- **assurance**: the audit engine. Audit records stay private to the MedOmni team.
- **contracts**: schemas and validators, versioned: the family registry, task layout, Service API, card, dataset policy, ledger row and fingerprint. Every other part depends on contracts and on nothing else; no part reads another part's files by path.
- **perception client**: pulls encoder images and starts the gateway.
- **docs/**: these pages, built to medomni.ai.
- **templates/ and CI**: templates for each extension point; GitHub Actions checks every pull request.

Encoder repository:

- **Gateway**: the HTTP service with `list_encoders`, `get_card` and `encode`.
- **Encoders**: one container per encoder, each reading one family. The repository pins a `medomni` version for the contracts, publishes images to ghcr.io and cards to Hugging Face.

## Components (C3)

![C3: a locked core and four extension points](../assets/c3-components.drawio.svg)

Core, changed only by the MedOmni team:

- **Contracts**: the schemas and validators listed above.
- **Task pipeline**: intake, freeze, emit, validate, verify.
- **Runner and scorer**: the Harbor environment, the route check against dataset policies, and the scorer, which is the only thing that writes scores.
- **Audit engine**: the audit matrix over fingerprints and ledger rows.
- **Gateway and perception client**: serve whichever encoders are registered.
- **medomni CLI**: the commands above.

Extension points, open to contributors. Each has a template and one check command, and CI runs the same check on every pull request:

| Extension point | What you bring | Template | Check |
|---|---|---|---|
| Agent | Your agent config, naming a route rather than a vendor | `templates/agent/` | `medomni run` on dummy tasks |
| Dataset adapter | An adapter and policy for an openly licensed dataset, with a data sample on Hugging Face | `templates/dataset/` | `medomni task check` |
| Task | A task spec on a supported dataset and family | `medomni task new` | `medomni task check` |
| Encoder | An encoder adapter, Dockerfile, card and test data for one family, in the encoder repository | `templates/encoder/` | `medomni encoder check` |

## Where next

- [Contracts](contracts/index.md): the interfaces between the parts.
- [Contribute](../guides/contribute.md): how the extension points work in practice.
- [Concepts](concepts.md): the terms used above.
