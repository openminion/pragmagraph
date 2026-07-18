"""CLI entrypoint for the reusable ``pragmagraph`` package."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

from pragmagraph import PACKAGE_STATUS, STABLE_IMPORT_ROOTS, __version__
from pragmagraph.adapters import (
    DEFAULT_GIT_IDENTITY_MODE,
    SUPPORTED_GIT_IDENTITY_MODES,
    index_path,
)
from pragmagraph.bench import benchmark_root, render_markdown_benchmark
from pragmagraph.certification import build_certification_pack
from pragmagraph.docgraph import build_doc_graph_summary, render_markdown_doc_graph
from pragmagraph.export import EXPORT_PROFILES, project_snapshot, render_graph_export
from pragmagraph.graphify import (
    snapshot_from_graphify_payload,
    to_graphify_payload,
)
from pragmagraph.interchange import (
    build_symbol_reference_bundle,
    load_native_scip,
    merge_precise_snapshot,
)
from pragmagraph.incremental import load_extraction_cache, save_extraction_cache
from pragmagraph.lineage import build_git_lineage
from pragmagraph.models import PragmaGraphError, QueryRequest
from pragmagraph.navigation import (
    build_repo_map,
    render_compact_handoff,
    render_markdown_repo_map,
)
from pragmagraph.operations import (
    build_refresh_plan,
    build_refresh_profile,
    load_refresh_profile,
    load_refresh_status,
    run_refresh_profile,
    save_refresh_profile,
)
from pragmagraph.parser_support import build_parser_support_matrix
from pragmagraph.planner import explain_query_plan
from pragmagraph.query import (
    commits_touching_symbol_file,
    files_touched_by_commit,
    health,
    neighborhood,
    path,
    query,
    recent_commits_for_path,
)
from pragmagraph.report import build_report, render_markdown_report
from pragmagraph.refresh import (
    build_ci_delta,
    load_manifest,
    refresh_snapshot,
    refresh_snapshot_incremental,
    save_manifest,
)
from pragmagraph.service import LocalQueryService, run_stdio_service
from pragmagraph.storage import SQLiteGraphStore, load_snapshot, save_snapshot
from pragmagraph.topology import build_topology_summary, render_markdown_topology
from pragmagraph.viewer.cli import (
    VIEWER_COMMANDS,
    register_viewer_commands,
    run_viewer_command,
)
from pragmagraph.workspace import (
    initialize_workspace,
    load_workspace_status,
    refresh_workspace,
)
from pragmagraph.workspace.cli import (
    WORKSPACE_COMMANDS,
    register_workspace_commands,
    run_workspace_command,
)


def smoke_payload() -> dict[str, object]:
    """Return a deterministic package smoke payload."""
    return {
        "package": "pragmagraph",
        "version": __version__,
        "status": PACKAGE_STATUS,
        "stable_import_roots": list(STABLE_IMPORT_ROOTS),
        "semantic_contract": True,
        "openminion_imports": False,
        "git_identity_mode_default": DEFAULT_GIT_IDENTITY_MODE,
    }


def _print_payload(payload: object, *, as_json: bool) -> None:
    if as_json:
        if hasattr(payload, "to_dict"):
            payload = payload.to_dict()
        print(json.dumps(payload, sort_keys=True))
        return
    print(payload)


def _add_json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="emit JSON output")


def _add_git_identity_mode_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--git-identity-mode",
        choices=tuple(sorted(SUPPORTED_GIT_IDENTITY_MODES)),
        default=DEFAULT_GIT_IDENTITY_MODE,
    )


def _store_payload(store: SQLiteGraphStore) -> dict[str, object]:
    return {
        "manifest": store.manifest().to_dict(),
        "capabilities": store.capabilities().to_dict(),
        "health": store.health().to_dict(),
    }


def _service_from_args(args: argparse.Namespace) -> LocalQueryService:
    if args.workspace:
        return LocalQueryService.from_workspace(args.workspace)
    if args.store:
        return LocalQueryService.from_store_path(args.store)
    if args.snapshot:
        return LocalQueryService.from_snapshot_path(args.snapshot)
    return LocalQueryService.from_root(
        args.root,
        namespace=args.namespace,
        manifest_path=args.manifest_in,
        snapshot_out_path=args.snapshot_out,
        manifest_out_path=args.manifest_out,
        state_out_path=args.state_out,
        cache_path=args.cache,
        git_identity_mode=args.git_identity_mode,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="pragmagraph package smoke")
    _add_json_flag(parser)
    subparsers = parser.add_subparsers(dest="command")

    index_parser = subparsers.add_parser("index", help="index a local root")
    index_parser.add_argument("root")
    index_parser.add_argument("--out", required=True)
    index_parser.add_argument("--namespace", default="default")
    _add_git_identity_mode_argument(index_parser)
    _add_json_flag(index_parser)

    query_parser = subparsers.add_parser("query", help="query a snapshot")
    query_parser.add_argument("snapshot")
    query_parser.add_argument("query")
    query_parser.add_argument("--max-results", type=int, default=10)
    query_parser.add_argument("--cursor", default="")
    query_parser.add_argument("--max-examined", type=int)
    _add_json_flag(query_parser)

    ci_delta_parser = subparsers.add_parser(
        "ci-delta",
        help="compare two canonical snapshots for CI",
    )
    ci_delta_parser.add_argument("before")
    ci_delta_parser.add_argument("after")
    ci_delta_parser.add_argument("--fail-on-changes", action="store_true")
    _add_json_flag(ci_delta_parser)

    explain_parser = subparsers.add_parser(
        "explain", help="query with score explanations"
    )
    explain_parser.add_argument("snapshot")
    explain_parser.add_argument("query")
    explain_parser.add_argument("--max-results", type=int, default=10)
    explain_parser.add_argument("--cursor", default="")
    explain_parser.add_argument("--max-examined", type=int)
    _add_json_flag(explain_parser)

    git_path_parser = subparsers.add_parser(
        "git-commits-for-path",
        help="show recent git commits affecting one relative path",
    )
    git_path_parser.add_argument("snapshot")
    git_path_parser.add_argument("path")
    git_path_parser.add_argument("--max-results", type=int, default=10)
    _add_json_flag(git_path_parser)

    git_commit_parser = subparsers.add_parser(
        "git-files-for-commit",
        help="show current file/path nodes touched by one git commit",
    )
    git_commit_parser.add_argument("snapshot")
    git_commit_parser.add_argument("commit_ref")
    git_commit_parser.add_argument("--max-results", type=int, default=50)
    _add_json_flag(git_commit_parser)

    git_symbol_parser = subparsers.add_parser(
        "git-commits-for-symbol",
        help="show recent git commits touching a symbol's containing file",
    )
    git_symbol_parser.add_argument("snapshot")
    git_symbol_parser.add_argument("symbol_node_id")
    git_symbol_parser.add_argument("--max-results", type=int, default=10)
    _add_json_flag(git_symbol_parser)

    report_parser = subparsers.add_parser(
        "report", help="build a deterministic structural report"
    )
    report_parser.add_argument("snapshot")
    report_parser.add_argument("--top-n", type=int, default=10)
    _add_json_flag(report_parser)

    repo_map_parser = subparsers.add_parser(
        "repo-map", help="render a compact repository navigation map"
    )
    repo_map_parser.add_argument("snapshot")
    repo_map_parser.add_argument("--top-n", type=int, default=8)
    repo_map_parser.add_argument(
        "--handoff",
        action="store_true",
        help="render the shorter agent handoff view",
    )
    _add_json_flag(repo_map_parser)

    topology_parser = subparsers.add_parser(
        "topology", help="summarize structural graph topology"
    )
    topology_parser.add_argument("snapshot")
    topology_parser.add_argument("--top-n", type=int, default=10)
    _add_json_flag(topology_parser)

    doc_graph_parser = subparsers.add_parser(
        "doc-graph", help="summarize document backlinks and mention candidates"
    )
    doc_graph_parser.add_argument("snapshot")
    doc_graph_parser.add_argument("--top-n", type=int, default=10)
    _add_json_flag(doc_graph_parser)

    interchange_parser = subparsers.add_parser(
        "interchange", help="emit stable symbol/reference interchange JSON"
    )
    interchange_parser.add_argument("snapshot")

    precise_import_parser = subparsers.add_parser(
        "precise-import",
        help="import an externally produced native SCIP index",
    )
    precise_import_parser.add_argument("scip_index")
    precise_import_parser.add_argument("--out", required=True)
    precise_import_parser.add_argument("--base")
    precise_import_parser.add_argument("--root", default="")
    precise_import_parser.add_argument("--namespace", default="scip")
    precise_import_parser.add_argument("--index-commit", default="")
    precise_import_parser.add_argument("--workspace-commit", default="")
    precise_import_parser.add_argument("--strict-freshness", action="store_true")
    _add_json_flag(precise_import_parser)

    query_plan_parser = subparsers.add_parser(
        "query-plan", help="explain deterministic query execution facts"
    )
    query_plan_parser.add_argument("snapshot")
    query_plan_parser.add_argument("query")
    query_plan_parser.add_argument("--max-results", type=int, default=10)

    lineage_parser = subparsers.add_parser(
        "git-lineage", help="show observed git path lineage"
    )
    lineage_parser.add_argument("snapshot")
    lineage_parser.add_argument("path")
    lineage_parser.add_argument("--max-results", type=int, default=20)

    parser_support_parser = subparsers.add_parser(
        "parser-support", help="show parser family support matrix"
    )
    _add_json_flag(parser_support_parser)

    certify_parser = subparsers.add_parser(
        "certify", help="emit snapshot certification facts"
    )
    certify_parser.add_argument("snapshot")
    certify_parser.add_argument("--top-n", type=int, default=10)

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
    export_parser.add_argument(
        "--profile", choices=tuple(sorted(EXPORT_PROFILES)), default="full"
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

    store_import_parser = subparsers.add_parser(
        "store-import",
        help="import a canonical snapshot into a materialized graph store",
    )
    store_import_parser.add_argument("snapshot")
    store_import_parser.add_argument("--out", required=True)
    store_import_parser.add_argument(
        "--backend",
        choices=("sqlite",),
        default="sqlite",
    )
    _add_json_flag(store_import_parser)

    store_export_parser = subparsers.add_parser(
        "store-export",
        help="export a materialized graph store as canonical snapshot JSON",
    )
    store_export_parser.add_argument("store")
    store_export_parser.add_argument("--out")
    _add_json_flag(store_export_parser)

    store_health_parser = subparsers.add_parser(
        "store-health",
        help="summarize a materialized graph store",
    )
    store_health_parser.add_argument("store")
    _add_json_flag(store_health_parser)

    store_query_parser = subparsers.add_parser(
        "store-query",
        help="query a materialized graph store",
    )
    store_query_parser.add_argument("store")
    store_query_parser.add_argument("query")
    store_query_parser.add_argument("--max-results", type=int, default=10)
    store_query_parser.add_argument("--cursor", default="")
    store_query_parser.add_argument("--max-examined", type=int)
    _add_json_flag(store_query_parser)

    store_neighborhood_parser = subparsers.add_parser(
        "store-neighborhood",
        help="show nodes around a materialized-store node",
    )
    store_neighborhood_parser.add_argument("store")
    store_neighborhood_parser.add_argument("node_id")
    store_neighborhood_parser.add_argument("--depth", type=int, default=1)
    store_neighborhood_parser.add_argument("--max-results", type=int, default=10)
    store_neighborhood_parser.add_argument("--edge-kind", action="append", default=[])
    store_neighborhood_parser.add_argument("--node-kind", action="append", default=[])
    _add_json_flag(store_neighborhood_parser)

    store_path_parser = subparsers.add_parser(
        "store-path",
        help="find a bounded path in a materialized graph store",
    )
    store_path_parser.add_argument("store")
    store_path_parser.add_argument("source_id")
    store_path_parser.add_argument("target_id")
    store_path_parser.add_argument("--max-hops", type=int, default=4)
    store_path_parser.add_argument("--edge-kind", action="append", default=[])
    store_path_parser.add_argument("--node-kind", action="append", default=[])
    _add_json_flag(store_path_parser)

    store_migrate_parser = subparsers.add_parser(
        "store-migrate", help="explicitly migrate a SQLite graph store"
    )
    store_migrate_parser.add_argument("store")
    _add_json_flag(store_migrate_parser)

    store_update_parser = subparsers.add_parser(
        "store-update", help="atomically apply a canonical snapshot delta"
    )
    store_update_parser.add_argument("store")
    store_update_parser.add_argument("snapshot")
    _add_json_flag(store_update_parser)

    benchmark_parser = subparsers.add_parser(
        "benchmark", help="benchmark package operations against a local root"
    )
    benchmark_parser.add_argument("root")
    benchmark_parser.add_argument("--namespace", default="default")
    _add_git_identity_mode_argument(benchmark_parser)
    benchmark_parser.add_argument("--query", default="README")
    benchmark_parser.add_argument("--max-results", type=int, default=10)
    benchmark_parser.add_argument("--top-n", type=int, default=10)
    _add_json_flag(benchmark_parser)

    refresh_parser = subparsers.add_parser("refresh", help="refresh a local root")
    refresh_parser.add_argument("root")
    refresh_parser.add_argument("--out", required=True)
    refresh_parser.add_argument("--manifest-in")
    refresh_parser.add_argument("--manifest-out", required=True)
    refresh_parser.add_argument("--cache-in")
    refresh_parser.add_argument("--cache-out")
    refresh_parser.add_argument("--namespace", default="default")
    _add_git_identity_mode_argument(refresh_parser)
    _add_json_flag(refresh_parser)

    refresh_plan_parser = subparsers.add_parser(
        "refresh-plan",
        help="preview explicit refresh-visible path changes without mutating outputs",
    )
    refresh_plan_parser.add_argument("root")
    refresh_plan_parser.add_argument("--manifest-in")
    refresh_plan_parser.add_argument("--namespace", default="default")
    _add_json_flag(refresh_plan_parser)

    refresh_status_parser = subparsers.add_parser(
        "refresh-status", help="inspect a persisted refresh status ledger"
    )
    refresh_status_parser.add_argument("state")
    _add_json_flag(refresh_status_parser)

    profile_init_parser = subparsers.add_parser(
        "profile-init", help="write a repeatable explicit-refresh invocation profile"
    )
    profile_init_parser.add_argument("root")
    profile_init_parser.add_argument("--out", required=True)
    profile_init_parser.add_argument("--label", default="default")
    profile_init_parser.add_argument("--namespace", default="default")
    profile_init_parser.add_argument("--snapshot-out", required=True)
    profile_init_parser.add_argument("--manifest-out", required=True)
    profile_init_parser.add_argument("--state-out", required=True)
    profile_init_parser.add_argument("--cache-out")
    _add_git_identity_mode_argument(profile_init_parser)
    _add_json_flag(profile_init_parser)

    profile_run_parser = subparsers.add_parser(
        "profile-run", help="run one explicit refresh from a saved invocation profile"
    )
    profile_run_parser.add_argument("profile")
    _add_json_flag(profile_run_parser)

    neighborhood_parser = subparsers.add_parser(
        "neighborhood", help="show nodes around a snapshot node"
    )
    neighborhood_parser.add_argument("snapshot")
    neighborhood_parser.add_argument("node_id")
    neighborhood_parser.add_argument("--depth", type=int, default=1)
    neighborhood_parser.add_argument("--max-results", type=int, default=10)
    _add_json_flag(neighborhood_parser)

    path_parser = subparsers.add_parser("path", help="find a bounded graph path")
    path_parser.add_argument("snapshot")
    path_parser.add_argument("source_id")
    path_parser.add_argument("target_id")
    path_parser.add_argument("--max-hops", type=int, default=4)
    _add_json_flag(path_parser)

    health_parser = subparsers.add_parser("health", help="summarize a snapshot")
    health_parser.add_argument("snapshot")
    _add_json_flag(health_parser)

    serve_parser = subparsers.add_parser(
        "serve", help="run the local newline-delimited JSON service"
    )
    serve_group = serve_parser.add_mutually_exclusive_group(required=True)
    serve_group.add_argument("--snapshot")
    serve_group.add_argument("--root")
    serve_group.add_argument("--workspace")
    serve_group.add_argument("--store")
    serve_parser.add_argument("--namespace", default="default")
    serve_parser.add_argument("--manifest-in")
    serve_parser.add_argument("--snapshot-out")
    serve_parser.add_argument("--manifest-out")
    serve_parser.add_argument("--state-out")
    serve_parser.add_argument("--cache")
    _add_git_identity_mode_argument(serve_parser)

    workspace_init_parser = subparsers.add_parser(
        "workspace-init",
        help="initialize a persistent local workspace directory",
    )
    workspace_init_parser.add_argument("root")
    workspace_init_parser.add_argument("--workspace", required=True)
    workspace_init_parser.add_argument("--label", default="default")
    workspace_init_parser.add_argument("--namespace", default="default")
    _add_git_identity_mode_argument(workspace_init_parser)
    _add_json_flag(workspace_init_parser)

    workspace_refresh_parser = subparsers.add_parser(
        "workspace-refresh",
        help="refresh a persistent local workspace directory",
    )
    workspace_refresh_parser.add_argument("workspace")
    _add_json_flag(workspace_refresh_parser)

    workspace_status_parser = subparsers.add_parser(
        "workspace-status",
        help="inspect a persistent local workspace directory",
    )
    workspace_status_parser.add_argument("workspace")
    _add_json_flag(workspace_status_parser)

    ui_parser = subparsers.add_parser(
        "ui-preview",
        help="open the package-local visual graph preview",
    )
    ui_parser.add_argument("--workspace")
    ui_parser.add_argument("--snapshot")
    ui_parser.add_argument(
        "--screen",
        choices=(
            "search",
            "result_detail",
            "neighborhood",
            "path",
            "provider_status",
        ),
        default="search",
    )
    ui_parser.add_argument("--html-out", default="pragmagraph-ui-preview.html")
    ui_parser.add_argument("--artifact-out", default="")
    ui_parser.add_argument("--embed-out", default="")
    ui_parser.add_argument("--report-out", default="")
    ui_parser.add_argument("--markdown-report-out", default="")
    ui_parser.add_argument("--query", default="RuntimeGraph")
    ui_parser.add_argument("--node-id")
    ui_parser.add_argument("--source-id")
    ui_parser.add_argument("--target-id")
    ui_parser.add_argument("--open", action="store_true")
    ui_parser.add_argument("--serve", action="store_true")
    ui_parser.add_argument("--host", default="127.0.0.1")
    ui_parser.add_argument("--port", type=int, default=8766)
    _add_json_flag(ui_parser)

    register_workspace_commands(subparsers)
    register_viewer_commands(subparsers)

    args = parser.parse_args(argv)

    if args.command == "index":
        snapshot = index_path(
            args.root,
            namespace=args.namespace,
            git_identity_mode=args.git_identity_mode,
        )
        save_snapshot(snapshot, args.out)
        _print_payload(health(snapshot), as_json=args.json)
    elif args.command == "query":
        snapshot = load_snapshot(args.snapshot)
        _print_payload(
            query(
                snapshot,
                QueryRequest(
                    query=args.query,
                    max_results=args.max_results,
                    cursor=args.cursor,
                    max_examined=args.max_examined,
                ),
            ).to_dict(),
            as_json=True,
        )
    elif args.command in WORKSPACE_COMMANDS:
        _print_payload(
            run_workspace_command(args, parser),
            as_json=args.json,
        )
    elif args.command == "ci-delta":
        report = build_ci_delta(
            load_snapshot(args.before),
            load_snapshot(args.after),
            fail_on_changes=args.fail_on_changes,
        )
        _print_payload(report.to_dict(), as_json=True)
        return report.exit_code
    elif args.command == "explain":
        snapshot = load_snapshot(args.snapshot)
        result = query(
            snapshot,
            QueryRequest(
                query=args.query,
                max_results=args.max_results,
                cursor=args.cursor,
                max_examined=args.max_examined,
            ),
        )
        _print_payload(result.to_dict(), as_json=True)
    elif args.command == "git-commits-for-path":
        snapshot = load_snapshot(args.snapshot)
        _print_payload(
            recent_commits_for_path(
                snapshot,
                args.path,
                max_results=args.max_results,
            ).to_dict(),
            as_json=True,
        )
    elif args.command == "git-files-for-commit":
        snapshot = load_snapshot(args.snapshot)
        _print_payload(
            files_touched_by_commit(
                snapshot,
                args.commit_ref,
                max_results=args.max_results,
            ).to_dict(),
            as_json=True,
        )
    elif args.command == "git-commits-for-symbol":
        snapshot = load_snapshot(args.snapshot)
        _print_payload(
            commits_touching_symbol_file(
                snapshot,
                args.symbol_node_id,
                max_results=args.max_results,
            ).to_dict(),
            as_json=True,
        )
    elif args.command == "report":
        snapshot = load_snapshot(args.snapshot)
        report = build_report(snapshot, top_n=args.top_n)
        if args.json:
            _print_payload(report.to_dict(), as_json=True)
        else:
            print(render_markdown_report(report), end="")
    elif args.command == "repo-map":
        snapshot = load_snapshot(args.snapshot)
        repo_map = build_repo_map(snapshot, top_n=args.top_n)
        if args.json:
            _print_payload(repo_map.to_dict(), as_json=True)
        elif args.handoff:
            print(render_compact_handoff(snapshot, top_n=args.top_n), end="")
        else:
            print(render_markdown_repo_map(repo_map), end="")
    elif args.command == "topology":
        snapshot = load_snapshot(args.snapshot)
        summary = build_topology_summary(snapshot, top_n=args.top_n)
        if args.json:
            _print_payload(summary.to_dict(), as_json=True)
        else:
            print(render_markdown_topology(summary), end="")
    elif args.command == "doc-graph":
        snapshot = load_snapshot(args.snapshot)
        summary = build_doc_graph_summary(snapshot, top_n=args.top_n)
        if args.json:
            _print_payload(summary.to_dict(), as_json=True)
        else:
            print(render_markdown_doc_graph(summary), end="")
    elif args.command == "interchange":
        snapshot = load_snapshot(args.snapshot)
        _print_payload(build_symbol_reference_bundle(snapshot), as_json=True)
    elif args.command == "precise-import":
        base = load_snapshot(args.base) if args.base else None
        namespace = base.namespace if base is not None else args.namespace
        imported = load_native_scip(
            args.scip_index,
            namespace=namespace,
            root_path=args.root,
            index_commit=args.index_commit,
            workspace_commit=args.workspace_commit,
            strict_freshness=args.strict_freshness,
        )
        snapshot = (
            merge_precise_snapshot(base, imported.snapshot)
            if base is not None
            else imported.snapshot
        )
        save_snapshot(snapshot, args.out)
        _print_payload(
            {
                "output": str(args.out),
                "merged": base is not None,
                "report": imported.report.to_dict(),
                "health": health(snapshot).to_dict(),
            },
            as_json=True,
        )
    elif args.command == "query-plan":
        snapshot = load_snapshot(args.snapshot)
        _print_payload(
            explain_query_plan(
                snapshot,
                QueryRequest(
                    query=args.query,
                    max_results=args.max_results,
                ),
            ),
            as_json=True,
        )
    elif args.command == "git-lineage":
        snapshot = load_snapshot(args.snapshot)
        _print_payload(
            build_git_lineage(snapshot, args.path, max_results=args.max_results),
            as_json=True,
        )
    elif args.command == "parser-support":
        _print_payload(
            [item.to_dict() for item in build_parser_support_matrix()],
            as_json=True,
        )
    elif args.command == "certify":
        snapshot = load_snapshot(args.snapshot)
        _print_payload(
            build_certification_pack(snapshot, top_n=args.top_n),
            as_json=True,
        )
    elif args.command == "export":
        snapshot = load_snapshot(args.snapshot)
        projection = project_snapshot(snapshot, profile=args.profile)
        print(render_graph_export(projection.snapshot, format=args.format), end="")
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
    elif args.command == "store-import":
        snapshot = load_snapshot(args.snapshot)
        if args.backend != "sqlite":
            raise ValueError(f"unsupported store backend: {args.backend}")
        store = SQLiteGraphStore.from_snapshot(snapshot, args.out)
        _print_payload(_store_payload(store), as_json=True)
    elif args.command == "store-export":
        store = SQLiteGraphStore(args.store)
        snapshot = store.export_snapshot()
        if args.out:
            save_snapshot(snapshot, args.out)
            _print_payload(health(snapshot), as_json=True)
        else:
            _print_payload(snapshot.to_dict(), as_json=True)
    elif args.command == "store-health":
        store = SQLiteGraphStore(args.store)
        _print_payload(_store_payload(store), as_json=True)
    elif args.command == "store-query":
        store = SQLiteGraphStore(args.store)
        _print_payload(
            store.query(
                QueryRequest(query=args.query, max_results=args.max_results),
            ).to_dict(),
            as_json=True,
        )
    elif args.command == "store-neighborhood":
        store = SQLiteGraphStore(args.store)
        _print_payload(
            store.neighborhood(
                args.node_id,
                depth=args.depth,
                max_results=args.max_results,
                edge_kinds=tuple(args.edge_kind),
                node_kinds=tuple(args.node_kind),
            ).to_dict(),
            as_json=True,
        )
    elif args.command == "store-path":
        store = SQLiteGraphStore(args.store)
        _print_payload(
            store.path(
                args.source_id,
                args.target_id,
                max_hops=args.max_hops,
                edge_kinds=tuple(args.edge_kind),
                node_kinds=tuple(args.node_kind),
            ).to_dict(),
            as_json=True,
        )
    elif args.command == "store-migrate":
        store = SQLiteGraphStore(args.store)
        _print_payload(store.migrate().to_dict(), as_json=True)
    elif args.command == "store-update":
        store = SQLiteGraphStore(args.store)
        report = store.apply_snapshot_delta(load_snapshot(args.snapshot))
        _print_payload(report.to_dict(), as_json=True)
    elif args.command == "benchmark":
        report = benchmark_root(
            args.root,
            namespace=args.namespace,
            query_text=args.query,
            max_results=args.max_results,
            top_n=args.top_n,
            git_identity_mode=args.git_identity_mode,
        )
        if args.json:
            _print_payload(report.to_dict(), as_json=True)
        else:
            print(render_markdown_benchmark(report), end="")
    elif args.command == "refresh":
        previous_manifest = (
            load_manifest(args.manifest_in) if args.manifest_in else None
        )
        previous_snapshot = load_snapshot(args.out) if Path(args.out).exists() else None
        if args.cache_in or args.cache_out:
            previous_cache = None
            fallback_reason = ""
            if args.cache_in and Path(args.cache_in).exists():
                try:
                    previous_cache = load_extraction_cache(args.cache_in)
                except PragmaGraphError as exc:
                    fallback_reason = exc.code.lower()
            result, next_cache = refresh_snapshot_incremental(
                args.root,
                namespace=args.namespace,
                previous_manifest=previous_manifest,
                previous_snapshot=previous_snapshot,
                previous_cache=previous_cache,
                git_identity_mode=args.git_identity_mode,
            )
            if fallback_reason:
                result = replace(
                    result,
                    work=replace(result.work, cache_fallback_reason=fallback_reason),
                )
        else:
            result = refresh_snapshot(
                args.root,
                namespace=args.namespace,
                previous_manifest=previous_manifest,
                previous_snapshot=previous_snapshot,
                git_identity_mode=args.git_identity_mode,
            )
        save_snapshot(result.snapshot, args.out)
        save_manifest(result.manifest, args.manifest_out)
        if args.cache_out:
            save_extraction_cache(next_cache, args.cache_out)
        _print_payload(
            {
                "changed_paths": list(result.changed_paths),
                "unchanged_paths": list(result.unchanged_paths),
                "removed_paths": list(result.removed_paths),
                "path_changes": [item.to_dict() for item in result.path_changes],
                "snapshot_delta": result.snapshot_delta.to_dict(),
                "identity_transitions": [
                    item.to_dict() for item in result.identity_transitions
                ],
                "work": result.work.to_dict(),
                "health": health(result.snapshot).to_dict(),
            },
            as_json=args.json,
        )
    elif args.command == "refresh-plan":
        previous_manifest = (
            load_manifest(args.manifest_in) if args.manifest_in else None
        )
        plan = build_refresh_plan(
            args.root,
            namespace=args.namespace,
            previous_manifest=previous_manifest,
        )
        _print_payload(plan.to_dict(), as_json=True)
    elif args.command == "refresh-status":
        status = load_refresh_status(args.state)
        _print_payload(status.to_dict(), as_json=True)
    elif args.command == "workspace-init":
        result = initialize_workspace(
            label=args.label,
            root_path=args.root,
            workspace_path=args.workspace,
            namespace=args.namespace,
            git_identity_mode=args.git_identity_mode,
        )
        _print_payload(result.to_dict(), as_json=True)
    elif args.command == "workspace-refresh":
        result = refresh_workspace(args.workspace)
        _print_payload(result.to_dict(), as_json=True)
    elif args.command == "workspace-status":
        status = load_workspace_status(args.workspace)
        _print_payload(status.to_dict(), as_json=True)
    elif args.command == "profile-init":
        profile = build_refresh_profile(
            label=args.label,
            root_path=args.root,
            snapshot_path=args.snapshot_out,
            manifest_path=args.manifest_out,
            state_path=args.state_out,
            cache_path=args.cache_out or "",
            namespace=args.namespace,
            git_identity_mode=args.git_identity_mode,
        )
        save_refresh_profile(profile, args.out)
        _print_payload(profile.to_dict(), as_json=True)
    elif args.command == "profile-run":
        profile = load_refresh_profile(args.profile)
        operation = run_refresh_profile(profile)
        _print_payload(operation.to_dict(), as_json=True)
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
    elif args.command == "serve":
        service = _service_from_args(args)
        return run_stdio_service(service)
    elif args.command == "ui-preview":
        from pragmagraph.ui import UiPreviewRequest, serve_ui_preview, write_ui_preview

        request = UiPreviewRequest(
            screen=args.screen,
            workspace=args.workspace,
            snapshot=args.snapshot,
            output_path=args.html_out,
            artifact_path=args.artifact_out,
            embed_path=args.embed_out,
            report_path=args.report_out,
            markdown_report_path=args.markdown_report_out,
            query=args.query,
            node_id=args.node_id,
            source_id=args.source_id,
            target_id=args.target_id,
            open_browser=args.open,
        )
        if args.serve:
            result = serve_ui_preview(
                request,
                host=args.host,
                port=args.port,
            )
            _print_payload(result.to_dict(), as_json=args.json)
            return 0
        result = write_ui_preview(request)
        _print_payload(result.to_dict(), as_json=args.json)
    elif args.command in VIEWER_COMMANDS:
        _print_payload(run_viewer_command(args), as_json=True)
    elif args.json:
        print(json.dumps(smoke_payload(), sort_keys=True))
    else:
        print(f"pragmagraph semantic alpha OK: {smoke_payload()}")
    return 0


def ui_preview_main(argv: list[str] | None = None) -> int:
    """Console entrypoint for the package-local visual graph preview."""
    return main(["ui-preview", *list(sys.argv[1:] if argv is None else argv)])


if __name__ == "__main__":
    raise SystemExit(main())
