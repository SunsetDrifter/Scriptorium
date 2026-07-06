"""All mechanical checks except index drift (which lives with the index
builder in derived.py)."""

import re
from datetime import date, datetime

from .model import (
    ADR_FILE_RE, FILENAME_EXEMPT, KEBAB_RE, LOG_HEADER_RE, MD_LINK_RE,
    SECRET_PATTERNS, WIKILINK_RE, build_link_index, line_at,
    parse_index_pinning, parse_iso_date, resolve_link,
)
from .settings import CONFIG


def missing_value(value):
    """True when a required field is absent in practice: None, "", or []."""
    return value is None or value == "" or value == []


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
        for field in CONFIG["required_fields"] + CONFIG["type_required"][ptype]:
            if missing_value(p.fields.get(field)):
                report.error("frontmatter", p.rel, f"missing or empty required field: {field}")
        check_enums(p, ptype, report)
        check_dates(p, report)
        desc = p.fields.get("description", "")
        if isinstance(desc, str) and len(desc) > 200:
            report.warning("frontmatter", p.rel, "description over 200 chars; keep it one line")


def check_enums(p, ptype, report):
    for field, allowed in CONFIG["enum_fields"].items():
        if field in p.fields and p.fields[field] not in allowed:
            report.error("frontmatter", p.rel, f"{field}: {p.fields[field]!r} not in {allowed}")
    for field, allowed in CONFIG["type_enum_fields"].get(ptype, {}).items():
        value = p.fields.get(field)
        if value is not None and value not in allowed:
            report.error("frontmatter", p.rel, f"{field}: {value!r} not in {allowed}")


def check_dates(p, report):
    parsed = {}
    for field in CONFIG.get("iso_date_fields", ["created", "updated"]):
        value = p.fields.get(field)
        if not value:
            continue
        parsed[field] = parse_iso_date(value)
        if parsed[field] is None:
            report.error("frontmatter", p.rel, f"{field} is not an ISO date")
    created, updated = parsed.get("created"), parsed.get("updated")
    if created and updated and updated < created:
        report.error("frontmatter", p.rel, "updated is older than created")


def check_filenames(pages, report):
    for p in pages:
        if p.path.name in FILENAME_EXEMPT:
            continue
        if not KEBAB_RE.match(p.path.name):
            report.warning("filename", p.rel, "not kebab-case")


def blank_inline_code(text):
    """Blank `inline code` spans (length-preserving) so link-shaped text
    inside them is not treated as a markdown link."""
    return re.sub(r"`[^`\n]*`", lambda m: " " * len(m.group(0)), text)


def check_markdown_links(p, pages_by_path, report):
    """Every relative [text](target) link must resolve on the filesystem
    (file or directory). Returns the resolved page targets for inbound
    counting. External, mailto:, and pure-anchor targets are skipped."""
    resolved_pages = []
    prose = blank_inline_code(p.prose)  # full text: line numbers are file-accurate
    for m in MD_LINK_RE.finditer(prose):
        target = m.group(1).split("#")[0]
        if not target or "://" in target or target.startswith(("mailto:", "//")):
            continue
        path = (p.path.parent / target).resolve()
        if not path.exists():
            report.error(
                "md-link", f"{p.rel}:{line_at(prose, m.start())}",
                f"broken relative link ({m.group(1)})",
            )
        elif path in pages_by_path:
            resolved_pages.append(pages_by_path[path])
    return resolved_pages


