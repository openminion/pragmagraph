"""Shared workspace path helpers for package-local UI commands."""

from __future__ import annotations

from pathlib import Path

from pragmagraph.workspace import initialize_workspace, resolve_workspace_config_paths


def ensure_config_workspace(config_path: str | Path) -> Path:
    """Initialize and return the workspace named by a workspace config."""
    resolved = resolve_workspace_config_paths(config_path)
    if not (resolved.workspace_path / "workspace.json").exists():
        initialize_workspace(
            label=resolved.config.label,
            root_path=resolved.root_path,
            workspace_path=resolved.workspace_path,
            namespace=resolved.config.namespace,
            git_identity_mode=resolved.config.git_identity_mode,
        )
    return resolved.workspace_path


__all__ = ["ensure_config_workspace"]
