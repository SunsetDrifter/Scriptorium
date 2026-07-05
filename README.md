# Scriptorium

Schemas for LLM-maintained markdown wikis. Each variant is a self-contained template you copy into a new wiki repo: an always-loaded `CLAUDE.md` core, on-demand `workflows/` procedures, and a stdlib-only `lint.py` that handles every mechanical health check so the model only spends judgment where judgment is needed.

## Variants

| Variant | For | Distinctive machinery |
|---|---|---|
| `generic/` | Reading notes, research, any source-driven knowledge base | sources / entities / concepts / synthesis / queries |
| `homelab/` | Home infrastructure documentation | component pages, topology diagrams, `last_verified` reality checks, incidents, runbooks |
| `codebase/` | A single repo, one or a few owners | commit-pinned pages, sync/verify loop, ADRs, postmortems |
| `codebase-large/` | 200k+ lines, multiple services and owners | subsystem sharding, criticality-weighted verification, owner review, coverage reports |

## Install

```sh
mkdir my-wiki && cd my-wiki && git init
cp -r path/to/Scriptorium/<variant>/ .
mkdir -p raw/inbox
python3 lint.py check     # should pass on the empty wiki
```

Then open the wiki in Claude Code (or any agent that reads `CLAUDE.md`) and drop sources into `raw/inbox/`.

## Design

The schemas follow a few rules, informed by how agent-maintained wikis actually fail:

- **Hot/cold split.** `CLAUDE.md` stays around a hundred lines (directives, layout, frontmatter schemas, a dispatch table). Step-by-step workflows live in `workflows/` and are read when triggered. Always-loaded context is a cost paid on every turn; verbose context files measurably hurt.
- **If a rule can be a script, it is a script.** `lint.py check` covers frontmatter validation, broken wikilinks, orphans, dangling references, staleness, secrets, ADR integrity, index drift, and log format. The LLM lint workflow keeps only what needs judgment: contradictions, stale claims, concept gaps.
- **Every relationship is stored once.** Pages declare their forward edges (`depends_on`, `defined_in`, `consumes`); reverse views are derived by `lint.py reverse-deps`. Agents reliably fail to keep hand-maintained symmetric fields consistent, so the schemas don't ask them to.
- **The index is a derived artifact.** Every page carries a one-line `description:`; `lint.py rebuild-index` generates `index.md` from frontmatter. Agents scan frontmatter first and open page bodies only on a hit.
- **Trust is structural, not remembered.** Immutable `raw/`, append-only `log.md`, a git commit per operation, and commit-pinned verification fields. Agent-maintained judgment metadata decays, so `confidence:` is reduced to the two states a lint can actually check (`low` = uncited, `contested` = sources disagree and the body must explain).

## Deliberately not adopted

Vector search, typed links, knowledge-graph exports, and symbol-level AST anchoring. Flat files + wikilinks + grep is the pattern that wins at these scales; the flat index ceiling (a few hundred pages) only bites in the large-codebase case, which shards by subsystem instead. Revisit if a wiki outgrows that.
