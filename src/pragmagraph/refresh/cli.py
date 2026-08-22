"""CLI registration and execution for explicit refresh workflows."""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from pragmagraph.cli import (
    add_git_identity_mode_argument,
    add_json_flag,
    print_payload,
)
from pragmagraph.incremental import load_extraction_cache, save_extraction_cache
from pragmagraph.models import GraphSnapshot, PragmaGraphError
from pragmagraph.operations import (
    build_refresh_plan,
    build_refresh_profile,
    load_refresh_profile,
    load_refresh_status,
    run_refresh_profile,
    save_refresh_profile,
)
from pragmagraph.query import health
from pragmagraph.refresh import (
    build_ci_delta,
    load_manifest,
    refresh_snapshot,
    refresh_snapshot_incremental,
    save_manifest,
)
from pragmagraph.storage import load_snapshot, save_snapshot
from pragmagraph.workspace.cli_resolution import freshness_snapshot_arg

REFRESH_COMMANDS = frozenset(
    {
        "refresh",
        "refresh-plan",
        "refresh-status",
        "profile-init",
        "profile-run",
        "freshness",
    }
)


def register_refresh_commands(subparsers: argparse._SubParsersAction) -> None:
    refresh_parser = subparsers.add_parser("refresh", help="refresh a local root")
    refresh_parser.add_argument("root")
    refresh_parser.add_argument("--out", required=True)
    refresh_parser.add_argument("--manifest-in")
    refresh_parser.add_argument("--manifest-out", required=True)
    refresh_parser.add_argument("--cache-in")
    refresh_parser.add_argument("--cache-out")
    refresh_parser.add_argument("--namespace", default="default")
    add_git_identity_mode_argument(refresh_parser)
    add_json_flag(refresh_parser)

    plan_parser = subparsers.add_parser(
        "refresh-plan",
        help="preview explicit refresh-visible path changes without mutating outputs",
    )
    plan_parser.add_argument("root")
    plan_parser.add_argument("--manifest-in")
    plan_parser.add_argument("--namespace", default="default")
    add_json_flag(plan_parser)

    status_parser = subparsers.add_parser(
        "refresh-status", help="inspect a persisted refresh status ledger"
    )
    status_parser.add_argument("state")
    add_json_flag(status_parser)

    profile_parser = subparsers.add_parser(
        "profile-init", help="write a repeatable explicit-refresh invocation profile"
    )
    profile_parser.add_argument("root")
    profile_parser.add_argument("--out", required=True)
    profile_parser.add_argument("--label", default="default")
    profile_parser.add_argument("--namespace", default="default")
    profile_parser.add_argument("--snapshot-out", required=True)
    profile_parser.add_argument("--manifest-out", required=True)
    profile_parser.add_argument("--state-out", required=True)
    profile_parser.add_argument("--cache-out")
    add_git_identity_mode_argument(profile_parser)
    add_json_flag(profile_parser)

    run_parser = subparsers.add_parser(
        "profile-run", help="run one explicit refresh from a saved invocation profile"
    )
    run_parser.add_argument("profile")
    add_json_flag(run_parser)

    freshness_parser = subparsers.add_parser(
        "freshness",
        help="show snapshot freshness and optional structural delta facts",
    )
    freshness_parser.add_argument("snapshot", nargs="?")
    freshness_parser.add_argument("--config")
    freshness_parser.add_argument("--before")
    add_json_flag(freshness_parser)


