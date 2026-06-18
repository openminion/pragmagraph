"""Persistent local workspace helpers for repeated PragmaGraph use."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from pragmagraph.adapters.git_history import DEFAULT_GIT_IDENTITY_MODE
from pragmagraph.models import PragmaGraphError
from pragmagraph.operations import (
    RefreshOperationResult,
    RefreshProfile,
    RefreshStatus,
    build_refresh_profile,
    load_refresh_profile,
    load_refresh_status,
    run_refresh_profile,
    save_refresh_profile,
)
from pragmagraph.storage import load_snapshot

WORKSPACE_SCHEMA_VERSION = "pragmagraph.workspace.v1alpha1"
WORKSPACE_METADATA_FILE = "workspace.json"
WORKSPACE_PROFILE_FILE = "profile.json"
WORKSPACE_SNAPSHOT_FILE = "snapshot.json"
WORKSPACE_MANIFEST_FILE = "manifest.json"
WORKSPACE_STATUS_FILE = "status.json"


def _stable_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(dict(payload), indent=2, sort_keys=True) + "\n"


@dataclass(frozen=True)
class WorkspacePaths:
    """Deterministic file layout for one local PragmaGraph workspace."""

    workspace_path: str
    metadata_path: str
    profile_path: str
    snapshot_path: str
    manifest_path: str
    status_path: str

    @classmethod
    def from_workspace(cls, workspace_path: str | Path) -> "WorkspacePaths":
        root = Path(workspace_path).resolve()
        return cls(
            workspace_path=str(root),
            metadata_path=str(root / WORKSPACE_METADATA_FILE),
            profile_path=str(root / WORKSPACE_PROFILE_FILE),
            snapshot_path=str(root / WORKSPACE_SNAPSHOT_FILE),
            manifest_path=str(root / WORKSPACE_MANIFEST_FILE),
            status_path=str(root / WORKSPACE_STATUS_FILE),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "workspace_path": self.workspace_path,
            "metadata_path": self.metadata_path,
            "profile_path": self.profile_path,
            "snapshot_path": self.snapshot_path,
            "manifest_path": self.manifest_path,
            "status_path": self.status_path,
        }


@dataclass(frozen=True)
class WorkspaceMetadata:
    """Persistent metadata for one package-owned local workspace."""

    label: str
    root_path: str
    namespace: str
    paths: WorkspacePaths
    git_identity_mode: str = DEFAULT_GIT_IDENTITY_MODE
    schema_version: str = WORKSPACE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.label:
            raise PragmaGraphError(
                "workspace label is required",
                code="INVALID_WORKSPACE_METADATA",
            )
        if not self.root_path:
            raise PragmaGraphError(
                "workspace root_path is required",
                code="INVALID_WORKSPACE_METADATA",
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "label": self.label,
            "root_path": self.root_path,
            "namespace": self.namespace,
            "git_identity_mode": self.git_identity_mode,
            "paths": self.paths.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "WorkspaceMetadata":
        paths_payload = payload.get("paths", {})
        if not isinstance(paths_payload, Mapping):
            raise PragmaGraphError(
                "workspace metadata paths must be an object",
                code="INVALID_WORKSPACE_METADATA",
            )
        return cls(
            schema_version=str(
                payload.get("schema_version", "") or WORKSPACE_SCHEMA_VERSION
            ),
            label=str(payload.get("label", "") or ""),
            root_path=str(payload.get("root_path", "") or ""),
            namespace=str(payload.get("namespace", "") or "default"),
            git_identity_mode=str(
                payload.get("git_identity_mode", "") or DEFAULT_GIT_IDENTITY_MODE
            ),
            paths=WorkspacePaths(
                workspace_path=str(paths_payload.get("workspace_path", "") or ""),
                metadata_path=str(paths_payload.get("metadata_path", "") or ""),
                profile_path=str(paths_payload.get("profile_path", "") or ""),
                snapshot_path=str(paths_payload.get("snapshot_path", "") or ""),
                manifest_path=str(paths_payload.get("manifest_path", "") or ""),
                status_path=str(paths_payload.get("status_path", "") or ""),
            ),
        )

    def build_profile(self) -> RefreshProfile:
        return build_refresh_profile(
            label=self.label,
            root_path=self.root_path,
            snapshot_path=self.paths.snapshot_path,
            manifest_path=self.paths.manifest_path,
            state_path=self.paths.status_path,
            namespace=self.namespace,
            git_identity_mode=self.git_identity_mode,
        )


@dataclass(frozen=True)
class WorkspaceStatusView:
    """Inspectable current facts for one local workspace."""

    workspace: WorkspaceMetadata
    refresh_status: RefreshStatus | None = None
    snapshot_present: bool = False
    manifest_present: bool = False
    profile_present: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace": self.workspace.to_dict(),
            "refresh_status": (
                self.refresh_status.to_dict()
                if self.refresh_status is not None
                else None
            ),
            "snapshot_present": self.snapshot_present,
            "manifest_present": self.manifest_present,
            "profile_present": self.profile_present,
        }


@dataclass(frozen=True)
class WorkspaceRefreshResult:
    """Result of one workspace init/refresh run."""

    workspace: WorkspaceMetadata
    operation: RefreshOperationResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace": self.workspace.to_dict(),
            "operation": self.operation.to_dict(),
        }


def build_workspace_metadata(
    *,
    label: str,
    root_path: str | Path,
    workspace_path: str | Path,
    namespace: str = "default",
    git_identity_mode: str = DEFAULT_GIT_IDENTITY_MODE,
) -> WorkspaceMetadata:
    return WorkspaceMetadata(
        label=label,
        root_path=str(Path(root_path).resolve()),
        namespace=namespace,
        git_identity_mode=git_identity_mode,
        paths=WorkspacePaths.from_workspace(workspace_path),
    )


def save_workspace_metadata(metadata: WorkspaceMetadata) -> Path:
    target = Path(metadata.paths.metadata_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_stable_json(metadata.to_dict()), encoding="utf-8")
    return target


def load_workspace_metadata(workspace_path: str | Path) -> WorkspaceMetadata:
    paths = WorkspacePaths.from_workspace(workspace_path)
    target = Path(paths.metadata_path)
    if not target.exists():
        raise PragmaGraphError(
            "workspace metadata file not found",
            code="WORKSPACE_NOT_FOUND",
            details={"workspace_path": str(Path(workspace_path).resolve())},
        )
    payload = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise PragmaGraphError(
            "workspace metadata JSON root must be an object",
            code="INVALID_WORKSPACE_METADATA",
        )
    return WorkspaceMetadata.from_dict(payload)


def initialize_workspace(
    *,
    label: str,
    root_path: str | Path,
    workspace_path: str | Path,
    namespace: str = "default",
    git_identity_mode: str = DEFAULT_GIT_IDENTITY_MODE,
    attempted_at: str = "",
) -> WorkspaceRefreshResult:
    metadata = build_workspace_metadata(
        label=label,
        root_path=root_path,
        workspace_path=workspace_path,
        namespace=namespace,
        git_identity_mode=git_identity_mode,
    )
    save_workspace_metadata(metadata)
    save_refresh_profile(metadata.build_profile(), metadata.paths.profile_path)
    operation = run_refresh_profile(metadata.build_profile(), attempted_at=attempted_at)
    return WorkspaceRefreshResult(workspace=metadata, operation=operation)


def refresh_workspace(
    workspace_path: str | Path,
    *,
    attempted_at: str = "",
) -> WorkspaceRefreshResult:
    metadata = load_workspace_metadata(workspace_path)
    profile = load_refresh_profile(metadata.paths.profile_path)
    operation = run_refresh_profile(profile, attempted_at=attempted_at)
    return WorkspaceRefreshResult(workspace=metadata, operation=operation)


def load_workspace_status(workspace_path: str | Path) -> WorkspaceStatusView:
    metadata = load_workspace_metadata(workspace_path)
    refresh_status = None
    if Path(metadata.paths.status_path).exists():
        refresh_status = load_refresh_status(metadata.paths.status_path)
    return WorkspaceStatusView(
        workspace=metadata,
        refresh_status=refresh_status,
        snapshot_present=Path(metadata.paths.snapshot_path).exists(),
        manifest_present=Path(metadata.paths.manifest_path).exists(),
        profile_present=Path(metadata.paths.profile_path).exists(),
    )


def ensure_workspace_snapshot(workspace_path: str | Path) -> WorkspaceMetadata:
    metadata = load_workspace_metadata(workspace_path)
    if not Path(metadata.paths.snapshot_path).exists():
        refresh_workspace(workspace_path)
    load_snapshot(metadata.paths.snapshot_path)
    return metadata


__all__ = [
    "WORKSPACE_MANIFEST_FILE",
    "WORKSPACE_METADATA_FILE",
    "WORKSPACE_PROFILE_FILE",
    "WORKSPACE_SCHEMA_VERSION",
    "WORKSPACE_SNAPSHOT_FILE",
    "WORKSPACE_STATUS_FILE",
    "WorkspaceMetadata",
    "WorkspacePaths",
    "WorkspaceRefreshResult",
    "WorkspaceStatusView",
    "build_workspace_metadata",
    "ensure_workspace_snapshot",
    "initialize_workspace",
    "load_workspace_metadata",
    "load_workspace_status",
    "refresh_workspace",
    "save_workspace_metadata",
]
