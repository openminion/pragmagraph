"""CLI entrypoint for the reusable ``pragmagraph`` package."""

from __future__ import annotations

import argparse
import json

from pragmagraph import PACKAGE_STATUS, STABLE_IMPORT_ROOTS, __version__
from pragmagraph.adapters import index_path
from pragmagraph.models import QueryRequest
from pragmagraph.query import health, neighborhood, path, query
from pragmagraph.storage import load_snapshot, save_snapshot


def smoke_payload() -> dict[str, object]:
    """Return a deterministic package smoke payload."""
    return {
        "package": "pragmagraph",
        "version": __version__,
        "status": PACKAGE_STATUS,
        "stable_import_roots": list(STABLE_IMPORT_ROOTS),
        "semantic_contract": True,
        "openminion_imports": False,
    }


def _print_payload(payload: object, *, as_json: bool) -> None:
    if as_json:
        if hasattr(payload, "to_dict"):
            payload = payload.to_dict()
        print(json.dumps(payload, sort_keys=True))
        return
    print(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="pragmagraph package smoke")
    parser.add_argument("--json", action="store_true", help="emit JSON output")
    subparsers = parser.add_subparsers(dest="command")

    index_parser = subparsers.add_parser("index", help="index a local root")
    index_parser.add_argument("root")
    index_parser.add_argument("--out", required=True)
    index_parser.add_argument("--namespace", default="default")
    index_parser.add_argument("--json", action="store_true", help="emit JSON output")

    query_parser = subparsers.add_parser("query", help="query a snapshot")
    query_parser.add_argument("snapshot")
    query_parser.add_argument("query")
    query_parser.add_argument("--max-results", type=int, default=10)
    query_parser.add_argument("--json", action="store_true", help="emit JSON output")

    neighborhood_parser = subparsers.add_parser(
        "neighborhood", help="show nodes around a snapshot node"
    )
    neighborhood_parser.add_argument("snapshot")
    neighborhood_parser.add_argument("node_id")
    neighborhood_parser.add_argument("--depth", type=int, default=1)
    neighborhood_parser.add_argument("--max-results", type=int, default=10)
    neighborhood_parser.add_argument(
        "--json", action="store_true", help="emit JSON output"
    )

    path_parser = subparsers.add_parser("path", help="find a bounded graph path")
    path_parser.add_argument("snapshot")
    path_parser.add_argument("source_id")
    path_parser.add_argument("target_id")
    path_parser.add_argument("--max-hops", type=int, default=4)
    path_parser.add_argument("--json", action="store_true", help="emit JSON output")

    health_parser = subparsers.add_parser("health", help="summarize a snapshot")
    health_parser.add_argument("snapshot")
    health_parser.add_argument("--json", action="store_true", help="emit JSON output")

    args = parser.parse_args(argv)

    if args.command == "index":
        snapshot = index_path(args.root, namespace=args.namespace)
        save_snapshot(snapshot, args.out)
        _print_payload(health(snapshot), as_json=args.json)
    elif args.command == "query":
        snapshot = load_snapshot(args.snapshot)
        _print_payload(
            query(
                snapshot,
                QueryRequest(query=args.query, max_results=args.max_results),
            ).to_dict(),
            as_json=True,
        )
    elif args.command == "neighborhood":
        snapshot = load_snapshot(args.snapshot)
        _print_payload(
            neighborhood(
                snapshot,
                args.node_id,
                depth=args.depth,
                max_results=args.max_results,
            ).to_dict(),
            as_json=True,
        )
    elif args.command == "path":
        snapshot = load_snapshot(args.snapshot)
        _print_payload(
            path(
                snapshot,
                args.source_id,
                args.target_id,
                max_hops=args.max_hops,
            ).to_dict(),
            as_json=True,
        )
    elif args.command == "health":
        snapshot = load_snapshot(args.snapshot)
        _print_payload(health(snapshot), as_json=True)
    elif args.json:
        print(json.dumps(smoke_payload(), sort_keys=True))
    else:
        print(f"pragmagraph semantic alpha OK: {smoke_payload()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
