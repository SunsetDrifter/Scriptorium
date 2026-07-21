---
type: workflow
---

# Document

Triggered by "document `libs/auth/session/`" or "document the new payments service".

1. **Identify the subsystem.** Does the target belong to an existing subsystem? If not, ask before creating a new one; subsystem boundaries are organizational, not just technical, and must match how the team thinks about ownership.
2. **Read the code.** Start with the public surface (exported functions, types, routes). If the module is large, read the entry points and the most-imported internals first. Do not pretend to have read what you skimmed, and do not infer behavior from filenames.
3. **Check for an existing page.** If one exists, this is an update, not a creation.
4. **Discuss before writing.** Tell the human what you found, what you'll file, and where in the subsystem hierarchy. Confirm `criticality` and `verification_method` with them. If the pass will create concept or synthesis pages, apply the page-worthiness test below and say so in the plan.
5. **Create or update the page.** Fill all required frontmatter, including `description` and `subsystem`. Set `last_verified_commit` to the current SHA and `verification_method` honestly: if you only spot-checked, say `spot-check`, not `full`. Cite specific file paths in the prose. If the code contradicts what a page already claims, do not overwrite: set `confidence: contested` and structure the body latest-evidence-first with dates, so `workflows/reconcile.md` has clean input. Never add reverse bookkeeping to other pages (`consumed_by` on modules, `consumers` on api pages); data-model pages DO store their own `producers` and `consumers` forward fields per the schema. Reverse views come from `python3 lint.py reverse-deps`.
6. **Update affected pages.** The subsystem README's `key_modules`/`key_services` if the page is significant, and subsystem or global architecture pages (Mermaid diagrams plus `includes`).
7. **File an ADR if a real decision was made.** Use the right scope: subsystem-local ADR if the decision only affects this subsystem, global ADR if it crosses boundaries. Follow `workflows/adr.md`.
8. **Rebuild and check.** Run `python3 lint.py rebuild-index`, then `python3 lint.py check` and fix any errors it reports.
9. **Append to `log.md`**, then commit: `document: <target>`.
10. **Report back** with every page created or updated and anything you could not verify.

## The page-worthiness test

Module, service, api, data-model, architecture, ADR, runbook, and postmortem pages are inventory: the code, its history, and its operation make them necessary. Any other new page (concept, synthesis) must pass all four parts:

1. **Topic shape.** It defines something referenceable by name: a concept, a pattern, a term, a convention, a metric. Not a grab-bag, not "assorted notes".
2. **Not meta.** It is not an overview, introduction, getting-started, quickstart, tutorial, walkthrough, FAQ, release-notes, changelog, or roadmap. If the natural filename would be one of those words, stop.
3. **Citation test.** You can write a sentence in an existing page of the form "See [X](/concepts/x.md) for ..." where X is a concrete noun. If the best sentence you can write is "see this page for context", it fails.
4. **Reuse test.** At least two existing pages would cite it, or one page needs it as load-bearing background that does not fit inline.

When in doubt, do not create the page; integrate the material into an existing one instead. A wiki that grows slowly is fine. A wiki full of overview and misc pages is noise.

Log entry format (append your bullets under today's `## YYYY-MM-DD` heading if it already exists; otherwise add a new heading at the top, newest first):

```
## 2026-04-10

- **Document**: libs/auth/session
- **Creation**: subsystems/auth/modules/session-store.md
- **Update**: subsystems/auth/README.md, subsystems/auth/architecture/module-deps.md
- **Verification**: full at e4f5g6h, criticality load-bearing
- **ADR**: subsystems/auth/adrs/0004-session-pinning.md
```
