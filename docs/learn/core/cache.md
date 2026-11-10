# Cache

The cache keeps the results of slow steps so they run once. Every user's cache is built the same way, from their own copy of the data. Two users with the same dataset version get the same entries, with the same keys and the same content hashes.

```text
your copy ──Build step──▶ cache/<dataset>/<step>/<key>/ ──▶ later builds, runs and checks
```

## What is cached

Three kinds of entry, each in one format:

| Kind | Made by | Format |
|---|---|---|
| Event table | Loading, the first part of [Build](../bench/build.md) | Parquet |
| Per-file results | File checks and [family converters](families.md#family-converters): header facts, converted recordings | The family's format, plus a JSON of facts |
| Encoder outputs | The gateway's [router](../perception/gateway.md) | The encoder's response, as JSON |

Nothing else is cached, and nothing is cached anywhere else.

## Layout

One root, in your workspace:

```text
<workspace>/cache/
└── <dataset>/
    └── <step>/
        └── <key>/
            ├── CACHE.json
            └── …            the entry's files
```

- **Step:** the named step that made the entry, such as `events` or `convert-psg-edf`.
- **Key:** a hash of the step name, the step's version, its parameters and the hashes of its inputs. Inputs are raw files or other entries. A raw file is hashed by a quick identity, its size and its first and last MiB, so a large recording is not read in full on each build.
- **`CACHE.json`:** the step, version, parameters, every input with its hash, row counts, and the content hash of the entry.

## Rules

<!-- pending: whether cache gc and cache verify stay in v0.3 depends on the cache redesign -->
- An entry is never changed. A changed input, parameter or step version gives a new key, and the old entry stays until `cache gc` removes it.
- `cache verify` recomputes each content hash, so a changed file is found. The cache does not rely on file permissions or links, and works on any file system, exFAT included.
- Build copies files from the cache into atom tasks. Atom tasks never link to the cache.
- Cache contents are derived from patient data. They stay in your workspace and are never committed, uploaded or shared.

## Commands

| Command | Does |
|---|---|
| `medomni cache build <dataset>` | Loads the dataset and runs file conversions ahead of a build. `medomni bench task build` does this too, when needed. |
| `medomni cache status` | Lists the entries per dataset and step, with size and whether anything current uses them. |
| `medomni cache verify` | Recomputes every content hash and names any entry that changed. |
| `medomni cache gc` | Removes entries no current step uses. `--dry-run` lists them first. |

## Where it lives

- `src/medomni/core/cache/`: keys, `CACHE.json`, and the four commands
- `<workspace>/cache/`: the entries; the workspace path is in your [workspace config](contracts.md)

## Where next

- [Build](../bench/build.md): the steps that fill the cache.
- [Rebuild a task set](../../guides/rebuild-a-task-set.md): build a published task set from your own copy.
