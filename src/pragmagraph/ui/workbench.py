"""CLI ownership for the standalone local PragmaGraph workbench."""

from __future__ import annotations

import argparse
from pathlib import Path

from pragmagraph.adapters.git_history import (
    DEFAULT_GIT_IDENTITY_MODE,
    SUPPORTED_GIT_IDENTITY_MODES,
)
from pragmagraph.storage import SQLiteGraphStore, load_snapshot
from pragmagraph.ui.preview import serve_ui_preview, write_ui_preview
from pragmagraph.ui.preview_types import UiPreviewRequest
from pragmagraph.ui.workspace_paths import ensure_config_workspace
from pragmagraph.workspace import (
    SUPPORTED_UI_SCREENS,
    initialize_workspace,
    load_workspace_metadata,
    resolve_workspace_config_paths,
)

WORKBENCH_COMMANDS = frozenset({"workbench"})


def register_workbench_commands(subparsers: argparse._SubParsersAction) -> None:
    """Register the standalone local workbench command."""
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
    parser.add_argument("--node-id")
    parser.add_argument("--source-id")
    parser.add_argument("--target-id")
    parser.add_argument("--open", action="store_true")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument(
        "--git-identity-mode",
        choices=tuple(sorted(SUPPORTED_GIT_IDENTITY_MODES)),
        default=DEFAULT_GIT_IDENTITY_MODE,
    )
    parser.add_argument("--json", action="store_true", help="emit JSON output")


def run_workbench_command(args: argparse.Namespace) -> object:
    """Execute one parsed standalone workbench command."""
    request = _workbench_request(args)
    if args.serve:
        return serve_ui_preview(request, host=args.host, port=args.port)
    result = write_ui_preview(request).to_dict()
    result["next_commands"] = _workbench_next_commands(request)
    return result


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
        query=query_text or "RuntimeGraph",
        node_id=args.node_id,
        source_id=args.source_id,
        target_id=args.target_id,
        open_browser=args.open,
    )


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
    commands: dict[str, list[str]] = {
        "query": ["pragmagraph", "query", snapshot_path, request.query, "--json"],
        "report": ["pragmagraph", "report", snapshot_path, "--json"],
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
    }
    if request.store_path:
        commands["store_health"] = [
            "pragmagraph",
            "store-health",
            request.store_path,
            "--json",
        ]
        pack_path = _default_graph_pack_path(request)
        commands["graph_pack_export"] = [
            "pragmagraph",
            "graph-pack-export",
            snapshot_path,
            pack_path,
            "--include-store",
            "--store",
            request.store_path,
            "--json",
        ]
        commands["graph_pack_verify"] = [
            "pragmagraph",
            "graph-pack-verify",
            pack_path,
            "--json",
        ]
    return commands


def _default_graph_pack_path(request: UiPreviewRequest) -> str:
    if request.workspace:
        return str(Path(request.workspace) / "graph-pack")
    if request.store_path:
        return str(Path(request.store_path).with_suffix("")) + "-pack"
    return ".pragmagraph/graph-pack"


__all__ = ["WORKBENCH_COMMANDS", "register_workbench_commands", "run_workbench_command"]
