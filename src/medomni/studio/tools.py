"""The six tool kinds, and how Studio finds tools (R-53, R-123).

A tool is a class of one kind, registered in the `medomni.tools` entry-point group. Every kind has the same interface,
so a new tool of a kind works with the same commands:

    class MySurvey(Survey):
        name = "my-survey"              # the command
        summary = "what it reports"
        target = "dataset"              # the positional argument, or None
        def options(self, parser): ...  # optional: more arguments
        def make(self, target, a, ctx) -> Result: ...

`make` returns the text to print and the files to write. Studio writes them, under `--out` or the tool's folder in
the workspace, so a tool that goes through `Result` cannot write anywhere else.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

from medomni.core import plugins, workspace

KINDS = ("survey", "propose", "review", "preview", "report", "assets")


@dataclass
class Result:
    text: str = ""  # printed by the command
    files: dict = field(default_factory=dict)  # relative path -> str or bytes
    code: int = 0  # the exit code


class Context:
    """What a tool may ask for: the workspace config, and its stream. The config is loaded on first use, so a tool
    that needs no workspace runs without one."""

    def __init__(self, stream=None, ws=None):
        self.stream = stream or sys.stdout
        self._ws = ws

    @property
    def ws(self):
        if self._ws is None:
            self._ws = workspace.load()
        return self._ws


class Tool:
    kind = ""
    name = ""
    summary = ""
    target: str | None = None  # the positional argument's name
    target_help = ""

    def options(self, parser) -> None:
        pass

    def make(self, target, a, ctx: Context) -> Result:
        raise NotImplementedError

    def folder(self, target, a, ctx: Context) -> Path:
        """Where `Result.files` go: `--out`, else `<workspace>/studio/<kind>/<tool>/`."""
        return Path(a.out) if getattr(a, "out", None) else workspace.home() / "studio" / self.kind / self.name

    def run(self, a, ctx: Context) -> int:
        r = self.make(getattr(a, "target", None), a, ctx)
        if r.text:
            print(r.text, file=ctx.stream)
        if r.files:
            out = self.folder(getattr(a, "target", None), a, ctx)
            for rel, content in sorted(r.files.items()):
                p = out / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(content) if isinstance(content, bytes) else p.write_text(content, encoding="utf-8")
            print(f"wrote {len(r.files)} file(s) under {out}", file=ctx.stream)
        return r.code


class Survey(Tool):
    """Reports what a dataset has: codes, families, time spans, counts."""

    kind = "survey"


class Propose(Tool):
    """Makes content for a pull request: task proposals, and the files people write by hand."""

    kind = "propose"


class Review(Tool):
    """Review forms and sign-off, status views, and the audit."""

    kind = "review"


class Preview(Tool):
    """Shows what something does without building it."""

    kind = "preview"


class Report(Tool):
    """Tables, figures and views of builds and runs."""

    kind = "report"


class Assets(Tool):
    """Works with the files encoders and families are checked on."""

    kind = "assets"


KIND_CLASSES = (Survey, Propose, Review, Preview, Report, Assets)


class ToolError(RuntimeError):
    """A tool refuses: the message names what is missing. The command prints it and exits 2."""


# Studio's own tools. They register in `medomni.tools` like any plug-in tool; this table is the same list, for an
# install that predates those entry points. A plug-in tool with one of these names clashes with it (R-65).
BUILTIN = {
    "survey": "medomni.studio.survey.dataset:DatasetSurvey",
    "census": "medomni.studio.survey.census:Census",
    "intake": "medomni.studio.propose.intake:Intake",
    "relevance": "medomni.studio.propose.relevance:Relevance",
    "audit": "medomni.studio.review.audit:Audit",
    "review-form": "medomni.studio.review.forms:ReviewForm",
    "encoder-status": "medomni.studio.review.encoder_status:EncoderStatus",
    "preview": "medomni.studio.preview.recipe:RecipePreview",
    "download-list": "medomni.studio.preview.download_list:DownloadList",
    "dummy": "medomni.studio.preview.dummy_tool:Dummy",
    "tables": "medomni.studio.report.tables:Tables",
    "build-sheet": "medomni.studio.report.build_sheet:BuildSheet",
    "progress": "medomni.studio.report.progress:Progress",
    "bench-health": "medomni.studio.report.bench_health:BenchHealth",
    "diagrams": "medomni.studio.report.diagrams_tool:Diagrams",
    "encoder-demo": "medomni.studio.assets.encoder_demo:EncoderDemo",
    "testdata": "medomni.studio.assets.testdata:Testdata",
    "family-samples": "medomni.studio.assets.family_samples:FamilySamples",
}


@dataclass(frozen=True)
class Found:
    targets: dict[str, str]  # command -> "module:Class"
    errors: tuple[str, ...]


def found() -> Found:
    r = plugins.resolve(plugins.TOOLS)
    targets = dict(BUILTIN)
    errors = [msg for _, msg in r.errors]
    for name, piece in r.pieces.items():
        if name in BUILTIN and piece.target != BUILTIN[name]:  # a clash: both are reported and neither is used
            targets.pop(name)
            errors.append(f"name '{name}' is registered more than once in {plugins.TOOLS} ({piece.full_name}, built-in); "
                          "none is loaded")
        else:
            targets[name] = piece.target
    return Found(targets, tuple(errors))


def load(target: str, name: str = "") -> Tool:
    piece = plugins.Piece(plugins.TOOLS, name or target, plugins.BUILTIN, target)
    cls = piece.load()
    return cls()


def problems(tool: Tool, name: str) -> list[str]:
    """What `medomni studio check <tool>` refuses: a tool that does not follow its kind's interface."""
    out = []
    kinds = [k for k in KIND_CLASSES if isinstance(tool, k)]
    if len(kinds) != 1:
        out.append(f"is a subclass of {len(kinds)} kinds; a tool is exactly one of {', '.join(KINDS)}")
    if tool.kind not in KINDS:
        out.append(f"kind '{tool.kind}' is not one of {', '.join(KINDS)}")
    if tool.name != name:
        out.append(f"registered as '{name}' but names itself '{tool.name}'")
    if not tool.summary.strip():
        out.append("has no summary")
    if tool.target is not None and not isinstance(tool.target, str):
        out.append("target must be the positional argument's name, or None")
    if type(tool).make is Tool.make:
        out.append("does not define make(target, a, ctx)")
    if type(tool).run is not Tool.run:  # Result is the only route Studio can confine to the workspace
        out.append("overrides run(); return files in Result so Studio writes them")
    return out
