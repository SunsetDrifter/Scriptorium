#!/usr/bin/env python3
"""Deterministic lint for this wiki. Stdlib only. Run from the wiki root.

Usage:
    python3 lint.py check            run all mechanical checks, exit 1 on errors
    python3 lint.py rebuild-index    regenerate index.md from page frontmatter
    python3 lint.py reverse-deps     print the derived reverse-dependency map
    python3 lint.py coverage         write coverage.md from the pinned repo scope

The LLM lint workflow (workflows/lint.md) runs `check` first and relays the
findings, then handles only the checks that need judgment. If a check can be
a script, it lives here, not in prose.

The CONFIG dict below is the only part that differs between wiki variants.
Everything under it is shared logic; keep it identical across variants so
fixes propagate by copy.
"""

import re
import sys
from datetime import date, datetime
from pathlib import Path

# --------------------------------------------------------------------------
# CONFIG (large codebase variant)
# --------------------------------------------------------------------------

CONFIG = {
    # Directories containing wiki pages, relative to the wiki root.
    "page_dirs": [
        "subsystems", "adrs", "architecture", "concepts", "runbooks",
        "postmortems", "synthesis", "queries",
    ],
    # Top-level entries that are allowed to exist but are not wiki pages.
    "non_page_allowed": [
        "CLAUDE.md", "index.md", "log.md", "coverage.md", "glossary.md",
        "lint.py", "raw", "workflows", ".git", ".gitignore",
    ],
    "raw_dir": "raw",
    "inbox_dir": "raw/inbox",
    "inbox_warn_count": 10,
    "inbox_warn_age_days": 14,
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


# --------------------------------------------------------------------------
# Shared logic below. Keep identical across variants.
# --------------------------------------------------------------------------

GENERATED_MARKER = "<!-- generated by lint.py: edit above this line only -->"

SECRET_PATTERNS = [
    (r"(?i)\bpassword\s*[:=]\s*\S", "password assignment"),
    (r"(?i)\bapi[_-]?key\s*[:=]\s*\S", "api key assignment"),
    (r"(?i)\bsecret\s*[:=]\s*\S", "secret assignment"),
    (r"(?i)\btoken\s*[:=]\s*[A-Za-z0-9._-]{8,}", "token assignment"),
    (r"BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY", "private key block"),
    (r"\bAKIA[0-9A-Z]{16}\b", "AWS access key id"),
    (r"(?i)wg[- ]?private", "wireguard private key reference"),
    (r"Bearer\s+[A-Za-z0-9._~+/-]{20,}", "bearer token"),
]

WIKILINK_RE = re.compile(r"\[\[([^\]\n]+?)\]\]")
KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
LOG_HEADER_RE = re.compile(r"^## \[\d{4}-\d{2}-\d{2}\] [a-z][a-z-]*(?: \| .+)?$")
ADR_FILE_RE = re.compile(r"^(\d{4})-[a-z0-9-]+\.md$")


class Report:
    def __init__(self):
        self.items = []  # (severity, check, path, message)

    def add(self, severity, check, path, message):
        self.items.append((severity, check, str(path), message))

    def error(self, check, path, message):
        self.add("ERROR", check, path, message)

    def warning(self, check, path, message):
        self.add("WARNING", check, path, message)

    def info(self, check, path, message):
        self.add("INFO", check, path, message)

    def render(self):
        order = {"ERROR": 0, "WARNING": 1, "INFO": 2}
        lines = []
        for sev in ("ERROR", "WARNING", "INFO"):
            group = [i for i in self.items if i[0] == sev]
            if not group:
                continue
            lines.append(f"\n{sev}S ({len(group)})")
            for _, check, path, message in sorted(group, key=lambda i: (i[1], i[2])):
                lines.append(f"  [{check}] {path}: {message}")
        counts = {s: sum(1 for i in self.items if i[0] == s) for s in order}
        lines.append(
            f"\nsummary: {counts['ERROR']} errors, "
            f"{counts['WARNING']} warnings, {counts['INFO']} info"
        )
        return "\n".join(lines)

    @property
    def has_errors(self):
        return any(i[0] == "ERROR" for i in self.items)


def parse_frontmatter(text):
    """Minimal YAML frontmatter parser: flat keys, inline and block lists.

    Returns (fields, error). Nested mappings beyond one list level are not
    supported by design; the page schemas only use flat fields.
    """
    if not text.startswith("---"):
        return None, "missing frontmatter"
    lines = text.split("\n")
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None, "unterminated frontmatter"
    fields = {}
    current_list_key = None
    for line in lines[1:end]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line.startswith((" ", "\t")):
            m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line)
            if not m:
                return None, f"unparseable frontmatter line: {stripped!r}"
            key, raw_val = m.group(1), m.group(2).strip()
            current_list_key = None
            if raw_val == "":
                fields[key] = []
                current_list_key = key
            elif raw_val.startswith("[") and raw_val.endswith("]"):
                inner = raw_val[1:-1].strip()
                fields[key] = (
                    [v.strip().strip("'\"") for v in inner.split(",") if v.strip()]
                    if inner else []
                )
            else:
                fields[key] = raw_val.strip("'\"")
        elif stripped.startswith("- ") and current_list_key is not None:
            fields[current_list_key].append(stripped[2:].strip().strip("'\""))
        # Indented non-list lines (nested mappings) are tolerated but ignored.
    return fields, None


