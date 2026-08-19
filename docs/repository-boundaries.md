# Repository boundaries

Harness Factory and HDP Reference have different change authorities and
independent Git histories.

## Harness Factory

[`jremick/harness-factory`](https://github.com/jremick/harness-factory) is the
active implementation and integration repository. It owns product development,
compiler and adapter evolution, runtime integrations, operational tooling, and
the work needed to turn the reference implementation into a maintained factory.

## HDP Reference

[`jremick/hdp-reference`](https://github.com/jremick/hdp-reference) is the
provider-neutral draft standard. It owns the normative specification, canonical
schema, ontology, semantic rules, profiles, examples, conformance fixtures, and
portable authoring and reconstruction skills for a declared HDP version. It
does not own this factory's runtime, adapters, evaluation corpus, or release
evidence.

## Synchronisation rule

Product changes do not flow into HDP Reference automatically. A proposed
standard change must identify the target HDP version, include compatibility and
migration decisions, update the contract artefacts together, and pass the
reference repository's conformance checks.

HDP Reference changes may be imported into Harness Factory deliberately. The
import must preserve the reference commit, tag, or release identifier, document
the implemented profile and any extensions, and reproduce the factory evidence
needed for its implementation claims. Git ancestry is not a compatibility
signal.

The factory retains the original experimental v0.1 implementation history and
evidence. That history is supporting implementation evidence, not the normative
history of the HDP standard.
