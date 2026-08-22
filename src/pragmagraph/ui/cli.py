"""CLI registration and execution for package-local UI preview commands."""

from __future__ import annotations

import argparse
import importlib
from pathlib import Path

from pragmagraph.adapters.git_history import (
    DEFAULT_GIT_IDENTITY_MODE,
    SUPPORTED_GIT_IDENTITY_MODES,
)
from pragmagraph.cli import add_json_flag
from pragmagraph.investigate import INVESTIGATION_PRESETS
from pragmagraph.storage import backend_catalog_payload
from pragmagraph.ui.evidence import (
    build_evidence_payload,
    write_agent_context,
    write_evidence_payload,
)
from pragmagraph.ui.preview import serve_ui_preview, write_ui_preview
from pragmagraph.ui.preview_inputs import snapshot_for_request
from pragmagraph.ui.preview_types import UiPreviewRequest
from pragmagraph.workspace import (
    SUPPORTED_UI_SCREENS,
    initialize_workspace,
    load_workspace_config,
    resolve_workspace_config_paths,
)
from pragmagraph.workspace.cli_resolution import ensure_config_workspace

UI_COMMANDS = frozenset({"ui-preview", "demo-ui", "doctor"})


def register_ui_commands(subparsers: argparse._SubParsersAction) -> None:
    """Register package-local UI commands."""
    _register_ui_preview_command(subparsers)
    _register_demo_ui_command(subparsers)
    _register_doctor_command(subparsers)


def run_ui_command(args: argparse.Namespace) -> dict[str, object]:
    """Execute one parsed UI command."""
    if args.command == "doctor":
        return _run_doctor_command(args)
    if args.command == "ui-preview":
        request = UiPreviewRequest(
            screen=args.screen,
            workspace=args.workspace,
            snapshot=args.snapshot,
            before_snapshot=args.before_snapshot,
            after_snapshot=args.after_snapshot,
            output_path=args.html_out,
            artifact_path=args.artifact_out,
            embed_path=args.embed_out,
            report_path=args.report_out,
            markdown_report_path=args.markdown_report_out,
            evidence_path=args.evidence_out,
            agent_context_path=args.agent_context_out,
            store_path=args.store,
            graph_pack_path=args.graph_pack,
            snapshot_out=args.snapshot_out,
            store_out=args.store_out,
            query=args.query,
            investigation_preset=args.preset,
            max_results=args.max_results,
            node_id=args.node_id,
            source_id=args.source_id,
            target_id=args.target_id,
            open_browser=args.open,
        )
        return _run_preview(request, args)
    workspace = _ensure_demo_workspace(args)
    store_path = None
    if args.config:
        config = load_workspace_config(args.config)
        store_path = str(resolve_workspace_config_paths(args.config).store_path)
        screen = config.ui_screen if args.screen == "search" else args.screen
        query_text = config.ui_query if args.query == "RuntimeGraph" else args.query
    else:
        screen = args.screen
        query_text = args.query
    request = UiPreviewRequest(
        screen=screen,
        workspace=str(workspace) if workspace is not None else "",
        output_path=args.html_out,
        artifact_path=args.artifact_out,
        report_path=args.report_out,
        evidence_path=args.evidence_out,
        agent_context_path=args.agent_context_out,
        store_path=store_path,
        graph_pack_path=args.graph_pack,
        snapshot_out=args.snapshot_out,
        store_out=args.store_out,
        query=query_text,
        investigation_preset=args.preset,
        max_results=args.max_results,
        open_browser=args.open,
    )
    return _run_preview(request, args)


def _register_ui_preview_command(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "ui-preview",
        help="open the package-local visual graph preview",
    )
    parser.add_argument("--workspace")
    parser.add_argument("--snapshot")
    parser.add_argument("--before-snapshot")
    parser.add_argument("--after-snapshot")
    parser.add_argument(
        "--screen",
        choices=tuple(sorted(SUPPORTED_UI_SCREENS)),
        default="search",
    )
    parser.add_argument("--html-out", default="pragmagraph-ui-preview.html")
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
    parser.add_argument("--query", default="RuntimeGraph")
    parser.add_argument("--preset", choices=INVESTIGATION_PRESETS, default="search")
    parser.add_argument("--max-results", type=int, default=5)
    parser.add_argument("--node-id")
    parser.add_argument("--source-id")
    parser.add_argument("--target-id")
    parser.add_argument("--open", action="store_true")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    add_json_flag(parser)