def parse_iso_date(value):
    try:
        return date.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def strip_code_blocks(body):
    """Remove fenced code blocks so wikilinks/secrets inside examples don't count."""
    return re.sub(r"```.*?```", "", body, flags=re.DOTALL)


class Page:
    def __init__(self, path, root):
        self.path = path
        self.rel = path.relative_to(root).as_posix()
        self.text = path.read_text(encoding="utf-8", errors="replace")
        self.fields, self.fm_error = parse_frontmatter(self.text)
        self.body = self._body_text()

    def _body_text(self):
        if not self.text.startswith("---"):
            return self.text
        parts = self.text.split("\n---\n", 1)
        return parts[1] if len(parts) == 2 else ""

    @property
    def stem(self):
        return self.path.stem

    @property
    def rel_no_ext(self):
        return self.rel[:-3] if self.rel.endswith(".md") else self.rel

    @property
    def type(self):
        return (self.fields or {}).get("type")


def discover_pages(root, report):
    pages = []
    for d in CONFIG["page_dirs"]:
        dir_path = root / d
        if not dir_path.is_dir():
            continue
        for path in sorted(dir_path.rglob("*.md")):
            pages.append(Page(path, root))
    known = set(CONFIG["page_dirs"]) | set(CONFIG["non_page_allowed"])
    for entry in sorted(root.iterdir()):
        if entry.name not in known and not entry.name.startswith("."):
            report.warning(
                "layout", entry.name,
                "unknown top-level entry; the schema says ask before inventing folders",
            )
    return pages


def build_link_index(pages):
    """stem -> [rel paths] and rel_no_ext -> page for resolution."""
    by_stem = {}
    by_rel = {}
    for p in pages:
        by_stem.setdefault(p.stem, []).append(p)
        by_rel[p.rel_no_ext] = p
        by_rel[p.rel] = p
    return by_stem, by_rel


def resolve_link(target, by_stem, by_rel):
    target = target.split("|")[0].split("#")[0].strip()
    if not target:
        return None
    if target in by_rel:
        return by_rel[target]
    candidates = by_stem.get(target.removesuffix(".md").split("/")[-1], [])
    if "/" in target:
        wanted = target.removesuffix(".md")
        matches = [p for p in candidates if p.rel_no_ext.endswith(wanted)]
        return matches[0] if len(matches) == 1 else None
    return candidates[0] if len(candidates) == 1 else None


