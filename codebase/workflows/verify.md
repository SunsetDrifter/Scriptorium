# Verify

Triggered by "verify modules" or "verify modules/<page>".

1. **List the pages to verify.** If a specific page was named, just that one. Otherwise every page whose `last_verified_commit` lags `last_synced_commit`; `python3 lint.py check` reports these as sync-drift warnings.
2. **For each, re-read the actual source files** and compare against the page's claims. Look for: removed exports, changed signatures, new dependencies, removed dependencies, changed file paths.
3. **Propose updates as a diff.** Show the human exactly what would change on each page before touching it.
4. **On approval, update the page** and bump `last_verified_commit` and `last_verified`. Update `depends_on` and the page's other forward edges if the code's dependencies changed. If nothing changed in the code, bumping the two fields is the whole edit.
5. **Rebuild the index if needed.** If any `description`, `status`, or `last_verified_commit` changed, run `python3 lint.py rebuild-index`.
6. **Append a verify entry to `log.md`**, then commit: `verify: <pages>`.

Log entry format:

```
## [2026-04-10] verify | modules/auth
- changes: SessionStore.Refresh signature changed, removed LegacyToken
- last_verified_commit bumped to e4f5g6h
```
