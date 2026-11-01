# Contracts

A contract is a versioned format plus the validator that checks it. Every file or message that passes between projects, or between MedOmni and a plug-in package, has one. Each side can change its code without breaking the other.

## The contracts

| Contract | Describes | Written by | Read by |
|---|---|---|---|
| Family registry | Each input format, and the aliases it accepts | MedOmni team | Bench, Perception |
| Dataset policy | What a dataset's license allows | Contributors | Bench |
| Dataset adapter | The methods a dataset adapter provides | Contributors | Bench |
| Task spec | One task | Contributors | Bench |
| Batch | Task ids pinned to fingerprints | MedOmni team | Bench, you |
| Fingerprint | The hash of a built task's content | Bench | Bench, the audit |
| Agent config | One agent: scaffold, model, route | You, contributors | Bench |
| Encoder set | The encoders and images a batch needs | Bench | Perception |
| Model card | One encoder | Contributors | Perception, agents |
| Container API | Requests between the gateway and an encoder image | MedOmni team | Perception |
| Gateway API | Requests to the gateway and the evidence it returns | MedOmni team | Bench, agents, your code |
| Results row | One run, or one score for one target | Bench | You, the audit |
| Workspace layout | Where configuration, caches, built tasks and results are kept | MedOmni team | Every project |

The fields of each are on its Reference page.

!!! warning "Designed later in Stage 1"
    The dataset adapter contract is designed with the task pipeline, from probes of the datasets. Its methods are not fixed yet.

## In code

- Each contract has a typed, frozen model in `medomni.core.contracts`.
- Files are loaded into their model once, at the edge. Code passes models, never raw dictionaries.
- A file that does not fit its model fails to load, with the field and the reason.

## Versions

- Every contract carries a version, such as task spec v1.
- A change that breaks existing files makes a new version.
- A deprecated version stays usable for at least two minor releases.
- A contract change and its docs change land in the same pull request.

Only the MedOmni team changes contracts. To propose one, such as a new family, open an issue.

## Check

```bash
medomni contracts check
```

It validates every contract file against its schema. Each check command ([Commands](../../cli/index.md)) runs the validators for the pieces it checks.

## Where it lives

- `src/medomni/core/contracts/`: the models and validators
- `src/medomni/core/contracts/schemas/`: one JSON Schema per contract
- `core/families/`: the family files, which follow the family registry contract

## Where next

- [Families](families.md): the contract both projects share.
- [Plug-ins](plugins.md): how outside packages use the same contracts.
