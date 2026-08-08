"""Root CLI parser registration for built-in PragmaGraph commands."""

from __future__ import annotations

import argparse

from pragmagraph.adapters import (
    DEFAULT_GIT_IDENTITY_MODE,
    SUPPORTED_GIT_IDENTITY_MODES,
)
from pragmagraph.export import EXPORT_PROFILES
from pragmagraph.investigate import INVESTIGATION_PRESETS


def add_json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="emit JSON output")


def add_git_identity_mode_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--git-identity-mode",
        choices=tuple(sorted(SUPPORTED_GIT_IDENTITY_MODES)),
        default=DEFAULT_GIT_IDENTITY_MODE,
    )


def _register_index_query_commands(subparsers: argparse._SubParsersAction) -> None:
    index_parser = subparsers.add_parser("index", help="index a local root")
    index_parser.add_argument("root")
    index_parser.add_argument("--out", required=True)
    index_parser.add_argument("--namespace", default="default")
    add_git_identity_mode_argument(index_parser)
    add_json_flag(index_parser)

    query_parser = subparsers.add_parser("query", help="query a snapshot")
    query_parser.add_argument("snapshot", nargs="?")
    query_parser.add_argument("query", nargs="?")
    query_parser.add_argument("--config")
    query_parser.add_argument("--max-results", type=int, default=10)
    query_parser.add_argument("--cursor", default="")
    query_parser.add_argument("--max-examined", type=int)
    add_json_flag(query_parser)

    ci_delta_parser = subparsers.add_parser(
        "ci-delta",
        help="compare two canonical snapshots for CI",
    )
    ci_delta_parser.add_argument("before")
    ci_delta_parser.add_argument("after")
    ci_delta_parser.add_argument("--fail-on-changes", action="store_true")
    add_json_flag(ci_delta_parser)

    explain_parser = subparsers.add_parser(
        "explain", help="query with score explanations"
    )
    explain_parser.add_argument("snapshot")
    explain_parser.add_argument("query")
    explain_parser.add_argument("--max-results", type=int, default=10)
    explain_parser.add_argument("--cursor", default="")
    explain_parser.add_argument("--max-examined", type=int)
    add_json_flag(explain_parser)

    investigate_parser = subparsers.add_parser(
        "investigate",
        help="build a guided observed-fact investigation bundle",
    )
    investigate_parser.add_argument("snapshot", nargs="?")
    investigate_parser.add_argument("query", nargs="?")
    investigate_parser.add_argument("--config")
    investigate_parser.add_argument(
        "--preset",
        choices=INVESTIGATION_PRESETS,
        default="search",
    )
    investigate_parser.add_argument("--max-results", type=int, default=5)
    add_json_flag(investigate_parser)


def _register_git_and_graph_view_commands(
    subparsers: argparse._SubParsersAction,
) -> None:
    git_path_parser = subparsers.add_parser(
        "git-commits-for-path",
        help="show recent git commits affecting one relative path",
    )
    git_path_parser.add_argument("snapshot")
    git_path_parser.add_argument("path")
    git_path_parser.add_argument("--max-results", type=int, default=10)
    add_json_flag(git_path_parser)

    git_commit_parser = subparsers.add_parser(
        "git-files-for-commit",
        help="show current file/path nodes touched by one git commit",
    )
    git_commit_parser.add_argument("snapshot")
    git_commit_parser.add_argument("commit_ref")
    git_commit_parser.add_argument("--max-results", type=int, default=50)
    add_json_flag(git_commit_parser)

    git_symbol_parser = subparsers.add_parser(
        "git-commits-for-symbol",
        help="show recent git commits touching a symbol's containing file",
    )
    git_symbol_parser.add_argument("snapshot")
    git_symbol_parser.add_argument("symbol_node_id")
    git_symbol_parser.add_argument("--max-results", type=int, default=10)
    add_json_flag(git_symbol_parser)

    report_parser = subparsers.add_parser(
        "report", help="build a deterministic structural report"
    )
    report_parser.add_argument("snapshot")
    report_parser.add_argument("--top-n", type=int, default=10)
    add_json_flag(report_parser)

    repo_map_parser = subparsers.add_parser(
        "repo-map", help="render a compact repository navigation map"
    )
    repo_map_parser.add_argument("snapshot")
    repo_map_parser.add_argument("--top-n", type=int, default=8)
    repo_map_parser.add_argument(
        "--handoff",
        action="store_true",
        help="render the shorter agent handoff view",
    )
    add_json_flag(repo_map_parser)

    topology_parser = subparsers.add_parser(
        "topology", help="summarize structural graph topology"
    )
    topology_parser.add_argument("snapshot")
    topology_parser.add_argument("--top-n", type=int, default=10)
    add_json_flag(topology_parser)

    doc_graph_parser = subparsers.add_parser(
        "doc-graph", help="summarize document backlinks and mention candidates"
    )
    doc_graph_parser.add_argument("snapshot")
    doc_graph_parser.add_argument("--top-n", type=int, default=10)
    add_json_flag(doc_graph_parser)


