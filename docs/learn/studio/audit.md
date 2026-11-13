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

- **Machine checks** run on every audit and can only reject. For tasks, they read the results of Build's [correctness checks](build.md#correctness-checks), which refuse a bad task at every build. They add seven of their own: a test case for every leakage rule, the canary, the call budget, encoder limits, family coverage, the file inventory and the instruction.
- **LLM reviews** are advisory.
- **Human sign-offs** are required for clinical validity.

## Rules

- **Machine checks only reject.** Passing all of them means no contradiction was found.
- **A verdict binds to the asset's config hash** (for a task: its template, cohort, labels, recipes and dataset release). After any of these changes, its LLM or human verdict reverts to unassessed.
- **Only threats to the main claim fail.** An item fails if the answer is reachable in the evidence, an encoder has seen the evaluation data, or a target does not mean what it says. Other failed checks are warnings with their reason.
- **Patient-level traces never go to an LLM.** Checks that need them are left for a human and reported as unassessed.

## Run it

```bash
medomni studio audit
```

It runs the machine checks, reads the recorded verdicts and writes a report and a findings list to the workspace.

## Release check

```bash
medomni studio release-check
```

It checks that the release tree may be published, before every release. It reads four things and fails on any conflict:

- **Encoder licences:** every model card states a licence, and every built image carries the same one in its `org.medomni.license` label, which `medomni perception check` sets. An encoder under a restricted licence ships like the rest, with the licence stated on both. `--no-images` skips the labels, so the check runs without Docker.
- **Dataset publish rules:** every file under a dataset package is a kind its policy's `publish` rules name and allow: schema files, templates or recipes. Any other file is refused.
- **Data files:** every signal, image or array file sits in a folder, or the folder above it, with a `PROVENANCE` file that states a licence. Site images under `docs/` aren't data.
- **Task set versions:** the version check of `medomni studio task check --release`.

The release tree is the repository's tracked files, less the folders that stay private.

## Where it lives

- `src/medomni/studio/review/`: the matrix, the runner and the report writer
- each project's audit checks, registered through Core's plug-in loading: data and tasks from Studio, runs from Bench, encoders from Perception

## Where next

- [Audit reference](../../reference/audit.md): the matrix and the command's options.
- [Tasks](tasks.md): the config hash verdicts bind to.
- [Studio](overview.md): the other review tools.
