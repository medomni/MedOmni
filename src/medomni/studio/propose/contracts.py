"""Studio's propose contract: one proposed task and its review state (R-147)."""
from __future__ import annotations

from typing import Any, Literal

from medomni.core.contracts.base import Contract, NonEmpty, Slug


class TaskProposal(Contract):
    """One proposed task and its review state (Studio). The draft becomes a frozen template when signed off."""

    title: NonEmpty
    by: NonEmpty
    org: str | None = None
    at: NonEmpty
    mode: NonEmpty
    state: Literal["draft", "under-review", "signed-off", "frozen"]
    dataset: Slug | None = None
    draft: dict[str, Any] = {}
