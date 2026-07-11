---
type: workflow
---

# Query

Triggered by any question answerable from the wiki.

1. **Orient via the subsystem README first.** Identify which subsystem the question touches and open its `README.md`. Do not load the global index into context for every query; it exists for global pages and subsystem entry points, nothing more. For cross-cutting questions, scan frontmatter of `subsystem: global` pages whose `affects` mentions the subsystems involved.
2. **Scan frontmatter before opening bodies.** Open a page only when its `description` or tags look relevant.
3. **Read the candidate pages fully**, then follow links one hop out for context.
4. **Synthesize an answer with citations.** Every claim links to the wiki page that supports it, and code claims carry the page's `last_verified_commit` caveat if the page is stale. For code questions, also offer to read the live source rather than relying solely on the wiki.
5. **Surface uncertainty.** If pages disagree, say so. If the wiki can't answer, say so and suggest what to document.
6. **Offer to file the answer.** If non-trivial and likely useful later, ask whether to save it under `queries/` (with `subsystem: global` and `affects:` listing the subsystems it spans). If filed: create the page, run `python3 lint.py rebuild-index`, append to `log.md`, and commit: `query: <short question>`.

Log entry format (append your bullets under today's `## YYYY-MM-DD` heading if it already exists; otherwise add a new heading at the top, newest first):

```
## 2026-04-10

- **Query**: "How do sessions survive an auth-api deploy?"
- **Filed**: queries/session-survival-on-deploy.md
- **Read**: 6 (auth README + 5)
```
