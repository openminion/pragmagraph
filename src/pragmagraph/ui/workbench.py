"""CLI ownership for the standalone local PragmaGraph workbench."""

from __future__ import annotations

import argparse
from pathlib import Path

from pragmagraph.adapters.git_history import (
    DEFAULT_GIT_IDENTITY_MODE,
    SUPPORTED_GIT_IDENTITY_MODES,
)
from pragmagraph.cli import add_json_flag
from pragmagraph.investigate import INVESTIGATION_PRESETS
from pragmagraph.storage import SQLiteGraphStore, load_snapshot
from pragmagraph.ui.preview import serve_ui_preview, write_ui_preview
from pragmagraph.ui.preview_types import UiPreviewRequest
from pragmagraph.workspace.cli_resolution import ensure_config_workspace
from pragmagraph.workspace import (
    DEFAULT_STORE_FILE,
    DEFAULT_UI_QUERY,
    DEFAULT_WORKSPACE_CONFIG,
    DEFAULT_WORKSPACE_DIR,
    SUPPORTED_UI_SCREENS,
    build_workspace_config,
    initialize_workspace,
    load_workspace_metadata,
    resolve_workspace_config_paths,
    save_workspace_config,
)

WORKBENCH_COMMANDS = frozenset({"quickstart", "workbench"})
QUICKSTART_UI_SCREENS = ("investigation", "project_health", "search")


def register_workbench_commands(subparsers: argparse._SubParsersAction) -> None:
    """Register the standalone local workbench command."""
    _register_quickstart_command(subparsers)
    _register_workbench_command(subparsers)


def _register_workbench_command(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "workbench",
        help="write or serve the standalone local graph workbench",
    )
    parser.add_argument("--config")
    parser.add_argument("--root")
    parser.add_argument("--workspace")
    parser.add_argument("--snapshot")
    parser.add_argument("--before-snapshot")
    parser.add_argument("--after-snapshot")
    parser.add_argument(
        "--screen",
        choices=tuple(sorted(SUPPORTED_UI_SCREENS)),
        default="search",
    )
    parser.add_argument("--query", default="")
    parser.add_argument("--html-out", default="pragmagraph-workbench.html")
    parser.add_argument("--artifact-out", default="")
    parser.add_argument("--embed-out", default="")
    parser.add_argument("--report-out", default="")
    parser.add_argument("--markdown-report-out", default="")
    parser.add_argument("--evidence-out", default="")
    parser.add_argument("--agent-context-out", default="")
    parser.add_argument("--store")
    parser.add_argument("--graph-pack")
    parser.add_argument("--snapshot-out")
    parser.add_argument("--store-out")
    parser.add_argument("--node-id")
    parser.add_argument("--source-id")
    parser.add_argument("--target-id")
    parser.add_argument("--preset", choices=INVESTIGATION_PRESETS, default="search")
    parser.add_argument("--max-results", type=int, default=5)
    parser.add_argument("--open", action="store_true")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument(
        "--git-identity-mode",
        choices=tuple(sorted(SUPPORTED_GIT_IDENTITY_MODES)),
        default=DEFAULT_GIT_IDENTITY_MODE,
    )
    add_json_flag(parser)


def run_workbench_command(args: argparse.Namespace) -> object:
    """Execute one parsed standalone workbench command."""
    if args.command == "quickstart":
        return _run_quickstart_command(args)
    request = _workbench_request(args)
    if args.serve:
        return serve_ui_preview(request, host=args.host, port=args.port)
    result = write_ui_preview(request).to_dict()
    result["next_commands"] = _workbench_next_commands(request)
    return result


