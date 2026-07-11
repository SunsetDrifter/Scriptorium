---
type: workflow
---

# ADR

Triggered by "draft an ADR for X".

1. **Read whatever context exists**: relevant module pages, raw decision notes, transcripts, recent code changes.
2. **Draft using the standard structure**: Context, Decision, Consequences, Alternatives Considered. Keep each section short and concrete. No filler. Write the Decision section as one declarative sentence.
3. **Number it next in sequence**, zero-padded: `adrs/0008-<slug>.md`. Set `status: proposed`.
4. **Handle supersession.** If it supersedes an existing ADR, list that ADR in `supersedes`, and edit the old ADR's frontmatter to set `superseded_by` and flip its `status` to `superseded`. This frontmatter flip is the one allowed edit to a past ADR; its body stays untouched.
5. **Show the human the draft. Wait for approval.** On approval, set `status: accepted` and link it from affected module and service pages.
6. **Rebuild the index** (`python3 lint.py rebuild-index`), **append to `log.md`**, then commit: `adr: NNNN <slug>`.

Log entry format (append your bullets under today's `## YYYY-MM-DD` heading if it already exists; otherwise add a new heading at the top, newest first):

```
## 2026-04-10

- **ADR**: 0008 stripe-over-adyen
- **Status**: accepted
- **Linked**: services/payments.md, modules/payments-core.md
```
