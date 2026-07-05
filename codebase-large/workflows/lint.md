# Lint

Triggered by "lint the wiki". Lint has two halves: the script does everything mechanical; you do only the checks that need judgment.

1. **Run `python3 lint.py check`** and relay its findings grouped by severity. Do not re-verify by hand what it already covers: frontmatter validity (including the `subsystem` field), broken wikilinks, orphans, dangling references (including `key_modules` and `includes`), tags, contested age, criticality-weighted sync drift, owner-review staleness, mermaid presence and node counts, ADR numbering gaps and forward links in both global and subsystem directories, secrets, inbox health, index drift, log format.
2. **Run `python3 lint.py coverage`** and summarize `coverage.md` per subsystem. Flag any subsystem under 30% coverage on load-bearing areas; coverage is partial by design, so report gaps as choices to make, not failures.
3. **Run `python3 lint.py reverse-deps`** and review the derived map for cross-subsystem coupling: modules depending on another subsystem's internal modules rather than its public APIs. Flag as architectural smell, not error.

Then the judgment checks:

4. **Orphan repair.** For each orphan the script reports, use its unlinked-mention hints to propose wikilink insertions; insert on approval. If no genuine mention exists anywhere, recommend merging or deleting the page (ask). Never force a link where the prose doesn't naturally mention the page.
5. **Dead code references.** `source_path` values and file citations pointing at code that no longer exists in the repo.
6. **Architecture fiction and diagram drift.** Architecture pages referencing modules that don't exist or are `removed`; diagrams whose story no longer matches the pages they include.
7. **ADR contradictions and mis-scoped ADRs.** Accepted ADRs contradicting newer accepted ADRs, and subsystem ADRs whose decisions affect other subsystems (they should be global).
8. **Contested without explanation.** Any `confidence: contested` page whose body doesn't explain the disagreement; offer to run `workflows/reconcile.md` on pages the script flags as long-contested.
9. **Stale runbooks.** Runbooks untouched in 6 months for active services.
10. **Glossary gaps.** Domain terms appearing in 5+ pages with no `glossary.md` entry.
11. **Subsystem orphans.** Modules in a subsystem not reachable from its README via `key_modules` or any architecture page.
12. **Description drift.** Spot-check a handful of pages: does `description` still match the body? A wrong description poisons every future scan.
13. **Investigation suggestions.** Three to five questions per active subsystem the wiki currently can't answer well.

Report findings as a structured list. Auto-fix only the trivially safe (broken wikilinks with an unambiguous rename target). Everything else waits for human direction.

When done: append a lint entry to `log.md` and commit: `lint: <n> findings`.

Log entry format:

```
## [2026-04-10] lint
- script: 2 errors, 7 warnings; coverage: auth 64%, billing 41%
- judgment: 1 mis-scoped adr, 2 glossary gaps, 1 coupling smell
- see lint report in chat
```
