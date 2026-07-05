# Maintain

The unattended maintenance pass, run on a schedule or by "maintenance pass". Its safety comes from reversibility: all work happens on the `maintenance` branch, never on main, and the human merges only after review.

Setup: `git checkout maintenance` (create it from main if absent; if it holds unmerged work from a prior run, continue on it).

Allowed actions, exhaustively:

1. **Run `python3 lint.py check` and fix the mechanical errors it reports**: broken wikilinks with unambiguous targets, frontmatter fields whose correct value is derivable (malformed dates, wrong enum casing), dangling references to renamed pages.
2. **Run `python3 lint.py rebuild-index`.**
3. **Insert cross-links for orphans**, only where the script's mention hints show an unambiguous prose mention of the orphan page.
4. **Collect, do not fix**: contested pages needing reconcile, concept gaps, taxonomy additions worth proposing, pages whose `description` has drifted from the body. These go in the run report, not into edits.

Forbidden in unattended runs: changing the meaning of any prose, deleting, merging, or renaming pages, creating new page types or folders, resolving contested pages, editing `CLAUDE.md`, `workflows/`, or `taxonomy.md`, and touching `raw/`.

Finish: append one log entry, commit everything as `maintain: <date> run`, and leave the branch unmerged. If errors remain that the allowed actions can't fix (a secrets hit, an ambiguous link), do not commit; leave the tree dirty and put the blocker at the top of the run report.

When the human says "review maintenance": walk them through `git diff main..maintenance` change by change, then merge on approval and continue reusing the branch.

Log entry format:

```
## [2026-07-05] maintain | scheduled run
- fixed: 2 broken wikilinks; index rebuilt
- cross-linked: queries/x-vs-y.md from synthesis/overview.md
- proposals: reconcile concepts/foo.md; add tag 'observability' to taxonomy
```
