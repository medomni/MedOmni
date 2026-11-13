"""Paths and the catalogue the gateway and registry tests share."""
from functools import cache
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ENCODERS = REPO / "perception" / "encoders"


@cache
def shipped():
    """The 44 encoders v0.3.0 ships (R-63). The other 22 v0.2 folders stay in the tree until part 8 deletes them."""
    from tests.repro.migrate import cards

    return tuple(cards.shipped(REPO))


def shipped_catalog():
    from medomni.perception.gateway.catalog import Catalog

    return Catalog.load(ENCODERS, ids=shipped())
