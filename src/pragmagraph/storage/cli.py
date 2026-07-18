"""CLI registration and execution for materialized store commands."""

from __future__ import annotations

import argparse

from pragmagraph.models import PragmaGraphError, QueryRequest
from pragmagraph.query import health
from pragmagraph.storage import (
    SQLiteGraphStore,
    explain_store_query,
    load_snapshot,
    save_snapshot,
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
        "store-update",
    }
)


def register_storage_commands(subparsers: argparse._SubParsersAction) -> None:
    """Register the bounded materialized-store command family."""
    import_parser = subparsers.add_parser(
        "store-import",
        help="import a canonical snapshot into a materialized graph store",
    )
    import_parser.add_argument("snapshot")
    import_parser.add_argument("--out", required=True)
    import_parser.add_argument("--backend", choices=("sqlite",), default="sqlite")
    _add_json_flag(import_parser)

    export_parser = subparsers.add_parser(
        "store-export",
        help="export a materialized graph store as canonical snapshot JSON",
    )
    export_parser.add_argument("store")
    export_parser.add_argument("--out")
    _add_json_flag(export_parser)

    health_parser = subparsers.add_parser(
        "store-health",
        help="summarize a materialized graph store",
    )
    health_parser.add_argument("store")
    _add_json_flag(health_parser)

    query_parser = subparsers.add_parser(
        "store-query",
        help="query a materialized graph store",
    )
    query_parser.add_argument("store")
    query_parser.add_argument("query")
    query_parser.add_argument("--max-results", type=int, default=10)
    query_parser.add_argument("--cursor", default="")
    query_parser.add_argument("--max-examined", type=int)
    _add_json_flag(query_parser)

    explain_parser = subparsers.add_parser(
        "store-search-explain",
        help="explain materialized-store search strategy and candidates",
    )
    explain_parser.add_argument("store")
    explain_parser.add_argument("query")
    explain_parser.add_argument("--max-results", type=int, default=10)
    explain_parser.add_argument("--max-examined", type=int)
    _add_json_flag(explain_parser)

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
    _add_json_flag(neighborhood_parser)

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
    _add_json_flag(path_parser)

    migrate_parser = subparsers.add_parser(
        "store-migrate", help="explicitly migrate a SQLite graph store"
    )
    migrate_parser.add_argument("store")
    _add_json_flag(migrate_parser)

    update_parser = subparsers.add_parser(
        "store-update", help="atomically apply a canonical snapshot delta"
    )
    update_parser.add_argument("store")
    update_parser.add_argument("snapshot")
    _add_json_flag(update_parser)


def run_storage_command(args: argparse.Namespace) -> object:
    """Execute one parsed materialized-store command."""
    if args.command == "store-import":
        if args.backend != "sqlite":
            raise PragmaGraphError(
                "unsupported store backend",
                code="STORE_BACKEND_UNSUPPORTED",
                details={"backend": args.backend},
            )
        store = SQLiteGraphStore.from_snapshot(load_snapshot(args.snapshot), args.out)
        return _store_payload(store)
    if args.command == "store-export":
        snapshot = SQLiteGraphStore(args.store).export_snapshot()
        if args.out:
            save_snapshot(snapshot, args.out)
            return health(snapshot).to_dict()
        return snapshot.to_dict()
    if args.command == "store-health":
        return _store_payload(SQLiteGraphStore(args.store))
    if args.command == "store-query":
        return SQLiteGraphStore(args.store).query(_query_request(args)).to_dict()
    if args.command == "store-search-explain":
        return explain_store_query(SQLiteGraphStore(args.store), _query_request(args))
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
    if args.command == "store-update":
        report = SQLiteGraphStore(args.store).apply_snapshot_delta(
            load_snapshot(args.snapshot)
        )
        return report.to_dict()
    raise PragmaGraphError(
        "unsupported store command",
        code="UNSUPPORTED_STORE_COMMAND",
        details={"command": args.command},
    )


def _query_request(args: argparse.Namespace) -> QueryRequest:
    return QueryRequest(
        query=args.query,
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


def _add_json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="emit JSON output")


__all__ = [
    "STORAGE_COMMANDS",
    "register_storage_commands",
    "run_storage_command",
]
