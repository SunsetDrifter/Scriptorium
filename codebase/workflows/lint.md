# Lint

Triggered by "lint the wiki". Lint has two halves: the script does everything mechanical; you do only the checks that need judgment.

1. **Run `python3 lint.py check`** and relay its findings to the human, grouped by severity. Do not re-verify by hand what the script already covers: frontmatter validity, broken wikilinks, orphans, dangling references (including `defined_in` and `includes`), sync drift against the pinning block, missing Mermaid diagrams on architecture pages, ADR numbering gaps and superseded ADRs without forward links, secrets, inbox health, index drift, log format.
2. **Dead code references.** File paths and line-range citations in prose that point at code that no longer exists, and `source_path` values that have moved. This needs access to the pinned repo; the script cannot see the code.
3. **Architecture fiction.** Architecture pages whose `includes` or diagrams reference modules that are `status: removed` or clearly gone. The script catches nonexistent pages; you judge status.
4. **Diagram semantic drift.** Mermaid diagrams whose nodes or edges no longer match what the pages and the code say.
5. **ADR contradictions.** Accepted ADRs whose decisions contradict newer accepted ADRs.
6. **Contested without explanation.** Any `confidence: contested` page must explain the disagreement in its body; flag ones that don't.
7. **Stale runbooks.** Runbooks not touched in 6 months for services that are still active.
8. **Concept gaps.** Domain terms appearing across many pages with no dedicated concept page.
9. **Description drift.** Spot-check a handful of pages: does the `description` still match the body? A wrong description poisons every future scan.
10. **Investigation suggestions.** Three to five questions the wiki currently can't answer well.

Report findings as a structured list. Do not auto-fix anything except trivially safe broken links (where the rename target is unambiguous). Wait for human direction on the rest.

When done: append a lint entry to `log.md` and commit: `lint: <n> findings`.

Log entry format:

```
## [2026-04-10] lint
- script: 2 errors, 4 warnings
- judgment: 1 dead code reference, 2 concept gaps
- see lint report in chat
```
