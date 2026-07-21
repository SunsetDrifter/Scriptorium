"""Test helpers: load a variant's CONFIG, build fixture wikis, run checks."""

import sys
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "generic"))

from wikilint.settings import configure  # noqa: E402

VARIANTS = ["generic", "homelab", "codebase", "codebase-large"]

TODAY = date.today().isoformat()
DAYS_AGO_41 = (date.today() - timedelta(days=41)).isoformat()
DAYS_AGO_95 = (date.today() - timedelta(days=95)).isoformat()


def load_variant_config(variant):
    """Execute a variant's lint.py head (the __main__ guard keeps it inert)."""
    ns = {"__name__": "lint_config_under_test"}
    exec(compile((REPO / variant / "lint.py").read_text(), "lint.py", "exec"), ns)
    return ns["CONFIG"], ns["index_entry_extra"]


def use_variant_with(variant, **overrides):
    """Configure a variant's CONFIG with keys overridden (for testing the
    opt-in engine extension points). Call AFTER make_wiki, which reconfigures
    with the stock variant config."""
    config, extra = load_variant_config(variant)
    config = {**config, **overrides}
    configure(config, extra)
    return config


def use_variant(variant):
    return use_variant_with(variant)


def page(ptype, description, extra_fm="", body="Body.\n", tags="[alpha]",
         created=TODAY, updated=None):
    updated = updated or created
    return (
        f"---\ntype: {ptype}\ncreated: {created}\nupdated: {updated}\n"
        f"description: {description}\ntags: {tags}\nsources: []\n{extra_fm}---\n\n{body}"
    )


def make_wiki(tmp, variant="generic", files=None, taxonomy="- alpha — test tag\n- beta — test tag\n"):
    """Create a minimal valid wiki skeleton for the variant plus extra files."""
    root = Path(tmp)
    config = use_variant(variant)
    for d in config["page_dirs"]:
        (root / d).mkdir(parents=True, exist_ok=True)
    (root / config["inbox_dir"]).mkdir(parents=True, exist_ok=True)
    (root / "CLAUDE.md").write_text("---\ntype: tooling\n---\n\n# CLAUDE.md test stub\n")
    (root / "workflows").mkdir(exist_ok=True)
    types_section = "\n## Page types\n\n" + "".join(
        f"- {t} — test meaning\n" for t in config["type_required"]
    )
    (root / "taxonomy.md").write_text(
        "---\ntype: tooling\n---\n\n# Taxonomy\n\n" + taxonomy + types_section
    )
    (root / "log.md").write_text("# Log\n\n## 2026-07-01\n\n- **Lint**: ok\n")
    for rel, content in (files or {}).items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    return root


def gather(root):
    from wikilint.cli import gather_report
    return gather_report(Path(root))[1]


def findings(report, check=None, severity=None):
    return [
        i for i in report.items
        if (check is None or i[1] == check) and (severity is None or i[0] == severity)
    ]
