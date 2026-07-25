"""Observed-fact evidence payloads for the local PragmaGraph workbench."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pragmagraph.models import GraphSnapshot, QueryRequest
from pragmagraph.query import query
from pragmagraph.service import LocalQueryService
from pragmagraph.storage import (
    SQLiteGraphStore,
    explain_store_query,
    verify_existing_store_round_trip,
)

from .preview_types import UiPreviewRequest

EVIDENCE_SCHEMA_VERSION = "pragmagraph.evidence_workbench.v1alpha1"
AGENT_CONTEXT_SCHEMA_VERSION = "pragmagraph.agent_context.v1alpha1"


def build_evidence_payload(
    snapshot: GraphSnapshot,
    request: UiPreviewRequest,
) -> dict[str, Any]:
    """Build one inspectable evidence payload for UI and doctor surfaces."""
    query_result = query(snapshot, QueryRequest(query=request.query, max_results=5))
    search_explanation = _search_explanation(snapshot, request)
    store_round_trip = _store_round_trip(snapshot, request)
    service_status = _service_status(request)
    agent_context = _agent_context(
        snapshot,
        request,
        query_result=query_result.to_dict(),
        search_explanation=search_explanation,
        store_round_trip=store_round_trip,
        service_status=service_status,
    )
    return {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "boundary": "observed_facts_only",
        "screen": request.screen,
        "query": request.query,
        "snapshot": {
            "namespace": snapshot.namespace,
            "root_path": snapshot.root_path,
            "schema_version": snapshot.schema_version,
            "indexer_version": snapshot.indexer_version,
            "node_count": len(snapshot.nodes),
            "edge_count": len(snapshot.edges),
            "omitted_count": len(snapshot.omitted),
        },
        "service_status": service_status,
        "query_result": query_result.to_dict(),
        "search_explanation": search_explanation,
        "store_round_trip": store_round_trip,
        "agent_context": agent_context,
    }


def write_evidence_payload(payload: dict[str, Any], path: str | Path) -> Path:
    """Write evidence JSON deterministically."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_stable_json(payload), encoding="utf-8")
    return target


