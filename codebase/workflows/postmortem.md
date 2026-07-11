---
type: workflow
---

# Postmortem

Triggered by "log postmortem: <thing>".

1. **Create `postmortems/<date>-<slug>.md`.** Standard frontmatter plus severity, duration, and the services and modules affected.
2. **Walk through the timeline with the human**: what was noticed, what was tried, what worked, root cause.
3. **Link every module and service involved** with markdown links, and add the postmortem to those pages' "incidents" section.
4. **End with action items**: new runbooks, ADRs, refactor proposals. Create the follow-ups in the same session if the human approves.
5. **Rebuild the index and lint.** Run `python3 lint.py rebuild-index`, then `python3 lint.py check` and fix any errors it reports.
6. **Append to `log.md`**, then commit: `postmortem: <slug>`.

Log entry format (append your bullets under today's `## YYYY-MM-DD` heading if it already exists; otherwise add a new heading at the top, newest first):

```
## 2026-04-10

- **Postmortem**: payments-outage
- **Creation**: postmortems/2026-04-10-payments-outage.md
- **Update**: services/payments.md, modules/payments-core.md
- **Follow-ups**: runbooks/restore-payments.md
```
