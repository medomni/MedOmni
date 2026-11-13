# Contracts

A contract is a fixed format plus the validator that checks it. Every file or message that passes between projects, between MedOmni and a plug-in package, or between MedOmni and you, has one. Each side can change its code without breaking the other.

## The contracts

| Contract | Describes | Written by | Read by |
|---|---|---|---|
| Family registry | The schema of a family file and of its aliases | MedOmni team | Studio, Bench, Perception |
| Dataset config | A dataset package: description, format readers, rules, named definitions (their form is the builder's), converters | Contributors | Studio |
| Event table | The table every dataset becomes, with its `FILE` rows | Core's loader | Studio |
| Dataset policy | What a dataset's license allows | Contributors | Studio, Bench |
| Built task | The content folder and atom tasks a builder writes. See [Built tasks](built-tasks.md) | A task builder | Bench |
| Benchmark card | One benchmark: name, version, owner, license, the intelligence kinds it accepts | MedOmni team, plug-in packages | Studio, Bench, you |
| Task set | `<template>@<cohort>` pairs pinned at version N, the arms to build them under, and the builder | MedOmni team, plug-in packages | Studio, Bench, you |
| Config hash | The hash of a task's config files under one arm | A task builder | Bench, you |
| Agent config | One intelligence of kind `agent`: name, model, route, and the settings its runner reads | You, contributors | Bench |
| Model card | One encoder | Contributors | Perception, agents |
| Container API | Requests between the gateway and an encoder image | MedOmni team | Perception |
| Gateway API | Requests to the gateway and the evidence it returns | MedOmni team | Bench, agents, your code |
| Prediction record | One answer for one target of one atom task: the only handoff from a run to the scorer | Bench's agent runner | Bench's scorer |
| Result record | One run, or one score for one target, naming its intelligence | Bench | You, Studio |
| Workspace config | Where your data copies, built tasks and results are kept, and which cache backend is used | You | Bench, Perception, Studio |

The fields of each are on its Reference page. Family files themselves are content, written by the MedOmni team; only their schema is a contract.

## Studio's formats

Studio defines its own formats. `medomni contracts check` checks them, and reading checks them, as for Core's contracts. They are not Core's: the recipe format belongs to MedOmni's builder, `medomni-v1`, and another [builder](built-tasks.md#write-your-own-builder) may read other files.

| Format | Describes | Written by | Read by |
|---|---|---|---|
| Recipe | A cohort with its task version and test patients, a label library and evidence rules | Contributors | `medomni-v1` |
| Task template | One task: targets, input, and an `agent` block (statement, instruction, environment, submission path) | Contributors | `medomni-v1` |
| Dataset config, as `medomni-v1` reads it | The dataset config, with its named definitions written as cohort requirements | Contributors | `medomni-v1` |
| Task proposal | One proposed task and its review state | Clinicians, reviewers | Studio |

## How a file is checked

- Each contract is a Python class in `medomni.core.contracts` that lists its fields and their types.
- A file is checked when it is read. If a field is missing or wrong, reading stops and names the field and the reason.
- After that, code works with the checked object, never with the raw YAML or JSON. The object cannot be changed, so no step can alter a template halfway through a build.

## Versions

Contracts follow the MedOmni release, such as v0.3.0. They have no version numbers of their own.

- A contract changes only in a minor release (v0.3 to v0.4), never in a patch release.
- Every change is listed in the changelog, with what to do about it.
- Files from the previous minor release still load, with a warning.
- Files that MedOmni writes, such as built tasks and result records, record the release that wrote them.
- A plug-in package states the releases it works with in its dependencies, such as `medomni>=0.3,<0.4`.

Three things outlive a release, so each carries its own marker:

- **Config hashes** start with the algorithm that made them, such as `cfg1:`, so published config hashes stay checkable after an upgrade.
- **Tasks** carry their own [version](../studio/tasks.md#version), `N.X`, so a task set stays comparable across releases.
- **Encoder images** record the release that built them. The gateway runs any image built since the Container API last changed, so a release that leaves the Container API alone needs no rebuild.

Only the MedOmni team changes contracts. To propose a change, such as a new family, open an issue.

## Check

```bash
medomni contracts check
```

It validates every contract file in the repository and in the installed plug-in packages. CI runs it on every pull request. Each check command ([Commands](../../cli/index.md)) also runs the validators for the pieces it checks.

## Where it lives

- `src/medomni/core/contracts/`: the classes and validators
- `src/medomni/core/contracts/schemas/`: one JSON Schema per contract, for tools outside Python
- `src/medomni/studio/build/contracts/` and `src/medomni/studio/schemas/`: Studio's formats and their JSON Schemas
- `core/families/`: the family files, which follow the family registry contract
- `studio/datasets/<dataset>/`: the dataset packages, which follow the dataset config and dataset policy contracts, and `medomni-v1`'s recipe format

## Where next

- [Families](families.md): the registry both projects share.
- [Extend MedOmni](../extend.md): what you can add, and the contract each piece follows.
