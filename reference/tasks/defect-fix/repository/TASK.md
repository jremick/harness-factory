# Defect task: username normalization

Repair `normalize_username(value)` in `src/usernames.py`.

- Accept only strings.
- Trim surrounding whitespace and lowercase the value.
- Replace each run of non-ASCII-alphanumeric characters with one hyphen.
- Remove leading/trailing hyphens.
- Raise `ValueError` when no alphanumeric characters remain.
- Preserve input strings and dependencies.

Run the repository tests through the generated evidence recorder and record
completion only after they pass.
