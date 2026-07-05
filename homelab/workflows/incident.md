# Incident

When something broke. Triggered by "log incident: <thing>".

1. **Create `incidents/<date>-<slug>.md`** with frontmatter `type: incident`, a one-line `description`, plus severity, affected components, and duration in the body or frontmatter.
2. **Walk through the timeline with the human:** what was noticed, what was tried, what worked. Write it up as a timeline, not a narrative.
3. **Link every component involved** with `[[wikilinks]]`. Add the incident to each affected component page's "Incidents" section and bump those pages' `updated`.
4. **Ask about follow-ups.** Does this suggest a new runbook, a topology change, or a concept page? If yes, create the follow-ups in the same session.
5. **Rebuild the index and lint.** Run `python3 lint.py rebuild-index`, then `python3 lint.py check` and fix any errors it reports.
6. **Append to `log.md`** using the format below, then commit: `incident: <slug>`.

Log entry format:

```
## [2026-04-10] incident | grafana down 45min
- filed: incidents/2026-04-10-grafana-oom.md
- updated: components/grafana.md, components/proxmox-01.md
- new runbook: runbooks/grafana-oom-recovery.md
```
