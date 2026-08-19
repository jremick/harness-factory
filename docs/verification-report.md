# Harness Definition Package 0.1 verification report

Status: working vertical slice; not release-eligible
Date: 2026-08-12  
Canonical definition: `urn:hdp:example:ai-sdlc`, version `1.0.0`

## Executive result

This repository contains a tested Harness Definition Package (HDP), a
target-neutral Harness Intermediate Representation (HIR), a fail-closed Codex
compiler/adapter, an independently controlled evaluator, deterministic release
packaging, and a portable `analyse-existing-harness` Agent Skill.

The software-development example was compiled into the same strict generated
harness three times with byte-identical output. Two independent
`gpt-5.6-sol`/`xhigh` agents then used that exact harness to implement the
release-notes fixture. Both agent changes passed twelve external acceptance and
process checks. The evaluator executed candidate code only inside a macOS
`sandbox-exec` default-deny child and demonstrated denial of private-evaluator
read/write, parent read, workspace write, network connection, and process fork.

The generated-harness reconstruction passes: all 620 visible fields were
assessed, the visible public projection is exact, and all seven deliberately
redacted evaluator fields remain explicit unknowns. The foreign-harness blind
test also produced a structurally and semantically valid HDP with 100% field
coverage and no invented business outcome, but its strict fidelity score is
`0.788678` with four false assertions. That is an improvement over the earlier
`0.694036` run, but it remains below the release rubric. The skill instructions
were tightened afterward; a clean post-fix foreign rerun was invalidated because
parallel-agent filesystem snapshot replay altered shared source. This failure is
preserved rather than hidden.

Accordingly, the HDP/compiler/evaluator vertical slice is working and the ten
requested completion demonstrations are represented, but the package is
intentionally **not release-eligible** until the revised analysis skill passes a
fresh blind foreign-harness fidelity gate and the direct Codex CLI host is
healthy enough to repeat the broader four-task corpus.

The machine-readable result is
[`evidence/final-verification-summary.json`](../evidence/final-verification-summary.json).

## What was built

- A normative HDP working specification defining AI harness, HDP, model,
  harness, runtime, environment, task, evaluator, evidence, generation,
  verification, validation, conformance, fitness for outcome, and operational
  assurance: [`specification.md`](specification.md).
- A complete information architecture, ontology, semantic-rule catalogue, and
  decision record under [`workstreams/schema-design`](../workstreams/schema-design/).
- A canonical Draft 2020-12
  [`hdp.schema.json`](../src/hdp/schemas/hdp.schema.json), safe bounded YAML/JSON
  loader, structural validator, and deterministic semantic validator.
- Human-friendly minimal and full YAML examples plus negative mutation
  fixtures under [`examples`](../examples/).
- A target-neutral HIR, target binding, Codex adapter, deterministic generator,
  source map, trace graph, runtime policy, evidence recorder, regeneration
  protection, conformance checker, analyser, semantic diff, package builder,
  and release verifier in [`src/hdp`](../src/hdp/).
- A generated Codex harness containing `AGENTS.md`, an Agent Skill, project
  configuration, roles, state, policies, evidence templates, HIR, public source
  projection, manifest, and HarnessCard:
  [`build/final-generated-harness-v3`](../build/final-generated-harness-v3/).
- An evaluator held outside the model/harness workspace, with hidden contract
  custody and a JSON-only candidate protocol:
  [`evaluator/release_notes`](../evaluator/release_notes/).
- A portable evidence-aware analysis skill:
  [`analyse-existing-harness`](../skills/analyse-existing-harness/SKILL.md).
- Reproduction instructions, a consolidated verification script, retained
  evidence, wheel, and source distribution.

## Architecture and rationale

HDP v0.1 uses one deterministic resolved YAML/JSON object inside a modular
package. The resolved object is the validation and generation authority;
purpose, operations, governance, evaluation, schemas, profiles, evaluator
assets, evidence, and decisions may be governed independently around it. This
avoids undocumented include/overlay precedence while retaining a migration path
to modular authoring.

The factory separates responsibilities:

```text
HDP + target binding -> validation -> target-neutral HIR -> Codex adapter
                     -> generated harness -> agent/runtime

external evaluator package -----------------------------> acceptance evidence

existing harness -> evidence inventory -> reconstructed HDP + uncertainty
```

The evaluator is not a harness role. Hidden fixtures, expected answers and
evaluator implementation references are absent from the generated public
projection. The generator retains only opaque identifiers, custody metadata and
commitments. A public reconstruction therefore remains valid as an
evidence-qualified partial projection and cannot be regenerated as a full
harness without human/evaluator authority.

