# Designing a scientific-testing variant for Scriptorium

Research note, 2026-07-20. Question: how would a new schema for scientific testing look, and what would it add on top of the existing structure? Scope set by the maintainer: a domain-agnostic scientific-method core with first-class support for computational experiments; wet-lab-only machinery (samples, instruments) out of scope beyond noting it as an extension. Produced by a research agent against primary sources; the `run` page type and its CONFIG entry were revised after scope review to carry computational-reproducibility fields. **§8 (added same day) records the verdict: not built — read it before building anything from §3–5.**

## 1. Summary

Build a fifth variant, `science/` (working name), following the exact same template shape as `homelab/` and `codebase-large/`: a `CLAUDE.md` operating manual, `taxonomy.md`, `workflows/*.md`, and a `lint.py` holding only a `CONFIG` dict that imports the unmodified `wikilint/` engine. The variant borrows ISA's containment hierarchy (Investigation→Study→Assay, generalized here to `project`→`study`→`experiment`) for structure, OSF-style preregistration for a hypothesis-before-result discipline enforced by a status enum and lint-checked timestamp ordering, and FAIR's identifier/provenance principles for `dataset`/`analysis` pages. Almost everything needed is expressible in existing CONFIG mechanisms (`membership`, `type_enum_fields`, `edge_fields`, `staleness`, `adr_dirs`, `mermaid_required_types`); the genuinely new needs are (a) multiple independent membership rules (today's engine supports exactly one `member_type`↔`container_type` pair), (b) a preregistration-order check (a hypothesis's `preregistered_at` must precede its result's `analyzed_at`), and (c) modality-conditional required fields on runs — (b) and (c) are best added as `extra_checks` callables, no engine change required.

## 2. What the existing structure already provides

| Scientific-testing need | Existing mechanism | Citation |
|---|---|---|
| Every experiment belongs to a study (containment) | `membership` rule (currently one pair only) | `homelab/lint.py:34-39`, enforced in `check_membership` at `wikilint/checks.py:180-205` |
| Experiment/hypothesis status lifecycle (planned/running/completed/abandoned) | `type_enum_fields` | `homelab/lint.py:59-70`, `codebase-large/lint.py:68-89` |
| "tests_hypothesis" / "produces_dataset" relationships stored once, reverse derived | `edge_fields` + `reverse_fields`, derived in `derive_reverse_edges` | `codebase-large/lint.py:33-36,98`; `wikilint/derived.py:13-28` |
| Frontmatter path-valued fields (e.g. `dataset`, `protocol`) must resolve to real pages | `path_fields`, checked in `check_links_and_orphans` | `codebase-large/lint.py:91-95`; `wikilint/checks.py:126-146` |
| Results must be periodically re-verified / re-analyzed (staleness) | `staleness` rules (field, types, max_days, severity) | `homelab/lint.py:76-85`; check at `wikilint/checks.py:330-349` |
| Pre-registration-style decision records, numbered and superseded, never edited after the fact | `adr_dirs` + `check_adrs`/`check_adr_dir` (numbering gaps, `superseded_by` enforcement) | `codebase-large/lint.py:112-113`; `wikilint/checks.py:432-457` |
| Protocol/experiment diagrams (workflow, sample flow) required on certain page types | `mermaid_required_types`, size-limited by `mermaid_node_warn/error` | `codebase-large/lint.py:109-111`; check at `wikilint/checks.py:414-430` |
| Uncited/contested claims (low statistical power, disputed replication) | `enum_fields.confidence` (`low`/`contested`) + `check_contested_age` | `homelab/lint.py:53-57`; `wikilint/checks.py:258-273` |
| Verification-effort weighting by criticality (e.g. flagship vs. exploratory experiments) | `criticality_field` for weighted drift reporting | `codebase-large/lint.py:105-107` |
| Data provenance to raw instrument output / lab notebook scans | `raw/` immutable-source convention, unchanged across variants | `homelab/CLAUDE.md` prime directive 1; `README.md` design section |
| OKF conformance (parseable frontmatter, non-empty `type`, reserved files) | `okf_conformance` default `True`, `check_okf` | `wikilint/settings.py:20-22`; check at `wikilint/checks.py:504` |
| Non-wiki/lab-journal trees needing lint without full bundle structure | opt-in extension points (`index_file`, `non_page_allowed` globs, `extra_secret_patterns`) | `README.md` "Opt-in extension points" section; `wikilint/settings.py:19-41` |

(Paths are repo-relative; `wikilint/` paths refer to any variant's copy — the engine is byte-identical across variants.)

## 3. Proposed schema

Directory layout (mirrors `homelab/` and `codebase-large/` shape):

```
science-wiki/
├── CLAUDE.md
├── workflows/          # register.md, run.md, analyze.md, reconcile.md, maintain.md, query.md, lint.md
├── lint.py
├── wikilint/           # byte-identical engine, untouched
├── taxonomy.md
├── index.md  log.md
├── raw/inbox/  raw/instrument-exports/  raw/lab-notebook-scans/  raw/decisions/
├── projects/        # ISA "Investigation" — top-level research program
├── studies/         # ISA "Study" — a bounded piece of work under a project
├── hypotheses/      # OSF preregistration object — testable prediction, dated before results
├── protocols/       # reusable method description (SOP), versioned
├── experiments/     # ISA "Assay" — one execution of a protocol against a hypothesis
├── runs/            # a single trial/replicate of an experiment (optional finer grain)
├── datasets/        # FAIR-described data artifact produced by a run
├── analyses/        # statistical/computational treatment of one or more datasets
├── concepts/  synthesis/  sources/  queries/    # unchanged cross-cutting types
└── docs/adr/        # pre-registration-style decision records (methodology choices), numbered
```

Page types, required/optional frontmatter, and justification:

- **project** (`type: project`) — ISA Investigation. `required_fields` (shared): `type, created, updated, description, tags`. Extra: `owners`, `mission`. Justification: ISA "Investigation provides overall experimental context" (isa-specs).
- **study** (`type: study`) — ISA Study. Extra required: `design_type`, `factors` (list), `project` (path field, membership container). `design_type` and `factors` map directly to ISA Study's "Design Type" and "Factor Name/Type" ontology-annotated fields (isa-specs).
- **hypothesis** (`type: hypothesis`) — OSF preregistration object. Required: `status` (enum: `draft | preregistered | tested | supported | refuted | inconclusive`), `preregistered_at` (ISO date, set once, immutable once status leaves `draft`), `study` (path field), prediction stated in the body. Justification: COS/OSF preregistration requires "at least one confirmatory test... specified" before data collection, and a documented time-ordering of plan vs. result (cos.io). The `preregistered_at`-before-`analyzed_at` ordering is one check that needs `extra_checks` (§5).
- **protocol** (`type: protocol`) — SOP. Required: `version`, `status` (`draft|active|deprecated`). Justification: ISA associates Process nodes with "parameter values, performer, date" (isa-specs); a protocol page is the reusable template those processes instantiate. Reuses `codebase-large`'s status-enum pattern for stable-artifact tracking.
- **experiment** (`type: experiment`) — ISA Assay. Required: `status` (`planned|running|completed|aborted`), `protocol` (path field), `tests_hypothesis` (edge field, list of `hypotheses/*.md`), `measurement_type`, `technology_type` (free-text analogs of ISA's ontology-annotated Measurement Type / Technology Type — isa-specs), `study` (path field).
- **run** (`type: run`) — one trial/replicate of an experiment, and the carrier of computational reproducibility. *(Revised 2026-07-20 after scope review.)* Required: `experiment` (path field), `performed_at`, `performer`, `modality` (enum: `computational | physical | mixed`). Conditionally required when `modality` is `computational` or `mixed`: `code_version` (commit hash or tag of the code that ran), `parameters` (inline mapping, or a path into `raw/` for large parameter files), `environment` (lockfile path, container image digest, or equivalent pin), `seed` (RNG seed; explicit `none` if genuinely unseeded). Optional on all runs: `metrics` (mapping of named result values — kept in frontmatter so runs can be compared by scanning, per prime directive "scan before you read", `homelab/CLAUDE.md`). Physical runs may omit all of the computational pins. Justification: `performed_at`/`performer` mirror ISA's Process-node fields (isa-specs); the pins operationalize FAIR R1.2 ("detailed provenance" — go-fair.org) for the case where the "instrument" is code; the specific field set (commit, parameters, environment, seed) is prose reasoning from what is minimally sufficient to re-execute a computational run, not taken from a fetched standard — no additional standard was consulted for it.
- **dataset** (`type: dataset`) — Required: `produced_by` (edge field, path to run/experiment), `identifier` (globally unique, e.g. DOI/ARK/UUID), `license`, `storage_path` (pointer into `raw/` or external store). Justification: FAIR F1 ("globally unique and persistent identifier"), R1.1 ("clear and accessible data usage license") (go-fair.org). The producers/consumers edge pattern is reused from `codebase-large/lint.py:91-95`.
- **analysis** (`type: analysis`) — Required: `datasets` (path field, list), `method`, `preregistered` (bool: confirmatory vs. exploratory), `hypothesis` (path field), `analyzed_at` (ISO date, compared against the hypothesis's `preregistered_at` by the ordering check). Justification: COS's confirmatory/exploratory distinction as a lint-checkable boolean (cos.io).
- **concept / synthesis / source / query**: unchanged, taken as-is from `generic/` and `homelab/`.
- ADRs under `docs/adr/` for methodology decisions ("why this statistical test, why this sample size"), reusing `adr_dirs` numbering/`superseded_by` machinery verbatim — the repo's existing mechanism for decisions that must not be silently edited after the fact (`wikilint/checks.py:440-457`).

Edges: `edge_fields = ["depends_on", "tests_hypothesis", "produced_by"]`; reverse maps derived via `reverse_fields`, never stored — direct reuse of the repo's "every relationship stored once" rule (`README.md`; `wikilint/derived.py:13-28`).

## 4. Draft `lint.py` CONFIG

Draft for discussion, not a verified-working file — it was not executed against `wikilint`, and the `extra_checks` import paths are illustrative.

```python
#!/usr/bin/env python3
"""Deterministic lint for this wiki (science variant). Stdlib only; run from
the wiki root. Subcommands: check | rebuild-index | reverse-deps | coverage.

This file holds ONLY the per-variant configuration. All logic lives in the
adjacent wikilint/ package, which is byte-identical across variants so fixes
propagate by copy. If a check can be a script, it belongs there, not in prose.
"""

from science_checks import check_prereg_order, check_run_modality  # see §5

CONFIG = {
    "page_dirs": [
        "projects", "studies", "hypotheses", "protocols", "experiments",
        "runs", "datasets", "analyses", "concepts", "synthesis", "sources", "queries",
    ],
    "non_page_allowed": [
        "CLAUDE.md", "index.md", "log.md", "lint.py", "wikilint", "taxonomy.md",
        "raw", "workflows", "docs", ".git", ".gitignore", ".githooks",
    ],
    "raw_dir": "raw",
    "inbox_dir": "raw/inbox",
    "inbox_warn_count": 10,
    "inbox_warn_age_days": 14,
    "claude_md_max_lines": 140,
    "taxonomy_file": "taxonomy.md",
    "contested_max_days": 30,
    "reverse_fields": ["depends_on", "tests_hypothesis", "produced_by"],
    # NOTE: engine currently supports exactly one membership rule; project<->study
    # containment is the one enforced mechanically. Study<->experiment and
    # hypothesis<->study containment are covered by path_fields resolution plus
    # prose review (same ceiling codebase-large hits; see §5).
    "membership": {
        "member_type": "study",
        "active_statuses": ["active", "running", "completed"],
        "container_type": "project",
        "container_field": "studies",
    },
    "required_fields": ["type", "created", "updated", "description", "tags"],
    "type_required": {
        "project": ["owners", "mission"],
        "study": ["design_type", "factors", "project"],
        "hypothesis": ["status", "preregistered_at", "study"],
        "protocol": ["version", "status"],
        "experiment": ["status", "protocol", "tests_hypothesis", "study",
                       "measurement_type", "technology_type"],
        # Computational pins (code_version, parameters, environment, seed) are
        # conditionally required by modality via check_run_modality (§5) —
        # type_required cannot express per-modality requirements.
        "run": ["experiment", "performed_at", "performer", "modality"],
        "dataset": ["produced_by", "identifier", "license", "storage_path"],
        "analysis": ["datasets", "method", "preregistered", "hypothesis", "analyzed_at"],
        "concept": [], "synthesis": [], "source": [], "query": [],
    },
    "enum_fields": {
        "confidence": ["low", "contested"],
    },
    "type_enum_fields": {
        "hypothesis": {
            "status": ["draft", "preregistered", "tested",
                       "supported", "refuted", "inconclusive"],
        },
        "protocol": {
            "status": ["draft", "active", "deprecated"],
        },
        "experiment": {
            "status": ["planned", "running", "completed", "aborted"],
        },
        "run": {
            "modality": ["computational", "physical", "mixed"],
        },
        "study": {
            "design_type": ["observational", "controlled", "factorial",
                            "longitudinal", "replication"],
        },
    },
    "path_fields": [
        "study", "project", "protocol", "experiment", "datasets",
        "hypothesis", "sources",
    ],
    "edge_fields": ["depends_on", "tests_hypothesis", "produced_by"],
    "staleness": [
        {
            "field": "preregistered_at",
            "types": ["hypothesis"],
            "max_days": 180,
            "severity": "warning",
        },
    ],
    "sync_drift": None,
    "criticality_field": None,
    "mermaid_required_types": ["protocol"],
    "mermaid_node_warn": 25,
    "mermaid_node_error": 40,
    "adr_dirs": ["docs/adr"],
    "index_mode": "flat",
    "index_sections": [
        ("Projects", ["project"]),
        ("Studies", ["study"]),
        ("Hypotheses", ["hypothesis"]),
        ("Protocols", ["protocol"]),
        ("Experiments", ["experiment"]),
        ("Runs", ["run"]),
        ("Datasets", ["dataset"]),
        ("Analyses", ["analysis"]),
        ("Concepts", ["concept"]),
        ("Synthesis", ["synthesis"]),
        ("Sources", ["source"]),
        ("Queries", ["query"]),
    ],
    "owner_review_max_days": None,
    "coverage": False,
    # Engine extension points (see wikilint/settings.py DEFAULTS): okf_conformance
    # stays True; extra_checks adds the two checks CONFIG alone cannot express.
    "extra_checks": [check_prereg_order, check_run_modality],
}


def index_entry_extra(fields):
    ptype = fields.get("type")
    if ptype == "hypothesis":
        return f"({fields.get('status', '?')}, prereg {fields.get('preregistered_at', '?')})"
    if ptype == "experiment":
        return f"({fields.get('status', '?')})"
    if ptype == "run":
        return f"({fields.get('modality', '?')}, {fields.get('performed_at', '?')})"
    if ptype == "dataset":
        return f"({fields.get('identifier', '?')})"
    return f"(updated {fields.get('updated', '?')})"


if __name__ == "__main__":
    import sys
    from wikilint import main
    sys.exit(main(CONFIG, index_entry_extra))
```

## 5. What's genuinely new on top

1. **Preregistration-order check** — no existing check compares two date fields *across* an edge (hypothesis `preregistered_at` vs. the `analyzed_at` of any `analysis` page whose `hypothesis` field points at it). `staleness` only compares one page's own date field to "now." Needs an `extra_checks` callable `check_prereg_order(pages, report, root)`: iterate `analysis` pages, resolve `hypothesis`, error if `analyzed_at < preregistered_at` or the hypothesis is still `status: draft`. Fits the documented extension point exactly (`extra_checks` — "Callables(pages, report, root) run at the end of every check pass," `wikilint/settings.py:39-40`); no engine change, only a callable in the variant's own module.
2. **Modality-conditional required fields** *(added in the scope revision)* — `type_required` is unconditional per type, so "computational runs must carry `code_version`/`parameters`/`environment`/`seed`, physical runs need not" cannot be expressed in CONFIG. A second small `extra_checks` callable `check_run_modality` covers it: for pages with `type: run` and `modality` in `{computational, mixed}`, error on any missing pin. Same extension point, zero engine changes.
3. **Multiple membership rules** — the schema wants containment enforced at two or three levels (project⊇study, study⊇experiment, possibly study⊇hypothesis), but `CONFIG["membership"]` is a single dict and `check_membership` (`wikilint/checks.py:180-205`) reads one pair; `codebase-large` hits the same ceiling and disables it (`codebase-large/lint.py:39`). Options: (a) accept the ceiling — secondary containment is still mechanically half-checked via `path_fields` resolution — or (b) change `membership` to accept a list of rule-dicts, a small engine change shared by all variants. Recommend (a) for a first cut; revisit (b) only if orphaned experiments/hypotheses become a real problem.
4. Everything else in §3–4 (status enums, edges, staleness, mermaid, ADRs, path fields) is pure CONFIG.

## 6. External standards consulted

- **ISA model** (isa-tools/isa-specs) — adopted: the Investigation→Study→Assay containment hierarchy (mapped to project→study→experiment), Study's `design_type`/`factors`, Assay's `measurement_type`/`technology_type`, and the Process-node fields (`performer`, `date`) reused on `run`. Deliberately left out: ISA's full ontology-annotation machinery (accession-numbered controlled-vocabulary terms) and its Material/sample provenance DAG — Scriptorium's markdown-wiki model has no ontology-annotation datatype and no graph-of-materials tracking; free-text fields plus `taxonomy.md`-checked tags substitute. Wet-lab sample/instrument tracking is the natural future extension point if a lab variant is ever needed. Source: https://isa-specs.readthedocs.io/en/latest/isamodel.html
- **FAIR principles** (GO FAIR) — adopted: F1 (persistent identifier → `dataset.identifier`), R1.1 (license → `dataset.license`), R1.2 (provenance → `produced_by` edge plus the run's computational pins), F2/R1 (rich description → shared `description` field, already required repo-wide). Deliberately left out: A1.2 (authentication/authorization) and I1–I3 (formal knowledge-representation languages, qualified cross-references) — out of scope for a flat-file markdown wiki with no access-control layer or RDF-style typed links. Source: https://www.go-fair.org/fair-principles/
- **OSF/COS preregistration** — adopted: the hypothesis-before-data discipline as a `status` enum plus a `preregistered_at` date, and the confirmatory/exploratory split as `analysis.preregistered: bool`. Deliberately left out: OSF's "Transparent Changes" deviation-tracking artifact and formal registry submission — represented instead by the existing append-only `log.md` and ADR machinery. Source: https://www.cos.io/initiatives/prereg
- **Computational run pins** (`code_version`, `parameters`, `environment`, `seed`, `metrics`): no dedicated standard was fetched for these; they are justified as the minimal set sufficient to re-execute a run, under FAIR R1.2's provenance requirement. Stated explicitly rather than stretching for a citation.
- **schema.org/Dataset, DataCite**: not separately fetched; FAIR F1/R1.1 already cover the identifier/license fields they would motivate.

## 7. Sources

Repo files: `README.md`, `docs/adr/0001-bundle-absolute-links.md`, `homelab/CLAUDE.md`, `homelab/lint.py`, `codebase-large/CLAUDE.md`, `codebase-large/lint.py`, `homelab/wikilint/settings.py`, `homelab/wikilint/checks.py`, `homelab/wikilint/derived.py`.

External:
- ISA model: https://isa-specs.readthedocs.io/en/latest/isamodel.html
- FAIR principles: https://www.go-fair.org/fair-principles/
- OSF/COS preregistration: https://www.cos.io/initiatives/prereg
- OKF v0.1 spec: https://raw.githubusercontent.com/GoogleCloudPlatform/knowledge-catalog/main/okf/SPEC.md

## 8. Verdict

**Do not build the §3–5 science variant as drafted.** Evaluated 2026-07-20 against real-world testing practice, the schema over-types the disposable layer (per-run pages, status enums that cache live state, containment hierarchies nobody fills in) and under-serves the durable layer, where lighter mechanisms (supersession pairs, one-of required fields, a structured version field, a `schema` subcommand) would carry the actual value. Those stand as a recorded menu only.

**Maintainer decision (2026-07-20): no science variant, and no speculative engine extensions either.** Scriptorium's scope is tracking OKF conformance; it evolves when the OKF spec does, not by importing features ahead of need. Revisit only with a concrete in-scope need, or if a future OKF version standardizes something equivalent (e.g. the `reliability` axis proposed in upstream OKF PR #159).
