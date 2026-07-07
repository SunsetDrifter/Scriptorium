#!/usr/bin/env python3
"""Deterministic lint for this wiki (codebase variant). Stdlib only; run from
the wiki root. Subcommands: check | rebuild-index | reverse-deps | coverage.

This file holds ONLY the per-variant configuration. All logic lives in the
adjacent wikilint/ package, which is byte-identical across variants so fixes
propagate by copy. If a check can be a script, it belongs there, not in prose.
"""

CONFIG = {
    # Directories containing wiki pages, relative to the wiki root.
    "page_dirs": [
        "modules", "services", "apis", "data-models", "architecture",
        "adrs", "concepts", "runbooks", "postmortems", "synthesis", "queries",
    ],
    # Top-level entries that are allowed to exist but are not wiki pages.
    "non_page_allowed": [
        "CLAUDE.md", "index.md", "log.md", "lint.py", "wikilint", "taxonomy.md", "raw", "workflows",
        ".git", ".gitignore", ".githooks",
    ],
    "raw_dir": "raw",
    "inbox_dir": "raw/inbox",
    "inbox_warn_count": 10,
    "inbox_warn_age_days": 14,
    # Hot-core size guard: warn when CLAUDE.md exceeds this many lines.
    "claude_md_max_lines": 130,
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
    # Every active module must appear in at least one architecture page.
    "membership": {
        "member_type": "module",
        "active_statuses": ["active"],
        "container_type": "architecture",
        "container_field": "includes",
    },
    # Frontmatter required on every page.
    "required_fields": ["type", "created", "updated", "description", "tags"],
    # type -> extra required fields for that type.
    "type_required": {
        "module": [
            "source_path", "language", "status",
            "last_verified_commit", "last_verified",
        ],
        "service": [
            "source_path", "deployment",
            "last_verified_commit", "last_verified",
        ],
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
        },
        "api": {
            "api_kind": ["http", "grpc", "cli", "library", "event"],
            "stability": ["stable", "beta", "experimental", "deprecated"],
        },
        "data-model": {
            "model_kind": ["db-table", "type", "schema", "message"],
        },
        "architecture": {
            "scope": [
                "system", "service", "module",
                "data-flow", "deployment", "request-flow",
            ],
        },
        "adr": {
            "status": ["proposed", "accepted", "superseded", "rejected"],
        },
    },
    # Frontmatter fields whose values are wiki paths that must exist.
    "path_fields": [
        "sources", "includes", "defined_in", "modules", "exposes",
        "consumes", "producers", "consumers", "supersedes", "superseded_by",
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
    "criticality_field": None,
    # Page types that must contain at least one ```mermaid block.
    "mermaid_required_types": ["architecture"],
    "mermaid_node_warn": None,
    "mermaid_node_error": None,
    # Directories holding numbered ADRs (NNNN-slug.md). Empty disables.
    "adr_dirs": ["adrs"],
    # Index generation.
    "index_mode": "flat",           # "flat" | "subsystems"
    "index_link_style": "path",     # "stem" -> [[page-name]], "path" -> [[dir/page-name]]
    "index_sections": [
        ("Services", ["service"]),
        ("Modules", ["module"]),
        ("APIs", ["api"]),
        ("Data Models", ["data-model"]),
        ("Architecture", ["architecture"]),
        ("ADRs", ["adr"]),
        ("Runbooks", ["runbook"]),
        ("Postmortems", ["postmortem"]),
        ("Concepts", ["concept"]),
        ("Synthesis", ["synthesis"]),
        ("Queries", ["query"]),
    ],
    # Owner review staleness in days (large variant). None disables.
    "owner_review_max_days": None,
    # Coverage report (large variant only).
    "coverage": False,
    # Engine extension points (markdown_links, orphans, index_file,
    # index_body_fn, iso_date_fields, extra_secret_patterns, secret_allow_res,
    # log_file, extra_checks) default to original wiki behavior in
    # wikilint/settings.py DEFAULTS. Add a key here only to override one, e.g.
    # to lint a non-wiki markdown tree.
}


def index_entry_extra(fields):
    """Trailing annotation for an index entry, by page type."""
    ptype = fields.get("type")
    if ptype == "module":
        status = fields.get("status", "?")
        commit = fields.get("last_verified_commit", "?")
        return f"({status}, verified {commit})"
    if ptype in ("service", "api", "data-model"):
        commit = fields.get("last_verified_commit", "?")
        return f"(verified {commit})"
    if ptype == "adr":
        status = fields.get("status", "?")
        adr_date = fields.get("date", "?")
        return f"({status} {adr_date})"
    updated = fields.get("updated", "?")
    return f"(updated {updated})"


if __name__ == "__main__":
    import sys
    from wikilint import main
    sys.exit(main(CONFIG, index_entry_extra))
