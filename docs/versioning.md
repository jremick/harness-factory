# Versioning policy

The Harness Factory distribution and the HDP contract version independently.
Factory `0.2.0a1` supports the compatibility matrix in
[`compatibility.md`](compatibility.md); it is not HDP `0.2`.

The machine-readable CLI response contract is a third, independent surface.
The beta candidate emits `cliContractVersion: "0.1.0"` alongside the Factory
version and operation name. A response-shape change requires a CLI contract
version change even when HDP/HIR semantics remain unchanged.

HDP, HIR, target bindings, adapters, release manifests, evidence records, and
custom attestation predicates have independent semantic versions.

- Unknown major versions fail closed.
- A major version is required to remove or reinterpret a required field,
  invariant, permission, approval, evaluator boundary, evidence meaning, or
  adapter obligation.
- A minor version may add optional fields or entity variants only when readers
  can preserve them and adapters explicitly declare support.
- Patch versions may correct validation, rendering, diagnostics, or tests
  without changing accepted semantics.
- Extensions use namespaced `x-` keys. They cannot weaken core semantics.
- Target bindings declare the adapter version they require. Target-specific
  keys never enter canonical HIR meaning.
- Migrations must be explicit deterministic transformations with old/new
  digests and source maps; implicit upgrade-on-read is out of scope for v0.1.

The beta has one narrow legacy exception: it validates the exact generated
format emitted by Factory `0.2.0a1`, which omitted runtime binding and adapter
markers. The exception is byte- and manifest-bound and does not establish
compatibility with future alpha or beta formats.

Mutable provider/model aliases are recorded as requested runtime inputs. They do
not establish a fully reproducible model subject unless the provider exposes and
the run records an immutable resolved identity.