def check_frontmatter(pages, report):
    valid_types = set(CONFIG["type_required"])
    for p in pages:
        if p.fm_error:
            report.error("frontmatter", p.rel, p.fm_error)
            continue
        ptype = p.type
        if ptype not in valid_types:
            report.error("frontmatter", p.rel, f"invalid or missing type: {ptype!r}")
            continue
        required = CONFIG["required_fields"] + CONFIG["type_required"][ptype]
        for field in required:
            if field not in p.fields or p.fields[field] in ("", None):
                report.error("frontmatter", p.rel, f"missing required field: {field}")
        for field, allowed in CONFIG["enum_fields"].items():
            if field in p.fields and p.fields[field] not in allowed:
                report.error(
                    "frontmatter", p.rel,
                    f"{field}: {p.fields[field]!r} not in {allowed}",
                )
        for field, allowed in CONFIG["type_enum_fields"].get(ptype, {}).items():
            value = p.fields.get(field)
            if value is not None and value not in allowed:
                report.error(
                    "frontmatter", p.rel,
                    f"{field}: {value!r} not in {allowed}",
                )
        created = parse_iso_date(p.fields.get("created"))
        updated = parse_iso_date(p.fields.get("updated"))
        if p.fields.get("created") and created is None:
            report.error("frontmatter", p.rel, "created is not an ISO date")
        if p.fields.get("updated") and updated is None:
            report.error("frontmatter", p.rel, "updated is not an ISO date")
        if created and updated and updated < created:
            report.error("frontmatter", p.rel, "updated is older than created")
        desc = p.fields.get("description", "")
        if isinstance(desc, str) and len(desc) > 200:
            report.warning("frontmatter", p.rel, "description over 200 chars; keep it one line")


def check_filenames(pages, report):
    exceptions = {"README.md", "OWNERS.md"}
    for p in pages:
        if p.path.name in exceptions:
            continue
        if not KEBAB_RE.match(p.path.name):
            report.warning("filename", p.rel, "not kebab-case")


def check_links_and_orphans(pages, report, root):
    by_stem, by_rel = build_link_index(pages)
    inbound = {p.rel: 0 for p in pages}
    for p in pages:
        prose = strip_code_blocks(p.body)
        for m in WIKILINK_RE.finditer(prose):
            target = resolve_link(m.group(1), by_stem, by_rel)
            if target is None:
                report.error("wikilink", p.rel, f"broken link [[{m.group(1)}]]")
            elif target.rel != p.rel:
                inbound[target.rel] += 1
        for field in CONFIG["path_fields"] + CONFIG["edge_fields"]:
            values = p.fields.get(field) if p.fields else None
            if not values:
                continue
            if isinstance(values, str):
                values = [values]
            for value in values:
                target = resolve_link(value, by_stem, by_rel)
                if target is None:
                    report.error(
                        "reference", p.rel,
                        f"{field} points to nonexistent page: {value}",
                    )
                else:
                    inbound[target.rel] += 1
    for p in pages:
        if inbound[p.rel] == 0 and p.path.name not in ("README.md", "OWNERS.md"):
            report.warning("orphan", p.rel, "no inbound links from any page")


def derive_reverse_edges(pages):
    """field -> {target rel: [source rels]}. The derived view of stored edges."""
    by_stem, by_rel = build_link_index(pages)
    reverse = {}
    for field in CONFIG["edge_fields"]:
        rev = {}
        for p in pages:
            values = p.fields.get(field) if p.fields else None
            if not values:
                continue
            if isinstance(values, str):
                values = [values]
            for value in values:
                target = resolve_link(value, by_stem, by_rel)
                if target is not None:
                    rev.setdefault(target.rel, []).append(p.rel)
        reverse[field] = rev
    return reverse


def check_inbox(root, report):
    inbox = root / CONFIG["inbox_dir"]
    if not inbox.is_dir():
        return
    items = [e for e in inbox.iterdir() if not e.name.startswith(".")]
    if len(items) >= CONFIG["inbox_warn_count"]:
        report.warning("inbox", CONFIG["inbox_dir"], f"{len(items)} items awaiting triage")
    today = datetime.now()
    for item in items:
        age = (today - datetime.fromtimestamp(item.stat().st_mtime)).days
        if age >= CONFIG["inbox_warn_age_days"]:
            report.warning("inbox", item.name, f"in inbox for {age} days")


def check_secrets(pages, report):
    for p in pages:
        for pattern, label in SECRET_PATTERNS:
            for m in re.finditer(pattern, p.text):
                line_no = p.text[:m.start()].count("\n") + 1
                report.error("secrets", f"{p.rel}:{line_no}", f"possible {label}")


