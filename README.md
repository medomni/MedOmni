# MedOmni

MedOmni is a benchmark for agent-based medical diagnosis across all clinical
modalities. An agent solves diagnostic tasks by querying the Modality Perception
service, which runs off-the-shelf encoders and returns standardized Evidence.
Tasks and data, perception, and assurance are owned by three independent teams
connected through a thin contract layer.

## Ownership

| Path | Team | Contact |
|---|---|---|
| `data_task/` | Data & Task | Bosong Huang · @medomni/task-team |
| `perception/` | Modality Perception | @medomni/modality-perception-team |
| `assurance/` | Assurance | @medomni/qa-team |
| `contracts/` | shared seam — changes need all three teams | — |
