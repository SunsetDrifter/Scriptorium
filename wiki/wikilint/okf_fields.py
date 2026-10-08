"""OKF v0.2 page-level trust and lifecycle keys: the shape of `generated`
(SPEC §5.2, timestamps per §5) and the `status` value set (§5.4), plus the
supersedes -> deprecated rule tying our edge field to OKF's lifecycle."""

from .model import (
    OKF_STATUSES, build_link_index, parse_okf_datetime, resolve_link,
)
from .settings import CONFIG

DATETIME_EXAMPLE = "2026-10-08T14:00:00Z"


def check_okf_fields(pages, report):
    """Validate OKF-defined keys wherever a page carries them. Presence is
    the schema's business (required_fields); this checks only that a key OKF
    defines means what OKF says, so foreign consumers read it correctly."""
    if not CONFIG["okf_conformance"]:
        return
    for p in pages:
        if not p.fields:
            continue
        if "generated" in p.fields:
            check_generated(p, report)
        status = p.fields.get("status")
        if status is not None and status not in OKF_STATUSES:
            report.error(
                "okf", p.rel,
                f"status: {status!r} is not an OKF lifecycle value "
                f"{list(OKF_STATUSES)} (OKF v0.2 §5.4)",
            )


def check_generated(p, report):
    generated = p.fields["generated"]
    if not isinstance(generated, dict):
        report.error(
            "okf", p.rel,
            "generated must be a mapping, e.g. "
            f"{{ by: claude-code/<model>, at: {DATETIME_EXAMPLE} }} (OKF v0.2 §5.2)",
        )
        return
    if not generated.get("by"):
        report.error(
            "okf", p.rel,
            "generated.by is required within generated: an actor such as "
            "claude-code/<model> or human:<id> (OKF v0.2 §5.2, §7)",
        )
    at = generated.get("at")
    if at and parse_okf_datetime(at) is None:
        report.error(
            "okf", p.rel,
            f"generated.at {at!r} must be an ISO 8601 datetime with an explicit "
            f"offset, e.g. {DATETIME_EXAMPLE} (OKF v0.2 §5)",
        )


def check_supersedes(pages, report):
    """A page another page supersedes is OKF's `deprecated`: kept for links
    and history, no longer current. Requiring the status makes the forward
    banner machine-readable to any OKF consumer."""
    field = CONFIG["supersedes_field"]
    if not field:
        return
    by_stem, by_rel = build_link_index(pages)
    for p in pages:
        for value in p.path_list(field):
            target = resolve_link(value, by_stem, by_rel)
            if target is None or target.rel == p.rel:
                continue  # dangling references are check_links_and_orphans' job
            if (target.fields or {}).get("status") != "deprecated":
                report.error(
                    "supersedes", target.rel,
                    f"superseded by {p.rel}; set status: deprecated "
                    "(OKF v0.2 §5.4)",
                )
