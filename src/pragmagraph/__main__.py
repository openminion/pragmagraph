"""CLI entrypoint for the reusable ``pragmagraph`` package."""

from __future__ import annotations

import argparse
import json

from pragmagraph import PACKAGE_STATUS, STABLE_IMPORT_ROOTS, __version__
from pragmagraph.adapters import index_path
from pragmagraph.export import render_graph_export
from pragmagraph.graphify import (
    snapshot_from_graphify_payload,
    to_graphify_payload,
)
from pragmagraph.models import QueryRequest
from pragmagraph.query import health, neighborhood, path, query
from pragmagraph.report import build_report, render_markdown_report
from pragmagraph.refresh import load_manifest, refresh_snapshot, save_manifest
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

    explain_parser = subparsers.add_parser(
        "explain", help="query with score explanations"
    )
    explain_parser.add_argument("snapshot")
    explain_parser.add_argument("query")
    explain_parser.add_argument("--max-results", type=int, default=10)
    explain_parser.add_argument("--json", action="store_true", help="emit JSON output")

    report_parser = subparsers.add_parser(
        "report", help="build a deterministic structural report"
    )
    report_parser.add_argument("snapshot")
    report_parser.add_argument("--top-n", type=int, default=10)
    report_parser.add_argument("--json", action="store_true", help="emit JSON output")

    export_parser = subparsers.add_parser(
        "export", help="export a snapshot as graph text"
    )
    export_parser.add_argument("snapshot")
    export_parser.add_argument(
        "--format",
        choices=("dot", "mermaid"),
        default="dot",
        help="graph text format",
    )

    graphify_export_parser = subparsers.add_parser(
        "graphify-export", help="export a snapshot as Graphify-shaped JSON"
    )
    graphify_export_parser.add_argument("snapshot")

    graphify_import_parser = subparsers.add_parser(
        "graphify-import", help="import supported Graphify-shaped JSON"
    )
    graphify_import_parser.add_argument("payload")
    graphify_import_parser.add_argument("--out", required=True)
    graphify_import_parser.add_argument("--namespace", default="graphify")
    graphify_import_parser.add_argument("--root-path", default="")

    refresh_parser = subparsers.add_parser("refresh", help="refresh a local root")
    refresh_parser.add_argument("root")
    refresh_parser.add_argument("--out", required=True)
    refresh_parser.add_argument("--manifest-in")
    refresh_parser.add_argument("--manifest-out", required=True)
    refresh_parser.add_argument("--namespace", default="default")
    refresh_parser.add_argument("--json", action="store_true", help="emit JSON output")

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
    elif args.command == "explain":
        snapshot = load_snapshot(args.snapshot)
        result = query(
            snapshot,
            QueryRequest(query=args.query, max_results=args.max_results),
        )
        _print_payload(result.to_dict(), as_json=True)
    elif args.command == "report":
        snapshot = load_snapshot(args.snapshot)
        report = build_report(snapshot, top_n=args.top_n)
        if args.json:
            _print_payload(report.to_dict(), as_json=True)
        else:
            print(render_markdown_report(report), end="")
    elif args.command == "export":
        snapshot = load_snapshot(args.snapshot)
        print(render_graph_export(snapshot, format=args.format), end="")
    elif args.command == "graphify-export":
        snapshot = load_snapshot(args.snapshot)
        _print_payload(to_graphify_payload(snapshot), as_json=True)
    elif args.command == "graphify-import":
        with open(args.payload, encoding="utf-8") as graphify_payload:
            payload = json.load(graphify_payload)
        snapshot = snapshot_from_graphify_payload(
            payload,
            namespace=args.namespace,
            root_path=args.root_path,
        )
        save_snapshot(snapshot, args.out)
        _print_payload(health(snapshot), as_json=True)
    elif args.command == "refresh":
        previous_manifest = (
            load_manifest(args.manifest_in) if args.manifest_in else None
        )
        result = refresh_snapshot(
            args.root,
            namespace=args.namespace,
            previous_manifest=previous_manifest,
        )
        save_snapshot(result.snapshot, args.out)
        save_manifest(result.manifest, args.manifest_out)
        _print_payload(
            {
                "changed_paths": list(result.changed_paths),
                "unchanged_paths": list(result.unchanged_paths),
                "removed_paths": list(result.removed_paths),
                "health": health(result.snapshot).to_dict(),
            },
            as_json=args.json,
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
