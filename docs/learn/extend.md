# Extend MedOmni

What you can add to MedOmni, how, and what checks it.

## Three ways in

- **Use it as is.** Your own agent config, your own data copy and your own code calling the gateway need no registration and no pull request.
- **Pull request.** The piece joins MedOmni's repository and its releases.
- **Plug-in package.** The piece stays in your own `medomni-*` package and loads like a built-in one. See [Plug-ins](core/plugins.md).

## What you can add

| You add | Project | Follows contract | Start from | Check | Pull request | Plug-in group |
|---|---|---|---|---|---|---|
| An agent | Bench | Agent config | `bench/starters/agent/` | `medomni bench run --set smoke-dummy` | `bench/agents/` | `medomni.agents` |
| A dataset | Bench | Dataset config, recipe, dataset policy | `bench/starters/dataset/` | `medomni bench data check` | openly licensed only | `medomni.datasets` |
| A task | Bench | Task template, recipe | `medomni bench task new` | `medomni bench task check` | openly licensed data only | `medomni.tasks` |
| An encoder | Perception | Model card, Container API | `perception/starters/encoder/` | `medomni perception check` | `perception/encoders/` | `medomni.encoders` |

- Every check is the same in MedOmni's CI, in your terminal and in a plug-in package's CI ([testing kit](core/plugins.md#the-testing-kit)).
- [Contribute](../guides/contribute.md) walks through each one.

## What you can use without adding anything

| You use | Through | See |
|---|---|---|
| Your own agent | An agent config file on your machine | [Run your agent](../guides/run-your-agent.md) |
| Your own data copy | `medomni bench data connect` | [Connect your data](../guides/connect-your-data.md) |
| The encoders from your own code | The Gateway API | [Use the encoders](../guides/use-the-encoders.md) |
| Results in your own analysis | The result records in `results.jsonl` | [Run your agent](../guides/run-your-agent.md#results-file) |

## What you ask the MedOmni team for

Open an issue for these. Only the MedOmni team changes them, because every project depends on them.

- a new family, or a new alias for one
- a new reader, for a file format no reader knows
- a new shared code
- a change to any [contract](core/contracts.md)

## Not open in v0.3.0

- **Metrics.** Targets use `auc`, `qwk` or `mae`.
- **Conditions.** `enc`, `noenc`, `enc-forced` and `ladder`.
- **Other tool access.** Inside an atom task the agent reaches only the perception service. Other tool access, such as MCP servers or skills, would be added beside it later, not inside it.
