# Task: deterministic release-note renderer

Implement `build_release_notes(changes)` in `src/release_notes.py`.

`changes` is a list of mappings. Every mapping MUST contain:

- `type`: exactly `added`, `changed`, or `fixed`;
- `summary`: a non-empty string after trimming surrounding whitespace;
- optional `issue`: a positive integer (booleans are not integers here).

The function MUST:

1. Reject a non-list input or an invalid entry with `ValueError`.
2. Not mutate the input or any entry.
3. Return Markdown beginning with `# Release notes`.
4. Group non-empty sections as `## Added`, `## Changed`, and `## Fixed` in
   that order.
5. Sort entries inside a section with numbered issues first in ascending numeric
   order, followed by entries without issues in case-insensitive summary order.
6. Render bullets as `- <trimmed summary> (#<issue>)` when an issue exists and
   `- <trimmed summary>` otherwise.
7. End the document with exactly one newline.
8. Return `# Release notes\n\nNo user-visible changes.\n` for an empty list.

Keep the implementation dependency-free and compatible with Python 3.9. Add or
improve repository-local tests as useful. Do not inspect or modify anything outside
this fixture workspace.

