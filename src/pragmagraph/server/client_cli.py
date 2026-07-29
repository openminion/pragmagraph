"""CLI registration and execution for MCP client setup snippets."""

from __future__ import annotations

import argparse

from pragmagraph.server.client_config import (
    build_mcp_config_smoke_payload,
    build_mcp_doctor_payload,
)
from pragmagraph.server.smoke import run_mcp_consumer_smoke
from pragmagraph.workspace import load_workspace_metadata
from pragmagraph.workspace.cli_resolution import ensure_config_workspace

MCP_CLIENT_COMMANDS = frozenset({"mcp-config", "mcp-config-smoke", "mcp-smoke"})


def register_mcp_client_commands(subparsers: argparse._SubParsersAction) -> None:
    """Register MCP client setup commands."""
    parser = subparsers.add_parser(
        "mcp-config",
        help="emit MCP client configuration snippets for pragmagraph-server",
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--snapshot")
    source.add_argument("--root")
    parser.add_argument("--namespace", default="default")
    parser.add_argument("--json", action="store_true", help="emit JSON output")

    smoke_parser = subparsers.add_parser(
        "mcp-config-smoke",
        help="validate generated MCP stdio setup snippets",
    )
    smoke_source = smoke_parser.add_mutually_exclusive_group()
    smoke_source.add_argument("--snapshot")
    smoke_source.add_argument("--root")
    smoke_parser.add_argument("--namespace", default="default")
    smoke_parser.add_argument("--json", action="store_true", help="emit JSON output")

    consumer_parser = subparsers.add_parser(
        "mcp-smoke",
        help="start a short-lived local MCP server and call the investigate tool",
    )
    consumer_source = consumer_parser.add_mutually_exclusive_group(required=True)
    consumer_source.add_argument("--config")
    consumer_source.add_argument("--snapshot")
    consumer_source.add_argument("--root")
    consumer_parser.add_argument("--namespace", default="default")
    consumer_parser.add_argument("--query", default="RuntimeGraph")
    consumer_parser.add_argument("--timeout", type=int, default=15)
    consumer_parser.add_argument("--json", action="store_true", help="emit JSON output")


def run_mcp_client_command(args: argparse.Namespace) -> object:
    """Execute one parsed MCP client setup command."""
    if args.command == "mcp-smoke":
        snapshot = _snapshot_from_config(args.config) if args.config else args.snapshot
        return run_mcp_consumer_smoke(
            snapshot=snapshot or "",
            root=args.root or "",
            namespace=args.namespace,
            query=args.query,
            timeout=args.timeout,
        )
    if args.command == "mcp-config-smoke":
        return build_mcp_config_smoke_payload(
            snapshot=args.snapshot or "",
            root=args.root or "",
            namespace=args.namespace,
        )
    return build_mcp_doctor_payload(
        snapshot=args.snapshot or "",
        root=args.root or "",
        namespace=args.namespace,
    )


def _snapshot_from_config(config_path: str) -> str:
    workspace = ensure_config_workspace(config_path)
    return load_workspace_metadata(workspace).paths.snapshot_path


__all__ = [
    "MCP_CLIENT_COMMANDS",
    "register_mcp_client_commands",
    "run_mcp_client_command",
]
