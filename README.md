# Scriptorium

Schemas for LLM-maintained markdown wikis. Each variant is a self-contained template you copy into a new wiki repo: an always-loaded `CLAUDE.md` core, on-demand `workflows/` procedures, and a stdlib-only lint tool (`lint.py` holds the variant's configuration; the `wikilint/` package holds the shared engine, byte-identical across variants) that handles every mechanical health check so the model only spends judgment where judgment is needed.

Every wiki produced from these templates is a conformant [Open Knowledge Format (OKF) v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) bundle, so it can be consumed by any OKF-aware agent or tool without translation.

## Where this sits in the OKF ecosystem

Most OKF tooling generates wikis: point a compiler at a codebase, a dataset, or a pile of documents and get a bundle. Scriptorium solves the other half of the problem, keeping a wiki true after week one. Its templates make an agent the accountable maintainer of the bundle: ownership rules, an append-only log, a commit per operation, and a deterministic linter that enforces freshness, contested-claim reconciliation, link integrity, and OKF conformance on every commit. Generated wikis are impressive on day one; these schemas are for knowledge that cannot be regenerated from a source of truth and has to still be right in month six.

One layering note when comparing bundles across producers: OKF reserves two filenames (`index.md`, `log.md`) and gives directory names no meaning. Folder taxonomies like `concepts/` or `synthesis/` here, or `tables/` and `references/` in Google's sample bundles, are producer conventions; the portable signal for consumers is the frontmatter `type` field.

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
- **If a rule can be a script, it is a script.** `lint.py check` covers frontmatter validation, broken links, orphans, dangling references, staleness, secrets, ADR integrity, index drift, log format, and OKF conformance. The LLM lint workflow keeps only what needs judgment: contradictions, stale claims, concept gaps.
- **Every relationship is stored once.** Pages declare their forward edges (`depends_on`, `defined_in`, `consumes`, `producers`, `consumers`, ...); `lint.py reverse-deps` derives the reverse map of every one of them. Agents reliably fail to keep hand-maintained symmetric fields consistent, so the schemas don't ask them to.
- **The index is a derived artifact.** Every page carries a one-line `description:`; `lint.py rebuild-index` generates `index.md` from frontmatter. Agents scan frontmatter first and open page bodies only on a hit.
- **Trust is structural, not remembered.** Immutable `raw/`, append-only `log.md`, a git commit per operation, a pre-commit hook that lints the staged snapshot (exactly the bytes that will land) and makes lint errors uncommittable, and commit-pinned verification fields. Agent-maintained judgment metadata decays, so `confidence:` is reduced to the two states a lint can actually check (`low` = uncited, `contested` = sources disagree and the body must explain), inferred claims are marked inline with `(inferred)`, and tags are validated against a `taxonomy.md`, whose `## Page types` section also describes every allowed page type with a one-line meaning, so each bundle self-describes its type vocabulary to OKF consumers.
- **Contested is a state to exit.** The documented failure mode of agent wikis is contradictions accumulating faster than they resolve. Lint flags contested pages older than 30 days; the reconcile workflow rewrites in place, moving losing claims to a dated "Superseded claims" section instead of deleting them.
- **Autonomous but reversible.** The maintenance workflow runs unattended on a `maintenance` branch with an exhaustively-listed set of safe actions (mechanical fixes, index rebuild, unambiguous cross-links); everything else becomes a proposal. The human reviews the branch diff and merges. Nothing automated ever lands on main directly.
- **Native OKF conformance.** Every wiki is an [OKF v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) bundle: markdown files with YAML frontmatter, ordinary markdown links as the edge form (bundle-absolute `[title](/dir/page.md)` preferred), reserved `index.md` (stamped with `okf_version` frontmatter by `rebuild-index`) and `log.md` (date-grouped headings, bold-action-word entries). `check_okf` enforces the spec's three conformance rules: parseable frontmatter on every non-reserved `.md`, a non-empty `type`, and reserved-file structure. Scriptorium's schemas are a strict superset of OKF's (its recommended `timestamp` field is our `updated`; its `resource` is our `source_path`; its `title` is optional, with the index prettifying filenames when absent). One deliberate deviation: `raw/` is excluded from conformance because prime directive 1 makes those sources immutable, and OKF has no concept of a non-concept directory.
- **Opt-in extension points for non-wiki trees.** The engine can also lint markdown trees that aren't wikis (a findings folder, a labs journal): `okf_conformance: False` turns off the OKF rules for trees that aren't bundles, `non_page_allowed` accepts glob patterns, `index_file`/`index_body_fn` relocate and reshape the generated index (`index_file: None` disables it), `extra_secret_patterns`/`secret_allow_res` extend the secrets scan, and `extra_checks` runs custom callables. Every knob's default lives once in `wikilint/settings.py` (`DEFAULTS`) and preserves the original behavior; a variant's `lint.py` lists a key only to override it. Bad values (a malformed regex, an out-of-tree `index_file`, a non-callable check) are rejected at startup with a clear message rather than a mid-run traceback.

## Unattended maintenance

Each variant ships a `workflows/maintain.md` pass designed for scheduled runs. Example with Claude Code on cron:

```sh
# nightly, from the wiki root
0 3 * * * cd ~/my-wiki && claude -p "maintenance pass" --permission-mode acceptEdits
```

The run commits to the `maintenance` branch only. Review with "review maintenance" in a normal session, then merge. If a run hits something outside its allowed actions (a secrets hit, an ambiguous fix), it leaves the tree uncommitted and reports the blocker instead.

## Deliberately not adopted

Vector search, typed links, knowledge-graph exports, and symbol-level AST anchoring. Flat files + markdown links + grep is the pattern that wins at these scales; the flat index ceiling (a few hundred pages) only bites in the large-codebase case, which shards by subsystem instead. Revisit if a wiki outgrows that.