def write_agent_context(payload: dict[str, Any], path: str | Path) -> Path:
    """Write a compact Markdown handoff for an agent or operator."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_agent_context(payload), encoding="utf-8")
    return target


def render_agent_context(payload: dict[str, Any]) -> str:
    """Render a compact observed-fact context handoff."""
    query_payload = _dict(payload.get("query_result"))
    hits = [
        item
        for item in query_payload.get("hits", [])
        if isinstance(item, dict) and isinstance(item.get("node"), dict)
    ]
    graph_line = (
        f"- graph: {_dict(payload.get('snapshot')).get('node_count', 0)} nodes, "
        f"{_dict(payload.get('snapshot')).get('edge_count', 0)} edges"
    )
    lines = [
        "# PragmaGraph Agent Context",
        "",
        f"- boundary: `{payload.get('boundary', 'observed_facts_only')}`",
        f"- query: `{payload.get('query', '')}`",
        f"- namespace: `{_dict(payload.get('snapshot')).get('namespace', '')}`",
        graph_line,
        "",
        "## Top Hits",
    ]
    if not hits:
        lines.append("- none")
    for hit in hits[:5]:
        node = _dict(hit.get("node"))
        source_ref = _dict(node.get("source_ref"))
        location = source_ref.get("path", "")
        line = source_ref.get("line", "")
        suffix = f":{line}" if line else ""
        lines.append(
            f"- `{node.get('id', '')}` {node.get('label', '')} "
            f"({node.get('kind', '')}) - {location}{suffix}"
        )
    search = _dict(payload.get("search_explanation"))
    store = _dict(payload.get("store_round_trip"))
    lines.extend(
        [
            "",
            "## Search Evidence",
            f"- mode: `{search.get('mode', '')}`",
            f"- strategy: `{search.get('strategy', '')}`",
            f"- hit_count: `{search.get('hit_count', 0)}`",
            f"- candidate_count: `{search.get('candidate_count', 0)}`",
            "",
            "## Store Proof",
            f"- status: `{store.get('status', '')}`",
            f"- ok: `{store.get('ok', False)}`",
            f"- store_path: `{store.get('store_path', '')}`",
            "",
        ]
    )
    return "\n".join(lines)


def _search_explanation(
    snapshot: GraphSnapshot,
    request: UiPreviewRequest,
) -> dict[str, Any]:
    store = _readable_store(request.store_path)
    if store is not None:
        payload = explain_store_query(
            store, QueryRequest(query=request.query)
        ).to_dict()
        payload["mode"] = "materialized_store"
        return payload
    result = query(snapshot, QueryRequest(query=request.query, max_results=5))
    return {
        "mode": "canonical_snapshot",
        "backend": "json",
        "query": request.query,
        "strategy": "canonical_scorer",
        "fts_available": False,
        "candidate_count": len(snapshot.nodes),
        "hit_count": len(result.hits),
        "candidate_node_ids": [hit.node.id for hit in result.hits],
        "omitted_reasons": [item.reason for item in result.omitted],
        "reproducible_command": [
            "pragmagraph",
            "query",
            request.snapshot or "<snapshot.json>",
            request.query,
            "--json",
        ],
        "result": result.to_dict(),
    }


def _store_round_trip(
    snapshot: GraphSnapshot,
    request: UiPreviewRequest,
) -> dict[str, Any]:
    store_path = request.store_path or ""
    if not store_path:
        return {
            "status": "not_requested",
            "ok": False,
            "reason": "store_path_not_provided",
        }
    if not Path(store_path).exists():
        return {
            "status": "unavailable",
            "ok": False,
            "store_path": store_path,
            "reason": "store_path_not_found",
        }
    report = verify_existing_store_round_trip(
        snapshot,
        store_path,
        query_text=request.query,
    ).to_dict()
    return {"status": "checked", **report}


def _agent_context(
    snapshot: GraphSnapshot,
    request: UiPreviewRequest,
    *,
    query_result: dict[str, Any],
    search_explanation: dict[str, Any],
    store_round_trip: dict[str, Any],
    service_status: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": AGENT_CONTEXT_SCHEMA_VERSION,
        "boundary": "observed_facts_only",
        "query": request.query,
        "snapshot": {
            "namespace": snapshot.namespace,
            "root_path": snapshot.root_path,
            "node_count": len(snapshot.nodes),
            "edge_count": len(snapshot.edges),
            "omitted_count": len(snapshot.omitted),
        },
        "top_hits": _top_hits(query_result),
        "search_evidence": {
            "mode": search_explanation.get("mode", ""),
            "strategy": search_explanation.get("strategy", ""),
            "candidate_count": search_explanation.get("candidate_count", 0),
            "hit_count": search_explanation.get("hit_count", 0),
            "omitted_reasons": search_explanation.get("omitted_reasons", []),
        },
        "store_proof": {
            "status": store_round_trip.get("status", ""),
            "ok": store_round_trip.get("ok", False),
            "mode": store_round_trip.get("mode", ""),
            "store_path": store_round_trip.get("store_path", ""),
        },
        "service": {
            "startup_mode": service_status.get("startup_mode", ""),
            "refresh_supported": service_status.get("refresh_supported", False),
            "refresh_readiness": service_status.get("refresh_readiness", {}),
        },
        "reproducible_commands": _reproducible_commands(request),
    }


def _top_hits(query_result: dict[str, Any]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for item in query_result.get("hits", []):
        if not isinstance(item, dict) or not isinstance(item.get("node"), dict):
            continue
        node = item["node"]
        source_ref = _dict(node.get("source_ref"))
        hits.append(
            {
                "node_id": node.get("id", ""),
                "label": node.get("label", ""),
                "kind": node.get("kind", ""),
                "source_path": source_ref.get("path", ""),
                "source_line": source_ref.get("line", 0),
                "score": item.get("score", 0),
            }
        )
    return hits[:5]


def _reproducible_commands(request: UiPreviewRequest) -> list[list[str]]:
    commands: list[list[str]] = []
    if request.snapshot:
        commands.append(
            ["pragmagraph", "query", request.snapshot, request.query, "--json"]
        )
    if request.store_path:
        commands.append(
            [
                "pragmagraph",
                "store-search-explain",
                request.store_path,
                request.query,
                "--json",
            ]
        )
    if request.workspace:
        commands.append(
            [
                "pragmagraph-ui",
                "--workspace",
                request.workspace,
                "--screen",
                "evidence",
                "--serve",
            ]
        )
    return commands


def _service_status(request: UiPreviewRequest) -> dict[str, Any]:
    service = None
    if request.workspace:
        service = LocalQueryService.from_workspace(request.workspace)
    elif request.snapshot:
        service = LocalQueryService.from_snapshot_path(request.snapshot)
    elif request.store_path and Path(request.store_path).exists():
        service = LocalQueryService.from_store_path(request.store_path)
    return service.status().to_dict() if service is not None else {}


def _readable_store(store_path: str | None) -> SQLiteGraphStore | None:
    if not store_path or not Path(store_path).exists():
        return None
    return SQLiteGraphStore(store_path)


def _stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


__all__ = [
    "AGENT_CONTEXT_SCHEMA_VERSION",
    "EVIDENCE_SCHEMA_VERSION",
    "build_evidence_payload",
    "render_agent_context",
    "write_agent_context",
    "write_evidence_payload",
]
