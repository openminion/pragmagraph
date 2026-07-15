"""CLI registration and execution for viewer-owned commands."""

from __future__ import annotations

import argparse

from pragmagraph.storage import load_snapshot
from pragmagraph.viewer import (
    VIEWER_FIXTURE_SCENARIOS,
    build_viewer_envelope,
    build_viewer_fixture_envelope,
    explain_omitted,
    load_viewer_envelope,
    viewer_cluster,
    viewer_cluster_nodes,
    viewer_content,
    viewer_delta,
    viewer_envelope_neighborhood,
    viewer_envelope_path,
    write_viewer_envelope,
)


VIEWER_COMMANDS = frozenset(
    {
        "viewer-export",
        "viewer-fixture",
        "viewer-cluster",
        "viewer-content",
        "viewer-neighborhood",
        "viewer-path",
        "viewer-cluster-nodes",
        "viewer-omitted",
        "viewer-delta",
    }
)


def register_viewer_commands(subparsers: argparse._SubParsersAction) -> None:
    """Register the viewer command family on the package parser."""
    export_parser = subparsers.add_parser(
        "viewer-export",
        help="export a snapshot as a provider-neutral viewer envelope",
    )
    export_parser.add_argument("snapshot")
    export_parser.add_argument(
        "--lod",
        choices=("auto", "raw", "sampled", "cluster", "meta"),
        default="auto",
    )
    export_parser.add_argument("--node-budget", type=int, default=240)
    export_parser.add_argument("--edge-budget", type=int, default=480)
    export_parser.add_argument("--cluster-size", type=int, default=24)
    export_parser.add_argument("--out", default="")
    _add_json_flag(export_parser)

    fixture_parser = subparsers.add_parser(
        "viewer-fixture",
        help="generate a deterministic large-scale viewer envelope fixture",
    )
    fixture_parser.add_argument(
        "--scenario", choices=VIEWER_FIXTURE_SCENARIOS, required=True
    )
    fixture_parser.add_argument("--out", required=True)
    fixture_parser.add_argument("--node-budget", type=int, default=240)
    fixture_parser.add_argument("--edge-budget", type=int, default=480)
    fixture_parser.add_argument("--seed", type=int, default=20260706)
    _add_json_flag(fixture_parser)

    cluster_parser = subparsers.add_parser(
        "viewer-cluster",
        help="show bounded cluster detail from a viewer envelope",
    )
    cluster_parser.add_argument("envelope")
    cluster_parser.add_argument("cluster_id")
    cluster_parser.add_argument("--budget", type=int, default=100)
    _add_json_flag(cluster_parser)

    content_parser = subparsers.add_parser(
        "viewer-content",
        help="show provider-owned node content from a viewer envelope",
    )
    content_parser.add_argument("envelope")
    content_parser.add_argument("node_id")
    content_parser.add_argument(
        "--mode", choices=("preview", "full"), default="preview"
    )
    _add_json_flag(content_parser)

    neighborhood_parser = subparsers.add_parser(
        "viewer-neighborhood",
        help="show bounded visible-node neighborhood from a viewer envelope",
    )
    neighborhood_parser.add_argument("envelope")
    neighborhood_parser.add_argument("node_id")
    neighborhood_parser.add_argument("--depth", type=int, default=1)
    neighborhood_parser.add_argument("--budget", type=int, default=100)
    _add_json_flag(neighborhood_parser)

    path_parser = subparsers.add_parser(
        "viewer-path",
        help="show a bounded visible path from a viewer envelope",
    )
    path_parser.add_argument("envelope")
    path_parser.add_argument("source_id")
    path_parser.add_argument("target_id")
    path_parser.add_argument("--budget", type=int, default=100)
    _add_json_flag(path_parser)

    cluster_nodes_parser = subparsers.add_parser(
        "viewer-cluster-nodes",
        help="show bounded hub or bridge node IDs for a viewer cluster",
    )
    cluster_nodes_parser.add_argument("envelope")
    cluster_nodes_parser.add_argument("cluster_id")
    cluster_nodes_parser.add_argument(
        "--role", choices=("hub", "bridge"), required=True
    )
    cluster_nodes_parser.add_argument("--budget", type=int, default=100)
    _add_json_flag(cluster_nodes_parser)

    omitted_parser = subparsers.add_parser(
        "viewer-omitted",
        help="explain omitted counts from a viewer envelope",
    )
    omitted_parser.add_argument("envelope")
    omitted_parser.add_argument("--reason", default="")
    _add_json_flag(omitted_parser)

    delta_parser = subparsers.add_parser(
        "viewer-delta",
        help="show viewer-safe structural delta between two snapshots",
    )
    delta_parser.add_argument("before_snapshot")
    delta_parser.add_argument("after_snapshot")
    delta_parser.add_argument("--budget", type=int, default=100)
    _add_json_flag(delta_parser)


def run_viewer_command(args: argparse.Namespace) -> object:
    """Execute one parsed viewer command and return its JSON-compatible output."""
    if args.command == "viewer-export":
        snapshot = load_snapshot(args.snapshot)
        envelope = build_viewer_envelope(
            snapshot,
            level_of_detail=args.lod,
            node_budget=args.node_budget,
            edge_budget=args.edge_budget,
            cluster_size=args.cluster_size,
        )
        return (
            write_viewer_envelope(envelope, args.out)
            if args.out
            else envelope.to_dict()
        )
    if args.command == "viewer-fixture":
        envelope = build_viewer_fixture_envelope(
            args.scenario,
            node_budget=args.node_budget,
            edge_budget=args.edge_budget,
            seed=args.seed,
        )
        return write_viewer_envelope(envelope, args.out)
    if args.command == "viewer-delta":
        before = load_snapshot(args.before_snapshot)
        after = load_snapshot(args.after_snapshot)
        return viewer_delta(before, after, budget=args.budget)

    envelope = load_viewer_envelope(args.envelope)
    if args.command == "viewer-cluster":
        return viewer_cluster(envelope, args.cluster_id, budget=args.budget)
    if args.command == "viewer-content":
        return viewer_content(envelope, args.node_id, mode=args.mode)
    if args.command == "viewer-neighborhood":
        return viewer_envelope_neighborhood(
            envelope,
            args.node_id,
            depth=args.depth,
            budget=args.budget,
        )
    if args.command == "viewer-path":
        return viewer_envelope_path(
            envelope,
            args.source_id,
            args.target_id,
            budget=args.budget,
        )
    if args.command == "viewer-cluster-nodes":
        return viewer_cluster_nodes(
            envelope,
            args.cluster_id,
            role=args.role,
            budget=args.budget,
        )
    if args.command == "viewer-omitted":
        return explain_omitted(envelope, reason=args.reason)
    raise ValueError(f"unsupported viewer command: {args.command}")


def _add_json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="emit JSON output")


__all__ = ["VIEWER_COMMANDS", "register_viewer_commands", "run_viewer_command"]
