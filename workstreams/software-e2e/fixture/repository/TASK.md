# Task: deterministic reorder candidates

Implement `reorder_candidates` in `src/inventory.py`.

Required behavior:

- Accept any iterable of `StockItem` values and a `threshold`.
- Reject a threshold that is a boolean, not an integer, or negative by raising
  `ValueError`.
- Reject an item whose SKU is empty after trimming, or whose quantity is a
  boolean, not an integer, or negative, by raising `ValueError`.
- Include items whose quantity is less than or equal to the threshold.
- Return trimmed SKU strings sorted by quantity ascending, then SKU using
  case-insensitive order, with the original trimmed SKU as the final tie-breaker.
- Do not mutate the iterable or its items.

Keep the existing `StockItem` API. Do not add dependencies, persistence,
network access, or a command-line interface.

