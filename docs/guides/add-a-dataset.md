# Add a dataset

For a new openly licensed dataset, such as VitalDB, read by MedOmni's builder, `medomni-v1`. Pull requests add datasets only when openly licensed; use a plug-in package for others.

## Before you start

- The dataset's license allows redistribution of samples (for example CC BY 4.0).
- Its recordings map to existing families. See [Families](../reference/families.md).

## Steps

1. Create the dataset package:

    ```bash
    medomni studio data new my-dataset
    ```

2. Write `dataset.yaml`: the description (unit, kind of time, version), the format readers and what each reads, the dataset's rules, and any family converters its raw files need. See [Datasets reference](../reference/datasets.md#dataset-package).
3. List every code the dataset emits in `codes.csv`. Use the [shared codes](../reference/recipes.md#shared-codes) where the dataset has those concepts.
4. Write `labels.yaml` and `evidence.yaml`. See [Recipes reference](../reference/recipes.md).
5. Write the dataset policy from the license: what may be published and which routes may see the data.
6. Generate dummy data from your package and check that it has the tables and codes you expect. It comes from `dataset.yaml` and `codes.csv`, with no extra file.

    ```bash
    medomni studio dummy my-dataset --subjects 20 --out ~/dummy/my-dataset
    ```

7. Optional: add the package's dummy data, from `medomni studio dummy`, to MedOmni's public Hugging Face repository. It holds dummy data only, never real records. Nothing in Build reads it.
8. Add at least one template and cohort, as in [Add a task](add-a-task.md), and open a pull request.

Python goes only in `hooks/`: for a label no rule can express, and `download.py`, which tells `medomni studio download-list` where the dataset's files come from. See [Hooks](../reference/datasets.md#hooks). A file format no format reader knows needs a new format reader in Core: open an issue first.

## Check

```bash
medomni studio data check my-dataset
```

It checks the package's files and policy, writes and loads its dummy data, and checks that every code is in `codes.csv`.

Submit it as a pull request, or ship it in your own plug-in package. [Contribute](contribute.md) covers both.

## Where next

- [Contribute](contribute.md): pull requests, plug-in packages and how MedOmni is developed.
- [Add a task](add-a-task.md): a template and cohort on the new dataset.
- [Datasets reference](../reference/datasets.md): every field of a dataset package.
