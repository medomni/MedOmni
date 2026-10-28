# Audit

Every part of MedOmni makes claims: a family claims what its files contain, a model card claims what an encoder does, a task claims its answer is not in its evidence. The audit checks each claim against the actual files, code and runs.

Defined in: `assurance/audit_matrix_v2/` (the matrix and its checks are listed in `audit-matrix.md`)

## The matrix

Each cell is one asset type × one criterion, checked by one or more auditors.

| Asset | Completeness | Conformance | Isolation | Clinical validity |
|---|---|---|---|---|
| Data | M | M | M | L, H |
| Families | M | M | M, L | L, H |
| Perception service | M | M | M, L | L, H |
| Tasks | M | M | M, L | L, H |
| Runs | M | M | M, L | L, H |

**M** is a machine check, **L** an LLM review (advisory) and **H** a human sign-off.

## Rules

- **Machines reject, never approve.** All machine checks passing means no contradiction was found, not that the asset is sound; clinical validity always needs a human.
- **A verdict binds to a fingerprint.** An LLM or human verdict counts only while the asset's fingerprint is unchanged; after a change it reverts to unassessed.
- **Only threats to the main claim fail.** An item fails if the answer is reachable in the evidence, an encoder has seen the evaluation data, or a target does not mean what it says. Every other failed check is shown as a warning with its reason.
- **Patient-level traces never go to an LLM.** Checks that need them are left for a human and reported as unassessed, so coverage never hides a gap.

In v0.2.0 no human sign-off has been recorded, so every human cell is reported as unassessed.

## Check

```bash
uv run --with huggingface_hub,pyedflib,pydicom,wfdb,pandas,pyarrow,pillow,h5py,pyyaml,jsonschema python assurance/audit_matrix_v2/run_all.py
```

It runs the machine checks, reads the LLM and human verdicts from `assurance/audit_matrix_v2/ledgers/reviews/`, and writes `REPORT.md` and `FINDINGS.md` to `assurance/audit_matrix_v2/ledgers/`. `--only data,family,service,tasks,runs` limits it to some assets.

## Where next

- [Tasks](tasks.md): the fingerprints verdicts bind to.
- [Encoders](encoders.md): the model card claims the audit checks.
