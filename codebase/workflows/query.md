# Query

Triggered by any question answerable from the wiki or the code.

1. **Scan `index.md` and frontmatter first** to find candidate pages. Do not guess at file paths, and do not open page bodies until a page's `description` or tags look relevant.
2. **Read the candidate pages fully**, then follow wikilinks one hop out for context.
3. **For code questions, offer to read the live source** instead of relying solely on the wiki, especially when a relevant page's `last_verified_commit` lags the pinning block. Reading the code repo is always allowed; modifying it never is.
4. **Synthesize an answer with citations.** Every claim links to the wiki page that supports it; claims about code cite `path/file.go:12-34` at a stated commit.
5. **Surface uncertainty.** If pages disagree, or the wiki lags the code, say so. If the question can't be answered, say so and suggest what to document next.
6. **Offer to file the answer.** If it is non-trivial and likely useful later, ask whether to save it under `queries/`. If filed: create the page, run `python3 lint.py rebuild-index`, append to `log.md`, and commit: `query: <short question>`.

Log entry format:

```
## [2026-04-10] query | "What writes to the sessions table?"
- filed as: queries/sessions-table-writers.md
- pages read: 6
```
