---
type: workflow
---

# Query

Triggered by any question answerable from the wiki: "what depends on proxmox-01?", "why is VLAN 20 the IoT VLAN?", "how do I recover grafana?".

1. **Scan `index.md` and frontmatter first** to find candidate pages. Do not guess at file paths, and do not open page bodies until a page's `description` or tags look relevant. For "what depends on X" questions, run `python3 lint.py reverse-deps` instead of grepping.
2. **Read the candidate pages fully**, then follow links one hop out for context (components to their topology pages, incidents to their runbooks).
3. **Synthesize an answer with citations.** Every claim links to the wiki page that supports it, and the wiki page in turn cites a source or decision record. The chain must be intact.
4. **Surface uncertainty.** If a component's `last_verified` is stale, say the answer may not match reality. If pages disagree, say so. If the wiki can't answer, say so and suggest what to document or verify to fill the gap.
5. **Offer to file the answer.** If the answer is non-trivial and likely useful later, ask whether to save it under `queries/`. If filed: create the page, run `python3 lint.py rebuild-index`, append to `log.md`, and commit: `query: <short question>`.

Log entry format (append your bullets under today's `## YYYY-MM-DD` heading if it already exists; otherwise add a new heading at the top, newest first):

```
## 2026-04-10

- **Query**: "What breaks if proxmox-01 goes down?"
- **Filed**: queries/proxmox-01-blast-radius.md
- **Read**: 6 pages
```
