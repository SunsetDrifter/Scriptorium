---
type: workflow
---

# Ingest

Triggered by "ingest `raw/articles/foo.md`" or similar. Default to one source at a time with the human in the loop; batch only on explicit request.

1. **Read it fully.** If it references images in `raw/assets/`, view them too. Do not skim.
2. **Discuss before writing.** Tell the human the three to five most important takeaways and ask what to emphasize. Wait for their response before touching the wiki.
3. **Create the source page** at `sources/<kebab-name>.md`. Include: bibliographic info, a one-paragraph summary, key claims as a bulleted list, notable quotes (under 15 words each), and open questions raised.
4. **Identify affected pages.** Scan `index.md` and page frontmatter for entities, concepts, and synthesis pages this source touches, then ripgrep for anything missed. Open bodies only for the candidates.
5. **Update each affected page.** Integrate the new information, add the source to its frontmatter, bump `updated`, and refresh `description` if the page's scope shifted. If the source contradicts an existing claim, do not silently overwrite: set `confidence: contested` and structure the body latest-evidence-first, newest claim on top with its date, older claims below with theirs, so `workflows/reconcile.md` has clean input.
6. **Create new pages where needed.** If the source introduces an entity or concept that deserves its own page and doesn't have one, create it.
7. **Rebuild the index and lint.** Run `python3 lint.py rebuild-index`, then `python3 lint.py check` and fix any errors it reports.
8. **Append to `log.md`** using the format below, then commit: `ingest: <source title>`.
9. **Report back.** Tell the human exactly which pages were created, which were updated, and which contradictions surfaced. Be specific.

Log entry format (append your bullets under today's `## YYYY-MM-DD` heading if it already exists; otherwise add a new heading at the top, newest first):

```
## 2026-04-10

- **Ingest**: Article Title Here
- **Source**: sources/article-title.md
- **Creation**: entities/foo.md, concepts/bar.md
- **Update**: entities/baz.md, synthesis/qux.md
- **Contested**: noted in concepts/bar.md (sources/article-title.md vs sources/old-paper.md)
```
