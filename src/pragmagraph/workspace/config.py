"""Tiny TOML workspace configuration for first-run PragmaGraph workflows."""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pragmagraph.adapters.git_history import (
    DEFAULT_GIT_IDENTITY_MODE,
    validate_git_identity_mode,
)
from pragmagraph.models import PragmaGraphError

WORKSPACE_CONFIG_SCHEMA_VERSION = "pragmagraph.workspace_config.v1alpha1"
DEFAULT_WORKSPACE_DIR = ".pragmagraph/workspace"
DEFAULT_WORKSPACE_CONFIG = ".pragmagraph/workspace.toml"
DEFAULT_STORE_FILE = "graph.sqlite"
DEFAULT_UI_SCREEN = "search"
DEFAULT_UI_QUERY = "RuntimeGraph"

SUPPORTED_UI_SCREENS = frozenset(
    {
        "search",
        "result_detail",
        "neighborhood",
        "path",
        "provider_status",
        "project_health",
        "evidence",
        "delta_review",
        "investigation",
        "graph_pack_review",
    }
)


@dataclass(frozen=True)
class WorkspaceConfig:
    """Public, shareable configuration for one local PragmaGraph workspace."""

    root_path: str
    workspace_path: str = DEFAULT_WORKSPACE_DIR
    label: str = "default"
    namespace: str = "default"
    git_identity_mode: str = DEFAULT_GIT_IDENTITY_MODE
    store_path: str = DEFAULT_STORE_FILE
    ui_screen: str = DEFAULT_UI_SCREEN
    ui_query: str = DEFAULT_UI_QUERY
    schema_version: str = WORKSPACE_CONFIG_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != WORKSPACE_CONFIG_SCHEMA_VERSION:
            raise PragmaGraphError(
                "workspace config schema_version is unsupported",
                code="INVALID_WORKSPACE_CONFIG",
                details={
                    "schema_version": self.schema_version,
                    "supported": WORKSPACE_CONFIG_SCHEMA_VERSION,
                },
            )
        if not self.root_path:
            raise PragmaGraphError(
                "workspace config root_path is required",
                code="INVALID_WORKSPACE_CONFIG",
            )
        if not self.workspace_path:
            raise PragmaGraphError(
                "workspace config workspace_path is required",
                code="INVALID_WORKSPACE_CONFIG",
            )
        if self.ui_screen not in SUPPORTED_UI_SCREENS:
            raise PragmaGraphError(
                "workspace config ui_screen is unsupported",
                code="INVALID_WORKSPACE_CONFIG",
                details={
                    "ui_screen": self.ui_screen,
                    "supported": sorted(SUPPORTED_UI_SCREENS),
                },
            )
        validate_git_identity_mode(self.git_identity_mode)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "root_path": self.root_path,
            "workspace_path": self.workspace_path,
            "label": self.label,
            "namespace": self.namespace,
            "git_identity_mode": self.git_identity_mode,
            "store_path": self.store_path,
            "ui": {
                "screen": self.ui_screen,
                "query": self.ui_query,
            },
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> WorkspaceConfig:
        ui = payload.get("ui", {})
        if not isinstance(ui, Mapping):
            raise PragmaGraphError(
                "workspace config ui section must be an object",
                code="INVALID_WORKSPACE_CONFIG",
            )
        return cls(
            schema_version=str(
                payload.get("schema_version", "") or WORKSPACE_CONFIG_SCHEMA_VERSION
            ),
            root_path=str(payload.get("root_path", "") or ""),
            workspace_path=str(
                payload.get("workspace_path", "") or DEFAULT_WORKSPACE_DIR
            ),
            label=str(payload.get("label", "") or "default"),
            namespace=str(payload.get("namespace", "") or "default"),
            git_identity_mode=str(
                payload.get("git_identity_mode", "") or DEFAULT_GIT_IDENTITY_MODE
            ),
            store_path=str(payload.get("store_path", "") or DEFAULT_STORE_FILE),
            ui_screen=str(ui.get("screen", "") or DEFAULT_UI_SCREEN),
            ui_query=str(ui.get("query", "") or DEFAULT_UI_QUERY),
        )


