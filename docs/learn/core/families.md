# Families

A family is a declared input format, such as `ecg-12lead-500hz-mv`: a 12-lead ECG at 500 Hz in millivolts. Datasets supply files in a family; encoders read one family. The family is where Bench and Perception meet.

```text
dataset ──event table──▶ FILE//F rows ──▶ encoders that read F
   └─ other format ──family converter──▶ files in F
```

## What a family declares

- **Format**: the file formats it accepts, such as EDF, WFDB, DICOM or a table.
- **Channels or roles**: the exact montage, a channel count, or roles at least one channel must match.
- **Rate and units**: the sampling rate and dominant unit, where they matter.
- **Type and range**: the data type of the values and their plausible range, such as 50–100 for SpO2 in %. A file outside the range is rejected, which catches unit and scaling errors that would otherwise pass silently.
- **Read by**: `deep-encoder`, `rule-extractor`, or `direct` (the agent reads the file itself).
- **Status**: `declared` (shape known), `supplied` (measured on real data) or `deprecated`.

The id names these facts: modality, shape, rate and unit.

## Aliases

Real files rarely match a protocol exactly. `aliases.yaml` lists what each family also accepts, such as channel relabels and extra sampling rates. Aliases are strict: an unknown key, family or target fails the check.

## How the registry is used

- A dataset's event table names each raw file as a `FILE//<family>` row.
- Build checks staged files against their family.
- The dummy-data generator, `medomni.core.families.dummy`, makes files from each family's protocol. [Datasets](../bench/datasets.md#open-credentialed-and-dummy-data) says how a dataset's dummy data is made.
- An encoder's model card names its one family; the gateway filters encoders by family.
- The runtime in every encoder image uses this module for aliases, labels and format checks.
- Every family count in MedOmni comes from the registry.

A new family is added by the MedOmni team. Family files are content; only their schema is a contract.

## Family converters

Some datasets store recordings in a format no family accepts, such as BDSP's HDF5 files or VitalDB's `.vital` files. A family converter turns one raw format into exactly one family; a family can have several converters.

- Each recording is converted once and kept in the [cache](cache.md), under a key that covers the source file, the family, the converter's version, and the parts of the family's declaration and aliases the conversion reads: channels, roles and channel prefixes. A change to any of them converts again. A change to a family's rate, units, type or range does not.
- Converters are shared code in Core, so any dataset with the same raw format uses the same one.
- The `.vital` converter reads with the `vitaldb` package and resamples VitalDB's 500 Hz arterial and ECG tracks to their families' rates.
- A converter is deterministic: the same input gives the same bytes. It writes no wall-clock time into a file header, so one cache key never has two content hashes.

## Where it lives

- `core/families/`: one `<id>.yaml` per family, plus `aliases.yaml`
- `src/medomni/core/contracts/schemas/`: the schema both follow
- `src/medomni/core/families/`: the registry loader, the family converters and the dummy-data generator

## Where next

- [Families reference](../../reference/families.md): every field of a family file.
- [Encoders](../perception/encoders.md): what reads a family.
