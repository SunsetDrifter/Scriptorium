"""Mutable configuration holder and the config-validation boundary.

cli.main() calls configure() once at startup with a variant's CONFIG; every
other module imports the CONFIG dict object and reads it live. DEFAULTS
supplies every key the engine reads, so a variant only lists a key when it
overrides one. configure() validates user-supplied values (regexes, paths,
callables) and fails fast with a clear message.
"""

import re
from pathlib import PurePosixPath

CONFIG = {}

# Core knobs: the schema a variant declares. These have no "before" — they
# were always variant-declared — so each defaults to the neutral/disabled
# value: no pages, no required fields, every optional check off. A default
# here can only ever silence a check, never invent one, so a variant that
# omits a key gets nothing rather than a surprise finding.
CORE_DEFAULTS = {
    # Directories containing lint-checked pages, relative to the wiki root.
    "page_dirs": [],
    # Top-level entries allowed to exist but not scanned as pages (fnmatch).
    "non_page_allowed": [],
    # Immutable human-owned sources, excluded from the OKF bundle; None
    # disables the exclusion.
    "raw_dir": None,
    # Hot-core size guard: warn when CLAUDE.md exceeds this many lines.
    "claude_md_max_lines": 200,
    # Frontmatter required on every page, then per-type extras.
    "required_fields": [],
    "type_required": {},
    # Frontmatter fields restricted to a value set, globally then per type.
    "enum_fields": {},
    "type_enum_fields": {},
    # Frontmatter fields whose values must resolve to existing pages, and the
    # extra graph edges walked for orphan detection.
    "path_fields": [],
    "edge_fields": [],
    # Fields `reverse-deps` inverts into a reverse-dependency map.
    "reverse_fields": [],
    # Container-page membership rule; None disables check_membership. A rule
    # is {member_type, status_field, active_statuses, container_type,
    # container_field}.
    "membership": None,
    # Edge field whose targets must carry OKF `status: deprecated` (SPEC
    # §5.4), e.g. "supersedes"; None disables check_supersedes.
    "supersedes_field": None,
    # Per-field staleness rules: [{field, types, max_days, severity}].
    "staleness": [],
    # Days a `confidence: contested` page may sit untouched.
    "contested_max_days": 30,
    # Cross-page sync-drift rule; None disables check_sync_drift.
    "sync_drift": None,
    # Criticality/owner-review knobs; None disables their checks.
    "criticality_field": None,
    "owner_review_max_days": None,
    # Mermaid diagram checks: types that must carry one, node-count budgets.
    "mermaid_required_types": [],
    "mermaid_node_warn": None,
    "mermaid_node_error": None,
    # Directories holding NNNN-slug ADRs; empty disables the ADR checks.
    "adr_dirs": [],
    # Built-in index generator shape (ignored when index_body_fn is set).
    "index_mode": "flat",
    "index_sections": [],
    # `coverage` verb availability.
    "coverage": False,
    # Controlled-tag vocabulary file; None disables the tag checks.
    "taxonomy_file": None,
    # Triage inbox directory (None disables) and its warning thresholds.
    "inbox_dir": None,
    "inbox_warn_count": 10,
    "inbox_warn_age_days": 14,
}

# The engine's own subcommands, as (verb, one-line help). Declared here rather
# than in cli.py because this module is the validation boundary and needs the
# reserved names to reject an `extra_commands` verb that would shadow a
# built-in; cli.usage() renders this same table, so the verb list has exactly
# one declaration.
BUILTIN_COMMANDS = (
    ("check", "run all mechanical checks, exit 1 on errors"),
    ("rebuild-index", "regenerate the index from page frontmatter"),
    ("reverse-deps", "print the derived reverse-dependency maps"),
    ("coverage", "write coverage.md (variants with coverage enabled)"),
    ("help", "print this usage"),
)

# Engine extension points. Unlike the core knobs above, these default to the
# ORIGINAL wiki behavior — including the non-off `orphans: True`,
# `log_file: "log.md"`, `okf_conformance: True` and `types_glossary: True` —
# so a variant written before the extension existed keeps behaving as it did,
# and a variant that wants one off lists it as a genuine override.
EXTENSION_DEFAULTS = {
    # Enforce OKF v0.2 conformance (check_okf) and stamp okf_version
    # frontmatter into the rebuilt index. Off for non-OKF markdown trees.
    "okf_conformance": True,
    # Report pages with no inbound links (plus unlinked-mention hints).
    "orphans": True,
    # Path of the generated index relative to the wiki root; None disables the
    # index build and drift check entirely.
    "index_file": "index.md",
    # Callable(pages) -> str replacing the built-in index body generator.
    "index_body_fn": None,
    # Frontmatter fields validated as ISO dates when present. The
    # created/updated ordering check runs regardless of this list.
    "iso_date_fields": ["created", "updated"],
    # Extra (regex, label) pairs appended to the secrets scan.
    "extra_secret_patterns": [],
    # Secrets matches on lines matching any of these regexes are suppressed.
    "secret_allow_res": [],
    # Require taxonomy.md to carry a '## Page types' section describing every
    # schema type with a one-line meaning, so the bundle self-describes its
    # type vocabulary to OKF consumers. Off for non-wiki markdown trees.
    "types_glossary": True,
    # Directory of harness skill wrappers (e.g. ".claude/skills"), each a
    # <prefix><name>/SKILL.md whose body points at workflows/<name>.md. When
    # set, check_skills errors on any drift between the two sets. None
    # disables.
    "skills_dir": None,
    # Wrapper-name prefix, namespacing wiki skills away from a user's global
    # skills (field finding, 2026-07-22: a bare /triage collided with a
    # global triage skill). "wiki-" pairs workflows/triage.md with
    # <skills_dir>/wiki-triage/SKILL.md.
    "skills_prefix": "",
    # Append-only operations log checked by check_log; None disables.
    "log_file": "log.md",
    # Callables(pages, report, root) run at the end of every check pass.
    "extra_checks": [],
    # Variant subcommands: {verb: (callable(root) -> exit code, help text)}.
    # Registered verbs dispatch ahead of the wiki-root guard and appear in the
    # one usage string, so a variant never intercepts argv for itself.
    "extra_commands": {},
}

