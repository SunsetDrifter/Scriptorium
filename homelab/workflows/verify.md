---
type: workflow
---

# Verify

Periodic reality check. Triggered by "verify components" or "verify components/<component>".

1. **Build the list.** The named component, or if none was named, all components whose `last_verified` is older than 60 days (`python3 lint.py check` reports them as staleness warnings).
2. **Propose current state, ask for corrections.** For each component, ask the human targeted questions: "Is `proxmox-01` still on firmware 7.2.1? Still hosting `grafana`, `prometheus`, `loki`?" Do not ask open-ended questions; state what the wiki currently believes and let the human correct it.
3. **Apply corrections.** For each correction, update the component page (frontmatter and body), touch every other page that references the changed fact (topology diagrams included), and bump `last_verified` to today.
4. **Bump the rest.** For each unchanged component, just bump `last_verified` to today.
5. **Rebuild the index and lint** if any pages changed: `python3 lint.py rebuild-index`, then `python3 lint.py check` and fix errors. (Bumping `last_verified` changes the index annotations, so this is almost always needed.)
6. **Append a verify entry to `log.md`** listing what was checked, what changed, what didn't, then commit: `verify: <n> components checked`.

Log entry format (append your bullets under today's `## YYYY-MM-DD` heading if it already exists; otherwise add a new heading at the top, newest first):

```
## 2026-04-10

- **Verify**: 7 components checked
- **Change**: opnsense (firmware 25.1 -> 25.4)
- **Unchanged**: 6
- **Note**: last_verified bumped on all 7
```
