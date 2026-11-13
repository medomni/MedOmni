# Dummy dataset packages

One loader-only package per dataset shape, for Core's tests: `dummy-mimic` (MIMIC-IV shape: `hosp/`, `icu/`, WFDB,
images), `dummy-omop` (AI-READI shape: OMOP tables and a folder tree of family files) and `dummy-bdsp` (BDSP shape: a
metadata table and h5 nights).

Each holds `dataset.yaml` and `codes.csv`, all the loader and the dummy generator read. Every name, item id and value
here is invented; ICD-10 codes are the public classification. The same packages with their labels, evidence rules and
tasks are Studio's test data (`medomni/studio/testing/datasets/`, R-147).
