# CLI reference

## Product workflow

| Command | Purpose | Important boundary |
| --- | --- | --- |
| `harness init` | Create an empty package or the `codex-sdlc` starter | Starter facts must be reviewed |
| `harness build` | Discover, validate, normalize and compile a project | Static result only |
| `harness install` | Install manifest-owned files | Use `--dry-run`; ownership, stale-file and concurrent-install conflicts fail closed |
| `harness audit` | Analyse an existing harness | Invalid/partial output exits 2 unless `--allow-partial` is explicit |
| `harness verify` | Rebuild and run static conformance | Does not invoke Codex |
| `harness release` | Package only with subject-bound verification evidence | Ineligible evidence exits non-zero |
| `harness doctor` | Report local prerequisites | Does not read credentials |

Projects are convention-driven. The definition is discovered at
`harness/hdp.yaml` (or JSON), the Codex binding at
`harness/bindings/codex.yaml` (or JSON), generated output at `build/harness`,
analysis at `build/analysis`, and release output at `dist/harness-release`.

All product commands that return structured data support `--json` where useful.

## Advanced compatibility interface

The `hdp` executable retains the reference implementation's lower-level
commands: `init`, `validate`, `compile`, `analyse`, `test`, `diff`, `package` and
`verify-release`. `generate` and `inspect` are hidden compatibility aliases.

Both `harness audit` and strict `hdp analyse` exit non-zero when the
reconstruction is invalid or partial. `--allow-partial` is an explicit
acknowledgement for inspection-only workflows. Run `COMMAND --help` for exact
arguments.

## Exit codes

- `0`: requested deterministic operation passed
- `1`: normalized HDP comparison found non-parity
- `2`: validation, conformance, conflict or eligibility failure
- `3`: malformed invocation or operational/input error
