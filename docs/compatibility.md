# Compatibility

| Surface | Supported in `0.2.0a1` |
| --- | --- |
| Python | 3.12 |
| HDP definition | Draft `0.1.0`, schema `urn:hdp:schema:0.1.0` |
| HIR | `0.1.x` |
| Codex target binding | `0.1.x` |
| Codex adapter | `0.1.x` |
| Release manifest/evidence | `0.1.x` |
| Host platforms in CI | Ubuntu and macOS |
| Complete target adapters | Codex only |

Unknown major versions fail closed. Target-specific values remain in binding
documents and adapters, not the canonical HDP/HIR meaning. Provider formats and
model aliases are moving external surfaces; compatibility claims apply to the
checked-in fixtures and recorded tool versions, not every future Codex release.

The canonical schema and the analyser skill copy are pinned byte-for-byte to
SHA-256 `4cb4a85dcdfe6b176be5760a1f109c720a66ea80a6179f94928e3683f1566e96`.
The Factory validation suite includes all three examples currently published by
the separate HDP Reference repository. Adapter support is narrower than schema
support: `0.2.0a1` compiles only the target-neutral `software-development`
profile through the Codex binding.

The `hdp` executable is retained for v0.1 command compatibility. The
distribution name changed from `hdp-reference` to `harness-factory` and the
simplified product entry point is `harness`; this alpha does not promise import-
level compatibility for third-party Python callers.
