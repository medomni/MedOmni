# Families

A family is a declared input format, such as `ecg-12lead-500hz-mv`: a 12-lead ECG at 500 Hz in millivolts. Datasets supply files in a family; encoders read one family. The family is where Bench and Perception meet.

```text
dataset ──adapter──▶ files in family F ──▶ encoders that read F
```

## What a family declares

- **Format**: the file formats it accepts, such as EDF, WFDB, DICOM or a table.
- **Channels or roles**: the exact montage, a channel count, or roles at least one channel must match.
- **Rate and units**: the sampling rate and dominant unit, where they matter.
- **Reader**: `deep-encoder`, `rule-extractor`, or `direct` (the agent reads the file itself).
- **Status**: `declared` (shape known), `supplied` (measured on real data) or `deprecated`.

The id names these facts: modality, shape, rate and unit.

## Aliases

Real files rarely match a protocol exactly. `aliases.yaml` lists what each family also accepts, such as channel relabels and extra sampling rates. Aliases are strict: an unknown key, family or target fails the check.

## How the registry is used

- A dataset adapter writes each input as files in a family.
- The task builder checks staged files against their family.
- The dummy-data generator reads each family's protocol.
- An encoder's model card names its one family; the gateway filters encoders by family.
- Every family count in MedOmni comes from the registry.

A new family is a contract change, made by the MedOmni team.

## Where it lives

`core/contracts/families/`: one `<id>.yaml` per family, plus `aliases.yaml`.

## Where next

- [Families reference](../../reference/families.md): every field of a family file.
- [Encoders](../perception/encoders.md): what reads a family.