def check_links_and_orphans(pages, report):
    by_stem, by_rel = build_link_index(pages)
    pages_by_path = {p.path.resolve(): p for p in pages}
    inbound = {p.rel: 0 for p in pages}
    for p in pages:
        for m in WIKILINK_RE.finditer(p.body_prose):
            target = resolve_link(m.group(1), by_stem, by_rel)
            if target is None:
                report.error("wikilink", p.rel, f"broken link [[{m.group(1)}]]")
            elif target.rel != p.rel:
                inbound[target.rel] += 1
        if CONFIG.get("markdown_links", False):
            for target in check_markdown_links(p, pages_by_path, report):
                if target.rel != p.rel:
                    inbound[target.rel] += 1
        for field in CONFIG["path_fields"] + CONFIG["edge_fields"]:
            for value in p.field_list(field):
                target = resolve_link(value, by_stem, by_rel)
                if target is None:
                    report.error(
                        "reference", p.rel,
                        f"{field} points to nonexistent page: {value}",
                    )
                elif target.rel != p.rel:
                    inbound[target.rel] += 1
    if not CONFIG.get("orphans", True):
        return
    orphans = [
        p for p in pages
        if inbound[p.rel] == 0 and p.path.name not in FILENAME_EXEMPT
    ]
    for p in orphans:
        report.warning("orphan", p.rel, "no inbound links from any page")
        report_unlinked_mentions(p, pages, report)


def report_unlinked_mentions(orphan, pages, report):
    """Hint generation for the cross-linker: places where an orphan's name
    appears in prose without a wikilink."""
    patterns = [
        re.compile(re.escape(orphan.stem.replace("-", " ")), re.IGNORECASE),
        re.compile(re.escape(orphan.stem), re.IGNORECASE),
    ]
    for other in pages:
        if other.rel == orphan.rel:
            continue
        for pattern in patterns:
            m = pattern.search(other.prose)
            if m:
                report.info(
                    "orphan", orphan.rel,
                    f"mentioned unlinked in {other.rel}:{line_at(other.prose, m.start())}; "
                    "candidate wikilink",
                )
                break


def check_membership(pages, report):
    """Active member pages (components/modules) must appear in at least one
    container page's (topology/architecture) membership field."""
    rule = CONFIG["membership"]
    if not rule:
        return
    by_stem, by_rel = build_link_index(pages)
    contained = set()
    for p in pages:
        if p.type != rule["container_type"]:
            continue
        for value in p.field_list(rule["container_field"]):
            target = resolve_link(value, by_stem, by_rel)
            if target is not None:
                contained.add(target.rel)
    for p in pages:
        if p.type != rule["member_type"] or not p.fields:
            continue
        if p.fields.get("status") not in rule["active_statuses"]:
            continue
        if p.rel not in contained:
            report.warning(
                "membership", p.rel,
                f"active {rule['member_type']} not included in any "
                f"{rule['container_type']} page",
            )


def check_claude_size(root, report):
    claude = root / "CLAUDE.md"
    if not claude.is_file():
        return
    lines = len(claude.read_text(encoding="utf-8", errors="replace").splitlines())
    cap = CONFIG["claude_md_max_lines"]
    if lines > cap:
        report.warning(
            "hot-core", "CLAUDE.md",
            f"{lines} lines exceeds the {cap}-line cap; "
            "the always-loaded core is regrowing, move detail to workflows/",
        )


def load_taxonomy(root):
    path = root / CONFIG["taxonomy_file"]
    if not path.is_file():
        return None
    tags = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^- ([a-z0-9][a-z0-9-]*)", line)
        if m:
            tags.add(m.group(1))
    return tags


def check_tags(pages, report, root):
    if CONFIG.get("taxonomy_file") is None:
        return
    taxonomy = load_taxonomy(root)
    if taxonomy is None:
        report.warning(
            "tags", CONFIG["taxonomy_file"],
            "missing; create it and list the allowed tags",
        )
        return
    used = set()
    for p in pages:
        for tag in p.field_list("tags"):
            used.add(tag)
            if tag not in taxonomy:
                report.warning(
                    "tags", p.rel,
                    f"tag {tag!r} not in {CONFIG['taxonomy_file']}; "
                    "normalize it or add it there in the same commit",
                )
    for unused in sorted(taxonomy - used):
        report.info("tags", CONFIG["taxonomy_file"], f"tag {unused!r} is used by no page")


def check_contested_age(pages, report):
    today = date.today()
    for p in pages:
        if (p.fields or {}).get("confidence") != "contested":
            continue
        updated = parse_iso_date(p.fields.get("updated"))
        if updated is None:
            continue
        age = (today - updated).days
        if age > CONFIG["contested_max_days"]:
            report.warning(
                "contested", p.rel,
                f"contested and untouched for {age} days "
                f"(limit {CONFIG['contested_max_days']}); run reconcile",
            )


