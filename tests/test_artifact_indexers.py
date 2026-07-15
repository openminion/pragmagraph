from __future__ import annotations

from pathlib import Path

from pragmagraph.adapters import index_path


def test_artifact_indexers_emit_cited_static_facts(tmp_path: Path) -> None:
    (tmp_path / "openapi.json").write_text(
        '{"openapi":"3.1.0","paths":{"/users":{"get":{}}},'
        '"components":{"schemas":{"User":{}}}}'
    )
    (tmp_path / "service.proto").write_text(
        "message Request {}\nservice Users {\n rpc Get(Request) returns (Request);\n}\n"
    )
    (tmp_path / "schema.sql").write_text(
        "CREATE TABLE users (id INT);\nCREATE TABLE posts (user_id INT REFERENCES users(id));\n"
    )
    (tmp_path / "main.tf").write_text('resource "aws_s3_bucket" "assets" {}\n')
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text(
        "jobs:\n  test:\n    steps:\n      - uses: actions/checkout@v4\n"
    )

    snapshot = index_path(tmp_path, namespace="artifacts")
    kinds = {node.kind for node in snapshot.nodes}

    assert {
        "api_endpoint",
        "api_schema",
        "proto_message",
        "proto_service",
        "proto_rpc",
        "sql_table",
        "terraform_block",
        "ci_job",
        "dependency_resolution",
    } <= kinds
    assert all(
        node.source_ref.path
        for node in snapshot.nodes
        if node.kind in kinds - {"project"}
    )
    sql_dependencies = [
        edge
        for edge in snapshot.edges
        if edge.kind == "depends_on"
        and snapshot.node_map().get(edge.source_id) is not None
        and snapshot.node_map()[edge.source_id].kind == "sql_table"
    ]
    assert len(sql_dependencies) == 1


def test_manifest_and_lockfile_dependency_facts_resolve_by_exact_name(
    tmp_path: Path,
) -> None:
    (tmp_path / "package.json").write_text(
        '{"dependencies":{"react":"^19.0.0","zod":"^4.0.0"}}'
    )
    (tmp_path / "package-lock.json").write_text(
        '{"packages":{"node_modules/react":{"name":"react","version":"19.1.0"}}}'
    )

    snapshot = index_path(tmp_path, namespace="deps")

    resolved = [edge for edge in snapshot.edges if edge.kind == "resolves_to"]
    unresolved = [
        item for item in snapshot.omitted if item.reason == "dependency_unresolved"
    ]
    assert len(resolved) == 1
    assert any(item.details["package"] == "zod" for item in unresolved)


def test_malformed_manifest_emits_typed_diagnostic(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{broken")

    snapshot = index_path(tmp_path, namespace="broken")

    assert any(item.reason == "artifact_parse_error" for item in snapshot.omitted)


def test_malformed_openapi_shape_emits_typed_diagnostic(tmp_path: Path) -> None:
    (tmp_path / "openapi.json").write_text(
        '{"openapi":"3.1.0","paths":[]}', encoding="utf-8"
    )

    snapshot = index_path(tmp_path, namespace="broken-openapi")

    assert any(item.reason == "artifact_parse_error" for item in snapshot.omitted)
