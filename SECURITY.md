# Security policy

## Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability. Use
[GitHub private vulnerability reporting](https://github.com/jremick/harness-factory/security/advisories/new)
with the affected version, impact, reproduction steps and any proposed fix.
Avoid including real secrets or third-party data.

Expect an acknowledgement within seven days. This is a maintainer target, not a
service-level agreement.

## Supported versions

Only the latest public alpha receives security fixes. Earlier snapshots and
unreleased branches are unsupported.

## Security boundary

Harness Factory validates and renders policy, but the generated command wrapper
is not an OS sandbox. The target runtime must enforce filesystem, process,
network, environment and resource boundaries. Release attestations are currently
unsigned, digest-only integrity records and do not authenticate a builder.