def check_inferred_markers(pages, report):
    for p in pages:
        if "(inferred)" not in p.body_prose:
            continue
        if (p.fields or {}).get("confidence") not in ("low", "contested"):
            report.warning(
                "provenance", p.rel,
                "contains '(inferred)' claims but confidence is not low",
            )


def check_inbox(root, report):
    if CONFIG.get("inbox_dir") is None:
        return
    inbox = root / CONFIG["inbox_dir"]
    if not inbox.is_dir():
        return
    items = [e for e in inbox.iterdir() if not e.name.startswith(".")]
    if len(items) >= CONFIG["inbox_warn_count"]:
        report.warning("inbox", CONFIG["inbox_dir"], f"{len(items)} items awaiting triage")
    now = datetime.now()
    for item in items:
        age = (now - datetime.fromtimestamp(item.stat().st_mtime)).days
        if age >= CONFIG["inbox_warn_age_days"]:
            report.warning("inbox", item.name, f"in inbox for {age} days")


def secret_patterns():
    return SECRET_PATTERNS + [
        (re.compile(pattern), label)
        for pattern, label in CONFIG.get("extra_secret_patterns", [])
    ]


def scan_text_for_secrets(text, rel, report):
    """Scan one file's text; matches whose line matches any allow regex are
    suppressed (template placeholders, redaction markers)."""
    allow = [re.compile(a) for a in CONFIG.get("secret_allow_res", [])]
    lines = text.split("\n")
    for pattern, label in secret_patterns():
        for m in pattern.finditer(text):
            line_no = line_at(text, m.start())
            if any(a.search(lines[line_no - 1]) for a in allow):
                continue
            report.error("secrets", f"{rel}:{line_no}", f"possible {label}")


def check_secrets(pages, report):
    for p in pages:
        scan_text_for_secrets(p.text, p.rel, report)


def check_field_staleness(pages, report):
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


def check_sync_drift(pages, report, root):
    if not CONFIG["sync_drift"]:
        return
    field, types = CONFIG["sync_drift"]
    synced = parse_index_pinning(root).get("last_synced_commit")
    if not synced:
        return
    crit_field = CONFIG["criticality_field"]
    plain_counts = {}
    for p in pages:
        if p.type not in types or not p.fields:
            continue
        verified = p.fields.get(field)
        if not verified or verified == synced:
            continue
        crit = p.fields.get(crit_field) if crit_field else None
        if crit == "load-bearing" or not crit_field:
            label = "load-bearing page" if crit_field else "page"
            report.warning(
                "sync-drift", p.rel,
                f"{label} verified at {verified}, repo at {synced}",
            )
        else:
            plain_counts[crit or "unspecified"] = (
                plain_counts.get(crit or "unspecified", 0) + 1
            )
    for crit, count in sorted(plain_counts.items()):
        report.info("sync-drift", crit, f"{count} stale pages (run verify)")


def check_owner_review(pages, report):
    if not CONFIG["owner_review_max_days"]:
        return
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
    for m in re.finditer(
        r"([A-Za-z][\w-]*)\s*(?:-->|---|-\.->|==>|--o|--x)\s*([A-Za-z][\w-]*)", block
    ):
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
            check_adr_dir(dir_path, pages, report, root)


def check_adr_dir(dir_path, pages, report, root):
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
    log_file = CONFIG.get("log_file", "log.md")
    if log_file is None:
        return
    log = root / log_file
    if not log.is_file():
        report.warning("log", log_file, "missing")
        return
    text = log.read_text(encoding="utf-8", errors="replace")
    for i, line in enumerate(text.splitlines(), 1):
        if line.startswith("## ") and not LOG_HEADER_RE.match(line):
            report.warning(
                "log", f"log.md:{i}",
                f"header not in '## [date] op | desc' form: {line!r}",
            )
