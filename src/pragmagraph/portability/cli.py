"""CLI registration and execution for portable graph-pack commands."""

from __future__ import annotations

import argparse

from pragmagraph.portability.graph_pack import (
    import_graph_pack,
    inspect_graph_pack,
    write_graph_pack,
)
from pragmagraph.storage import load_snapshot

GRAPH_PACK_COMMANDS = frozenset(
    {"graph-pack-export", "graph-pack-import", "graph-pack-inspect"}
)


def register_graph_pack_commands(subparsers: argparse._SubParsersAction) -> None:
    """Register portable graph-pack commands."""
    export_parser = subparsers.add_parser(
        "graph-pack-export",
        help="export a portable graph pack directory",
    )
    export_parser.add_argument("snapshot")
    export_parser.add_argument("out")
    export_parser.add_argument("--include-store", action="store_true")
    export_parser.add_argument("--store")
    export_parser.add_argument("--evidence")
    export_parser.add_argument("--redaction-profile", default="none")
    _add_json_flag(export_parser)

    import_parser = subparsers.add_parser(
        "graph-pack-import",
        help="import a portable graph pack directory",
    )
    import_parser.add_argument("pack")
    import_parser.add_argument("--snapshot-out")
    import_parser.add_argument("--store-out")
    _add_json_flag(import_parser)

    inspect_parser = subparsers.add_parser(
        "graph-pack-inspect",
        help="inspect a portable graph pack manifest",
    )
    inspect_parser.add_argument("pack")
    _add_json_flag(inspect_parser)


def run_graph_pack_command(args: argparse.Namespace) -> object:
    """Execute one parsed graph-pack command."""
    if args.command == "graph-pack-export":
        manifest = write_graph_pack(
            load_snapshot(args.snapshot),
            args.out,
            include_store=args.include_store,
            store_path=args.store,
            evidence_path=args.evidence,
            redaction_profile=args.redaction_profile,
        )
        return {"pack_path": str(args.out), "manifest": manifest.to_dict()}
    if args.command == "graph-pack-import":
        return import_graph_pack(
            args.pack,
            snapshot_out=args.snapshot_out,
            store_out=args.store_out,
        )
    return inspect_graph_pack(args.pack).to_dict()


def _add_json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="emit JSON output")


__all__ = [
    "GRAPH_PACK_COMMANDS",
    "register_graph_pack_commands",
    "run_graph_pack_command",
]
