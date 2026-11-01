# Contracts

A contract is a fixed format plus the validator that checks it. Every file or message that passes between projects, between MedOmni and a plug-in package, or between MedOmni and you, has one. Each side can change its code without breaking the other.

## The contracts

| Contract | Describes | Written by | Read by |
|---|---|---|---|
| Family registry | Each input format, and the aliases it accepts | MedOmni team | Bench, Perception |
| Dataset policy | What a dataset's license allows | Contributors | Bench |
| Dataset adapter | The methods a dataset adapter provides | Contributors | Bench |
| Task spec | One task | Contributors | Bench |
| Task suite | Task ids pinned to fingerprints | MedOmni team | Bench, you |
| Fingerprint | The hash of a built task's content | Bench | Bench, the audit |
| Agent config | One agent: scaffold, model, route | You, contributors | Bench |
| Model card | One encoder | Contributors | Perception, agents |
| Container API | Requests between the gateway and an encoder image | MedOmni team | Perception |
| Gateway API | Requests to the gateway and the evidence it returns | MedOmni team | Bench, agents, your code |
| Result record | One run, or one score for one target | Bench | You, the audit |
| Workspace config | Where your data copies, caches, built tasks and results are kept | You | Bench, Perception |

The fields of each are on its Reference page.

!!! warning "Designed later in Stage 1"
    The dataset adapter contract is designed with the task pipeline, from probes of the datasets. Its methods are not fixed yet.

## How a file is checked

- Each contract is a Python class in `medomni.core.contracts` that lists its fields and their types.
- A file is checked when it is read. If a field is missing or wrong, reading stops and names the field and the reason.
- After that, code works with the checked object, never with the raw YAML or JSON. The object cannot be changed, so no step can alter a spec halfway through a build.

## Versions

Contracts follow the MedOmni release, such as v0.3.0. They have no version numbers of their own.

- A contract changes only in a minor release (v0.3 to v0.4), never in a patch release.
- Every change is listed in the changelog, with what to do about it.
- Files from the previous minor release still load, with a warning.
- Files that MedOmni writes, such as built tasks and result records, record the release that wrote them.
- A plug-in package states the releases it works with in its dependencies, such as `medomni>=0.3,<0.4`.

Two things outlive a release, so each carries its own marker:

- **Fingerprints** start with the algorithm that made them, such as `fp1:`, so published fingerprints stay checkable after an upgrade.
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
- `core/families/`: the family files, which follow the family registry contract

## Where next

- [Families](families.md): the contract both projects share.
- [Extend MedOmni](../extend.md): what you can add, and the contract each piece follows.
