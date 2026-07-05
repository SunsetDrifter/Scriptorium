# Postmortem

Triggered by "log postmortem: <thing>".

1. **Create `postmortems/<date>-<slug>.md`** with `subsystem: global` and `affects:` listing every subsystem involved. Frontmatter also records severity, duration, affected services, affected modules.
2. **Walk through the timeline with the human:** what was noticed, what was tried, what worked, root cause.
3. **Link every module and service involved** using full paths. Add the postmortem to the "incidents" section of each affected subsystem's README.
4. **End with action items:** new runbooks, ADRs, refactor proposals. Create the follow-ups in the same session if the human approves (ADRs via `workflows/adr.md`, at the right scope).
5. **Rebuild and check:** `python3 lint.py rebuild-index`, then `python3 lint.py check`.
6. **Append to `log.md`**, then commit: `postmortem: <slug>`.

Log entry format:

```
## [2026-04-10] postmortem | session-cache-stampede
- filed as: postmortems/2026-04-10-session-cache-stampede.md
- subsystems affected: auth, platform
- readmes updated: subsystems/auth/README.md, subsystems/platform/README.md
- follow-ups: runbooks/cache-warmup.md, adrs/0009-session-cache-ttl.md (proposed)
```