def _run_refresh(args: argparse.Namespace) -> None:
    previous_manifest = load_manifest(args.manifest_in) if args.manifest_in else None
    previous_snapshot = load_snapshot(args.out) if Path(args.out).exists() else None
    if args.cache_in or args.cache_out:
        previous_cache = None
        fallback_reason = ""
        if args.cache_in and Path(args.cache_in).exists():
            try:
                previous_cache = load_extraction_cache(args.cache_in)
            except PragmaGraphError as exc:
                fallback_reason = exc.code.lower()
        result, next_cache = refresh_snapshot_incremental(
            args.root,
            namespace=args.namespace,
            previous_manifest=previous_manifest,
            previous_snapshot=previous_snapshot,
            previous_cache=previous_cache,
            git_identity_mode=args.git_identity_mode,
        )
        if fallback_reason:
            result = replace(
                result,
                work=replace(result.work, cache_fallback_reason=fallback_reason),
            )
    else:
        result = refresh_snapshot(
            args.root,
            namespace=args.namespace,
            previous_manifest=previous_manifest,
            previous_snapshot=previous_snapshot,
            git_identity_mode=args.git_identity_mode,
        )
    save_snapshot(result.snapshot, args.out)
    save_manifest(result.manifest, args.manifest_out)
    if args.cache_out:
        save_extraction_cache(next_cache, args.cache_out)
    print_payload(
        {
            "changed_paths": list(result.changed_paths),
            "unchanged_paths": list(result.unchanged_paths),
            "removed_paths": list(result.removed_paths),
            "path_changes": [item.to_dict() for item in result.path_changes],
            "snapshot_delta": result.snapshot_delta.to_dict(),
            "identity_transitions": [
                item.to_dict() for item in result.identity_transitions
            ],
            "work": result.work.to_dict(),
            "health": health(result.snapshot).to_dict(),
        },
        as_json=args.json,
    )


def _run_refresh_plan(args: argparse.Namespace) -> None:
    previous_manifest = load_manifest(args.manifest_in) if args.manifest_in else None
    plan = build_refresh_plan(
        args.root,
        namespace=args.namespace,
        previous_manifest=previous_manifest,
    )
    print_payload(plan.to_dict(), as_json=True)


def _run_profile_init(args: argparse.Namespace) -> None:
    profile = build_refresh_profile(
        label=args.label,
        root_path=args.root,
        snapshot_path=args.snapshot_out,
        manifest_path=args.manifest_out,
        state_path=args.state_out,
        cache_path=args.cache_out or "",
        namespace=args.namespace,
        git_identity_mode=args.git_identity_mode,
    )
    save_refresh_profile(profile, args.out)
    print_payload(profile.to_dict(), as_json=True)


def _freshness_payload(
    snapshot: GraphSnapshot,
    *,
    snapshot_path: str,
    before_path: str | None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "pragmagraph.freshness.v1alpha1",
        "boundary": "observed_facts_only",
        "snapshot_path": snapshot_path,
        "created_at": snapshot.created_at,
        "indexer_version": snapshot.indexer_version,
        "health": health(snapshot).to_dict(),
        "git_overlay": {
            "enabled": bool(snapshot.stats.get("git_overlay_enabled", False)),
            "commit_count": int(snapshot.stats.get("git_commit_count", 0) or 0),
            "changed_path_count": int(
                snapshot.stats.get("git_changed_path_count", 0) or 0
            ),
            "identity_mode": str(snapshot.stats.get("git_identity_mode", "") or ""),
        },
        "next_commands": {
            "refresh_plan": [
                "pragmagraph",
                "refresh-plan",
                snapshot.root_path or "<repo-root>",
                "--json",
            ],
            "health": ["pragmagraph", "health", snapshot_path, "--json"],
        },
    }
    if before_path:
        payload["delta"] = build_ci_delta(
            load_snapshot(before_path),
            snapshot,
        ).to_dict()
    return payload


def _run_freshness(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    snapshot_path = freshness_snapshot_arg(args, parser)
    snapshot = load_snapshot(snapshot_path)
    print_payload(
        _freshness_payload(
            snapshot,
            snapshot_path=snapshot_path,
            before_path=args.before,
        ),
        as_json=True,
    )


def run_refresh_command(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> None:
    if args.command == "refresh":
        _run_refresh(args)
    elif args.command == "refresh-plan":
        _run_refresh_plan(args)
    elif args.command == "refresh-status":
        print_payload(load_refresh_status(args.state).to_dict(), as_json=True)
    elif args.command == "profile-init":
        _run_profile_init(args)
    elif args.command == "profile-run":
        print_payload(
            run_refresh_profile(load_refresh_profile(args.profile)).to_dict(),
            as_json=True,
        )
    elif args.command == "freshness":
        _run_freshness(args, parser)


__all__ = [
    "REFRESH_COMMANDS",
    "register_refresh_commands",
    "run_refresh_command",
]
