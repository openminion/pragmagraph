"""Observed-fact parsers for common repository artifacts."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from typing import Any, Mapping

from pragmagraph.contracts import (
    EDGE_DEFINES,
    EDGE_DEPENDS_ON,
    NODE_API_ENDPOINT,
    NODE_API_SCHEMA,
    NODE_CI_JOB,
    NODE_DEPENDENCY_DECLARATION,
    NODE_DEPENDENCY_RESOLUTION,
    NODE_PROTO_MESSAGE,
    NODE_PROTO_RPC,
    NODE_PROTO_SERVICE,
    NODE_SQL_TABLE,
    NODE_TERRAFORM_BLOCK,
)
from pragmagraph.models import (
    GraphEdge,
    GraphNode,
    ParserDiagnostic,
    ParserResult,
    SourceRef,
)
from pragmagraph.portability import edge_id, node_id

ARTIFACT_PARSER_VERSION = "pragmagraph.artifacts.v1alpha1"
HTTP_METHODS = frozenset(
    {"delete", "get", "head", "options", "patch", "post", "put", "trace"}
)


def parse_artifact(
    *,
    namespace: str,
    rel: str,
    file_id: str,
    path: Path,
    text: str,
) -> ParserResult:
    """Parse one recognized artifact; return an empty result when not applicable."""
    name = path.name.lower()
    suffix = path.suffix.lower()
    if _is_openapi(rel, text):
        return _parse_openapi(namespace, rel, file_id, text)
    if suffix == ".proto":
        return _parse_proto(namespace, rel, file_id, text)
    if suffix == ".sql":
        return _parse_sql(namespace, rel, file_id, text)
    if suffix == ".tf":
        return _parse_terraform(namespace, rel, file_id, text)
    if _is_ci_workflow(rel):
        return _parse_ci_workflow(namespace, rel, file_id, text)
    if name in {"package.json", "package-lock.json"}:
        return _parse_npm(
            namespace,
            rel,
            file_id,
            text,
            locked=name == "package-lock.json",
        )
    if name == "pyproject.toml":
        return _parse_pyproject(namespace, rel, file_id, text)
    if name in {"poetry.lock", "uv.lock"}:
        return _parse_python_lock(namespace, rel, file_id, text)
    if name.startswith("requirements") and suffix in {"", ".txt", ".in"}:
        return _parse_requirements(namespace, rel, file_id, text)
    return ParserResult()


class _Facts:
    def __init__(self, namespace: str, rel: str, file_id: str) -> None:
        self.namespace = namespace
        self.rel = rel
        self.file_id = file_id
        self.nodes: dict[str, GraphNode] = {}
        self.edges: dict[str, GraphEdge] = {}
        self.diagnostics: list[ParserDiagnostic] = []

    def add(
        self,
        kind: str,
        key: str,
        label: str,
        *,
        line: int | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> str:
        item_id = node_id(self.namespace, kind, f"{self.rel}:{key}")
        source_ref = SourceRef(path=self.rel, line=line)
        self.nodes[item_id] = GraphNode(
            id=item_id,
            kind=kind,
            label=label,
            source_ref=source_ref,
            metadata={
                "parser": "artifact",
                "parser_version": ARTIFACT_PARSER_VERSION,
                **dict(metadata or {}),
            },
        )
        relation_id = edge_id(self.namespace, self.file_id, EDGE_DEFINES, item_id)
        self.edges[relation_id] = GraphEdge(
            id=relation_id,
            kind=EDGE_DEFINES,
            source_id=self.file_id,
            target_id=item_id,
            source_ref=source_ref,
        )
        return item_id

    def depends(
        self, source_id: str, target_id: str, *, line: int | None = None
    ) -> None:
        relation_id = edge_id(self.namespace, source_id, EDGE_DEPENDS_ON, target_id)
        self.edges[relation_id] = GraphEdge(
            id=relation_id,
            kind=EDGE_DEPENDS_ON,
            source_id=source_id,
            target_id=target_id,
            source_ref=SourceRef(path=self.rel, line=line),
        )

    def diagnostic(self, code: str, message: str) -> None:
        self.diagnostics.append(
            ParserDiagnostic(code=code, message=message, path=self.rel)
        )

    def result(self) -> ParserResult:
        return ParserResult(
            nodes=tuple(sorted(self.nodes.values(), key=lambda item: item.id)),
            edges=tuple(sorted(self.edges.values(), key=lambda item: item.id)),
            diagnostics=tuple(self.diagnostics),
        )


def _is_openapi(rel: str, text: str) -> bool:
    name = Path(rel).name.lower()
    return "openapi" in name or bool(re.search(r"(?m)^\s*(openapi|swagger)\s*:", text))


def _is_ci_workflow(rel: str) -> bool:
    normalized = rel.replace("\\", "/").lower()
    return normalized.startswith(".github/workflows/") and normalized.endswith(
        (".yml", ".yaml")
    )


def _parse_openapi(namespace: str, rel: str, file_id: str, text: str) -> ParserResult:
    facts = _Facts(namespace, rel, file_id)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, Mapping):
        paths = payload.get("paths")
        if paths is None:
            paths = {}
        if not isinstance(paths, Mapping):
            facts.diagnostic("artifact_parse_error", "OpenAPI paths must be an object")
            return facts.result()
        for route, operations in sorted(paths.items()):
            if not isinstance(operations, Mapping):
                continue
            for method in sorted(set(operations) & HTTP_METHODS):
                facts.add(
                    NODE_API_ENDPOINT,
                    f"{method}:{route}",
                    f"{method.upper()} {route}",
                    metadata={"method": method.upper(), "route": route},
                )
        components = payload.get("components") or {}
        schemas = (
            components.get("schemas") or {} if isinstance(components, Mapping) else {}
        )
        if isinstance(schemas, Mapping):
            for schema in sorted(schemas):
                facts.add(NODE_API_SCHEMA, str(schema), str(schema))
        return facts.result()
    current_route = ""
    for line_number, line in enumerate(text.splitlines(), start=1):
        route = re.match(r"^\s{2}(/[^:]+):\s*$", line)
        if route:
            current_route = route.group(1)
            continue
        method = re.match(
            r"^\s{4}(get|post|put|patch|delete|head|options|trace):\s*$", line, re.I
        )
        if method and current_route:
            value = method.group(1).upper()
            facts.add(
                NODE_API_ENDPOINT,
                f"{value}:{current_route}",
                f"{value} {current_route}",
                line=line_number,
                metadata={
                    "method": value,
                    "route": current_route,
                    "syntax": "yaml_lexical",
                },
            )
    if not facts.nodes:
        facts.diagnostic(
            "artifact_parse_incomplete", "OpenAPI paths were not recoverable"
        )
    return facts.result()


def _parse_proto(namespace: str, rel: str, file_id: str, text: str) -> ParserResult:
    facts = _Facts(namespace, rel, file_id)
    service_id = ""
    for line_number, line in enumerate(text.splitlines(), start=1):
        message = re.search(r"\bmessage\s+([A-Za-z_]\w*)", line)
        service = re.search(r"\bservice\s+([A-Za-z_]\w*)", line)
        rpc = re.search(
            r"\brpc\s+([A-Za-z_]\w*)\s*\(([^)]*)\)\s*returns\s*\(([^)]*)\)", line
        )
        if message:
            facts.add(
                NODE_PROTO_MESSAGE, message.group(1), message.group(1), line=line_number
            )
        if service:
            service_id = facts.add(
                NODE_PROTO_SERVICE, service.group(1), service.group(1), line=line_number
            )
        if rpc:
            rpc_id = facts.add(
                NODE_PROTO_RPC,
                rpc.group(1),
                rpc.group(1),
                line=line_number,
                metadata={
                    "request_type": rpc.group(2).strip(),
                    "response_type": rpc.group(3).strip(),
                },
            )
            if service_id:
                facts.depends(service_id, rpc_id, line=line_number)
    return _complete_or_diagnose(
        facts, text, "protobuf declarations were not recoverable"
    )


def _parse_sql(namespace: str, rel: str, file_id: str, text: str) -> ParserResult:
    facts = _Facts(namespace, rel, file_id)
    statements = tuple(
        re.finditer(
            r"(?is)\bcreate\s+table\s+(?:if\s+not\s+exists\s+)?([\w.\"`]+)\s*\((.*?)\)\s*;",
            text,
        )
    )
    table_ids = {
        match.group(1).strip('"`'): facts.add(
            NODE_SQL_TABLE,
            match.group(1).strip('"`'),
            match.group(1).strip('"`'),
            line=_line(text, match.start()),
        )
        for match in statements
    }
    for statement in statements:
        source_id = table_ids[statement.group(1).strip('"`')]
        for reference in re.finditer(
            r"(?is)\breferences\s+([\w.\"`]+)", statement.group(2)
        ):
            target = reference.group(1).strip('"`')
            line = _line(text, statement.start() + reference.start())
            target_id = table_ids.get(target) or facts.add(
                NODE_SQL_TABLE,
                f"external:{target}",
                target,
                line=line,
                metadata={"external": True},
            )
            facts.depends(source_id, target_id, line=line)
    return _complete_or_diagnose(
        facts, text, "SQL table declarations were not recoverable"
    )


def _parse_terraform(namespace: str, rel: str, file_id: str, text: str) -> ParserResult:
    facts = _Facts(namespace, rel, file_id)
    pattern = re.compile(
        r'(?m)^\s*(resource|data|module|provider)\s+"([^"]+)"(?:\s+"([^"]+)")?\s*\{'
    )
    for match in pattern.finditer(text):
        block_type, first, second = match.groups()
        label = ".".join(item for item in (block_type, first, second) if item)
        facts.add(
            NODE_TERRAFORM_BLOCK,
            label,
            label,
            line=_line(text, match.start()),
            metadata={"block_type": block_type, "type": first, "name": second or ""},
        )
    return _complete_or_diagnose(facts, text, "Terraform blocks were not recoverable")


def _parse_ci_workflow(
    namespace: str, rel: str, file_id: str, text: str
) -> ParserResult:
    facts = _Facts(namespace, rel, file_id)
    in_jobs = False
    for line_number, line in enumerate(text.splitlines(), start=1):
        if re.match(r"^jobs:\s*$", line):
            in_jobs = True
            continue
        job = re.match(r"^\s{2}([A-Za-z0-9_-]+):\s*$", line) if in_jobs else None
        if job:
            facts.add(NODE_CI_JOB, job.group(1), job.group(1), line=line_number)
        use = re.search(r"\buses:\s*([^\s#]+)", line)
        if use:
            _dependency(
                facts, "github-actions", use.group(1), "", line_number, resolved=True
            )
    return _complete_or_diagnose(
        facts, text, "CI jobs or uses facts were not recoverable"
    )


def _parse_npm(
    namespace: str, rel: str, file_id: str, text: str, *, locked: bool
) -> ParserResult:
    facts = _Facts(namespace, rel, file_id)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        facts.diagnostic("artifact_parse_error", f"invalid JSON: {exc.msg}")
        return facts.result()
    if not isinstance(payload, Mapping):
        facts.diagnostic("artifact_parse_error", "npm manifest must be an object")
        return facts.result()
    for group in (
        "dependencies",
        "devDependencies",
        "peerDependencies",
        "optionalDependencies",
    ):
        values = payload.get(group) or {}
        if isinstance(values, Mapping):
            for name, version in sorted(values.items()):
                _dependency(
                    facts,
                    "npm",
                    str(name),
                    str(version),
                    None,
                    resolved=locked,
                    group=group,
                )
    if locked:
        for package_path, details in sorted((payload.get("packages") or {}).items()):
            if not package_path or not isinstance(details, Mapping):
                continue
            name = str(
                details.get("name") or package_path.rsplit("node_modules/", 1)[-1]
            )
            version = str(details.get("version") or "")
            if name and version:
                _dependency(
                    facts, "npm", name, version, None, resolved=True, group="packages"
                )
    return facts.result()


def _parse_pyproject(namespace: str, rel: str, file_id: str, text: str) -> ParserResult:
    facts = _Facts(namespace, rel, file_id)
    try:
        payload = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        facts.diagnostic("artifact_parse_error", f"invalid TOML: {exc}")
        return facts.result()
    project = payload.get("project") or {}
    if isinstance(project, Mapping):
        for value in project.get("dependencies", ()) or ():
            name, constraint = _pep508(str(value))
            _dependency(
                facts, "python", name, constraint, None, resolved=False, group="project"
            )
        optional = project.get("optional-dependencies") or {}
        if isinstance(optional, Mapping):
            for group, values in sorted(optional.items()):
                for value in values or ():
                    name, constraint = _pep508(str(value))
                    _dependency(
                        facts,
                        "python",
                        name,
                        constraint,
                        None,
                        resolved=False,
                        group=str(group),
                    )
    return facts.result()


def _parse_python_lock(
    namespace: str, rel: str, file_id: str, text: str
) -> ParserResult:
    facts = _Facts(namespace, rel, file_id)
    try:
        payload = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        facts.diagnostic("artifact_parse_error", f"invalid TOML: {exc}")
        return facts.result()
    packages = payload.get("package") or ()
    if isinstance(packages, list):
        for item in packages:
            if isinstance(item, Mapping) and item.get("name"):
                _dependency(
                    facts,
                    "python",
                    str(item["name"]),
                    str(item.get("version") or ""),
                    None,
                    resolved=True,
                    group="lock",
                )
    return facts.result()


def _parse_requirements(
    namespace: str, rel: str, file_id: str, text: str
) -> ParserResult:
    facts = _Facts(namespace, rel, file_id)
    for line_number, raw in enumerate(text.splitlines(), start=1):
        value = raw.split("#", 1)[0].strip()
        if not value or value.startswith(("-", "http:", "https:")):
            continue
        name, constraint = _pep508(value)
        _dependency(
            facts,
            "python",
            name,
            constraint,
            line_number,
            resolved=False,
            group="requirements",
        )
    return facts.result()


def _dependency(
    facts: _Facts,
    ecosystem: str,
    name: str,
    version: str,
    line: int | None,
    *,
    resolved: bool,
    group: str = "",
) -> str:
    kind = NODE_DEPENDENCY_RESOLUTION if resolved else NODE_DEPENDENCY_DECLARATION
    return facts.add(
        kind,
        f"{ecosystem}:{name}:{'resolved' if resolved else 'declared'}",
        name,
        line=line,
        metadata={
            "ecosystem": ecosystem,
            "package": name,
            "version": version,
            "group": group,
            "resolved": resolved,
        },
    )


def _pep508(value: str) -> tuple[str, str]:
    match = re.match(r"\s*([A-Za-z0-9_.-]+)\s*(.*)", value)
    return (match.group(1), match.group(2).strip()) if match else (value, "")


def _line(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _complete_or_diagnose(facts: _Facts, text: str, message: str) -> ParserResult:
    if text.strip() and not facts.nodes:
        facts.diagnostic("artifact_parse_incomplete", message)
    return facts.result()


__all__ = ["ARTIFACT_PARSER_VERSION", "parse_artifact"]
