# Independent evaluator boundary

Checked-in evaluator packages are public reproducibility fixtures. Isolation
during execution protects evaluator-owned files from the candidate process, but
publication means their contents are not genuinely hidden from repository
readers. A held-out claim requires an untracked, separately controlled evaluator
whose commitment is recorded before the run. See
[ADR 0011](decisions/0011-public-evaluator-fixture-semantics.md).

## Trust model

The system under evaluation is the model plus generated harness plus fixture
runtime and visible task environment. The evaluator, its private fixtures, and
its acceptance implementation are outside that system.

## Enforced invariants

1. Generator inputs MUST contain only public evaluation contracts and metrics.
2. Generated output MUST NOT contain evaluator source, private fixtures, expected
   implementation text, or evaluator-only secrets.
3. The agent process MUST have a path allowlist limited to its disposable fixture
   worktree and generated harness.
4. Evaluator paths MUST be outside that allowlist and SHOULD be read-only to the
   agent OS process when the platform supports it.
5. The evaluator MUST run after the agent and MUST write to a distinct evidence
   directory.
6. Acceptance MUST be determined from independent tests plus required process and
   evidence assertions, not from generated-harness self-report.
7. Every boundary check MUST produce a command, exit status, timestamp, tool
   version, and content digest in the evidence ledger.

## Leakage checks

- Scan generated output and agent-visible fixture content for private canaries.
- Attempt prohibited reads and writes from the same command wrapper used by the
  agent.
- Hash evaluator-private files before and after execution.
- Compare evaluator-owned paths against the generator manifest.

## Residual limitation

Logical path isolation alone is weaker than an OS sandbox. The end-to-end runner
must record whether it used OS-level sandboxing or the fallback command wrapper,
and the verification report must not equate the fallback with strong isolation.
The 2026-08-20 public-alpha probe found that Codex `workspace-write` allowed an
outside-workspace read on the current macOS host. Evaluator filenames and
canaries remained undisclosed during the task runs, but that is not a general
read-isolation guarantee; generated-harness release eligibility remains denied.
