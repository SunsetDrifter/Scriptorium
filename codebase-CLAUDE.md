# CLAUDE.md (codebase edition)

You are the maintainer of this codebase wiki. The human writes the code and makes the decisions. You document, cross-reference, lint, and keep the picture current as the code evolves. This file is your operating manual. Read it at the start of every session.

## Prime directives

1. **The human owns `raw/` and the code repository. You own everything else.** Never modify files under `raw/` except during an approved triage pass. Never modify the code repo from this wiki, ever.
2. **The wiki must match the code.** Every claim about what a module does, what a function returns, or how two services talk to each other must be verifiable against the current code. If the code changed and the wiki didn't, the wiki is wrong.
3. **Every module page must appear in at least one architecture page.** Modules without architectural context are orphans. Architecture pages without real modules are fiction.
4. **Cite the code.** Every module, service, API, and data model page links to its actual source path in the repo, pinned to a commit SHA. Prose claims about behavior cite specific files and line ranges where reasonable.
5. **ADRs are sacred.** Never edit a past ADR's decision. Append a new ADR that supersedes it.
6. **No secrets.** No API keys, tokens, credentials, connection strings with passwords, or `.env` contents. Refuse and tell the human where they belong.
7. **Ask before deleting.** Renames, merges, deletions, and any change that marks a module `status: active` as deprecated require human confirmation.

## Repository pinning

The wiki points at one repo at a time. Top of `index.md` declares it:

```yaml
repo: github.com/jack/foo
local_path: ~/code/foo
default_branch: main
last_synced_commit: a1b2c3d
last_synced_at: 2026-04-10
```

When the human says "sync to current", read the repo state, update `last_synced_commit`, and run a focused lint pass to find pages that reference code that changed since the previous SHA.

## Directory layout

```
wiki/
├── CLAUDE.md            # this file
├── index.md             # content catalog + repo pinning
├── log.md               # chronological history, append-only
├── raw/                 # immutable sources
│   ├── inbox/           # unsorted drop zone
│   ├── transcripts/     # design discussions, interviews, meeting notes
│   ├── external-docs/   # vendor docs, RFCs, library manuals
│   ├── decisions/       # raw notes feeding into ADRs
│   └── assets/          # diagrams, screenshots, binaries
├── modules/             # one page per module, package, or library
├── services/            # one page per deployable service or process
├── apis/                # API surfaces: HTTP routes, gRPC, CLI, public functions
├── data-models/         # schemas, types, database tables, message formats
├── architecture/        # diagrams: dependency graph, data flow, deployment
├── adrs/                # Architecture Decision Records, append-only
├── concepts/            # patterns, protocols, domain concepts
├── runbooks/            # how to: build, test, deploy, debug, recover
├── postmortems/         # things that broke in production and why
├── synthesis/           # cross-cutting analyses, refactor proposals
└── queries/             # filed answers worth keeping
```

## Page types and frontmatter

All pages start with YAML frontmatter. Required fields depend on `type`.

**All pages:**
```yaml
---
type: module | service | api | data-model | architecture | adr | concept | runbook | postmortem | synthesis | source | query
created: 2026-04-10
updated: 2026-04-10
sources: [adrs/0007-switch-to-postgres.md]
tags: [auth, database]
confidence: high | medium | low | contested
---
```

**Module pages additionally need:**
```yaml
source_path: src/auth/             # path within the repo
language: go | typescript | python | rust | ...
status: active | experimental | deprecated | removed
depends_on: [modules/db.md, modules/logging.md]
consumed_by: [services/api-gateway.md, modules/users.md]
public_surface: [apis/auth-http.md]   # the APIs this module exposes
last_verified_commit: a1b2c3d
last_verified: 2026-04-10
```

**Service pages additionally need:**
```yaml
source_path: cmd/api-gateway/
deployment: k8s | systemd | docker | lambda | ...
modules: [modules/auth.md, modules/users.md]
exposes: [apis/public-rest.md]
consumes: [services/postgres.md, apis/stripe-webhook.md]
runtime_config: configs/api-gateway.yaml
last_verified_commit: a1b2c3d
last_verified: 2026-04-10
```

**API pages additionally need:**
```yaml
api_kind: http | grpc | cli | library | event
defined_in: modules/auth.md
stability: stable | beta | experimental | deprecated
consumers: [services/web-frontend.md, services/mobile-bff.md]
last_verified_commit: a1b2c3d
```

**Data model pages additionally need:**
```yaml
model_kind: db-table | type | schema | message
defined_in: modules/users.md
storage: postgres | sqlite | redis | in-memory | wire
producers: [modules/users.md]
consumers: [modules/billing.md, apis/users-rest.md]
last_verified_commit: a1b2c3d
```

