"""Wiki lint engine. This package is kept identical across installs so
fixes propagate by copy; per-wiki behavior lives entirely in the CONFIG
dict and index_entry_extra() defined in the wiki root's lint.py."""

import sys

# The oldest CPython still in security support; bumped each October as the
# next release reaches end of life. This module must stay parseable by older
# interpreters so they get the message below instead of a traceback.
MIN_PYTHON = (3, 11)


def python_version_error(version_info=None):
    """A one-line explanation when the interpreter is below MIN_PYTHON."""
    v = tuple(version_info or sys.version_info)
    if v[:2] >= MIN_PYTHON:
        return None
    found = ".".join(str(part) for part in v[:3])
    return (
        f"Scriptorium's lint engine needs Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+, "
        f"found {found}. Install a newer python3 and put it first on PATH."
    )


_version_error = python_version_error()
if _version_error:
    raise SystemExit(_version_error)

from .cli import main  # noqa: E402

__all__ = ["MIN_PYTHON", "main", "python_version_error"]
