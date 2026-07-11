---
type: workflow
---

# Triage

The human drops new material into `raw/inbox/` without sorting or renaming. Triage is bulk and cheap; documenting is per-thing and slow. Never collapse them into a single step unless the human explicitly waives it.

1. **List everything in `raw/inbox/`.** Read enough of each file to classify it. For binaries (PDFs, images), inspect the first page or two.
2. **Propose a plan as a table.** For each file: current name, proposed destination subfolder under `raw/` (`transcripts/`, `external-docs/`, `decisions/`, or other), proposed kebab-case filename, and a one-line "what this is" summary. If a file is unclear, mark it `needs human input` and ask.
3. **Wait for explicit approval.** Do not move anything until the human confirms the plan or sends corrections. If they correct individual rows, update those rows and re-show the table.
4. **Move and rename.** Once approved, move each file to its destination with the new name. Move any associated assets into `raw/assets/<slug>/` if they exist alongside the source.
5. **Append a triage entry to `log.md`** listing what moved where, then commit: `triage: <n> items from inbox`.
6. **Stop.** Triage does not write wiki pages and does not touch module, service, or architecture pages. That happens in document, separately.

Log entry format (append your bullets under today's `## YYYY-MM-DD` heading if it already exists; otherwise add a new heading at the top, newest first):

```
## 2026-04-10

- **Triage**: 4 items from inbox
- **Move**: raw/inbox/notes.txt -> raw/decisions/payments-provider-notes.md
- **Move**: raw/inbox/standup.m4a -> raw/transcripts/2026-04-09-standup.m4a
```