Models may synthesize only bounded prose. Deterministic code owns schema and
semantic validity, permission checks, trace coverage, artifact derivation,
hashes, acceptance results and release eligibility. MCP bindings fail closed in
v0.1 rather than widening undeclared authority. `harnessctl.py` is explicitly a
recorder/precheck; operating-system isolation belongs to the outer runtime.

## Standards position

HDP is an original integration layer. It does not claim formal conformance to
the sources below.

| Source and verified version | Classification | Adopted use | Gap retained by HDP |
| --- | --- | --- | --- |
| JSON Schema Draft 2020-12 | Mature open specification | Canonical structural contract | Cross-field meaning, runtime and outcome fitness |
| ISO/IEC/IEEE 29148:2018 | Formal standard | Requirement quality and traceability concepts | AI runtime and evaluator custody |
| OMG SACM 2.3 | Formal standard | Claim/evidence/argument concepts | Executable harness generation |
| NIST AI RMF 1.0 and AI 600-1 | Government framework/guidance | Risk and TEVV framing | Portable executable information contract |
| Oracle Agent Spec language 26.1.0 / PyAgentSpec 26.1.2 | Emerging specification/SDK | Optional future agent/flow adapter | Purpose, permissions and independent assurance |
| Oracle create-agent-spec skill | Implementation guidance | Authoring/round-trip lessons | Not a normative language contract |
| Agent Spec Eval and Tracing 26.1.2 | Emerging libraries | Dataset, metric, trace vocabulary mapping | Evaluator independence and evidence authority |
| MCP 2026-07-28 | Emerging protocol | Tool/context binding boundary | Authorization and outcome validation |
| A2A 1.0 | Emerging protocol | Future external-agent interface | Internal harness governance |
| OpenAPI 3.2.0 | Stable industry specification | HTTP contracts by URI/digest | Harness semantics and outcome proof |
| OASF 1.1.0 | Emerging schema framework | Optional discovery export | Verified capability and assurance state |
| Agent Skills living specification | Emerging portable format | Analysis-skill packaging | Enforcement and certification |
| Natural-Language Agent Harnesses and harness-engineering research | Research frameworks | Roles, stages, state, adapters and failure hypotheses | Normative interoperable contract |

Primary-source URLs, dates, coverage and omissions are retained in
[`standards-research.md`](../workstreams/standards/standards-research.md) and
[`sources.json`](../workstreams/standards/sources.json).

## Exact test environment

| Component | Version |
| --- | --- |
| macOS | 26.5.2, build 25F84, arm64 |
| Python used by project | 3.12.13 |
| uv | 0.11.25 |
| Codex CLI reality check | 0.147.0 |
| hdp-reference | 0.1.0 |
| jsonschema | 4.25.1 |
| Pydantic | 2.13.4 |
| PyYAML | 6.0.3 |
| Typer | 0.27.1 |
| pytest | 9.1.1 |
| Hypothesis | 6.165.3 |
| Agent executions | requested `gpt-5.6-sol`, `xhigh` |

The collaboration runtime records the requested sub-agent model and reasoning
but exposes no provider-side model readback or JSONL transcript. Invocation
records state that limitation explicitly.

## Authoritative validation commands and results

Run from the repository root:

```bash
uv sync --frozen --python 3.12
uv run hdp validate examples/minimal/hdp.yaml --json
uv run hdp validate examples/software-development/hdp.yaml --json
uv run pytest -q
uv run python -m unittest discover -s workstreams/software-e2e/tests -v
uv run python -m unittest discover -s workstreams/analysis-skill/tests -v
uv run python /Users/jarel/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/analyse-existing-harness
sh scripts/verify-all.sh
uv run --python 3.12 python tools/run_local_verification.py --output evidence/local-verification-sealed
uv build --wheel --sdist --out-dir dist
uv run pytest -q tests/test_distribution.py
uv run --isolated --python 3.12 \
  --with ./dist/hdp_reference-0.1.0-py3-none-any.whl hdp --help
```

Results:

- Main suite: `102 passed, 3 subtests passed`.
- Software E2E prototype suite: `14 passed`.
- Analysis fidelity scorer suite: `8 passed`.
- Skill structural validation: pass.
- Consolidated deterministic script: pass.
- Final local verification: all nine gates pass, including release tamper
  detection at the expected exit code `2`.
- Distribution leakage test: pass; wheel and sdist each contain 24 public
  package files and zero evaluator/evidence/gold/canary paths.
- Isolated wheel smoke test: pass; all eight public CLI commands are present.

Exact commands, exit codes and log digests are in
[`local-verification-sealed/verification.json`](../evidence/local-verification-sealed/verification.json).

## Generation, determinism and negative tests

