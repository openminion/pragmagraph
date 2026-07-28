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
        "supported_clients": list(clients),
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
        "next_steps": [
            "replace placeholder paths when present",
            "install pragmagraph in the same Python environment used by the client",
            "paste the matching stdio config into the MCP client settings",
        ],
    }


def build_mcp_config_smoke_payload(
    *,
    snapshot: str = "",
    root: str = "",
    namespace: str = "default",
) -> dict[str, object]:
    """Validate the generated MCP setup payload without starting a client."""
    payload = build_mcp_doctor_payload(
        snapshot=snapshot,
        root=root,
        namespace=namespace,
    )
    diagnostics: list[str] = []
    command = payload.get("command")
    if not isinstance(command, list) or command[:2] != [
        "pragmagraph-server",
        "serve-stdio",
    ]:
        diagnostics.append("command_does_not_start_stdio_server")
    clients = payload.get("clients")
    if not isinstance(clients, list) or not clients:
        diagnostics.append("no_client_configs")
    else:
        for client in clients:
            if not isinstance(client, dict):
                diagnostics.append("client_config_not_object")
                continue
            config = client.get("config")
            if not _config_uses_stdio_command(config):
                diagnostics.append(f"{client.get('client', 'unknown')}_missing_command")
    return {
        "schema_version": "pragmagraph.mcp_config_smoke.v1alpha1",
        "ok": not diagnostics,
        "diagnostics": diagnostics,
        "source": "snapshot" if snapshot else "root" if root else "placeholder",
        "supported_clients": payload["supported_clients"],
        "command": payload["command"],
        "next_steps": payload["next_steps"],
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


def _config_uses_stdio_command(config: object) -> bool:
    if not isinstance(config, dict):
        return False
    servers = config.get("mcpServers")
    if not isinstance(servers, dict):
        return False
    pragmagraph = servers.get("pragmagraph")
    return (
        isinstance(pragmagraph, dict)
        and pragmagraph.get("command") == "pragmagraph-server"
        and isinstance(pragmagraph.get("args"), list)
        and pragmagraph.get("args", [])[:1] == ["serve-stdio"]
    )


__all__ = [
    "McpClientConfig",
    "build_mcp_client_config",
    "build_mcp_config_smoke_payload",
    "build_mcp_doctor_payload",
]
