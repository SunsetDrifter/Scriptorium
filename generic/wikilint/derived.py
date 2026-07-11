"""Derived artifacts: the generated index, reverse-dependency maps, and the
coverage report. check_index_drift lives here beside the builder it reuses."""

from pathlib import Path

from .model import (
    GENERATED_MARKER, OKF_VERSION, YAML_FENCE_RE, build_link_index,
    discover_pages, parse_index_pinning, resolve_link, Report,
)
from .settings import CONFIG


def derive_reverse_edges(pages):
    """field -> {target rel: [source rels]} for every relationship field in
    CONFIG['reverse_fields']. This is the derived view that replaces the old
    stored mirror fields (consumed_by, public_surface, api consumers)."""
    by_stem, by_rel = build_link_index(pages)
    reverse = {}
    for field in CONFIG["reverse_fields"]:
        rev = {}
        for p in pages:
            for value in p.field_list(field):
                target = resolve_link(value, by_stem, by_rel)
                if target is not None:
                    rev.setdefault(target.rel, []).append(p.rel)
        reverse[field] = rev
    return reverse


def run_reverse_deps(root):
    report = Report()
    pages = discover_pages(root, report)
    if not CONFIG["reverse_fields"]:
        print("no reverse fields configured for this variant")
        return 0
    for field, rev in derive_reverse_edges(pages).items():
        print(f"\nreverse of {field}:")
        if not rev:
            print("  (no edges)")
        for target, sources in sorted(rev.items()):
            print(f"  {target} <- {', '.join(sorted(sources))}")
    return 0


def index_path(root):
    """Absolute path of the generated index, or None when the index is
    disabled (index_file is None)."""
    index_file = CONFIG["index_file"]
    return root / index_file if index_file is not None else None


def prettify_title(stem):
    """Display title for a page without an authored `title` field:
    'zero-trust-networking' -> 'Zero Trust Networking'."""
    return " ".join(w.capitalize() for w in stem.split("-"))


def _index_entry_link(p):
    """OKF index entry link: bundle-absolute markdown link with the page's
    authored title, falling back to a prettified stem."""
    title = (p.fields or {}).get("title") or prettify_title(p.stem)
    return f"[{title}](/{p.rel})"


def generate_index_body(pages):
    body_fn = CONFIG["index_body_fn"]
    if body_fn is not None:
        return body_fn(pages)
    lines = []
    if CONFIG["index_mode"] == "subsystems":
        lines.extend(_subsystem_section(pages))
        pool = [p for p in pages
                if p.fields and p.fields.get("subsystem") == "global"]
    else:
        pool = pages
    entry_extra = CONFIG["index_entry_extra"]
    for section, types in CONFIG["index_sections"]:
        members = sorted((p for p in pool if p.type in types), key=lambda p: p.rel)
        if not members:
            continue
        lines.append(f"## {section}")
        lines.append("")
        for p in members:
            desc = p.fields.get("description", "") if p.fields else ""
            lines.append(
                f"* {_index_entry_link(p)} - {desc} {entry_extra(p.fields or {})}".rstrip())
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _subsystem_section(pages):
    lines = ["## Subsystems", ""]
    for p in sorted((p for p in pages if p.type == "subsystem"), key=lambda p: p.rel):
        desc = p.fields.get("mission") or p.fields.get("description", "")
        review = p.fields.get("last_owner_review", "never")
        lines.append(f"* {_index_entry_link(p)} - {desc} (last review {review})")
    lines.append("")
    return lines


def _strip_leading_frontmatter(text):
    """Drop a leading YAML frontmatter block (the okf_version stamp) so a
    re-run of rebuild-index never accumulates duplicate blocks. Mirrors
    Page._body_text but stays local: index.md is not a Page."""
    if not text.startswith("---"):
        return text
    lines = text.split("\n")
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[i + 1:]).lstrip("\n")
    return text


