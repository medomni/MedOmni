# MedOmni

<p align="center">
  <img src="docs/assets/logo.png" alt="MedOmni" width="280">
</p>

<p align="center">
  <a href="https://medomni.ai"><img src="https://img.shields.io/badge/docs-medomni.ai-blue" alt="Documentation: medomni.ai"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/licence-Apache--2.0-green" alt="Licence: Apache-2.0"></a>
</p>

### The open-source ecosystem for omni-modality medical intelligence

MedOmni is open infrastructure for medical AI on any data modality: tables, waveforms, images, volumes and notes.

## Goal

A clinician reads lab tables, ECGs, sleep recordings, X-rays, retinal scans and notes side by side. MedOmni aims to be the shared, open infrastructure where agents and models learn to do the same: take in any medical data modality, be tested on it, and improve. A dataset or encoder added to MedOmni once can be used by every agent and model tested on it.

## Overview

MedOmni is one shared Core with three projects built on it. Bench and Perception depend only on Core, and the projects exchange data only through Core's contracts, so each can be used and changed on its own.

| Project | What you get | Command |
|---|---|---|
| **Bench** | Test your agent, or a foundation model behind one, on built medical tasks, and score it. | `medomni bench` |
| **Perception** | Give your agent perception across medical modalities: 44 encoders behind one HTTP gateway, each reading one kind of input, such as a 12-lead ECG. | `medomni perception` |
| **Studio** | The rest of the workflow: survey a dataset, preview and select cohorts, build tasks, and audit them. | `medomni studio` |
| **Core** | What every project shares: the contracts, the `medomni` command, plug-in loading, dataset loading, the cache and the testing kit. | `medomni` |

Anyone can add a dataset, an encoder, a task or an agent without changing Core: by pull request, or as a plug-in package in their own repository. Each piece has a `new` command to start from and a check command to run. See [Contributing](CONTRIBUTING.md).

No patient data ships with MedOmni. Tasks are built on your machine from generated dummy data, open datasets such as VitalDB, or datasets you are licensed to use, such as MIMIC-IV.

## Install

Python 3.11 or later, Docker and [uv](https://docs.astral.sh/uv/).

```bash
git clone --branch v0.3.0 https://github.com/medomni/MedOmni medomni && cd medomni
uv venv && source .venv/bin/activate && uv pip install -e .
medomni --version
```

Then follow [Get started](docs/get-started.md) to build, run and score a first task set on dummy data.

## Repository

```text
src/medomni/     the package: core/, bench/, perception/, studio/
core/families/   one file per input family, and aliases.yaml
bench/           benchmarks/ (benchmark cards and task sets), agents/
perception/      encoders/<family>/<encoder>/, deployed.yaml (the images the perception service starts)
studio/          datasets/<dataset>/ (dataset packages, templates, cohorts)
tests/           one folder per project
docs/            the documentation
```

## Documentation

- [Get started](docs/get-started.md): install and score a first run on dummy data.
- [Run your agent](docs/guides/run-your-agent.md), [Use the encoders](docs/guides/use-the-encoders.md), [Contribute](docs/guides/contribute.md).
- [Architecture](docs/learn/architecture.md): how the projects fit together.

## Licence

MedOmni's code is under the Apache License 2.0; see [LICENSE](LICENSE). Each encoder, dataset package and task set states its own licence on its card or policy.

## Releases

This is v0.3.0, the first public release, a beta. The documentation is at [medomni.ai](https://medomni.ai). Releases are tags on [github.com/medomni/MedOmni](https://github.com/medomni/MedOmni). There is no PyPI release, and encoder images are built on your machine.
