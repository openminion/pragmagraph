"""CLI registration and execution for workspace commands."""

from __future__ import annotations

import argparse

from pragmagraph.cli import add_json_flag
from pragmagraph.adapters.git_history import (
    DEFAULT_GIT_IDENTITY_MODE,
    SUPPORTED_GIT_IDENTITY_MODES,
)
from pragmagraph.models import PragmaGraphError, QueryRequest
from pragmagraph.query import query
from pragmagraph.storage import load_snapshot, save_snapshot
from pragmagraph.workspace import (
    SUPPORTED_UI_SCREENS,
    build_workspace_config,
    ensure_workspace_snapshot,
    initialize_workspace,
    load_workspace_status,
    refresh_workspace,
    resolve_workspace_config_paths,
    save_workspace_config,
)
from pragmagraph.workspace.composition import (
    NamedSnapshot,
    compose_snapshots,
    save_composed_snapshot_atomic,
)
from pragmagraph.workspace.multi_root import WorkspaceRoot, index_multi_root

WORKSPACE_COMMANDS = frozenset(
    {
        "workspace-init",
        "workspace-refresh",
        "workspace-status",
        "workspace-query",
        "workspace-config-init",
        "workspace-config-status",
        "multi-root-index",
        "multi-root-compose",
    }
)


def register_workspace_commands(subparsers: argparse._SubParsersAction) -> None:
    """Register the bounded workspace command family."""
    init_parser = subparsers.add_parser(
        "workspace-init",
        help="initialize a persistent local workspace directory",
    )
    init_parser.add_argument("root")
    init_parser.add_argument("--workspace", required=True)
    init_parser.add_argument("--label", default="default")
    init_parser.add_argument("--namespace", default="default")
    _add_git_identity_mode_argument(init_parser)
    add_json_flag(init_parser)

    refresh_parser = subparsers.add_parser(
        "workspace-refresh",
        help="refresh a persistent local workspace directory",
    )
    refresh_parser.add_argument("workspace", nargs="?")
    refresh_parser.add_argument("--config")
    add_json_flag(refresh_parser)

    status_parser = subparsers.add_parser(
        "workspace-status",
        help="inspect a persistent local workspace directory",
    )
    status_parser.add_argument("workspace", nargs="?")
    status_parser.add_argument("--config")
    add_json_flag(status_parser)

    query_parser = subparsers.add_parser(
        "workspace-query",
        help="query the snapshot in a persistent local workspace",
    )
    query_parser.add_argument("query")
    query_parser.add_argument("--workspace")
    query_parser.add_argument("--config")
    query_parser.add_argument("--max-results", type=int, default=10)
    query_parser.add_argument("--cursor", default="")
    query_parser.add_argument("--max-examined", type=int)
    add_json_flag(query_parser)

    config_parser = subparsers.add_parser(
        "workspace-config-init",
        help="write a shareable package-local workspace TOML file",
    )
    config_parser.add_argument("root")
    config_parser.add_argument("--out", default=".pragmagraph/workspace.toml")
    config_parser.add_argument("--workspace", default=".pragmagraph/workspace")
    config_parser.add_argument("--label", default="default")
    config_parser.add_argument("--namespace", default="default")
    config_parser.add_argument("--store", default="graph.sqlite")
    config_parser.add_argument(
        "--ui-screen",
        choices=tuple(sorted(SUPPORTED_UI_SCREENS)),
        default="search",
    )
    config_parser.add_argument("--ui-query", default="RuntimeGraph")
    _add_git_identity_mode_argument(config_parser)
    add_json_flag(config_parser)

    config_status_parser = subparsers.add_parser(
        "workspace-config-status",
        help="inspect a workspace TOML file and any realized workspace state",
    )
    config_status_parser.add_argument("config")
    add_json_flag(config_status_parser)

    index_parser = subparsers.add_parser(
        "multi-root-index",
        help="index explicitly named roots into one overlay",
    )
    index_parser.add_argument("--root", action="append", required=True)
    index_parser.add_argument("--namespace", default="workspace")
    index_parser.add_argument("--out", required=True)
    add_json_flag(index_parser)

    compose_parser = subparsers.add_parser(
        "multi-root-compose",
        help="compose named canonical snapshots with exact SCIP resolution",
    )
    compose_parser.add_argument("--snapshot", action="append", required=True)
    compose_parser.add_argument("--namespace", default="workspace")
    compose_parser.add_argument("--created-at", default="")
    compose_parser.add_argument("--out", required=True)
    add_json_flag(compose_parser)


