# Recipes

The fields of a cohort file, a label library and an evidence file, the shared codes, and two worked examples. The recipe format is the input of MedOmni's builder, `medomni-v1`. [Recipes](../learn/studio/recipes.md) explains how the parts fit.

Format: recipe, in `src/medomni/studio/schemas/`: `recipe.schema.json` (cohort), `recipe-tests.schema.json` (test patients), `recipe-labels.schema.json` and `recipe-evidence.schema.json`.

## Times and windows

Windows are written relative to the prediction time or an event:

- `anchor`: the prediction time
- `anchor.event`: the anchor event itself, before the offset
- `anchor + 7 days`, `anchor - 24 hours`: an offset; units `minutes`, `hours`, `days`
- `visit:<code>`: the time of that code in the anchor's visit

`from` and `to` bound a window. `from` is included and `to` is included unless `include_from` or `include_to` is `false`. A missing bound is open.

## Cohort file

`studio/datasets/<dataset>/tasks/<template>/cohorts/<cohort>.yaml`

| Field | Required | Meaning |
|---|---|---|
| `version` | yes | The [version](../learn/studio/tasks.md#version) `N.X` of the tasks built from this cohort, as a quoted string such as `"1.0"`. Unquoted, YAML reads it as a number and `1.10` becomes `1.1`, so the contract refuses it. |
| `source` | yes | The source population: `all`, or `{fraction: f}` for the hash rule with the dataset's salt. Omitting `fraction` uses the dataset's default. |
| `anchor` | yes | The prediction time: `event` (a code), `pick` (`first` or `last`; default `first`), `plus` (an offset). |
| `require` | no | A list of requirements, all of which must hold. |
| `select` | yes | How cohort selection picks patients: `n` (patients in all), `by` (target names that define the classes; empty for a continuous target), `balance` (labels from the library that split each class into groups; never scored or shown), `seed` (a number or text). |

A requirement is one of:

| Form | Holds when |
|---|---|
| `any: [codes]` | at least one of the codes occurs in the window |
| `none: [codes]` | none of the codes occurs in the window |
| `files: [families]` | the patient has a file in each family in the window |
| `has_label: <target>` | the target's label has a value |
| `definition: <name>` | the dataset's named definition holds |
| `converts: {min_families: n}` | at least n of the patient's files convert and match their family; checked during cohort selection, going down the ranking, and a patient who fails is replaced by the next one |

`any`, `none` and `files` take `from`, `to` and `same_visit: true` (only events in the anchor's visit count). Codes may be patterns: `^DIAGNOSIS//ICD//(N17|584)`.

Test patients: `cohorts/<cohort>.tests.yaml`, a list of patients, each with `events` (rows of the event table) and `expect`: `in` (true or false), and when in, `anchor` and the label values.

## Label library

`studio/datasets/<dataset>/labels.yaml`: one entry per label, named `<dataset>:<label>` in templates.

| Field | Meaning |
|---|---|
| `exists` | 1 when a matching code occurs in the window, else 0. |
| `none` | 1 when no matching code occurs in the window, else 0. |
| `value` | The code whose value is read. |
| `pick` | Which value: `first`, `last` (default), `min`, `max`. |
| `op`, `x` | Compare the value with `x` (`<`, `<=`, `==`, `>=`, `>`), giving 1 or 0. |
| `bins` | Cut points; gives the bin index, 0 to the number of cuts. |
| `cases`, `else` | Ordered `when` (a rule) and `then` (the result); the first that holds wins. |
| `default` | The result when no event is found. Without it, the patient has no label. |
| `from`, `to` | The window, as above. Required; `any` marks a label read from any time, which Build flags. |
| `same_visit`, `other_visit` | Count only events in the anchor's visit, or only events in other visits, such as for a readmission. They exclude each other. |
| `hook` | A Python function in the package's `hooks/`, for a label no rule can express. |
| `guard` | What would reveal the answer: `codes` (patterns) and `fields` (table columns). Removed from the evidence. |
| `question` | The sentence that tells the agent exactly what the target asks. A template's target may replace it. Each target needs one, here or in the template. |

Each label has exactly one rule: `exists`, `none`, `value`, `cases` or `hook`.

Named definitions are in the package's `dataset.yaml`, under `definitions`, each a requirement as above.

## Evidence file

`studio/datasets/<dataset>/evidence.yaml`: `tables`, `static`, `files`, `views` and `reading_note`.

Per table:

| Field | Meaning |
|---|---|
| `time` | The column compared with the prediction time. A date-only value counts as the end of that day. An empty value is kept. |
| `time_from` | Time the row by a linked row instead: `{table, key, column}`. `missing_time: drop` drops rows with no linked time. |
| `visit` | The visit column. `skip_index_visit: true` drops rows of the anchor's visit. |
| `end`, `blank_after_end` | When the row's `end` is after the prediction time, blank these fields. `missing_end` says whether an empty end counts as `after` or `before`. |
| `blank_in_index_visit` | Fields blanked on the anchor's visit, at any time. `guard.fields` names the guard fields of the template's labels. |
| `drop` | `guard`: drop rows whose emitted code matches a guard code of the template's labels. |
| `keep_if_kept` | Keep a row only when its key is in another table's kept rows: `{table, key}`. |
| `write_empty` | Write the table, header only, when the patient has no rows. |

`static`: the patient's static facts. `blank` names the fields to blank, or `guard.fields`; `aliases` maps a static field to the column, or columns, that hold it.

`files`: files are kept when their time is at or before the prediction time; an untimed file is kept. `crop` lists families whose files have no time of their own but hold rows from after it, such as one table of a whole stay: each such file is cut at the prediction time by the `views` hook's `crop_file`, and staged as a copy.

The rest of the file:

| Field | Meaning |
|---|---|
| `views` | A hook in the package's `hooks/` that gives the forms the agent reads. Its functions are optional: `demographics` (the patient's static facts), `measurements` (the kept rows as one long table, read by the `clinical-measurement-irregular` family), `file_meta` (details of a file, such as an image's size), `crop_file` (for `files.crop`). |
| `reading_note` | A fact about reading this dataset's files, told to the agent in every arm. |

## Template fields that use the recipe

In `template.yaml`:

| Field | Meaning |
|---|---|
| `targets` | Each with `name`, `label` (a library entry), `metric` (`auc`, `qwk` or `mae`), and an optional `question` that replaces the label's. |
| `input`, `exclude` | What the proposal named to show and to remove. A record only: the evidence is the whole record minus the targets' guards. |

The other template fields are in [Tasks reference](tasks.md#task-template).

## Shared codes

Every dataset that has these concepts uses these codes. All other codes are the dataset's own, listed in its `codes.csv`.

| Code | Meaning |
|---|---|
| `ADMISSION`, `DISCHARGE` | Start and end of a hospital stay |
| `DEATH` | Death |
| `ICU_ADMISSION` | Start of an ICU stay |
| `DIAGNOSIS//ICD//<code>` | A diagnosis code, ICD-9 or ICD-10, without the dot |
| `FILE//<family>` | A file in a family, with its path |
| `RECORDING//START`, `RECORDING//END` | Start and end of a recording, such as a sleep study |

## Example: MIMIC-IV, coagulation disorder at 24 hours

`template.yaml` (part):

```yaml
targets:
  - {name: coagulation_hemorrhagic, label: mimic-iv:coagulation-hemorrhagic, metric: auc}
input:
  tables: [admissions, labevents, ed_vitalsign]
  families: [cxr-radiograph-2d, ecg-12lead-500hz-mv]
```

`labels.yaml` (entry):

```yaml
coagulation-hemorrhagic:
  exists: ^DIAGNOSIS//ICD//(D65|D66|D67|D68|D69|286|287)
  from: visit:ADMISSION
  to: visit:DISCHARGE
  guard: {codes: ['^DIAGNOSIS//ICD//(D65|D66|D67|D68|D69|286|287)']}
  question: Your prediction is the probability that the patient's record carries a coded diagnosis of a coagulation or hemorrhagic disorder.
```

`cohorts/n20.yaml`:

```yaml
version: "1.0"
source: {fraction: 0.05}
anchor: {event: ADMISSION, pick: first, plus: 24 hours}
require:
  - any: [DISCHARGE, DEATH]           # the stay has ended in the data
    same_visit: true
  - none: [DISCHARGE, DEATH]          # still in hospital at the prediction time
    from: anchor.event
    to: anchor
    same_visit: true
select: {n: 20, by: [coagulation_hemorrhagic], seed: 7}
```

Built as `mimic-iv_coag-hemorrhagic@n20`.

## Example: VitalDB, creatinine after surgery

`labels.yaml` (entry):

```yaml
cr_max_7d:
  value: LAB//cr
  pick: max
  from: anchor
  include_from: false
  to: anchor + 7 days
  guard: {codes: [LAB//cr], fields: [preop_cr]}
  question: Your prediction is the numeric value of the highest blood creatinine (mg/dL) in the 7 days after the end of this operation.
```

`cohorts/n20.yaml`:

```yaml
version: "1.0"
source: all
anchor: {event: OP//END}
require:
  - any: [LAB//cr]                    # a creatinine before the end of surgery
    to: anchor
  - has_label: cr_max_7d
select: {n: 20, by: [], seed: 7}          # a numeric target: no classes
```

The guard removes every creatinine row and the pre-operative creatinine field from the evidence, including values from before the end of surgery. The requirement still uses them to choose patients.

## Where next

- [Recipes](../learn/studio/recipes.md): the ideas behind the format.
- [Datasets reference](datasets.md): the dataset package and its files.
- [Tasks reference](tasks.md): the template, the atom task and the config hash.
