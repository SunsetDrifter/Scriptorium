# Document

Triggered by "document `src/auth/`" or "document the new payments service".

1. **Read the code.** Open the actual source files. Do not infer behavior from filenames or guess from imports. If the code is too large to read fully, read the package's public surface first (exported functions, types, routes), then drill into the most important internals.
2. **Discuss before writing.** Tell the human what you found, what you'll file, and where. Confirm scope: is this one module page or several? Does it need a service page too? API or data-model pages?
3. **Create or update the module/service/api/data-model pages.** Fill all required frontmatter, including a one-sentence `description`. Set `last_verified_commit` to the current SHA and `last_verified` to today. Cite specific file paths and line ranges in the prose. The new page's own forward fields (`depends_on`, `modules`, `exposes`, `consumes`, `defined_in`, `producers`, `consumers`) are the only stored edges; do not add reverse bookkeeping to other pages. The reverse view is derived: `python3 lint.py reverse-deps`.
4. **Update affected architecture pages.** Add the new module to the relevant Mermaid diagrams and update `includes`. Every module must land in at least one architecture page.
5. **File an ADR if a real decision was made.** Why this library, why this pattern, why this boundary. Use the next ADR number. Cite it from the module page.
6. **Rebuild the index and lint.** Run `python3 lint.py rebuild-index`, then `python3 lint.py check` and fix any errors it reports.
7. **Append to `log.md`** using the format below, then commit: `document: <thing>`.
8. **Report back** with every file created or updated and any inconsistencies you couldn't resolve.

Log entry format:

```
## [2026-04-10] document | payments service
- created: services/payments.md, modules/payments-core.md, apis/payments-http.md
- updated: architecture/system.md
- adr: adrs/0008-stripe-over-adyen.md
```
