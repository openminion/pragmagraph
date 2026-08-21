"""CLI registration and execution for materialized store commands."""

from __future__ import annotations

import argparse

from pragmagraph.cli import add_json_flag
from pragmagraph.models import PragmaGraphError, QueryRequest
from pragmagraph.query import health
from pragmagraph.storage import (
    SQLiteGraphStore,
    backend_capabilities_for_path,
    backend_catalog_payload,
    explain_store_query,
    load_snapshot,
    save_snapshot,
    verify_store_round_trip,
)
from pragmagraph.workspace import (
    ResolvedWorkspaceConfig,
    ensure_workspace_snapshot,
    initialize_workspace,
    resolve_workspace_config_paths,
)

STORAGE_COMMANDS = frozenset(
    {
        "store-import",
        "store-export",
        "store-health",
        "store-query",
        "store-search-explain",
        "store-neighborhood",
        "store-path",
        "store-migrate",
        "store-round-trip",
        "store-update",
        "store-backends",
    }
)


def register_storage_commands(subparsers: argparse._SubParsersAction) -> None:
    """Register the bounded materialized-store command family."""
    import_parser = subparsers.add_parser(
        "store-import",
        help="import a canonical snapshot into a materialized graph store",
    )
    import_parser.add_argument("snapshot", nargs="?")
    import_parser.add_argument("--out")
    import_parser.add_argument("--backend", choices=("sqlite",), default="sqlite")
    import_parser.add_argument("--config")
    add_json_flag(import_parser)

    export_parser = subparsers.add_parser(
        "store-export",
        help="export a materialized graph store as canonical snapshot JSON",
    )
    export_parser.add_argument("store")
    export_parser.add_argument("--out")
    add_json_flag(export_parser)

    health_parser = subparsers.add_parser(
        "store-health",
        help="summarize a materialized graph store",
    )
    health_parser.add_argument("store", nargs="?")
    health_parser.add_argument("--config")
    add_json_flag(health_parser)

    query_parser = subparsers.add_parser(
        "store-query",
        help="query a materialized graph store",
    )
    query_parser.add_argument("store", nargs="?")
    query_parser.add_argument("query", nargs="?")
    query_parser.add_argument("--config")
    query_parser.add_argument("--max-results", type=int, default=10)
    query_parser.add_argument("--cursor", default="")
    query_parser.add_argument("--max-examined", type=int)
    add_json_flag(query_parser)

    explain_parser = subparsers.add_parser(
        "store-search-explain",
        help="explain materialized-store search strategy and candidates",
    )
    explain_parser.add_argument("store", nargs="?")
    explain_parser.add_argument("query", nargs="?")
    explain_parser.add_argument("--config")
    explain_parser.add_argument("--max-results", type=int, default=10)
    explain_parser.add_argument("--max-examined", type=int)
    add_json_flag(explain_parser)

    neighborhood_parser = subparsers.add_parser(
        "store-neighborhood",
        help="show nodes around a materialized-store node",
    )
    neighborhood_parser.add_argument("store")
    neighborhood_parser.add_argument("node_id")
    neighborhood_parser.add_argument("--depth", type=int, default=1)
    neighborhood_parser.add_argument("--max-results", type=int, default=10)
    neighborhood_parser.add_argument("--edge-kind", action="append", default=[])
    neighborhood_parser.add_argument("--node-kind", action="append", default=[])
    add_json_flag(neighborhood_parser)

    path_parser = subparsers.add_parser(
        "store-path",
        help="find a bounded path in a materialized graph store",
    )
    path_parser.add_argument("store")
    path_parser.add_argument("source_id")
    path_parser.add_argument("target_id")
    path_parser.add_argument("--max-hops", type=int, default=4)
    path_parser.add_argument("--edge-kind", action="append", default=[])
    path_parser.add_argument("--node-kind", action="append", default=[])
    add_json_flag(path_parser)

    migrate_parser = subparsers.add_parser(
        "store-migrate", help="explicitly migrate a SQLite graph store"
    )
    migrate_parser.add_argument("store")
    add_json_flag(migrate_parser)

    round_trip_parser = subparsers.add_parser(
        "store-round-trip",
        help="verify import/export parity through a materialized graph store",
    )
    round_trip_parser.add_argument("snapshot")
    round_trip_parser.add_argument("--store", required=True)
    round_trip_parser.add_argument("--query", default="")
    round_trip_parser.add_argument("--export-out")
    add_json_flag(round_trip_parser)

    update_parser = subparsers.add_parser(
        "store-update", help="atomically apply a canonical snapshot delta"
    )
    update_parser.add_argument("store")
    update_parser.add_argument("snapshot")
    add_json_flag(update_parser)

    _register_backend_catalog_command(subparsers)


