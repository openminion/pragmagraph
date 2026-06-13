"""Local git-history overlays for PragmaGraph snapshots."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path
from typing import Mapping

from pragmagraph.contracts import (
    EDGE_GIT_CHANGES_PATH,
    EDGE_GIT_PARENT,
    EDGE_GIT_TOUCHES,
    NODE_FILE,
    NODE_GIT_CHANGED_PATH,
    NODE_GIT_COMMIT,
)
from pragmagraph.models import GraphEdge, GraphNode, OmittedDiagnostic, SourceRef
from pragmagraph.portability import edge_id, node_id, normalize_relative_path

DEFAULT_GIT_IDENTITY_MODE = "name_email_hash"
GIT_IDENTITY_MODE_FULL = "full"
SUPPORTED_GIT_IDENTITY_MODES = frozenset(
    {DEFAULT_GIT_IDENTITY_MODE, GIT_IDENTITY_MODE_FULL}
)

_FIELD_SEPARATOR = "\x1f"
_RECORD_SEPARATOR = "\x1e"
_GIT_LOG_FORMAT = (
    f"{_RECORD_SEPARATOR}%H{_FIELD_SEPARATOR}%P{_FIELD_SEPARATOR}%at"
    f"{_FIELD_SEPARATOR}%ai{_FIELD_SEPARATOR}%aN{_FIELD_SEPARATOR}%aE"
    f"{_FIELD_SEPARATOR}%ct{_FIELD_SEPARATOR}%ci{_FIELD_SEPARATOR}%cN"
    f"{_FIELD_SEPARATOR}%cE{_FIELD_SEPARATOR}%s"
)


def validate_git_identity_mode(mode: str) -> str:
    """Return a canonical git identity mode or raise for invalid input."""
    normalized = str(mode or DEFAULT_GIT_IDENTITY_MODE).strip().lower()
    if normalized not in SUPPORTED_GIT_IDENTITY_MODES:
        supported = ", ".join(sorted(SUPPORTED_GIT_IDENTITY_MODES))
        raise ValueError(
            f"unsupported git identity mode {mode!r}; expected one of: {supported}"
        )
    return normalized


def collect_git_overlay(
    *,
    root: Path,
    namespace: str,
    nodes_by_id: Mapping[str, GraphNode],
    git_identity_mode: str = DEFAULT_GIT_IDENTITY_MODE,
) -> tuple[
    tuple[GraphNode, ...],
    tuple[GraphEdge, ...],
    tuple[OmittedDiagnostic, ...],
    dict[str, object],
]:
    """Return git overlay nodes/edges/diagnostics plus overlay stats."""
    identity_mode = validate_git_identity_mode(git_identity_mode)
    try:
        repo_root = _resolve_repo_root(root)
    except FileNotFoundError:
        return (
            (),
            (),
            (_git_diagnostic("git_unavailable", root),),
            _overlay_stats(
                enabled=False,
                identity_mode=identity_mode,
            ),
        )
    if repo_root is None:
        return (
            (),
            (),
            (_git_diagnostic("git_not_repo", root),),
            _overlay_stats(
                enabled=False,
                identity_mode=identity_mode,
            ),
        )

    prefix = _root_prefix(repo_root, root)
    shallow = _is_shallow_repository(repo_root)
    diagnostics: list[OmittedDiagnostic] = []
    if shallow:
        diagnostics.append(
            OmittedDiagnostic(
                reason="git_shallow_repository",
                item_id="git_history",
                details={"repo_root": str(repo_root)},
            )
        )

    file_nodes_by_path = {
        node.source_ref.path: node
        for node in nodes_by_id.values()
        if node.kind == NODE_FILE and node.source_ref.path
    }

    try:
        records = _read_git_history(repo_root)
    except FileNotFoundError:
        return (
            (),
            (),
            (_git_diagnostic("git_unavailable", root),),
            _overlay_stats(
                enabled=False,
                identity_mode=identity_mode,
            ),
        )
    except subprocess.CalledProcessError as exc:
        diagnostics.append(
            OmittedDiagnostic(
                reason="git_history_unsupported",
                item_id="git_history",
                details={
                    "repo_root": str(repo_root),
                    "returncode": exc.returncode,
                },
            )
        )
        return (
            (),
            (),
            tuple(diagnostics),
            _overlay_stats(
                enabled=False,
                identity_mode=identity_mode,
            ),
        )

    overlay_nodes: dict[str, GraphNode] = {}
    overlay_edges: dict[str, GraphEdge] = {}
    included_commits: dict[str, str] = {}

    for record in records:
        changed_paths = tuple(
            change
            for change in (
                _normalize_changed_path(change, prefix) for change in record["changes"]
            )
            if change is not None
        )
        if not changed_paths:
            continue
        commit_hash = str(record["commit_hash"])
        commit_node = _commit_node(
            namespace=namespace,
            commit_hash=commit_hash,
            parents=tuple(str(parent) for parent in record["parents"]),
            author_name=str(record["author_name"]),
            author_email=str(record["author_email"]),
            author_time_epoch=int(record["author_time_epoch"]),
            author_time_offset=str(record["author_time_offset"]),
            committer_name=str(record["committer_name"]),
            committer_email=str(record["committer_email"]),
            committer_time_epoch=int(record["committer_time_epoch"]),
            committer_time_offset=str(record["committer_time_offset"]),
            subject=str(record["subject"]),
            identity_mode=identity_mode,
            touched_path_count=len(changed_paths),
        )
        overlay_nodes[commit_node.id] = commit_node
        included_commits[commit_hash] = commit_node.id

        for changed_path in changed_paths:
            path_node = _changed_path_node(
                namespace=namespace,
                changed_path=changed_path["path"],
                current_exists=changed_path["path"] in file_nodes_by_path,
            )
            overlay_nodes[path_node.id] = path_node
            overlay_edges[
                edge_id(namespace, commit_node.id, EDGE_GIT_CHANGES_PATH, path_node.id)
            ] = GraphEdge(
                id=edge_id(
                    namespace,
                    commit_node.id,
                    EDGE_GIT_CHANGES_PATH,
                    path_node.id,
                ),
                kind=EDGE_GIT_CHANGES_PATH,
                source_id=commit_node.id,
                target_id=path_node.id,
                source_ref=SourceRef(path=changed_path["path"]),
                metadata={
                    "additions": changed_path["additions"],
                    "deletions": changed_path["deletions"],
                },
            )
            file_node = file_nodes_by_path.get(changed_path["path"])
            if file_node is not None:
                overlay_edges[
                    edge_id(namespace, commit_node.id, EDGE_GIT_TOUCHES, file_node.id)
                ] = GraphEdge(
                    id=edge_id(
                        namespace,
                        commit_node.id,
                        EDGE_GIT_TOUCHES,
                        file_node.id,
                    ),
                    kind=EDGE_GIT_TOUCHES,
                    source_id=commit_node.id,
                    target_id=file_node.id,
                    source_ref=SourceRef(path=changed_path["path"]),
                    metadata={
                        "additions": changed_path["additions"],
                        "deletions": changed_path["deletions"],
                    },
                )

    for record in records:
        commit_id = included_commits.get(str(record["commit_hash"]))
        if commit_id is None:
            continue
        for parent_hash in record["parents"]:
            parent_id = included_commits.get(str(parent_hash))
            if parent_id is None:
                continue
            overlay_edges[edge_id(namespace, commit_id, EDGE_GIT_PARENT, parent_id)] = (
                GraphEdge(
                    id=edge_id(namespace, commit_id, EDGE_GIT_PARENT, parent_id),
                    kind=EDGE_GIT_PARENT,
                    source_id=commit_id,
                    target_id=parent_id,
                    source_ref=SourceRef(uri=f"git://commit/{record['commit_hash']}"),
                )
            )

    stats = _overlay_stats(
        enabled=True,
        identity_mode=identity_mode,
        repo_root=str(repo_root),
        root_prefix=prefix,
        commit_count=sum(
            1 for node in overlay_nodes.values() if node.kind == NODE_GIT_COMMIT
        ),
        changed_path_count=sum(
            1 for node in overlay_nodes.values() if node.kind == NODE_GIT_CHANGED_PATH
        ),
        shallow=shallow,
    )
    return (
        tuple(sorted(overlay_nodes.values(), key=lambda item: item.id)),
        tuple(sorted(overlay_edges.values(), key=lambda item: item.id)),
        tuple(diagnostics),
        stats,
    )


def _resolve_repo_root(root: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
            env=_git_env(),
        )
    except FileNotFoundError:
        raise
    except subprocess.CalledProcessError:
        return None
    output = result.stdout.strip()
    return Path(output).resolve() if output else None


def _is_shallow_repository(repo_root: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--is-shallow-repository"],
            check=True,
            capture_output=True,
            text=True,
            env=_git_env(),
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False
    return result.stdout.strip().lower() == "true"


def _read_git_history(repo_root: Path) -> list[dict[str, object]]:
    result = subprocess.run(
        [
            "git",
            "-c",
            "core.quotepath=false",
            "-C",
            str(repo_root),
            "log",
            "--date-order",
            "--no-renames",
            f"--format={_GIT_LOG_FORMAT}",
            "--numstat",
            "--",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=_git_env(),
    )
    records: list[dict[str, object]] = []
    for raw_record in result.stdout.split(_RECORD_SEPARATOR):
        payload = raw_record.strip()
        if not payload:
            continue
        lines = payload.splitlines()
        header = lines[0]
        fields = header.split(_FIELD_SEPARATOR)
        if len(fields) != 11:
            continue
        changes: list[dict[str, object]] = []
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) != 3:
                continue
            additions, deletions, path_text = parts
            changes.append(
                {
                    "path": normalize_relative_path(path_text),
                    "additions": _numstat_value(additions),
                    "deletions": _numstat_value(deletions),
                }
            )
        records.append(
            {
                "commit_hash": fields[0],
                "parents": tuple(
                    parent for parent in fields[1].split(" ") if parent.strip()
                ),
                "author_time_epoch": int(fields[2] or 0),
                "author_time_offset": _git_offset(fields[3]),
                "author_name": fields[4],
                "author_email": fields[5],
                "committer_time_epoch": int(fields[6] or 0),
                "committer_time_offset": _git_offset(fields[7]),
                "committer_name": fields[8],
                "committer_email": fields[9],
                "subject": fields[10],
                "changes": tuple(changes),
            }
        )
    return records


def _commit_node(
    *,
    namespace: str,
    commit_hash: str,
    parents: tuple[str, ...],
    author_name: str,
    author_email: str,
    author_time_epoch: int,
    author_time_offset: str,
    committer_name: str,
    committer_email: str,
    committer_time_epoch: int,
    committer_time_offset: str,
    subject: str,
    identity_mode: str,
    touched_path_count: int,
) -> GraphNode:
    metadata = {
        "commit_hash": commit_hash,
        "short_commit_hash": commit_hash[:12],
        "parent_hashes": parents,
        "subject": subject,
        "author_name": author_name,
        "author_time_epoch": author_time_epoch,
        "author_time_offset": author_time_offset,
        "committer_name": committer_name,
        "committer_time_epoch": committer_time_epoch,
        "committer_time_offset": committer_time_offset,
        "git_identity_mode": identity_mode,
        "touched_path_count": touched_path_count,
    }
    if identity_mode == GIT_IDENTITY_MODE_FULL:
        metadata["author_email"] = author_email
        metadata["committer_email"] = committer_email
    else:
        metadata["author_email_hash"] = _hash_identity(author_email)
        metadata["committer_email_hash"] = _hash_identity(committer_email)
    return GraphNode(
        id=node_id(namespace, NODE_GIT_COMMIT, commit_hash),
        kind=NODE_GIT_COMMIT,
        label=commit_hash[:12],
        source_ref=SourceRef(uri=f"git://commit/{commit_hash}"),
        text=subject,
        metadata=metadata,
    )


def _changed_path_node(
    *,
    namespace: str,
    changed_path: str,
    current_exists: bool,
) -> GraphNode:
    return GraphNode(
        id=node_id(namespace, NODE_GIT_CHANGED_PATH, changed_path),
        kind=NODE_GIT_CHANGED_PATH,
        label=changed_path,
        source_ref=SourceRef(path=changed_path),
        metadata={"current_exists": current_exists},
    )


def _root_prefix(repo_root: Path, root: Path) -> str:
    if repo_root == root:
        return ""
    return normalize_relative_path(root.relative_to(repo_root))


def _normalize_changed_path(
    change: Mapping[str, object],
    prefix: str,
) -> dict[str, object] | None:
    path = normalize_relative_path(str(change["path"]))
    if prefix:
        prefix_match = f"{prefix}/"
        if path == prefix:
            local_path = "."
        elif path.startswith(prefix_match):
            local_path = path[len(prefix_match) :]
        else:
            return None
    else:
        local_path = path
    return {
        "path": normalize_relative_path(local_path),
        "additions": change["additions"],
        "deletions": change["deletions"],
    }


def _hash_identity(value: str) -> str:
    return hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()


def _numstat_value(raw_value: str) -> int | None:
    text = raw_value.strip()
    if text == "-" or not text:
        return None
    return int(text)


def _git_offset(timestamp: str) -> str:
    parts = str(timestamp).strip().rsplit(" ", 1)
    if len(parts) == 2:
        return parts[1]
    return ""


def _git_env() -> dict[str, str]:
    env = dict(os.environ)
    env.setdefault("LC_ALL", "C")
    return env


def _git_diagnostic(reason: str, root: Path) -> OmittedDiagnostic:
    return OmittedDiagnostic(
        reason=reason,
        item_id="git_history",
        details={"root_path": str(root.resolve())},
    )


def _overlay_stats(
    *,
    enabled: bool,
    identity_mode: str,
    repo_root: str = "",
    root_prefix: str = "",
    commit_count: int = 0,
    changed_path_count: int = 0,
    shallow: bool = False,
) -> dict[str, object]:
    return {
        "git_overlay_enabled": enabled,
        "git_identity_mode": identity_mode,
        "git_repo_root": repo_root,
        "git_root_prefix": root_prefix,
        "git_commit_count": commit_count,
        "git_changed_path_count": changed_path_count,
        "git_shallow_repository": shallow,
    }


__all__ = [
    "DEFAULT_GIT_IDENTITY_MODE",
    "GIT_IDENTITY_MODE_FULL",
    "SUPPORTED_GIT_IDENTITY_MODES",
    "collect_git_overlay",
    "validate_git_identity_mode",
]
