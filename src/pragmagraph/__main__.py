"""CLI entrypoint for the reusable ``pragmagraph`` package."""

from __future__ import annotations

import argparse
import json
import sys

from pragmagraph import PACKAGE_STATUS, STABLE_IMPORT_ROOTS, __version__
from pragmagraph.adapters import (
    DEFAULT_GIT_IDENTITY_MODE,
    SUPPORTED_GIT_IDENTITY_MODES,
    index_path,
)
from pragmagraph.bench import benchmark_root, render_markdown_benchmark
from pragmagraph.export import render_graph_export
from pragmagraph.graphify import (
    snapshot_from_graphify_payload,
    to_graphify_payload,
)
from pragmagraph.models import QueryRequest
from pragmagraph.operations import (
    build_refresh_plan,
    build_refresh_profile,
    load_refresh_profile,
    load_refresh_status,
    run_refresh_profile,
    save_refresh_profile,
)
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
from pragmagraph.refresh import load_manifest, refresh_snapshot, save_manifest
from pragmagraph.service import LocalQueryService, run_stdio_service
from pragmagraph.storage import load_snapshot, save_snapshot
from pragmagraph.ui import UiPreviewRequest, serve_ui_preview, write_ui_preview
from pragmagraph.workspace import (
    initialize_workspace,
    load_workspace_status,
    refresh_workspace,
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="pragmagraph package smoke")
    parser.add_argument("--json", action="store_true", help="emit JSON output")
    subparsers = parser.add_subparsers(dest="command")

    index_parser = subparsers.add_parser("index", help="index a local root")
    index_parser.add_argument("root")
    index_parser.add_argument("--out", required=True)
    index_parser.add_argument("--namespace", default="default")
    index_parser.add_argument(
        "--git-identity-mode",
        choices=tuple(sorted(SUPPORTED_GIT_IDENTITY_MODES)),
        default=DEFAULT_GIT_IDENTITY_MODE,
    )
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

    git_path_parser = subparsers.add_parser(
        "git-commits-for-path",
        help="show recent git commits affecting one relative path",
    )
    git_path_parser.add_argument("snapshot")
    git_path_parser.add_argument("path")
    git_path_parser.add_argument("--max-results", type=int, default=10)
    git_path_parser.add_argument("--json", action="store_true", help="emit JSON output")

    git_commit_parser = subparsers.add_parser(
        "git-files-for-commit",
        help="show current file/path nodes touched by one git commit",
    )
    git_commit_parser.add_argument("snapshot")
    git_commit_parser.add_argument("commit_ref")
    git_commit_parser.add_argument("--max-results", type=int, default=50)
    git_commit_parser.add_argument(
        "--json", action="store_true", help="emit JSON output"
    )

    git_symbol_parser = subparsers.add_parser(
        "git-commits-for-symbol",
        help="show recent git commits touching a symbol's containing file",
    )
    git_symbol_parser.add_argument("snapshot")
    git_symbol_parser.add_argument("symbol_node_id")
    git_symbol_parser.add_argument("--max-results", type=int, default=10)
    git_symbol_parser.add_argument(
        "--json", action="store_true", help="emit JSON output"
    )

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

    benchmark_parser = subparsers.add_parser(
        "benchmark", help="benchmark package operations against a local root"
    )
    benchmark_parser.add_argument("root")
    benchmark_parser.add_argument("--namespace", default="default")
    benchmark_parser.add_argument(
        "--git-identity-mode",
        choices=tuple(sorted(SUPPORTED_GIT_IDENTITY_MODES)),
        default=DEFAULT_GIT_IDENTITY_MODE,
    )
    benchmark_parser.add_argument("--query", default="README")
    benchmark_parser.add_argument("--max-results", type=int, default=10)
    benchmark_parser.add_argument("--top-n", type=int, default=10)
    benchmark_parser.add_argument(
        "--json", action="store_true", help="emit JSON output"
    )

    refresh_parser = subparsers.add_parser("refresh", help="refresh a local root")
    refresh_parser.add_argument("root")
    refresh_parser.add_argument("--out", required=True)
    refresh_parser.add_argument("--manifest-in")
    refresh_parser.add_argument("--manifest-out", required=True)
    refresh_parser.add_argument("--namespace", default="default")
    refresh_parser.add_argument(
        "--git-identity-mode",
        choices=tuple(sorted(SUPPORTED_GIT_IDENTITY_MODES)),
        default=DEFAULT_GIT_IDENTITY_MODE,
    )
    refresh_parser.add_argument("--json", action="store_true", help="emit JSON output")

    refresh_plan_parser = subparsers.add_parser(
        "refresh-plan",
        help="preview explicit refresh-visible path changes without mutating outputs",
    )
    refresh_plan_parser.add_argument("root")
    refresh_plan_parser.add_argument("--manifest-in")
    refresh_plan_parser.add_argument("--namespace", default="default")
    refresh_plan_parser.add_argument(
        "--json", action="store_true", help="emit JSON output"
    )

    refresh_status_parser = subparsers.add_parser(
        "refresh-status", help="inspect a persisted refresh status ledger"
    )
    refresh_status_parser.add_argument("state")
    refresh_status_parser.add_argument(
        "--json", action="store_true", help="emit JSON output"
    )

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
    profile_init_parser.add_argument(
        "--git-identity-mode",
        choices=tuple(sorted(SUPPORTED_GIT_IDENTITY_MODES)),
        default=DEFAULT_GIT_IDENTITY_MODE,
    )
    profile_init_parser.add_argument(
        "--json", action="store_true", help="emit JSON output"
    )

    profile_run_parser = subparsers.add_parser(
        "profile-run", help="run one explicit refresh from a saved invocation profile"
    )
    profile_run_parser.add_argument("profile")
    profile_run_parser.add_argument(
        "--json", action="store_true", help="emit JSON output"
    )

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

    serve_parser = subparsers.add_parser(
        "serve", help="run the local newline-delimited JSON service"
    )
    serve_group = serve_parser.add_mutually_exclusive_group(required=True)
    serve_group.add_argument("--snapshot")
    serve_group.add_argument("--root")
    serve_group.add_argument("--workspace")
    serve_parser.add_argument("--namespace", default="default")
    serve_parser.add_argument("--manifest-in")
    serve_parser.add_argument("--snapshot-out")
    serve_parser.add_argument("--manifest-out")
    serve_parser.add_argument("--state-out")
    serve_parser.add_argument(
        "--git-identity-mode",
        choices=tuple(sorted(SUPPORTED_GIT_IDENTITY_MODES)),
        default=DEFAULT_GIT_IDENTITY_MODE,
    )

    workspace_init_parser = subparsers.add_parser(
        "workspace-init",
        help="initialize a persistent local workspace directory",
    )
    workspace_init_parser.add_argument("root")
    workspace_init_parser.add_argument("--workspace", required=True)
    workspace_init_parser.add_argument("--label", default="default")
    workspace_init_parser.add_argument("--namespace", default="default")
    workspace_init_parser.add_argument(
        "--git-identity-mode",
        choices=tuple(sorted(SUPPORTED_GIT_IDENTITY_MODES)),
        default=DEFAULT_GIT_IDENTITY_MODE,
    )
    workspace_init_parser.add_argument(
        "--json", action="store_true", help="emit JSON output"
    )

    workspace_refresh_parser = subparsers.add_parser(
        "workspace-refresh",
        help="refresh a persistent local workspace directory",
    )
    workspace_refresh_parser.add_argument("workspace")
    workspace_refresh_parser.add_argument(
        "--json", action="store_true", help="emit JSON output"
    )

    workspace_status_parser = subparsers.add_parser(
        "workspace-status",
        help="inspect a persistent local workspace directory",
    )
    workspace_status_parser.add_argument("workspace")
    workspace_status_parser.add_argument(
        "--json", action="store_true", help="emit JSON output"
    )

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
    ui_parser.add_argument("--query", default="RuntimeGraph")
    ui_parser.add_argument("--node-id")
    ui_parser.add_argument("--source-id")
    ui_parser.add_argument("--target-id")
    ui_parser.add_argument("--open", action="store_true")
    ui_parser.add_argument("--serve", action="store_true")
    ui_parser.add_argument("--host", default="127.0.0.1")
    ui_parser.add_argument("--port", type=int, default=8766)
    ui_parser.add_argument("--json", action="store_true", help="emit JSON output")

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
        result = refresh_snapshot(
            args.root,
            namespace=args.namespace,
            previous_manifest=previous_manifest,
            git_identity_mode=args.git_identity_mode,
        )
        save_snapshot(result.snapshot, args.out)
        save_manifest(result.manifest, args.manifest_out)
        _print_payload(
            {
                "changed_paths": list(result.changed_paths),
                "unchanged_paths": list(result.unchanged_paths),
                "removed_paths": list(result.removed_paths),
                "path_changes": [item.to_dict() for item in result.path_changes],
                "snapshot_delta": result.snapshot_delta.to_dict(),
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
        if args.workspace:
            service = LocalQueryService.from_workspace(args.workspace)
        elif args.snapshot:
            service = LocalQueryService.from_snapshot_path(args.snapshot)
        else:
            service = LocalQueryService.from_root(
                args.root,
                namespace=args.namespace,
                manifest_path=args.manifest_in,
                snapshot_out_path=args.snapshot_out,
                manifest_out_path=args.manifest_out,
                state_out_path=args.state_out,
                git_identity_mode=args.git_identity_mode,
            )
        return run_stdio_service(service)
    elif args.command == "ui-preview":
        request = UiPreviewRequest(
            screen=args.screen,
            workspace=args.workspace,
            snapshot=args.snapshot,
            output_path=args.html_out,
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
