# MedOmni

<p align="center">
  <img src="docs/assets/logo.png" alt="MedOmni" width="280">
</p>

### Benchmarking Omni Modality* Integration in Medical Multimodal Agentic Systems

MedOmni is open-source software for medical AI on many data modalities: tables, waveforms, images and notes. This is v0.3.0.

MedOmni is developed in a private repository; this public repository is an export of each release, with every commit's author kept. Pull requests are reviewed and merged here and ship in the next release: see [Contributing](CONTRIBUTING.md).

| Project | Does | Command |
|---|---|---|
| **Bench** | Runs AI agents on built medical tasks and scores them. | `medomni bench` |
| **Perception** | Serves 44 medical encoders through an HTTP gateway. | `medomni perception` |
| **Studio** | Makes and builds tasks, and audits them. | `medomni studio` |
| **Core** | The contracts, the `medomni` command, plug-in loading, dataset loading, the cache and the testing kit, shared by every project. | `medomni` |

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

The documentation is at [medomni.ai](https://medomni.ai). Releases are tags on [github.com/medomni/MedOmni](https://github.com/medomni/MedOmni); v0.3.0 is a beta. There is no PyPI release, and encoder images are built on your machine.
