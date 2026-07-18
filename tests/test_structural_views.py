from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from pragmagraph.adapters import index_path
from pragmagraph.certification import (
    build_certification_pack,
    build_privacy_profile,
    render_markdown_certification_pack,
)
from pragmagraph.docgraph import build_doc_graph_summary
from pragmagraph.interchange import build_symbol_reference_bundle
from pragmagraph.parser_support import build_parser_support_matrix
from pragmagraph.planner import explain_query_plan
from pragmagraph.storage import save_snapshot
from pragmagraph.topology import build_topology_summary

from .package_paths import build_fixture_repo


def _repo(tmp_path: Path) -> Path:
    return build_fixture_repo(
        tmp_path,
        repo_name="view-repo",
        files={
            "README.md": (
                "# Runtime Graph\n\n"
                "See RuntimeGraph in src/app.py and [Guide](docs/guide.md).\n"
            ),
            "docs/guide.md": "# Guide\n\nRuntimeGraph explains the static graph.\n",
            "src/app.py": (
                "class RuntimeGraph:\n"
                "    pass\n\n"
                "def build_runtime_graph():\n"
                "    return RuntimeGraph()\n"
            ),
        },
    )


def test_structural_view_helpers_are_observed_fact_only(tmp_path) -> None:
    snapshot = index_path(_repo(tmp_path), namespace="fixture")

    bundle = build_symbol_reference_bundle(snapshot)
    topology = build_topology_summary(snapshot, top_n=5)
    doc_graph = build_doc_graph_summary(snapshot, top_n=5)
    plan = explain_query_plan(snapshot, "RuntimeGraph")
    privacy = build_privacy_profile(snapshot)
    certification = build_certification_pack(snapshot, top_n=5)
    certification_markdown = render_markdown_certification_pack(certification)
    parser_support = build_parser_support_matrix()

    assert bundle.format == "pragmagraph.symbol_reference.v1alpha1"
    assert any(symbol.label == "RuntimeGraph" for symbol in bundle.symbols)
    assert bundle.diagnostics["reference_count"] >= 1
    assert topology.node_count == len(snapshot.nodes)
    assert topology.high_degree_nodes
    assert doc_graph.doc_section_count >= 1
    assert doc_graph.unlinked_candidate_count >= 1
    assert plan.strategy == "lexical_structural"
    assert plan.candidate_count >= plan.returned_count
    assert privacy.export_safe is True
    assert certification.privacy.export_safe is True
    assert "# PragmaGraph Certification Pack" in certification_markdown
    assert "## Parser Coverage" in certification_markdown
    assert any(row.family == "python_ast" for row in parser_support)


def test_structural_view_cli_commands_emit_json(tmp_path) -> None:
    snapshot_path = tmp_path / "snapshot.json"
    markdown_path = tmp_path / "certification.md"
    save_snapshot(index_path(_repo(tmp_path), namespace="fixture"), snapshot_path)

    commands = [
        ["interchange", str(snapshot_path)],
        ["query-plan", str(snapshot_path), "RuntimeGraph"],
        ["topology", str(snapshot_path), "--json"],
        ["doc-graph", str(snapshot_path), "--json"],
        ["certify", str(snapshot_path)],
        ["parser-support", "--json"],
    ]
    env = dict(os.environ)
    package_root = Path(__file__).resolve().parents[1]
    graphfakos_src = package_root.parent / "graphfakos" / "src"
    env["PYTHONPATH"] = os.pathsep.join(
        (str(package_root / "src"), str(graphfakos_src))
    )
    for command in commands:
        payload = json.loads(
            subprocess.run(
                [sys.executable, "-m", "pragmagraph", *command],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            ).stdout
        )
        assert payload

    certification_payload = json.loads(
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pragmagraph",
                "certify",
                str(snapshot_path),
                "--markdown-out",
                str(markdown_path),
                "--json",
            ],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        ).stdout
    )
    assert certification_payload["privacy"]["export_safe"] is True
    assert "# PragmaGraph Certification Pack" in markdown_path.read_text(
        encoding="utf-8"
    )
