# Evaluator boundary

This directory is evaluator-owned and is never an input to the generator or the
generated harness. The clean-agent runner places it beside, not inside, the
agent workspace and removes all write permission bits before execution.

The harness receives only the task repository and generated artifacts. The
outer runner records evaluator hashes before and after the run and fails if the
boundary changes.

