---
type: workflow
---

# Verify (sampled)

Triggered by "verify auth", "verify load-bearing", or "verify <page>". Exhaustive verification does not scale; sampling does.

1. **Determine the verification budget.** The human can specify a number of pages, a time budget, or a criticality filter. Default: all `load-bearing` pages flagged by the most recent sync, capped at 10 per session.
2. **Process in priority order:** load-bearing first, then important, then normal. Skip peripheral unless explicitly asked.
3. **For each page, honor its declared `verification_method`:**
   - `full`: re-read all the source files the page describes.
   - `spot-check`: read entry points and one or two internals.
   - `signature-only`: verify exported symbols haven't changed.
   - `declared-by-owner`: ask the owner to confirm in chat.
   Look for removed exports, changed signatures, new or removed dependencies, changed file paths.
4. **Propose updates as a diff.** Show the human what would change on each page. Wait for approval.
5. **On approval,** apply the edits and bump `last_verified_commit` and `last_verified`. Never bump them without having re-read the code at the declared depth.
6. **Append a verify entry to `log.md`** listing what was checked, what was deferred, and what changed, then commit: `verify: <scope>`.

Log entry format (append your bullets under today's `## YYYY-MM-DD` heading if it already exists; otherwise add a new heading at the top, newest first):

```
## 2026-04-10

- **Verify**: auth load-bearing
- **Checked**: subsystems/auth/modules/session-store.md (full), subsystems/auth/modules/token-mint.md (spot-check)
- **Deferred**: 4 normal pages (budget)
- **Changes**: SessionStore.Refresh signature changed; last_verified_commit bumped to e4f5g6h
```
