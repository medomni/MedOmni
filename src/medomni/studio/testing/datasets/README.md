# Dummy dataset packages

Studio's test packages, one per dataset shape: `dummy-mimic` (MIMIC-IV shape: `hosp/`, `icu/`, WFDB, images),
`dummy-omop` (AI-READI shape: OMOP tables and a folder tree of family files) and `dummy-bdsp` (BDSP shape: a metadata
table and h5 nights).

Each holds `dataset.yaml`, `codes.csv` and `labels.yaml`, in the v1 builder's format; `dummy-mimic` also has
`evidence.yaml` and one task. Core keeps the loader-only part of each (`medomni/core/testing/datasets/`, R-147). Every
name, item id and value here is invented; ICD-10 codes are the public classification. `medomni studio dummy <package>
--out <dir>` writes a raw folder from one.