@dataclass(frozen=True)
class ResolvedWorkspaceConfig:
    """Workspace config plus paths resolved relative to the config file."""

    config: WorkspaceConfig
    root_path: Path
    workspace_path: Path
    store_path: Path

    def to_dict(self) -> dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "resolved_root_path": str(self.root_path),
            "resolved_workspace_path": str(self.workspace_path),
            "resolved_store_path": str(self.store_path),
        }


def build_workspace_config(
    root_path: str | Path,
    *,
    workspace_path: str | Path = DEFAULT_WORKSPACE_DIR,
    label: str = "default",
    namespace: str = "default",
    git_identity_mode: str = DEFAULT_GIT_IDENTITY_MODE,
    store_path: str | Path = DEFAULT_STORE_FILE,
    ui_screen: str = DEFAULT_UI_SCREEN,
    ui_query: str = DEFAULT_UI_QUERY,
) -> WorkspaceConfig:
    """Build a deterministic config without resolving caller-provided paths."""
    return WorkspaceConfig(
        root_path=str(root_path),
        workspace_path=str(workspace_path),
        label=label,
        namespace=namespace,
        git_identity_mode=git_identity_mode,
        store_path=str(store_path),
        ui_screen=ui_screen,
        ui_query=ui_query,
    )


def save_workspace_config(config: WorkspaceConfig, path: str | Path) -> Path:
    """Write ``config`` as deterministic TOML."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_workspace_config(config), encoding="utf-8")
    return target


def load_workspace_config(path: str | Path) -> WorkspaceConfig:
    """Load and validate a package-owned workspace TOML file."""
    target = Path(path)
    if not target.exists():
        raise PragmaGraphError(
            "workspace config file not found",
            code="WORKSPACE_CONFIG_NOT_FOUND",
            details={"path": str(target)},
        )
    payload = tomllib.loads(target.read_text(encoding="utf-8"))
    return WorkspaceConfig.from_dict(payload)


def resolve_config_path(config_path: str | Path, value: str) -> Path:
    """Resolve one config path relative to the config file directory."""
    path = Path(value)
    if path.is_absolute():
        return path
    return (Path(config_path).resolve().parent / path).resolve()


def resolve_workspace_config_paths(config_path: str | Path) -> ResolvedWorkspaceConfig:
    """Load one config and resolve its package-owned local paths."""
    config = load_workspace_config(config_path)
    return ResolvedWorkspaceConfig(
        config=config,
        root_path=resolve_config_path(config_path, config.root_path),
        workspace_path=resolve_config_path(config_path, config.workspace_path),
        store_path=resolve_config_path(config_path, config.store_path),
    )


def render_workspace_config(config: WorkspaceConfig) -> str:
    """Render deterministic TOML for the tiny public config contract."""
    lines = [
        f'schema_version = "{_toml_string(config.schema_version)}"',
        f'label = "{_toml_string(config.label)}"',
        f'namespace = "{_toml_string(config.namespace)}"',
        f'root_path = "{_toml_string(config.root_path)}"',
        f'workspace_path = "{_toml_string(config.workspace_path)}"',
        f'git_identity_mode = "{_toml_string(config.git_identity_mode)}"',
        f'store_path = "{_toml_string(config.store_path)}"',
        "",
        "[ui]",
        f'screen = "{_toml_string(config.ui_screen)}"',
        f'query = "{_toml_string(config.ui_query)}"',
        "",
    ]
    return "\n".join(lines)


def _toml_string(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


__all__ = [
    "DEFAULT_STORE_FILE",
    "DEFAULT_UI_QUERY",
    "DEFAULT_UI_SCREEN",
    "DEFAULT_WORKSPACE_CONFIG",
    "DEFAULT_WORKSPACE_DIR",
    "SUPPORTED_UI_SCREENS",
    "WORKSPACE_CONFIG_SCHEMA_VERSION",
    "ResolvedWorkspaceConfig",
    "WorkspaceConfig",
    "build_workspace_config",
    "load_workspace_config",
    "render_workspace_config",
    "resolve_config_path",
    "resolve_workspace_config_paths",
    "save_workspace_config",
]
