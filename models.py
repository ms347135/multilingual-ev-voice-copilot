from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class QueryAnalysis:
    language: str
    intent: str
    vehicle_model: str
    doc_type_preferences: list[str] = field(default_factory=list)
    uses_vehicle_state: bool = False
    mode_used: str = "docs_only"


@dataclass
class RetrievedHit:
    text: str
    score: float
    rerank_score: float
    metadata: dict
