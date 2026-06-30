"""Query-plan evidence for deterministic PragmaGraph search."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from pragmagraph._immutables import frozen_mapping
from pragmagraph.models import GraphSnapshot, QueryRequest
from pragmagraph.query import query


@dataclass(frozen=True)
class QueryPlanEvidence:
    """Observed execution facts for one deterministic query call."""

    query: str
    strategy: str
    candidate_count: int
    returned_count: int
    omitted_count: int
    max_results: int
    include_edges: bool
    completeness: str
    filters: Mapping[str, Any] = field(default_factory=dict)
    omitted_reasons: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "filters", frozen_mapping(self.filters))
        object.__setattr__(
            self, "omitted_reasons", frozen_mapping(self.omitted_reasons)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "strategy": self.strategy,
            "candidate_count": self.candidate_count,
            "returned_count": self.returned_count,
            "omitted_count": self.omitted_count,
            "max_results": self.max_results,
            "include_edges": self.include_edges,
            "completeness": self.completeness,
            "filters": dict(self.filters),
            "omitted_reasons": dict(self.omitted_reasons),
        }


def explain_query_plan(
    snapshot: GraphSnapshot,
    request: QueryRequest | str,
) -> QueryPlanEvidence:
    """Return structural execution evidence for a deterministic query."""
    req = request if isinstance(request, QueryRequest) else QueryRequest(query=request)
    result = query(snapshot, req)
    omitted_reasons: dict[str, int] = {}
    for item in result.omitted:
        omitted_reasons[item.reason] = omitted_reasons.get(item.reason, 0) + 1
    omitted_count = sum(
        int(item.details.get("omitted", 1) or 1) for item in result.omitted
    )
    return QueryPlanEvidence(
        query=req.query,
        strategy="lexical_structural",
        candidate_count=int(result.diagnostics.get("candidate_count", 0) or 0),
        returned_count=len(result.hits),
        omitted_count=omitted_count,
        max_results=req.max_results,
        include_edges=req.include_edges,
        completeness="truncated" if result.omitted else "complete",
        filters={
            "node_ids": list(req.node_ids),
        },
        omitted_reasons=omitted_reasons,
    )


__all__ = ["QueryPlanEvidence", "explain_query_plan"]
