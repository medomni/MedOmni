# Families

Inputs that can share an encoder are one family, defined by a declared format. Datasets supply families and encoders read them, so a family is where the two meet.

One file per family in `data_task/families/<id>.yaml`, plus `data_task/family_alias.yaml`.

## Family file

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | Family id; equals the file name. |
| `reader` | yes | How it is read: `deep-encoder`, `rule-extractor` or `direct`. |
| `protocol.format` | yes | Accepted file formats: `edf`, `wfdb`, `dicom`, `image`, `omh`, `table`, `json-manifest`. |
| `protocol.channels` / `protocol.roles` | for EDF and WFDB | The exact montage or a channel count, or a role vocabulary that at least one channel must match. |
| `protocol.rate_hz` | no | Sampling rate; null means unchecked. |
| `protocol.units` | no | Dominant unit; null means unchecked. |
| `protocol.ndim` | yes | Dimensionality of the data. |
| `status` | yes | `declared` (shape known), `supplied` (measured on real data) or `deprecated`. |
| `samples` | no | Where the family's checked sample files live. |

## Aliases

`family_alias.yaml` lists what each family accepts beyond its protocol: channel and role relabels, extra sampling rates, label prefixes and DICOM colour modes. Reusable alias blocks are declared once under `vocab` and referenced by name. Aliases are strict: an unknown key, family or target fails.

## Rules

- A sample file opens in a declared format, carries every declared channel, matches `rate_hz` within 2% (or an alias rate) and matches `units`.
- Sample content is real: no flat channels, constant images or empty tables.

## Check

```bash
python data_task/taskbuilder/family_audit.py audit
```

```bash
uv run --with pyyaml --with pydantic python data_task/materialize_family_aliases.py --check
```

The first checks the families and their samples; the second checks the aliases.

## Where next

- [Encoders](encoders.md): which encoders read each family.
- [Tasks](tasks.md): how a spec names its inputs by family.
