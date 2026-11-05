# Rebuild a task set

For agent evaluators who want to run on a published task set, such as `v1`, built from their own copy of the data. You build every `<template>@<cohort>` in the set and check each one against its published fingerprint.

## Before you start

- Your copy of each dataset in the set is connected. See [Connect your data](connect-your-data.md).
- Space for the cache and the atom tasks in your workspace, on a disk with room for the dataset copies you use.

## Steps

1. Build the cache for each dataset in the set, and compare it with the published hashes.

    ```bash
    medomni cache build mimic-iv
    medomni cache verify --set v1
    ```

2. Build the set. Every `<template>@<cohort>` in it is built under every condition.

    ```bash
    medomni bench task build --set v1
    ```

3. Check every build against the set's published fingerprints.

    ```bash
    medomni bench task check --set v1
    ```

## Check

`medomni bench task check --set v1` lists each `<template>@<cohort>` as matching or not. For one that does not match, it prints the step counts beside the published ones, and marks the first step that differs:

| Differs first at | Usual cause |
|---|---|
| Source population | A different dataset version or module |
| Prediction time or requirements | Missing tables or files in your copy |
| File check | A recording that does not convert |
| Draw, with every earlier count equal | A changed build; open an issue |

`medomni cache verify --set v1` names the cache entries that differ, which usually point at the same cause.

You can still run on a build that differs. Its runs are recorded apart, and `medomni bench score` never puts them in the same table as published scores.

!!! warning "Keep data local"
    The cache, built atom tasks, answers, traces and the results file contain patient data. Do not commit, upload or share them.

## Where next

- [Run your agent](run-your-agent.md): run on the set you built.
- [Build](../learn/bench/build.md): the steps the counts come from.
- [Cache](../learn/core/cache.md): what `cache verify` compares.
