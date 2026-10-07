# Scriptorium

A schema for LLM-maintained markdown wikis. `wiki/` is a self-contained template you copy into a new wiki repo: an always-loaded `CLAUDE.md` core, on-demand `workflows/` procedures, and a stdlib-only lint tool (`lint.py` holds the configuration; the `wikilint/` package holds the engine) that handles every mechanical health check so the model only spends judgment where judgment is needed.

Every wiki produced from this template is a conformant [Open Knowledge Format (OKF) v0.2](https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md) bundle, so it can be consumed by any OKF-aware agent or tool without translation.

## Where this sits in the OKF ecosystem

Most OKF tooling generates wikis: point a compiler at a codebase, a dataset, or a pile of documents and get a bundle. Scriptorium solves the other half of the problem, keeping a wiki true after week one. Its template makes an agent the accountable maintainer of the bundle: ownership rules, an append-only log, a commit per operation, and a deterministic linter that enforces freshness, contested-claim reconciliation, link integrity, and OKF conformance on every commit. Generated wikis are impressive on day one; this schema is for knowledge that cannot be regenerated from a source of truth and has to still be right in month six.

One layering note when comparing bundles across producers: OKF reserves two filenames (`index.md`, `log.md`) and gives directory names no meaning. Folder taxonomies like `concepts/` or `synthesis/` here, or `tables/` and `references/` in Google's sample bundles, are producer conventions; the portable signal for consumers is the frontmatter `type` field.

## The template

`wiki/` organizes knowledge as sources / entities / concepts / synthesis / queries, fed from an immutable, human-owned `raw/` inbox. It suits reading notes, research, and any source-driven knowledge base.

## Install

```sh
mkdir my-wiki && cd my-wiki && git init
cp -r path/to/Scriptorium/wiki/ .
git config core.hooksPath .githooks   # lint errors become uncommittable
mkdir -p raw/inbox
python3 lint.py check     # should pass on the empty wiki
```

Then open the wiki in Claude Code (or any agent that reads `CLAUDE.md`) and drop sources into `raw/inbox/`. If the wiki is hosted, also run `python3 lint.py check` in CI so the gate holds for every clone.

## Design

The schema follows a few rules, informed by how agent-maintained wikis actually fail:

