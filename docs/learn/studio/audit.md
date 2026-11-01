# Audit

The audit checks MedOmni's claims against its files, code and runs. Each part makes claims:

- a family claims what its files contain
- a model card claims what an encoder does
- a task claims its answer is not in its evidence
- a run claims it used the task and model it names

## Assets and criteria

The audit covers five assets: data, families, encoders, tasks and runs. Each is checked on four criteria:

- **Completeness**: every required part is present.
- **Conformance**: it matches its contract.
- **Isolation**: no answer reaches the evidence, and no encoder has seen the evaluation data.
- **Clinical validity**: the target means what it says.

The [Audit reference](../../reference/audit.md) shows which auditor covers each asset and criterion.

## Auditors

- **Machine checks** run on every audit and can only reject.
- **LLM reviews** are advisory.
- **Human sign-offs** are required for clinical validity.

## Rules

- **Machine checks only reject.** Passing all of them means no contradiction was found.
- **A verdict binds to a fingerprint.** After the asset changes, its LLM or human verdict reverts to unassessed.
- **Only threats to the main claim fail.** An item fails if the answer is reachable in the evidence, an encoder has seen the evaluation data, or a target does not mean what it says. Other failed checks are warnings with their reason.
- **Patient-level traces never go to an LLM.** Checks that need them are left for a human and reported as unassessed.

## Run it

```bash
medomni audit
```

It runs the machine checks, reads the recorded verdicts and writes a report and a findings list to the workspace.

## Where it lives

`core/audit/`: one check module per asset, the matrix and the report writer.

## Where next

- [Audit reference](../../reference/audit.md): the matrix and the command's options.
- [Tasks](../bench/tasks.md): the fingerprints verdicts bind to.
