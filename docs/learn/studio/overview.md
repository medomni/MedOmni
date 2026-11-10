# Studio

Studio is the project for the work people do around Bench and Perception: surveying datasets, proposing and reviewing tasks, previewing cohorts, auditing, and reporting results. Bench and Perception hold only what builds, runs, scores and serves.

```text
survey ──▶ propose ──▶ review and sign-off ──▶ frozen template + cohorts ──pull request──▶ Bench
                                                       preview on your copy ─┘
results ──▶ report, audit
```

## The line between Studio and the other projects

With Studio removed, anyone can still rebuild a task set, run an agent, score it and serve the encoders, with the same results. Anything that test does not need belongs in Studio.

- Studio may import Core, Bench and Perception. Nothing imports Studio.
- Studio writes to your workspace, or to its own content folder by pull request. Bench and Perception never read what Studio writes.
- Patient-level outputs, such as survey counts per patient or review sheets with records, stay in your workspace. Proposals and forms in the repository hold no patient data.

## Tool kinds

Every Studio tool is one of six kinds. Each kind has one interface, so a new tool of that kind works with the same commands.

| Kind | Does | In v0.3.0 |
|---|---|---|
| **survey** | Reports what a dataset has: codes, families, time spans, counts. Reads the event table. | The dataset survey, the target census |
| **propose** | Makes content for a pull request: task proposals from clinicians, and the files people write by hand. | Intake form and task catalogue, the relevance table scoring reads |
| **review** | Review forms and sign-off, status views, and the [audit](audit.md). | Review forms, the audit, encoder status (which are built and which are planned) |
| **preview** | Shows what something does without building it. | Cohort preview up to cohort selection, the files a source population needs, dummy data |
| **assets** | Works with the files encoders and families are checked on. | An encoder demo on one sample, encoder test data, family samples |
| **report** | Tables, figures and views of builds and runs. | Result tables, build sheets, a run's live progress, encoder health from a finished run, the architecture diagrams |

## From proposal to Bench

A task proposal moves through four states, recorded in its file:

1. **draft:** written from the intake form
2. **under review:** reviewers fill in the review form
3. **signed off:** a named clinician and a MedOmni maintainer sign, with the date
4. **frozen:** turned into a task template and cohorts, and opened as a pull request to Bench

A change to a frozen template is a new proposal, and raises the [version](../bench/tasks.md#version) of each of its cohorts.

## Commands in v0.3.0

```bash
medomni studio survey mimic-iv                     # codes, families, time spans and counts
medomni studio census medomni-bench/v1            # families staged and answers' spread, per pair and arm
medomni studio intake <file>                       # intake rows to drafts, or a signed-off proposal to a template
medomni studio review-form <template>@<cohort>     # a task's clinical review form
medomni studio preview mimic-iv_ckd-staging@n20   # patients left after each step and per class
medomni studio download-list bdsp                  # what to download: source, path in your copy, how
medomni studio dummy vitaldb --out ~/dummy         # VitalDB-shaped dummy data, in a folder
medomni studio audit                               # the audit report, in your workspace
medomni studio progress <run>                      # a live view of a run, beside medomni bench run
medomni studio build-sheet medomni-bench/v1        # what a set's build made, per task
medomni studio bench-health <run>                  # encoder health from a finished run
medomni studio tables                              # the results table of the scored runs
medomni studio relevance <template>                # write the relevance table for a template
medomni studio encoder-status                      # which encoders are built and which are planned
medomni studio encoder-demo <encoder>              # run an encoder on one sample
medomni studio testdata <encoder>                  # write an encoder's test inputs and PROVENANCE.md
medomni studio family-samples <family>             # write samples of a family
```

The architecture diagrams are drawn from one description, `docs/assets/diagrams.yaml`. After a change, regenerate them; each SVG also opens in draw.io:

```bash
medomni studio diagrams docs/assets/diagrams.yaml --out docs/assets/
```

## Add a tool

A tool is a Python class of one kind, registered in the `medomni.tools` entry-point group, from MedOmni's repository or a plug-in package. `medomni studio check <tool>` checks that it follows its kind's interface and writes only to the workspace.

## Where it lives

- `src/medomni/studio/`: one subpackage per kind: `survey/`, `propose/`, `review/` (with the audit), `preview/`, `assets/`, `report/`
- `studio/`: content people write and review: `proposals/` and `forms/`
- your workspace: everything the tools write

## Where next

- [Audit](audit.md): the review kind's audit.
- [Recipes](../bench/recipes.md): what `preview` runs.
- [Build](../bench/build.md#make-and-build): where a frozen template goes next.
