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

Every Studio tool is one of five kinds. Each kind has one interface, so a new tool of that kind works with the same commands.

| Kind | Does | In v0.3.0 |
|---|---|---|
| **survey** | Reports what a dataset has: codes, families, time spans, counts. Reads the event table. | The v0.2 dataset survey, moved as it is |
| **propose** | Collects task proposals from clinicians: intake form, task-collection site. | The v0.2 intake and catalogue, moved as they are |
| **review** | Review forms and sign-off, the target census, and the [audit](audit.md). | The audit; the v0.2 review sheets, moved as they are |
| **preview** | Runs a cohort on your copy or on dummy data up to the draw, without building. Lists the files a source population needs. Writes a dataset's dummy data to a folder. | `preview`, `download-list`, `dummy` |
| **report** | Tables and figures: from result records, and the architecture diagrams in these docs. | The diagram generator |

## From proposal to Bench

A task proposal moves through four states, recorded in its file:

1. **draft:** written from the intake form
2. **under review:** reviewers fill in the review form
3. **signed off:** a named clinician and a MedOmni maintainer sign, with the date
4. **frozen:** turned into a task template and cohorts, and opened as a pull request to Bench

A frozen template is never changed; a change is a new proposal.

## Commands in v0.3.0

```bash
medomni studio preview mimic_ckd-staging@n20     # patients left after each step and per class
medomni studio download-list bdsp                 # files the source population needs
medomni studio dummy vitaldb --out ~/dummy        # VitalDB-shaped dummy data, in a folder
medomni studio audit                              # the audit report, in your workspace
```

The architecture diagrams are drawn from one description, `docs/assets/diagrams.yaml`. After a change, regenerate them; each SVG also opens in draw.io:

```bash
uv run python src/medomni/studio/report/diagrams.py docs/assets/diagrams.yaml docs/assets/
```

The other v0.2 tools run as scripts and become commands of their kind later.

## Add a tool

A tool is a Python class of one kind, registered in the `medomni.tools` entry-point group, from MedOmni's repository or a plug-in package. `medomni studio check <tool>` checks that it follows its kind's interface and writes only to the workspace.

## Where it lives

- `src/medomni/studio/`: one subpackage per kind: `survey/`, `propose/`, `review/` (with the audit), `preview/`, `report/`
- `studio/`: content people write and review: `proposals/` and `forms/`
- your workspace: everything the tools write

## Where next

- [Audit](audit.md): the review kind's audit.
- [Recipes](../bench/recipes.md): what `preview` runs.
- [Build](../bench/build.md#make-and-build): where a frozen template goes next.
