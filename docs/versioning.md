# Versioning policy

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

Mutable provider/model aliases are recorded as requested runtime inputs. They do
not establish a fully reproducible model subject unless the provider exposes and
the run records an immutable resolved identity.
