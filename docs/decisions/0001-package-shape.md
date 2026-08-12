# ADR 0001: Canonical document inside a governed package

- Status: accepted for v0.1
- Date: 2026-08-12

## Context

HDP needs machine validation, model readability, independent governance, and a
safe evaluator boundary. Arbitrary include/overlay semantics would complicate
validation and could accidentally merge private evaluation data into model-visible
content.

## Decision

Version 0.1 uses one canonical YAML or JSON definition document validated by one
canonical Draft 2020-12 JSON Schema. The surrounding package holds schemas,
profiles, generated artefacts, examples, fixtures, evaluator code, evidence, and
decision records. Definition fields may reference governed artefacts by URI and
digest; they do not import or merge their contents.

## Consequences

The definition is portable and deterministic. Independent governance and access
control can be applied to sibling package areas. Very large definitions may be
verbose, and reusable overlays are deferred until their merge semantics can be
specified and tested.

## Revisit trigger

Add imports or overlays only after at least three real HDPs demonstrate repeated
content that cannot be managed safely through profiles, templates, or external
content-addressed references.

