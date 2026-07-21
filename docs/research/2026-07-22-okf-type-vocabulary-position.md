# Position: OKF's next gap is type semantics, and the fix is a glossary convention, not a vocabulary

Position note, 2026-07-22. Part analysis, part prediction; the falsifiable parts are dated and marked. Written as the evidence base for a possible upstream discussion issue.

## The observable facts

1. **OKF v0.1 standardizes syntax, not semantics.** The spec reserves two filenames, defines two link forms, and requires frontmatter with a non-empty `type`, described only as "a short string identifying the kind of concept" (SPEC §4). Directory names carry no meaning. Everything the spec pins down is parser-checkable.
2. **Producers are minting types freely and divergently.** Google's sample bundles use vendor strings (`BigQuery Table`, `BigQuery Dataset`, `Reference`); Scriptorium's variants use epistemic categories (`concept`, `synthesis`, `component`, `source`). Both are conformant. A consumer holding bundles from both has no field it can key on across them.
3. **The upstream PR queue is already applying semantic pressure** (checked 2026-07-20): PR #189 proposes agent-routing hint fields (producers telling consumers what a page is *for*); PR #195 proposes typed relationship edges (`supersedes`, `contested_by`); PR #159 proposes a `reliability` frontmatter axis. Different surfaces, same demand: meaning, not just shape.
4. **Tooling is already filling the semantic void by accident.** The reference visualizer hardcodes a node-color palette keyed to Google's type strings (`_TYPE_PALETTE` in `okf/src/reference_agent/viewer/generator.py`); every other producer's types render as the default gray. An unwritten de-facto type registry, discovered the same way the link-style gap was: by watching something render wrong.

## The historical pattern

Knowledge-interchange standards repeatedly hit this fork, with known outcomes:

- **Controlled vocabulary by committee** (RDF/OWL ontologies, Topic Maps): decades of alignment effort, minimal producer adoption. Semantics agreed in advance is ceremony, and ceremony kills adoption.
- **Registry with namespacing** (MIME types, RFC 6838): survives, but solves only collisions, not meaning.
- **Benevolent-dictator core vocabulary** (schema.org): survives because the vocabulary owner also owns the dominant consumer. A story about power, not interop.
- **Standardize nothing** (HTML `class`): survives; meaning accretes as voluntary convention (microformats). OKF `type` today is exactly this.

## The argument

Previous iterations of this problem assumed dumb-parser consumers, so meaning had to be pre-agreed: vocabularies, ontologies, registries. OKF's consumers are agents that read prose. A consumer handed a foreign bundle does not need `synthesis` pre-registered in a shared ontology; it needs one findable sentence saying what `synthesis` means in this bundle. The apparatus that required a standards body in the dumb-parser era collapses into a description line a model reads in passing.

Therefore the v0.2 ask should be a **place, not a vocabulary**: a reserved, conventional location where a bundle declares its own types (and, if typed edges land, its edge kinds) with a one-line meaning each. A reserved `types.md`, or a declared block in `index.md` frontmatter. Self-description keeps producer freedom, gives consumers something mechanical to fetch and something semantic to read, and lets the spec stay semantics-free while making semantics discoverable. The difference between legislating a language and requiring a glossary.

**Prior art in this repo:** `taxonomy.md` applies exactly this mechanism to tags. Every tag must appear there with a one-line meaning; lint enforces it (`check_tags` in `wikilint/checks.py`); introducing a tag means defining it in the same commit. The generalization from tags to types is mechanical, and Scriptorium could prototype it as a variant convention without any spec change.

## Predictions (falsifiable, 2026-07-22)

- If OKF v0.2 ships a controlled type vocabulary: adoption bifurcates within roughly a year. Asset-catalog bundles conform; wiki-style bundles ignore it; "OKF-conformant" stops naming one thing.
- If v0.2 ships a self-description convention (glossary file or frontmatter block): it holds the ecosystem together by converting divergence into documented local dialects.
- If v0.2 ships nothing on types: tooling defaults (starting with the reference visualizer's palette) harden into an unwritten registry, and the gap resurfaces as interop bugs rather than as a design discussion.

## Possible Scriptorium moves (recorded, not committed to)

1. Prototype the glossary convention locally: extend `taxonomy.md` (or add a sibling section) to cover page types with one-line meanings, lint-enforced. Zero spec dependency; becomes running code to cite upstream.
2. Open an upstream discussion issue proposing the self-description convention, citing this note's facts (§1–4) and the local prototype if built.
3. Do nothing until v0.2 signals a direction; keep §Predictions as the scorecard.

Per the project's scope rule, none of these proceed without a concrete decision.

## Sources

- OKF spec: https://raw.githubusercontent.com/GoogleCloudPlatform/knowledge-catalog/main/okf/SPEC.md (v0.1 Draft as of 2026-07-22)
- Upstream PRs (open as of 2026-07-20): #189 (agent-routing hints), #195 (typed relationship edges), #159 (reliability axis)
- Reference visualizer palette: `GoogleCloudPlatform/knowledge-catalog` `okf/src/reference_agent/viewer/generator.py` (`_TYPE_PALETTE`, pinned at commit `d44368c`)
- MIME type registration: RFC 6838
- This repo: `taxonomy.md` convention and its lint enforcement; `docs/research/2026-07-21-claude-md-vs-okf-reference-agent.md`
