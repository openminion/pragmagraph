"""Directory-based graph packs for portable PragmaGraph handoffs."""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from pragmagraph.models import GraphSnapshot, PragmaGraphError
from pragmagraph.storage import SQLiteGraphStore, load_snapshot, save_snapshot
from pragmagraph.storage.snapshots import snapshot_to_dict

GRAPH_PACK_SCHEMA_VERSION = "pragmagraph.graph_pack.v1alpha1"
GRAPH_PACK_MANIFEST = "manifest.json"
GRAPH_PACK_SNAPSHOT = "snapshot.json"
GRAPH_PACK_STORE = "graph.sqlite"
GRAPH_PACK_EVIDENCE = "evidence.json"


@dataclass(frozen=True, slots=True)
class GraphPackManifest:
    """Deterministic metadata for one portable graph pack."""

    schema_version: str = GRAPH_PACK_SCHEMA_VERSION
    package: str = "pragmagraph"
    package_version: str = ""
    snapshot_file: str = GRAPH_PACK_SNAPSHOT
    namespace: str = "default"
    node_count: int = 0
    edge_count: int = 0
    omitted_count: int = 0
    includes_store: bool = False
    store_file: str = ""
    includes_evidence: bool = False
    evidence_file: str = ""
    redaction_profile: str = "none"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "GraphPackManifest":
        version = str(payload.get("schema_version", "") or "")
        if version != GRAPH_PACK_SCHEMA_VERSION:
            raise PragmaGraphError(
                "unsupported graph pack manifest schema",
                code="GRAPH_PACK_SCHEMA_UNSUPPORTED",
                details={"expected": GRAPH_PACK_SCHEMA_VERSION, "actual": version},
            )
        return cls(
            schema_version=version,
            package=str(payload.get("package", "") or "pragmagraph"),
            package_version=str(payload.get("package_version", "") or ""),
            snapshot_file=str(payload.get("snapshot_file", "") or GRAPH_PACK_SNAPSHOT),
            namespace=str(payload.get("namespace", "") or "default"),
            node_count=int(payload.get("node_count", 0) or 0),
            edge_count=int(payload.get("edge_count", 0) or 0),
            omitted_count=int(payload.get("omitted_count", 0) or 0),
            includes_store=bool(payload.get("includes_store", False)),
            store_file=str(payload.get("store_file", "") or ""),
            includes_evidence=bool(payload.get("includes_evidence", False)),
            evidence_file=str(payload.get("evidence_file", "") or ""),
            redaction_profile=str(payload.get("redaction_profile", "") or "none"),
        )


def write_graph_pack(
    snapshot: GraphSnapshot,
    pack_dir: str | Path,
    *,
    include_store: bool = False,
    store_path: str | Path | None = None,
    evidence_path: str | Path | None = None,
    redaction_profile: str = "none",
) -> GraphPackManifest:
    """Write a deterministic graph pack directory."""
    target = Path(pack_dir)
    target.mkdir(parents=True, exist_ok=True)
    snapshot_file = target / GRAPH_PACK_SNAPSHOT
    save_snapshot(snapshot, snapshot_file)

    store_file = ""
    if include_store:
        store_file = GRAPH_PACK_STORE
        destination = target / store_file
        if store_path:
            source = Path(store_path)
            if not source.exists():
                raise PragmaGraphError(
                    "store file for graph pack was not found",
                    code="GRAPH_PACK_STORE_NOT_FOUND",
                    details={"path": str(source)},
                )
            shutil.copyfile(source, destination)
        else:
            SQLiteGraphStore.from_snapshot(snapshot, destination)

    evidence_file = ""
    if evidence_path:
        source = Path(evidence_path)
        if not source.exists():
            raise PragmaGraphError(
                "evidence file for graph pack was not found",
                code="GRAPH_PACK_EVIDENCE_NOT_FOUND",
                details={"path": str(source)},
            )
        evidence_file = GRAPH_PACK_EVIDENCE
        _copy_json_stably(source, target / evidence_file)

    manifest = GraphPackManifest(
        package_version=_package_version(),
        namespace=snapshot.namespace,
        node_count=len(snapshot.nodes),
        edge_count=len(snapshot.edges),
        omitted_count=len(snapshot.omitted),
        includes_store=include_store,
        store_file=store_file,
        includes_evidence=bool(evidence_file),
        evidence_file=evidence_file,
        redaction_profile=redaction_profile,
    )
    _write_json(target / GRAPH_PACK_MANIFEST, manifest.to_dict())
    return manifest


def inspect_graph_pack(pack_dir: str | Path) -> GraphPackManifest:
    """Load only the manifest for a graph pack directory."""
    manifest_path = Path(pack_dir) / GRAPH_PACK_MANIFEST
    if not manifest_path.exists():
        raise PragmaGraphError(
            "graph pack manifest was not found",
            code="GRAPH_PACK_MANIFEST_NOT_FOUND",
            details={"path": str(manifest_path)},
        )
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise PragmaGraphError(
            "graph pack manifest must be a JSON object",
            code="GRAPH_PACK_MANIFEST_INVALID",
            details={"path": str(manifest_path)},
        )
    return GraphPackManifest.from_dict(payload)


def load_graph_pack_snapshot(pack_dir: str | Path) -> GraphSnapshot:
    """Load the canonical snapshot from a graph pack directory."""
    manifest = inspect_graph_pack(pack_dir)
    return load_snapshot(Path(pack_dir) / manifest.snapshot_file)


def import_graph_pack(
    pack_dir: str | Path,
    *,
    snapshot_out: str | Path | None = None,
    store_out: str | Path | None = None,
) -> dict[str, object]:
    """Import graph-pack contents into explicit caller-selected output paths."""
    root = Path(pack_dir)
    manifest = inspect_graph_pack(root)
    snapshot = load_snapshot(root / manifest.snapshot_file)
    payload: dict[str, object] = {
        "manifest": manifest.to_dict(),
        "snapshot": snapshot_to_dict(snapshot),
    }
    if snapshot_out:
        payload["snapshot_output_path"] = str(save_snapshot(snapshot, snapshot_out))
    if store_out:
        if manifest.includes_store and manifest.store_file:
            source = root / manifest.store_file
            if not source.exists():
                raise PragmaGraphError(
                    "graph pack store file was not found",
                    code="GRAPH_PACK_STORE_NOT_FOUND",
                    details={"path": str(source)},
                )
            destination = Path(store_out)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        else:
            SQLiteGraphStore.from_snapshot(snapshot, store_out)
        payload["store_output_path"] = str(store_out)
    return payload


def _copy_json_stably(source: Path, destination: Path) -> None:
    payload = json.loads(source.read_text(encoding="utf-8"))
    _write_json(destination, payload)


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _package_version() -> str:
    import pragmagraph

    return pragmagraph.__version__


__all__ = [
    "GRAPH_PACK_EVIDENCE",
    "GRAPH_PACK_MANIFEST",
    "GRAPH_PACK_SCHEMA_VERSION",
    "GRAPH_PACK_SNAPSHOT",
    "GRAPH_PACK_STORE",
    "GraphPackManifest",
    "import_graph_pack",
    "inspect_graph_pack",
    "load_graph_pack_snapshot",
    "write_graph_pack",
]