def _register_interchange_and_plan_commands(
    subparsers: argparse._SubParsersAction,
) -> None:
    interchange_parser = subparsers.add_parser(
        "interchange", help="emit stable symbol/reference interchange JSON"
    )
    interchange_parser.add_argument("snapshot")

    precise_import_parser = subparsers.add_parser(
        "precise-import",
        help="import an externally produced native SCIP index",
    )
    precise_import_parser.add_argument("scip_index")
    precise_import_parser.add_argument("--out", required=True)
    precise_import_parser.add_argument("--base")
    precise_import_parser.add_argument("--root", default="")
    precise_import_parser.add_argument("--namespace", default="scip")
    precise_import_parser.add_argument("--index-commit", default="")
    precise_import_parser.add_argument("--workspace-commit", default="")
    precise_import_parser.add_argument("--strict-freshness", action="store_true")
    add_json_flag(precise_import_parser)

    query_plan_parser = subparsers.add_parser(
        "query-plan", help="explain deterministic query execution facts"
    )
    query_plan_parser.add_argument("snapshot")
    query_plan_parser.add_argument("query")
    query_plan_parser.add_argument("--max-results", type=int, default=10)

    lineage_parser = subparsers.add_parser(
        "git-lineage", help="show observed git path lineage"
    )
    lineage_parser.add_argument("snapshot")
    lineage_parser.add_argument("path")
    lineage_parser.add_argument("--max-results", type=int, default=20)

    parser_support_parser = subparsers.add_parser(
        "parser-support", help="show parser family support matrix"
    )
    add_json_flag(parser_support_parser)


def _register_certify_export_commands(subparsers: argparse._SubParsersAction) -> None:
    certify_parser = subparsers.add_parser(
        "certify", help="emit snapshot certification facts"
    )
    certify_parser.add_argument("snapshot")
    certify_parser.add_argument("--top-n", type=int, default=10)
    certify_parser.add_argument("--markdown-out")
    add_json_flag(certify_parser)

    export_parser = subparsers.add_parser(
        "export", help="export a snapshot as graph text"
    )
    export_parser.add_argument("snapshot")
    export_parser.add_argument(
        "--format",
        choices=("dot", "mermaid"),
        default="dot",
        help="graph text format",
    )
    export_parser.add_argument(
        "--profile", choices=tuple(sorted(EXPORT_PROFILES)), default="full"
    )

    graphify_export_parser = subparsers.add_parser(
        "graphify-export", help="export a snapshot as Graphify-shaped JSON"
    )
    graphify_export_parser.add_argument("snapshot")

    graphify_import_parser = subparsers.add_parser(
        "graphify-import", help="import supported Graphify-shaped JSON"
    )
    graphify_import_parser.add_argument("payload")
    graphify_import_parser.add_argument("--out", required=True)
    graphify_import_parser.add_argument("--namespace", default="graphify")
    graphify_import_parser.add_argument("--root-path", default="")


