# Contributing

Small, evidence-backed changes are welcome.

1. Open an issue before changing HDP/HIR semantics, release eligibility,
   evaluator boundaries or the adapter contract.
2. Create a focused branch and keep canonical semantics target-neutral.
3. Add tests that encode the failure being prevented.
4. Run:

   ```bash
   uv sync --frozen --python 3.12
   uv run pytest
   ./scripts/smoke-consumer.sh
   ./scripts/verify-all.sh
   ```

5. Update relevant documentation and add an ADR for a material architectural
   decision or rejected alternative.

Do not commit credentials, personal paths, private harnesses, raw prompts or
held-out evaluator cases. Generated tests are not independent proof of behaviour;
preserve negative, flaky and blocked outcomes in verification reports.

By contributing, you agree that your contribution is licensed under Apache-2.0.
