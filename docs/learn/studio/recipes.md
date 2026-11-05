# Recipes

A recipe says what Build takes from a dataset. One format covers all of it:

- **cohort:** who is included, and at which prediction time
- **labels:** each target's answer
- **evidence:** which rows, codes and files each patient's atom task holds

Each part is a set of queries over the dataset's [event table](datasets.md#event-table). The queries name codes and windows; they never name patient ids. A cohort is therefore published as rules, never as a list of patients, which every dataset license allows.

## Where each part lives

| Part | File | Written by |
|---|---|---|
| Cohort | `cohorts/<cohort>.yaml`, next to its template | The task's authors |
| Labels | `labels.yaml`, in the dataset package | The dataset's maintainers |
| Evidence | `evidence.yaml`, in the dataset package; the template names its tables and families | The dataset's maintainers |

A template's targets name labels from the library, such as `mimic:ckd-kdigo`. Templates on one dataset share its labels and its evidence rules.

## Cohort

A cohort file has five parts, run in this order:

1. **Source population:** the patients a cohort may draw from.
2. **Prediction time:** an anchor event, such as an admission, plus an optional offset. Nothing after it is evidence.
3. **Requirements:** events or files each patient must, or must not, have in a window.
4. **Labels:** the targets' answers. A patient with no answer is left out.
5. **Draw:** how many patients per class, and the seed.

### Source population

A patient is in the source population when `sha256(salt|patient id)`, read as a fraction, is below f. The salt and the default f are in the dataset package.

- The rule needs no list of ids, so it can be published.
- Source populations nest: the patients at 1% are all in the 5% source population.
- For datasets downloaded in parts, the rule runs on the dataset's own metadata first, and [Studio](../studio/overview.md) lists the files to download.

### Draw

- n is split evenly across the classes of the `by` label. Any remainder goes to the first classes.
- Within each class, patients are ranked by `sha256(seed|patient id|prediction time)` and the first k are taken.
- A class with too few patients stops the build. Other classes do not make up the shortfall.

Because the draw ranks by hash:

- it is the same on every machine and Python version
- the first 20 of a class at n = 50 are the patients drawn at n = 20
- one patient more or less in the pool changes at most one place

## Labels

Each entry in `labels.yaml` is one rule: a code, a window relative to the prediction time, and how the value is read (present or not, last value, highest value, a threshold, bins). A label that cannot be written as a rule calls a hook in the dataset package, such as CKD staging by KDIGO.

Each label also states its **guard**: the codes and fields that would reveal its answer. Build removes them from the evidence.

Every label states its window. A label read from any time, before or after the prediction time, is allowed and is flagged by Build's check.

## Evidence

Per table, the evidence rules say:

- which column holds the row's time; rows after the prediction time are left out
- which fields are only known later, such as a discharge time, and are blanked while the stay is open
- which rows belong to the patient's current visit and are left out or blanked
- which rows are kept only when a linked row is kept, such as triage rows of a kept ED stay

Files are kept when their time is before the prediction time. The template chooses which tables and families the agent sees; the guard of every target is then removed.

## Checks in every recipe

- **Test patients.** Each cohort comes with a few hand-written patients as event rows, and the expected result: in or out, prediction time, label values. They run in CI with no licensed data, so any copy of Build can be checked before it touches real data.
- **Step counts.** Build records how many patients are left after each step. A rebuild that differs shows where.
- **Named conditions.** A condition used by several recipes, such as "acute kidney injury", is defined once in the dataset package and named in each recipe.

## Where it lives

- `src/medomni/core/recipes/`: the recipe format and its validator
- `bench/datasets/<dataset>/labels.yaml` and `evidence.yaml`
- `bench/datasets/<dataset>/tasks/<template>/cohorts/`: the cohorts and their test patients

## Where next

- [Recipes reference](../../reference/recipes.md): every field, the shared codes, and two worked examples.
- [Build](build.md): how a recipe runs.
- [Studio](../studio/overview.md): preview a recipe's counts on your copy before you build.
