# Lint

Triggered by "lint the wiki". Lint has two halves: the script does everything mechanical; you do only the checks that need judgment.

1. **Run `python3 lint.py check`** and relay its findings to the human, grouped by severity. Do not re-verify by hand what the script already checks (frontmatter, wikilinks, orphans, references, inbox, secrets, index drift, log format).
2. **Contradictions.** Look for pages whose claims disagree with each other or with newer sources. Any `confidence: contested` page must explain the disagreement in its body; flag ones that don't.
3. **Stale claims.** Pages whose sources have been superseded by newer ones in the same topic area.
4. **Concept gaps.** Terms that appear repeatedly across pages but have no dedicated page of their own.
5. **Description drift.** Spot-check a handful of pages: does the `description` still match the body? A wrong description poisons every future scan.
6. **Investigation suggestions.** Three to five questions the wiki currently can't answer well, and what kinds of sources would help.

Report findings as a structured list. Do not auto-fix anything except trivially safe broken links (where the rename target is unambiguous). Wait for human direction on the rest.

When done: append a lint entry to `log.md` and commit: `lint: <n> findings`.

Log entry format:

```
## [2026-04-10] lint
- script: 1 error, 3 warnings
- judgment: 2 contradictions, 3 concept gaps
- see lint report in chat
```
