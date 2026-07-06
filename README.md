# Scriptorium

Schemas for LLM-maintained markdown wikis. Each variant is a self-contained template you copy into a new wiki repo: an always-loaded `CLAUDE.md` core, on-demand `workflows/` procedures, and a stdlib-only lint tool (`lint.py` holds the variant's configuration; the `wikilint/` package holds the shared engine, byte-identical across variants) that handles every mechanical health check so the model only spends judgment where judgment is needed.

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
git config core.hooksPath .githooks   # lint errors become uncommittable
mkdir -p raw/inbox
python3 lint.py check     # should pass on the empty wiki
```

Then open the wiki in Claude Code (or any agent that reads `CLAUDE.md`) and drop sources into `raw/inbox/`. If the wiki is hosted, also run `python3 lint.py check` in CI so the gate holds for every clone.

## Design

The schemas follow a few rules, informed by how agent-maintained wikis actually fail:

- **Hot/cold split.** `CLAUDE.md` stays around a hundred lines (directives, layout, frontmatter schemas, a dispatch table). Step-by-step workflows live in `workflows/` and are read when triggered. Always-loaded context is a cost paid on every turn; verbose context files measurably hurt.
- **If a rule can be a script, it is a script.** `lint.py check` covers frontmatter validation, broken wikilinks, orphans, dangling references, staleness, secrets, ADR integrity, index drift, and log format. The LLM lint workflow keeps only what needs judgment: contradictions, stale claims, concept gaps.
- **Every relationship is stored once.** Pages declare their forward edges (`depends_on`, `defined_in`, `consumes`, `producers`, `consumers`, ...); `lint.py reverse-deps` derives the reverse map of every one of them. Agents reliably fail to keep hand-maintained symmetric fields consistent, so the schemas don't ask them to.
- **The index is a derived artifact.** Every page carries a one-line `description:`; `lint.py rebuild-index` generates `index.md` from frontmatter. Agents scan frontmatter first and open page bodies only on a hit.
- **Trust is structural, not remembered.** Immutable `raw/`, append-only `log.md`, a git commit per operation, a pre-commit hook that lints the staged snapshot (exactly the bytes that will land) and makes lint errors uncommittable, and commit-pinned verification fields. Agent-maintained judgment metadata decays, so `confidence:` is reduced to the two states a lint can actually check (`low` = uncited, `contested` = sources disagree and the body must explain), inferred claims are marked inline with `(inferred)`, and tags are validated against a `taxonomy.md`.
- **Contested is a state to exit.** The documented failure mode of agent wikis is contradictions accumulating faster than they resolve. Lint flags contested pages older than 30 days; the reconcile workflow rewrites in place, moving losing claims to a dated "Superseded claims" section instead of deleting them.
- **Autonomous but reversible.** The maintenance workflow runs unattended on a `maintenance` branch with an exhaustively-listed set of safe actions (mechanical fixes, index rebuild, unambiguous cross-links); everything else becomes a proposal. The human reviews the branch diff and merges. Nothing automated ever lands on main directly.
- **Opt-in extension points for non-wiki trees.** The engine can also lint markdown trees that aren't wikis (a findings folder, a labs journal): `markdown_links` checks relative `[text](file.md)` links, `non_page_allowed` accepts glob patterns, `index_file`/`index_body_fn` relocate and reshape the generated index, `extra_secret_patterns`/`secret_allow_res` extend the secrets scan, and `extra_checks` runs custom callables. Every knob defaults to the original behavior; each variant's `lint.py` documents them.

## Unattended maintenance

Each variant ships a `workflows/maintain.md` pass designed for scheduled runs. Example with Claude Code on cron:

```sh
# nightly, from the wiki root
0 3 * * * cd ~/my-wiki && claude -p "maintenance pass" --permission-mode acceptEdits
```

The run commits to the `maintenance` branch only. Review with "review maintenance" in a normal session, then merge. If a run hits something outside its allowed actions (a secrets hit, an ambiguous fix), it leaves the tree uncommitted and reports the blocker instead.

## Deliberately not adopted

Vector search, typed links, knowledge-graph exports, and symbol-level AST anchoring. Flat files + wikilinks + grep is the pattern that wins at these scales; the flat index ceiling (a few hundred pages) only bites in the large-codebase case, which shards by subsystem instead. Revisit if a wiki outgrows that.
