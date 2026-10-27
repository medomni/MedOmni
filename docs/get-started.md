# Get started

This page takes you from install to a scored run, first on dummy data, then on VitalDB, then on a dataset you are licensed to use.

!!! note "Draft"
    The `medomni` command arrives in v1.0.0 (roadmap phase 3). Command names are fixed; flags may still change.

## Before you start

- Python 3.10 or later, and Docker (the task environments and encoders run in containers).
- An agent: a model plus the scaffold that drives it. A local open model is the default; see [Run your agent](guides/run-your-agent.md) for cloud routes.

## 1. Install

```bash
pip install medomni
```

```bash
medomni --version
```

## 2. Run on dummy data

Dummy data is generated from each family's protocol alone, so it needs no credentials and contains no patient values.

```bash
medomni run --agent templates/agent/local.yaml --batch smoke-dummy
```

```bash
medomni score --batch smoke-dummy
```

The scores show the pipeline works end to end. They mean nothing clinically.

## 3. Run on VitalDB

VitalDB is openly licensed (CC BY 4.0, PhysioNet copy), so its tasks run on real data with no credentialing.

```bash
medomni run --agent templates/agent/local.yaml --batch vitaldb
```

## 4. Run on your own licensed data

For MIMIC-IV, AI-READI or BDSP, obtain access from the data owner, point MedOmni at your local copy, and build the tasks yourself. Every task is rebuilt from its spec and checked against the published fingerprint, so you get exactly the task everyone else ran.

See [Connect your data](guides/connect-your-data.md).

## Check

`medomni score` prints one row per task with the score, the number of atom tasks and the error rate. A run that finished but produced no score row did not complete; its run folder holds the trace.

## Where next

- [Run your agent](guides/run-your-agent.md): configure your own agent and route.
- [Benchmarks](catalog/benchmarks.md): the pinned task batches.
- [Concepts](learn/concepts.md): what a task, an atom task and a batch are.
