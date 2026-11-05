# Families

The fields of a family file and of `aliases.yaml`. [Families](../learn/core/families.md) explains how the registry is used.

Contract: family registry, one file per family in `core/families/<id>.yaml`, plus `core/families/aliases.yaml`.

## Family file

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | Family id; equals the file name. |
| `read_by` | yes | What reads it: `deep-encoder`, `rule-extractor` or `direct`. |
| `protocol.format` | yes | Accepted file formats: `edf`, `wfdb`, `dicom`, `image`, `omh`, `table`, `json-manifest`. |
| `protocol.channels` / `protocol.roles` | for EDF and WFDB | The exact montage or a channel count, or a role vocabulary that at least one channel must match. |
| `protocol.rate_hz` | no | Sampling rate; null means unchecked. |
| `protocol.units` | no | Dominant unit; null means unchecked. |
| `protocol.ndim` | yes | Dimensionality of the data. |
| `status` | yes | `declared` (shape known), `supplied` (measured on real data) or `deprecated`. |
| `samples` | no | Where the family's checked sample files live. |

## Aliases

`aliases.yaml` lists, per family:

- channel and role relabels
- extra sampling rates
- label prefixes
- DICOM colour modes

Reusable alias blocks are declared once under `vocab` and referenced by name.

## Rules

- A sample file opens in a declared format, carries every declared channel, matches `rate_hz` within 2% (or an alias rate) and matches `units`.
- Sample content is real: no flat channels, constant images or empty tables.

## Check

```bash
medomni contracts check families
```

It checks every family file, its samples and the aliases.

## Where next

- [Encoders](encoders.md): which encoders read each family.
- [Tasks](tasks.md): how a template names its inputs by family.
