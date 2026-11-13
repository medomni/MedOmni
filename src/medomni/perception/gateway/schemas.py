"""Response models for the routes. The request is Core's `EncodeRequest` (gateway API contract)."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class OutputBlock(BaseModel):
    kind: Optional[str] = None
    scale: Optional[str] = None
    dim: Optional[int] = None
    n_labels: Optional[int] = None


class EncoderSummary(BaseModel):
    id: str
    family: Optional[str] = None
    modality: Optional[str] = None
    summary: str = ""
    outputs: List[OutputBlock] = []
    runnable: bool = False
    reliability: Optional[str] = None
    acceptance: Optional[str] = None
    license: Optional[str] = None
    score: Optional[float] = Field(None, description="Match score for q, 0..1.")


class FamilyRow(BaseModel):
    family: Optional[str] = None
    encoders: int = 0
    runnable: int = 0


class PoolSlot(BaseModel):
    encoder_id: str
    state: str
    inflight: int
    concurrency: int
    idle_s: Optional[float] = None
    started_at: Optional[float] = None
    url: Optional[str] = None
    image_id: Optional[str] = None
    adopted: Optional[bool] = None


class PoolStatus(BaseModel):
    max_live_containers: int
    idle_timeout_s: float
    live: List[PoolSlot]
    cache: Dict[str, Any]
    call_log_failures: int = 0


class Health(BaseModel):
    ok: bool
    encoders: int
    live: int
    data_root: Optional[str] = None


class Ready(BaseModel):
    """Whether this gateway can actually run an encoder, not merely answer."""
    ready: bool
    docker: bool
    data_root_ok: bool
    reasons: List[str] = []