def _register_quickstart_command(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "quickstart",
        help="recommended first run: create a workspace and visual investigation",
        description=(
            "Create a repeatable local PragmaGraph workspace, materialized store, "
            "and visual investigation from one source root."
        ),
        epilog=(
            "First run: pragmagraph quickstart . --serve --open --json\n"
            "Reopen later: pragmagraph demo-ui --config "
            ".pragmagraph/workspace.toml --serve --open --json"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--config", default=DEFAULT_WORKSPACE_CONFIG)
    parser.add_argument("--workspace", default=DEFAULT_WORKSPACE_DIR)
    parser.add_argument("--store", default=DEFAULT_STORE_FILE)
    parser.add_argument("--label", default="quickstart")
    parser.add_argument("--namespace", default="default")
    parser.add_argument(
        "--screen",
        choices=QUICKSTART_UI_SCREENS,
        default="investigation",
    )
    parser.add_argument("--query", default=DEFAULT_UI_QUERY)
    parser.add_argument("--preset", choices=INVESTIGATION_PRESETS, default="search")
    parser.add_argument("--max-results", type=int, default=5)
    parser.add_argument("--html-out", default=".pragmagraph/pragmagraph.html")
    parser.add_argument("--artifact-out", default="")
    parser.add_argument("--report-out", default="")
    parser.add_argument("--overwrite-config", action="store_true")
    parser.add_argument("--open", action="store_true")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument(
        "--git-identity-mode",
        choices=tuple(sorted(SUPPORTED_GIT_IDENTITY_MODES)),
        default=DEFAULT_GIT_IDENTITY_MODE,
    )
    add_json_flag(parser)


def _workbench_request(args: argparse.Namespace) -> UiPreviewRequest:
    workspace = args.workspace
    snapshot = args.snapshot
    store_path = args.store
    screen = args.screen
    query_text = args.query
    if args.config:
        resolved = resolve_workspace_config_paths(args.config)
        workspace = str(ensure_config_workspace(args.config))
        store_path = store_path or str(resolved.store_path)
        screen = resolved.config.ui_screen if args.screen == "search" else args.screen
        query_text = args.query or resolved.config.ui_query
    elif args.root:
        result = initialize_workspace(
            label="workbench",
            root_path=args.root,
            workspace_path=args.workspace or ".pragmagraph/workspace",
            namespace="default",
            git_identity_mode=args.git_identity_mode,
        )
        workspace = result.workspace.paths.workspace_path
        store_path = store_path or str(Path(workspace) / "graph.sqlite")
    if workspace and store_path:
        _ensure_workbench_store(workspace, store_path)
    return UiPreviewRequest(
        screen=screen,
        workspace=workspace,
        snapshot=snapshot,
        before_snapshot=args.before_snapshot,
        after_snapshot=args.after_snapshot,
        output_path=args.html_out,
        artifact_path=args.artifact_out,
        embed_path=args.embed_out,
        report_path=args.report_out,
        markdown_report_path=args.markdown_report_out,
        evidence_path=args.evidence_out,
        agent_context_path=args.agent_context_out,
        store_path=store_path,
        graph_pack_path=args.graph_pack,
        snapshot_out=args.snapshot_out,
        store_out=args.store_out,
        query=query_text or "RuntimeGraph",
        investigation_preset=args.preset,
        max_results=args.max_results,
        node_id=args.node_id,
        source_id=args.source_id,
        target_id=args.target_id,
        open_browser=args.open,
    )


def _run_quickstart_command(args: argparse.Namespace) -> object:
    config_path = Path(args.config)
    config_written = _ensure_quickstart_config(args, config_path)
    resolved = resolve_workspace_config_paths(config_path)
    workspace_path = ensure_config_workspace(config_path)
    store_path = str(resolved.store_path)
    _ensure_workbench_store(str(workspace_path), store_path)
    request = UiPreviewRequest(
        screen=resolved.config.ui_screen,
        workspace=str(workspace_path),
        output_path=args.html_out,
        artifact_path=args.artifact_out,
        report_path=args.report_out,
        store_path=store_path,
        query=resolved.config.ui_query,
        investigation_preset=args.preset,
        max_results=args.max_results,
        open_browser=args.open,
    )
    if args.serve:
        return serve_ui_preview(request, host=args.host, port=args.port)
    result = write_ui_preview(request).to_dict()
    result["quickstart"] = {
        "config_path": str(config_path),
        "config_written": config_written,
        "workspace_path": str(workspace_path),
        "store_path": store_path,
    }
    result["next_commands"] = _quickstart_next_commands(
        config_path,
        resolved.config.ui_query,
    )
    return result


def _ensure_quickstart_config(
    args: argparse.Namespace,
    config_path: Path,
) -> bool:
    if config_path.exists() and not args.overwrite_config:
        return False
    config = build_workspace_config(
        args.root,
        workspace_path=args.workspace,
        label=args.label,
        namespace=args.namespace,
        git_identity_mode=args.git_identity_mode,
        store_path=args.store,
        ui_screen=args.screen,
        ui_query=args.query,
    )
    save_workspace_config(config, config_path)
    return True


def _quickstart_next_commands(
    config_path: Path,
    query_text: str,
) -> dict[str, list[str]]:
    config = str(config_path)
    resolved = resolve_workspace_config_paths(config_path)
    snapshot_path = str(resolved.workspace_path / "snapshot.json")
    return {
        "refresh": [
            "pragmagraph",
            "workspace-refresh",
            "--config",
            config,
            "--json",
        ],
        "investigate": [
            "pragmagraph",
            "investigate",
            "--config",
            config,
            query_text,
            "--json",
        ],
        "repo_map": [
            "pragmagraph",
            "repo-map",
            snapshot_path,
            "--handoff",
        ],
        "project_health_visual": _demo_visual_command(
            config,
            screen="project_health",
        ),
        "search_visual": _demo_visual_command(
            config,
            screen="search",
            query=query_text,
        ),
        "visual": _demo_visual_command(config),
        "reopen_visual": _demo_visual_command(config),
        "store_search_explain": [
            "pragmagraph",
            "store-search-explain",
            "--config",
            config,
            query_text,
            "--json",
        ],
        "mcp_smoke": [
            "pragmagraph",
            "mcp-smoke",
            "--config",
            config,
            "--json",
        ],
    }


def _demo_visual_command(
    config_path: str,
    *,
    screen: str = "",
    query: str = "",
) -> list[str]:
    command = [
        "pragmagraph",
        "demo-ui",
        "--config",
        config_path,
    ]
    if screen:
        command.extend(["--screen", screen])
    if query:
        command.extend(["--query", query])
    command.extend(["--serve", "--open", "--json"])
    return command


def _ensure_workbench_store(workspace: str, store_path: str) -> None:
    target = Path(store_path)
    if target.exists():
        return
    metadata = load_workspace_metadata(workspace)
    SQLiteGraphStore.from_snapshot(load_snapshot(metadata.paths.snapshot_path), target)


def _workbench_next_commands(request: UiPreviewRequest) -> dict[str, list[str]]:
    snapshot_path = request.snapshot
    if request.workspace:
        metadata = load_workspace_metadata(request.workspace)
        snapshot_path = metadata.paths.snapshot_path
    if not snapshot_path:
        return {}
    commands = _base_next_commands(request, snapshot_path)
    if request.store_path:
        commands.update(_graph_pack_next_commands(request, snapshot_path))
    commands["investigation_ui"] = _investigation_ui_command(request, snapshot_path)
    if request.workspace:
        commands["reopen_visual"] = _reopen_visual_command(request)
    return commands


def _base_next_commands(
    request: UiPreviewRequest,
    snapshot_path: str,
) -> dict[str, list[str]]:
    return {
        "query": ["pragmagraph", "query", snapshot_path, request.query, "--json"],
        "repo_map": ["pragmagraph", "repo-map", snapshot_path, "--handoff"],
        "report": ["pragmagraph", "report", snapshot_path, "--json"],
        "investigate": [
            "pragmagraph",
            "investigate",
            snapshot_path,
            request.query,
            "--preset",
            request.investigation_preset,
            "--json",
        ],
        "freshness": ["pragmagraph", "freshness", snapshot_path, "--json"],
        "backend_probe": [
            "pragmagraph",
            "store-backends",
            "--probe-optional",
            "--json",
        ],
        "mcp_config": [
            "pragmagraph",
            "mcp-config",
            "--snapshot",
            snapshot_path,
            "--json",
        ],
        "mcp_config_smoke": [
            "pragmagraph",
            "mcp-config-smoke",
            "--snapshot",
            snapshot_path,
            "--json",
        ],
    }


def _graph_pack_next_commands(
    request: UiPreviewRequest,
    snapshot_path: str,
) -> dict[str, list[str]]:
    if not request.store_path:
        return {}
    pack_path = _default_graph_pack_path(request)
    imported_snapshot = _default_imported_snapshot_path(request)
    imported_store = _default_imported_store_path(request)
    return {
        "store_health": [
            "pragmagraph",
            "store-health",
            request.store_path,
            "--json",
        ],
        "store_search_explain": [
            "pragmagraph",
            "store-search-explain",
            request.store_path,
            request.query,
            "--json",
        ],
        "graph_pack_export": [
            "pragmagraph",
            "graph-pack-export",
            snapshot_path,
            pack_path,
            "--include-store",
            "--store",
            request.store_path,
            "--json",
        ],
        "graph_pack_verify": [
            "pragmagraph",
            "graph-pack-verify",
            pack_path,
            "--json",
        ],
        "graph_pack_review": [
            "pragmagraph",
            "graph-pack-review",
            pack_path,
            "--snapshot-out",
            imported_snapshot,
            "--store-out",
            imported_store,
            "--json",
        ],
        "graph_pack_ui": [
            "pragmagraph",
            "ui-preview",
            "--screen",
            "graph_pack_review",
            "--graph-pack",
            pack_path,
            "--snapshot-out",
            imported_snapshot,
            "--store-out",
            imported_store,
            "--json",
        ],
    }


def _investigation_ui_command(
    request: UiPreviewRequest,
    snapshot_path: str,
) -> list[str]:
    return [
        "pragmagraph",
        "ui-preview",
        "--screen",
        "investigation",
        "--snapshot",
        snapshot_path,
        "--query",
        request.query,
        "--preset",
        request.investigation_preset,
        "--json",
    ]


def _reopen_visual_command(request: UiPreviewRequest) -> list[str]:
    return [
        "pragmagraph",
        "ui-preview",
        "--workspace",
        str(request.workspace),
        "--screen",
        request.screen,
        "--query",
        request.query,
        "--preset",
        request.investigation_preset,
        "--serve",
        "--open",
        "--json",
    ]


def _default_graph_pack_path(request: UiPreviewRequest) -> str:
    if request.workspace:
        return str(Path(request.workspace) / "graph-pack")
    if request.store_path:
        return str(Path(request.store_path).with_suffix("")) + "-pack"
    return ".pragmagraph/graph-pack"


def _default_imported_snapshot_path(request: UiPreviewRequest) -> str:
    if request.workspace:
        return str(Path(request.workspace) / "imported-snapshot.json")
    if request.store_path:
        return str(Path(request.store_path).with_name("imported-snapshot.json"))
    return ".pragmagraph/imported-snapshot.json"


def _default_imported_store_path(request: UiPreviewRequest) -> str:
    if request.workspace:
        return str(Path(request.workspace) / "imported.sqlite")
    if request.store_path:
        return str(Path(request.store_path).with_name("imported.sqlite"))
    return ".pragmagraph/imported.sqlite"


__all__ = ["WORKBENCH_COMMANDS", "register_workbench_commands", "run_workbench_command"]
