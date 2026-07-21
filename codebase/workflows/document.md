---
type: workflow
---

# Document

Triggered by "document `src/auth/`" or "document the new payments service".

1. **Read the code.** Open the actual source files. Do not infer behavior from filenames or guess from imports. If the code is too large to read fully, read the package's public surface first (exported functions, types, routes), then drill into the most important internals.
2. **Discuss before writing.** Tell the human what you found, what you'll file, and where. Confirm scope: is this one module page or several? Does it need a service page too? API or data-model pages? If the pass will create concept or synthesis pages, apply the page-worthiness test at the end of this file and say so in the plan.
3. **Create or update the module/service/api/data-model pages.** Fill all required frontmatter, including a one-sentence `description`. Set `last_verified_commit` to the current SHA and `last_verified` to today. Cite specific file paths and line ranges in the prose. If the code contradicts what a page already claims, do not overwrite: set `confidence: contested` and structure the body latest-evidence-first with dates, so `workflows/reconcile.md` has clean input. The new page's own forward fields (`depends_on`, `modules`, `exposes`, `consumes`, `defined_in`, `producers`, `consumers`) are the only stored edges; do not add reverse bookkeeping to other pages. The reverse view is derived: `python3 lint.py reverse-deps`.
4. **Update affected architecture pages.** Add the new module to the relevant Mermaid diagrams and update `includes`. Every module must land in at least one architecture page.
5. **File an ADR if a real decision was made.** Why this library, why this pattern, why this boundary. Use the next ADR number. Cite it from the module page.
6. **Rebuild the index and lint.** Run `python3 lint.py rebuild-index`, then `python3 lint.py check` and fix any errors it reports.
7. **Append to `log.md`** using the format below, then commit: `document: <thing>`.
8. **Report back** with every file created or updated and any inconsistencies you couldn't resolve.

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

- **Document**: payments service
- **Creation**: services/payments.md, modules/payments-core.md, apis/payments-http.md
- **Update**: architecture/system.md
- **ADR**: adrs/0008-stripe-over-adyen.md
```
