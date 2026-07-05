# ADR

Triggered by "draft an ADR for X".

1. **Pick the scope first.** Subsystem-local decisions go in `subsystems/<name>/adrs/`; anything that crosses subsystem boundaries is global and goes in `adrs/`. When in doubt, ask. Cross-subsystem ADRs are always global.
2. **Read the context:** relevant module and subsystem pages, `raw/decisions/` notes, transcripts, recent code changes.
3. **Draft** using the standard structure: Context, Decision, Consequences, Alternatives Considered. The Decision section is one declarative sentence; the rest justifies it. No filler.
4. **Number it** next in sequence within its directory (numbering is per directory; the script flags gaps in each). Set `status: proposed`, `subsystem: <name>` or `subsystem: global` with `affects: [...]` for global ADRs.
5. **Handle supersession.** If it supersedes an existing ADR, add it to `supersedes`, and edit the old ADR's frontmatter only: add `superseded_by` and flip its status. The old ADR's body stays untouched, always.
6. **Show the human the draft. Wait.** On approval, set `status: accepted` and link it from affected module and subsystem pages (README `key_adrs` if it is load-bearing for the subsystem).
7. **Rebuild and check:** `python3 lint.py rebuild-index`, then `python3 lint.py check`.
8. **Append to `log.md`**, then commit: `adr: <number> <slug>`.

Log entry format:

```
## [2026-04-10] adr | 0008 stripe over adyen
- scope: global (affects: billing, platform)
- status: accepted
- linked from: subsystems/billing/README.md, subsystems/billing/modules/payments-core.md
```