The full HDP validates with source digest
`2d990078d5a3d38b897bfd5d2ea41b942f905200297e3472180030b845abcf4f`.
Its binding digest is
`a0d3f2fd6fe3ef29e547083ea6f42b36bc02f9eaaeebb036ea48b9748c5f8f0d`.
Compilation produces HIR digest
`0d361d54e169d85b87a72db3765620201d56b5f4719a1a6555b9048d2ee26e56`
and managed harness manifest digest
`987a6ade9cc9da66d100b1c4656ab7441a62467cfc1bba1f861090dbdefb0c40`.

Three clean compilations were byte-identical. Static conformance verified exact
configuration, trusted full-HIR subject, public-HIR projection, source map,
manifest, generated artifact digests, required outer enforcement, supported
budgets and secret-pattern absence. The public projection contains neither
hidden fixture/test prose nor evaluator implementation references.

Negative tests cover missing mandatory fields, unresolved references,
MUST-without-verification, wrong trace edge types, controlled-profile gaps,
unknown required extensions, permission contradictions, hidden fixture leaks,
MCP authority expansion, command-binding widening, hard-budget enforcement,
symlink/path escapes, stale/manual files, source/HIR/binding mismatches,
fabricated conformance, failed/missing/duplicate gates, manifest/predicate/mode
tampering, invalid analyser assessments and distribution leakage.

The verified release package is intentionally ineligible without a complete
content-addressed verification bundle. Its payload digest is
`f4093da7cba4ca269bc70b629e53c6810ab8c6098c2cbf07527b11b8fdf8ee16`.
`verify-release` passes for the original and fails for a modified HarnessCard.

## Independent software-development execution

Both final runs began from the same Git baseline and exact strict harness
manifest. The harness described the desired coding process and controls; it did
not encode the release-notes implementation.

| Run | Agent result | Recorded verification | Independent evaluator |
| --- | --- | --- | --- |
| `final-strict-agent-1` | Implemented task; no test/control edit | 2 public tests pass; ledger `0aef0b…24e6` | 12/12 pass |
| `final-strict-agent-2` | Independent implementation; supplemental contract checks | 2 public tests plus supplemental checks pass; ledger `7cbc80…3da6` | 12/12 pass |

The evaluator independently recomputed ledger and log digests, verified the
generated manifest against the Git baseline, bound the report to HEAD/status/
diff/tree digests, detected no canary leakage, and confirmed that the evaluator
and workspace were unchanged during evaluation. Its external sandbox probes
passed for workspace read and denied private read/write, parent read, workspace
write, network and fork.

Evidence:

- [`agent 1 evaluation report`](../evidence/runs/final-strict-agent-1/external-evaluation/evaluation-report.json)
- [`agent 1 diff`](../evidence/runs/final-strict-agent-1/workspace.diff)
- [`agent 2 evaluation report`](../evidence/runs/final-strict-agent-2/external-evaluation/evaluation-report.json)
- [`agent 2 diff`](../evidence/runs/final-strict-agent-2/workspace.diff)

The agent execution itself was governed procedurally by its workspace boundary;
the report does not claim an independently observed OS sandbox around the
collaboration agent. OS-enforced isolation is demonstrated for candidate
execution inside the external evaluator.

## Analysis skill verification

### Generated strict harness

The final frozen skill reconstructed the generated redacted harness as an exact
visible public projection:

- validator: pass;
- visible-projection equality: exact;
- 620 assessed fields: 613 declared, seven unknown, zero observed;
- hidden fixture/test values invented: zero;
- `generationReady: false`, correctly preventing full regeneration.

See the
[`reconstruction report`](../evidence/final-skill-roundtrip-strict-v3/reconstruction-report.json),
[`HDP`](../evidence/final-skill-roundtrip-strict-v3/hdp.reconstructed.yaml), and
[`evidence map`](../evidence/final-skill-roundtrip-strict-v3/evidence-map.json).

### Foreign Agent Spec-style harness

The clean blind foreign test produced a structurally/semantically valid HDP
with 807/807 fields assessed, 100% coverage, no runtime claims and no invented
business KPI. It retained contradictions/omissions and correctly blocked
generation. The independent scorer returned:

- content `0.876404`;
- evidence contract `0.993950`;
- confidence calibration `1.0`;
- coverage `1.0`;
- overall `0.788678`, strict status `fail`;
- four false assertions, two marked critical by the rubric.

Three failures were lossless-copy differences; the material failure substituted
`decomposedInto` for a declared `verifiedBy` trace relation. The final skill now
requires exact declared strings and exact `(source, relation, target)` tuples.
Because post-fix blind reruns suffered shared-source snapshot replay, they were
interrupted and moved under `evidence/invalidated`; they are not counted.

See the
[`foreign HDP`](../evidence/final-skill-foreign-current/hdp.reconstructed.yaml),
[`fidelity score`](../evidence/final-skill-foreign-current/fidelity-score.json),
and [`review summary`](../evidence/final-skill-foreign-current/review-summary.md).

