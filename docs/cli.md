# CLI reference

## Beta command contract

The supported product entry point is `harness`. The beta candidate freezes the
following seven-command surface:

| Command | Purpose | Important boundary |
| --- | --- | --- |
| `harness init [DIRECTORY]` | Create an empty package or the `codex-sdlc` starter | Starter facts must be reviewed |
| `harness build [PROJECT]` | Discover, validate, normalize and compile a project | Static result only |
| `harness install TARGET` | Install manifest-owned files | Use `--dry-run`; ownership, stale-file and concurrent-install conflicts fail closed |
| `harness audit HARNESS` | Analyse an existing harness | Invalid/partial output exits 2 unless `--allow-partial` is explicit; installed targets require exact ownership |
| `harness verify [PROJECT]` | Rebuild and run static conformance | Does not invoke Codex |
| `harness release [PROJECT]` | Package only with subject-bound verification evidence | Ineligible evidence exits non-zero |
| `harness doctor` | Report local prerequisites | Does not read credentials |

The beta option surface is also intentionally small:

| Command | Supported options |
| --- | --- |
| `init` | `--template empty|codex-sdlc`, `--json` |
| `build` | `--output`, `--force-generated`, `--json` |
| `install` | `--project`, `--harness`, `--dry-run`, `--json` |
| `audit` | `--output`, `--allow-partial`, `--json` |
| `verify` | `--json` |
| `release` | `--conformance`, `--output`, `--json` |
| `doctor` | `--json` |

Projects are convention-driven. The definition is discovered at
`harness/hdp.yaml` (or JSON), the Codex binding at
`harness/bindings/codex.yaml` (or JSON), generated output at `build/harness`,
the project analysis path is `build/analysis`, and release output is
`dist/harness-release`. When `harness audit` has no `--output`, it writes to
`<current-directory>/<harness-name>-analysis`. If that path would be inside the
audited harness, it writes the analysis beside the harness instead.

`build`, `install`, `audit`, `verify`, `release` and `doctor` accept `--json`
for machine-readable output. `init` also accepts `--json`; its established
alpha behavior is JSON by default, so the flag is an explicit, compatible way
to request the same output. There is no `--human` init mode in this contract.
`audit` keeps its established human-readable output by default and emits one
marked JSON object only with `--json`. Strict audit treats a root with installer
controls as an installed repository: it validates the ownership manifest and
all manifest-owned generated files, while excluding only the exact installer
control files from the generated digest. Running either `harness` or `hdp` with no
arguments prints help to stdout and exits 0; the help request is not an input
error.

Every JSON response is one object with the operation's existing fields plus
these additive markers:

```json
{
  "cliContractVersion": "0.1.0",
  "command": "build",
  "factoryVersion": "0.2.0a1",
  "status": "pass"
}
```

`cliContractVersion` versions the response shape independently from the Factory
distribution and HDP/HIR documents. `command` is the operation name, including
`generate` or `inspect` when a hidden compatibility alias is used. Human text
is never mixed into machine-readable stdout. Deterministic results may still
be emitted as JSON before a non-zero exit; invocation and input errors emit no
JSON and report an actionable diagnostic on stderr.

## Advanced compatibility interface

The `hdp` executable retains the reference implementation's lower-level
commands: `init`, `validate`, `compile`, `analyse`, `test`, `diff`, `package` and
`verify-release`. `generate` and `inspect` are hidden compatibility aliases.

The shared `hdp` names (`init`, `build`, `install`, `audit`, `verify`, `release`
and `doctor`) retain the product implementations. The lower-level commands
that return structured data emit JSON without an additional flag; `validate`
uses human diagnostics by default and emits the same marked JSON object with
`--json`. The alias output marker identifies the alias that was invoked while
the generated artifact and semantics remain those of `compile` or `analyse`.

Both `harness audit` and strict `hdp analyse` exit non-zero when the
reconstruction is invalid or partial. `--allow-partial` is an explicit
acknowledgement for inspection-only workflows. Run `COMMAND --help` for exact
arguments.

## Exit codes

- `0`: requested deterministic operation passed
- `1`: normalized HDP comparison found non-parity
- `2`: validation, conformance, conflict or eligibility failure
- `3`: malformed invocation or operational/input error

`verify-release` emits no JSON and exits 3 when the release root or its release
manifest is missing, unsafe, or not parseable JSON. A parsed release with
tampered or inconsistent contents emits its failure object and exits 2.

Unsupported document, binding, generated-manifest, installer-manifest,
transaction-journal or release-manifest versions fail closed. They do not get
upgraded on read; the diagnostic names the supported version and instructs the
caller to update the source explicitly before retrying. A pre-existing opaque
installer journal is a generic conflict in both dry-run and live mode: it is
reported with exit `2` and is never parsed for a more specific message.
