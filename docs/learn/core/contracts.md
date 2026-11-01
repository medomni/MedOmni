# Contracts

A contract is a versioned format plus the validator that checks it. Projects and plug-in packages depend only on contracts, so each side can change its code without breaking the other.

## The contracts

| Contract | Describes | Written by | Read by |
|---|---|---|---|
| Family registry | Each input format | MedOmni team | Bench, Perception |
| Task spec | One task | Contributors | Bench |
| Dataset policy | What a dataset's license allows | Contributors | Bench |
| Model card | One encoder | Contributors | Perception, agents |
| Gateway API | Requests to the gateway and the evidence it returns | MedOmni team | Bench, agents, your code |
| Results row | One run or one score in the results file | Bench | You, the audit |
| Fingerprint | The hash of a built task | Bench | Bench, the audit |

The fields of each are on its Reference page.

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

- `core/contracts/schemas/`: one JSON Schema per contract
- `core/contracts/families/`: the family registry

## Where next

- [Families](families.md): the contract both projects share.
- [Plug-ins](plugins.md): how outside packages use the same contracts.
