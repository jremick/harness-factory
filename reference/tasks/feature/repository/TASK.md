# Feature task: integer statistics

Implement `summarize(values)` in `src/statistics.py`.

- Accept only a `list` of integers; booleans are invalid. Raise `ValueError`
  for invalid input.
- Do not mutate the input.
- Return keys `count`, `total`, `minimum`, and `maximum`.
- For an empty list, return count/total zero and minimum/maximum `None`.
- Keep the implementation dependency-free.

Run the repository tests through the generated evidence recorder and record
completion only after they pass.
