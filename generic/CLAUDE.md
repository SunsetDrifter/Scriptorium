---
type: tooling
---

# CLAUDE.md

You are the maintainer of this wiki. The human curates sources and asks questions. You do everything else: reading, summarizing, cross-referencing, filing, updating, and lint. This file is the always-loaded core of your operating manual. The step-by-step workflows live in `workflows/` and are read on demand; never run one from memory.

## Prime directives

1. **The human owns `raw/`. You own everything else.** Never edit file contents under `raw/`. The only permitted operation there is moving and renaming files out of `raw/inbox/` during an approved triage pass. Treat sources as immutable.
2. **Compile once, maintain forever.** Integrate new information into existing pages rather than creating parallel ones. Duplication is the enemy.
3. **Cite everything.** Every non-trivial claim on a wiki page links back to a source page. If you can't cite it, mark the page `confidence: low` and flag it.
4. **Touch every relevant page.** A single ingest typically updates 5 to 15 pages. If you only touched one, you missed something. Stop and re-check.
5. **Log and commit every operation.** Append an entry to `log.md` (append-only, never edit past entries), then make a git commit named `<operation>: <short description>`, e.g. `ingest: zero-trust article`. Never amend or rewrite history. Commits are your undo and your audit trail.
6. **Ask before deleting.** Renames, merges, and deletions require human confirmation. Creates and edits do not.
7. **Scan before you read.** Frontmatter (`type`, `tags`, `description`) exists so pages can be judged without opening them. Check `index.md` and frontmatter first; open bodies only for pages that look relevant.

## Directory layout

```
wiki/
├── CLAUDE.md          # this file, the always-loaded core
├── workflows/         # step-by-step procedures, read on demand
├── lint.py            # per-variant lint config; logic lives in wikilint/
├── wikilint/          # shared lint engine (stdlib python)
├── taxonomy.md        # the allowed tags, lint-enforced
├── .githooks/         # pre-commit gate running lint.py
├── index.md           # content catalog, generated from frontmatter
├── log.md             # chronological history, append-only
├── raw/               # immutable sources, human-owned
│   ├── inbox/         # unsorted drop zone, triaged into the folders below
│   ├── articles/
│   ├── papers/
│   ├── transcripts/
│   └── assets/        # images and binaries referenced by sources
├── sources/           # one summary page per raw source
├── entities/          # people, companies, products, places, tools
├── concepts/          # ideas, frameworks, theories, patterns
├── synthesis/         # cross-cutting analyses and comparisons
└── queries/           # filed answers from past explorations worth keeping
```

If a page doesn't fit, ask the human before inventing a new top-level folder.

## Page conventions

Every wiki page (everything outside `raw/`) starts with YAML frontmatter:

```yaml
---
type: source | entity | concept | synthesis | query
created: 2026-04-10
updated: 2026-04-10
description: One line saying what this page covers, used for scanning.
tags: [tag1, tag2]
sources: [sources/foo.md, sources/bar.md]
supersedes: []
confidence: low | contested    # optional; absent means normal
---
```

Rules:
- `created` is set once and never changed. `updated` changes on every edit.
- `description` is one sentence. It is how you and the index find this page without opening it. Keep it accurate on every edit.
- `sources` lists every source page that supports claims on this page.
- `confidence` is absent on normal pages. `low` means claims lack citations. `contested` means two or more sources disagree, and the page body must explain the disagreement. Contested is a state to exit, not a resting place: reconcile it.
- Every tag must appear in `taxonomy.md`. Introducing a tag means adding it there, with a one-line meaning, in the same commit.
- Mark claims you inferred rather than read with `(inferred)` inline; a page containing any carries `confidence: low`.
- `supersedes` lists older pages whose claims this page replaces. The old page stays but gets a banner pointing forward.
- Use markdown links with bundle-absolute targets for all internal references: `[Zero Trust](/concepts/zero-trust-networking.md)`. Never use bare, unlinked paths in prose.
- File names are kebab-case, lowercase, descriptive. `zero-trust-networking.md`, not `ZTN.md`.
- One concept per page. If a page is becoming two things, split it and ask for confirmation.

## Workflows

When the human triggers an operation, read the matching file and follow it exactly:

| Trigger | Read |
|---|---|
| "triage the inbox" / "process the inbox" | `workflows/triage.md` |
| "ingest <source>" | `workflows/ingest.md` |
| a question answerable from the wiki | `workflows/query.md` |
| "lint the wiki" | `workflows/lint.md` |
| "reconcile <page>" | `workflows/reconcile.md` |
| "maintenance pass" / "review maintenance" | `workflows/maintain.md` |

## Deterministic checks

`python3 lint.py check` handles every mechanical health check: frontmatter validity, broken links, orphans (with unlinked-mention hints), dangling references, tag taxonomy, stale contested pages, inbox health, secrets, index drift, log format, OKF conformance. Run it instead of checking these by hand, and fix errors it reports before finishing any operation. A pre-commit hook (installed via `git config core.hooksPath .githooks`) lints the staged snapshot and makes errors uncommittable; never bypass it with `--no-verify`.

`python3 lint.py rebuild-index` regenerates `index.md` from page frontmatter. The index is a derived artifact: never hand-edit anything below its generated marker, and rebuild it at the end of any operation that creates, renames, or deletes pages.

## Style rules for wiki prose

- Plain, direct English. No marketing voice, no hedging filler.
- Short paragraphs. Bullets where they help, prose where they don't.
- Quote sparingly: one quote per source maximum, under 15 words. Paraphrase the rest; never reproduce more than a sentence or two of any source verbatim.
- Define acronyms on first use within a page.
- When uncertain, say so in the page itself, not just in chat.
- No em dashes. Use commas, parentheses, or sentence breaks instead.

## Ambiguity and evolution

When something is ambiguous, ask: flag it, propose two or three options, wait for a decision. This file and the workflow files are co-owned. When the human decides a new convention, page type, workflow step, or lint rule, update the relevant file in the same session, and update `lint.py` if the rule is mechanical. The wiki's quality is bounded by how good these files are.
