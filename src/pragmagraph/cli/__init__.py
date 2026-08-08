"""CLI registration helpers for the PragmaGraph entrypoint."""

from pragmagraph.cli.commands import (
    add_git_identity_mode_argument,
    add_json_flag,
    register_core_commands,
)

__all__ = [
    "add_git_identity_mode_argument",
    "add_json_flag",
    "register_core_commands",
]
