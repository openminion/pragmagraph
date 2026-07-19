"""Release-readiness certification facts for PragmaGraph snapshots."""

from __future__ import annotations

from collections import Counter
import hashlib
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any, Mapping

from pragmagraph._immutables import frozen_mapping
from pragmagraph.models import GraphSnapshot
from pragmagraph.topology import TopologySummary, build_topology_summary
from pragmagraph.storage import stable_dumps


@dataclass(frozen=True)
class PrivacyProfile:
    """Observed privacy/export posture for one snapshot."""

    full_git_email_count: int = 0
    hashed_git_email_count: int = 0
    absolute_path_ref_count: int = 0
    git_identity_mode: str = ""
    export_safe: bool = True
    diagnostics: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "diagnostics", frozen_mapping(self.diagnostics))

    def to_dict(self) -> dict[str, Any]:
        return {
            "full_git_email_count": self.full_git_email_count,
            "hashed_git_email_count": self.hashed_git_email_count,
            "absolute_path_ref_count": self.absolute_path_ref_count,
            "git_identity_mode": self.git_identity_mode,
            "export_safe": self.export_safe,
            "diagnostics": dict(self.diagnostics),
        }


@dataclass(frozen=True)
class CertificationPack:
    """One deterministic package certification pack."""

    namespace: str
    node_count: int
    edge_count: int
    omitted_count: int
    parser_set: tuple[str, ...] = ()
    node_kinds: Mapping[str, int] = field(default_factory=dict)
    edge_kinds: Mapping[str, int] = field(default_factory=dict)
    omitted_reasons: Mapping[str, int] = field(default_factory=dict)
    cross_repo_resolution: Mapping[str, Any] = field(default_factory=dict)
    privacy: PrivacyProfile = field(default_factory=PrivacyProfile)
    topology: TopologySummary | None = None
    canonical_snapshot_hash: str = ""
    canonical_snapshot_bytes: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "parser_set", tuple(self.parser_set))
        object.__setattr__(self, "node_kinds", frozen_mapping(self.node_kinds))
        object.__setattr__(self, "edge_kinds", frozen_mapping(self.edge_kinds))
        object.__setattr__(
            self, "omitted_reasons", frozen_mapping(self.omitted_reasons)
        )
        object.__setattr__(
            self, "cross_repo_resolution", frozen_mapping(self.cross_repo_resolution)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "namespace": self.namespace,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "omitted_count": self.omitted_count,
            "parser_set": list(self.parser_set),
            "node_kinds": dict(self.node_kinds),
            "edge_kinds": dict(self.edge_kinds),
            "omitted_reasons": dict(self.omitted_reasons),
            "cross_repo_resolution": dict(self.cross_repo_resolution),
            "privacy": self.privacy.to_dict(),
            "topology": self.topology.to_dict() if self.topology else {},
            "canonical_snapshot_hash": self.canonical_snapshot_hash,
            "canonical_snapshot_bytes": self.canonical_snapshot_bytes,
        }


def build_privacy_profile(snapshot: GraphSnapshot) -> PrivacyProfile:
    """Summarize observed privacy-sensitive snapshot fields."""
    full_email_count = 0
    hash_count = 0
    absolute_ref_count = 0
    for node in snapshot.nodes:
        full_email_count += int("author_email" in node.metadata)
        full_email_count += int("committer_email" in node.metadata)
        hash_count += int("author_email_hash" in node.metadata)
        hash_count += int("committer_email_hash" in node.metadata)
        absolute_ref_count += int(_is_absolute_ref(node.source_ref.path))
    for edge in snapshot.edges:
        absolute_ref_count += int(_is_absolute_ref(edge.source_ref.path))
    identity_mode = str(snapshot.stats.get("git_identity_mode", "") or "")
    return PrivacyProfile(
        full_git_email_count=full_email_count,
        hashed_git_email_count=hash_count,
        absolute_path_ref_count=absolute_ref_count,
        git_identity_mode=identity_mode,
        export_safe=full_email_count == 0 and absolute_ref_count == 0,
        diagnostics={
            "full_git_email_present": full_email_count > 0,
            "absolute_source_refs_present": absolute_ref_count > 0,
        },
    )


