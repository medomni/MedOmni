# Recipes

The fields of a cohort file, a label library and an evidence file, the shared codes, and two worked examples. [Recipes](../learn/bench/recipes.md) explains how the parts fit.

Contract: recipe, `src/medomni/core/contracts/schemas/recipe.schema.json`

## Times and windows

Windows are written relative to the prediction time or an event:

- `anchor`: the prediction time
- `anchor.event`: the anchor event itself, before the offset
- `anchor + 7 days`, `anchor - 24 hours`: an offset; units `minutes`, `hours`, `days`
- `visit:<code>`: the time of that code in the anchor's visit

`from` and `to` bound a window. `from` is included and `to` is included unless `include_from` or `include_to` is `false`. A missing bound is open.

## Cohort file

`bench/datasets/<dataset>/tasks/<template>/cohorts/<cohort>.yaml`

| Field | Required | Meaning |
|---|---|---|
| `source` | yes | The source population: `all`, or `{fraction: f}` for the hash rule with the dataset's salt. Omitting `fraction` uses the dataset's default. |
| `anchor` | yes | The prediction time: `event` (a code), `pick` (`first` or `last`; default `first`), `plus` (an offset). |
| `require` | no | A list of requirements, all of which must hold. |
| `draw` | yes | `n` (patients in all), `by` (target names that define the classes), `seed`. |

A requirement is one of:

| Form | Holds when |
|---|---|
| `any: [codes]` | at least one of the codes occurs in the window |
| `none: [codes]` | none of the codes occurs in the window |
| `files: [families]` | the patient has a file in each family in the window |
| `has_label: <target>` | the target's label has a value |
| `condition: <name>` | the dataset's named condition holds |

`any`, `none` and `files` take `from`, `to` and `same_visit: true` (only events in the anchor's visit count). Codes may be patterns: `^DIAGNOSIS//ICD//(N17|584)`.

Test patients: `cohorts/<cohort>.tests.yaml`, a list of patients, each with `events` (rows of the event table) and `expect`: `in` (true or false), and when in, `anchor` and the label values.

## Label library

`bench/datasets/<dataset>/labels.yaml`: one entry per label, named `<dataset>:<label>` in templates.

| Field | Meaning |
|---|---|
| `exists` | 1 when a matching code occurs in the window, else 0. |
| `value` | The code whose value is read. |
| `pick` | Which value: `first`, `last` (default), `min`, `max`. |
| `op`, `x` | Compare the value with `x` (`<`, `<=`, `==`, `>=`, `>`), giving 1 or 0. |
| `bins` | Cut points; gives the bin index, 0 to the number of cuts. |
| `cases`, `else` | Ordered `when` (a rule) and `then` (the result); the first that holds wins. |
| `default` | The result when no event is found. Without it, the patient has no label. |
| `from`, `to` | The window, as above. Required; `any` marks a label read from any time, which Build flags. |
| `hook` | A Python function in the package's `hooks/`, for a label no rule can express. |
| `guard` | What would reveal the answer: `codes` (patterns) and `fields` (table columns). Removed from the evidence. |

Named conditions are in the package's `dataset.yaml`, under `conditions`, each a requirement as above.

## Evidence file

`bench/datasets/<dataset>/evidence.yaml`: `tables`, `static` and `files`.

Per table:

| Field | Meaning |
|---|---|
| `time` | The column compared with the prediction time. A date-only value counts as the end of that day. An empty value is kept. |
| `time_from` | Time the row by a linked row instead: `{table, key, column}`. `missing_time: drop` drops rows with no linked time. |
| `visit` | The visit column. `skip_index_visit: true` drops rows of the anchor's visit. |
| `end`, `blank_after_end` | When the row's `end` is after the prediction time, blank these fields. `missing_end` says whether an empty end counts as `after` or `before`. |
| `blank_in_index_visit` | Fields blanked on the anchor's visit, at any time. |
| `drop` | Drop rows whose codes match the guard: `columns` (names, or `*suffix`), and optional `split` and `strip` to clean the value first. |
| `keep_if_kept` | Keep a row only when its key is in another table's kept rows: `{table, key}`. |
| `write_empty` | Write the table, header only, when the patient has no rows. |

`static`: the patient's static facts, with `blank` naming guard fields and `aliases` their column names. `files`: files are kept when their time is at or before the prediction time; an untimed file is kept.

## Template fields that use the recipe

In `template.yaml`:

| Field | Meaning |
|---|---|
| `targets` | Each with `name`, `label` (a library entry) and `metric` (`auc`, `qwk` or `mae`). |
| `input` | The tables and families the default evidence variant stages. |
| `variants` | The evidence variants built: `default`, and `full` for every table and family. |
| `exclude` | Codes or fields to remove beyond the targets' guards. |

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
  - {name: coagulation_hemorrhagic, label: mimic:coagulation-hemorrhagic, metric: auc}
input:
  tables: [admissions, labevents, ed_vitalsign]
  families: [cxr-radiograph-2d, ecg-12lead-500hz-mv]
variants: [default, full]
```

`labels.yaml` (entry):

```yaml
coagulation-hemorrhagic:
  exists: ^DIAGNOSIS//ICD//(D65|D66|D67|D68|D69|286|287)
  from: visit:ADMISSION
  to: visit:DISCHARGE
  guard: {codes: ['^DIAGNOSIS//ICD//(D65|D66|D67|D68|D69|286|287)']}
```

`cohorts/n20.yaml`:

```yaml
source: {fraction: 0.05}
anchor: {event: ADMISSION, pick: first, plus: 24 hours}
require:
  - any: [DISCHARGE, DEATH]           # the stay has ended in the data
    same_visit: true
  - none: [DISCHARGE, DEATH]          # still in hospital at the prediction time
    from: anchor.event
    to: anchor
    same_visit: true
draw: {n: 20, by: [coagulation_hemorrhagic], seed: 7}
```

Built as `mimic_coag-hemorrhagic@n20`, and `mimic_coag-hemorrhagic:full@n20` for the full variant.

## Example: VitalDB, creatinine after surgery

`labels.yaml` (entry):

```yaml
cr-max-7d:
  value: LAB//cr
  pick: max
  from: anchor
  include_from: false
  to: anchor + 7 days
  guard: {codes: [LAB//cr]}
```

`cohorts/opend.yaml`:

```yaml
source: all
anchor: {event: OP//END}
require:
  - any: [LAB//cr]                    # a creatinine before the end of surgery
    to: anchor
  - has_label: cr_max_7d
draw: {n: 20, by: [cr_max_7d], seed: 7}
```

The guard removes every creatinine row from the evidence, including those before the end of surgery. The requirement still uses them to choose patients.

## Where next

- [Recipes](../learn/bench/recipes.md): the ideas behind the format.
- [Datasets reference](datasets.md): the dataset package and its files.
- [Tasks reference](tasks.md): the template, the atom task and the fingerprint.
