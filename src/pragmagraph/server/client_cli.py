"""CLI registration and execution for MCP client setup snippets."""

from __future__ import annotations

import argparse

from pragmagraph.server.client_config import build_mcp_doctor_payload

MCP_CLIENT_COMMANDS = frozenset({"mcp-config"})


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


def run_mcp_client_command(args: argparse.Namespace) -> object:
    """Execute one parsed MCP client setup command."""
    return build_mcp_doctor_payload(
        snapshot=args.snapshot or "",
        root=args.root or "",
        namespace=args.namespace,
    )


__all__ = [
    "MCP_CLIENT_COMMANDS",
    "register_mcp_client_commands",
    "run_mcp_client_command",
]