def build_certification_pack(
    snapshot: GraphSnapshot,
    *,
    top_n: int = 10,
) -> CertificationPack:
    """Build a deterministic certification pack for package consumers."""
    payload = stable_dumps(snapshot).encode("utf-8")
    return CertificationPack(
        namespace=snapshot.namespace,
        node_count=len(snapshot.nodes),
        edge_count=len(snapshot.edges),
        omitted_count=len(snapshot.omitted),
        parser_set=tuple(str(item) for item in snapshot.stats.get("parser_set", ())),
        node_kinds=dict(Counter(node.kind for node in snapshot.nodes)),
        edge_kinds=dict(Counter(edge.kind for edge in snapshot.edges)),
        omitted_reasons=dict(Counter(item.reason for item in snapshot.omitted)),
        cross_repo_resolution=_cross_repo_resolution(snapshot),
        privacy=build_privacy_profile(snapshot),
        topology=build_topology_summary(snapshot, top_n=top_n),
        canonical_snapshot_hash=hashlib.sha256(payload).hexdigest(),
        canonical_snapshot_bytes=len(payload),
    )


def render_markdown_certification_pack(pack: CertificationPack) -> str:
    """Render a compact public certification report."""
    lines = [
        "# PragmaGraph Certification Pack",
        "",
        f"- Namespace: `{pack.namespace}`",
        f"- Nodes: `{pack.node_count}`",
        f"- Edges: `{pack.edge_count}`",
        f"- Omitted diagnostics: `{pack.omitted_count}`",
        f"- Canonical snapshot hash: `{pack.canonical_snapshot_hash}`",
        f"- Canonical snapshot bytes: `{pack.canonical_snapshot_bytes}`",
        f"- Export safe: `{str(pack.privacy.export_safe).lower()}`",
        "",
        "## Parser Coverage",
        "",
    ]
    if pack.parser_set:
        lines.extend(f"- `{item}`" for item in pack.parser_set)
    else:
        lines.append("- none recorded")
    lines.extend(
        [
            "",
            "## Observed Node Kinds",
            "",
            *_count_lines(pack.node_kinds),
            "",
            "## Observed Edge Kinds",
            "",
            *_count_lines(pack.edge_kinds),
            "",
            "## Omitted Reasons",
            "",
            *_count_lines(pack.omitted_reasons),
            "",
            "## Privacy",
            "",
            f"- Git identity mode: `{pack.privacy.git_identity_mode or 'unknown'}`",
            f"- Full git email fields: `{pack.privacy.full_git_email_count}`",
            f"- Hashed git email fields: `{pack.privacy.hashed_git_email_count}`",
            f"- Absolute source refs: `{pack.privacy.absolute_path_ref_count}`",
            "",
            "## Cross-Repository Resolution",
            "",
        ]
    )
    if pack.cross_repo_resolution:
        outcome_counts = pack.cross_repo_resolution.get("outcome_counts", {})
        if isinstance(outcome_counts, Mapping):
            lines.extend(_count_lines(outcome_counts))
        else:
            lines.append("- recorded")
    else:
        lines.append("- none recorded")
    lines.append("")
    return "\n".join(lines)


def _cross_repo_resolution(snapshot: GraphSnapshot) -> Mapping[str, Any]:
    value = snapshot.stats.get("cross_repo_resolution", {})
    return value if isinstance(value, Mapping) else {}


def _count_lines(counts: Mapping[str, Any]) -> list[str]:
    if not counts:
        return ["- none"]
    return [
        f"- `{key}`: `{value}`"
        for key, value in sorted(counts.items(), key=lambda item: str(item[0]))
    ]


def _is_absolute_ref(path: str) -> bool:
    if not path:
        return False
    return path.startswith("/") or PurePosixPath(path).is_absolute()


__all__ = [
    "CertificationPack",
    "PrivacyProfile",
    "build_certification_pack",
    "build_privacy_profile",
    "render_markdown_certification_pack",
]
