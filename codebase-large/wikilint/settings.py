"""Mutable configuration holder and the config-validation boundary.

cli.main() calls configure() once at startup with a variant's CONFIG; every
other module imports the CONFIG dict object and reads it live. Engine
extension points default to original wiki behavior via DEFAULTS, so a variant
only lists a key when it overrides one. configure() validates user-supplied
values (regexes, paths, callables) and fails fast with a clear message.
"""

import re
from pathlib import PurePosixPath

CONFIG = {}

# Engine extension points. Defaults live here, once, and preserve the original
# wiki behavior; a variant's lint.py overrides a key only to change it. Reading
# these bare as CONFIG[key] is safe because configure() merges DEFAULTS under
# every variant config.
DEFAULTS = {
    # Enforce OKF v0.1 conformance (check_okf) and stamp okf_version
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
    # Append-only operations log checked by check_log; None disables.
    "log_file": "log.md",
    # Callables(pages, report, root) run at the end of every check pass.
    "extra_checks": [],
}


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
    if not isinstance(cfg["types_glossary"], bool):
        raise ConfigError("types_glossary must be a bool")
    if cfg["index_body_fn"] is not None and not callable(cfg["index_body_fn"]):
        raise ConfigError("index_body_fn must be None or callable")
    for fn in cfg["extra_checks"]:
        if not callable(fn):
            raise ConfigError(f"extra_checks entries must be callable: {fn!r}")

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
