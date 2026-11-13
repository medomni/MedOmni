"""The audit's Encoder cells: each card against its contract and its folder. No container or gateway is started, so
the live-service checks stay unassessed (v0.2's were the same offline)."""
from __future__ import annotations

from ... import common
from ..matrix import FAIL, NONE, PASS, WARN


def run(scope, sink) -> None:
    from medomni.core.contracts import ContractError, ModelCard, load

    for edir in scope.encoders:
        eid = common.encoder_id(edir)
        try:
            card = load(edir / "card.yaml", ModelCard)
        except ContractError as e:
            sink.add("P-COMP.1", "M", eid, FAIL, str(e), "card")
            continue
        adapter = (edir / "adapter.py").is_file()
        source_ok = card.source is None or bool(getattr(card.source, "rev", None)) or card.weights is None
        sink.add("P-COMP.1", "M", eid, PASS if adapter and source_ok else FAIL,
                 "card, source and adapter present" if adapter and source_ok else "no adapter.py" if not adapter else "weighted model without a source revision",
                 "encoder folder")
        missing = [f for f in ("Dockerfile", "testdata/expected.json") if not (edir / f).is_file()]
        sink.add("P-COMP.2", "M", eid, PASS if not missing else FAIL, f"missing: {missing}" if missing else "image recipe and expected output present", "encoder folder")
        ok = eid == card.id and card.family in scope.families
        sink.add("P-CONF.1", "M", eid, PASS if ok else FAIL, "card id and family match" if ok else f"card id or family mismatch: {card.id}, {card.family}", "card")
        sink.add("P-CONF.4", "M", eid, PASS if card.acceptance == "accepted" else WARN, f"acceptance: {card.acceptance}", "card")
        sink.add("P-ISOL.3", "M", eid, PASS if card.non_training else NONE,
                 "non-training by its card" if card.non_training else "trained on outside data: needs the LLM or human review", "card")
        limits = bool(card.limits)
        sink.add("P-COMP.2", "M", eid, PASS if limits else WARN, f"{len(card.limits)} limits declared" if limits else "card declares no limits", "limits")
