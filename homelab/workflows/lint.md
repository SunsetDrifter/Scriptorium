# Lint

Triggered by "lint the wiki". Lint has two halves: the script does everything mechanical; you do only the checks that need judgment.

1. **Run `python3 lint.py check`** and relay its findings to the human, grouped by severity. Do not re-verify by hand what the script already checks (frontmatter, wikilinks, orphans, dangling references, inbox health, secrets, `last_verified` staleness, Mermaid presence on topology pages, index drift, log format).
2. **Topology fiction.** The script verifies that `includes` paths exist; you check that no topology page includes a component whose `status` is `retired`, and that diagrams don't depict links or devices that no longer exist.
3. **Diagram semantic drift.** Mermaid diagrams whose node names no longer match the current component page titles, or that show a component under an old hostname.
4. **Contested pages.** Any `confidence: contested` page must explain the disagreement in its body; flag ones that don't.
5. **Concept gaps.** Terms that appear repeatedly across pages (a protocol, a pattern) but have no dedicated concept page.
6. **Stale runbooks.** Runbooks not touched in over 6 months whose components are still `status: active`. Procedures rot as fast as firmware.
7. **Description drift.** Spot-check a handful of pages: does the `description` still match the body? A wrong description poisons every future scan.
8. **Investigation suggestions.** Three to five questions the wiki currently can't answer well, and what to document or verify to fix that.

Report findings as a structured list. Do not auto-fix anything except trivially safe broken links (where the rename target is unambiguous). Wait for human direction on the rest.

When done: append a lint entry to `log.md` and commit: `lint: <n> findings`.

Log entry format:

```
## [2026-04-10] lint
- script: 2 errors, 4 warnings
- judgment: 1 topology fiction, 2 concept gaps
- see lint report in chat
```