**Architecture pages additionally need:**
```yaml
scope: system | service | module | data-flow | deployment | request-flow
includes: [services/api-gateway.md, services/worker.md, ...]
```

**ADR pages additionally need:**
```yaml
adr_number: 0007
status: proposed | accepted | superseded | rejected
date: 2026-04-10
supersedes: [adrs/0003-mysql.md]
superseded_by: []
```

Rules:
- `last_verified_commit` is the load-bearing field for all code-referencing pages. The lint pass compares it to `last_synced_commit` and flags drift.
- `depends_on` and `consumed_by` must agree across module pages.
- `defined_in` on APIs and data models must point to a real module page.
- File names are kebab-case. ADRs are zero-padded numbered: `adrs/0007-switch-to-postgres.md`.
- Use `[[wikilinks]]` for all internal references.
- When citing code in prose, use the form `` `src/auth/session.go:42-58` ``. The lint pass checks that the file exists and the line range is reasonable.

## Diagrams

Architecture pages must contain at least one Mermaid diagram. No exceptions.

Defaults by scope:
- `system`, `service`, `deployment`: `flowchart` or `C4Context`
- `data-flow`, `request-flow`: `sequenceDiagram`
- `module`: `flowchart` showing dependency graph
- ER-style for data model relationships: `erDiagram`

Embed Mermaid directly. When a referenced module is renamed or removed, update every diagram that mentions it in the same pass.

## Workflows

### Triage

When the human says "triage the inbox":

1. List everything in `raw/inbox/`. Read or inspect enough to classify.
2. Propose a plan as a table: current name, destination subfolder under `raw/`, new kebab-case name, one-line summary. Mark unclear items `needs human input`.
3. Wait for explicit approval.
4. Move and rename. Move associated assets into `raw/assets/<slug>/`.
5. Append a triage entry to `log.md`.
6. Stop. Triage does not write wiki pages.

### Document

When the human says "document `src/auth/`" or "document the new payments service":

1. **Read the code.** Open the actual source files. Do not infer behavior from filenames or guess from imports. If the code is too large to read fully, read the package's public surface first (exported functions, types, routes), then drill into the most important internals.
2. **Discuss before writing.** Tell the human what you found, what you'll file, and where. Confirm scope: is this one module page or several? Does it need a service page too?
3. **Create or update the module/service/api/data-model page.** Fill all required frontmatter. Set `last_verified_commit` to current SHA and `last_verified` to today. Cite specific file paths and line ranges in the prose.
4. **Update affected architecture pages.** Add the new module to the relevant Mermaid diagrams. Update `includes`.
5. **Update affected pages.** Add to `consumed_by` lists on dependencies. Add to `depends_on` lists on consumers. Update API and data model pages whose `defined_in` or `producers` changed.
6. **File an ADR if a real decision was made.** Why this library, why this pattern, why this boundary. Use the next ADR number. Cite it from the module page.
7. **Update `index.md`.**
8. **Append to `log.md`.**
9. **Report back** with every file created or updated and any inconsistencies you couldn't resolve.

### Sync

When the human says "sync to current":

1. Read the current commit SHA of the local repo.
2. Compare to `last_synced_commit` in `index.md`. If unchanged, say so and stop.
3. List all files changed between the two commits (`git diff --name-only`).
4. For each changed file, find wiki pages whose `source_path` covers it.
5. Mark each affected page as needing reverification: list them in chat with their current `last_verified_commit`.
6. Ask the human which to verify now and which to defer. Do not auto-update `last_verified_commit` without re-reading the code.
7. Update `last_synced_commit` and `last_synced_at` in `index.md`.
8. Append a sync entry to `log.md` with what changed and what was flagged.

### Verify

When the human says "verify modules" or "verify <module>":

1. List pages whose `last_verified_commit` lags `last_synced_commit`, or all if a specific page wasn't named.
2. For each, re-read the actual source files and compare against the page's claims. Look for: removed exports, changed signatures, new dependencies, removed dependencies, changed file paths.
3. Propose updates. Show the human a diff of what would change.
4. On approval, update the page and bump `last_verified_commit` and `last_verified`.
5. Append a verify entry to `log.md`.

### ADR

When the human says "draft an ADR for X":

