# API reference

The Python API of the `medomni` package, one section per subpackage, generated from the docstrings.

!!! note "Draft"
    The `medomni` package arrives in v1.0.0 (roadmap phase 1). This page is generated with mkdocstrings once it exists.

## medomni.contracts

Schemas and validators: family registry, task layout, Service API, card, dataset policy, ledger row, fingerprint.

## medomni.datasets

Dataset adapters and policies, one module per dataset, and the dummy-data generator.

## medomni.tasks

Task specs, the task builder, batches, and verification against published fingerprints.

## medomni.harness

The Harbor environment, agent routes, the scorer and metrics.

## medomni.assurance

The audit engine.

## medomni.perception

The perception client: pulls encoder images and starts the gateway.

## Where next

- [CLI](../cli/index.md): the same functions as commands.
- [Contracts](../learn/contracts/index.md): what each schema means.