## Defects found and corrected

Adversarial review found and the implementation corrected:

- evaluator-private files in the source distribution;
- candidate code imported in-process with evaluator authority;
- agent-writable evidence trusted without direct recomputation;
- hidden expected values and evaluator references copied into generated output;
- release eligibility accepted from arbitrary JSON or mutable manifest flags;
- packaging a harness from definition A while attesting definition B;
- static conformance accepting modified target configuration/HIR;
- path-dependent HIR digests;
- semantic diff omitting material permissions;
- command/MCP bindings widening authority;
- declared hard budgets without outer enforcement;
- stale generated files and regeneration symlink escapes;
- analyser symlink-based local file disclosure;
- exact-mode and attestation-predicate tampering gaps;
- missing MUST verification/trace/profile/extension semantic checks;
- YAML aliases, merge keys, non-string keys and input bounds;
- reconstruction validator accepting unresolved references or forged values;
- stale/incomplete distributions and inaccurate reproduction commands.

Failed experiments were retained. Two early clean Codex executions failed when
the tool host returned `timed out negotiating with the code-mode host`. The
latest preserved direct CLI run has Codex exit `0`, evaluator exit `1`, no
workspace change, eight JSONL events and the exact host errors. It is failure
evidence only:
[`final-current-reference-feature`](../evidence/final-current-reference-feature/).

Several analysis reruns and one broader direct runner were invalidated when
parallel-agent filesystem snapshots replayed an older unsafe generator/test
state. They are under [`evidence/invalidated`](../evidence/invalidated/) and do
not support success claims. The strict source was restored from a content-
addressed wheel, locked, and reverified afterward.

## Completion-gate assessment

| Gate | Result | Evidence |
| --- | --- | --- |
| Full example validates | Pass | schema/semantic command and tests |
| Invalid HDPs fail semantically | Pass | negative fixtures and tests |
| Generator creates usable harness | Pass | strict harness + manifest |
| Agent executes generated harness | Pass | two workspace runs |
| Agent completes fixture task | Pass | two independent diffs |
| External acceptance passes | Pass | 12/12 twice |
| Process/permission/evidence controls verified | Pass with stated execution-boundary qualification | ledger/log checks and evaluator sandbox probes |
| Analysis skill creates valid HDP | Pass | redacted generated + foreign validator passes |
| Reconstruction accuracy measured | Pass; foreign strict release gate fails | exact redacted result and fidelity score |
| Reproducible by another agent | Pass for deterministic and documented example path | reproduction guide and retained commands |

## Remaining limitations

- The revised skill still needs a new uncontaminated blind foreign-harness run;
  the prior run is below its strict release threshold.
- The direct Codex CLI code-mode host was unhealthy. The collaboration-agent
  successes have explicit requested model/reasoning but no provider-side model
  observation or JSONL transcript.
- The final example proves one realistic small Python task twice. Older runs
  cover feature/fix/refactor/policy-block, but those predate the final strict
  public projection and are supporting history, not the final subject.
- macOS `sandbox-exec` is not portable. Other platforms need an equivalent
  independently verified container/OS profile.
- Digest-only statements prove internal consistency, not builder identity,
  signature authenticity, SLSA level, certification or non-repudiation.
- The Codex adapter is implemented; Agent Spec, OASF, SACM, A2A and OpenAPI are
  mappings/future adapters, not emitted executable profiles in v0.1.
- Model/provider aliases can change; requested identity is not observed identity.
- Full modular overlay semantics, formal unknown values, SACM export and LLM-
  judge policy remain open design questions.

## Recommendations for HDP 0.2

1. Make the public/private evaluator package split a first-class schema and
   compilation input rather than a projection rule inside one document.
2. Add a portable isolation capability contract with macOS, Linux container and
   remote-runner implementations plus identical adversarial probes.
3. Rerun the revised analysis skill blind against several foreign harness
   families and require zero critical false assertions before release.
4. Add an optional PyAgentSpec adapter pinned separately to SDK and language
   versions, with explicit loss reporting for permissions and assurance data.
5. Define signed release statements and an externally pinned trust root.
6. Generate a machine-readable field-family coverage matrix joining schema,
   semantic rule, HIR, adapter, test and evidence.
7. Define deterministic module-resolution and overlay provenance rules.
8. Add observed provider/runtime identity and resource-usage receipts where the
   execution platform exposes them.

## Reproduction

Follow [`reproduction.md`](reproduction.md) or run `sh scripts/verify-all.sh`.
The consolidated script creates a new temporary harness/analysis/distribution,
retains its location, and exits non-zero on any deterministic gate failure.
