"""Read-only MCP resources over one loaded PragmaGraph service."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Mapping
from urllib.parse import unquote, urlparse

from pragmagraph.report import build_report
from pragmagraph.service import LocalQueryService

RESOURCE_STATUS = "pragma://status"
RESOURCE_SNAPSHOT = "pragma://snapshot"
RESOURCE_REPORT = "pragma://report"
RESOURCE_PRECISE_INGESTION = "pragma://precise-ingestion"
RESOURCE_NODE_TEMPLATE = "pragma://node/{node_id}"


@dataclass(frozen=True)
class ResourceDescriptor:
    uri: str
    name: str
    description: str
    mime_type: str = "application/json"

    def to_dict(self) -> dict[str, str]:
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type,
        }


class ResourceRegistry:
    """Bounded resource registry backed by one already-loaded service."""

    def __init__(self, service: LocalQueryService) -> None:
        self._service = service

    def list_resources(self) -> tuple[ResourceDescriptor, ...]:
        return (
            ResourceDescriptor(
                RESOURCE_STATUS,
                "PragmaGraph status",
                "Loaded service capabilities and health posture.",
            ),
            ResourceDescriptor(
                RESOURCE_SNAPSHOT,
                "PragmaGraph snapshot",
                "Canonical observed-fact snapshot.",
            ),
            ResourceDescriptor(
                RESOURCE_REPORT,
                "PragmaGraph report",
                "Deterministic structural report.",
            ),
            ResourceDescriptor(
                RESOURCE_PRECISE_INGESTION,
                "PragmaGraph precise ingestion",
                "Loaded external precise-index provenance and loss report.",
            ),
        )

    def list_templates(self) -> tuple[dict[str, str], ...]:
        return (
            {
                "uriTemplate": RESOURCE_NODE_TEMPLATE,
                "name": "PragmaGraph node",
                "description": "One observed node addressed by canonical node ID.",
                "mimeType": "application/json",
            },
        )

    def read(self, uri: str) -> dict[str, object]:
        parsed = urlparse(uri)
        if parsed.scheme != "pragma":
            raise ValueError("resource URI must use the pragma scheme")
        if uri == RESOURCE_STATUS:
            payload = {
                "status": self._service.status().to_dict(),
                "capabilities": self._service.capabilities().to_dict(),
                "snapshot_stats": dict(self._service.snapshot.stats),
            }
        elif uri == RESOURCE_SNAPSHOT:
            payload = self._service.snapshot.to_dict()
        elif uri == RESOURCE_REPORT:
            payload = build_report(self._service.snapshot).to_dict()
        elif uri == RESOURCE_PRECISE_INGESTION:
            report = self._service.snapshot.stats.get("precise_ingestion", {})
            payload = {
                "loaded": bool(report),
                "report": dict(report) if isinstance(report, Mapping) else {},
            }
        elif parsed.netloc == "node" and parsed.path.strip("/"):
            node_id = unquote(parsed.path.strip("/"))
            node = self._service.snapshot.node_map().get(node_id)
            if node is None:
                raise ValueError(f"resource node {node_id!r} was not found")
            payload = node.to_dict()
        else:
            raise ValueError(f"unsupported resource URI {uri!r}")
        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": json.dumps(payload, sort_keys=True),
                }
            ]
        }


__all__ = [
    "RESOURCE_NODE_TEMPLATE",
    "RESOURCE_PRECISE_INGESTION",
    "RESOURCE_REPORT",
    "RESOURCE_SNAPSHOT",
    "RESOURCE_STATUS",
    "ResourceDescriptor",
    "ResourceRegistry",
]