def parse_index_pinning(root):
    """Parse the yaml pinning block at the top of index.md, if any."""
    index = root / "index.md"
    if not index.is_file():
        return {}
    text = index.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"```yaml\n(.*?)```", text, re.DOTALL)
    if not m:
        return {}
    pinning = {}
    current_key = None
    for line in m.group(1).splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        if not line.startswith((" ", "\t")):
            km = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
            if km:
                key, val = km.group(1), km.group(2).strip()
                if val == "":
                    pinning[key] = {}
                    current_key = key
                else:
                    pinning[key] = val
                    current_key = None
        elif current_key is not None:
            km = re.match(r"^\s+([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
            if km:
                val = km.group(2).strip()
                if val.startswith("[") and val.endswith("]"):
                    items = [v.strip() for v in val[1:-1].split(",") if v.strip()]
                    pinning[current_key][km.group(1)] = items
                else:
                    pinning[current_key][km.group(1)] = val
    return pinning


def check_staleness(pages, report, root):
    today = date.today()
    for rule in CONFIG["staleness"]:
        for p in pages:
            if p.type not in rule["types"] or not p.fields:
                continue
            value = p.fields.get(rule["field"])
            if not value:
                continue
            d = parse_iso_date(value)
            if d is None:
                report.error("staleness", p.rel, f"{rule['field']} is not an ISO date")
                continue
            age = (today - d).days
            if age > rule["max_days"]:
                report.add(
                    rule["severity"].upper(), "staleness", p.rel,
                    f"{rule['field']} is {age} days old (limit {rule['max_days']})",
                )
    if CONFIG["sync_drift"]:
        field, types = CONFIG["sync_drift"]
        pinning = parse_index_pinning(root)
        synced = pinning.get("last_synced_commit")
        if synced:
            crit_field = CONFIG["criticality_field"]
            plain_counts = {}
            for p in pages:
                if p.type not in types or not p.fields:
                    continue
                verified = p.fields.get(field)
                if verified and verified != synced:
                    crit = p.fields.get(crit_field) if crit_field else None
                    if crit == "load-bearing":
                        report.warning(
                            "sync-drift", p.rel,
                            f"load-bearing page verified at {verified}, repo at {synced}",
                        )
                    elif crit_field:
                        plain_counts[crit or "unspecified"] = (
                            plain_counts.get(crit or "unspecified", 0) + 1
                        )
                    else:
                        report.warning(
                            "sync-drift", p.rel,
                            f"verified at {verified}, repo at {synced}",
                        )
            for crit, count in sorted(plain_counts.items()):
                report.info("sync-drift", crit, f"{count} stale pages (run verify)")
    if CONFIG["owner_review_max_days"]:
        today = date.today()
        for p in pages:
            if p.type != "subsystem" or not p.fields:
                continue
            reviewed = parse_iso_date(p.fields.get("last_owner_review"))
            if reviewed is None:
                report.warning("owner-review", p.rel, "missing or invalid last_owner_review")
            elif (today - reviewed).days > CONFIG["owner_review_max_days"]:
                report.warning(
                    "owner-review", p.rel,
                    f"last owner review {(today - reviewed).days} days ago",
                )


def count_mermaid_nodes(block):
    """Rough node count for a mermaid block: unique identifiers that are
    declared with a shape or appear on either side of an edge."""
    ids = set()
    for m in re.finditer(r"([A-Za-z][\w-]*)\s*(?:\[|\(|\{)", block):
        ids.add(m.group(1))
    for m in re.finditer(r"([A-Za-z][\w-]*)\s*(?:-->|---|-\.->|==>|--o|--x)\s*([A-Za-z][\w-]*)", block):
        ids.add(m.group(1))
        ids.add(m.group(2))
    keywords = {"flowchart", "graph", "sequenceDiagram", "subgraph", "end",
                "classDef", "class", "style", "direction", "erDiagram", "C4Context"}
    return len(ids - keywords)


def check_mermaid(pages, report):
    if not CONFIG["mermaid_required_types"]:
        return
    for p in pages:
        if p.type not in CONFIG["mermaid_required_types"]:
            continue
        blocks = re.findall(r"```mermaid\n(.*?)```", p.body, re.DOTALL)
        if not blocks:
            report.error("mermaid", p.rel, "page type requires at least one mermaid diagram")
            continue
        for block in blocks:
            nodes = count_mermaid_nodes(block)
            if CONFIG["mermaid_node_error"] and nodes > CONFIG["mermaid_node_error"]:
                report.error("mermaid", p.rel, f"diagram has ~{nodes} nodes; split it")
            elif CONFIG["mermaid_node_warn"] and nodes > CONFIG["mermaid_node_warn"]:
                report.warning("mermaid", p.rel, f"diagram has ~{nodes} nodes; consider splitting")


def check_adrs(pages, report, root):
    for adr_dir in CONFIG["adr_dirs"]:
        for dir_path in sorted(root.glob(adr_dir)):
            if not dir_path.is_dir():
                continue
            numbers = {}
            for p in pages:
                if p.path.parent != dir_path:
                    continue
                m = ADR_FILE_RE.match(p.path.name)
                if not m:
                    report.warning("adr", p.rel, "not in NNNN-slug.md form")
                    continue
                numbers[int(m.group(1))] = p
                status = (p.fields or {}).get("status")
                if status == "superseded" and not (p.fields or {}).get("superseded_by"):
                    report.error("adr", p.rel, "superseded ADR has no superseded_by forward link")
            if numbers:
                expected = set(range(min(numbers), max(numbers) + 1))
                for gap in sorted(expected - set(numbers)):
                    rel = dir_path.relative_to(root).as_posix()
                    report.warning("adr", rel, f"numbering gap: {gap:04d} missing")


def check_log(root, report):
    log = root / "log.md"
    if not log.is_file():
        report.warning("log", "log.md", "missing")
        return
    for i, line in enumerate(log.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if line.startswith("## ") and not LOG_HEADER_RE.match(line):
            report.warning("log", f"log.md:{i}", f"header not in '## [date] op | desc' form: {line!r}")


def generate_index_body(pages):
    lines = []
    if CONFIG["index_mode"] == "subsystems":
        subsystems = sorted(
            (p for p in pages if p.type == "subsystem"),
            key=lambda p: p.rel,
        )
        lines.append("## Subsystems")
        lines.append("")
        for p in subsystems:
            desc = p.fields.get("mission") or p.fields.get("description", "")
            review = p.fields.get("last_owner_review", "never")
            lines.append(f"- [[{p.rel_no_ext}]] — {desc} (last review {review})")
        lines.append("")
        global_pages = [p for p in pages
                        if p.fields and p.fields.get("subsystem") == "global"]
        pool = global_pages
    else:
        pool = pages
    for section, types in CONFIG["index_sections"]:
        members = sorted(
            (p for p in pool if p.type in types),
            key=lambda p: p.rel,
        )
        if not members:
            continue
        lines.append(f"## {section}")
        lines.append("")
        for p in members:
            link = p.stem if CONFIG["index_link_style"] == "stem" else p.rel_no_ext
            desc = p.fields.get("description", "") if p.fields else ""
            extra = index_entry_extra(p.fields or {})
            lines.append(f"- [[{link}]] — {desc} {extra}".rstrip())
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def rebuild_index(root):
    report = Report()
    pages = discover_pages(root, report)
    index = root / "index.md"
    head = "# Index\n\n"
    if index.is_file():
        existing = index.read_text(encoding="utf-8", errors="replace")
        if GENERATED_MARKER in existing:
            head = existing.split(GENERATED_MARKER)[0]
        else:
            m = re.match(r"\A(.*?```yaml\n.*?```\n)", existing, re.DOTALL)
            if m:
                head = m.group(1) + "\n"
    body = generate_index_body(pages)
    index.write_text(f"{head}{GENERATED_MARKER}\n\n{body}", encoding="utf-8")
    print(f"index.md rebuilt: {sum(1 for _ in body.splitlines() if _.startswith('- '))} entries")


def check_index_drift(pages, report, root):
    index = root / "index.md"
    if not index.is_file():
        report.warning("index", "index.md", "missing; run `python3 lint.py rebuild-index`")
        return
    existing = index.read_text(encoding="utf-8", errors="replace")
    if GENERATED_MARKER not in existing:
        report.warning("index", "index.md", "no generated marker; run `python3 lint.py rebuild-index`")
        return
    current = existing.split(GENERATED_MARKER, 1)[1].lstrip("\n")
    if current != generate_index_body(pages):
        report.warning("index", "index.md", "out of date; run `python3 lint.py rebuild-index`")


def run_coverage(root):
    """Approximate per-subsystem coverage report (large variant).

    Counts first-level directories under each include root of the pinned repo
    and checks whether any module page's source_path covers them.
    """
    report = Report()
    pages = discover_pages(root, report)
    pinning = parse_index_pinning(root)
    local = pinning.get("local_path")
    scope = pinning.get("wiki_scope", {})
    if not local:
        print("coverage: no local_path in index.md pinning block; skipping")
        return
    repo = Path(local).expanduser()
    if not repo.is_dir():
        print(f"coverage: {repo} not found; skipping")
        return
    modules = [p for p in pages if p.type == "module" and p.fields]
    source_paths = [p.fields.get("source_path", "").strip("/") for p in modules]
    lines = ["# Coverage", "", f"Generated by lint.py against `{local}`.", ""]
    includes = scope.get("include", []) if isinstance(scope, dict) else []
    excludes = scope.get("exclude", []) if isinstance(scope, dict) else []
    for inc in includes:
        inc_dir = repo / inc.strip("/")
        if not inc_dir.is_dir():
            continue
        entries = sorted(
            e for e in inc_dir.iterdir()
            if e.is_dir() and not any(e.match(x) for x in excludes)
        )
        covered = []
        uncovered = []
        for e in entries:
            rel = e.relative_to(repo).as_posix()
            if any(sp and (sp == rel or sp.startswith(rel + "/") or rel.startswith(sp))
                   for sp in source_paths):
                covered.append(rel)
            else:
                uncovered.append(rel)
        total = len(covered) + len(uncovered)
        pct = round(100 * len(covered) / total) if total else 100
        lines.append(f"## {inc}")
        lines.append("")
        lines.append(f"{len(covered)}/{total} first-level directories covered ({pct}%)")
        for u in uncovered:
            lines.append(f"- uncovered: `{u}`")
        lines.append("")
    (root / "coverage.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print("coverage.md written")


def run_check(root):
    report = Report()
    pages = discover_pages(root, report)
    check_frontmatter(pages, report)
    check_filenames(pages, report)
    check_links_and_orphans(pages, report, root)
    check_inbox(root, report)
    check_secrets(pages, report)
    check_staleness(pages, report, root)
    check_mermaid(pages, report)
    check_adrs(pages, report, root)
    check_log(root, report)
    check_index_drift(pages, report, root)
    print(f"checked {len(pages)} pages")
    print(report.render())
    return 1 if report.has_errors else 0


def run_reverse_deps(root):
    report = Report()
    pages = discover_pages(root, report)
    if not CONFIG["edge_fields"]:
        print("no edge fields configured for this variant")
        return 0
    for field, rev in derive_reverse_edges(pages).items():
        print(f"\nreverse of {field}:")
        for target, sources in sorted(rev.items()):
            print(f"  {target} <- {', '.join(sorted(sources))}")
    return 0


def main():
    root = Path.cwd()
    if not (root / "CLAUDE.md").is_file():
        print("run from the wiki root (CLAUDE.md not found here)", file=sys.stderr)
        return 2
    command = sys.argv[1] if len(sys.argv) > 1 else "check"
    if command == "check":
        return run_check(root)
    if command in ("rebuild-index", "--rebuild-index"):
        rebuild_index(root)
        return 0
    if command in ("reverse-deps", "--reverse-deps"):
        return run_reverse_deps(root)
    if command in ("coverage", "--coverage"):
        if not CONFIG["coverage"]:
            print("coverage is not enabled for this variant")
            return 2
        run_coverage(root)
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
