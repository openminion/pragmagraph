"""Directory-based graph packs for portable PragmaGraph handoffs."""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

from pragmagraph.models import GraphSnapshot, PragmaGraphError
from pragmagraph.storage import (
    SQLiteGraphStore,
    load_snapshot,
    save_snapshot,
    stable_dumps,
)
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
    snapshot_sha256: str = ""
    store_sha256: str = ""
    evidence_sha256: str = ""
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
            snapshot_sha256=str(payload.get("snapshot_sha256", "") or ""),
            store_sha256=str(payload.get("store_sha256", "") or ""),
            evidence_sha256=str(payload.get("evidence_sha256", "") or ""),
            redaction_profile=str(payload.get("redaction_profile", "") or "none"),
        )


@dataclass(frozen=True, slots=True)
class GraphPackVerification:
    """Observed consistency facts for one graph pack."""

    ok: bool
    manifest: GraphPackManifest
    snapshot_ok: bool
    counts_match: bool
    checksums_match: bool
    store_ok: bool
    evidence_ok: bool
    diagnostics: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "manifest": self.manifest.to_dict(),
            "snapshot_ok": self.snapshot_ok,
            "counts_match": self.counts_match,
            "checksums_match": self.checksums_match,
            "store_ok": self.store_ok,
            "evidence_ok": self.evidence_ok,
            "diagnostics": list(self.diagnostics),
        }


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
    store_hash = ""
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
        store_hash = _file_sha256(destination)

    evidence_file = ""
    evidence_hash = ""
    if evidence_path:
        source = Path(evidence_path)
        if not source.exists():
            raise PragmaGraphError(
                "evidence file for graph pack was not found",
                code="GRAPH_PACK_EVIDENCE_NOT_FOUND",
                details={"path": str(source)},
            )
        evidence_file = GRAPH_PACK_EVIDENCE
        evidence_destination = target / evidence_file
        _copy_json_stably(source, evidence_destination)
        evidence_hash = _file_sha256(evidence_destination)

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
        snapshot_sha256=_file_sha256(snapshot_file),
        store_sha256=store_hash,
        evidence_sha256=evidence_hash,
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


def verify_graph_pack(pack_dir: str | Path) -> GraphPackVerification:
    """Verify graph-pack consistency without mutating its contents."""
    root = Path(pack_dir)
    manifest = inspect_graph_pack(root)
    diagnostics: list[str] = []

    snapshot_ok = False
    counts_match = False
    checksums_match = False
    store_ok = not manifest.includes_store
    evidence_ok = not manifest.includes_evidence

    try:
        snapshot_path = root / manifest.snapshot_file
        snapshot = load_snapshot(snapshot_path)
        snapshot_ok = True
        counts_match = _snapshot_counts_match(snapshot, manifest)
        if not counts_match:
            diagnostics.append("manifest_counts_do_not_match_snapshot")
        checksums_match = _checksums_match(root, manifest, diagnostics)
        if manifest.includes_store:
            store_ok = _store_matches_snapshot(root, manifest, snapshot, diagnostics)
    except PragmaGraphError as exc:
        diagnostics.append(exc.code.lower())
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        diagnostics.append(type(exc).__name__.lower())

    if manifest.includes_evidence:
        evidence_ok = _evidence_json_is_readable(root, manifest, diagnostics)

    return GraphPackVerification(
        ok=snapshot_ok
        and counts_match
        and checksums_match
        and store_ok
        and evidence_ok,
        manifest=manifest,
        snapshot_ok=snapshot_ok,
        counts_match=counts_match,
        checksums_match=checksums_match,
        store_ok=store_ok,
        evidence_ok=evidence_ok,
        diagnostics=tuple(diagnostics),
    )


def _snapshot_counts_match(
    snapshot: GraphSnapshot,
    manifest: GraphPackManifest,
) -> bool:
    return (
        len(snapshot.nodes) == manifest.node_count
        and len(snapshot.edges) == manifest.edge_count
        and len(snapshot.omitted) == manifest.omitted_count
        and snapshot.namespace == manifest.namespace
    )


def _store_matches_snapshot(
    root: Path,
    manifest: GraphPackManifest,
    snapshot: GraphSnapshot,
    diagnostics: list[str],
) -> bool:
    if not manifest.store_file:
        diagnostics.append("manifest_missing_store_file")
        return False
    store_path = root / manifest.store_file
    if not store_path.exists():
        diagnostics.append("store_file_not_found")
        return False
    try:
        exported = SQLiteGraphStore(store_path).export_snapshot()
    except PragmaGraphError as exc:
        diagnostics.append(exc.code.lower())
        return False
    if stable_dumps(exported) != stable_dumps(snapshot):
        diagnostics.append("store_export_does_not_match_snapshot")
        return False
    return True


def _checksums_match(
    root: Path,
    manifest: GraphPackManifest,
    diagnostics: list[str],
) -> bool:
    expected = {
        manifest.snapshot_file: manifest.snapshot_sha256,
        manifest.store_file: manifest.store_sha256,
        manifest.evidence_file: manifest.evidence_sha256,
    }
    ok = True
    for relative_path, expected_hash in expected.items():
        if not relative_path or not expected_hash:
            continue
        path = root / relative_path
        if not path.exists():
            diagnostics.append(f"{relative_path}_checksum_file_not_found")
            ok = False
        elif _file_sha256(path) != expected_hash:
            diagnostics.append(f"{relative_path}_checksum_mismatch")
            ok = False
    return ok


def _evidence_json_is_readable(
    root: Path,
    manifest: GraphPackManifest,
    diagnostics: list[str],
) -> bool:
    if not manifest.evidence_file:
        diagnostics.append("manifest_missing_evidence_file")
        return False
    evidence_path = root / manifest.evidence_file
    if not evidence_path.exists():
        diagnostics.append("evidence_file_not_found")
        return False
    try:
        json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        diagnostics.append(type(exc).__name__.lower())
        return False
    return True


def _copy_json_stably(source: Path, destination: Path) -> None:
    payload = json.loads(source.read_text(encoding="utf-8"))
    _write_json(destination, payload)


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    "GraphPackVerification",
    "import_graph_pack",
    "inspect_graph_pack",
    "load_graph_pack_snapshot",
    "verify_graph_pack",
    "write_graph_pack",
]
