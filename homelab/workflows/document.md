# Document

Triggered by "document the new VM", "document this OPNsense config", or similar. Default to one component at a time with the human in the loop.

1. **Gather context.** Read the raw source (config dump, screenshot, vendor doc) if there is one. Ask the human anything you need: hostname, IP, purpose, dependencies, who consumes it.
2. **Discuss before writing.** Tell the human what you're going to file and where. Confirm component kind, dependencies, and which topology pages this touches. Wait for their response before touching the wiki.
3. **Create or update the component page** under `components/`. Fill all required frontmatter, including a one-line `description`. Set `last_verified` to today. If new information contradicts what a page already claims, do not overwrite: set `confidence: contested` and structure the body latest-evidence-first with dates, so `workflows/reconcile.md` has clean input. List everything it depends on in its own `depends_on`; that is the only stored edge. Do not touch other components' frontmatter to record the reverse direction, it is derived (`python3 lint.py reverse-deps`).
4. **Update affected topology pages.** Add the component to the relevant Mermaid diagrams and to `includes` frontmatter. Every component must appear in at least one topology page.
5. **Create or append a decision record.** If this involved a real decision (why VLAN 20 and not VLAN 30, why Caddy over Traefik), file the reasoning under `sources/decisions/<date>-<slug>.md` and cite it from the component page's `sources`.
6. **Rebuild the index and lint.** Run `python3 lint.py rebuild-index`, then `python3 lint.py check` and fix any errors it reports.
7. **Append to `log.md`** using the format below, then commit: `document: <component>`.
8. **Report back.** List every file created or updated. Call out any cross-reference inconsistencies you couldn't resolve.

Log entry format:

```
## [2026-04-10] document | grafana VM
- created: components/grafana.md
- updated: topology/services.md (diagram + includes)
- decision: sources/decisions/2026-04-10-grafana-on-proxmox-01.md
```
