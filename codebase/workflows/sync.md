---
type: workflow
---

# Sync

Triggered by "sync to current".

1. **Read the current commit SHA** of the local repo (`local_path` in the pinning block). Read-only; never modify the code repo.
2. **Compare to `last_synced_commit`** in `index.md`. If unchanged, say so and stop.
3. **List all files changed** between the two commits (`git diff --name-only <old>..<new>` in the code repo).
4. **For each changed file, find wiki pages whose `source_path` covers it.** Scan frontmatter; do not open bodies for this.
5. **Mark each affected page as needing reverification.** List them in chat with their current `last_verified_commit`.
6. **Ask the human which to verify now and which to defer.** Do not auto-update `last_verified_commit` without re-reading the code.
7. **Update the pinning block by hand.** Set `last_synced_commit` and `last_synced_at` in the yaml block at the top of `index.md`. It lives above the generated marker, so `rebuild-index` will not touch it; you must edit it yourself.
8. **Append a sync entry to `log.md`** with what changed and what was flagged, then commit: `sync: <old> -> <new>`.

Log entry format (append your bullets under today's `## YYYY-MM-DD` heading if it already exists; otherwise add a new heading at the top, newest first):

```
## 2026-04-10

- **Sync**: a1b2c3d -> e4f5g6h
- **Changed**: 23
- **Pages**: modules/auth, modules/users, services/api-gateway
```
