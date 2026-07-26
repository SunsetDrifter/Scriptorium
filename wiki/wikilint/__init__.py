"""Wiki lint engine. This package is kept identical across installs so
fixes propagate by copy; per-wiki behavior lives entirely in the CONFIG
dict and index_entry_extra() defined in the wiki root's lint.py."""

from .cli import main

__all__ = ["main"]
