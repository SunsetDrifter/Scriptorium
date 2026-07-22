"""All mechanical checks except index drift (which lives with the index
builder in derived.py)."""

import re
from datetime import date, datetime
from urllib.parse import unquote

from .model import (
    ADR_FILE_RE, FILENAME_EXEMPT, KEBAB_RE, LOG_DATE_HEADER_RE, LOG_ENTRY_RE,
    MD_LINK_RE, OKF_VERSION, SECRET_PATTERNS, blank_frontmatter, blank_images,
    blank_inline_code, build_link_index, discover_okf_bundle, line_at,
    parse_frontmatter, parse_index_pinning, parse_iso_date, resolve_link,
)
from .settings import CONFIG

# A URI scheme (mailto:, tel:, https:, data:, ...) or protocol-relative //host.
URI_SCHEME_RE = re.compile(r"^(?:[a-zA-Z][a-zA-Z0-9+.\-]*:|//)")


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
    for field in CONFIG["iso_date_fields"]:
        value = p.fields.get(field)
        if value and parse_iso_date(value) is None:
            report.error("frontmatter", p.rel, f"{field} is not an ISO date")
    # The created/updated ordering invariant holds regardless of which fields
    # are ISO-validated above.
    created = parse_iso_date(p.fields.get("created"))
    updated = parse_iso_date(p.fields.get("updated"))
    if created and updated and updated < created:
        report.error("frontmatter", p.rel, "updated is older than created")


def check_filenames(pages, report):
    for p in pages:
        if p.path.name in FILENAME_EXEMPT:
            continue
        if not KEBAB_RE.match(p.path.name):
            report.warning("filename", p.rel, "not kebab-case")


def _file_identity(path):
    """(device, inode) identity for a path, or None if it can't be stat'd.
    Used to match a link target to a page independent of the spelling of the
    path (case on case-insensitive filesystems, symlinks, mount aliases)."""
    try:
        st = path.stat()
    except OSError:
        return None
    return (st.st_dev, st.st_ino)


def check_markdown_links(p, pages_by_identity, report, root):
    """Every [text](target) link must resolve on the filesystem (file or
    directory): bundle-absolute targets (leading /, OKF's recommended form)
    resolve against the wiki root, relative targets against the linking
    page's directory. Returns the resolved page targets for inbound counting.
    External (scheme/protocol-relative) and pure-anchor targets are skipped."""
    resolved_pages = []
    # resolve() both sides so symlinked roots (e.g. /var -> /private/var)
    # compare equal when checking bundle containment.
    root_resolved = root.resolve()
    # Body content only, images and code blanked, line numbers file-accurate.
    scan = blank_images(blank_frontmatter(p.prose))
    for m in MD_LINK_RE.finditer(scan):
        raw = m.group(1)
        target = raw.split("#")[0]
        if not target or URI_SCHEME_RE.match(target):
            continue
        if target.startswith("/"):
            path = (root / unquote(target).lstrip("/")).resolve()
        else:
            path = (p.path.parent / unquote(target)).resolve()
        if not path.exists():
            report.error(
                "link", f"{p.rel}:{line_at(scan, m.start())}",
                f"broken link ({raw})",
            )
            continue
        if path != root_resolved and root_resolved not in path.parents:
            report.error(
                "link", f"{p.rel}:{line_at(scan, m.start())}",
                f"link escapes the wiki root ({raw})",
            )
            continue
        target_page = pages_by_identity.get(_file_identity(path))
        if target_page is not None:
            resolved_pages.append(target_page)
    return resolved_pages


