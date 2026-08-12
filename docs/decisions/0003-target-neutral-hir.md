# ADR 0003: Explicit target-neutral HIR and typed relations

- Status: accepted
- Date: 2026-08-12

## Decision

Normalize resolved HDP documents into a versioned HIR with typed entities and
relations. Codex paths, TOML keys, skill layout, and MCP representation live in
the Codex binding/adapter only.

## Rejected alternatives

Direct template rendering from authoring YAML and a target-shaped nested model
were rejected because they prevent cross-target semantic checks and make reverse
analysis compare filenames rather than behaviour and authority.
