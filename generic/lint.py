#!/usr/bin/env python3
"""Deterministic lint for this wiki (generic variant). Stdlib only; run from
the wiki root. Subcommands: check | rebuild-index | reverse-deps | coverage.

This file holds ONLY the per-variant configuration. All logic lives in the
adjacent wikilint/ package, which is byte-identical across variants so fixes
propagate by copy. If a check can be a script, it belongs there, not in prose.
"""

CONFIG = {
    # Directories containing wiki pages, relative to the wiki root.
    "page_dirs": ["sources", "entities", "concepts", "synthesis", "queries"],
    # Top-level entries that are allowed to exist but are not wiki pages.
    "non_page_allowed": [
        "CLAUDE.md", "index.md", "log.md", "lint.py", "wikilint", "taxonomy.md",
        "raw", "workflows", ".git", ".gitignore", ".githooks",
    ],
    "raw_dir": "raw",
    "inbox_dir": "raw/inbox",
    "inbox_warn_count": 10,
    "inbox_warn_age_days": 14,
    # Hot-core size guard: warn when CLAUDE.md exceeds this many lines.
    "claude_md_max_lines": 110,
    # Every page tag must appear in this file (one `- tag — meaning` line each).
    "taxonomy_file": "taxonomy.md",
    # Contested pages untouched for this many days get flagged for reconcile.
    "contested_max_days": 30,
    # Fields whose derived reverse maps `reverse-deps` prints.
    "reverse_fields": [],
    # Active members that must appear in a container page (None disables).
    "membership": None,
    # Frontmatter required on every page.
    "required_fields": ["type", "created", "updated", "description", "tags"],
    # type -> extra required fields for that type.
    "type_required": {
        "source": [],
        "entity": [],
        "concept": [],
        "synthesis": [],
        "query": [],
    },
    # Optional fields with a fixed value set. `confidence` is absent on
    # normal pages; only the two structurally checkable states exist.
    "enum_fields": {
        "confidence": ["low", "contested"],
    },
    # Per-type enum fields: type -> {field: [values]}.
    "type_enum_fields": {},
    # Frontmatter fields whose values are wiki paths that must exist.
    "path_fields": ["sources", "supersedes"],
    # Fields that define dependency edges (stored once, on the depender).
    # The reverse map is derived, never stored.
    "edge_fields": [],
    # Staleness rules: each dict flags pages of the given types whose date
    # field is older than max_days. severity: "error" | "warning".
    "staleness": [],
    # Compare this commit field against `last_synced_commit` in the index
    # pinning block. None disables. Format: (field, [types]) or None.
    "sync_drift": None,
    # Criticality field for weighted drift reporting (large variant). None
    # disables weighting.
    "criticality_field": None,
    # Page types that must contain at least one ```mermaid block.
    "mermaid_required_types": [],
    "mermaid_node_warn": None,
    "mermaid_node_error": None,
    # Directories holding numbered ADRs (NNNN-slug.md). Empty disables.
    "adr_dirs": [],
    # Index generation.
    "index_mode": "flat",           # "flat" | "subsystems"
    "index_link_style": "stem",     # "stem" -> [[page-name]], "path" -> [[dir/page-name]]
    "index_sections": [
        ("Sources", ["source"]),
        ("Entities", ["entity"]),
        ("Concepts", ["concept"]),
        ("Synthesis", ["synthesis"]),
        ("Queries", ["query"]),
    ],
    # Owner review staleness in days (large variant). None disables.
    "owner_review_max_days": None,
    # Coverage report (large variant only).
    "coverage": False,
}


def index_entry_extra(fields):
    """Trailing annotation for an index entry, by page type."""
    updated = fields.get("updated", "?")
    return f"(updated {updated})"


if __name__ == "__main__":
    import sys
    from wikilint import main
    sys.exit(main(CONFIG, index_entry_extra))