- **Hot/cold split.** `CLAUDE.md` stays around a hundred lines (directives, layout, frontmatter schemas, a dispatch table). Step-by-step workflows live in `workflows/` and are read when triggered. Always-loaded context is a cost paid on every turn; verbose context files measurably hurt.
- **If a rule can be a script, it is a script.** `lint.py check` covers frontmatter validation, broken links, orphans, dangling references, staleness, secrets, ADR integrity, index drift, log format, and OKF conformance. The LLM lint workflow keeps only what needs judgment: contradictions, stale claims, concept gaps.
- **Every relationship is stored once.** Pages declare their forward edges (`depends_on`, `defined_in`, `consumes`, `producers`, `consumers`, ...); `lint.py reverse-deps` derives the reverse map of every one of them. Agents reliably fail to keep hand-maintained symmetric fields consistent, so the schema doesn't ask them to.
- **Workflows double as skills.** Each workflow has a thin `.claude/skills/wiki-<name>/SKILL.md` wrapper, so `/wiki-triage`, `/wiki-document`, etc. dispatch deterministically in Claude Code (the prefix avoids collisions with globally installed skills). Wrappers contain no procedure text, only a pointer; `check_skills` makes wrapper/workflow drift a lint error.
- **The index is a derived artifact.** Every page carries a one-line `description:`; `lint.py rebuild-index` generates `index.md` from frontmatter. Agents scan frontmatter first and open page bodies only on a hit.
- **Trust is structural, not remembered.** Immutable `raw/`, append-only `log.md`, a git commit per operation, a pre-commit hook that lints the staged snapshot (exactly the bytes that will land) and makes lint errors uncommittable, and commit-pinned verification fields. Agent-maintained judgment metadata decays, so `confidence:` is reduced to the two states a lint can actually check (`low` = uncited, `contested` = sources disagree and the body must explain), inferred claims are marked inline with `(inferred)`, and tags are validated against a `taxonomy.md`, whose `## Page types` section also describes every allowed page type with a one-line meaning, so each bundle self-describes its type vocabulary to OKF consumers.
- **Contested is a state to exit.** The documented failure mode of agent wikis is contradictions accumulating faster than they resolve. Lint flags contested pages older than 30 days; the reconcile workflow rewrites in place, moving losing claims to a dated "Superseded claims" section instead of deleting them.
- **Autonomous but reversible.** The maintenance workflow runs unattended on a `maintenance` branch with an exhaustively-listed set of safe actions (mechanical fixes, index rebuild, unambiguous cross-links); everything else becomes a proposal. The human reviews the branch diff and merges. Nothing automated ever lands on main directly.
- **Native OKF conformance.** Every wiki is an [OKF v0.2](https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md) bundle: markdown files with YAML frontmatter, ordinary markdown links as the edge form (bundle-absolute `[title](/dir/page.md)`, the form v0.2 §6.1 recommends), reserved `index.md` (stamped with `okf_version` frontmatter by `rebuild-index`, the mechanism §12 specifies) and `log.md` (date-grouped headings, bold-action-word entries). `check_okf` enforces the spec's three conformance rules: parseable frontmatter on every non-reserved `.md`, a non-empty `type`, and reserved-file structure. Provenance uses the spec's `sources` shape (§5.1): mapping entries with a required `resource`, enforced by `check_sources`, with pre-0.2 string entries downgraded to warnings. Scriptorium's schema is a strict superset of OKF's (the spec's `generated.at` is our `updated`; its `resource` is our `source_path`; its `title` is optional, with the index prettifying filenames when absent). One deliberate deviation: `raw/` is excluded from conformance because prime directive 1 makes those sources immutable, and OKF has no concept of a non-concept directory.
- **Opt-in extension points for non-wiki trees.** The engine can also lint markdown trees that aren't wikis (a findings folder, a labs journal): `okf_conformance: False` turns off the OKF rules for trees that aren't bundles, `non_page_allowed` accepts glob patterns, `index_file`/`index_body_fn` relocate and reshape the generated index (`index_file: None` disables it), `extra_secret_patterns`/`secret_allow_res` extend the secrets scan, `extra_checks` runs custom callables, and `extra_commands` registers extra `lint.py <verb>` subcommands (`{verb: (callable(root) -> exit code, help)}`) which dispatch ahead of the wiki-root guard and appear in `lint.py help` alongside the engine's own verbs, so a wiki never has to intercept `argv` and end up with a second, partial usage string. Every knob's default lives once in `wikilint/settings.py` (`DEFAULTS`) and a wiki's `lint.py` lists a key only to override it. `DEFAULTS` covers *every* key the engine reads, in two documented tiers: `EXTENSION_DEFAULTS` (the extension points above) preserves the original wiki behavior, so a wiki written before an extension existed keeps behaving as it did; `CORE_DEFAULTS` (the schema knobs — page dirs, required fields, staleness, ADRs, mermaid, coverage, ...) defaults to the neutral/disabled value, so a default can only ever silence a check, never invent one. A minimal config is therefore a handful of lines rather than a full key list. Bad values (a malformed regex, an out-of-tree `index_file`, a non-callable check) are rejected at startup with a clear message rather than a mid-run traceback.

## Unattended maintenance

The template ships a `workflows/maintain.md` pass designed for scheduled runs. Example with Claude Code on cron:

```sh
# nightly, from the wiki root
0 3 * * * cd ~/my-wiki && claude -p "/wiki-maintain" --permission-mode acceptEdits
```

Two permission prerequisites, or the headless run blocks at its first `git` command (`acceptEdits` auto-approves edits, not Bash; field-tested 2026-07-22):

1. Add a `.claude/settings.json` to the wiki allowing exactly the commands the pass needs, and nothing destructive:

```json
{"permissions": {"allow": [
  "Bash(python3 lint.py:*)", "Bash(git status:*)", "Bash(git branch:*)",
  "Bash(git checkout:*)", "Bash(git add:*)", "Bash(git commit:*)",
  "Bash(git log:*)", "Bash(git diff:*)", "Bash(rg:*)", "Bash(grep:*)"
]}}
```

2. Trust the workspace (open the wiki in Claude Code interactively once and accept the trust dialog) — untrusted workspaces ignore project settings in headless runs. Alternatively, pass the same rules on the command line via `--allowedTools`, which needs no trust.

The run commits to the `maintenance` branch only. Review with "review maintenance" in a normal session, then merge. If a run hits something outside its allowed actions (a secrets hit, an ambiguous fix), it leaves the tree uncommitted and reports the blocker instead.

## Deliberately not adopted

Vector search, typed links, knowledge-graph exports, and symbol-level AST anchoring. Flat files + markdown links + grep is the pattern that wins at these scales; the flat index ceiling (a few hundred pages) is far away for the wikis this template targets. Revisit if a wiki outgrows that.
