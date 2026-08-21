"""CLI registration and execution for portable graph-pack commands."""

from __future__ import annotations

import argparse

from pragmagraph.cli import add_json_flag
from pragmagraph.portability.graph_pack import (
    import_graph_pack,
    inspect_graph_pack,
    review_graph_pack,
    verify_graph_pack,
    write_graph_pack,
)
from pragmagraph.storage import load_snapshot

GRAPH_PACK_COMMANDS = frozenset(
    {
        "graph-pack-export",
        "graph-pack-import",
        "graph-pack-inspect",
        "graph-pack-review",
        "graph-pack-verify",
    }
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
    add_json_flag(export_parser)

    import_parser = subparsers.add_parser(
        "graph-pack-import",
        help="import a portable graph pack directory",
    )
    import_parser.add_argument("pack")
    import_parser.add_argument("--snapshot-out")
    import_parser.add_argument("--store-out")
    add_json_flag(import_parser)

    inspect_parser = subparsers.add_parser(
        "graph-pack-inspect",
        help="inspect a portable graph pack manifest",
    )
    inspect_parser.add_argument("pack")
    add_json_flag(inspect_parser)

    review_parser = subparsers.add_parser(
        "graph-pack-review",
        help="review graph pack receive posture before import",
    )
    review_parser.add_argument("pack")
    review_parser.add_argument("--snapshot-out")
    review_parser.add_argument("--store-out")
    add_json_flag(review_parser)

    verify_parser = subparsers.add_parser(
        "graph-pack-verify",
        help="verify graph pack manifest, snapshot, store, and evidence consistency",
    )
    verify_parser.add_argument("pack")
    add_json_flag(verify_parser)


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
    if args.command == "graph-pack-verify":
        return verify_graph_pack(args.pack).to_dict()
    if args.command == "graph-pack-review":
        return review_graph_pack(
            args.pack,
            snapshot_out=args.snapshot_out,
            store_out=args.store_out,
        ).to_dict()
    return inspect_graph_pack(args.pack).to_dict()


__all__ = [
    "GRAPH_PACK_COMMANDS",
    "register_graph_pack_commands",
    "run_graph_pack_command",
]