def run_storage_command(args: argparse.Namespace) -> object:
    """Execute one parsed materialized-store command."""
    if args.command == "store-import":
        if args.backend != "sqlite":
            raise PragmaGraphError(
                "unsupported store backend",
                code="STORE_BACKEND_UNSUPPORTED",
                details={"backend": args.backend},
            )
        snapshot_path, store_path = _import_paths(args)
        store = SQLiteGraphStore.from_snapshot(load_snapshot(snapshot_path), store_path)
        return _store_payload(store)
    if args.command == "store-export":
        snapshot = SQLiteGraphStore(args.store).export_snapshot()
        if args.out:
            save_snapshot(snapshot, args.out)
            return health(snapshot).to_dict()
        return snapshot.to_dict()
    if args.command == "store-health":
        return _store_payload(SQLiteGraphStore(_store_path(args)))
    if args.command == "store-query":
        store_path, query_text = _store_query_args(args)
        return (
            SQLiteGraphStore(store_path)
            .query(_query_request(args, query_text))
            .to_dict()
        )
    if args.command == "store-search-explain":
        store_path, query_text = _store_query_args(args)
        return explain_store_query(
            SQLiteGraphStore(store_path),
            _query_request(args, query_text),
        )
    if args.command == "store-neighborhood":
        return (
            SQLiteGraphStore(args.store)
            .neighborhood(
                args.node_id,
                depth=args.depth,
                max_results=args.max_results,
                edge_kinds=tuple(args.edge_kind),
                node_kinds=tuple(args.node_kind),
            )
            .to_dict()
        )
    if args.command == "store-path":
        return (
            SQLiteGraphStore(args.store)
            .path(
                args.source_id,
                args.target_id,
                max_hops=args.max_hops,
                edge_kinds=tuple(args.edge_kind),
                node_kinds=tuple(args.node_kind),
            )
            .to_dict()
        )
    if args.command == "store-migrate":
        return SQLiteGraphStore(args.store).migrate().to_dict()
    if args.command == "store-round-trip":
        snapshot = load_snapshot(args.snapshot)
        report = verify_store_round_trip(
            snapshot,
            args.store,
            query_text=args.query,
        )
        if args.export_out:
            save_snapshot(
                SQLiteGraphStore(args.store).export_snapshot(), args.export_out
            )
            return {**report.to_dict(), "export_path": str(args.export_out)}
        return report.to_dict()
    if args.command == "store-update":
        report = SQLiteGraphStore(args.store).apply_snapshot_delta(
            load_snapshot(args.snapshot)
        )
        return report.to_dict()
    if args.command == "store-backends":
        if args.backend or args.path:
            if not args.backend or not args.path:
                raise PragmaGraphError(
                    "store-backends requires both --backend and --path for inspection",
                    code="INVALID_STORE_COMMAND",
                )
            return {
                "catalog": backend_catalog_payload(probe_optional=args.probe_optional),
                "selected": backend_capabilities_for_path(args.backend, args.path),
            }
        return backend_catalog_payload(probe_optional=args.probe_optional)
    raise PragmaGraphError(
        "unsupported store command",
        code="UNSUPPORTED_STORE_COMMAND",
        details={"command": args.command},
    )


def _import_paths(args: argparse.Namespace) -> tuple[str, str]:
    if getattr(args, "config", None):
        resolved = _ensure_config_workspace(args.config)
        snapshot_path = (
            args.snapshot
            or ensure_workspace_snapshot(resolved.workspace_path).paths.snapshot_path
        )
        store_path = args.out or str(resolved.store_path)
        return str(snapshot_path), store_path
    if not args.snapshot or not args.out:
        raise PragmaGraphError(
            "store-import requires SNAPSHOT and --out, or --config",
            code="INVALID_STORE_COMMAND",
        )
    return str(args.snapshot), str(args.out)


def _store_path(args: argparse.Namespace) -> str:
    if getattr(args, "config", None):
        return str(resolve_workspace_config_paths(args.config).store_path)
    if not getattr(args, "store", None):
        raise PragmaGraphError(
            f"{args.command} requires STORE or --config",
            code="INVALID_STORE_COMMAND",
        )
    return str(args.store)


def _store_query_args(args: argparse.Namespace) -> tuple[str, str]:
    if getattr(args, "config", None):
        store_path = str(resolve_workspace_config_paths(args.config).store_path)
        query_text = args.query if args.query is not None else args.store
        if not query_text:
            raise PragmaGraphError(
                f"{args.command} requires QUERY when --config is used",
                code="INVALID_STORE_COMMAND",
            )
        return store_path, str(query_text)
    if not args.store or not args.query:
        raise PragmaGraphError(
            f"{args.command} requires STORE QUERY or --config QUERY",
            code="INVALID_STORE_COMMAND",
        )
    return str(args.store), str(args.query)


def _ensure_config_workspace(config_path: str) -> ResolvedWorkspaceConfig:
    resolved = resolve_workspace_config_paths(config_path)
    if not (resolved.workspace_path / "workspace.json").exists():
        initialize_workspace(
            label=resolved.config.label,
            root_path=resolved.root_path,
            workspace_path=resolved.workspace_path,
            namespace=resolved.config.namespace,
            git_identity_mode=resolved.config.git_identity_mode,
        )
    return resolved


def _query_request(args: argparse.Namespace, query_text: str) -> QueryRequest:
    return QueryRequest(
        query=query_text,
        max_results=args.max_results,
        cursor=getattr(args, "cursor", ""),
        max_examined=args.max_examined,
    )


def _store_payload(store: SQLiteGraphStore) -> dict[str, object]:
    return {
        "manifest": store.manifest().to_dict(),
        "capabilities": store.capabilities().to_dict(),
        "health": store.health().to_dict(),
    }


def _register_backend_catalog_command(
    subparsers: argparse._SubParsersAction,
) -> None:
    parser = subparsers.add_parser(
        "store-backends",
        help="list storage/search backend capabilities and reserves",
    )
    parser.add_argument("--backend", choices=("json", "sqlite"))
    parser.add_argument("--path")
    parser.add_argument(
        "--probe-optional",
        action="store_true",
        help="check whether reserved optional backend packages are installed",
    )
    add_json_flag(parser)


__all__ = [
    "STORAGE_COMMANDS",
    "register_storage_commands",
    "run_storage_command",
]
