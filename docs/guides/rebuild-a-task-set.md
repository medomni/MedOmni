# Rebuild a task set

For agent evaluators who want to run on a published task set, such as `medomni-bench/v1`, built from their own copy of the data. You build every `<template>@<cohort>` in the set from its config and check each build.

## Before you start

- Your copy of each dataset in the set is connected. See [Connect your data](connect-your-data.md).
- Space for the cache and the atom tasks in your workspace, on a disk with room for the dataset copies you use.

## Steps

1. Build the cache for each dataset in the set.

    ```bash
    medomni cache build mimic-iv
    ```

2. Build the set. Every `<template>@<cohort>` in it is built under every arm the set lists.

    ```bash
    medomni bench task build --set medomni-bench/v1
    ```

3. Check every build.

    ```bash
    medomni bench task check --set medomni-bench/v1
    ```

## Check

`medomni bench task check --set medomni-bench/v1` runs the checks of `medomni bench task check <template>@<cohort>` on every pair in the set, and lists each pair as passing or failing.

Your results carry each task's [config hash](../learn/bench/tasks.md#config-hash). Results with the same config hash used the same task config; the hash doesn't show that your copy of the data matches. To compare a build with someone else's, compare the per-step patient counts in your build manifests by hand.

!!! warning "Keep data local"
    The cache, built atom tasks, answers, traces and the results file contain patient data. Do not commit, upload or share them.

## Where next

- [Run your agent](run-your-agent.md): run on the set you built.
- [Build](../learn/bench/build.md): the steps the counts come from.
- [Cache](../learn/core/cache.md): what the cache holds.
