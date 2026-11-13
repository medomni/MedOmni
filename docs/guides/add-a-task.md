# Add a task

For a task on a supported dataset, using labels and families MedOmni already has, or labels you add to the dataset's library.

## Steps

1. Create the template and a first cohort:

    ```bash
    medomni studio task new vitaldb_my-task --dataset vitaldb
    ```

2. Fill in `template.yaml`: the targets with each one's label and metric, the input, and the `agent` block with the statement, the prediction-time paragraph, environment and submission path. Give each label a `question`, or give the target its own. The agent sees the patient's whole record minus the labels' guards, so do not list leaking evidence again. The fields are in [Tasks reference](../reference/tasks.md#task-template).
3. Write a cohort in `cohorts/`: source population, prediction time, requirements and cohort selection (`select`). Add its test patients. See [Recipes reference](../reference/recipes.md#cohort-file).
4. Preview the counts on your copy, adjust the cohort, then build.

    ```bash
    medomni studio preview vitaldb_my-task@n20
    medomni studio task build vitaldb_my-task@n20
    ```

5. Open a pull request with the template folder.

## Check

```bash
medomni studio task check vitaldb_my-task@n20
```

It checks:

- the template's fields and metrics
- that each target's label is in the library and states its window
- that the cohort's test patients give their expected results
- the [correctness checks](../learn/studio/build.md#correctness-checks): no answer in the evidence, events still ahead and images before the prediction time, enough patients, answers that vary, complete recordings, a closed network
- that staged files match their families

Submit it as a pull request, or ship it in your own plug-in package. [Contribute](contribute.md) covers both.

## Where next

- [Contribute](contribute.md): pull requests, plug-in packages and how MedOmni is developed.
- [Tasks reference](../reference/tasks.md): the task template contract.
- [Recipes reference](../reference/recipes.md): the cohort, label and evidence fields.
