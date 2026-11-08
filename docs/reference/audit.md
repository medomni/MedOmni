# Audit

The audit matrix and the options of `medomni studio audit`. [Audit](../learn/studio/audit.md) explains the criteria, auditors and rules.

## The matrix

Each cell is one asset type × one criterion, checked by one or more auditors.

| Asset | Completeness | Conformance | Isolation | Clinical validity |
|---|---|---|---|---|
| Data | M | M | M | L, H |
| Families | M | M | M, L | L, H |
| Encoders | M | M | M, L | L, H |
| Tasks | M | M | M, L | L, H |
| Runs | M | M | M, L | L, H |

**M** is a machine check, **L** an LLM review (advisory) and **H** a human sign-off.

## Check

```bash
medomni studio audit
```

`--only data,families,encoders,tasks,runs` limits it to some assets.

## Where next

- [Tasks](tasks.md): the config hash verdicts bind to.
- [Encoders](encoders.md): the model card claims the audit checks.
