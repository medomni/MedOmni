# Cache

The cache keeps the results of slow steps, such as loading a dataset or converting a recording, so a later build can skip them. It only saves time. Deleting it loses nothing but time, and a build with no cache gives the same atom tasks as a build with one. Nothing checks, compares or publishes what it holds.

```text
your copy ──step──▶ cache ──▶ later builds
```

## Steps

A step is a function of its arguments: the dataset, the step's name and version, its parameters and its inputs. Inputs are raw files, each named with its identity: a hash of the file, or for a large recording a quick identity, its size and its first and last MiB. The result's key is built from those arguments alone, so a changed input, parameter or step version gives a new key.

Core's steps are `events`, the dataset's [event table](../studio/datasets.md), and one `convert-<converter>` per [family converter](families.md#family-converters).

A cache backend has one call:

```text
run(dataset, step, version, params, inputs, make) -> (result, created)
```

`make` writes the step's files into an empty folder. `run` returns a folder holding those files, made now or kept from before, and whether it made them. Callers read only that folder.

- A step writes real files only, no links, so every backend works on any file system, exFAT included.
- Build copies files from the cache into atom tasks. Atom tasks never link to the cache.
- Cache contents are derived from patient data. They stay on your machine and are never committed, uploaded or shared.

## Backends

The workspace config's `cache` names the backend:

```yaml
cache: /home/me/medomni/cache          # the folder backend, at this path
cache: {backend: none}                 # keep nothing between processes
cache: {backend: my-cache, path: …, options: {…}}   # a backend from a plug-in package
```

| Backend | Keeps |
|---|---|
| `folder` (the default) | Each result in its own folder, `<path>/<dataset>/<step>/<key>/`, with a `CACHE.json` of the step, version, parameters, inputs and row counts. A result is never changed; the old one stays until `cache gc` removes it. |
| `none` | Nothing between processes. Within one process a step with the same arguments runs once. |

A [plug-in package](plugins.md) adds a backend in the `medomni.caches` entry-point group, with no change to Core. `path` and `options` are the backend's own.

## Commands

| Command | Does |
|---|---|
| `medomni cache build <dataset>` | Loads the dataset's event table into the cache, ahead of a build. `medomni studio task build` does this too, when needed. |
| `medomni cache status` | Lists the results per dataset and step, with size and whether a current step uses them. |
| `medomni cache gc [--dry-run]` | Removes results no current step uses, and unfinished folders. `--dry-run` lists them first. |

`cache status` and `cache gc` are features of the `folder` backend. A backend without them says so.

## Where it lives

- `src/medomni/core/cache/`: the backend call, the `folder` and `none` backends, and the commands
- the path in your workspace config: the `folder` backend's results

## Where next

- [Build](../studio/build.md): the steps that fill the cache.
- [Rebuild a task set](../../guides/rebuild-a-task-set.md): build a published task set from your own copy.
