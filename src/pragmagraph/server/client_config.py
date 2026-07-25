"""MCP client configuration snippets for pragmagraph-server."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class McpClientConfig:
    """One generated client configuration snippet."""

    client: str
    command: str
    args: tuple[str, ...]
    config: dict[str, object]
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["args"] = list(self.args)
        payload["notes"] = list(self.notes)
        return payload


def build_mcp_client_config(
    client: str,
    *,
    snapshot: str = "",
    root: str = "",
    namespace: str = "default",
) -> McpClientConfig:
    """Build a portable MCP client snippet for one supported client family."""
    args = _server_args(snapshot=snapshot, root=root, namespace=namespace)
    if client == "claude_desktop":
        return McpClientConfig(
            client=client,
            command="pragmagraph-server",
            args=args,
            config={
                "mcpServers": {
                    "pragmagraph": {
                        "command": "pragmagraph-server",
                        "args": list(args),
                    }
                }
            },
            notes=("replace placeholder paths before use",),
        )
    if client == "cursor":
        return McpClientConfig(
            client=client,
            command="pragmagraph-server",
            args=args,
            config={
                "mcpServers": {
                    "pragmagraph": {
                        "command": "pragmagraph-server",
                        "args": list(args),
                    }
                }
            },
            notes=("paste into an MCP config surface that supports stdio servers",),
        )
    raise ValueError(f"unsupported MCP client {client!r}")


def build_mcp_doctor_payload(
    *,
    snapshot: str = "",
    root: str = "",
    namespace: str = "default",
) -> dict[str, object]:
    """Return user-facing MCP setup facts and generated client snippets."""
    clients = ("claude_desktop", "cursor")
    return {
        "schema_version": "pragmagraph.mcp_client_setup.v1alpha1",
        "server": "pragmagraph-server",
        "transport": "stdio",
        "boundary": "observed_facts_only",
        "command": [
            "pragmagraph-server",
            *_server_args(
                snapshot=snapshot,
                root=root,
                namespace=namespace,
            ),
        ],
        "clients": [
            build_mcp_client_config(
                client,
                snapshot=snapshot,
                root=root,
                namespace=namespace,
            ).to_dict()
            for client in clients
        ],
        "resources": [
            "pragma://status",
            "pragma://snapshot",
            "pragma://report",
            "pragma://precise-ingestion",
            "pragma://node/{node_id}",
        ],
    }


def _server_args(
    *,
    snapshot: str,
    root: str,
    namespace: str,
) -> tuple[str, ...]:
    if snapshot:
        return ("serve-stdio", "--snapshot", snapshot)
    if root:
        return ("serve-stdio", "--root", root, "--namespace", namespace)
    return ("serve-stdio", "--snapshot", "<snapshot.json>")


__all__ = ["McpClientConfig", "build_mcp_client_config", "build_mcp_doctor_payload"]