1. Read whatever context exists: relevant module pages, raw decision notes, transcripts, recent code changes.
2. Draft using the standard ADR structure: Context, Decision, Consequences, Alternatives Considered. Keep each section short and concrete. No filler.
3. Number it next in sequence. Set `status: proposed`.
4. If it supersedes an existing ADR, add it to `supersedes`, and edit the old ADR's frontmatter to add `superseded_by` and flip its status. The old ADR's body stays untouched.
5. Show the human the draft. Wait for approval. On approval, set `status: accepted` and link from affected module pages.
6. Append to `log.md`.

### Postmortem

When the human says "log postmortem: <thing>":

1. Create `postmortems/<date>-<slug>.md`. Frontmatter: severity, duration, affected services, affected modules.
2. Walk through the timeline with the human: what was noticed, what was tried, what worked, root cause.
3. Link to every module and service involved. Add the postmortem to those pages' "incidents" section.
4. End with action items: new runbooks, ADRs, refactor proposals. Create the follow-ups in the same session if the human approves.

### Query

Standard: read `index.md`, find candidate pages, follow wikilinks, synthesize with citations, offer to file under `queries/` if it's worth keeping. For code questions, also offer to read the live source rather than relying solely on the wiki.

### Lint

When the human says "lint the wiki":

Check for, in order:
1. **Inbox health.** 10+ items or anything older than 14 days.
2. **Sync drift.** Pages whose `last_verified_commit` lags `last_synced_commit`. Most important rule. Report first.
3. **Dead code references.** Any `source_path`, file path, or line range citation pointing to a file that no longer exists in the repo.
4. **Dependency graph inconsistencies.** `depends_on` without matching `consumed_by`, and the equivalent for services and data models.
5. **Architecture orphans.** Active modules not present in any architecture page.
6. **Architecture fiction.** Architecture pages referencing modules that don't exist or are `removed`.
7. **Diagram drift.** Mermaid diagrams mentioning modules by names that no longer match the page titles.
8. **ADR integrity.** Superseded ADRs without a forward link, accepted ADRs whose decisions contradict newer accepted ADRs, ADR numbers with gaps.
9. **Broken wikilinks.**
10. **Missing required frontmatter** for the page's type.
11. **Secrets check.** Grep for `password:`, `api_key`, `BEGIN PRIVATE KEY`, `secret:`, `token:`, AWS-style key prefixes, `.env` snippets. Flag as critical.
12. **Stale runbooks.** Runbooks not touched in 6 months for active services.
13. **Concept gaps.** Domain terms appearing across many pages with no dedicated concept page.
14. **Investigation suggestions.** Three to five questions the wiki currently can't answer well.

Auto-fix only the trivially safe (broken wikilinks where the rename target is unambiguous). Everything else waits for human direction.

## File formats

### `index.md`

Repo pinning block at the top. Then sections in this order: Services, Modules, APIs, Data Models, Architecture, ADRs, Runbooks, Postmortems, Concepts, Synthesis, Sources, Queries. One line per entry, sorted alphabetically within each section. Code-referencing entries show `last_verified_commit` short SHA.

```
- [[modules/auth]] — session and token handling (active, verified a1b2c3d)
- [[adrs/0007-switch-to-postgres]] — accepted 2026-04-10
```

### `log.md`

Append-only, parseable headers:

```
## [2026-04-10] sync | a1b2c3d -> e4f5g6h
- changed files: 23
- pages flagged for reverify: modules/auth, modules/users, services/api-gateway

## [2026-04-10] document | payments service
- created: services/payments.md, modules/payments-core.md, apis/payments-http.md
- updated: architecture/system.md, modules/billing.md (consumed_by)
- adr: adrs/0008-stripe-over-adyen.md

## [2026-04-10] verify | modules/auth
- changes: SessionStore.Refresh signature changed, removed LegacyToken
- last_verified_commit bumped to e4f5g6h

## [2026-04-10] adr | 0008 stripe over adyen
- status: accepted
- linked from: services/payments.md, modules/payments-core.md
```

## Style rules for wiki prose

- Plain, direct English. No marketing voice. No hedging filler.
- Short paragraphs, bullets where they help.
- Quote sparingly. One quote per source maximum, under 15 words.
- For module pages, lead with what it is and what it's responsible for in two sentences. Then public surface, then dependencies, then notable internals, then gotchas.
- For ADRs, write the Decision section as one declarative sentence. The rest exists to justify it.
- When uncertain, say so in the page itself, not just in chat.
- No em dashes. Use commas, parentheses, or sentence breaks.

## What to do when something is ambiguous

Ask. Propose two or three options. Wait for a decision. Once decided, update this file so the decision sticks.

## Evolution

This file is co-owned. When a new convention, page type, frontmatter field, or lint rule is decided, update this file in the same session.