def rebuild_index(root):
    report = Report()
    pages = discover_pages(root, report)
    index = index_path(root)
    if index is None:
        print("index is disabled (index_file is None); nothing to rebuild")
        return 0
    index_name = index.relative_to(root).as_posix()
    index.parent.mkdir(parents=True, exist_ok=True)
    # The okf_version stamp is a single fixed key: always regenerate it so a
    # deleted or corrupted block self-heals on the next rebuild.
    front = f'---\nokf_version: "{OKF_VERSION}"\n---\n\n' if CONFIG["okf_conformance"] else ""
    head = "# Index\n\n"
    if index.is_file():
        existing = _strip_leading_frontmatter(
            index.read_text(encoding="utf-8", errors="replace"))
        if GENERATED_MARKER in existing:
            head = existing.split(GENERATED_MARKER)[0]
        else:
            m = YAML_FENCE_RE.search(existing)
            if m and existing[:m.start()].strip() in ("", "# Index"):
                head = existing[:m.end()] + "\n\n"
    body = generate_index_body(pages)
    index.write_text(f"{front}{head}{GENERATED_MARKER}\n\n{body}", encoding="utf-8")
    # The built-in body lists entries as "* " lines; a custom index_body_fn can
    # use any format, so report page count rather than guess at "entries".
    if CONFIG["index_body_fn"] is not None:
        print(f"{index_name} rebuilt ({len(pages)} pages)")
    else:
        entries = sum(1 for line in body.splitlines() if line.startswith("* "))
        print(f"{index_name} rebuilt: {entries} entries")
    return 0


def check_index_drift(pages, report, root):
    index = index_path(root)
    if index is None:
        return
    index_name = index.relative_to(root).as_posix()
    if not index.is_file():
        report.warning("index", index_name, "missing; run `python3 lint.py rebuild-index`")
        return
    existing = index.read_text(encoding="utf-8", errors="replace")
    if GENERATED_MARKER not in existing:
        report.warning("index", index_name, "no generated marker; run `python3 lint.py rebuild-index`")
        return
    # rebuild_index writes exactly "{head}{MARKER}\n\n{body}", so compare the
    # post-marker text against the same "\n\n"+body rather than lstrip-ing,
    # which would also strip a body that legitimately starts with a newline.
    current = existing.split(GENERATED_MARKER, 1)[1]
    if current != f"\n\n{generate_index_body(pages)}":
        report.warning("index", index_name, "out of date; run `python3 lint.py rebuild-index`")


def source_path_covers(source_paths, rel):
    """Boundary-anchored: 'src' covers 'src' and 'src/x', never 'src-utils'."""
    return any(
        sp and (sp == rel or sp.startswith(rel + "/") or rel.startswith(sp + "/"))
        for sp in source_paths
    )


def run_coverage(root):
    """Write coverage.md: per-subsystem module inventory by criticality, then
    per-include-root directory coverage with the uncovered directories named."""
    report = Report()
    pages = discover_pages(root, report)
    pinning = parse_index_pinning(root)
    local = pinning.get("local_path")
    if not local:
        index_name = CONFIG["index_file"] or "the index"
        print(f"coverage: no local_path in {index_name} pinning block; skipping")
        return 0
    repo = Path(local).expanduser()
    if not repo.is_dir():
        print(f"coverage: {repo} not found; skipping")
        return 0
    modules = [p for p in pages if p.type == "module" and p.fields]
    # Fully generated, so stamp OKF-conformant frontmatter directly.
    lines = ["---", "type: report", "---", "",
             "# Coverage", "", f"Generated by lint.py against `{local}`.", ""]
    lines.extend(_subsystem_coverage(modules))
    lines.extend(_directory_coverage(repo, pinning, modules))
    (root / "coverage.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print("coverage.md written")
    return 0


def _subsystem_coverage(modules):
    crit_field = CONFIG["criticality_field"]
    by_subsystem = {}
    for p in modules:
        by_subsystem.setdefault(p.fields.get("subsystem", "unassigned"), []).append(p)
    lines = ["## Module pages by subsystem", ""]
    for subsystem, members in sorted(by_subsystem.items()):
        if crit_field:
            counts = {}
            for p in members:
                crit = p.fields.get(crit_field, "unspecified")
                counts[crit] = counts.get(crit, 0) + 1
            breakdown = ", ".join(f"{n} {c}" for c, n in sorted(counts.items()))
            lines.append(f"- {subsystem}: {len(members)} module pages ({breakdown})")
        else:
            lines.append(f"- {subsystem}: {len(members)} module pages")
    lines.append("")
    return lines


def _directory_coverage(repo, pinning, modules):
    scope = pinning.get("wiki_scope", {})
    includes = scope.get("include", []) if isinstance(scope, dict) else []
    excludes = scope.get("exclude", []) if isinstance(scope, dict) else []
    source_paths = [p.fields.get("source_path", "").strip("/") for p in modules]
    lines = ["## Directory coverage", ""]
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
            (covered if source_path_covers(source_paths, rel) else uncovered).append(rel)
        total = len(covered) + len(uncovered)
        pct = round(100 * len(covered) / total) if total else 100
        lines.append(f"### {inc}")
        lines.append("")
        lines.append(f"{len(covered)}/{total} first-level directories covered ({pct}%)")
        for u in uncovered:
            lines.append(f"- uncovered: `{u}`")
        lines.append("")
    return lines
