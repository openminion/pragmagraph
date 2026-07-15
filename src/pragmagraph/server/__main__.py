"""CLI entrypoint for the in-package `pragmagraph-server` runtime command."""

from __future__ import annotations

import argparse
import sys

from pragmagraph.adapters import DEFAULT_GIT_IDENTITY_MODE, SUPPORTED_GIT_IDENTITY_MODES
from pragmagraph.server.backend import ServiceConfig, build_wired_registry
from pragmagraph.server.server import ServerInfo, serve_stdio


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pragmagraph-server")
    subparsers = parser.add_subparsers(dest="command")
    stdio_help = (
        "Run the bounded PragmaGraph MCP runtime over stdio using one "
        "snapshot-backed or root-backed local graph session."
    )
    stdio_parser = subparsers.add_parser(
        "serve-stdio",
        help=stdio_help,
        description=stdio_help,
    )
    startup = stdio_parser.add_mutually_exclusive_group(required=True)
    startup.add_argument("--snapshot", help="snapshot-backed startup path")
    startup.add_argument("--root", help="root-backed startup path")
    stdio_parser.add_argument("--namespace", default="default")
    stdio_parser.add_argument("--manifest-in", default=None)
    stdio_parser.add_argument("--snapshot-out", default=None)
    stdio_parser.add_argument("--manifest-out", default=None)
    stdio_parser.add_argument("--state-out", default=None)
    stdio_parser.add_argument("--cache", default=None)
    stdio_parser.add_argument(
        "--git-identity-mode",
        choices=tuple(sorted(SUPPORTED_GIT_IDENTITY_MODES)),
        default=DEFAULT_GIT_IDENTITY_MODE,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "serve-stdio":
        registry = build_wired_registry(
            ServiceConfig(
                snapshot_path=args.snapshot,
                root_path=args.root,
                namespace=args.namespace,
                manifest_in=args.manifest_in,
                snapshot_out=args.snapshot_out,
                manifest_out=args.manifest_out,
                state_out=args.state_out,
                cache_path=args.cache,
                git_identity_mode=args.git_identity_mode,
            )
        )
        return serve_stdio(registry=registry, server_info=ServerInfo())
    parser.print_help(sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
