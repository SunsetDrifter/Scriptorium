"""CLI entry point: subcommand dispatch and the check orchestrator."""

import sys
from pathlib import Path

from . import checks
from .derived import check_index_drift, rebuild_index, run_coverage, run_reverse_deps
from .model import Report, discover_pages
from .settings import CONFIG, configure

USAGE = """\
Usage:
    python3 lint.py check            run all mechanical checks, exit 1 on errors
    python3 lint.py rebuild-index    regenerate index.md from page frontmatter
    python3 lint.py reverse-deps     print the derived reverse-dependency maps
    python3 lint.py coverage         write coverage.md (variants with coverage enabled)
"""


def gather_report(root):
    """Run every mechanical check and return the Report (no printing).
    This is the testable core of `lint.py check`."""
    report = Report()
    pages = discover_pages(root, report)
    checks.check_frontmatter(pages, report)
    checks.check_filenames(pages, report)
    checks.check_links_and_orphans(pages, report)
    checks.check_membership(pages, report)
    checks.check_claude_size(root, report)
    checks.check_tags(pages, report, root)
    checks.check_contested_age(pages, report)
    checks.check_inferred_markers(pages, report)
    checks.check_inbox(root, report)
    checks.check_secrets(pages, report)
    checks.check_field_staleness(pages, report)
    checks.check_sync_drift(pages, report, root)
    checks.check_owner_review(pages, report)
    checks.check_mermaid(pages, report)
    checks.check_adrs(pages, report, root)
    checks.check_log(root, report)
    check_index_drift(pages, report, root)
    return len(pages), report


def run_check(root):
    count, report = gather_report(root)
    print(f"checked {count} pages")
    print(report.render())
    return 1 if report.has_errors else 0


def main(config, index_entry_extra, argv=None, root=None):
    configure(config, index_entry_extra)
    root = Path(root) if root else Path.cwd()
    if not (root / "CLAUDE.md").is_file():
        print("run from the wiki root (CLAUDE.md not found here)", file=sys.stderr)
        return 2
    args = sys.argv[1:] if argv is None else argv
    command = args[0] if args else "check"
    if command == "check":
        return run_check(root)
    if command == "rebuild-index":
        return rebuild_index(root)
    if command == "reverse-deps":
        return run_reverse_deps(root)
    if command == "coverage":
        if not CONFIG["coverage"]:
            print("coverage is not enabled for this variant")
            return 2
        return run_coverage(root)
    print(USAGE)
    return 2
