# Operating manuals compared: Scriptorium's CLAUDE.md vs. the OKF reference agent

Research note, 2026-07-21. Question: how do Scriptorium's per-variant CLAUDE.md files compare to the agent Google ships with the OKF spec? All sources are public: `GoogleCloudPlatform/knowledge-catalog` (pinned at commit `d44368c`, 2026-06-20) and this repo. The reference agent's instructions live in two prompt files totaling 299 lines: `okf/src/reference_agent/prompts/reference_instruction.md` (84 lines, enrich one concept from source metadata) and `prompts/web_ingestion_instruction.md` (215 lines, crawl seed URLs and augment the bundle).

## Summary

The two encode different jobs. Google's prompts are a **production recipe**: inputs, workflow steps, output format, taste rules, executed per invocation by a stateless batch agent. Scriptorium's CLAUDE.md files are a **governance charter**: a resident maintainer with ownership boundaries, mechanical enforcement, and a lifecycle model. Both produce conformant OKF v0.1 bundles — which is the point of the spec — but they solve opposite halves of the knowledge problem: compilation vs. custody.

## Five structural differences

### 1. Compiler vs. custodian

The reference agent "enriches exactly one concept and finishes by calling `write_concept_doc` exactly once" (`reference_instruction.md:2-3`); the web-ingestion agent runs one budgeted crawl and stops. Neither has identity or obligations beyond the task. Every Scriptorium CLAUDE.md opens by making the agent *the maintainer* and derives everything from that: the human owns `raw/` and reality, the agent owns everything else (prime directive 1); every operation appends to `log.md` and commits ("commits are your undo and your audit trail", directive 6); deletions require confirmation (directive 7). The reference prompts contain no ownership model, no log, no confirmation gates, and nothing is immutable.

### 2. Where correctness lives

Google enforces quality by exhortation: "Do not invent fields, partitions, or shard counts" (`reference_instruction.md:80-81`), "Do not over-link" (line 72), "cite only sources you actually know" (line 51). Nothing verifies compliance — no linter runs in their loop (a `validate` subcommand exists only as open PR #125). Scriptorium's doctrine is the inverse, stated in every variant's `lint.py` docstring: "If a check can be a script, it belongs there, not in prose." Frontmatter validity, link resolution, staleness, secrets, taxonomy, index drift and OKF conformance are deterministic checks (`wikilint/checks.py`), gated by a pre-commit hook; CLAUDE.md carries only what cannot be mechanized. Their agent is trusted; Scriptorium's is verified.

### 3. Lifecycle and time

The reference prompts contain one temporal instruction: reuse an existing doc and "refine rather than rewrite" (`reference_instruction.md:7-8`). There is no staleness concept, no re-verification, no contested state. Defensible for their use case — docs compiled from BigQuery metadata are cheaply regenerable from a queryable source of truth. Scriptorium treats time as the primary threat, because its content (decisions, incidents, human statements) is *not* regenerable: `last_verified` staleness rules, `confidence: contested` as "a state to exit, not a resting place", and verify/reconcile workflows.

### 4. Context economics

Scriptorium uses progressive disclosure: a lint-capped CLAUDE.md core (`claude_md_max_lines`, e.g. 135 in `homelab/lint.py:26`) plus `workflows/*.md` read on demand, per trigger table. Google's prompts are flat — the whole instruction loads every invocation. At 84/215 lines that is fine, but it is small because the job is narrow, not because the design manages context.

### 5. Link style (the spec's live fault line)

`reference_instruction.md:68-69`: "Never start a link with `/` (that breaks GitHub rendering)" — the reference agent forbidding a form its own spec recommends (SPEC §5.1 at the pinned commit). Scriptorium takes the opposite position for agent-operability reasons ([ADR 0001](../adr/0001-bundle-absolute-links.md)). Upstream PR #165 resolves the three-way disagreement in the agent's favor by swapping the recommendation; the open question is whether consumers remain obligated to resolve both forms (see the discussion on that PR).

## Credit where due

The web-ingestion prompt contains the best judgment scaffolding in either system: a four-part test for minting a new reference page (`web_ingestion_instruction.md:37-70`) — topic shape, not-bundle-meta (with a URL-slug blocklist), a *citation test* ("you can plausibly write `See the [X reference](/references/x.md) for ...` where X is a concrete noun; if the best sentence is 'See the overview for context', it fails"), and a *reuse test* (≥2 citing concepts, or one load-bearing dependency). Capped by: "A bundle with zero `references/` docs is fine; a bundle full of `references/overview` ... is noise." This is a sharper page-worthiness heuristic than anything in Scriptorium's `document.md` workflows. Recorded as observation, not proposal, per this project's OKF-first scope.

## So what

This comparison substantiates Scriptorium's position in the post-OKF landscape: the ecosystem's reference implementation (and most of the tools tracking it) *compiles* knowledge; Scriptorium *keeps it true* — governed maintenance with deterministic enforcement, for knowledge that cannot be regenerated from a source of truth. That one-line contrast, with this doc as evidence, is the intended basis for a README positioning section.

## Sources

- `GoogleCloudPlatform/knowledge-catalog @ d44368c15e38e7c92481c5992e4f9b5b421a801d`: `okf/src/reference_agent/prompts/reference_instruction.md`, `okf/src/reference_agent/prompts/web_ingestion_instruction.md`, `okf/SPEC.md` §5
- Upstream PRs referenced: #165 (link recommendation swap), #125 (validate subcommand)
- This repo: `homelab/CLAUDE.md` (prime directives, workflow trigger table), `homelab/lint.py` (docstring, `claude_md_max_lines`), `wikilint/checks.py`, `docs/adr/0001-bundle-absolute-links.md`
