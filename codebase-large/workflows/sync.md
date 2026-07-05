# Sync

Triggered by "sync to current". Sync flags; it never rewrites pages.

1. **Read the current commit SHA** of the local repo. Compare to `last_synced_commit` in `index.md`. If unchanged, say so and stop.
2. **Diff and bucket by subsystem.** `git diff --name-only <last_synced_commit>..HEAD`, drop anything outside `wiki_scope` (`include`/`exclude` in the pinning block), and bucket the remaining files by subsystem.
3. **Find affected pages.** For each subsystem with changes, list pages whose `source_path` covers the changed files. Group them by `criticality`.
4. **Report in chat:** changed files per subsystem, pages flagged for reverify with their criticality and current `last_verified_commit`. Do not auto-update anything; `last_verified_commit` only moves when the code is actually re-read (see `workflows/verify.md`).
5. **Update `last_synced_commit` and `last_synced_at`** in the `index.md` pinning block (above the generated marker).
6. **Append a sync entry to `log.md`**, then commit: `sync: <old> -> <new>`.

Log entry format (per-subsystem counts are mandatory):

```
## [2026-04-10] sync | a1b2c3d -> e4f5g6h
- changed files: 247
- subsystems affected: auth (43), billing (12), platform (88)
- pages flagged for reverify: load-bearing 6, important 14, normal 21
```
