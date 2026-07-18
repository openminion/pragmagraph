"""CLI registration and execution for workspace composition commands."""

from __future__ import annotations

import argparse

from pragmagraph.models import PragmaGraphError
from pragmagraph.storage import load_snapshot, save_snapshot
from pragmagraph.workspace.composition import (
    NamedSnapshot,
    compose_snapshots,
    save_composed_snapshot_atomic,
)
from pragmagraph.workspace.multi_root import WorkspaceRoot, index_multi_root

WORKSPACE_COMMANDS = frozenset({"multi-root-index", "multi-root-compose"})


def register_workspace_commands(subparsers: argparse._SubParsersAction) -> None:
    """Register the bounded workspace command family."""
    index_parser = subparsers.add_parser(
        "multi-root-index",
        help="index explicitly named roots into one overlay",
    )
    index_parser.add_argument("--root", action="append", required=True)
    index_parser.add_argument("--namespace", default="workspace")
    index_parser.add_argument("--out", required=True)
    _add_json_flag(index_parser)

    compose_parser = subparsers.add_parser(
        "multi-root-compose",
        help="compose named canonical snapshots with exact SCIP resolution",
    )
    compose_parser.add_argument("--snapshot", action="append", required=True)
    compose_parser.add_argument("--namespace", default="workspace")
    compose_parser.add_argument("--created-at", default="")
    compose_parser.add_argument("--out", required=True)
    _add_json_flag(compose_parser)


def run_workspace_command(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> object:
    """Execute one parsed workspace command."""
    if args.command == "multi-root-index":
        roots = tuple(
            WorkspaceRoot(name=name, path=path)
            for name, path in _named_values(args.root, "--root", parser)
        )
        snapshot = index_multi_root(roots, namespace=args.namespace)
        save_snapshot(snapshot, args.out)
        return snapshot.to_dict()
    if args.command == "multi-root-compose":
        inputs = tuple(
            NamedSnapshot(name=name, snapshot=load_snapshot(path))
            for name, path in _named_values(args.snapshot, "--snapshot", parser)
        )
        result = compose_snapshots(
            inputs,
            namespace=args.namespace,
            created_at=args.created_at,
        )
        save_composed_snapshot_atomic(result.snapshot, args.out)
        return {
            "output_path": args.out,
            "report": result.report.to_dict(),
            "stats": dict(result.snapshot.stats),
        }
    raise PragmaGraphError(
        "unsupported workspace command",
        code="UNSUPPORTED_WORKSPACE_COMMAND",
        details={"command": args.command},
    )


def _named_values(
    values: list[str],
    option: str,
    parser: argparse.ArgumentParser,
) -> tuple[tuple[str, str], ...]:
    parsed: list[tuple[str, str]] = []
    for value in values:
        name, separator, path = value.partition("=")
        if not separator or not name.strip() or not path.strip():
            parser.error(f"{option} must use NAME=PATH")
        parsed.append((name.strip(), path.strip()))
    return tuple(parsed)


def _add_json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="emit JSON output")


__all__ = [
    "WORKSPACE_COMMANDS",
    "register_workspace_commands",
    "run_workspace_command",
]
