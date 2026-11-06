# Dummy dataset packages

One dataset package per dataset shape, for tests: `dummy-mimic` (MIMIC-IV shape: `hosp/`, `icu/`, WFDB, images),
`dummy-omop` (AI-READI shape: OMOP tables and a folder tree of family files) and `dummy-bdsp` (BDSP shape: a
metadata table and h5 nights).

Each holds `dataset.yaml`, `codes.csv` and `labels.yaml`. Every name, item id and value here is invented; ICD-10
codes are the public classification. `medomni studio dummy <package> --out <dir>` writes a raw folder from one.