# Every key the engine reads, with its default. Reading these bare as
# CONFIG[key] is safe because configure() merges DEFAULTS under every variant
# config — that merge is the reason a variant may omit a key entirely.
DEFAULTS = {**CORE_DEFAULTS, **EXTENSION_DEFAULTS}


class ConfigError(Exception):
    """A variant lint.py holds an invalid value for an engine knob."""


def configure(config, index_entry_extra):
    merged = {**DEFAULTS, **config}
    merged["index_entry_extra"] = index_entry_extra
    _validate(merged)
    CONFIG.clear()
    CONFIG.update(merged)


def _compile(pattern, key):
    try:
        return re.compile(pattern)
    except re.error as e:
        raise ConfigError(f"{key}: invalid regex {pattern!r}: {e}")


def _validate_commands(commands):
    """Validate the extra_commands registration table so a misregistered verb
    fails here, once, instead of at dispatch time."""
    reserved = {verb for verb, _help in BUILTIN_COMMANDS}
    if not isinstance(commands, dict):
        raise ConfigError("extra_commands must be a {verb: (callable, help)} dict")
    for verb, entry in commands.items():
        if not isinstance(verb, str) or not verb.strip():
            raise ConfigError(f"extra_commands verbs must be non-empty strings: {verb!r}")
        if verb in reserved:
            raise ConfigError(f"extra_commands verb {verb!r} shadows an engine subcommand")
        try:
            fn, help_text = entry
        except (TypeError, ValueError):
            raise ConfigError(
                f"extra_commands[{verb!r}] must be a (callable, help) pair: {entry!r}")
        if not callable(fn):
            raise ConfigError(f"extra_commands[{verb!r}] handler must be callable: {fn!r}")
        if not isinstance(help_text, str) or not help_text.strip():
            raise ConfigError(f"extra_commands[{verb!r}] needs a non-empty help string")


MEMBERSHIP_KEYS = ("member_type", "status_field", "active_statuses",
                   "container_type", "container_field")


def _validate_membership(rule):
    """A membership rule must name every key check_membership reads, so an
    older rule (status_field arrived when OKF claimed `status`) fails here
    with the fix rather than as a KeyError mid-run."""
    if rule is None:
        return
    if not isinstance(rule, dict):
        raise ConfigError("membership must be None or a dict")
    missing = [k for k in MEMBERSHIP_KEYS if k not in rule]
    if missing:
        raise ConfigError(
            f"membership rule missing {missing}; status_field names the member "
            "lifecycle field (not `status`, which OKF v0.2 §5.4 defines)")


def _validate(cfg):
    """Validate user-supplied extension values at the config boundary and
    precompile the secret regexes so a bad pattern fails here, once, with a
    clear message rather than mid-scan with a raw traceback."""
    index_file = cfg["index_file"]
    if index_file is not None:
        if not isinstance(index_file, str) or not index_file.strip():
            raise ConfigError("index_file must be None or a non-empty relative path")
        posix = PurePosixPath(index_file)
        if posix.is_absolute() or ".." in posix.parts:
            raise ConfigError(
                f"index_file must stay within the wiki root: {index_file!r}")
    if cfg["log_file"] is not None and not isinstance(cfg["log_file"], str):
        raise ConfigError("log_file must be None or a relative path string")
    _validate_membership(cfg["membership"])
    if not isinstance(cfg["types_glossary"], bool):
        raise ConfigError("types_glossary must be a bool")
    skills_dir = cfg["skills_dir"]
    if skills_dir is not None:
        if not isinstance(skills_dir, str) or not skills_dir.strip():
            raise ConfigError("skills_dir must be None or a non-empty relative path")
        posix = PurePosixPath(skills_dir)
        if posix.is_absolute() or ".." in posix.parts:
            raise ConfigError(
                f"skills_dir must stay within the wiki root: {skills_dir!r}")
    if not isinstance(cfg["skills_prefix"], str):
        raise ConfigError("skills_prefix must be a string")
    if cfg["index_body_fn"] is not None and not callable(cfg["index_body_fn"]):
        raise ConfigError("index_body_fn must be None or callable")
    for fn in cfg["extra_checks"]:
        if not callable(fn):
            raise ConfigError(f"extra_checks entries must be callable: {fn!r}")
    _validate_commands(cfg["extra_commands"])

    compiled_extra = []
    for item in cfg["extra_secret_patterns"]:
        try:
            pattern, label = item
        except (TypeError, ValueError):
            raise ConfigError(
                f"extra_secret_patterns entries must be (regex, label): {item!r}")
        compiled_extra.append((_compile(pattern, "extra_secret_patterns"), label))
    cfg["secret_extra_compiled"] = compiled_extra
    cfg["secret_allow_compiled"] = [
        _compile(pattern, "secret_allow_res") for pattern in cfg["secret_allow_res"]
    ]
