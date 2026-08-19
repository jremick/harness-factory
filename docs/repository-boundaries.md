# Repository boundaries

Harness Factory and HDP Reference have different change authorities even though
they share the verified v0.1 implementation history.

## Harness Factory

[`jremick/harness-factory`](https://github.com/jremick/harness-factory) is the
active implementation and integration repository. It owns product development,
compiler and adapter evolution, runtime integrations, operational tooling, and
the work needed to turn the reference implementation into a maintained factory.

## HDP Reference

[`jremick/hdp-reference`](https://github.com/jremick/hdp-reference) is the
versioned reference line. It owns the normative working specification,
canonical schema, examples, semantic rules, conformance fixtures, reconstruction
contract, and evidence required to reproduce a declared HDP version.

## Synchronisation rule

The repositories start from the same verified v0.1 commit. Product changes do
not flow into HDP Reference automatically. A reference update must identify the
target HDP version, include compatibility and migration decisions, update the
contract artefacts together, and reproduce the applicable verification evidence.

HDP Reference changes may be imported into Harness Factory deliberately. The
import must preserve the reference commit or release identifier so generated
artefacts and evidence can name the exact contract they implement.
