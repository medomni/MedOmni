# Runs

A run is one agent on one atom task, once. The harness turns a task set into Harbor jobs, Harbor runs each atom task in Docker, and the harness records each run in the results file and its answers as prediction records.

```text
agent config + task set ──harness──▶ Harbor jobs ──▶ one run per atom task × condition × repetition
                                                     ├──▶ results file
                                                     └──▶ prediction records ──▶ scorer
```

## Agent

The system being evaluated is an intelligence. Its kind in v0.3.0 is `agent`: a scaffold driving a model, described in an agent config. The config names the scaffold (a Harbor agent such as `terminus-2`), the model, the model name the provider must report back, and the route (`local` or `cloud`). [Run your agent](../../guides/run-your-agent.md) lists every field.

The replay agent repeats recorded runs with no model calls. MedOmni's own tests use it to run a task set at no cost.

## Conditions

A condition sets the agent's encoder access:

- `enc`: with encoders
- `noenc`: without encoders
- `enc-forced`: must call at least one encoder
- `ladder`: with encoders, at six rungs; each rung adds input families to the one before

Each condition is its own built set of atom tasks.

- `enc`, `noenc` and `enc-forced` differ only in encoder access and the instruction paragraph that describes it. Patients, files and answers are identical.
- `ladder` has its own fixed cohort, the same at every rung. Rungs differ only in the families staged.

## Inside an atom task

- The agent works in a closed-network container with the patient's files.
- Under every condition except `noenc`, the perception service runs beside it, at `http://perception:8899`. It is Perception's [gateway](../perception/gateway.md), run by Bench, which adds:
    - a call budget per atom task
    - a family filter: only the families staged for that patient are listed
    - a call log, recorded with the run
- The agent writes its answer to the submission path. A format check confirms the answer's shape; it never scores.

## The harness

`medomni bench run`:

1. checks the agent's route against every dataset policy in the task set
2. pulls the encoder images for the families the tasks stage
3. writes one Harbor job per condition and repetition, and runs them
4. records each run: ids, the intelligence, fingerprint, served model, cost and errors; and, in the run's `agent` block, the condition, the encoders served (id and image digest), encoder calls and files opened
5. reads the agent's answer from the submission path and writes one prediction record per target to the run's `predictions.jsonl`

Running it again resumes: atom tasks that already have a run are skipped.

The harness is Bench's runner for agents, registered in `medomni.runners`.

## Prediction records

A prediction record is one answer for one target of one atom task: `run_id`, `atom`, `target`, `value` and `intelligence`. It is the only thing the scorer reads from a run. A value is a number, or a class label as text.

## Where it lives

- `src/medomni/bench/harness/`: the agent runner: Harbor jobs, the route check, run and prediction records, the replay agent
- `src/medomni/bench/service/`: the perception service and its call budget, family filter and call log
- `bench/agents/`: contributed agent configs
- your workspace: runs with their `predictions.jsonl`, and the results file

## Where next

- [Run your agent](../../guides/run-your-agent.md): the agent config fields and the commands.
- [Scoring](scoring.md): how runs become scores.
- [Gateway](../perception/gateway.md): what the perception service runs.
