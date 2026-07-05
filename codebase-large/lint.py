#!/usr/bin/env python3
"""Deterministic lint for this wiki (large codebase variant). Stdlib only; run from
the wiki root. Subcommands: check | rebuild-index | reverse-deps | coverage.

This file holds ONLY the per-variant configuration. All logic lives in the
adjacent wikilint/ package, which is byte-identical across variants so fixes
propagate by copy. If a check can be a script, it belongs there, not in prose.
"""

CONFIG = {
    # Directories containing wiki pages, relative to the wiki root.
    "page_dirs": [
        "subsystems", "adrs", "architecture", "concepts", "runbooks",
        "postmortems", "synthesis", "queries",
    ],
    # Top-level entries that are allowed to exist but are not wiki pages.
    "non_page_allowed": [
        "CLAUDE.md", "index.md", "log.md", "coverage.md", "glossary.md",
        "lint.py", "wikilint", "taxonomy.md", "raw", "workflows", ".git", ".gitignore", ".githooks",
    ],
    "raw_dir": "raw",
    "inbox_dir": "raw/inbox",
    "inbox_warn_count": 10,
    "inbox_warn_age_days": 14,
    # Hot-core size guard: warn when CLAUDE.md exceeds this many lines.
    "claude_md_max_lines": 145,
    # Every page tag must appear in this file (one `- tag — meaning` line each).
    "taxonomy_file": "taxonomy.md",
    # Contested pages untouched for this many days get flagged for reconcile.
    "contested_max_days": 30,
    # Fields whose derived reverse maps `reverse-deps` prints. Together these
    # cover every relationship the schema stores forward-only.
    "reverse_fields": [
        "depends_on", "defined_in", "modules", "exposes", "consumes",
        "producers", "consumers",
    ],
    # Architecture membership is per-subsystem judgment here (see lint.md
    # "Subsystem orphans"); the mechanical check is disabled.
    "membership": None,
    # Frontmatter required on every page.
    "required_fields": ["type", "created", "updated", "description", "tags", "subsystem"],
    # type -> extra required fields for that type.
    "type_required": {
        "subsystem": ["owners", "mission", "last_owner_review"],
        "owners": [],
        "module": [
            "source_path", "language", "status", "criticality",
            "last_verified_commit", "last_verified", "verification_method",
        ],
        "service": ["source_path", "deployment", "last_verified_commit", "last_verified"],
        "api": ["api_kind", "defined_in", "stability", "last_verified_commit"],
        "data-model": ["model_kind", "defined_in", "storage", "last_verified_commit"],
        "architecture": ["scope", "includes"],
        "adr": ["adr_number", "status", "date"],
        "concept": [],
        "runbook": [],
        "postmortem": [],
        "synthesis": [],
        "source": [],
        "query": [],
    },
    # Optional fields with a fixed value set. `confidence` is absent on
    # normal pages; only the two structurally checkable states exist.
    "enum_fields": {
        "confidence": ["low", "contested"],
    },
    # Per-type enum fields: type -> {field: [values]}.
    "type_enum_fields": {
        "module": {
            "status": ["active", "experimental", "deprecated", "removed"],
            "criticality": ["load-bearing", "important", "normal", "peripheral"],
            "verification_method": [
                "full", "spot-check", "signature-only", "declared-by-owner",
            ],
        },
        "api": {
            "api_kind": ["http", "grpc", "cli", "library", "event"],
            "stability": ["stable", "beta", "experimental", "deprecated"],
        },
        "data-model": {
            "model_kind": ["db-table", "type", "schema", "message"],
        },
        "architecture": {
            "scope": ["system", "service", "module", "data-flow", "deployment", "request-flow"],
        },
        "adr": {
            "status": ["proposed", "accepted", "superseded", "rejected"],
        },
    },
    # Frontmatter fields whose values are wiki paths that must exist.
    "path_fields": [
        "sources", "includes", "defined_in", "modules", "exposes", "consumes",
        "producers", "consumers", "supersedes", "superseded_by",
        "key_modules", "key_services", "key_adrs",
    ],
    # Fields that define dependency edges (stored once, on the depender).
    # The reverse map is derived, never stored.
    "edge_fields": ["depends_on"],
    # Staleness rules: each dict flags pages of the given types whose date
    # field is older than max_days. severity: "error" | "warning".
    "staleness": [],
    # Compare this commit field against `last_synced_commit` in the index
    # pinning block. None disables. Format: (field, [types]) or None.
    "sync_drift": ("last_verified_commit", ["module", "service", "api", "data-model"]),
    # Criticality field for weighted drift reporting (large variant). None
    # disables weighting.
    "criticality_field": "criticality",
    # Page types that must contain at least one ```mermaid block.
    "mermaid_required_types": ["architecture"],
    "mermaid_node_warn": 30,
    "mermaid_node_error": 50,
    # Directories holding numbered ADRs (NNNN-slug.md). Empty disables.
    "adr_dirs": ["adrs", "subsystems/*/adrs"],
    # Index generation. Subsystem mode lists subsystem READMEs first, then
    # only pages with `subsystem: global` in the sections below.
    "index_mode": "subsystems",     # "flat" | "subsystems"
    "index_link_style": "path",     # "stem" -> [[page-name]], "path" -> [[dir/page-name]]
    "index_sections": [
        ("ADRs", ["adr"]),
        ("Architecture", ["architecture"]),
        ("Concepts", ["concept"]),
        ("Runbooks", ["runbook"]),
        ("Postmortems", ["postmortem"]),
        ("Synthesis", ["synthesis"]),
        ("Queries", ["query"]),
    ],
    # Owner review staleness in days (large variant). None disables.
    "owner_review_max_days": 90,
    # Coverage report (large variant only).
    "coverage": True,
}


def index_entry_extra(fields):
    """Trailing annotation for an index entry, by page type."""
    ptype = fields.get("type")
    if ptype == "module":
        status = fields.get("status", "?")
        criticality = fields.get("criticality", "?")
        verified = fields.get("last_verified_commit", "?")
        return f"({status}/{criticality}, verified {verified})"
    if ptype in ("service", "api", "data-model"):
        return f"(verified {fields.get('last_verified_commit', '?')})"
    if ptype == "adr":
        return f"({fields.get('status', '?')} {fields.get('date', '?')})"
    return f"(updated {fields.get('updated', '?')})"


if __name__ == "__main__":
    import sys
    from wikilint import main
    sys.exit(main(CONFIG, index_entry_extra))
