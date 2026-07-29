"""Shared workspace-config resolution helpers for root CLI commands."""

from __future__ import annotations

import argparse
from pathlib import Path

from pragmagraph.workspace import (
    initialize_workspace,
    load_workspace_metadata,
    resolve_workspace_config_paths,
)


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


def query_args(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> tuple[str, str]:
    """Resolve snapshot and query text for config-aware query commands."""
    if args.config:
        workspace_path = ensure_config_workspace(args.config)
        metadata = load_workspace_metadata(workspace_path)
        if args.query is None:
            if args.snapshot is None:
                parser.error("query requires query text when --config is used")
            return metadata.paths.snapshot_path, args.snapshot
        return metadata.paths.snapshot_path, args.query
    if args.snapshot is None or args.query is None:
        parser.error("query requires SNAPSHOT QUERY or --config QUERY")
    return args.snapshot, args.query


def investigation_args(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> tuple[str, str]:
    """Resolve snapshot and query text for config-aware investigation."""
    if args.config:
        workspace_path = ensure_config_workspace(args.config)
        metadata = load_workspace_metadata(workspace_path)
        if args.query is None:
            if args.snapshot is None:
                return metadata.paths.snapshot_path, "RuntimeGraph"
            return metadata.paths.snapshot_path, args.snapshot
        return metadata.paths.snapshot_path, args.query
    if args.snapshot is None or args.query is None:
        parser.error("investigate requires SNAPSHOT QUERY or --config [QUERY]")
    return args.snapshot, args.query


def freshness_snapshot_arg(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> str:
    """Resolve snapshot path for config-aware freshness checks."""
    if args.config:
        workspace_path = ensure_config_workspace(args.config)
        return load_workspace_metadata(workspace_path).paths.snapshot_path
    if args.snapshot is None:
        parser.error("freshness requires SNAPSHOT or --config")
    return args.snapshot


__all__ = [
    "ensure_config_workspace",
    "freshness_snapshot_arg",
    "investigation_args",
    "query_args",
]
