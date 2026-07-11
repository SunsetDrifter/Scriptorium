---
type: workflow
---

# Query

Triggered by any question answerable from the wiki.

1. **Scan `index.md` and frontmatter first** to find candidate pages. Do not guess at file paths, and do not open page bodies until a page's `description` or tags look relevant.
2. **Read the candidate pages fully**, then follow links one hop out for context.
3. **Synthesize an answer with citations.** Every claim links to the wiki page that supports it, and the wiki page in turn cites a source. The chain must be intact.
4. **Surface uncertainty.** If pages disagree, say so. If a question can't be answered from the wiki, say so and suggest what source would fill the gap.
5. **Offer to file the answer.** If the answer is non-trivial and likely useful later, ask whether to save it under `queries/`. If filed: create the page, run `python3 lint.py rebuild-index`, append to `log.md`, and commit: `query: <short question>`.

Log entry format (append your bullets under today's `## YYYY-MM-DD` heading if it already exists; otherwise add a new heading at the top, newest first):

```
## 2026-04-10

- **Query**: "How does X relate to Y?"
- **Filed**: queries/x-vs-y.md
- **Read**: 7 pages
```