def _register_refresh_profile_commands(
    subparsers: argparse._SubParsersAction,
) -> None:
    benchmark_parser = subparsers.add_parser(
        "benchmark", help="benchmark package operations against a local root"
    )
    benchmark_parser.add_argument("root")
    benchmark_parser.add_argument("--namespace", default="default")
    add_git_identity_mode_argument(benchmark_parser)
    benchmark_parser.add_argument("--query", default="README")
    benchmark_parser.add_argument("--max-results", type=int, default=10)
    benchmark_parser.add_argument("--top-n", type=int, default=10)
    add_json_flag(benchmark_parser)

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

    refresh_plan_parser = subparsers.add_parser(
        "refresh-plan",
        help="preview explicit refresh-visible path changes without mutating outputs",
    )
    refresh_plan_parser.add_argument("root")
    refresh_plan_parser.add_argument("--manifest-in")
    refresh_plan_parser.add_argument("--namespace", default="default")
    add_json_flag(refresh_plan_parser)

    refresh_status_parser = subparsers.add_parser(
        "refresh-status", help="inspect a persisted refresh status ledger"
    )
    refresh_status_parser.add_argument("state")
    add_json_flag(refresh_status_parser)

    profile_init_parser = subparsers.add_parser(
        "profile-init", help="write a repeatable explicit-refresh invocation profile"
    )
    profile_init_parser.add_argument("root")
    profile_init_parser.add_argument("--out", required=True)
    profile_init_parser.add_argument("--label", default="default")
    profile_init_parser.add_argument("--namespace", default="default")
    profile_init_parser.add_argument("--snapshot-out", required=True)
    profile_init_parser.add_argument("--manifest-out", required=True)
    profile_init_parser.add_argument("--state-out", required=True)
    profile_init_parser.add_argument("--cache-out")
    add_git_identity_mode_argument(profile_init_parser)
    add_json_flag(profile_init_parser)

    profile_run_parser = subparsers.add_parser(
        "profile-run", help="run one explicit refresh from a saved invocation profile"
    )
    profile_run_parser.add_argument("profile")
    add_json_flag(profile_run_parser)


def _register_navigation_service_commands(
    subparsers: argparse._SubParsersAction,
) -> None:
    neighborhood_parser = subparsers.add_parser(
        "neighborhood", help="show nodes around a snapshot node"
    )
    neighborhood_parser.add_argument("snapshot")
    neighborhood_parser.add_argument("node_id")
    neighborhood_parser.add_argument("--depth", type=int, default=1)
    neighborhood_parser.add_argument("--max-results", type=int, default=10)
    add_json_flag(neighborhood_parser)

    path_parser = subparsers.add_parser("path", help="find a bounded graph path")
    path_parser.add_argument("snapshot")
    path_parser.add_argument("source_id")
    path_parser.add_argument("target_id")
    path_parser.add_argument("--max-hops", type=int, default=4)
    add_json_flag(path_parser)

    health_parser = subparsers.add_parser("health", help="summarize a snapshot")
    health_parser.add_argument("snapshot")
    add_json_flag(health_parser)

    freshness_parser = subparsers.add_parser(
        "freshness",
        help="show snapshot freshness and optional structural delta facts",
    )
    freshness_parser.add_argument("snapshot", nargs="?")
    freshness_parser.add_argument("--config")
    freshness_parser.add_argument("--before")
    add_json_flag(freshness_parser)

    serve_parser = subparsers.add_parser(
        "serve", help="run the local newline-delimited JSON service"
    )
    serve_group = serve_parser.add_mutually_exclusive_group(required=True)
    serve_group.add_argument("--snapshot")
    serve_group.add_argument("--root")
    serve_group.add_argument("--workspace")
    serve_group.add_argument("--store")
    serve_parser.add_argument("--namespace", default="default")
    serve_parser.add_argument("--manifest-in")
    serve_parser.add_argument("--snapshot-out")
    serve_parser.add_argument("--manifest-out")
    serve_parser.add_argument("--state-out")
    serve_parser.add_argument("--cache")
    add_git_identity_mode_argument(serve_parser)


def register_core_commands(subparsers: argparse._SubParsersAction) -> None:
    _register_index_query_commands(subparsers)
    _register_git_and_graph_view_commands(subparsers)
    _register_interchange_and_plan_commands(subparsers)
    _register_certify_export_commands(subparsers)
    _register_refresh_profile_commands(subparsers)
    _register_navigation_service_commands(subparsers)


__all__ = [
    "add_git_identity_mode_argument",
    "add_json_flag",
    "register_core_commands",
]
