---
type: workflow
---

# Document

Triggered by "document the new VM", "document this OPNsense config", or similar. Default to one component at a time with the human in the loop.

1. **Gather context.** Read the raw source (config dump, screenshot, vendor doc) if there is one. Ask the human anything you need: hostname, IP, purpose, dependencies, who consumes it.
2. **Discuss before writing.** Tell the human what you're going to file and where. Confirm component kind, dependencies, and which topology pages this touches. Wait for their response before touching the wiki. If the pass will create concept or synthesis pages, apply the page-worthiness test at the end of this file and say so in the plan.
3. **Create or update the component page** under `components/`. Fill all required frontmatter, including a one-line `description`. Set `last_verified` to today. If new information contradicts what a page already claims, do not overwrite: set `confidence: contested` and structure the body latest-evidence-first with dates, so `workflows/reconcile.md` has clean input. List everything it depends on in its own `depends_on`; that is the only stored edge. Do not touch other components' frontmatter to record the reverse direction, it is derived (`python3 lint.py reverse-deps`).
4. **Update affected topology pages.** Add the component to the relevant Mermaid diagrams and to `includes` frontmatter. Every component must appear in at least one topology page.
5. **Create or append a decision record.** If this involved a real decision (why VLAN 20 and not VLAN 30, why Caddy over Traefik), file the reasoning under `sources/decisions/<date>-<slug>.md` and cite it from the component page's `sources`.
6. **Rebuild the index and lint.** Run `python3 lint.py rebuild-index`, then `python3 lint.py check` and fix any errors it reports.
7. **Append to `log.md`** using the format below, then commit: `document: <component>`.
8. **Report back.** List every file created or updated. Call out any cross-reference inconsistencies you couldn't resolve.

## The page-worthiness test

Component, topology, incident, runbook, and decision pages are inventory: they record what exists, what happened, and how to operate it. Any other new page (concept, synthesis) must pass all four parts:

1. **Topic shape.** It defines something referenceable by name: a concept, a pattern, a term, a convention, a metric. Not a grab-bag, not "assorted notes".
2. **Not meta.** It is not an overview, introduction, getting-started, quickstart, tutorial, walkthrough, FAQ, release-notes, changelog, or roadmap. If the natural filename would be one of those words, stop.
3. **Citation test.** You can write a sentence in an existing page of the form "See [X](/concepts/x.md) for ..." where X is a concrete noun. If the best sentence you can write is "see this page for context", it fails.
4. **Reuse test.** At least two existing pages would cite it, or one page needs it as load-bearing background that does not fit inline.

When in doubt, do not create the page; integrate the material into an existing one instead. A wiki that grows slowly is fine. A wiki full of overview and misc pages is noise.

Log entry format (append your bullets under today's `## YYYY-MM-DD` heading if it already exists; otherwise add a new heading at the top, newest first):

```
## 2026-04-10

- **Document**: grafana VM
- **Creation**: components/grafana.md
- **Update**: topology/services.md (diagram + includes)
- **Decision**: sources/decisions/2026-04-10-grafana-on-proxmox-01.md
```