def _register_demo_ui_command(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "demo-ui",
        help="open or write the quickest visual PragmaGraph demo",
    )
    parser.add_argument("--config")
    parser.add_argument("--root")
    parser.add_argument("--workspace")
    parser.add_argument("--label", default="default")
    parser.add_argument("--namespace", default="default")
    parser.add_argument(
        "--git-identity-mode",
        choices=tuple(sorted(SUPPORTED_GIT_IDENTITY_MODES)),
        default=DEFAULT_GIT_IDENTITY_MODE,
    )
    parser.add_argument(
        "--screen",
        choices=tuple(sorted(SUPPORTED_UI_SCREENS)),
        default="search",
    )
    parser.add_argument("--query", default="RuntimeGraph")
    parser.add_argument("--html-out", default="pragmagraph-demo.html")
    parser.add_argument("--artifact-out", default="")
    parser.add_argument("--report-out", default="")
    parser.add_argument("--evidence-out", default="")
    parser.add_argument("--agent-context-out", default="")
    parser.add_argument("--graph-pack")
    parser.add_argument("--snapshot-out")
    parser.add_argument("--store-out")
    parser.add_argument("--preset", choices=INVESTIGATION_PRESETS, default="search")
    parser.add_argument("--max-results", type=int, default=5)
    parser.add_argument("--open", action="store_true")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    add_json_flag(parser)


def _register_doctor_command(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "doctor",
        help="inspect status, search evidence, and storage proof for one graph",
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--config")
    source.add_argument("--workspace")
    source.add_argument("--snapshot")
    source.add_argument("--store-only")
    parser.add_argument("--store")
    parser.add_argument("--query", default="")
    parser.add_argument("--evidence-out", default="")
    parser.add_argument("--agent-context-out", default="")
    add_json_flag(parser)


def _run_doctor_command(args: argparse.Namespace) -> dict[str, object]:
    request = _doctor_request(args)
    payload = build_evidence_payload(snapshot_for_request(request), request)
    output: dict[str, object] = {"evidence": payload}
    if args.evidence_out:
        output["evidence_output_path"] = str(
            write_evidence_payload(payload, args.evidence_out)
        )
    if args.agent_context_out:
        output["agent_context_output_path"] = str(
            write_agent_context(payload, args.agent_context_out)
        )
    output["storage_backends"] = backend_catalog_payload()
    output["mcp"] = importlib.import_module(
        "pragmagraph.server.client_config"
    ).build_mcp_doctor_payload(
        snapshot=request.snapshot or "",
        root="",
        namespace="default",
    )
    return output


def _doctor_request(args: argparse.Namespace) -> UiPreviewRequest:
    if args.config:
        resolved = resolve_workspace_config_paths(args.config)
        return UiPreviewRequest(
            screen="evidence",
            workspace=str(ensure_config_workspace(args.config)),
            store_path=str(resolved.store_path),
            query=args.query or resolved.config.ui_query or "RuntimeGraph",
            evidence_path=args.evidence_out,
            agent_context_path=args.agent_context_out,
        )
    if args.workspace:
        return UiPreviewRequest(
            screen="evidence",
            workspace=args.workspace,
            store_path=args.store,
            query=args.query or "RuntimeGraph",
            evidence_path=args.evidence_out,
            agent_context_path=args.agent_context_out,
        )
    if args.snapshot:
        return UiPreviewRequest(
            screen="evidence",
            snapshot=args.snapshot,
            store_path=args.store,
            query=args.query or "RuntimeGraph",
            evidence_path=args.evidence_out,
            agent_context_path=args.agent_context_out,
        )
    if args.store_only:
        return UiPreviewRequest(
            screen="evidence",
            store_path=args.store_only,
            query=args.query or "RuntimeGraph",
            evidence_path=args.evidence_out,
            agent_context_path=args.agent_context_out,
        )
    return UiPreviewRequest(
        screen="evidence",
        query=args.query or "RuntimeGraph",
        evidence_path=args.evidence_out,
        agent_context_path=args.agent_context_out,
    )


def _run_preview(
    request: UiPreviewRequest,
    args: argparse.Namespace,
) -> dict[str, object]:
    if args.serve:
        return serve_ui_preview(request, host=args.host, port=args.port).to_dict()
    return write_ui_preview(request).to_dict()


def _ensure_demo_workspace(args: argparse.Namespace) -> Path | None:
    if args.config:
        return ensure_config_workspace(args.config)
    if not args.root and not args.workspace:
        return None
    workspace_path = (
        Path(args.workspace)
        if args.workspace
        else Path(args.root) / ".pragmagraph" / "workspace"
    )
    if not (workspace_path / "workspace.json").exists():
        initialize_workspace(
            label=args.label,
            root_path=args.root or ".",
            workspace_path=workspace_path,
            namespace=args.namespace,
            git_identity_mode=args.git_identity_mode,
        )
    return workspace_path


__all__ = ["UI_COMMANDS", "register_ui_commands", "run_ui_command"]
