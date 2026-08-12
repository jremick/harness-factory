# Harness Factory research brief

As of: 2026-08-12  
Scope: primary specifications, official documentation, original papers, and
source repositories relevant to HDP/HIR, the Codex adapter, evaluation,
observability, governance, and provenance.

## Evidence classes

### Established standards and frameworks

- [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12) is the
  normative structural-validation dialect for HDP v0.1. Cross-field meaning,
  runtime behaviour, safety, and fitness remain separate deterministic gates.
- [in-toto Attestation v1.2](https://github.com/in-toto/attestation/blob/main/spec/README.md)
  and [SLSA v1.2](https://slsa.dev/spec/v1.2/) shape the provenance envelope.
  Prototype statements are explicitly unsigned and digest-only; they do not
  claim SLSA level achievement or signer authenticity.
- [OCI Image Specification v1.1.1](https://github.com/opencontainers/image-spec/releases)
  is a future transport option. The first prototype uses a deterministic local
  package and does not require an OCI registry.
- [NIST AI RMF 1.0](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10)
  and [NIST AI 600-1](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence)
  provide risk and TEVV framing.
- ISO/IEC [42001:2023](https://www.iso.org/standard/81230.html),
  [23894:2023](https://www.iso.org/standard/77304.html),
  [5338:2023](https://www.iso.org/standard/81118.html), and
  [42005:2025](https://www.iso.org/standard/42005?browse=tc) provide management,
  risk, lifecycle, and impact-assessment anchors. Public summaries do not
  support clause-level conformity or certification claims.

### Released but evolving protocols and conventions

- [MCP revision 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28)
  is a tool/context binding protocol, not an authorization or approval system.
  The Codex adapter records configured and observed protocol/client versions.
- [A2A v1.0](https://github.com/a2aproject/A2A/blob/main/docs/specification.md)
  is relevant to future remote-agent interoperability, not the canonical
  internal orchestration model.
- [OpenTelemetry GenAI semantic conventions](https://github.com/open-telemetry/semantic-conventions-genai)
  are marked Development. HIR events remain stable and are mapped to a pinned
  exporter vocabulary; volatile attribute names are not canonical semantics.
- The [OWASP Top 10 for Agentic Applications](https://genai.owasp.org/2025/12/09/owasp-genai-security-project-releases-top-10-risks-and-mitigations-for-agentic-ai-security/)
  is a threat catalog used to derive adversarial tests, not a certification.

### Current Codex target surface

- [Codex AGENTS.md guidance](https://developers.openai.com/codex/guides/agents-md)
  defines repository instruction discovery, root-to-leaf precedence, override
  behaviour, and a default aggregate size limit of 32 KiB. The adapter emits a
  compact root `AGENTS.md` that routes detail to generated artifacts.
- [Codex Skills documentation](https://developers.openai.com/codex/skills) and
  the open [Agent Skills specification](https://github.com/agentskills/agentskills/blob/main/docs/specification.mdx)
  govern `.agents/skills/<name>/SKILL.md`. `name` must match the directory and
  use 1–64 lowercase alphanumeric/hyphen characters; `description` is required.
  Experimental `allowed-tools` metadata is never treated as a security boundary.
- [Codex configuration](https://developers.openai.com/codex/config-reference)
  uses trusted-project `.codex/config.toml`. The adapter emits only documented
  project-scoped keys and rejects settings known to be machine-local or inert.
- [Codex MCP configuration](https://developers.openai.com/codex/mcp) uses
  `mcp_servers.<id>` bindings for STDIO or Streamable HTTP servers. Server
  instructions are untrusted input and require inventory/provenance.
- OpenAI's [Harness engineering](https://openai.com/index/harness-engineering/)
  is practitioner evidence for compact instruction maps, repository-local
  truth, mechanical checks, isolated workspaces, and visible logs/traces.

### Experimental harness research

- [Natural-Language Agent Harnesses / IHR](https://arxiv.org/abs/2603.25723)
  separates readable roles, stages, handoffs, artifacts, recovery, and stopping
  policy from deterministic tools, parsing, sandboxing, and logging. HDP adopts
  this hybrid pattern without treating the paper's terminology as a standard.
- [Meta-Harness](https://arxiv.org/abs/2603.28052) and its
  [reference repository](https://github.com/stanford-iris-lab/meta-harness)
  motivate candidate lineage, immutable evaluation splits, and comparison
  across changes. A synthesizer never decides release eligibility.
- [Agentic Harness Engineering](https://arxiv.org/abs/2604.25850) and its
  [source repository](https://github.com/china-qijizhifeng/agentic-harness-engineering)
  motivate component, experience, and decision observability plus explicit
  change hypotheses.
- [HarnessFix](https://arxiv.org/abs/2606.06324) and its
  [source repository](https://github.com/HarnessFix/HarnessFix) motivate a trace
  IR joining runtime steps, effects, data/control flow, and implementation
  anchors. Its missing raw benchmark traces limit independent reproduction.
- [AutoHarness](https://arxiv.org/abs/2603.03329) supports iteratively generating
  deterministic guards from environment feedback, but does not establish a
  general cross-target compiler contract.
- Comparable target-specific generators include
  [GitHub Agentic Workflows](https://github.com/github/gh-aw),
  [Google Cloud Agent Starter Pack](https://github.com/googlecloudplatform/agent-starter-pack),
  and the [OpenAI Symphony draft specification](https://github.com/openai/symphony/blob/main/SPEC.md).
  None supplies this prototype's evidence-aware reverse analysis and strict
  analyse-to-compile parity contract.

## Decisions supported by the evidence

1. HDP/HIR, evidence maps, synthesis records, parity, and release gates are
   explicitly versioned local contracts, not claimed external standards.
2. Hard validation, permissions, hashes, test outcomes, parity, and release
   eligibility are deterministic. Assisted synthesis is bounded, recorded, and
   non-authoritative.
3. Codex file paths, TOML keys, MCP bindings, and skill frontmatter exist only
   in target bindings and adapter outputs; canonical HIR stays target-neutral.
4. Every conformance result records the Codex version, requested and observed
   model/reasoning, sandbox/approval mode, enabled features, tools, and MCP
   revision when observable.
5. Behavioural held-out tasks and an external evaluator remain mandatory. A
   successful generator or agent exit code is insufficient evidence.

## Known uncertainty

Codex and MCP continue to evolve; Agent Skills does not define signing or
dependency provenance; OpenTelemetry GenAI remains Development; complete ISO
texts are not publicly available; and some research artifacts omit official
code or raw evaluation traces. These surfaces are version-pinned and their
claims limited accordingly.
