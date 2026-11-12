# Datasets

Every dataset v0.3.0 builds tasks from, with how to get access and what its policy allows, and the fields of a dataset package.

Contracts: dataset config, `dataset-config.schema.json`, and dataset policy, `dataset-policy.schema.json`, in `src/medomni/core/contracts/schemas/`. Each dataset has one package, in `studio/datasets/<dataset>/`, which MedOmni's builder, `medomni-v1`, reads with its own stricter `v1-dataset-config.schema.json`, in `src/medomni/studio/schemas/`.

!!! note "Not legal advice"
    Each policy summarises the data owner's license and data use agreement. You are responsible for following your agreement. Before a run, Bench checks the agent's route against the policy of each dataset in the task set, but it cannot check a route's conditions for you.

## Datasets in v0.3.0

| Dataset | Access | License | What may be published | Routes |
|---|---|---|---|---|
| **MIMIC-IV 3.1** (core, ED, CXR-JPG, Note 2.2) | Credentialed (PhysioNet) | PhysioNet Credentialed Health Data License 1.5.0 + DUA | Schema, templates, recipes, config hashes, aggregate results. Never labels or per-record outputs | `local`. `cloud` only with verified zero retention, no training and no human review |
| **MIMIC-IV-ECG 1.0, MIMIC-IV Waveform 0.1.0** | Open (PhysioNet) | ODbL 1.0 | Schema, templates, recipes, IDs, samples, with attribution and share-alike | `local`, `cloud` |
| **AI-READI** | Credentialed (FAIRhub) | AI-READI Data License Agreement v2.0; type 2 diabetes research only | Schema, templates, recipes, config hashes, a small representative sample in papers. Never labels, ID lists or derived data | `local`. `cloud` only with a HIPAA BAA between the vendor and your institution; never for model training |
| **BDSP Human Sleep Project** | Credentialed (bdsp.io) | BDSP Credentialed Health Data License 1.5.0 + DUA | Schema, templates, recipes (a selection rule plus a hash), config hashes. Never record-level derivatives | `local` only, unless BDSP approves otherwise in writing |
| **VitalDB** | Open (VitalDB's open API) | CC BY 4.0 | Everything, with attribution | `local`, `cloud` |
| **Dummy data** | Generated | None | Everything | `local`, `cloud` |

## Source populations

Each cohort selects from its dataset's source population: the patients for whom `sha256(salt|patient id)`, read as a fraction, is below the default fraction. A cohort may set a smaller fraction.

| Dataset | Unit | Default source population |
|---|---|---|
| MIMIC-IV | Patient | 5% of patients |
| AI-READI | Participant | All |
| BDSP | Patient at site I0006 | 10% of patients; download only their latest sleep study, listed by `medomni studio download-list bdsp` |
| VitalDB | Surgery case | All |

## Dataset package

| File | Required | Holds |
|---|---|---|
| `dataset.yaml` | yes | The dataset config, below. |
| `labels.yaml` | yes | The label library. See [Recipes](recipes.md#label-library). |
| `evidence.yaml` | yes | The evidence rules. See [Recipes](recipes.md#evidence-file). |
| `codes.csv` | yes | Every code the dataset emits: `code`, `description`, `source_table`. |
| `policy.yaml` | yes | The dataset policy, below. |
| `hooks/` | no | Python for what no reader option can express. See [Hooks](#hooks). |
| `converters/` | no | The dataset's own family converters, listed in `dataset.yaml`. |
| `tasks/` | no | Task templates and their cohorts. |

`dataset.yaml`:

| Field | Required | Meaning |
|---|---|---|
| `description` | yes | `unit` (what one subject is), `time` (the kind of time: date and time, visit dates only, seconds from start) and `version` (the dataset release). |
| `units` | yes | The table and column that list every subject. |
| `source` | yes | The source population: `salt` and the default `fraction`, or `all`. |
| `verify` | no | What to check before reading, beyond the files the readers list. See [Verify](#verify). |
| `read` | yes | A list of format readers, each with what it reads. See [Format readers](#format-readers). |
| `rules` | no | Visit and timing rules. See [Visit rules](#visit-rules). |
| `definitions` | no | Named definitions, such as a disease, that recipes use. Core leaves their form to the builder; `medomni-v1` reads them as cohort requirements. See [Recipes](recipes.md#cohort-file). |
| `converters` | no | The dataset's own [family converters](../learn/core/families.md#family-converters): files in the package, such as `converters/h5_to_edf.py`, each defining `CONVERTER`. Core loads them by path. |
| `storage_mb` | no | The disk space each atom task gets, in MB. 16,384 when absent; BDSP sets 65,536. |

## Format readers

Each entry in `read` names a reader and its `options`:

```yaml
read:
- reader: csv
  options:
    tables:
      admissions:
        file: hosp/admissions.csv
        subject: subject_id
        subject_type: int
        time: admittime
        visit: hadm_id
        events:
        - code: ADMISSION
        - {code: DISCHARGE, time: dischtime}
      labevents:
        file: hosp/labevents.csv
        subject: subject_id
        time: charttime
        events:
        - {code: "LAB//{itemid}", value: valuenum}
- reader: tree
  options:
    files:
      cxr-radiograph-2d: {pattern: "cxr/{subject}/{record}.png"}
      psg-night: {pattern: "psg/{subject}/{record}.h5", format: h5, families: [eeg-sleep-6ch-200hz-uv]}
```

`csv` reads tables, as CSV or Parquet. Per table:

| Field | Required | Meaning |
|---|---|---|
| `file` | yes | The file, relative to your copy. A glob, such as `waves/*.csv`, reads every match as one table. |
| `subject` | yes | The subject column. |
| `subject_type` | no | `str` (default) or `int`. |
| `time` | no | The time column. |
| `time_from` | no | For rows with no time of their own: `{table, key, column}`, the time of the other table's row with the same key. Not with `time`. |
| `visit` | no | The visit column. |
| `events` | yes | The codes each row emits. See the event fields below. |
| `where` | no | Keep only rows whose column holds one of the listed values: `{column: [values]}`. |
| `clean` | no | How a column's text is cleaned before codes are filled from it: `before` (keep the text before this, stripped), `remove` (drop these characters), `lower`. |
| `load` | no | `false`: the table is read for evidence but not loaded into the event table, for a table too large to load. Default `true`. |
| `missing_time` | no | `drop`: a row whose time is empty emits nothing. Default `keep`. |

A table with neither `time` nor `time_from` holds static facts.

Each event:

| Field | Required | Meaning |
|---|---|---|
| `code` | yes | The code. `{column}` is filled from that column, as in `LAB//{itemid}`. |
| `value` | no | A numeric column. |
| `text` | no | A text column. |
| `time` | no | A time column other than the table's. |
| `path` | for `FILE//` codes | The file or folder, relative to your copy; `{column}` is filled. |
| `present` | no | Emit only when these columns are filled. |
| `absent` | no | Emit only when these columns are empty. |
| `equals` | no | Emit only when the column holds one of these values: `{column: [values]}`. |

```yaml
events:
- {code: DEATH, time: deathtime, present: [deathtime]}
- {code: DEATH, time: dischtime, absent: [deathtime], equals: {hospital_expire_flag: ["1"]}}
```

`tree` finds files by folder pattern. Per entry:

| Field | Required | Meaning |
|---|---|---|
| `pattern` | yes | The path, relative to your copy, with `{subject}` and `{record}`. |
| `format` | no | `family` (default): the files are in the family the entry is named by. `h5`: one raw night per file, which a family converter turns into several families. |
| `families` | for `h5` | The families an `h5` file carries. |
| `per_subject` | no | Files per subject (default 1). |
| `exclude` | no | Skip a path that holds any of these strings. |
| `subject_from` | no | `{table, key}`: the path's `{subject}` is a value of the table's `key` column, mapped to that table's subject. A path whose key isn't in the table is skipped. |

Hidden files and empty files are skipped.

`hook` runs a [hook](#hooks): `{hook: <name>, params: {...}}`.

## Hooks

A hook is Python for what no reader option can express, at `studio/datasets/<dataset>/hooks/<name>.py`. A `hook` reader names it; hooks run after the other readers, in the order listed.

```yaml
read:
- reader: hook
  options: {hook: ckd, params: {creatinine: [LAB//50912, LAB//52546]}}
```

| Function | Required | Does |
|---|---|---|
| `derive(rows, raw_root, params)` | yes | Returns new event rows. `rows` are the rows read so far, which it must not change; it may also read raw files. |
| `inputs(raw_root, params)` | no | The raw files it reads, relative to your copy. They are checked before loading, and they join the cache key. |
| `dummy(raw_root, subjects, params, rng)` | no | Writes those raw files for a dummy copy. `subjects` maps each subject id to its start time. |
| `problems(raw_root, params)` | no | Problems in your copy, which `medomni studio data check` reports. |

Every code a hook emits is listed in `codes.csv` with `source_table` `hook:<name>`.

Two more hooks are found by their names, and no reader runs them:

- `views`, which the [evidence rules](recipes.md#evidence-file) name: it gives the forms the agent reads. When the package has `verify.unit_files`, it may also define `dummy_unit(path, rng)`, which writes one unit's file for dummy data.
- `download`, at `hooks/download.py`: it tells `medomni studio download-list` where the dataset's files come from. `index_files()` gives the index tables to fetch first, and `files(raw_root, params, rows)` the files of the source population's patients, chosen from those tables. Each entry is a source, the path in your copy, and how to fetch it: `file`, `folder` or `gunzip`. A package with no `download` hook is listed by its `tree` patterns.

The hooks in v0.3.0:

| Dataset | Hook | Does |
|---|---|---|
| AI-READI | `views` | The participant's demographics, and the measurement and observation rows as one table. |
| BDSP | `download` | Keys under BDSP's S3 access point: the index tables, then each patient's latest night. |
| BDSP | `psg` | Each patient's latest night on disk: its start and end, the families it carries, its sleep metrics and the demographics. `rate_enforced` lists families a night only carries when the family accepts the night's native rate. It is also the evidence rules' `views`. |
| MIMIC-IV | `download` | PhysioNet: core and ED whole, then the chest films, ECGs and bedside waveforms of the source population. |
| MIMIC-IV | `ckd` | CKD by KDIGO from blood creatinine, and the end of each patient's creatinine span. |
| MIMIC-IV | `cxr` | One row per frontal chest film (PA, AP), timed by the study's date and time. |
| MIMIC-IV | `wdb` | Bedside waveforms and numerics: one row per segment and family, and one per numerics file. |
| MIMIC-IV | `views` | Demographics, labs, ED vitals and outpatient measurements as one table, image sizes, and `crop_file` for the numerics. |
| VitalDB | `download` | VitalDB's open API: the clinical, lab and track tables, then each case's `.vital` file. |
| VitalDB | `views` | The case's demographics, the lab rows as one table, and `dummy_unit` for `.vital` files. Lab times are dates counted from 2000-01-01 00:00:00, the start of the case, the moment the EDF recordings start; surgical times stay in seconds from the start of the case. |

## Verify

Before loading, every table file the readers list and every file a hook's `inputs` names must exist. `verify` adds:

| Check | Meaning |
|---|---|
| `version` | The copy's release, which must equal `description.version`: `{file, key}` reads a field of a JSON file, or `{file, contains, version}` gives `version` when the file contains the text. |
| `manifests` | A glob of tab-separated manifests. Every file their `filepath` or `file_path` columns list must exist. |
| `unit_files` | A path pattern with `{unit}`, such as `cases/{unit}.vital`. The file must exist for every unit. |

```yaml
verify:
  manifests: "*/manifest.tsv"
  version: {file: dataset_description.json, key: version}
```

## Visit rules

| Rule | Meaning |
|---|---|
| `visit: unit` | The subject is the visit: one case, one visit. |
| `one_visit: <code>` | Each subject has exactly one `<code>` event, and every event belongs to its visit. |
| `untimed: true` | An event with no time takes the time of the subject's `one_visit` event, for cross-sectional data. Needs `one_visit`. |

## Policy file

| Field | Required | Meaning |
|---|---|---|
| `dataset` | yes | Dataset id, matching its package folder, such as `mimic-iv`. |
| `version` | yes | The dataset release the policy was read against. |
| `access` | yes | `open` or `credentialed`. |
| `license` | yes | `id` and `url` of the license or data use agreement. |
| `modules` | no | Per-module overrides where modules carry different licenses. |
| `publish` | yes | For each kind of output (`schema`, `templates`, `recipes`, `id_lists`, `labels`, `per_record_derived`, `samples`): `allow`, `conditional` or `deny`. |
| `routes` | yes | `local` and `cloud`, each `allow`, `conditional` or `deny`. |
| `route_conditions` | no | What a `conditional` route requires, such as verified zero retention. |
| `use` | yes | Whether commercial use is allowed, and any restriction on purpose. |
| `attribution` | no | The notice a published sample must carry. |
| `sources` | yes | The license, agreement and FAQ pages the policy was read from. |

## Rules

- Use only a route the policy allows. Before a run, Bench refuses a route the policy denies, and prints the `route_conditions` of a `conditional` route: it runs, and you must meet each condition. A dataset with no policy allows only `local`.
- Nothing marked `deny` under `publish` is ever uploaded or published. For credentialed datasets, templates, recipes and config hashes ship instead of data.
- MedOmni's public Hugging Face repository holds dummy data only. No real record is published there, whatever the policy allows.

## Where next

- [Connect your data](../guides/connect-your-data.md): build tasks from your own access.
- [Tasks](tasks.md): the templates and task sets on each dataset.
- [Recipes](recipes.md): the label library and evidence files in each package.
- [Design principles](../learn/principles.md): why patient data stays local.
