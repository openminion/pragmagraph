"""Explicit refresh and ingest operation helpers for PragmaGraph."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Mapping

from pragmagraph.adapters.git_history import DEFAULT_GIT_IDENTITY_MODE
from pragmagraph.models import (
    GraphSnapshot,
    PragmaGraphError,
    RefreshManifest,
    RefreshPathChange,
    RefreshResult,
)
from pragmagraph.incremental import load_extraction_cache, save_extraction_cache
from pragmagraph.refresh import (
    build_manifest,
    describe_manifest_changes,
    load_manifest,
    refresh_snapshot,
    refresh_snapshot_incremental,
    save_manifest,
)
from pragmagraph.storage import load_snapshot, save_snapshot, stable_dumps

_STATUS_SCHEMA_VERSION = "pragmagraph.refresh_status.v1alpha1"
_PROFILE_SCHEMA_VERSION = "pragmagraph.refresh_profile.v1alpha1"


def _stable_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(dict(payload), indent=2, sort_keys=True) + "\n"


def _snapshot_id(snapshot: GraphSnapshot) -> str:
    import hashlib

    return hashlib.sha256(stable_dumps(snapshot).encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class RefreshProfile:
    """Saved explicit-refresh invocation profile for one local root."""

    label: str
    root_path: str
    namespace: str = "default"
    snapshot_path: str = ""
    manifest_path: str = ""
    state_path: str = ""
    cache_path: str = ""
    git_identity_mode: str = DEFAULT_GIT_IDENTITY_MODE
    schema_version: str = _PROFILE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.label:
            raise PragmaGraphError(
                "refresh profile label is required",
                code="INVALID_REFRESH_PROFILE",
            )
        if not self.root_path:
            raise PragmaGraphError(
                "refresh profile root_path is required",
                code="INVALID_REFRESH_PROFILE",
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "label": self.label,
            "root_path": self.root_path,
            "namespace": self.namespace,
            "snapshot_path": self.snapshot_path,
            "manifest_path": self.manifest_path,
            "state_path": self.state_path,
            "cache_path": self.cache_path,
            "git_identity_mode": self.git_identity_mode,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RefreshProfile":
        return cls(
            schema_version=str(
                payload.get("schema_version", "") or _PROFILE_SCHEMA_VERSION
            ),
            label=str(payload.get("label", "") or ""),
            root_path=str(payload.get("root_path", "") or ""),
            namespace=str(payload.get("namespace", "") or "default"),
            snapshot_path=str(payload.get("snapshot_path", "") or ""),
            manifest_path=str(payload.get("manifest_path", "") or ""),
            state_path=str(payload.get("state_path", "") or ""),
            cache_path=str(payload.get("cache_path", "") or ""),
            git_identity_mode=str(
                payload.get("git_identity_mode", "") or DEFAULT_GIT_IDENTITY_MODE
            ),
        )


@dataclass(frozen=True)
class RefreshPlan:
    """Preview of what one explicit refresh would touch."""

    root_path: str
    namespace: str
    previous_manifest_present: bool
    changed_paths: tuple[str, ...] = ()
    unchanged_paths: tuple[str, ...] = ()
    removed_paths: tuple[str, ...] = ()
    path_changes: tuple[RefreshPathChange, ...] = ()
    parser_set: tuple[str, ...] = ()
    manifest_entry_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "root_path": self.root_path,
            "namespace": self.namespace,
            "previous_manifest_present": self.previous_manifest_present,
            "changed_paths": list(self.changed_paths),
            "unchanged_paths": list(self.unchanged_paths),
            "removed_paths": list(self.removed_paths),
            "path_changes": [item.to_dict() for item in self.path_changes],
            "parser_set": list(self.parser_set),
            "manifest_entry_count": self.manifest_entry_count,
        }


@dataclass(frozen=True)
class RefreshStatus:
    """Persistent status facts about the last explicit refresh attempts."""

    root_path: str
    namespace: str
    status: str
    snapshot_path: str = ""
    manifest_path: str = ""
    last_attempt_at: str = ""
    last_success_at: str = ""
    last_failure_at: str = ""
    last_error_code: str = ""
    last_error_message: str = ""
    git_identity_mode: str = DEFAULT_GIT_IDENTITY_MODE
    snapshot_id: str = ""
    changed_path_count: int = 0
    unchanged_path_count: int = 0
    removed_path_count: int = 0
    added_node_count: int = 0
    removed_node_count: int = 0
    added_edge_count: int = 0
    removed_edge_count: int = 0
    added_omitted_count: int = 0
    removed_omitted_count: int = 0
    manifest_entry_count: int = 0
    omitted_reason_counts: Mapping[str, int] = field(default_factory=dict)
    parser_set: tuple[str, ...] = ()
    schema_version: str = _STATUS_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "omitted_reason_counts",
            {str(key): int(value) for key, value in self.omitted_reason_counts.items()},
        )
        object.__setattr__(
            self,
            "parser_set",
            tuple(str(item) for item in self.parser_set),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "root_path": self.root_path,
            "namespace": self.namespace,
            "status": self.status,
            "snapshot_path": self.snapshot_path,
            "manifest_path": self.manifest_path,
            "last_attempt_at": self.last_attempt_at,
            "last_success_at": self.last_success_at,
            "last_failure_at": self.last_failure_at,
            "last_error_code": self.last_error_code,
            "last_error_message": self.last_error_message,
            "git_identity_mode": self.git_identity_mode,
            "snapshot_id": self.snapshot_id,
            "changed_path_count": self.changed_path_count,
            "unchanged_path_count": self.unchanged_path_count,
            "removed_path_count": self.removed_path_count,
            "added_node_count": self.added_node_count,
            "removed_node_count": self.removed_node_count,
            "added_edge_count": self.added_edge_count,
            "removed_edge_count": self.removed_edge_count,
            "added_omitted_count": self.added_omitted_count,
            "removed_omitted_count": self.removed_omitted_count,
            "manifest_entry_count": self.manifest_entry_count,
            "omitted_reason_counts": dict(self.omitted_reason_counts),
            "parser_set": list(self.parser_set),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RefreshStatus":
        return cls(
            schema_version=str(
                payload.get("schema_version", "") or _STATUS_SCHEMA_VERSION
            ),
            root_path=str(payload.get("root_path", "") or ""),
            namespace=str(payload.get("namespace", "") or "default"),
            status=str(payload.get("status", "") or ""),
            snapshot_path=str(payload.get("snapshot_path", "") or ""),
            manifest_path=str(payload.get("manifest_path", "") or ""),
            last_attempt_at=str(payload.get("last_attempt_at", "") or ""),
            last_success_at=str(payload.get("last_success_at", "") or ""),
            last_failure_at=str(payload.get("last_failure_at", "") or ""),
            last_error_code=str(payload.get("last_error_code", "") or ""),
            last_error_message=str(payload.get("last_error_message", "") or ""),
            git_identity_mode=str(
                payload.get("git_identity_mode", "") or DEFAULT_GIT_IDENTITY_MODE
            ),
            snapshot_id=str(payload.get("snapshot_id", "") or ""),
            changed_path_count=int(payload.get("changed_path_count", 0) or 0),
            unchanged_path_count=int(payload.get("unchanged_path_count", 0) or 0),
            removed_path_count=int(payload.get("removed_path_count", 0) or 0),
            added_node_count=int(payload.get("added_node_count", 0) or 0),
            removed_node_count=int(payload.get("removed_node_count", 0) or 0),
            added_edge_count=int(payload.get("added_edge_count", 0) or 0),
            removed_edge_count=int(payload.get("removed_edge_count", 0) or 0),
            added_omitted_count=int(payload.get("added_omitted_count", 0) or 0),
            removed_omitted_count=int(payload.get("removed_omitted_count", 0) or 0),
            manifest_entry_count=int(payload.get("manifest_entry_count", 0) or 0),
            omitted_reason_counts={
                str(key): int(value)
                for key, value in dict(
                    payload.get("omitted_reason_counts", {}) or {}
                ).items()
            },
            parser_set=tuple(str(item) for item in payload.get("parser_set", ()) or ()),
        )


@dataclass(frozen=True)
class RefreshOperationResult:
    """Result of one explicit refresh run plus persisted status facts."""

    result: RefreshResult
    status: RefreshStatus

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.to_dict(),
            "changed_paths": list(self.result.changed_paths),
            "unchanged_paths": list(self.result.unchanged_paths),
            "removed_paths": list(self.result.removed_paths),
            "path_changes": [item.to_dict() for item in self.result.path_changes],
            "snapshot_delta": self.result.snapshot_delta.to_dict(),
            "identity_transitions": [
                item.to_dict() for item in self.result.identity_transitions
            ],
            "work": self.result.work.to_dict(),
        }


def build_refresh_plan(
    root_path: str | Path,
    *,
    namespace: str = "default",
    previous_manifest: RefreshManifest | None = None,
) -> RefreshPlan:
    """Return a deterministic preview of refresh-visible path changes."""
    manifest = build_manifest(root_path)
    previous = previous_manifest or RefreshManifest()
    path_changes = describe_manifest_changes(previous, manifest)
    changed_paths = tuple(
        item.path
        for item in path_changes
        if item.status in {"added", "removed", "changed"}
    )
    unchanged_paths = tuple(
        item.path for item in path_changes if item.status == "unchanged"
    )
    removed_paths = tuple(
        item.path for item in path_changes if item.status == "removed"
    )
    parser_set = tuple(sorted({entry.parser for entry in manifest.entries}))
    return RefreshPlan(
        root_path=str(Path(root_path).resolve()),
        namespace=namespace,
        previous_manifest_present=previous_manifest is not None,
        changed_paths=changed_paths,
        unchanged_paths=unchanged_paths,
        removed_paths=removed_paths,
        path_changes=tuple(path_changes),
        parser_set=parser_set,
        manifest_entry_count=len(manifest.entries),
    )


def save_refresh_profile(profile: RefreshProfile, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_stable_json(profile.to_dict()), encoding="utf-8")
    return target


def load_refresh_profile(path: str | Path) -> RefreshProfile:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise PragmaGraphError(
            "refresh profile JSON root must be an object",
            code="INVALID_REFRESH_PROFILE",
        )
    return RefreshProfile.from_dict(payload)


def save_refresh_status(status: RefreshStatus, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_stable_json(status.to_dict()), encoding="utf-8")
    return target


def load_refresh_status(path: str | Path) -> RefreshStatus:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise PragmaGraphError(
            "refresh status JSON root must be an object",
            code="INVALID_REFRESH_STATUS",
        )
    return RefreshStatus.from_dict(payload)


def build_refresh_profile(
    *,
    label: str,
    root_path: str | Path,
    snapshot_path: str | Path,
    manifest_path: str | Path,
    state_path: str | Path,
    cache_path: str | Path = "",
    namespace: str = "default",
    git_identity_mode: str = DEFAULT_GIT_IDENTITY_MODE,
) -> RefreshProfile:
    """Build a saved profile for repeatable explicit local refresh runs."""
    return RefreshProfile(
        label=label,
        root_path=str(Path(root_path).resolve()),
        snapshot_path=str(Path(snapshot_path)),
        manifest_path=str(Path(manifest_path)),
        state_path=str(Path(state_path)),
        cache_path=str(Path(cache_path)) if cache_path else "",
        namespace=namespace,
        git_identity_mode=git_identity_mode,
    )


def run_refresh_profile(
    profile: RefreshProfile,
    *,
    attempted_at: str = "",
) -> RefreshOperationResult:
    """Run one explicit refresh using a saved local profile."""
    previous_manifest = None
    if profile.manifest_path and Path(profile.manifest_path).exists():
        previous_manifest = load_manifest(profile.manifest_path)
    previous_snapshot = None
    if profile.snapshot_path and Path(profile.snapshot_path).exists():
        previous_snapshot = load_snapshot(profile.snapshot_path)
    try:
        cache = None
        cache_fallback_reason = ""
        if profile.cache_path and Path(profile.cache_path).exists():
            try:
                cache = load_extraction_cache(profile.cache_path)
            except PragmaGraphError as exc:
                cache_fallback_reason = exc.code.lower()
        if profile.cache_path:
            result, next_cache = refresh_snapshot_incremental(
                profile.root_path,
                namespace=profile.namespace,
                previous_manifest=previous_manifest,
                previous_snapshot=previous_snapshot,
                previous_cache=cache,
                created_at=attempted_at,
                git_identity_mode=profile.git_identity_mode,
            )
            if cache_fallback_reason:
                result = replace(
                    result,
                    work=replace(
                        result.work,
                        cache_fallback_reason=cache_fallback_reason,
                    ),
                )
        else:
            result = refresh_snapshot(
                profile.root_path,
                namespace=profile.namespace,
                previous_manifest=previous_manifest,
                previous_snapshot=previous_snapshot,
                created_at=attempted_at,
                git_identity_mode=profile.git_identity_mode,
            )
    except PragmaGraphError as exc:
        status = RefreshStatus(
            root_path=profile.root_path,
            namespace=profile.namespace,
            status="failed",
            snapshot_path=profile.snapshot_path,
            manifest_path=profile.manifest_path,
            last_attempt_at=attempted_at,
            last_failure_at=attempted_at,
            last_error_code=exc.code,
            last_error_message=exc.message,
            git_identity_mode=profile.git_identity_mode,
        )
        if profile.state_path:
            save_refresh_status(status, profile.state_path)
        raise
    save_snapshot(result.snapshot, profile.snapshot_path)
    save_manifest(result.manifest, profile.manifest_path)
    status = refresh_status_from_result(
        profile=profile,
        result=result,
        attempted_at=attempted_at,
    )
    if profile.state_path:
        save_refresh_status(status, profile.state_path)
    if profile.cache_path:
        save_extraction_cache(next_cache, profile.cache_path)
    return RefreshOperationResult(result=result, status=status)


def refresh_status_from_result(
    *,
    profile: RefreshProfile,
    result: RefreshResult,
    attempted_at: str = "",
) -> RefreshStatus:
    parser_set = tuple(sorted({entry.parser for entry in result.manifest.entries}))
    omitted_reason_counts = Counter(item.reason for item in result.snapshot.omitted)
    return RefreshStatus(
        root_path=profile.root_path,
        namespace=profile.namespace,
        status="fresh",
        snapshot_path=profile.snapshot_path,
        manifest_path=profile.manifest_path,
        last_attempt_at=attempted_at,
        last_success_at=attempted_at,
        git_identity_mode=profile.git_identity_mode,
        snapshot_id=_snapshot_id(result.snapshot),
        changed_path_count=len(result.changed_paths),
        unchanged_path_count=len(result.unchanged_paths),
        removed_path_count=len(result.removed_paths),
        added_node_count=len(result.snapshot_delta.added_node_ids),
        removed_node_count=len(result.snapshot_delta.removed_node_ids),
        added_edge_count=len(result.snapshot_delta.added_edge_ids),
        removed_edge_count=len(result.snapshot_delta.removed_edge_ids),
        added_omitted_count=len(result.snapshot_delta.added_omitted_ids),
        removed_omitted_count=len(result.snapshot_delta.removed_omitted_ids),
        manifest_entry_count=len(result.manifest.entries),
        omitted_reason_counts=dict(sorted(omitted_reason_counts.items())),
        parser_set=parser_set,
    )


__all__ = [
    "RefreshOperationResult",
    "RefreshPlan",
    "RefreshProfile",
    "RefreshStatus",
    "build_refresh_plan",
    "build_refresh_profile",
    "load_refresh_profile",
    "load_refresh_status",
    "refresh_status_from_result",
    "run_refresh_profile",
    "save_refresh_profile",
    "save_refresh_status",
]
