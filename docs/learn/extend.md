# Extend MedOmni

What you can add to MedOmni, how, and what checks it.

## Three ways in

- **Use it as is.** Your own agent config, your own data copy and your own code calling the gateway need no registration and no pull request.
- **Pull request.** The piece joins MedOmni's repository and its releases.
- **Plug-in package.** The piece stays in your own `medomni-*` package and loads like a built-in one. See [Plug-ins](core/plugins.md).

## What you can add

| You add | Project | Follows contract | Create with | Check | Pull request | Plug-in package |
|---|---|---|---|---|---|---|
| An agent | Bench | Agent config | `medomni bench agent new` | `medomni bench run --set medomni-bench/smoke-dummy` | `bench/agents/` | content folder: `bench/agents/` |
| A dataset | Bench | Dataset config, recipe, dataset policy | `medomni bench data new` | `medomni bench data check` | openly licensed only | content folder: `bench/datasets/<dataset>/` |
| A task | Bench | Task template, recipe | `medomni bench task new` | `medomni bench task check` | openly licensed data only | content folder: `bench/datasets/<dataset>/tasks/<template>/` |
| A benchmark | Bench | Benchmark card, task set | `bench/benchmarks/<benchmark>/` | `medomni bench task check --set <benchmark>/<set>` | MedOmni team only | content folder: `bench/benchmarks/<benchmark>/` |
| An encoder | Perception | Model card, Container API | `medomni perception new` | `medomni perception check` | `perception/encoders/` | content folder: `perception/encoders/<family>/<encoder>/` |
| An arm | Bench | The arm interface | A plug-in package | `medomni bench task build --set <benchmark>/<set>`, on a set that lists it | no: Bench's four arms are fixed | entry point: `medomni.arms` |
| A Studio tool | Studio | Its kind's interface | `src/medomni/studio/<kind>/` | `medomni studio check` | `src/medomni/studio/<kind>/` | entry point: `medomni.tools` |

- Every check is the same in MedOmni's CI, in your terminal and in a plug-in package's CI ([testing kit](core/plugins.md#the-testing-kit)).
- [Contribute](../guides/contribute.md) walks through each one.
- A benchmark is a card (version, owner, license, the intelligence kinds it accepts) and its task sets. MedOmni's own is `medomni-bench`; a plug-in package publishes its own the same way.

## What you can use without adding anything

| You use | Through | See |
|---|---|---|
| Your own agent | An agent config file on your machine | [Run your agent](../guides/run-your-agent.md) |
| Your own data copy | `medomni bench data connect` | [Connect your data](../guides/connect-your-data.md) |
| The encoders from your own code | The Gateway API | [Use the encoders](../guides/use-the-encoders.md) |
| Results in your own analysis | The result records in the run folders and `results.jsonl` | [Run your agent](../guides/run-your-agent.md#results-file) |

## What you ask the MedOmni team for

Open an issue for these. Only the MedOmni team changes them, because every project depends on them.

- a new family, or a new alias for one
- a new format reader, for a file format no format reader knows
- a new shared code
- a change to any [contract](core/contracts.md)

## Not open in v0.3.0

- **Metrics.** Targets use `auc`, `qwk` or `mae`.
- **Runners.** The agent is the only kind of intelligence, and Bench's harness is its runner.
- **Other tool access.** Inside an atom task the agent reaches only the perception service. Other tool access, such as MCP servers or skills, would be added beside it later, not inside it.
