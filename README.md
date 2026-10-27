# MedOmni

<p align="center">
  <img src="docs/assets/logo.png" alt="MedOmni bench" width="280">
</p>

### Benchmarking Omni Modality* Integration in Medical Multimodal Agentic Systems


## Ownership


| Path          | Team                | Contact                    |
| ------------- | ------------------- | -------------------------- |
| `data_task/`  | Data & Task         | Bosong Huang · @BosonHwang |
| `perception/` | Modality Perception | Timo Stoffregen · @TimoStoff  |
| `assurance/`  | Assurance           | Xiaoda Wang · @ignite-abd  |


## Interfaces (what teams hand each other)


| Artifact                                                 | From → To                       | Where                                                     |
| -------------------------------------------------------- | ------------------------------- | --------------------------------------------------------- |
| Family declarations + samples                            | Data & Task → Perception        | `data_task/families/*.yaml` · HF `MedOmni/family-samples` |
| Benchmark tasks (template + patients + labels)           | Data & Task → agents, Assurance | `data_task/tasks/<task-id>/` · HF `MedOmni/tasks`         |
| Perception API (`list_encoders` / `get_card` / `encode`) | Perception → agents             | `perception/spec/service-api.md` · served by `perception/gateway/` |
| Encoder cards                                            | Perception → agents, Assurance  | `perception/encoders/<family>/<encoder>/card.yaml` · `perception/encoders.yaml` |
| Audit verdicts + sign-offs                               | Assurance → everyone            | `assurance/records/`                                      |


## DATA resources

Private datasets under the `MedOmni` org — ask Bosong for access.


| Repo                                                                               | Contents                                                                |
| ---------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| [MedOmni/family-samples](https://huggingface.co/datasets/MedOmni/family-samples) | `families.yaml` (37 input families) + representative samples per family |
| [MedOmni/tasks](https://huggingface.co/datasets/MedOmni/tasks)                   | `tasks.yaml` index + per-task definition, patients, labels              |
| [MedOmni/encoder-assets](https://huggingface.co/datasets/MedOmni/encoder-assets) | `encoders.yaml` ledger + encoder weights + source snapshots (reference) |