def run_workspace_command(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> object:
    """Execute one parsed workspace command."""
    if args.command == "workspace-init":
        return initialize_workspace(
            label=args.label,
            root_path=args.root,
            workspace_path=args.workspace,
            namespace=args.namespace,
            git_identity_mode=args.git_identity_mode,
        ).to_dict()
    if args.command == "workspace-refresh":
        workspace_path = _workspace_path_from_args(args, parser, ensure=True)
        return refresh_workspace(workspace_path).to_dict()
    if args.command == "workspace-status":
        workspace_path = _workspace_path_from_args(args, parser, ensure=False)
        return load_workspace_status(workspace_path).to_dict()
    if args.command == "workspace-query":
        workspace_path = _workspace_path_from_args(args, parser, ensure=True)
        metadata = ensure_workspace_snapshot(workspace_path)
        snapshot = load_snapshot(metadata.paths.snapshot_path)
        return query(
            snapshot,
            QueryRequest(
                query=args.query,
                max_results=args.max_results,
                cursor=args.cursor,
                max_examined=args.max_examined,
            ),
        ).to_dict()
    if args.command == "workspace-config-init":
        config = build_workspace_config(
            args.root,
            workspace_path=args.workspace,
            label=args.label,
            namespace=args.namespace,
            git_identity_mode=args.git_identity_mode,
            store_path=args.store,
            ui_screen=args.ui_screen,
            ui_query=args.ui_query,
        )
        config_output_path = save_workspace_config(config, args.out)
        return {"config_path": str(config_output_path), "config": config.to_dict()}
    if args.command == "workspace-config-status":
        resolved = resolve_workspace_config_paths(args.config)
        status = None
        if (resolved.workspace_path / "workspace.json").exists():
            status = load_workspace_status(resolved.workspace_path).to_dict()
        return {**resolved.to_dict(), "workspace_status": status}
    if args.command == "multi-root-index":
        roots = tuple(
            WorkspaceRoot(name=name, path=path)
            for name, path in _named_values(args.root, "--root", parser)
        )
        snapshot = index_multi_root(roots, namespace=args.namespace)
        save_snapshot(snapshot, args.out)
        return snapshot.to_dict()
    if args.command == "multi-root-compose":
        inputs = tuple(
            NamedSnapshot(name=name, snapshot=load_snapshot(path))
            for name, path in _named_values(args.snapshot, "--snapshot", parser)
        )
        result = compose_snapshots(
            inputs,
            namespace=args.namespace,
            created_at=args.created_at,
        )
        save_composed_snapshot_atomic(result.snapshot, args.out)
        return {
            "output_path": args.out,
            "report": result.report.to_dict(),
            "stats": dict(result.snapshot.stats),
        }
    raise PragmaGraphError(
        "unsupported workspace command",
        code="UNSUPPORTED_WORKSPACE_COMMAND",
        details={"command": args.command},
    )


def _named_values(
    values: list[str],
    option: str,
    parser: argparse.ArgumentParser,
) -> tuple[tuple[str, str], ...]:
    parsed: list[tuple[str, str]] = []
    for value in values:
        name, separator, path = value.partition("=")
        if not separator or not name.strip() or not path.strip():
            parser.error(f"{option} must use NAME=PATH")
        parsed.append((name.strip(), path.strip()))
    return tuple(parsed)


def _workspace_path_from_args(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
    *,
    ensure: bool,
) -> str:
    if getattr(args, "config", None):
        resolved = resolve_workspace_config_paths(args.config)
        if ensure and not (resolved.workspace_path / "workspace.json").exists():
            initialize_workspace(
                label=resolved.config.label,
                root_path=resolved.root_path,
                workspace_path=resolved.workspace_path,
                namespace=resolved.config.namespace,
                git_identity_mode=resolved.config.git_identity_mode,
            )
        return str(resolved.workspace_path)
    if getattr(args, "workspace", None):
        return str(args.workspace)
    parser.error(f"{args.command} requires a workspace path or --config")
    raise AssertionError("unreachable")


def _add_git_identity_mode_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--git-identity-mode",
        choices=tuple(sorted(SUPPORTED_GIT_IDENTITY_MODES)),
        default=DEFAULT_GIT_IDENTITY_MODE,
    )


__all__ = [
    "WORKSPACE_COMMANDS",
    "register_workspace_commands",
    "run_workspace_command",
]
