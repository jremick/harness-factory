# Limitations, backlog, and next adapter gate

## Current limitations

- The only complete adapter is Codex. MCP bindings are modelled but rejected by
  adapter v0.1 when exact canonical capability/policy/network semantics cannot
  be represented.
- The generated command wrapper cannot enforce a complete OS sandbox. Codex or
  another outer runtime must enforce filesystem, process, environment, network,
  and externally owned budgets.
- Live results cover four small Python tasks and one run per final subject.
  They do not estimate broad software-engineering success rates.
- Requested model and reasoning settings are recorded, but current Codex JSONL
  did not expose an immutable observed model identifier or monetary cost.
- Release statements are unsigned digest-only metadata. Authenticated builder
  identity, transparency logging, OCI publication, and a SLSA level are absent.
- Generic harness reconstruction is necessarily evidence-limited. Required
  unknowns make output non-generation-ready until a human resolves them.
- OpenTelemetry GenAI, MCP, A2A, Agent Skills, and Codex formats are moving
  conventions; adapters must pin and retest versions.

## Backlog

1. Add a portable outer sandbox runner with deterministic filesystem, process,
   environment, network, wall-time, output, and resource-exhaustion probes.
2. Add authenticated signing and verification for build and conformance
   statements, then optional deterministic OCI packaging.
3. Add repeated multi-seed behavioural runs and richer repositories without
   exposing evaluator-private cases.
4. Implement bounded synthesis provider interfaces and approval records; v0.1
   executes zero synthesis requests.
5. Add version negotiation and exact policy projection for MCP tools.
6. Add line-level generated source maps where templates materially combine
   multiple HDP elements.
7. Add conflict-heavy analyser fixtures and authorized runtime observation.

## Gate for a second adapter

Claude Code or another adapter may start only after the Codex vertical slice
remains green on a clean checkout and the candidate adapter has:

- an official-format research update;
- a target binding schema outside canonical semantics;
- a capability/permission/approval loss analysis;
- fail-closed handling for unsupported fields;
- golden and trigger tests;
- all four behavioural tasks under an independently enforced sandbox;
- analyse-to-recompile parity fixtures; and
- an ADR demonstrating that no target-specific field was added to HDP/HIR.
