# Alpha-to-beta compatibility fixtures

These fixtures freeze the narrow compatibility claim without introducing an
automatic migration command.

`alpha-root-json.json` describes the alpha's legacy root-level JSON layout and
pins the exact source-definition and binding SHA-256 digests. The test checks
those digests before copying the published software-development HDP and Codex
binding into that layout, then runs the supported build, dry-run install,
install and verify path in a temporary directory.

`alpha-generated.json` pins the compressed SHA-256 and selected artifact
digests for `alpha-generated.tar.gz.b64`, an immutable generated harness byte
bundle emitted by the released alpha. The compatibility test unpacks those
bytes without regenerating them, then consumes the same harness through live
install, strict audit, package and release verification. The beta accepts this
legacy format only when the complete manifest-owned artifact set matches the
alpha renderer; arbitrary older output is not accepted.

The `unsupported-*.json` files are intentionally small version probes. They
stop before generation, installation or release writes and assert the
actionable fail-closed diagnostics documented in `docs/compatibility.md`.
