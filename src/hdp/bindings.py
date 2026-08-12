"""Versioned target binding contracts kept outside canonical HIR semantics."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .diagnostics import HdpInputError
from .io import load_document


class BindingModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class McpServerBinding(BindingModel):
    id: str
    transport: Literal["stdio", "streamable_http"]
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    url: str | None = None
    required: bool = True
    enabled_tools: list[str] = Field(default_factory=list, alias="enabledTools")
    disabled_tools: list[str] = Field(default_factory=list, alias="disabledTools")
    startup_timeout_seconds: int = Field(10, ge=1, le=300, alias="startupTimeoutSeconds")
    tool_timeout_seconds: int = Field(60, ge=1, le=1800, alias="toolTimeoutSeconds")

    @field_validator("id")
    @classmethod
    def valid_id(cls, value: str) -> str:
        if not re.fullmatch(r"[a-z][a-z0-9_-]{0,62}", value):
            raise ValueError("MCP server id must be lowercase alphanumeric with '_' or '-'")
        return value

    def validate_transport(self) -> None:
        if self.transport == "stdio" and not self.command:
            raise ValueError(f"MCP server {self.id!r} requires command for stdio")
        if self.transport == "streamable_http" and not self.url:
            raise ValueError(f"MCP server {self.id!r} requires url for streamable_http")
        if self.command and self.url:
            raise ValueError(f"MCP server {self.id!r} cannot declare both command and url")


class CodexSettings(BindingModel):
    model: str
    reasoning_effort: Literal["low", "medium", "high", "xhigh"] = Field(alias="reasoningEffort")
    approval_policy: Literal["untrusted", "on-request", "never"] = Field(alias="approvalPolicy")
    sandbox_mode: Literal["read-only", "workspace-write", "danger-full-access"] = Field(alias="sandboxMode")


class CodexBinding(BindingModel):
    binding_version: Literal["0.1.0"] = Field(alias="bindingVersion")
    kind: Literal["TargetBinding"]
    target: Literal["codex"]
    adapter_version: Literal["0.1.0"] = Field(alias="adapterVersion")
    settings: CodexSettings
    externally_enforced_resources: list[
        Literal["environment", "filesystem", "network", "process", "wall-time"]
    ] = Field(default_factory=list, alias="externallyEnforcedResources")
    command_bindings: dict[str, list[str]] = Field(default_factory=dict, alias="commandBindings")
    mcp_servers: list[McpServerBinding] = Field(default_factory=list, alias="mcpServers")

    @field_validator("command_bindings")
    @classmethod
    def valid_command_bindings(cls, value: dict[str, list[str]]) -> dict[str, list[str]]:
        executable = re.compile(r"[A-Za-z0-9._+-]+")
        for capability_id, names in value.items():
            if not names:
                raise ValueError(f"command binding {capability_id!r} must name an executable")
            if len(names) != len(set(names)):
                raise ValueError(f"command binding {capability_id!r} contains duplicates")
            for name in names:
                if not executable.fullmatch(name):
                    raise ValueError(f"command binding executable must be a basename: {name!r}")
        return value

    @field_validator("mcp_servers")
    @classmethod
    def unique_servers(cls, value: list[McpServerBinding]) -> list[McpServerBinding]:
        identifiers = [item.id for item in value]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("MCP server ids must be unique")
        for server in value:
            server.validate_transport()
        if value:
            raise ValueError(
                "Codex adapter 0.1.0 cannot bind MCP servers exactly to canonical "
                "capabilities and therefore rejects MCP configuration"
            )
        return value

    @field_validator("externally_enforced_resources")
    @classmethod
    def unique_external_resources(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("externally enforced resource names must be unique")
        return value


def load_codex_binding(path: Path) -> CodexBinding:
    try:
        return CodexBinding.model_validate(load_document(path))
    except ValueError as exc:
        raise HdpInputError(f"invalid Codex target binding {path}: {exc}") from exc
