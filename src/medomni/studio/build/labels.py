"""Labels from a package's label library, over one subject's events (Recipes reference page, label library).

S1's probed interpreter (U1.16, U1.17: all 65 v0.2 targets agree on every patient of their pools), on v0.3's event
table and Core's `Label` contract. Build's gold step uses it in part 3.

    ctx = anchor(events, cohort.anchor)        # None: the subject has no anchor event
    value = label(library["outcome:los-gt7"], ctx)

`events` are one subject's event-table rows (dicts with `time`, `code`, `numeric_value`, `visit_id`), in event-table
order. Times are ISO text (or seconds from start); an untimed event is a static fact, known from the start.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

_OFFSET = re.compile(r"^\s*(?P<base>[^\s+-]+(?::\S+)?)\s*(?:(?P<sign>[+-])\s*(?P<n>\d+(?:\.\d+)?)\s*(?P<unit>minutes|hours|days))?\s*$")
START, END, MISSING = "START", "END", "MISSING"


def when(t):
    """An event time as a comparable value: a datetime, or seconds from start."""
    if t is None or t == "":
        return None
    if isinstance(t, (int, float)):
        return float(t)
    s = str(t)
    try:
        return datetime.fromisoformat(s.replace(" ", "T"))
    except ValueError:
        return float(s)


def _shift(t, sign: str, n: float, unit: str):
    d = n * {"minutes": 60, "hours": 3600, "days": 86400}[unit] * (-1 if sign == "-" else 1)
    return t + timedelta(seconds=d) if isinstance(t, datetime) else t + d


@dataclass(frozen=True)
class Context:
    events: tuple  # the subject's events
    anchor: object  # the prediction time (None: cross-sectional, everything known counts)
    anchor_event: object  # the anchor event's own time, before `plus`
    visit: str | None  # the anchor event's visit


def match(code: str, pattern: str) -> bool:
    """A pattern starting `^` is a regex; anything else is the code itself."""
    return bool(re.match(pattern, code)) if pattern.startswith("^") else code == pattern


def anchor(events, spec) -> Context | None:
    """The cohort anchor: the first (or last) event with the anchor code, plus its offset."""
    hits = [e for e in events if match(e["code"], spec.event)]
    if not hits:
        return None
    e = hits[0] if spec.pick == "first" else hits[-1]
    t = when(e["time"])
    if t is not None and spec.plus:
        m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*(minutes|hours|days)\s*$", spec.plus)
        t = _shift(t, "+", float(m.group(1)), m.group(2))
    return Context(tuple(events), t, when(e["time"]), e.get("visit_id"))


def at(ref: str | None, ctx: Context, side: str):
    """`any`, `anchor`, `anchor.event` or `visit:<code>`, each with an optional offset."""
    if ref is None or ref.strip() == "any":
        return START if side == "from" else END
    m = _OFFSET.match(ref)
    if not m:
        raise ValueError(f"time '{ref}'")
    base = m.group("base")
    if base == "anchor":
        t = ctx.anchor
    elif base == "anchor.event":
        t = ctx.anchor_event
    elif base.startswith("visit:"):
        code = base[6:]
        t = next((when(e["time"]) for e in ctx.events if e.get("visit_id") == ctx.visit and e["code"] == code), None)
        if t is None:
            return MISSING
    else:
        raise ValueError(f"time '{ref}'")
    if t is None:  # a cross-sectional anchor: everything known counts
        return END
    return _shift(t, m.group("sign"), float(m.group("n")), m.group("unit")) if m.group("n") else t


def window(ctx: Context, rule, codes) -> list | None:
    """Events whose code matches inside [from, to] (ends included unless the rule says not), and in or out of the
    anchor's visit. None when a visit time the window needs is missing."""
    lo, hi = at(rule.from_, ctx, "from"), at(rule.to, ctx, "to")
    if MISSING in (lo, hi):
        return None
    pats = codes if isinstance(codes, (list, tuple)) else [codes]
    out = []
    for e in ctx.events:
        if not any(match(e["code"], p) for p in pats):
            continue
        if getattr(rule, "same_visit", False) and e.get("visit_id") != ctx.visit:
            continue
        if getattr(rule, "other_visit", False) and e.get("visit_id") == ctx.visit:
            continue
        t = when(e["time"])
        if t is None:
            if lo != START:
                continue
        else:
            if lo != START and (t < lo or (t == lo and not rule.include_from)):
                continue
            if hi != END and (t > hi or (t == hi and not rule.include_to)):
                continue
        out.append(e)
    return out


_OPS = {"==": lambda v, x: v == x, ">=": lambda v, x: v >= x, ">": lambda v, x: v > x, "<": lambda v, x: v < x,
        "<=": lambda v, x: v <= x}
_PICK = {"first": lambda vs: vs[0], "last": lambda vs: vs[-1], "min": min, "max": max}


def _plain(rule, ctx: Context):
    if rule.value is not None:
        hits = window(ctx, rule, rule.value)
        if not hits:
            return None
        vals = [e["numeric_value"] for e in hits if e["numeric_value"] is not None]
        if not vals:
            return None
        v = _PICK[rule.pick](vals)
        if rule.bins is not None:
            return sum(1 for edge in rule.bins if v >= edge)
        if rule.op is not None:
            return int(_OPS[rule.op](v, rule.x))
        return v
    hits = window(ctx, rule, rule.exists if rule.exists is not None else rule.none)
    if hits is None:
        return None
    return int(bool(hits)) if rule.exists is not None else int(not hits)


def _case(when_: dict, ctx: Context):
    from medomni.core.contracts.recipe import Label

    return _plain(Label.model_validate({"from": "any", "to": "any", **when_}), ctx)


def label(rule, ctx: Context, hooks=None):
    """The label's value for one subject: a number, 0/1, a class, or None (no value)."""
    if rule.hook is not None:
        if hooks is None or rule.hook not in hooks:
            raise ValueError(f"label hook {rule.hook!r} is not loaded")
        v = hooks[rule.hook](ctx)
    elif rule.cases is not None:
        vals = [(_case(c.when, ctx), c.then) for c in rule.cases]
        if all(v is None for v, _ in vals):
            v = None
        else:
            v = next((then for v, then in vals if v == 1), rule.else_)
    else:
        v = _plain(rule, ctx)
    return rule.default if v is None and rule.default is not None else v
