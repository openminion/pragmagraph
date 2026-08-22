"""CLI entrypoint for the reusable ``pragmagraph`` package."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

from pragmagraph import PACKAGE_STATUS, STABLE_IMPORT_ROOTS, __version__
from pragmagraph.adapters import DEFAULT_GIT_IDENTITY_MODE, index_path
from pragmagraph.bench import benchmark_root, render_markdown_benchmark
from pragmagraph.cli import (
    add_json_flag,
    print_payload,
    register_core_commands,
)
from pragmagraph.certification import (
    build_certification_pack,
    render_markdown_certification_pack,
)
from pragmagraph.docgraph import build_doc_graph_summary, render_markdown_doc_graph
from pragmagraph.export import project_snapshot, render_graph_export
from pragmagraph.graphify import (
    snapshot_from_graphify_payload,
    to_graphify_payload,
)
from pragmagraph.investigate import (
    build_investigation_bundle,
    render_markdown_investigation,
)
from pragmagraph.interchange import (
    build_symbol_reference_bundle,
    load_native_scip,
    merge_precise_snapshot,
)
from pragmagraph.lineage import build_git_lineage
from pragmagraph.models import QueryRequest
from pragmagraph.navigation import (
    build_repo_map,
    render_compact_handoff,
    render_markdown_repo_map,
)
from pragmagraph.parser_support import build_parser_support_matrix
from pragmagraph.planner import explain_query_plan
from pragmagraph.portability.cli import (
    GRAPH_PACK_COMMANDS,
    register_graph_pack_commands,
    run_graph_pack_command,
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
from pragmagraph.refresh import build_ci_delta
from pragmagraph.refresh.cli import (
    REFRESH_COMMANDS,
    register_refresh_commands,
    run_refresh_command,
)
from pragmagraph.report import build_report, render_markdown_report
from pragmagraph.service import LocalQueryService, run_stdio_service
from pragmagraph.storage import load_snapshot, save_snapshot
from pragmagraph.storage.cli import (
    STORAGE_COMMANDS,
    register_storage_commands,
    run_storage_command,
)
from pragmagraph.topology import build_topology_summary, render_markdown_topology
from pragmagraph.ui.cli import UI_COMMANDS, register_ui_commands, run_ui_command
from pragmagraph.ui.workbench import (
    WORKBENCH_COMMANDS,
    register_workbench_commands,
    run_workbench_command,
)
from pragmagraph.viewer.cli import (
    VIEWER_COMMANDS,
    register_viewer_commands,
    run_viewer_command,
)
from pragmagraph.workspace.cli import (
    WORKSPACE_COMMANDS,
    register_workspace_commands,
    run_workspace_command,
)
from pragmagraph.workspace.cli_resolution import investigation_args, query_args


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


def _server_client_cli():
    return importlib.import_module("pragmagraph.server.client_cli")


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
    parser = argparse.ArgumentParser(
        prog="pragmagraph",
        description=(
            "PragmaGraph observed-fact graph CLI. Start with "
            "`pragmagraph quickstart . --json`."
        ),
        epilog=(
            "Recommended first run: pragmagraph quickstart . --json\n"
            "Reopen the visual graph: pragmagraph demo-ui --config "
            ".pragmagraph/workspace.toml --serve --open"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_json_flag(parser)
    subparsers = parser.add_subparsers(dest="command", metavar="<command>")

    register_core_commands(subparsers)
    register_refresh_commands(subparsers)

    register_ui_commands(subparsers)
    register_workbench_commands(subparsers)
    register_graph_pack_commands(subparsers)
    server_client_cli = _server_client_cli()
    server_client_cli.register_mcp_client_commands(subparsers)
    register_storage_commands(subparsers)
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
        print_payload(health(snapshot).to_dict(), as_json=args.json)
    elif args.command == "query":
        snapshot_path, query_text = query_args(args, parser)
        snapshot = load_snapshot(snapshot_path)
        print_payload(
            query(
                snapshot,
                QueryRequest(
                    query=query_text,
                    max_results=args.max_results,
                    cursor=args.cursor,
                    max_examined=args.max_examined,
                ),
            ).to_dict(),
            as_json=True,
        )
    elif args.command in WORKSPACE_COMMANDS:
        print_payload(
            run_workspace_command(args, parser),
            as_json=args.json,
        )
    elif args.command == "ci-delta":
        report = build_ci_delta(
            load_snapshot(args.before),
            load_snapshot(args.after),
            fail_on_changes=args.fail_on_changes,
        )
        print_payload(report.to_dict(), as_json=True)
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
        print_payload(result.to_dict(), as_json=True)
    elif args.command == "investigate":
        snapshot_path, query_text = investigation_args(args, parser)
        snapshot = load_snapshot(snapshot_path)
        bundle = build_investigation_bundle(
            snapshot,
            query_text,
            snapshot_path=snapshot_path,
            preset=args.preset,
            max_results=args.max_results,
        )
        if args.json:
            print_payload(bundle.to_dict(), as_json=True)
        else:
            print(render_markdown_investigation(bundle), end="")
    elif args.command == "git-commits-for-path":
        snapshot = load_snapshot(args.snapshot)
        print_payload(
            recent_commits_for_path(
                snapshot,
                args.path,
                max_results=args.max_results,
            ).to_dict(),
            as_json=True,
        )
    elif args.command == "git-files-for-commit":
        snapshot = load_snapshot(args.snapshot)
        print_payload(
            files_touched_by_commit(
                snapshot,
                args.commit_ref,
                max_results=args.max_results,
            ).to_dict(),
            as_json=True,
        )
    elif args.command == "git-commits-for-symbol":
        snapshot = load_snapshot(args.snapshot)
        print_payload(
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
            print_payload(report.to_dict(), as_json=True)
        else:
            print(render_markdown_report(report), end="")
    elif args.command == "repo-map":
        snapshot = load_snapshot(args.snapshot)
        repo_map = build_repo_map(snapshot, top_n=args.top_n)
        if args.json:
            print_payload(repo_map.to_dict(), as_json=True)
        elif args.handoff:
            print(render_compact_handoff(snapshot, top_n=args.top_n), end="")
        else:
            print(render_markdown_repo_map(repo_map), end="")
    elif args.command == "topology":
        snapshot = load_snapshot(args.snapshot)
        summary = build_topology_summary(snapshot, top_n=args.top_n)
        if args.json:
            print_payload(summary.to_dict(), as_json=True)
        else:
            print(render_markdown_topology(summary), end="")
    elif args.command == "doc-graph":
        snapshot = load_snapshot(args.snapshot)
        summary = build_doc_graph_summary(snapshot, top_n=args.top_n)
        if args.json:
            print_payload(summary.to_dict(), as_json=True)
        else:
            print(render_markdown_doc_graph(summary), end="")
    elif args.command == "interchange":
        snapshot = load_snapshot(args.snapshot)
        print_payload(build_symbol_reference_bundle(snapshot).to_dict(), as_json=True)
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
        print_payload(
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
        print_payload(
            explain_query_plan(
                snapshot,
                QueryRequest(
                    query=args.query,
                    max_results=args.max_results,
                ),
            ).to_dict(),
            as_json=True,
        )
    elif args.command == "git-lineage":
        snapshot = load_snapshot(args.snapshot)
        lineage = build_git_lineage(snapshot, args.path, max_results=args.max_results)
        print_payload(lineage.to_dict(), as_json=True)
    elif args.command == "parser-support":
        print_payload(
            [item.to_dict() for item in build_parser_support_matrix()],
            as_json=True,
        )
    elif args.command == "certify":
        snapshot = load_snapshot(args.snapshot)
        certification = build_certification_pack(snapshot, top_n=args.top_n)
        if args.markdown_out:
            Path(args.markdown_out).write_text(
                render_markdown_certification_pack(certification),
                encoding="utf-8",
            )
        print_payload(certification.to_dict(), as_json=True)
    elif args.command == "export":
        snapshot = load_snapshot(args.snapshot)
        projection = project_snapshot(snapshot, profile=args.profile)
        print(render_graph_export(projection.snapshot, format=args.format), end="")
    elif args.command == "graphify-export":
        snapshot = load_snapshot(args.snapshot)
        print_payload(to_graphify_payload(snapshot), as_json=True)
    elif args.command == "graphify-import":
        with open(args.payload, encoding="utf-8") as graphify_payload:
            payload = json.load(graphify_payload)
        snapshot = snapshot_from_graphify_payload(
            payload,
            namespace=args.namespace,
            root_path=args.root_path,
        )
        save_snapshot(snapshot, args.out)
        print_payload(health(snapshot).to_dict(), as_json=True)
    elif args.command in STORAGE_COMMANDS:
        print_payload(run_storage_command(args), as_json=True)
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
            print_payload(report.to_dict(), as_json=True)
        else:
            print(render_markdown_benchmark(report), end="")
    elif args.command in REFRESH_COMMANDS:
        run_refresh_command(args, parser)
    elif args.command == "neighborhood":
        snapshot = load_snapshot(args.snapshot)
        print_payload(
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
        print_payload(
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
        print_payload(health(snapshot).to_dict(), as_json=True)
    elif args.command == "serve":
        service = _service_from_args(args)
        return run_stdio_service(service)
    elif args.command in UI_COMMANDS:
        print_payload(run_ui_command(args), as_json=args.json)
    elif args.command in WORKBENCH_COMMANDS:
        print_payload(run_workbench_command(args), as_json=args.json)
    elif args.command in GRAPH_PACK_COMMANDS:
        print_payload(run_graph_pack_command(args), as_json=args.json)
    elif args.command in server_client_cli.MCP_CLIENT_COMMANDS:
        print_payload(server_client_cli.run_mcp_client_command(args), as_json=args.json)
    elif args.command in VIEWER_COMMANDS:
        print_payload(run_viewer_command(args), as_json=True)
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
