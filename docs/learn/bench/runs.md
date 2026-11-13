# Runs

A run is one agent on one atom task, once. Bench runs any [built task](../core/built-tasks.md), whoever built it. The harness turns a built task set into Harbor jobs, Harbor runs each atom task in Docker, and the harness records each run and its answers in the job's run folder.

```text
agent config + built task set ──harness──▶ Harbor jobs ──▶ one run per atom task × arm × repetition
                                                     ├──▶ run records, in the run folder
                                                     └──▶ prediction records ──▶ scorer ──▶ results file
```

## Agent

The system being evaluated is an intelligence. Its kind in v0.3.0 is `agent`: a scaffold driving a model, described in an agent config. The config names the kind, the agent, the model and the route (`local` or `cloud`); its `settings`, which the runner reads and checks, hold the scaffold (a Harbor agent such as `terminus-2`), the model name the provider must report back, and the run limits. [Run your agent](../../guides/run-your-agent.md) lists every field.

The replay agent repeats recorded runs with no model calls. MedOmni's own tests use it to run a task set at no cost.

## Arms

An arm is one way of giving the same tasks to the intelligence. Arms are compared side by side, as in a clinical trial. Bench has four:

- `encoders`: with encoders
- `no-perception`: without encoders
- `encoders-required`: must call at least one encoder
- `modality-ladder`: with encoders, at six rungs, `r1` to `r6`; each rung adds input families to the one before

Every arm renders its own atom tasks from the same content, and each has its own config hash. A task set lists its arms, and the builder builds every pair under each of them.

- `encoders`, `no-perception` and `encoders-required` differ only in encoder access and the instruction paragraph that describes it. Patients, files and answers are identical.
- `modality-ladder` has its own `ladder` cohort, the same at every rung. Rungs differ only in the families staged. The rungs and their masks are in the template folder's `arms/modality-ladder.yaml`. Records name the rung in `arm_variant`.

An arm is one name, with a one-line description, registered in `medomni.arms`. It has two sides:

- **Build side:** what it changes in the built atom task, such as the instruction paragraph, staged files or masks. Each builder implements it for the arms it supports, and refuses any other; the definition and variant are in the task's config hash.
- **Run side:** what the run attaches, such as the perception service and its call budget. Bench implements it.

A [plug-in package](../core/plugins.md) can add an arm: its run side in `medomni.arms`, and its build side for a builder in `medomni.arm_builds` as `<builder>:<arm>`, such as `medomni-v1:my-arm`. The harness reads an arm's variants from the built task's manifest. `medomni bench run --arm <arm>` picks the arms to run, and `medomni plugins` lists the arms plug-in packages add.

## Inside an atom task

- The agent works in a closed-network container with the patient's files.
- When the arm attaches it (every built-in arm except `no-perception`), the perception service runs beside it, at `http://perception:8899`. It is Perception's [gateway](../perception/gateway.md), which Bench starts and reaches only through the Gateway API. It adds:
    - a call budget per atom task
    - a family filter: only the families staged for that patient are listed
    - a call log, recorded with the run
- The agent writes its answer to the submission path. A format check confirms the answer's shape; it never scores.

## The harness

`medomni bench run`:

1. checks the whole set, and runs nothing if any check fails:
    - the [checks on built tasks](../core/built-tasks.md#checks-on-any-built-task)
    - the [stand-in agents](scoring.md#stand-in-agents) on each task
    - the agent's route against the policy of each dataset the tasks hold data from: a denied route refuses the run, and a `conditional` route prints the conditions you must meet
2. checks that the perception service's image is on your machine, when the arm attaches it
3. writes one Harbor job per arm (and rung) and repetition, with what the arm attaches, and runs them
4. records each run: ids, the intelligence, the task version and config hash, served model, cost and errors; and, in the run's `agent` block, the arm and its variant, the encoders served (id and image digest), encoder calls and files opened
5. reads the agent's answer from the submission path and writes one prediction record per target to the run's `predictions.jsonl`

Running it again resumes: atom tasks that already have a run are skipped.

## Run folders

Each Harbor job is one folder under the workspace's `runs` folder, named `<set>--<agent>--<arm>[.<variant>]--r<rep>--<stamp>`, with the `/` of the set's name written as `.`, such as `medomni-bench.v1--my-agent--encoders--r1--20261109-142000/`. It holds:

- `runs.jsonl`: one run record per atom task
- `predictions.jsonl`: the prediction records
- `encoder_use.jsonl`, on an arm with the perception service: each encoder call's [level](scoring.md#behaviour-metrics)
- one folder per trial, as Harbor writes it

Harbor sets file permissions in the job folder, so `runs` must be on a file system that supports them, not exFAT. Set it in the workspace's `workspace.yaml`.

The harness is Bench's runner for agents, registered in `medomni.runners`. Every runner has the same three steps: prepare the tasks, run them, and collect the predictions and run records.

## Prediction records

A prediction record is one answer for one target of one atom task: `run_id`, `atom`, `target`, `value` and `intelligence`. It is the only thing the scorer reads from a run. A value is a number, or a class label as text.

## Where it lives

- `src/medomni/bench/runs/`: the runner interface, the agent runner on Harbor, the replay agent, and run and prediction records
- `src/medomni/bench/arms/`: the run side of the four built-in arms
- `src/medomni/bench/runs/assets/harbor/`: the Harbor runner's job config
- `src/medomni/bench/runs/routes.py`: the route check
- `src/medomni/perception/sidecar/`: the perception service, with its call budget, family filter and call log; Perception owns it
- `bench/agents/`: contributed agent configs
- your workspace: the run folders and the results file

## Where next

- [Run your agent](../../guides/run-your-agent.md): the agent config fields and the commands.
- [Scoring](scoring.md): how runs become scores.
- [Gateway](../perception/gateway.md): what the perception service runs.