def check_links_and_orphans(pages, report, root):
    by_stem, by_rel = build_link_index(pages)
    pages_by_identity = {}
    for p in pages:
        identity = _file_identity(p.path)
        if identity is not None:
            pages_by_identity[identity] = p
    inbound = {p.rel: 0 for p in pages}
    for p in pages:
        for target in check_markdown_links(p, pages_by_identity, report, root):
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
    if not CONFIG["orphans"]:
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
    appears in prose without a link."""
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
                    "candidate link",
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
    """Parse the taxonomy file into (tags, types). Tag entries are `- slug`
    lines anywhere outside a `## Page types` section; entries inside that
    section map type slug -> one-line meaning (empty string when the line has
    no meaning after the dash). `types` is None when the section is absent."""
    path = root / CONFIG["taxonomy_file"]
    if not path.is_file():
        return None
    tags = set()
    types = None
    in_types = False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if re.match(r"^##\s+Page types\s*$", line):
            in_types = True
            if types is None:
                types = {}
            continue
        if re.match(r"^#{1,6}\s", line):
            in_types = False
            continue
        m = re.match(r"^- ([a-z0-9][a-z0-9-]*)(?:\s*—\s*(.*))?", line)
        if m:
            if in_types:
                types[m.group(1)] = (m.group(2) or "").strip()
            else:
                tags.add(m.group(1))
    return tags, types


def check_tags(pages, report, root):
    if CONFIG["taxonomy_file"] is None:
        return
    taxonomy = load_taxonomy(root)
    if taxonomy is None:
        report.warning(
            "tags", CONFIG["taxonomy_file"],
            "missing; create it and list the allowed tags",
        )
        return
    taxonomy, _types = taxonomy
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


def check_types(pages, report, root):
    """The type glossary: taxonomy.md's `## Page types` section must describe
    every schema type with a one-line meaning, so the bundle self-describes
    its type vocabulary to foreign OKF consumers."""
    if CONFIG["taxonomy_file"] is None or not CONFIG["types_glossary"]:
        return
    taxonomy = load_taxonomy(root)
    if taxonomy is None:
        return  # check_tags already reports the missing file
    _tags, types = taxonomy
    tfile = CONFIG["taxonomy_file"]
    if types is None:
        report.warning(
            "types", tfile,
            "no '## Page types' section; describe each page type there "
            "with a one-line meaning",
        )
        return
    schema_types = set(CONFIG["type_required"])
    for t in sorted(schema_types - set(types)):
        report.warning(
            "types", tfile,
            f"page type {t!r} is not described; add '- {t} — <meaning>' "
            "under '## Page types'",
        )
    for t in sorted(schema_types & set(types)):
        if not types[t]:
            report.warning(
                "types", tfile,
                f"page type {t!r} has no meaning; add one after the dash",
            )
    for t in sorted(set(types) - schema_types):
        report.warning(
            "types", tfile,
            f"'## Page types' describes unknown type {t!r}; remove it or "
            "add it to the schema",
        )


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
    if CONFIG["inbox_dir"] is None:
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
    """Built-in secret patterns plus the variant's extra_secret_patterns,
    compiled once at configure() time."""
    return SECRET_PATTERNS + CONFIG["secret_extra_compiled"]


def scan_text_for_secrets(text, rel, report):
    """Scan one file's text; matches whose line matches any allow regex are
    suppressed (template placeholders, redaction markers). Allow regexes are
    precompiled; the line split is deferred until a suppression check needs it."""
    allow = CONFIG["secret_allow_compiled"]
    lines = None
    for pattern, label in secret_patterns():
        for m in pattern.finditer(text):
            line_no = line_at(text, m.start())
            if allow:
                if lines is None:
                    lines = text.split("\n")
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
    """OKF log structure: '## YYYY-MM-DD' date headings, newest first, with
    entries as '- **Action**: ...' bullets. This check owns log.md end to
    end; check_okf deliberately does not re-validate it."""
    log_file = CONFIG["log_file"]
    if log_file is None:
        return
    log = root / log_file
    if not log.is_file():
        report.warning("log", log_file, "missing")
        return
    text = log.read_text(encoding="utf-8", errors="replace")
    prev = None  # (date, line_no) of the last valid heading seen
    for i, line in enumerate(text.splitlines(), 1):
        if line.startswith("## "):
            m = LOG_DATE_HEADER_RE.match(line)
            if not m:
                report.warning(
                    "log", f"{log_file}:{i}",
                    f"heading not in '## YYYY-MM-DD' form: {line!r}",
                )
                continue
            d = parse_iso_date(m.group(1))
            if d is None:
                report.warning("log", f"{log_file}:{i}", f"heading is not a valid date: {line!r}")
                continue
            if prev is not None and d > prev[0]:
                report.warning(
                    "log", f"{log_file}:{i}",
                    f"headings out of order (want newest-first): {d} follows {prev[0]}",
                )
            elif prev is not None and d == prev[0]:
                report.warning(
                    "log", f"{log_file}:{i}",
                    f"duplicate heading for {d}; append entries under the existing one",
                )
            prev = (d, i)
        elif line.startswith("- ") and not LOG_ENTRY_RE.match(line):
            report.warning(
                "log", f"{log_file}:{i}",
                "entry should open with a bold action word: '- **Update**: ...'",
            )


def check_okf(pages, report, root):
    """OKF v0.1 conformance: (1) every non-reserved .md parses as frontmatter,
    (2) with a non-empty type, (3) reserved files follow their structure.
    Pages are skipped here: check_frontmatter is strictly stricter. log.md's
    structure is owned by check_log, not re-validated here. raw/ is excluded
    by design (immutable human-owned sources; see discover_okf_bundle)."""
    if not CONFIG["okf_conformance"]:
        return
    page_rels = {p.rel for p in pages}
    for path in discover_okf_bundle(root):
        rel = path.relative_to(root).as_posix()
        if rel in page_rels:
            continue
        fields, err = parse_frontmatter(
            path.read_text(encoding="utf-8", errors="replace"))
        if err:
            report.error("okf", rel, f"OKF rule 1: {err}")
        elif missing_value(fields.get("type")):
            report.error("okf", rel, "OKF rule 2: missing or empty type")
    index_file = CONFIG["index_file"]
    if index_file and (root / index_file).is_file():
        fields, _ = parse_frontmatter(
            (root / index_file).read_text(encoding="utf-8", errors="replace"))
        if not fields or fields.get("okf_version") != OKF_VERSION:
            report.error(
                "okf", index_file,
                f'OKF rule 3: missing okf_version: "{OKF_VERSION}" frontmatter; '
                "run `python3 lint.py rebuild-index`",
            )
