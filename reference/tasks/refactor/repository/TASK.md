# Refactor task: invoice total

Refactor `calculate_total(lines)` in `src/invoice.py` to separate validation and
line calculation into one or more private helpers while preserving behaviour.

Constraints:

- Keep `calculate_total` as the only public callable.
- Preserve exact `Decimal` arithmetic and input order.
- Do not mutate the input or accept new input forms.
- Keep the module dependency-free outside the standard library.

Run the repository tests through the generated evidence recorder and record
completion only after they pass.
