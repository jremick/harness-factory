# Change and monitoring policy

Incident Scribe uses semantic versioning. Removing an input, output, prohibited
action, hard evaluation gate, or evaluator boundary is a breaking change.

Changes require review by Reliability Enablement and an incident commander.
Permission expansion and hard-gate reduction require both reviewers and fail
closed if either is unavailable. Deprecations must identify the superseding
version and remain documented for 90 days.

At run start, record the agent-spec version, tool-policy version, prompt digest,
resolved model revision, container image digest, and evaluation-plan version.
Retain redacted traces and intervention events for 30 days; retain aggregate
measure results for 180 days. Use the incident identifier as the correlation ID
and redact credentials, raw payloads, and customer message bodies.

Re-evaluate when the agent spec, prompt, tool policy, model revision, runtime
image, runbook schema, or evaluation plan changes. Suspend operation on any
prohibited-action attempt or evaluator-boundary violation. Alert Reliability
Enablement and the incident commander when a hard measure misses its threshold.

The baseline is Incident Scribe 2.3.0 with tool-policy 2026-08-01 and evaluation
plan 4.1.0. No production fitness, service-level objective, or business KPI is
declared by this policy.
