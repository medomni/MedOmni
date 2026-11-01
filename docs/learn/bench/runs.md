# Runs

A run is one agent on one atom task, once. The harness turns a batch into Harbor jobs, Harbor runs each atom task in Docker, and the harness records each run in the results file.

```text
agent config + batch ──harness──▶ Harbor jobs ──▶ one run per atom task × condition × repetition
                                                     └──▶ results file
```

## Agent

An agent is a scaffold driving a model, described in an agent config. The config names the scaffold (a Harbor agent such as `terminus-2`), the model, the model name the provider must report back, and the route (`local` or `cloud`). [Run your agent](../../guides/run-your-agent.md) lists every field.

## Conditions

A condition sets the agent's encoder access:

- `enc`: with encoders
- `noenc`: without encoders
- `enc-forced`: must call at least one encoder

Each condition is its own built set of atom tasks. They differ only in encoder access and the instruction paragraph that describes it; patients, files and answers are identical.

## Inside an atom task

- The agent works in a closed-network container with the patient's files.
- Under `enc` and `enc-forced`, the gateway runs beside it as the perception sidecar. The sidecar adds a call budget, lists only the families staged for that patient, and logs every call.
- The agent writes its answer to the submission path. A format check confirms the answer's shape; it never scores.

## The harness

`medomni bench run`:

1. checks the agent's route against every dataset policy in the batch
2. pulls the encoder images the tasks need
3. writes one Harbor job per condition and repetition, and runs them
4. records each run: ids, fingerprint, served model, encoder calls, files opened, cost, errors

Running it again resumes: atom tasks that already have a run are skipped.

## Where it lives

- `bench/harness/`: Harbor jobs, the route check, run records
- `bench/agents/`: contributed agent configs
- your workspace: runs and the results file

## Where next

- [Run your agent](../../guides/run-your-agent.md): the agent config fields and the commands.
- [Scoring](scoring.md): how runs become scores.
- [Gateway](../perception/gateway.md): what the sidecar serves.
